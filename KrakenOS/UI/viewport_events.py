"""A 3D-viewport input event any shell can produce (docs/design_qt_migration.md phase 5a).

The Open 3D inspector's mouse and key handlers were written against Tk's event object, but they
read only a handful of its fields: the position, the modifier bitmask, the key symbol, and the
screen position a context menu is placed at. `ViewportEvent` is exactly those fields, so a Qt
viewport can drive the SAME handlers with no Tk event in sight (bugs/0905). The modifier bits keep
Tk's X11 values, because the handlers already test them (`_event_control_pressed` masks 0x0004).
"""
from __future__ import annotations

from dataclasses import dataclass

#: X11 modifier bits, as Tk reports them in `event.state`
SHIFT = 0x0001
CONTROL = 0x0004
#: Alt is Mod1 on most X11 setups; some report it as Mod5, which the handlers also accept
ALT = 0x0008

#: every handler a viewport can drive, by name
KINDS = ("left_press", "left_motion", "left_release", "double_left", "middle_press",
         "middle_motion", "middle_release", "right_press", "right_motion", "right_release",
         "hover", "alt_press", "alt_release", "focus_out")


@dataclass(frozen=True)
class ViewportEvent:
    """The fields the inspector's handlers read from an input event -- and nothing else."""

    x: int = 0
    y: int = 0
    #: Tk-convention modifier bitmask: SHIFT | CONTROL | ALT
    state: int = 0
    keysym: str = ""
    #: screen coordinates, for placing a context menu; None when the shell has none
    x_root: "int | None" = None
    y_root: "int | None" = None

    @classmethod
    def at(cls, x: int, y: int, *, shift: bool = False, control: bool = False,
           alt: bool = False, keysym: str = "", x_root=None, y_root=None) -> "ViewportEvent":
        state = (SHIFT if shift else 0) | (CONTROL if control else 0) | (ALT if alt else 0)
        return cls(int(x), int(y), state, keysym, x_root, y_root)


def button_handler(button: int, state: int, phase: str) -> str:
    """Which handler a mouse button event goes to -- the rule the Tk bindings encode.

    `phase` is "press", "motion" or "release". Shift + left drags like the middle button (a
    touchpad-friendly pan); Control + left is still the left handler, which reads Control
    itself. A shell asks this rather than re-deciding it.
    """
    if button == 1 and state & SHIFT:
        return f"middle_{phase}"
    name = {1: "left", 2: "middle", 3: "right"}.get(int(button))
    if name is None:
        raise ValueError(f"no handler for mouse button {button}")
    return f"{name}_{phase}"
