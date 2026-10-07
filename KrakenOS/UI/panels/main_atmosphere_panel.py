"""Main layout-editor atmosphere controls and dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.system_controls import ATMOSPHERE_CONTROL_SPECS, ATMOSPHERE_NOTE, ATMOSPHERE_TITLE
from KrakenOS.UI.widgets import bind_entry_commit



class MainAtmospherePanel:
    """Build atmosphere controls while keeping settings on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        atmos_plot_mode_default: str,
        atmos_plot_mode_values: Sequence[str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "atmos_plot_mode_default", atmos_plot_mode_default)
        object.__setattr__(self, "atmos_plot_mode_values", tuple(atmos_plot_mode_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "atmos_plot_mode_default", "atmos_plot_mode_values"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _bind_deferred_manual_update(self, widget: tk.Widget) -> None:
        """An atmosphere entry commits on Return, the keypad's Enter and on leaving it.

        What a commit DOES is the model's, `_commit_manual_update`; the binding is Tk, and the
        panel's own since bugs/0985 -- it is the only one that binds these.
        """
        bind_entry_commit(widget, self._commit_manual_update, on_focus_in=self._begin_history_capture)

    def build_hidden_panel(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1)

        ttk.Label(parent, text="Observatory preset").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.atmos_observatory_var = tk.StringVar(value="Manual")
        self.atmos_observatory_menu = ttk.Combobox(
            parent,
            textvariable=self.atmos_observatory_var,
            state="readonly",
            width=16,
            values=self._atmos_observatory_names(),
        )
        self.atmos_observatory_menu.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.atmos_observatory_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.atmos_observatory_menu.bind("<<ComboboxSelected>>", self._on_atmos_observatory_changed)

        ttk.Label(parent, text="Atmos plot").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.atmos_plot_mode_var = tk.StringVar(value=self.atmos_plot_mode_default)
        self.atmos_plot_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.atmos_plot_mode_var,
            state="readonly",
            width=16,
            values=self.atmos_plot_mode_values,
        )
        self.atmos_plot_mode_menu.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.atmos_plot_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.atmos_plot_mode_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        entries: list[ttk.Entry] = []
        for index, (label, attr_name, default) in enumerate(ATMOSPHERE_CONTROL_SPECS):
            row = 4 + (index // 2) * 2
            column = index % 2
            ttk.Label(parent, text=label).grid(
                row=row,
                column=column,
                sticky="w",
                pady=(0 if row == 0 else 6, 2),
                padx=(8 if column else 0, 0),
            )
            var = tk.StringVar(value=default)
            setattr(self, attr_name, var)
            entry = ttk.Entry(parent, textvariable=var, width=12)
            entry.grid(row=row + 1, column=column, sticky="ew", padx=(8 if column else 0, 0))
            entries.append(entry)

        self.atmosphere_summary_var = tk.StringVar(value="")
        ttk.Label(
            parent,
            textvariable=self.atmosphere_summary_var,
            foreground="#3f4a5a",
            wraplength=460,
            justify="left",
        ).grid(row=14, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        for entry in entries:
            self._bind_deferred_manual_update(entry)
        for _label, attr_name, _default in ATMOSPHERE_CONTROL_SPECS:
            var = getattr(self, attr_name)
            var.trace_add("write", lambda *_args: self._update_atmosphere_summary())
        self.atmos_plot_mode_var.trace_add("write", lambda *_args: self._update_atmosphere_summary())
        self._update_atmosphere_summary()

    def open_settings_dialog(self) -> None:
        window = self.__dict__.get("_atmosphere_settings_window")
        if window is not None:
            try:
                if window.winfo_exists():
                    window.deiconify()
                    window.lift()
                    window.focus_force()
                    return
            except Exception:
                pass

        window = tk.Toplevel(self.editor)
        self._atmosphere_settings_window = window
        window.title(ATMOSPHERE_TITLE)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self.close_settings_dialog)
        window.columnconfigure(0, weight=1)

        root = ttk.Frame(window, padding=12)
        root.grid(row=0, column=0, sticky="nsew")
        for column in range(2):
            root.columnconfigure(column, weight=1)

        ttk.Label(
            root,
            text=ATMOSPHERE_NOTE,
            foreground="#475569",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(root, text="Observatory preset").grid(row=1, column=0, sticky="w", pady=(0, 2))
        observatory_menu = ttk.Combobox(
            root,
            textvariable=self.atmos_observatory_var,
            state="readonly",
            values=self._atmos_observatory_names(),
            width=20,
        )
        observatory_menu.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        observatory_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        observatory_menu.bind("<<ComboboxSelected>>", self._on_atmos_observatory_changed)

        ttk.Label(root, text="Atmos plot").grid(row=3, column=0, sticky="w", pady=(0, 2))
        plot_menu = ttk.Combobox(
            root,
            textvariable=self.atmos_plot_mode_var,
            state="readonly",
            values=self.atmos_plot_mode_values,
            width=20,
        )
        plot_menu.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        plot_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        plot_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        for index, (label, attr_name, _default) in enumerate(ATMOSPHERE_CONTROL_SPECS):
            row = 5 + (index // 2) * 2
            column = index % 2
            ttk.Label(root, text=label).grid(
                row=row,
                column=column,
                sticky="w",
                pady=(6, 2),
                padx=(8 if column else 0, 0),
            )
            entry = ttk.Entry(root, textvariable=getattr(self, attr_name), width=14)
            entry.grid(row=row + 1, column=column, sticky="ew", padx=(8 if column else 0, 0))
            self._bind_deferred_manual_update(entry)

        ttk.Label(
            root,
            textvariable=self.atmosphere_summary_var,
            foreground="#3f4a5a",
            wraplength=520,
            justify="left",
        ).grid(row=16, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        buttons = ttk.Frame(root)
        buttons.grid(row=17, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(
            buttons,
            text="Apply",
            command=lambda: self.apply_atmosphere_settings(),
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Apply + Atmos",
            command=lambda: self.apply_atmosphere_settings(show_plot=True),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Close", command=self.close_settings_dialog).pack(side="left", padx=(8, 0))

        self._show_centered_dialog(window)

    def close_settings_dialog(self) -> None:
        window = self.__dict__.get("_atmosphere_settings_window")
        self._atmosphere_settings_window = None
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
