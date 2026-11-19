"""Original Tkinter interface, backed by the shared controller."""

import tkinter as tk
from tkinter import messagebox, ttk

from core import SERVICES, TITLE, Controller, browse, open_env


class Panel(tk.Tk):
    def __init__(self, controller: Controller):
        super().__init__()
        self.title(TITLE)
        self.geometry("1090x720")
        self.minsize(950, 620)
        self.configure(bg="#f3f5f8")
        self.controller = controller
        self.closing = False
        self.row_widgets = {}
        self.action_buttons = []
        self._ui()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(100, self.drain)
        self.after(250, self.refresh)

    def _ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", font=("Helvetica", 11), padding=(10, 7))
        style.configure("TCombobox", padding=5)
        header = tk.Frame(self, bg="#172b46", padx=25, pady=20)
        header.pack(fill="x")
        tk.Label(
            header,
            text="BOOKORBIT",
            bg="#172b46",
            fg="white",
            font=("Helvetica", 24, "bold"),
        ).pack(side="left")
        tk.Label(
            header,
            text="CONTROL PANEL",
            bg="#172b46",
            fg="#8fd6c8",
            font=("Helvetica", 11, "bold"),
        ).pack(side="left", padx=18, pady=(9, 0))
        body = tk.Frame(self, bg="#f3f5f8", padx=24, pady=17)
        body.pack(fill="both", expand=True)
        top = tk.Frame(body, bg="#f3f5f8")
        top.pack(fill="x", pady=(0, 14))
        self.connection = tk.StringVar(value="Comprobando Docker…")
        tk.Label(
            top,
            textvariable=self.connection,
            bg="#f3f5f8",
            fg="#43516a",
            font=("Helvetica", 11),
        ).pack(side="left")
        ttk.Button(top, text="Abrir .env", command=self.open_env).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(top, text="Abrir biblioteca ↗", command=self.browse).pack(
            side="right"
        )
        ttk.Button(top, text="Actualizar estado", command=self.refresh).pack(
            side="right", padx=8
        )
        table = tk.Frame(body, bg="white", padx=15, pady=10)
        table.pack(fill="x")
        for col, label in enumerate(["SERVICIO", "ESTADO", "ACCIONES"]):
            tk.Label(
                table,
                text=label,
                bg="white",
                fg="#64748b",
                anchor="w",
                font=("Helvetica", 10, "bold"),
            ).grid(row=0, column=col, sticky="w", pady=(0, 8))
        table.columnconfigure(0, weight=1)
        table.columnconfigure(1, minsize=175)
        for index, (service, title, subtitle) in enumerate(SERVICES, 1):
            name = tk.Frame(table, bg="white")
            name.grid(row=index, column=0, sticky="w", pady=8)
            tk.Label(
                name,
                text=title,
                bg="white",
                fg="#172b46",
                font=("Helvetica", 12, "bold"),
            ).pack(anchor="w")
            tk.Label(
                name, text=subtitle, bg="white", fg="#64748b", font=("Helvetica", 10)
            ).pack(anchor="w")
            status = tk.Label(
                table,
                text="● Sin comprobar",
                bg="white",
                fg="#64748b",
                font=("Helvetica", 11),
            )
            status.grid(row=index, column=1, sticky="w", padx=(0, 15))
            actions = tk.Frame(table, bg="white")
            actions.grid(row=index, column=2)
            buttons = {}
            for action, caption in [
                ("start", "Iniciar"),
                ("stop", "Detener"),
                ("restart", "Reiniciar"),
            ]:
                button = ttk.Button(
                    actions,
                    text=caption,
                    command=lambda a=action, s=service: self.act(a, s),
                )
                button.pack(side="left", padx=2)
                buttons[action] = button
                self.action_buttons.append(button)
            ttk.Button(
                actions, text="Logs", command=lambda s=service: self.watch_logs(s)
            ).pack(side="left", padx=2)
            self.row_widgets[service] = (status, buttons)
        toolbar = tk.Frame(body, bg="#f3f5f8")
        toolbar.pack(fill="x", pady=12)
        for text, action in [("Iniciar base", "start"), ("Detener todo", "stop")]:
            button = ttk.Button(
                toolbar, text=text, command=lambda a=action: self.act(a)
            )
            button.pack(side="left", padx=(0, 8))
            self.action_buttons.append(button)
        tk.Label(
            toolbar,
            text="Iniciar base: BookOrbit + PostgreSQL + Edge TTS. Kokoro es opcional.",
            bg="#f3f5f8",
            fg="#64748b",
            font=("Helvetica", 10),
        ).pack(side="left", padx=5)
        logs_header = tk.Frame(body, bg="#f3f5f8")
        logs_header.pack(fill="x", pady=(0, 7))
        tk.Label(
            logs_header,
            text="LOGS Y ACTIVIDAD",
            bg="#f3f5f8",
            fg="#172b46",
            font=("Helvetica", 11, "bold"),
        ).pack(side="left")
        self.log_choice = tk.StringVar(value="Todos")
        chooser = ttk.Combobox(
            logs_header,
            textvariable=self.log_choice,
            state="readonly",
            width=20,
            values=["Todos"] + [s[0] for s in SERVICES],
        )
        chooser.pack(side="left", padx=12)
        ttk.Button(
            logs_header, text="Seguir logs", command=lambda: self.watch_logs()
        ).pack(side="left")
        ttk.Button(logs_header, text="Pausar", command=self.stop_logs).pack(
            side="left", padx=7
        )
        ttk.Button(logs_header, text="Limpiar", command=self.clear_logs).pack(
            side="right"
        )
        frame = tk.Frame(body)
        frame.pack(fill="both", expand=True)
        self.output = tk.Text(
            frame,
            bg="#101b2c",
            fg="#d5e4f4",
            insertbackground="white",
            font=("Menlo", 10),
            wrap="word",
            relief="flat",
            padx=12,
            pady=10,
            state="disabled",
        )
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(frame, command=self.output.yview)
        scrollbar.pack(side="right", fill="y")
        self.output.configure(yscrollcommand=scrollbar.set)
        tk.Label(
            body,
            text="Cerrar este panel no detiene los contenedores. Docker Desktop debe estar iniciado.",
            bg="#f3f5f8",
            fg="#64748b",
            font=("Helvetica", 10),
        ).pack(anchor="w", pady=(9, 0))
        self.append(
            "Panel listo. Los servicios solo cambian cuando pulsas una acción.\n"
        )

    def append(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text)
        if int(self.output.index("end-1c").split(".")[0]) > 3000:
            self.output.delete("1.0", "500.0")
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_logs(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def open_env(self):
        try:
            open_env()
        except Exception as error:
            messagebox.showerror(TITLE, str(error))

    def browse(self):
        browse()

    def act(self, action, service=None):
        if (
            service == "read-aloud-worker"
            and action == "start"
            and not messagebox.askyesno(
                TITLE,
                "Este servicio requiere configurar su token y URL en BookOrbit. ¿Continuar?",
            )
        ):
            return
        if self.controller.act(action, service):
            for button in self.action_buttons:
                button.configure(state="disabled")

    def refresh(self):
        self.controller.refresh()

    def watch_logs(self, service=None):
        service = service or self.log_choice.get()
        self.log_choice.set(service)
        self.controller.watch_logs(service)

    def stop_logs(self):
        self.controller.stop_logs()

    def drain(self):
        if self.closing:
            return
        for kind, value in self.controller.poll():
            if kind == "log":
                self.append(value[1])
            elif kind == "activity":
                self.append(value)
            elif kind == "action":
                for button in self.action_buttons:
                    button.configure(state="normal")
                code, output = value
                self.append(
                    output
                    + (
                        "\nOperación completada.\n"
                        if code == 0
                        else "\nLa operación falló.\n"
                    )
                )
                self.refresh()
            elif kind in ("status", "status_error"):
                if kind == "status_error":
                    self.connection.set("Docker no disponible · revisa Docker Desktop")
                    for label, _ in self.row_widgets.values():
                        label.configure(text="● Sin conexión", fg="#b45309")
                else:
                    self.connection.set("Docker conectado · proyecto bookorbit")
                    for service, (label, _) in self.row_widgets.items():
                        row = value.get(service, {})
                        state = row.get("State", "not-created")
                        health = row.get("Health", "")
                        text = {
                            "running": "Activo",
                            "exited": "Detenido",
                            "restarting": "Reiniciando",
                            "not-created": "No creado",
                        }.get(state, state)
                        if health:
                            text += " · " + health
                        label.configure(
                            text="● " + text,
                            fg="#15803d"
                            if state == "running" and health != "unhealthy"
                            else "#b45309",
                        )
        self.after(100, self.drain)

    def close(self):
        self.closing = True
        self.controller.close()
        self.destroy()
