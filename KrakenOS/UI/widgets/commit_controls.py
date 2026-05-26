"""Reusable Tk controls with standard commit bindings."""

from __future__ import annotations

import tkinter as tk
from typing import Any
from tkinter import ttk

from KrakenOS.UI.widgets.commit_bindings import TkEventCallback, bind_entry_commit


class CommitEntry(ttk.Entry):
    """ttk.Entry with the Kraken UI's standard commit gestures."""

    def __init__(
        self,
        master=None,
        *,
        on_commit: TkEventCallback | None = None,
        on_focus_in: TkEventCallback | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        if on_commit is not None:
            self.bind_commit(on_commit, on_focus_in=on_focus_in)
        elif on_focus_in is not None:
            self.bind("<FocusIn>", on_focus_in, add="+")

    def bind_commit(
        self,
        on_commit: TkEventCallback,
        *,
        on_focus_in: TkEventCallback | None = None,
        add: str = "+",
    ):
        bind_entry_commit(self, on_commit, on_focus_in=on_focus_in, add=add)
        return self


def grid_labeled_commit_entry(
    parent: tk.Widget,
    row: int,
    column: int,
    label: str,
    textvariable: tk.Variable,
    *,
    on_commit: TkEventCallback,
    on_focus_in: TkEventCallback | None = None,
    width: int = 10,
    label_textvariable: tk.Variable | None = None,
    label_padx: tuple[int, int] | None = None,
    entry_padx: tuple[int, int] | None = None,
    label_pady: tuple[int, int] = (0, 2),
    entry_pady: tuple[int, int] = (0, 8),
    label_sticky: str = "w",
    entry_sticky: str = "ew",
    label_kwargs: dict[str, Any] | None = None,
    entry_kwargs: dict[str, Any] | None = None,
) -> CommitEntry:
    """Grid a label plus CommitEntry pair using the compact control-panel layout."""
    left_pad = (8, 0) if column else (0, 0)
    label_padding = left_pad if label_padx is None else label_padx
    entry_padding = left_pad if entry_padx is None else entry_padx
    label_options = dict(label_kwargs or {})
    if label_textvariable is None:
        label_options["text"] = label
    else:
        label_options["textvariable"] = label_textvariable
    label_widget = ttk.Label(parent, **label_options)
    label_widget.grid(
        row=row,
        column=column,
        sticky=label_sticky,
        pady=label_pady,
        padx=label_padding,
    )
    entry = CommitEntry(
        parent,
        textvariable=textvariable,
        width=width,
        on_commit=on_commit,
        on_focus_in=on_focus_in,
        **(entry_kwargs or {}),
    )
    entry.label_widget = label_widget
    entry.grid(
        row=row + 1,
        column=column,
        sticky=entry_sticky,
        pady=entry_pady,
        padx=entry_padding,
    )
    return entry
