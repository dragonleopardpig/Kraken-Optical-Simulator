"""ScriptedUiHost -- no toolkit at all: a deterministic clock and scripted dialog answers
(docs/design_qt_migration.md).

For display-free guards. Instead of patching module attributes to intercept a dialog, a guard
constructs the code under test with a ScriptedUiHost, reads ``calls`` to see WHICH question was
asked, and scripts the answer:

    ui = ScriptedUiHost(answers={"askyesno": [True, False], "askopenfilename": "/tmp/a.py"})

An answer is a value, a list (consumed in order, then the default), or a callable receiving the
call's arguments. Unscripted questions get the answer a user gets by closing the dialog --
cancel -- which is the safe thing for automation to do.
"""
from __future__ import annotations

import heapq
import itertools
from typing import Any

from KrakenOS.UI.uihost.base import UiHost

_CANCEL: dict[str, Any] = {
    "showinfo": "ok", "showwarning": "ok", "showerror": "ok",
    "askyesno": False, "askokcancel": False, "askyesnocancel": None, "askretrycancel": False,
    "askquestion": "no",
    "askopenfilename": "", "askopenfilenames": (), "asksaveasfilename": "", "askdirectory": "",
    "askstring": None, "askinteger": None, "askfloat": None,
}


class ScriptedUiHost(UiHost):
    def __init__(self, answers: "dict[str, Any] | None" = None, *, clipboard: str = "") -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self._answers = {key: (list(value) if isinstance(value, list) else value)
                         for key, value in dict(answers or {}).items()}
        self._clipboard = str(clipboard)
        self._now_ms = 0
        self._counter = itertools.count()
        self._queue: list[tuple[int, int, str]] = []
        self._callbacks: dict[str, tuple] = {}

    # ---- the script -----------------------------------------------------------------------------
    def _answer(self, name: str, *args, **kwargs):
        self.calls.append((name, args, kwargs))
        if name not in self._answers:
            return _CANCEL.get(name)
        value = self._answers[name]
        if isinstance(value, list):
            return value.pop(0) if value else _CANCEL.get(name)
        if callable(value):
            return value(*args, **kwargs)
        return value

    def asked(self, name: str) -> list[tuple[tuple, dict]]:
        """The ``(args, kwargs)`` of every ``name`` call, in order."""
        return [(args, kwargs) for called, args, kwargs in self.calls if called == name]

    # ---- event loop -------------------------------------------------------------------------------
    def after(self, ms, func=None, *args):
        if func is None:                      # tk: `after(ms)` just waits
            self._now_ms += max(int(ms), 0)
            return None
        seq = next(self._counter)
        handle = f"after#{seq}"
        heapq.heappush(self._queue, (self._now_ms + max(int(ms), 0), seq, handle))
        self._callbacks[handle] = (func, args)
        return handle

    def after_cancel(self, handle) -> None:
        self._callbacks.pop(handle, None)

    def after_idle(self, func, *args):
        return self.after(0, func, *args)

    def update_idletasks(self) -> None:
        self.calls.append(("update_idletasks", (), {}))

    def pending(self) -> int:
        return len(self._callbacks)

    def run_due(self, advance_ms: int = 0) -> int:
        """Advance the clock and run every callback now due -- including ones those callbacks
        schedule for no later than the new time. Returns how many ran."""
        self._now_ms += max(int(advance_ms), 0)
        ran = 0
        while self._queue and self._queue[0][0] <= self._now_ms:
            _due, _seq, handle = heapq.heappop(self._queue)
            entry = self._callbacks.pop(handle, None)
            if entry is None:
                continue                      # cancelled
            func, args = entry
            func(*args)
            ran += 1
        return ran

    def run_all(self, *, max_callbacks: int = 10000) -> int:
        """Run everything, jumping the clock to each deadline in turn."""
        ran = 0
        while self._queue and ran < max_callbacks:
            self._now_ms = max(self._now_ms, self._queue[0][0])
            ran += self.run_due()
        return ran

    # ---- dialogs --------------------------------------------------------------------------------
    def showinfo(self, title=None, message=None, **options):
        return self._answer("showinfo", title, message, **options)

    def showwarning(self, title=None, message=None, **options):
        return self._answer("showwarning", title, message, **options)

    def showerror(self, title=None, message=None, **options):
        return self._answer("showerror", title, message, **options)

    def askyesno(self, title=None, message=None, **options):
        return self._answer("askyesno", title, message, **options)

    def askokcancel(self, title=None, message=None, **options):
        return self._answer("askokcancel", title, message, **options)

    def askyesnocancel(self, title=None, message=None, **options):
        return self._answer("askyesnocancel", title, message, **options)

    def askretrycancel(self, title=None, message=None, **options):
        return self._answer("askretrycancel", title, message, **options)

    def askquestion(self, title=None, message=None, **options):
        return self._answer("askquestion", title, message, **options)

    def askopenfilename(self, **options):
        return self._answer("askopenfilename", **options)

    def askopenfilenames(self, **options):
        return self._answer("askopenfilenames", **options)

    def asksaveasfilename(self, **options):
        return self._answer("asksaveasfilename", **options)

    def askdirectory(self, **options):
        return self._answer("askdirectory", **options)

    def askstring(self, title, prompt, **options):
        return self._answer("askstring", title, prompt, **options)

    def askinteger(self, title, prompt, **options):
        return self._answer("askinteger", title, prompt, **options)

    def askfloat(self, title, prompt, **options):
        return self._answer("askfloat", title, prompt, **options)

    # ---- state variables ----------------------------------------------------------------------
    def string_var(self, value="", **options):
        from KrakenOS.UI.uihost.values import ObservableValue

        return ObservableValue("string", value)

    def int_var(self, value=0, **options):
        from KrakenOS.UI.uihost.values import ObservableValue

        return ObservableValue("int", value)

    def double_var(self, value=0.0, **options):
        from KrakenOS.UI.uihost.values import ObservableValue

        return ObservableValue("double", value)

    def boolean_var(self, value=False, **options):
        from KrakenOS.UI.uihost.values import ObservableValue

        return ObservableValue("boolean", value)

    # ---- clipboard ------------------------------------------------------------------------------
    def clipboard_get(self) -> str:
        return self._clipboard

    def clipboard_set(self, text: str) -> None:
        self._clipboard = str(text)
