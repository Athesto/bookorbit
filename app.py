"""BookOrbit entry point. Only the selected GUI is imported."""

import argparse
import json

from core import RUNTIME, TITLE, DockerController, browse, docker_path, ensure_runtime
lazy from panel import Panel
lazy from webview_ui import launch


def main():
    parser = argparse.ArgumentParser(description=TITLE)
    parser.add_argument("--ui", choices=("tkinter", "webview"), default="tkinter")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--browse", action="store_true")
    mode.add_argument("--diagnose", action="store_true")
    mode.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args()
    if args.diagnose:
        print(
            json.dumps(
                {
                    "runtime": str(RUNTIME),
                    "compose_exists": (RUNTIME / "compose.yaml").exists(),
                    "docker": docker_path(),
                    "ui": args.ui,
                }
            )
        )
        return
    ensure_runtime()
    if args.browse:
        browse()
        return
    controller = DockerController()
    try:
        if args.ui == "tkinter":
            panel = Panel(controller)
            if args.smoke_test:
                panel.after(1200, panel.close)
            panel.mainloop()
        else:
            launch(controller, smoke_test=args.smoke_test)
    finally:
        controller.close()
    if args.smoke_test:
        print(f"{args.ui} smoke test OK")


if __name__ == "__main__":
    main()
