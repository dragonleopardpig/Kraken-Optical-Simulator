"""How much of the Qt shell is built WITHOUT Tk (docs/design_qt_migration.md phase 7f).

The Qt shell has always run a hidden Tk application beside itself: the editor's root with its
panels, and the 3D inspector's withdrawn window with its own. Both can be built without now
(bugs/0993, bugs/0998), but neither is the default yet -- the default changes when the whole
shell has been measured without them. Until then ``KRAKEN_QT_TK_FREE`` asks for it:

    KRAKEN_QT_TK_FREE=inspector    the 3D inspector has no Tk window; the editor keeps its root
    KRAKEN_QT_TK_FREE=all          neither has: the editor is built with no Tk root (bugs/0993)

Unset, empty or ``0``: as it has always been.
"""
from __future__ import annotations

import os

#: what each level leaves without Tk
LEVELS = {"inspector": ("inspector",), "all": ("inspector", "editor")}


def tk_free_level() -> str:
    """The level asked for: "", "inspector" or "all"."""
    value = os.environ.get("KRAKEN_QT_TK_FREE", "").strip().lower()
    if value in ("", "0", "no", "off", "false"):
        return ""
    if value in ("1", "yes", "on", "true"):
        return "all"
    if value not in LEVELS:
        raise ValueError(f"KRAKEN_QT_TK_FREE={value!r}: expected one of {sorted(LEVELS)}")
    return value


def tk_free(part: str) -> bool:
    """Whether ``part`` ("inspector" or "editor") is to be built without Tk."""
    return part in LEVELS.get(tk_free_level(), ())
