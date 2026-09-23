"""QtUiHost -- the Qt implementation of the UI host (docs/design_qt_migration.md phase 2).

Same interface as TkUiHost, so model/controller code reached through ``host_of`` does not change:
QTimer for scheduling, QMessageBox / QFileDialog / QInputDialog for dialogs, the Qt clipboard, and
toolkit-free ``ObservableValue`` state variables (a Qt view binds to them through ``trace_add``).

PySide6 is imported lazily inside the methods: importing this module must not require Qt, so a Tk
run and the display-free guards never pull it in.
"""
from __future__ import annotations

import itertools
from typing import Any

from KrakenOS.UI.uihost.base import UiHost
from KrakenOS.UI.uihost.values import ObservableValue


def qt_filter(filetypes) -> str:
    """tkinter ``[("Python layout", "*.py"), ...]`` -> Qt ``"Python layout (*.py);;..."``.

    A pattern may be one glob, a space-separated run of them (``"*.step *.stp"``, which Qt reads
    the same way tkinter does), or a tuple of globs. tkinter also accepts a bare extension
    (``".py"``); Qt does not, so those grow the star they are missing.
    """
    parts = []
    for entry in filetypes or ():
        try:
            label, patterns = entry
        except (TypeError, ValueError):
            continue
        if isinstance(patterns, str):
            patterns = (patterns,)
        globs = " ".join(_glob(str(p)) for p in patterns if str(p))
        parts.append(f"{label} ({globs})" if globs else str(label))
    return ";;".join(parts)


def _glob(pattern: str) -> str:
    return " ".join(
        word if "*" in word else ("*" + word if word.startswith(".") else "*." + word)
        for word in pattern.split()
    )


class QtUiHost(UiHost):
    """``parent`` is the widget dialogs centre on and timers belong to -- the main window, or
    ``None`` before one exists."""

    def __init__(self, parent=None) -> None:
        self._parent = parent
        self._timers: dict[str, Any] = {}
        self._counter = itertools.count()

    def set_parent(self, parent) -> None:
        """Adopt the window dialogs should centre on, once it exists -- the model is built before
        the window that displays it, so the host starts parentless."""
        self._parent = parent

    @property
    def parent_widget(self):
        return self._parent

    # ---- event loop -------------------------------------------------------------------------------
    def after(self, ms, func=None, *args):
        """Like ``tk.Misc.after``: with a callback, schedule it and return a cancellable handle;
        without one, block for ``ms`` -- which is what Tk does, so a caller that means to sleep
        sleeps on either toolkit."""
        from PySide6.QtCore import QThread, QTimer

        if func is None:
            QThread.msleep(max(int(ms), 0))
            return None

        handle = f"after#{next(self._counter)}"
        timer = QTimer(self._parent)
        timer.setSingleShot(True)

        def fire():
            # Hold the timer in a local while the callback runs: dropping the last reference to a
            # QObject from inside its own signal is what deletes it mid-emission.
            fired = self._timers.pop(handle, None)
            if fired is not None:
                fired.deleteLater()
            func(*args)

        timer.timeout.connect(fire)
        self._timers[handle] = timer
        timer.start(max(int(ms), 0))
        return handle

    def after_cancel(self, handle) -> None:
        timer = self._timers.pop(handle, None)
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    def after_idle(self, func, *args):
        return self.after(0, func, *args)

    def update_idletasks(self) -> None:
        """Flush queued redraws and geometry, run nothing else -- Tk's update_idletasks runs idle
        work only, and code calls it mid-operation counting on that.

        Delivering the posted-event queue repaints the widgets that asked to be repainted while
        leaving BOTH sources of re-entrancy alone: scheduled `after` callbacks (they are real
        QTimers, dispatched by the event loop, not posted events -- `processEvents` would run
        them, measured) and user input (it is read from the window system, which this never
        asks).
        """
        from PySide6.QtCore import QCoreApplication, QEvent

        app = QCoreApplication.instance()
        if app is not None:
            QCoreApplication.sendPostedEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    # ---- messages ---------------------------------------------------------------------------------
    @staticmethod
    def _box():
        from PySide6.QtWidgets import QMessageBox

        return QMessageBox

    def _parent_for(self, options):
        from PySide6.QtWidgets import QWidget

        parent = options.get("parent")
        return parent if isinstance(parent, QWidget) else self._parent

    def showinfo(self, title=None, message=None, **options):
        self._box().information(self._parent_for(options), str(title or ""), str(message or ""))
        return "ok"

    def showwarning(self, title=None, message=None, **options):
        self._box().warning(self._parent_for(options), str(title or ""), str(message or ""))
        return "ok"

    def showerror(self, title=None, message=None, **options):
        self._box().critical(self._parent_for(options), str(title or ""), str(message or ""))
        return "ok"

    def askyesno(self, title=None, message=None, **options):
        box = self._box()
        answer = box.question(self._parent_for(options), str(title or ""), str(message or ""),
                              box.StandardButton.Yes | box.StandardButton.No)
        return answer == box.StandardButton.Yes

    def askokcancel(self, title=None, message=None, **options):
        box = self._box()
        answer = box.question(self._parent_for(options), str(title or ""), str(message or ""),
                              box.StandardButton.Ok | box.StandardButton.Cancel)
        return answer == box.StandardButton.Ok

    def askyesnocancel(self, title=None, message=None, **options):
        box = self._box()
        answer = box.question(self._parent_for(options), str(title or ""), str(message or ""),
                              box.StandardButton.Yes | box.StandardButton.No | box.StandardButton.Cancel)
        if answer == box.StandardButton.Cancel:
            return None
        return answer == box.StandardButton.Yes

    def askretrycancel(self, title=None, message=None, **options):
        box = self._box()
        answer = box.warning(self._parent_for(options), str(title or ""), str(message or ""),
                             box.StandardButton.Retry | box.StandardButton.Cancel)
        return answer == box.StandardButton.Retry

    def askquestion(self, title=None, message=None, **options):
        return "yes" if self.askyesno(title, message, **options) else "no"

    # ---- files ------------------------------------------------------------------------------------
    @staticmethod
    def _dialog():
        from PySide6.QtWidgets import QFileDialog

        return QFileDialog

    def askopenfilename(self, **options):
        path, _selected = self._dialog().getOpenFileName(
            self._parent_for(options), str(options.get("title") or ""),
            str(options.get("initialdir") or ""), qt_filter(options.get("filetypes")))
        return path or ""

    def askopenfilenames(self, **options):
        paths, _selected = self._dialog().getOpenFileNames(
            self._parent_for(options), str(options.get("title") or ""),
            str(options.get("initialdir") or ""), qt_filter(options.get("filetypes")))
        return tuple(paths or ())

    def asksaveasfilename(self, **options):
        path, _selected = self._dialog().getSaveFileName(
            self._parent_for(options), str(options.get("title") or ""),
            str(options.get("initialdir") or ""), qt_filter(options.get("filetypes")))
        return path or ""

    def askdirectory(self, **options):
        return self._dialog().getExistingDirectory(
            self._parent_for(options), str(options.get("title") or ""),
            str(options.get("initialdir") or "")) or ""

    # ---- input ------------------------------------------------------------------------------------
    @staticmethod
    def _input():
        from PySide6.QtWidgets import QInputDialog

        return QInputDialog

    def askstring(self, title, prompt, **options):
        text, ok = self._input().getText(self._parent_for(options), str(title), str(prompt),
                                         text=str(options.get("initialvalue") or ""))
        return text if ok else None

    def askinteger(self, title, prompt, **options):
        value, ok = self._input().getInt(self._parent_for(options), str(title), str(prompt),
                                         int(options.get("initialvalue") or 0),
                                         int(options.get("minvalue", -2**31)),
                                         int(options.get("maxvalue", 2**31 - 1)))
        return value if ok else None

    def askfloat(self, title, prompt, **options):
        value, ok = self._input().getDouble(self._parent_for(options), str(title), str(prompt),
                                            float(options.get("initialvalue") or 0.0),
                                            float(options.get("minvalue", -1e300)),
                                            float(options.get("maxvalue", 1e300)), decimals=6)
        return value if ok else None

    # ---- clipboard --------------------------------------------------------------------------------
    @staticmethod
    def _clipboard():
        from PySide6.QtGui import QGuiApplication

        return QGuiApplication.clipboard()

    def clipboard_get(self) -> str:
        clipboard = self._clipboard()
        return "" if clipboard is None else str(clipboard.text())

    def clipboard_set(self, text: str) -> None:
        clipboard = self._clipboard()
        if clipboard is not None:
            clipboard.setText(str(text))

    # ---- state variables --------------------------------------------------------------------------
    # A Qt view binds to these through trace_add, the way a Tk view binds textvariable=.
    def string_var(self, value="", **options):
        return ObservableValue("string", value)

    def int_var(self, value=0, **options):
        return ObservableValue("int", value)

    def double_var(self, value=0.0, **options):
        return ObservableValue("double", value)

    def boolean_var(self, value=False, **options):
        return ObservableValue("boolean", value)
