"""How much of the Qt shell is built WITHOUT Tk (docs/design_qt_migration.md phase 7f).

The Qt shell used to run a hidden Tk application beside itself: the editor's root with its
panels (414 widgets), and the 3D inspector's withdrawn window with its own (247). Both can be
built without (bugs/0993, bugs/0998), and since bugs/1000 that is how the shell starts: no Tk
root, no Tk widget, no Tk variable in the process.

``KRAKEN_QT_TK_FREE`` asks for something else -- to compare, or to get out of the way of a Tk
call that turns out to be still needed somewhere:

    KRAKEN_QT_TK_FREE=0            the hidden Tk application, as it was before bugs/1000
    KRAKEN_QT_TK_FREE=inspector    only the 3D inspector has no Tk window; the editor keeps its root
    KRAKEN_QT_TK_FREE=all          neither has (the default; also unset, empty or ``1``)
"""
from __future__ import annotations

import os

#: what each level leaves without Tk
LEVELS = {"": (), "inspector": ("inspector",), "all": ("inspector", "editor")}
#: the level when nothing is asked for
DEFAULT_LEVEL = "all"


def tk_free_level() -> str:
    """The level in force: "all" (the default), "inspector", or "" for the hidden Tk application."""
    value = os.environ.get("KRAKEN_QT_TK_FREE", "").strip().lower()
    if value == "":
        return DEFAULT_LEVEL
    if value in ("0", "no", "off", "false", "none", "tk"):
        return ""
    if value in ("1", "yes", "on", "true"):
        return "all"
    if value not in LEVELS:
        raise ValueError(f"KRAKEN_QT_TK_FREE={value!r}: expected 0, inspector or all")
    return value


def tk_free(part: str) -> bool:
    """Whether ``part`` ("inspector" or "editor") is to be built without Tk."""
    return part in LEVELS[tk_free_level()]
