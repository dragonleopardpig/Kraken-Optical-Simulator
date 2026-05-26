"""Reusable Tk commit bindings for compact editor controls."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk


TkEventCallback = Callable[[object | None], object]


def bind_entry_commit(
    widget: tk.Widget,
    on_commit: TkEventCallback,
    *,
    on_focus_in: TkEventCallback | None = None,
    add: str = "+",
) -> tk.Widget:
    """Bind ordinary text-entry commit gestures to one callback."""
    if on_focus_in is not None:
        widget.bind("<FocusIn>", on_focus_in, add=add)
    widget.bind("<FocusOut>", on_commit, add=add)
    widget.bind("<Return>", on_commit, add=add)
    widget.bind("<KP_Enter>", on_commit, add=add)
    return widget


def bind_combobox_commit(
    widget: tk.Widget,
    on_commit: TkEventCallback,
    *,
    on_focus_in: TkEventCallback | None = None,
    include_focus_out: bool = False,
    add: str = "+",
) -> tk.Widget:
    """Bind combobox selection/keyboard commit gestures to one callback."""
    if on_focus_in is not None:
        widget.bind("<FocusIn>", on_focus_in, add=add)
    widget.bind("<<ComboboxSelected>>", on_commit, add=add)
    widget.bind("<Return>", on_commit, add=add)
    widget.bind("<KP_Enter>", on_commit, add=add)
    if include_focus_out:
        widget.bind("<FocusOut>", on_commit, add=add)
    return widget
