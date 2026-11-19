"""Build and archive the desktop app on its target operating system."""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE = "BookOrbit Control"


def main():
    if sys.platform not in {"darwin", "win32"}:
        raise SystemExit("Builds are supported on macOS and Windows only.")
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        TITLE,
        "--hidden-import",
        "panel",
        "--hidden-import",
        "webview_ui",
        "--add-data",
        "index.html:.",
        "--add-data",
        "resources:resources",
    ]
    if sys.platform == "darwin":
        command += [
            "--osx-bundle-identifier",
            "io.athesto.bookorbit-control",
            "--icon",
            "resources/bookorbit.icns",
        ]
    command.append("app.py")
    subprocess.run(command, cwd=ROOT, check=True)
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    system = "macos" if sys.platform == "darwin" else "windows"
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64"}.get(
        platform.machine().lower(), platform.machine().lower()
    )
    archive = output / f"bookorbit-control-{version}-{system}-{arch}.zip"
    if sys.platform == "darwin":
        subprocess.run(
            [
                "/usr/bin/ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(ROOT / "dist" / f"{TITLE}.app"),
                str(archive),
            ],
            check=True,
        )
    else:
        shutil.make_archive(str(archive.with_suffix("")), "zip", ROOT / "dist", TITLE)
    with archive.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n")
    print(f"Created {archive}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(
                f"### Build {version}\n\n- {archive.name}\n- SHA256: `{checksum}`\n"
            )


if __name__ == "__main__":
    main()
