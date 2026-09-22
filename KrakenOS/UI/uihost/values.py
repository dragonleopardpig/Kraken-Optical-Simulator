"""ObservableValue -- a toolkit-free stand-in for a tkinter variable (docs/design_qt_migration.md
step 1c).

Model code calls only ``get`` and ``set`` on its state variables (1174 sets and 191 gets,
measured 2026-09-22); views bind to them through ``trace_add``. This reproduces exactly that
surface, with tkinter's coercion on ``get`` and its callback signature ``(name, index, mode)``,
so a service cannot tell whether it is holding a ``tk.StringVar`` or one of these.
"""
from __future__ import annotations

import itertools
from typing import Any, Callable

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}
_names = itertools.count()


def _to_bool(value) -> bool:
    if isinstance(value, str):
        text = value.strip().lower()
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise ValueError(f"expected boolean value but got {value!r}")
    return bool(value)


_COERCE: dict[str, Callable[[Any], Any]] = {
    "string": lambda v: v if isinstance(v, str) else str(v),
    "int": lambda v: int(float(v)) if isinstance(v, str) and "." in v else int(v),
    "double": float,
    "boolean": _to_bool,
}


class ObservableValue:
    """A named value with tkinter-variable semantics: ``get`` / ``set`` / ``trace_add`` /
    ``trace_remove`` / ``trace_info``. ``kind`` is one of string, int, double, boolean."""

    def __init__(self, kind: str = "string", value: Any = None, name: "str | None" = None) -> None:
        if kind not in _COERCE:
            raise ValueError(f"unknown ObservableValue kind {kind!r}")
        self.kind = kind
        self._name = name or f"PY_VAR{next(_names)}"
        self._value = value if value is not None else {"string": "", "int": 0, "double": 0.0, "boolean": False}[kind]
        self._traces: list[tuple[str, str, Callable]] = []
        self._trace_ids = itertools.count()

    def __str__(self) -> str:
        return self._name

    def get(self):
        return _COERCE[self.kind](self._value)

    def set(self, value) -> None:
        self._value = value
        for modes, _handle, callback in list(self._traces):
            if "write" in modes:
                callback(self._name, "", "write")

    def trace_add(self, mode, callback) -> str:
        modes = (mode,) if isinstance(mode, str) else tuple(mode)
        handle = f"trace{next(self._trace_ids)}"
        self._traces.append((modes, handle, callback))
        return handle

    def trace_remove(self, mode, cbname) -> None:
        self._traces = [entry for entry in self._traces if entry[1] != cbname]

    def trace_info(self) -> list:
        return [(modes, handle) for modes, handle, _cb in self._traces]
