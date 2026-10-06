"""Start KrakenOS in the interface the user prefers (bugs/0971).

    python -m KrakenOS.UI [layout.py] [--shell tk|qt]

The user, 2026-10-06: "I would like to have both TK and QT available, let user to choose his usage
preference." So there are two interfaces over one model, and which one starts is decided, in order,
by:

1. the command line -- ``--shell qt``, ``--shell=tk``, ``--qt``, ``--tk`` (this run only);
2. the environment -- ``KRAKEN_UI_SHELL=qt`` (this run only);
3. the saved preference (`user_preferences`, key ``shell``) -- set from either interface with
   **Interface Preference...**, or by the question below;
4. nothing decides: the user is ASKED, once, and the answer is remembered unless they untick it.

An interface that cannot run here (Qt without PySide6) is not offered, and a request for it falls
back to the other with a line saying why. ``python -m KrakenOS.UI.layout_editor`` and
``python -m KrakenOS.UI.qt.app`` still start their own interface directly.

Everything but `ask_which_shell` (a twelve-widget Tk window, Tk being the toolkit every install
has) is toolkit-free, so the decision is tested without starting anything.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from typing import Callable, Optional

from KrakenOS.UI import user_preferences

PREFERENCE_KEY = "shell"
ENVIRONMENT_KEY = "KRAKEN_UI_SHELL"
#: shell -> (name shown to the user, one line about it)
SHELLS = {
    "qt": ("Qt interface", "The newer interface: a ribbon, panels that fold away, one large 3D scene."),
    "tk": ("Tk interface", "The classic interface: a menu bar, the 2D layout, a separate 3D window."),
}
#: asked first when nothing has decided
ASK_ORDER = ("qt", "tk")


class ShellRefused(Exception):
    """The request names no interface this program has."""


def available_shells() -> dict:
    """shell -> "" when it can run here, else why not."""
    out = {}
    for shell, module in (("qt", "PySide6"), ("tk", "tkinter")):
        try:
            found = importlib.util.find_spec(module) is not None
        except Exception:
            found = False
        out[shell] = "" if found else f"{module} is not installed"
    return out


def split_arguments(argv: list) -> tuple:
    """(the shell the command line asks for or "", the arguments without that request)."""
    asked, rest = "", []
    iterator = iter(list(argv))
    for argument in iterator:
        if argument in ("--qt", "--tk"):
            asked = argument[2:]
        elif argument == "--shell":
            asked = str(next(iterator, "")).strip().lower()
            if not asked:
                raise ShellRefused("--shell needs a value: tk or qt")
        elif argument.startswith("--shell="):
            asked = argument.split("=", 1)[1].strip().lower()
        else:
            rest.append(argument)
            continue
        if asked not in SHELLS:
            raise ShellRefused(f"unknown interface {asked!r}: choose one of {', '.join(sorted(SHELLS))}")
    return asked, rest


def resolve_shell(argv: list, environ: Optional[dict] = None, saved: Optional[str] = None) -> tuple:
    """(shell or "", where the decision came from, the remaining arguments).

    "" means nothing decided -- the caller asks. An unknown value on the command line is refused;
    an unknown value in the environment or the file is ignored (a stale file must not stop a start).
    """
    environ = os.environ if environ is None else environ
    asked, rest = split_arguments(argv)
    if asked:
        return asked, "the command line", rest
    from_environment = str(environ.get(ENVIRONMENT_KEY, "") or "").strip().lower()
    if from_environment in SHELLS:
        return from_environment, f"{ENVIRONMENT_KEY}", rest
    if saved is None:
        saved = user_preferences.get(PREFERENCE_KEY, "")
    saved = str(saved or "").strip().lower()
    if saved in SHELLS:
        return saved, "your saved preference", rest
    return "", "", rest


def runnable(shell: str, available: Optional[dict] = None) -> tuple:
    """(the shell that will actually start, a note when that is not the one asked for)."""
    available = available_shells() if available is None else available
    if not available.get(shell, "unknown interface"):
        return shell, ""
    other = next((name for name in SHELLS if name != shell and not available.get(name, "x")), "")
    if not other:
        raise ShellRefused(f"no interface can run here: " + "; ".join(f"{k}: {v}" for k, v in available.items() if v))
    return other, (f"the {SHELLS[shell][0]} cannot run here ({available[shell]}); "
                   f"starting the {SHELLS[other][0]} instead")


def first_run_choice(ask: Callable[[list, str], tuple], available: Optional[dict] = None) -> str:
    """Nothing has decided which interface starts: ask, and remember the answer when told to.
    Returns the shell, or "" when the user closed the question (nothing starts)."""
    available = available_shells() if available is None else available
    offered = [shell for shell in ASK_ORDER if not available.get(shell, "x")]
    if not offered:
        raise ShellRefused("no interface can run here: " + "; ".join(f"{k}: {v}" for k, v in available.items() if v))
    if len(offered) == 1:
        return offered[0]                       # nothing to choose between: do not ask
    shell, remember = ask(offered, offered[0])
    if shell not in offered:
        return ""
    if remember:
        problem = user_preferences.set_value(PREFERENCE_KEY, shell)
        if problem:
            print(f"[KrakenOS] {problem}")
    return shell


def ask_which_shell(offered: list, default: str) -> tuple:
    """The first-run question, as a small Tk window. Returns (shell or "", remember)."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("KrakenOS -- choose an interface")
    root.resizable(False, False)
    answer = {"shell": "", "remember": True}
    choice = tk.StringVar(master=root, value=default)
    remember = tk.BooleanVar(master=root, value=True)
    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    ttk.Label(frame, text="KrakenOS has two interfaces over the same program.\nWhich one should open?",
              justify="left").grid(row=0, column=0, columnspan=2, sticky="w")
    for row, shell in enumerate(offered, start=1):
        name, about = SHELLS[shell]
        ttk.Radiobutton(frame, text=name, value=shell, variable=choice).grid(row=2 * row - 1, column=0, columnspan=2,
                                                                             sticky="w", pady=(12, 0))
        ttk.Label(frame, text=about, foreground="#475569", wraplength=420, justify="left").grid(
            row=2 * row, column=0, columnspan=2, sticky="w", padx=(24, 0))
    last = 2 * len(offered) + 1
    ttk.Checkbutton(frame, text="Remember my choice", variable=remember).grid(row=last, column=0, columnspan=2,
                                                                             sticky="w", pady=(14, 0))
    ttk.Label(frame, text="Change it any time: Interface Preference... in either interface, or --shell tk|qt.",
              foreground="#475569", wraplength=440, justify="left").grid(row=last + 1, column=0, columnspan=2, sticky="w")

    def accept() -> None:
        answer["shell"], answer["remember"] = choice.get(), bool(remember.get())
        root.destroy()

    buttons = ttk.Frame(frame)
    buttons.grid(row=last + 2, column=0, columnspan=2, sticky="e", pady=(14, 0))
    ttk.Button(buttons, text="Quit", command=root.destroy).pack(side="right")
    opener = ttk.Button(buttons, text="Open", command=accept)
    opener.pack(side="right", padx=(0, 8))
    root.bind("<Return>", lambda _event: accept())
    root.bind("<Escape>", lambda _event: root.destroy())
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    #: for a guard to drive
    root.kraken_choice, root.kraken_remember, root.kraken_open = choice, remember, opener
    ask_which_shell.last_window = root
    root.mainloop()
    return answer["shell"], answer["remember"]


def start(shell: str, arguments: list) -> int:
    """Run one interface until it closes. ``arguments`` is the command line less the shell request."""
    scene = next((a for a in arguments[1:] if a.endswith(".py") and os.path.exists(a)), None)
    if shell == "qt":
        from KrakenOS.UI.qt.app import run

        return int(run(arguments) or 0)
    from KrakenOS.UI.layout_editor import main as tk_main

    tk_main(scene=scene)
    return 0


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    try:
        shell, source, rest = resolve_shell(argv)
        if not shell:
            shell = first_run_choice(ask_which_shell)
            source = "your answer"
            if not shell:
                return 0
        shell, note = runnable(shell)
    except ShellRefused as exc:
        print(f"[KrakenOS] {exc}", file=sys.stderr)
        return 2
    if note:
        print(f"[KrakenOS] {note}.")
    print(f"[KrakenOS] opening the {SHELLS[shell][0]} ({source}). Change it with --shell tk|qt or "
          f"Interface Preference... in the app.")
    if os.environ.get("KRAKEN_LAUNCHER_DRY_RUN"):         # say what would start, and stop (a guard reads it)
        print(f"[KrakenOS] dry run: shell={shell} arguments={rest[1:]}")
        return 0
    return start(shell, rest)


if __name__ == "__main__":
    raise SystemExit(main())
