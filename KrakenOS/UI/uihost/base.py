"""The UiHost interface (docs/design_qt_migration.md).

Method names and arguments mirror tkinter's own -- ``after``, ``askyesno``,
``askopenfilename``... -- so converting a call site is a rename a reviewer can check at a glance,
and a Tk implementation is pure delegation. A Qt implementation maps the same calls onto
QTimer / QMessageBox / QFileDialog / QInputDialog / QClipboard.
"""
from __future__ import annotations

from typing import Any, Callable


class UiHost:
    """Everything model/controller code may ask of a toolkit. Subclasses implement all of it."""

    # ---- event loop ---------------------------------------------------------------------------
    def after(self, ms: int, func: "Callable[..., Any] | None" = None, *args) -> Any:
        """Run ``func(*args)`` after ``ms`` milliseconds on the UI thread; returns a handle."""
        raise NotImplementedError

    def after_cancel(self, handle: Any) -> None:
        raise NotImplementedError

    def after_idle(self, func: "Callable[..., Any]", *args) -> Any:
        """Run ``func(*args)`` once the UI is idle; returns a handle."""
        raise NotImplementedError

    def update_idletasks(self) -> None:
        """Flush pending redraws / geometry work without processing user input."""
        raise NotImplementedError

    # ---- messages -----------------------------------------------------------------------------
    def showinfo(self, title: "str | None" = None, message: "str | None" = None, **options) -> Any:
        raise NotImplementedError

    def showwarning(self, title: "str | None" = None, message: "str | None" = None, **options) -> Any:
        raise NotImplementedError

    def showerror(self, title: "str | None" = None, message: "str | None" = None, **options) -> Any:
        raise NotImplementedError

    def askyesno(self, title: "str | None" = None, message: "str | None" = None, **options) -> bool:
        raise NotImplementedError

    def askokcancel(self, title: "str | None" = None, message: "str | None" = None, **options) -> bool:
        raise NotImplementedError

    def askyesnocancel(self, title: "str | None" = None, message: "str | None" = None, **options) -> "bool | None":
        raise NotImplementedError

    def askretrycancel(self, title: "str | None" = None, message: "str | None" = None, **options) -> bool:
        raise NotImplementedError

    def askquestion(self, title: "str | None" = None, message: "str | None" = None, **options) -> str:
        raise NotImplementedError

    # ---- files --------------------------------------------------------------------------------
    def askopenfilename(self, **options) -> str:
        raise NotImplementedError

    def askopenfilenames(self, **options) -> "tuple[str, ...]":
        raise NotImplementedError

    def asksaveasfilename(self, **options) -> str:
        raise NotImplementedError

    def askdirectory(self, **options) -> str:
        raise NotImplementedError

    # ---- input --------------------------------------------------------------------------------
    def askstring(self, title: str, prompt: str, **options) -> "str | None":
        raise NotImplementedError

    def askinteger(self, title: str, prompt: str, **options) -> "int | None":
        raise NotImplementedError

    def askfloat(self, title: str, prompt: str, **options) -> "float | None":
        raise NotImplementedError

    # ---- clipboard ----------------------------------------------------------------------------
    def clipboard_get(self) -> str:
        raise NotImplementedError

    def clipboard_set(self, text: str) -> None:
        raise NotImplementedError
