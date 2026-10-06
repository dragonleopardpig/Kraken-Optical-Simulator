"""A right-click menu any shell can show (docs/design_qt_migration.md phase 5c, bugs/0907).

The Open 3D inspector builds its context menus the Tk way: create a `tk.Menu`, call `add_command`,
`add_separator`, `add_checkbutton` and `add_cascade` on it, then post it. Measured, those builders
use only that handful of calls (plus `invoke` and `unpost`), and every entry's action is a plain
Python callable. So the builders do not need rewriting: when a shell other than Tk hosts the
inspector, they are handed a `MenuModel` instead of a `tk.Menu`. It takes the same calls, records
the entries, and the shell renders the record with its own menu widget, whose actions run the SAME
callables. One builder, both shells, the same entries.

Only the calls the builders make are modelled; anything else raises AttributeError rather than
passing silently, so a builder that grows a new Tk-only call is caught.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

KINDS = ("command", "separator", "checkbutton", "radiobutton", "cascade")


@dataclass
class MenuEntry:
    kind: str
    label: str = ""
    command: "Callable | None" = None
    state: str = "normal"
    #: the submenu of a cascade
    submenu: "MenuModel | None" = None
    #: a check or radio entry's variable and its values, as Tk takes them
    variable: Any = None
    onvalue: Any = True
    offvalue: Any = False
    value: Any = None
    accelerator: str = ""
    options: dict = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return str(self.state) != "disabled"

    def checked(self) -> bool:
        """Whether a check or radio entry shows as ticked -- read from its variable, as Tk does."""
        if self.variable is None:
            return False
        try:
            current = self.variable.get()
        except Exception:
            return False
        if self.kind == "radiobutton":
            return current == self.value
        return current == self.onvalue


class MenuModel:
    """Records what a menu builder adds; `run` does what clicking an entry does in Tk."""

    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.entries: list[MenuEntry] = []
        #: set by the shell that shows it: closes the shown menu
        self.on_close: "Callable | None" = None
        self._alive = True

    # ---- the tk.Menu calls the builders make -----------------------------------------------
    def add_command(self, label="", command=None, state="normal", accelerator="", **options):
        self.entries.append(MenuEntry("command", str(label), command, str(state),
                                      accelerator=str(accelerator or ""), options=options))

    def add_separator(self, **options):
        self.entries.append(MenuEntry("separator", options=options))

    def add_checkbutton(self, label="", variable=None, command=None, onvalue=True,
                        offvalue=False, state="normal", accelerator="", **options):
        self.entries.append(MenuEntry("checkbutton", str(label), command, str(state),
                                      variable=variable, onvalue=onvalue, offvalue=offvalue,
                                      accelerator=str(accelerator or ""), options=options))

    def add_radiobutton(self, label="", variable=None, value=None, command=None,
                        state="normal", accelerator="", **options):
        self.entries.append(MenuEntry("radiobutton", str(label), command, str(state),
                                      variable=variable, value=value,
                                      accelerator=str(accelerator or ""), options=options))

    def add_cascade(self, label="", menu=None, state="normal", **options):
        self.entries.append(MenuEntry("cascade", str(label), None, str(state), submenu=menu,
                                      options=options))

    def invoke(self, index):
        return self.run(self.entries[int(index)])

    def index(self, which):
        """`index("end")` as Tk answers it: the last entry's index, None for an empty menu -- how
        the table's builder asks whether a submenu got anything (bugs/0948)."""
        if str(which) == "end":
            return len(self.entries) - 1 if self.entries else None
        return int(which)

    def unpost(self) -> None:
        if self.on_close is not None:
            self.on_close()

    def grab_release(self) -> None:
        pass

    def bind(self, *_args, **_kwargs) -> None:
        pass

    def winfo_exists(self) -> bool:
        return self._alive

    def destroy(self) -> None:
        self._alive = False

    # ---- for the shell -----------------------------------------------------------------------
    def run(self, entry: MenuEntry):
        """What a click on `entry` does in Tk: a check entry toggles its variable and a radio
        entry sets its own, THEN the command runs."""
        if not entry.enabled or entry.kind in ("separator", "cascade"):
            return None
        if entry.kind == "checkbutton" and entry.variable is not None:
            entry.variable.set(entry.offvalue if entry.checked() else entry.onvalue)
        elif entry.kind == "radiobutton" and entry.variable is not None:
            entry.variable.set(entry.value)
        if entry.command is not None:
            return entry.command()
        return None

    def outline(self) -> list:
        """The menu as nested (kind, label, enabled[, children]) tuples -- what a guard compares."""
        rows = []
        for entry in self.entries:
            if entry.kind == "separator":
                rows.append(("separator",))
            elif entry.kind == "cascade":
                children = entry.submenu.outline() if isinstance(entry.submenu, MenuModel) else []
                rows.append(("cascade", entry.label, entry.enabled, children))
            else:
                rows.append((entry.kind, entry.label, entry.enabled))
        return rows


def new_context_menu(owner, master):
    """The menu a context-menu builder should fill: a real `tk.Menu` on `master`, exactly as
    before, unless the inspector (`owner`, or the service standing in for it) is hosted by a
    shell that shows its own menus -- then a `MenuModel`. A submenu of a model is a model."""
    if isinstance(master, MenuModel) or getattr(owner, "show_context_menu", None) is not None:
        return MenuModel(master if isinstance(master, MenuModel) else None)
    import tkinter as tk

    return tk.Menu(master, tearoff=False)


def fill_tk_menu(menu, model) -> list:
    """Replace a real `tk.Menu`'s entries by `model`'s, cascades and all (bugs/0972: the menu bar's
    Layouts / Examples menus are model data now). Returns the submenus it made -- the caller keeps
    them, as the menu bar always kept its category menus."""
    import tkinter as tk

    menu.delete(0, "end")
    made = []
    for entry in model.entries:
        if entry.kind == "separator":
            menu.add_separator()
        elif entry.kind == "cascade":
            submenu = tk.Menu(menu, tearoff=0)
            made.append(submenu)
            if entry.submenu is not None:
                made.extend(fill_tk_menu(submenu, entry.submenu))
            menu.add_cascade(label=entry.label, menu=submenu, state=entry.state)
        elif entry.kind == "checkbutton":
            menu.add_checkbutton(label=entry.label, variable=entry.variable, command=entry.command,
                                 onvalue=entry.onvalue, offvalue=entry.offvalue, state=entry.state)
        elif entry.kind == "radiobutton":
            menu.add_radiobutton(label=entry.label, variable=entry.variable, value=entry.value,
                                 command=entry.command, state=entry.state)
        else:
            menu.add_command(label=entry.label, command=entry.command, state=entry.state)
    return made


def tk_menu_outline(menu) -> list:
    """The same outline, read back from a REAL posted `tk.Menu` -- so a guard can compare what
    the Tk shell showed with what a shell was handed."""
    rows = []
    end = menu.index("end")
    if end is None:
        return rows
    for index in range(int(end) + 1):
        kind = str(menu.type(index))
        if kind == "tearoff":
            continue
        if kind == "separator":
            rows.append(("separator",))
            continue
        label = str(menu.entrycget(index, "label"))
        enabled = str(menu.entrycget(index, "state")) != "disabled"
        if kind == "cascade":
            submenu = menu.nametowidget(str(menu.entrycget(index, "menu")))
            rows.append(("cascade", label, enabled, tk_menu_outline(submenu)))
        else:
            rows.append((kind, label, enabled))
    return rows
