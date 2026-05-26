"""Reusable Tk controls with standard commit bindings."""

from __future__ import annotations

import tkinter as tk
from typing import Any
from tkinter import ttk

from KrakenOS.UI.widgets.commit_bindings import TkEventCallback, bind_combobox_commit, bind_entry_commit


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


class CommitCombobox(ttk.Combobox):
    """ttk.Combobox with the Kraken UI's standard commit gestures."""

    def __init__(
        self,
        master=None,
        *,
        on_commit: TkEventCallback | None = None,
        on_focus_in: TkEventCallback | None = None,
        include_focus_out: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        if on_commit is not None:
            self.bind_commit(
                on_commit,
                on_focus_in=on_focus_in,
                include_focus_out=include_focus_out,
            )
        elif on_focus_in is not None:
            self.bind("<FocusIn>", on_focus_in, add="+")

    def bind_commit(
        self,
        on_commit: TkEventCallback,
        *,
        on_focus_in: TkEventCallback | None = None,
        include_focus_out: bool = False,
        add: str = "+",
    ):
        bind_combobox_commit(
            self,
            on_commit,
            on_focus_in=on_focus_in,
            include_focus_out=include_focus_out,
            add=add,
        )
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


def grid_labeled_commit_combobox(
    parent: tk.Widget,
    row: int,
    column: int,
    label: str,
    textvariable: tk.Variable,
    *,
    values: Any = (),
    on_commit: TkEventCallback,
    on_focus_in: TkEventCallback | None = None,
    include_focus_out: bool = False,
    width: int = 10,
    state: str = "readonly",
    label_textvariable: tk.Variable | None = None,
    label_padx: tuple[int, int] | None = None,
    combo_padx: tuple[int, int] | None = None,
    label_pady: tuple[int, int] = (0, 2),
    combo_pady: tuple[int, int] = (0, 8),
    label_sticky: str = "w",
    combo_sticky: str = "ew",
    label_columnspan: int = 1,
    combo_columnspan: int = 1,
    label_kwargs: dict[str, Any] | None = None,
    combo_kwargs: dict[str, Any] | None = None,
) -> CommitCombobox:
    """Grid a label plus CommitCombobox pair using the compact control-panel layout."""
    left_pad = (8, 0) if column else (0, 0)
    label_padding = left_pad if label_padx is None else label_padx
    combo_padding = left_pad if combo_padx is None else combo_padx
    label_options = dict(label_kwargs or {})
    if label_textvariable is None:
        label_options["text"] = label
    else:
        label_options["textvariable"] = label_textvariable
    label_widget = ttk.Label(parent, **label_options)
    label_widget.grid(
        row=row,
        column=column,
        columnspan=label_columnspan,
        sticky=label_sticky,
        pady=label_pady,
        padx=label_padding,
    )
    combo = CommitCombobox(
        parent,
        textvariable=textvariable,
        state=state,
        width=width,
        values=values,
        on_commit=on_commit,
        on_focus_in=on_focus_in,
        include_focus_out=include_focus_out,
        **(combo_kwargs or {}),
    )
    combo.label_widget = label_widget
    combo.grid(
        row=row + 1,
        column=column,
        columnspan=combo_columnspan,
        sticky=combo_sticky,
        pady=combo_pady,
        padx=combo_padding,
    )
    return combo


def grid_commit_checkbutton(
    parent: tk.Widget,
    row: int,
    column: int,
    text: str,
    variable: tk.Variable,
    *,
    command: TkEventCallback | None = None,
    on_press: TkEventCallback | None = None,
    columnspan: int = 1,
    sticky: str = "w",
    padx: tuple[int, int] | None = None,
    pady: tuple[int, int] = (0, 0),
    width: int | None = None,
    check_kwargs: dict[str, Any] | None = None,
) -> ttk.Checkbutton:
    """Grid a checkbutton with the standard history-capture press binding."""
    left_pad = (8, 0) if column else (0, 0)
    check_padding = left_pad if padx is None else padx
    options = dict(check_kwargs or {})
    if width is not None:
        options["width"] = width
    checkbutton = ttk.Checkbutton(
        parent,
        text=text,
        variable=variable,
        command=command,
        **options,
    )
    checkbutton.grid(
        row=row,
        column=column,
        columnspan=columnspan,
        sticky=sticky,
        padx=check_padding,
        pady=pady,
    )
    if on_press is not None:
        checkbutton.bind("<ButtonPress-1>", on_press, add="+")
    return checkbutton


def grid_command_button(
    parent: tk.Widget,
    row: int,
    column: int,
    text: str,
    *,
    command: Any,
    columnspan: int = 1,
    sticky: str = "ew",
    padx: tuple[int, int] | None = None,
    pady: tuple[int, int] = (0, 0),
    width: int | None = None,
    button_kwargs: dict[str, Any] | None = None,
) -> ttk.Button:
    """Grid a command button using the compact control-panel layout."""
    left_pad = (8, 0) if column else (0, 0)
    button_padding = left_pad if padx is None else padx
    options = dict(button_kwargs or {})
    if width is not None:
        options["width"] = width
    button = ttk.Button(parent, text=text, command=command, **options)
    button.grid(
        row=row,
        column=column,
        columnspan=columnspan,
        sticky=sticky,
        padx=button_padding,
        pady=pady,
    )
    return button
