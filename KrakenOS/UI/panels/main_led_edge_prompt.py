"""The Tk window that asks for the LED's edge distance (bugs/0977).

One value, Save / Cancel, centred on the screen by hand so that it lands there under Wayland
(bugs/0950 kept these small windows as they are for the Tk app). It lived in
`services/scene_placement_commands.py`, which is why that service imported tkinter. The command
that uses the answer -- and the shell's own prompt when another shell draws the editor -- stays in
the service.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

TITLE = "LED Edge Distance"
PROMPT = "Distance from object plane to the object-side LED box edge [mm]"


class MainLedEdgePrompt:
    """Ask for the LED edge distance in a Tk window while delegating state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def ask_led_edge_distance(self, initial_value: float, *, parent: Any = None) -> float | None:
        """The typed distance, never below zero; None when the window is cancelled or closed."""
        value_var = tk.StringVar(value=f"{max(float(initial_value), 0.0):g}")
        value_holder: dict[str, float] = {}

        dialog_parent = parent or self.editor       # the panel is not a widget (bugs/0955)
        dialog = tk.Toplevel(dialog_parent)
        dialog.withdraw()
        dialog.title(TITLE)
        dialog.transient(dialog_parent)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text=PROMPT).grid(row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w")
        entry = ttk.Entry(dialog, textvariable=value_var, width=18)
        entry.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

        def accept() -> None:
            try:
                value_holder["value"] = max(float(value_var.get()), 0.0)
            except ValueError:
                self.status_var.set("Invalid LED edge distance.")
                return
            dialog.destroy()

        ttk.Button(dialog, text="Save", command=accept).grid(row=2, column=0, padx=(12, 4), pady=(0, 12), sticky="e")
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(row=2, column=1, padx=(4, 12), pady=(0, 12), sticky="w")
        dialog.bind("<Return>", lambda _event: accept())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._show_centered_dialog(dialog)
        entry.focus_set()
        self.wait_window(dialog)

        value = value_holder.get("value")
        return float(value) if value is not None else None
