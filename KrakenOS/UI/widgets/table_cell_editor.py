"""Reusable Treeview cell editor helpers."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

from KrakenOS.UI.widgets.commit_controls import CommitEntry


def place_commit_cell_entry(
    parent: tk.Widget,
    *,
    value: str,
    bbox: tuple[int, int, int, int],
    on_commit: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
) -> CommitEntry:
    """Place an inline Treeview cell editor with Kraken's standard gestures."""

    x, y, width, height = bbox
    editor = CommitEntry(parent, on_commit=lambda _event: on_commit())
    editor.insert(0, value)
    editor.place(x=x, y=y, width=width, height=height)
    editor.focus_set()
    try:
        editor.select_range(0, "end")
    except tk.TclError:
        pass
    if on_cancel is not None:
        editor.bind("<Escape>", lambda _event: on_cancel(), add="+")
    return editor
