"""Reusable menu builders for compact Tk toolbars."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk
from typing import Any


@dataclass(frozen=True)
class MenuCommand:
    label: str
    command: object
    state: str | None = None


@dataclass(frozen=True)
class MenuCheckbutton:
    label: str
    variable: tk.Variable
    command: object | None = None


def create_popup_menu(parent: tk.Misc, *, tearoff: bool = False) -> tk.Menu:
    """Create a non-tearoff popup/dropdown menu using the project default."""

    return tk.Menu(parent, tearoff=tearoff)


def add_menu_commands(menu: tk.Menu, items: Iterable[MenuCommand | None]) -> tk.Menu:
    """Append command items, using ``None`` as a separator marker."""

    for item in items:
        if item is None:
            menu.add_separator()
            continue
        options: dict[str, Any] = {"label": item.label, "command": item.command}
        if item.state is not None:
            options["state"] = item.state
        menu.add_command(**options)
    return menu


def add_menu_checkbuttons(menu: tk.Menu, items: Iterable[MenuCheckbutton]) -> tk.Menu:
    """Append checkbutton items to a menu."""

    for item in items:
        menu.add_checkbutton(label=item.label, variable=item.variable, command=item.command)
    return menu


def pack_menubutton(
    parent: tk.Widget,
    text: str,
    menu: tk.Menu,
    *,
    side: str = "left",
    padx: tuple[int, int] | int = (0, 0),
    pady: tuple[int, int] | int = (0, 0),
    button_kwargs: dict[str, Any] | None = None,
) -> ttk.Menubutton:
    """Create, attach, and pack a Menubutton."""

    button = ttk.Menubutton(parent, text=text, **(button_kwargs or {}))
    button["menu"] = menu
    button.pack(side=side, padx=padx, pady=pady)
    return button
