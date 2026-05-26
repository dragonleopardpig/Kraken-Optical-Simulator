"""Reusable Tk controls with standard commit bindings."""

from __future__ import annotations

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
