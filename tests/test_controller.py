"""No Docker daemon or real containers required."""

import json
import subprocess
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import core
from core import DockerController, parse_status


class ControllerTests(unittest.TestCase):
    def collect(self, controller, kind):
        events = []
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            events.extend(controller.poll())
            if any(k == kind for k, _ in events):
                return next(v for k, v in events if k == kind)
            time.sleep(0.01)
        self.fail(f"Missing event: {kind}")

    def test_parse_compose_formats(self):
        row = {"Service": "app", "State": "running"}
        for text in (
            json.dumps([row]),
            json.dumps(row),
            json.dumps(row) + "\n" + json.dumps({"Service": "postgres"}),
        ):
            self.assertEqual(parse_status(text)["app"], row)
        self.assertEqual(parse_status(""), {})

    def test_actions_keep_base_targets_and_profiles(self):
        controller = DockerController()
        result = SimpleNamespace(returncode=0, stdout="OK", stderr="")
        with (
            patch.object(core, "compose_args", side_effect=lambda *a: list(a)),
            patch.object(core.subprocess, "run", return_value=result) as run,
        ):
            self.assertTrue(controller.act("start"))
            self.assertEqual(self.collect(controller, "action"), (0, "OK"))
            self.assertEqual(
                run.call_args.args[0], ["up", "-d", "app", "postgres", "edge-tts"]
            )
            self.assertTrue(controller.act("stop"))
            self.collect(controller, "action")
            self.assertEqual(run.call_args.args[0], ["--profile", "*", "stop"])
            self.assertTrue(controller.act("restart", "kokoro"))
            self.collect(controller, "action")
            self.assertEqual(
                run.call_args.args[0], ["--profile", "*", "restart", "kokoro"]
            )

    def test_invalid_inputs_do_not_run_commands(self):
        controller = DockerController()
        with patch.object(core.subprocess, "run") as run:
            for action, service in [("down", None), ("start", "--help")]:
                with self.assertRaises(ValueError):
                    controller.act(action, service)
            with self.assertRaises(ValueError):
                controller.watch_logs("--help")
            run.assert_not_called()

    def test_serializes_actions_and_recovers_from_errors(self):
        controller = DockerController()
        entered, release = threading.Event(), threading.Event()

        def run(*a, **kw):
            entered.set()
            release.wait(2)
            raise OSError("Docker unavailable")

        with (
            patch.object(core, "compose_args", return_value=["docker"]),
            patch.object(core.subprocess, "run", side_effect=run),
        ):
            self.assertTrue(controller.act("start"))
            self.assertTrue(entered.wait(1))
            self.assertFalse(controller.act("stop"))
            release.set()
            self.assertEqual(
                self.collect(controller, "action"), (1, "Docker unavailable")
            )
        self.assertFalse(controller.busy)
        controller.close()
        self.assertFalse(controller.act("start"))

    def test_refresh_error_and_obsolete_logs(self):
        controller = DockerController()
        with (
            patch.object(core, "compose_args", return_value=["docker"]),
            patch.object(core.subprocess, "run", side_effect=OSError("offline")),
        ):
            controller.refresh()
            self.assertEqual(self.collect(controller, "status_error"), "offline")
        controller.events.put(("log", (0, "obsolete")))
        controller.stop_logs()
        self.assertEqual(controller.poll(), [])

    def test_lazy_imports_do_not_load_either_gui(self):
        root = str(Path(__file__).resolve().parents[1])
        code = """import sys
import app
assert "panel" not in sys.modules
assert "tkinter" not in sys.modules
assert "webview_ui" not in sys.modules
assert "webview" not in sys.modules
"""
        subprocess.run([sys.executable, "-c", code], cwd=root, check=True)

    def test_loading_one_adapter_does_not_load_the_other(self):
        root = str(Path(__file__).resolve().parents[1])
        for name, absent in [("Panel", "webview"), ("launch", "tkinter")]:
            code = f'import sys; import app; obj=app.{name}; assert "{absent}" not in sys.modules'
            subprocess.run([sys.executable, "-c", code], cwd=root, check=True)


if __name__ == "__main__":
    unittest.main()
