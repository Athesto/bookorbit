"""Shared Docker operations. No dependency on either graphical interface."""

from __future__ import annotations

import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import threading
import webbrowser
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import NamedTuple, Protocol

# Finder launches apps with a minimal PATH; Docker credential helpers need these paths.
os.environ["PATH"] = os.pathsep.join(
    [
        str(Path.home() / ".docker/bin"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
        "/Applications/Docker.app/Contents/Resources/bin",
        os.environ.get("PATH", "/usr/bin:/bin"),
    ]
)

TITLE = "BookOrbit Control"
RESOURCES = Path(__file__).resolve().parent / "resources"


class PlatformConfig(NamedTuple):
    data_dir: Callable[[], Path]
    editor: tuple[str, ...]


PLATFORMS: dict[str, PlatformConfig] = {
    "darwin": PlatformConfig(
        data_dir=lambda: Path.home() / "Library" / "Application Support" / TITLE,
        editor=("/usr/bin/open", "-a", "TextEdit"),
    ),
    "win32": PlatformConfig(
        data_dir=lambda: Path(os.environ["LOCALAPPDATA"]) / TITLE,
        editor=("notepad.exe",),
    ),
}

try:
    PLATFORM = PLATFORMS[sys.platform]
except KeyError:
    raise RuntimeError(f"Plataforma no soportada: {sys.platform}") from None

DATA = Path(os.environ.get("BOOKORBIT_CONTROL_HOME") or PLATFORM.data_dir())
RUNTIME = Path(os.environ.get("BOOKORBIT_RUNTIME_DIR") or DATA / "runtime")
SERVICES = [
    ("app", "BookOrbit", "Biblioteca y lector web"),
    ("postgres", "PostgreSQL", "Base de datos"),
    ("kokoro", "Kokoro", "Narración local · CPU"),
    ("edge-tts", "Edge TTS", "Narración online · Microsoft"),
    ("read-aloud-worker", "Read-aloud", "Sincronización de texto y audio"),
]


def docker_path():
    candidates = [
        shutil.which("docker"),
        "/usr/local/bin/docker",
        "/opt/homebrew/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("No se encontró Docker. Instala e inicia Docker Desktop.")


def ensure_runtime():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if not (RUNTIME / "compose.yaml").exists():
        shutil.copy2(RESOURCES / "compose.yaml", RUNTIME / "compose.yaml")
        shutil.copy2(RESOURCES / "Dockerfile.edge-tts", RUNTIME / "Dockerfile.edge-tts")
    if not (RUNTIME / ".env").exists():
        values = {
            "APP_IMAGE": "ghcr.io/bookorbit/bookorbit:latest",
            "APP_URL": "http://localhost:3000",
            "POSTGRES_USER": "bookorbit",
            "POSTGRES_DB": "bookorbit",
            "POSTGRES_PASSWORD": secrets.token_hex(24),
            "JWT_SECRET": secrets.token_hex(32),
            "SETUP_BOOTSTRAP_TOKEN": secrets.token_hex(16),
            "EDGE_TTS_API_KEY": secrets.token_hex(24),
            "BOOKS_HOST_PATH": str(DATA / "books"),
            "TZ": "America/Bogota",
        }
        fd = os.open(RUNTIME / ".env", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write("".join(f"{key}={value}\n" for key, value in values.items()))
        (DATA / "books").mkdir(exist_ok=True)


def compose_args(*args):
    return [
        docker_path(),
        "compose",
        "--project-directory",
        str(RUNTIME),
        "--env-file",
        str(RUNTIME / ".env"),
        "-f",
        str(RUNTIME / "compose.yaml"),
        *args,
    ]


def parse_status(output):
    """Accept both Compose's NDJSON and JSON-array output."""
    if not output.strip():
        return {}
    try:
        parsed = json.loads(output)
        records = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        records = [json.loads(line) for line in output.splitlines() if line.strip()]
    return {row["Service"]: row for row in records if row.get("Service")}


def open_env() -> None:
    try:
        subprocess.Popen([*PLATFORM.editor, str(RUNTIME / ".env")])
    except OSError as error:
        raise RuntimeError(f"No se pudo abrir el archivo .env: {error}") from error


def browse():
    values = {}
    for line in (RUNTIME / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    # APP_URL may be a public reverse-proxy URL or a template placeholder.
    # This desktop launcher opens the port published on the local machine.
    port = values.get("APP_PORT") or "3000"
    url = (
        os.environ.get("BOOKORBIT_URL")
        or values.get("BOOKORBIT_URL")
        or f"http://localhost:{port}"
    )
    webbrowser.open(url)


class Controller(Protocol):
    """Contract consumed by both GUI adapters; methods publish events to poll()."""

    def act(self, action: str, service: str | None = None) -> bool: ...
    def refresh(self) -> None: ...
    def watch_logs(self, service: str | None = None) -> None: ...
    def stop_logs(self) -> None: ...
    def poll(self) -> list[tuple[str, object]]: ...
    def close(self) -> None: ...


class DockerController:
    def __init__(self):
        self.events = queue.Queue(maxsize=6000)
        self.log_process = None
        self.log_generation = 0
        self.busy = False
        self.closing = False
        self.status_loading = False
        self._action_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._logs_lock = threading.RLock()

    @staticmethod
    def _validate(service):
        if service is not None and service not in {s[0] for s in SERVICES}:
            raise ValueError("Servicio no permitido")

    def _append(self, text):
        self.events.put(("activity", text))

    def poll(self):
        items = []
        for _ in range(200):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log" and value[0] != self.log_generation:
                continue
            items.append((kind, value))
        return items

    def close(self):
        self.closing = True
        self.stop_logs()

    def act(self, action, service=None):
        self._validate(service)
        if action not in {"start", "stop", "restart"}:
            raise ValueError("Acción no permitida")
        if not self._action_lock.acquire(blocking=False):
            return False
        if self.closing:
            self._action_lock.release()
            return False
        self.busy = True
        self._append(f"\n→ {action} {service or 'servicios base / todos'}\n")

        def work():
            try:
                if action == "start":
                    args = [
                        "up",
                        "-d",
                        *([service] if service else ["app", "postgres", "edge-tts"]),
                    ]
                else:
                    args = ["--profile", "*", action, *([service] if service else [])]
                result = subprocess.run(
                    compose_args(*args), capture_output=True, text=True, timeout=600
                )
                self.events.put(
                    ("action", (result.returncode, result.stdout + result.stderr))
                )
            except Exception as error:
                self.events.put(("action", (1, str(error))))
            finally:
                self.busy = False
                self._action_lock.release()

        threading.Thread(target=work, daemon=True).start()
        return True

    def refresh(self):
        if self.closing or not self._status_lock.acquire(blocking=False):
            return
        self.status_loading = True

        def work():
            try:
                result = subprocess.run(
                    compose_args("--profile", "*", "ps", "-a", "--format", "json"),
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if result.returncode:
                    raise RuntimeError(result.stderr.strip())
                self.events.put(("status", parse_status(result.stdout)))
            except Exception as error:
                self.events.put(("status_error", str(error)))
            finally:
                self.status_loading = False
                self._status_lock.release()

        threading.Thread(target=work, daemon=True).start()

    def stop_logs(self):
        with self._logs_lock:
            self._stop_logs()

    def _stop_logs(self):
        self.log_generation += 1
        process, self.log_process = self.log_process, None
        if process and process.poll() is None:
            process.terminate()
            threading.Thread(target=self._reap, args=(process,), daemon=True).start()

    @staticmethod
    def _reap(process):
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def watch_logs(self, service=None):
        with self._logs_lock:
            self._watch_logs(service)

    def _watch_logs(self, service=None):
        if self.closing:
            return
        service = service or "Todos"
        self._validate(None if service == "Todos" else service)
        self.stop_logs()
        generation = self.log_generation
        try:
            process = subprocess.Popen(
                compose_args(
                    "--profile",
                    "*",
                    "logs",
                    "--no-color",
                    "--tail=100",
                    "--follow",
                    *([] if service == "Todos" else [service]),
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            self.log_process = process
        except Exception as error:
            self._append(f"Logs: {error}\n")
            return
        self._append(f"\n— Logs: {service} —\n")

        def read():
            stream = process.stdout
            # Popen's type permits None, but stdout=PIPE guarantees a stream here.
            assert stream is not None, "stdout=PIPE debe crear un flujo de salida"
            for line in stream:
                if self.closing or generation != self.log_generation:
                    break
                with suppress(queue.Full):
                    self.events.put_nowait(("log", (generation, line)))
            stream.close()
            process.wait()

        threading.Thread(target=read, daemon=True).start()
