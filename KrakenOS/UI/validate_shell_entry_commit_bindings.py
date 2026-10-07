"""Guard for bugs/0985: the left panel's entry-commit bindings are the Tk panels' own; the shell-controls service lets go of tkinter.

Phase 7d of the Qt migration. `services/layout_shell_controls.py` loaded tkinter for one import,
`widgets.bind_entry_commit`, used by two helpers that bind Return, the keypad's Enter and
leaving-the-field on a Tk entry. Each helper had exactly one caller, a Tk panel: the operand entries
of the optimization panel, and the atmosphere entries. Each is that panel's own method now. What a
committed atmosphere entry DOES -- the controls follow it, then the plot is owed -- stays the
model's, `_commit_manual_update`.

  S  the service imports nothing from `widgets` and names no `bind_entry_commit`; the mixin no
     longer has the two binders and has the model's commit; each panel class defines its own
     binder; nothing outside the two panels calls either
  L  asked of the interpreter, in a fresh process: importing the service loads no tkinter
  M  the model's commit, no display: the left-mode controls are synced and THEN the plot marked
     owed; with `sync_fields` it is the object controls that are synced; an event argument is
     accepted
  T  a real Tk editor: every operand entry the optimization panel built, and every atmosphere entry
     of the hidden panel and of the settings dialog, binds focus-in, focus-out, Return and the
     keypad's Enter; on a real atmosphere entry of the dialog, focus-in begins a history capture
     and each of the three commit gestures syncs the left-mode controls and then marks the plot
     owed, and the status line says so; on an entry bound by the optimization panel, focus-in
     begins a history capture and each commit gesture marks the plot owed, and nothing else
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "SHELLBINDINGS_RESULT "
SKIP_MARK = "SHELLBINDINGS_SKIP "
ROOT = Path("KrakenOS/UI")
SERVICE = ROOT / "services/layout_shell_controls.py"
BINDERS = {"_bind_deferred_refresh": "panels/main_optimization_panel.py",
           "_bind_deferred_manual_update": "panels/main_atmosphere_panel.py"}
#: Tk's own names for what `bind_entry_commit` binds
COMMIT_SEQUENCES = ("<FocusIn>", "<FocusOut>", "<Key-KP_Enter>", "<Key-Return>")
WATCHED = ("_begin_history_capture", "_sync_left_mode_controls", "_sync_object_controls", "_mark_plot_update_pending")
OWED = "Display settings changed. Click Update."


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _fresh(code: str) -> str:
    """The last line a fresh interpreter prints for ``code``."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=str(Path.cwd()))
    return (done.stdout.strip().splitlines() or ["ERROR " + done.stderr.strip()[-300:]])[-1]


def pure_checks() -> list:
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin as Model

    def s():
        from KrakenOS.UI.panels.main_atmosphere_panel import MainAtmospherePanel
        from KrakenOS.UI.panels.main_optimization_panel import MainOptimizationPanel

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        from_widgets = sorted({node.lineno for node in ast.walk(tree)
                               if (isinstance(node, ast.ImportFrom) and (node.module or "").startswith("KrakenOS.UI.widgets"))
                               or (node.__class__ is ast.Import and any(a.name.startswith("KrakenOS.UI.widgets") for a in node.names))})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id == "bind_entry_commit"})
        on_model = [name for name in BINDERS if name in vars(Model)]
        on_panels = ["_bind_deferred_refresh" in vars(MainOptimizationPanel), "_bind_deferred_manual_update" in vars(MainAtmospherePanel)]
        callers = {}
        for name in BINDERS:
            pattern = re.compile(rf"\.{name}\(")
            callers[name] = {path.relative_to(ROOT).as_posix(): len(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
                             for path in sorted(ROOT.rglob("*.py"))
                             if "archive" not in path.parts and not path.name.startswith("validate_")
                             and pattern.search(path.read_text(encoding="utf-8", errors="replace"))}
        only_its_panel = all(list(found) == [BINDERS[name]] and found[BINDERS[name]] >= 2 for name, found in callers.items())
        return (from_widgets == [] and named == [] and on_model == [] and on_panels == [True, True]
                and "_commit_manual_update" in vars(Model) and only_its_panel,
                f"{SERVICE.name}: imports from widgets at lines {from_widgets or 'none'}, names bind_entry_commit "
                f"{'nowhere' if not named else 'still'}, binders still on the model {on_model or 'none'}; the model has the "
                f"commit: {'_commit_manual_update' in vars(Model)}; each panel defines its binder: {on_panels}; called from "
                f"{callers}")

    def l():
        answer = _fresh("import sys\nimport KrakenOS.UI.services.layout_shell_controls\nprint('tkinter' in sys.modules)\n")
        return answer == "False", f"importing the service in a fresh process loads tkinter: {answer}"

    def m():
        def owner():
            calls: list = []
            return calls, SimpleNamespace(_sync_left_mode_controls=lambda: calls.append("left-mode controls"),
                                          _sync_object_controls=lambda: calls.append("object controls"),
                                          _mark_plot_update_pending=lambda *_a: calls.append("plot owed"))

        plain, first = owner()
        Model._commit_manual_update(first)
        with_event, second = owner()
        Model._commit_manual_update(second, SimpleNamespace(keysym="Return"))
        fields, third = owner()
        Model._commit_manual_update(third, None, sync_fields=True)
        return (plain == ["left-mode controls", "plot owed"] and with_event == plain and fields == ["object controls", "plot owed"],
                f"a commit does {plain}; with an event argument {with_event}; with sync_fields {fields}")

    return _claims((("S", s), ("L", l), ("M", m)))


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.system_controls import ATMOSPHERE_CONTROL_SPECS

    # watched at the CLASS, before the editor exists: a binding keeps the bound method it was given
    calls: list = []
    for name in WATCHED:
        real = getattr(KrakenLayoutEditor, name)
        setattr(KrakenLayoutEditor, name,
                (lambda real, name: lambda self, *a, **k: (calls.append(name), real(self, *a, **k))[1])(real, name))

    editor = KrakenLayoutEditor()

    def pump() -> None:
        for _ in range(4):
            editor.update()

    pump()

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def gestures(entry) -> dict:
        """What each of the four gestures calls on ``entry`` (a key needs the focus; a focus event does not)."""
        heard = {}
        for sequence, needs_focus in (("<FocusIn>", False), ("<Return>", True), ("<KP_Enter>", True), ("<FocusOut>", False)):
            if needs_focus:
                entry.focus_force()
                pump()
            calls.clear()
            entry.event_generate(sequence)
            pump()
            heard[sequence] = list(calls)
        return heard

    def claim_t():
        notes, ok = [], True

        def check(condition, note) -> None:
            nonlocal ok
            ok = ok and bool(condition)
            notes.append(f"{note}: {bool(condition)}")

        bound = lambda entry: tuple(sorted(entry.bind()))
        operand = [w for controls in editor.operand_control_widgets.values() for group in controls.values() for w in group
                   if type(w) is ttk.Entry]
        operand_bound = [entry for entry in operand if bound(entry) == COMMIT_SEQUENCES]
        check(len(operand) >= 8 and len(operand_bound) == len(operand),
              f"{len(operand_bound)} of the {len(operand)} operand entries the optimization panel built bind {list(COMMIT_SEQUENCES)}")

        variables = {str(getattr(editor, attr)) for _label, attr, _default in ATMOSPHERE_CONTROL_SPECS}
        atmosphere = lambda root: [e for e in widgets(root, ttk.Entry) if str(e.cget("textvariable")) in variables]
        hidden = atmosphere(editor.root)
        editor._main_atmosphere_panel().open_settings_dialog()
        pump()
        window = editor._main_atmosphere_panel().__dict__.get("_atmosphere_settings_window")
        in_dialog = atmosphere(window) if window is not None else []
        check(len(hidden) == len(variables) == len(in_dialog) and len(variables) >= 4
              and all(bound(entry) == COMMIT_SEQUENCES for entry in hidden + in_dialog),
              f"the {len(variables)} atmosphere settings have {len(hidden)} entries in the hidden panel and {len(in_dialog)} "
              f"in the settings dialog, all bound the same")

        editor.status_var.set("")
        heard = gestures(in_dialog[0]) if in_dialog else {}
        status = str(editor.status_var.get())
        commit = ["_sync_left_mode_controls", "_mark_plot_update_pending"]
        check(heard == {"<FocusIn>": ["_begin_history_capture"], "<Return>": commit, "<KP_Enter>": commit, "<FocusOut>": commit}
              and status == OWED,
              f"on a real atmosphere entry of the dialog the gestures call {heard}; the status line reads {status!r}")
        editor._main_atmosphere_panel().close_settings_dialog()
        pump()

        host = ttk.Frame(editor.root)
        host.place(x=0, y=0, width=260, height=40)
        entry = ttk.Entry(host)
        entry.pack()
        editor._main_optimization_panel()._bind_deferred_refresh(entry)
        pump()
        heard = gestures(entry)
        host.destroy()
        owed = ["_mark_plot_update_pending"]
        check(heard == {"<FocusIn>": ["_begin_history_capture"], "<Return>": owed, "<KP_Enter>": owed, "<FocusOut>": owed},
              f"on an entry bound by the optimization panel the gestures call {heard}")
        return ok, "; ".join(notes)

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_shell_entry_commit_bindings import tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=300,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["S", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("tk_checks()", "T")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
