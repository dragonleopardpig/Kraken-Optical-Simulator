"""TkUiHost -- today's behaviour, by delegation (docs/design_qt_migration.md).

Scheduling goes to the wrapped widget (so a timer belongs to the same widget it always did, and
dies with it); dialogs go to the tkinter modules, resolved at CALL time so anything that patches
``tkinter.messagebox`` keeps working.
"""
from __future__ import annotations

from typing import Any

from KrakenOS.UI.uihost.base import UiHost


class TkUiHost(UiHost):
    def __init__(self, root) -> None:
        self._root = root

    @property
    def root(self):
        return self._root

    # ---- event loop ---------------------------------------------------------------------------
    def after(self, ms, func=None, *args) -> Any:
        return self._root.after(ms, func, *args)

    def after_cancel(self, handle) -> None:
        self._root.after_cancel(handle)

    def after_idle(self, func, *args) -> Any:
        return self._root.after_idle(func, *args)

    def update_idletasks(self) -> None:
        self._root.update_idletasks()

    # ---- messages -----------------------------------------------------------------------------
    @staticmethod
    def _messagebox():
        from tkinter import messagebox

        return messagebox

    def showinfo(self, title=None, message=None, **options):
        return self._messagebox().showinfo(title, message, **options)

    def showwarning(self, title=None, message=None, **options):
        return self._messagebox().showwarning(title, message, **options)

    def showerror(self, title=None, message=None, **options):
        return self._messagebox().showerror(title, message, **options)

    def askyesno(self, title=None, message=None, **options):
        return self._messagebox().askyesno(title, message, **options)

    def askokcancel(self, title=None, message=None, **options):
        return self._messagebox().askokcancel(title, message, **options)

    def askyesnocancel(self, title=None, message=None, **options):
        return self._messagebox().askyesnocancel(title, message, **options)

    def askretrycancel(self, title=None, message=None, **options):
        return self._messagebox().askretrycancel(title, message, **options)

    def askquestion(self, title=None, message=None, **options):
        return self._messagebox().askquestion(title, message, **options)

    # ---- files --------------------------------------------------------------------------------
    @staticmethod
    def _filedialog():
        from tkinter import filedialog

        return filedialog

    def askopenfilename(self, **options):
        return self._filedialog().askopenfilename(**options)

    def askopenfilenames(self, **options):
        return self._filedialog().askopenfilenames(**options)

    def asksaveasfilename(self, **options):
        return self._filedialog().asksaveasfilename(**options)

    def askdirectory(self, **options):
        return self._filedialog().askdirectory(**options)

    # ---- input --------------------------------------------------------------------------------
    @staticmethod
    def _simpledialog():
        from tkinter import simpledialog

        return simpledialog

    def askstring(self, title, prompt, **options):
        return self._simpledialog().askstring(title, prompt, **options)

    def askinteger(self, title, prompt, **options):
        return self._simpledialog().askinteger(title, prompt, **options)

    def askfloat(self, title, prompt, **options):
        return self._simpledialog().askfloat(title, prompt, **options)

    # ---- state variables ----------------------------------------------------------------------
    # `master` defaults to None -- tkinter's default root -- exactly as the `tk.StringVar(value=...)`
    # calls these replace; every widget of the app shares one interpreter either way.
    def string_var(self, value="", **options):
        import tkinter as tk

        return tk.StringVar(master=options.get("master"), value=value)

    def int_var(self, value=0, **options):
        import tkinter as tk

        return tk.IntVar(master=options.get("master"), value=value)

    def double_var(self, value=0.0, **options):
        import tkinter as tk

        return tk.DoubleVar(master=options.get("master"), value=value)

    def boolean_var(self, value=False, **options):
        import tkinter as tk

        return tk.BooleanVar(master=options.get("master"), value=value)

    # ---- clipboard ----------------------------------------------------------------------------
    def clipboard_get(self) -> str:
        return str(self._root.clipboard_get())

    def clipboard_set(self, text: str) -> None:
        self._root.clipboard_clear()
        self._root.clipboard_append(str(text))
