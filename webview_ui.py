"""Explicit, small JavaScript API; Docker logic stays in core."""

import threading
from pathlib import Path

import webview

from core import SERVICES, TITLE, Controller, browse, open_env


class WebviewAPI:
    def __init__(self, controller: Controller):
        self._controller = controller

    def services(self):
        return [{"id": s, "title": t, "subtitle": d} for s, t, d in SERVICES]

    def act(self, action, service=None, confirmed=False):
        if (
            service == "read-aloud-worker"
            and action == "start"
            and confirmed is not True
        ):
            raise ValueError("Confirma primero la configuración del worker.")
        return self._controller.act(action, service)

    def refresh(self):
        self._controller.refresh()

    def poll(self):
        return self._controller.poll()

    def watch_logs(self, service=None):
        self._controller.watch_logs(service)

    def stop_logs(self):
        self._controller.stop_logs()

    def browse(self):
        browse()

    def open_env(self):
        open_env()


def launch(controller: Controller, *, smoke_test=False):
    # Inline HTML avoids exposing the project directory through a local HTTP server.
    html = Path(__file__).with_name("index.html").read_text(encoding="utf-8")
    window = webview.create_window(
        TITLE,
        html=html,
        js_api=WebviewAPI(controller),
        width=1120,
        height=800,
        min_size=(950, 620),
        background_color="#f5f5f7",
    )
    window.events.closed += controller.close
    if smoke_test:

        def ready():
            timer = threading.Timer(1.5, window.destroy)
            timer.daemon = True
            timer.start()

        window.events.loaded += ready
    webview.start()
