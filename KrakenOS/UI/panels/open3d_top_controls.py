"""Top toolbar construction for the embedded Open 3D inspector.

The View / Scene / Carry rows are data in `open3d_toolbar.py` (phase 5f); this panel lays them out
in Tk, and `qt/inspector_toolbar.py` lays out the same catalogue in the Qt shell.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI import open3d_toolbar as catalogue
from KrakenOS.UI.widgets import (
    MenuCheckbutton,
    MenuCommand,
    add_menu_checkbuttons,
    add_menu_commands,
    create_popup_menu,
    pack_command_button,
    pack_commit_checkbutton,
    pack_commit_combobox,
    pack_menubutton,
)


class Open3DTopControlsPanel:
    """Build the View, Scene, and Carry toolbar rows from the catalogue."""

    def __init__(self, inspector: Any, *, normal_target_choices: Sequence[str] = ()) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        # kept for the call site; the choices are the catalogue's (the same constant)
        self.normal_target_choices = tuple(normal_target_choices)

    def build(self, parent: tk.Widget) -> ttk.Frame:
        toolbar_container = ttk.Frame(parent, padding=(8, 8, 8, 0))
        toolbar_container.grid(row=0, column=0, columnspan=3, sticky="ew")
        toolbar_container.columnconfigure(0, weight=1)
        for index, row in enumerate(catalogue.ROWS):
            self.build_row(toolbar_container, row, index)
        return toolbar_container

    # kept names: callers and guards build one row at a time
    def build_view_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        return self.build_row(parent, catalogue.ROWS[0], 0)

    def build_scene_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        return self.build_row(parent, catalogue.ROWS[1], 1)

    def build_carry_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        return self.build_row(parent, catalogue.ROWS[2], 2)

    def build_row(self, parent: tk.Widget, row, index: int) -> ttk.Frame:
        frame = ttk.Frame(parent)
        frame.grid(row=index, column=0, sticky="ew", pady=(0, 0) if index == 0 else (4, 0))
        ttk.Label(frame, text=row.title).pack(side="left", padx=(0, 6))
        for position, item in enumerate(row.left):
            self._pack(frame, item, side="left", padx=(0, 0) if position == 0 else (8, 0))
        for item in row.right:
            self._pack(frame, item, side="right", padx=(8, 0))
        if row.title == "View":
            self.inspector._open3d_toolbar_ray_count_entry = None
        return frame

    def _pack(self, frame: tk.Widget, item, *, side: str, padx) -> None:
        inspector = self.inspector
        if isinstance(item, catalogue.Command):
            pack_command_button(frame, item.label, command=catalogue.callback(inspector, item.target, item.args),
                                side=side, padx=padx)
        elif isinstance(item, (catalogue.Button, catalogue.Toggle)):
            if isinstance(item, catalogue.Toggle):
                button = ttk.Button(frame, textvariable=catalogue.resolve(inspector, item.textvar),
                                    command=catalogue.callback(inspector, item.target))
            else:
                button = ttk.Button(frame, text=item.label, command=catalogue.callback(inspector, item.target))
            button.pack(side=side, padx=padx)
            if item.handle:
                setattr(inspector, item.handle, button)
        elif isinstance(item, catalogue.Check):
            variable = catalogue.resolve(inspector, item.var)
            if variable is not None:
                pack_commit_checkbutton(frame, item.label, variable=variable,
                                        command=catalogue.callback(inspector, item.target), padx=padx)
        elif isinstance(item, catalogue.Choice):
            ttk.Label(frame, text=item.label).pack(side="left", padx=(padx[0] + 4, 4))
            on_commit = (catalogue.callback(inspector, item.target) if item.target else (lambda _event: None))
            pack_commit_combobox(frame, textvariable=catalogue.resolve(inspector, item.var), on_commit=on_commit,
                                 state="readonly", values=catalogue.choices_for(inspector, item), width=item.width)
        elif isinstance(item, catalogue.Entry):
            ttk.Label(frame, text=item.label).pack(side="left", padx=(padx[0] + 2, 2))
            ttk.Entry(frame, textvariable=catalogue.resolve(inspector, item.var), width=item.width).pack(side="left")
        elif isinstance(item, catalogue.Text):
            ttk.Label(frame, text=item.text).pack(side="left")
        elif isinstance(item, catalogue.Radio):
            menu = create_popup_menu(frame)
            for option_label, value in item.options:
                menu.add_radiobutton(label=option_label, value=value,
                                     variable=catalogue.resolve(inspector, item.var),
                                     command=catalogue.callback(inspector, item.target))
            pack_menubutton(frame, item.label, menu, padx=padx)
            if item.handle:
                setattr(inspector, item.handle, menu)
        elif isinstance(item, catalogue.Menu):
            pack_menubutton(frame, item.label, self._menu(frame, item), padx=padx)

    def _menu(self, parent: tk.Misc, spec) -> tk.Menu:
        inspector = self.inspector
        menu = create_popup_menu(parent)
        for entry in spec.entries:
            if entry is None:
                menu.add_separator()
            elif isinstance(entry, catalogue.Menu):
                menu.add_cascade(label=entry.label, menu=self._menu(menu, entry))
            elif isinstance(entry, catalogue.Check):
                variable = catalogue.resolve(inspector, entry.var)
                if variable is not None:
                    add_menu_checkbuttons(menu, (MenuCheckbutton(entry.label, variable,
                                                                 catalogue.callback(inspector, entry.target)),))
            elif isinstance(entry, catalogue.Command):
                add_menu_commands(menu, (MenuCommand(entry.label,
                                                     catalogue.callback(inspector, entry.target, entry.args)),))
        if spec.handle:
            setattr(inspector, spec.handle, menu)
        return menu
