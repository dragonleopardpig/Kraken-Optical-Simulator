"""Guard for bugs/0964: the Qt shell has its 2D plot -- with the Tk plot toolbar's controls.

`qt/plot2d.LayoutPlot2D` existed since bugs/0893, but only its guard built it: the running Qt shell
had no 2D layout plot, and every analysis plot (MTF, spot, ...) was drawn into the hidden Tk window.
The Tk plot toolbar's controls -- the layout pane, Plane, Show PP / EP / XP, Show labels, Rays,
Physical Distance, Trace Now -- had no Qt route at all.

  S  (static) the Tk plot toolbar still binds each variable of `plot2d_toolbar.TK_BINDINGS` to its
     commit, and the Qt row offers a control for each -- the two shells offer the same switches
  P  in a real Qt shell on the two-arm doublets example (in git), `build_scene` builds the 2D Plot:
     a panel on the right, its own tab on the right edge, tabbed BEHIND the System panel (the
     start-up layout unchanged); the editor draws into ITS figure and canvas, and the layout is
     drawn there
  C  each control drives the model through the Tk commit: a check writes its variable and runs the
     commit once; a model write repaints the check; the Rays and Plane choices write their
     variable and run their commit; Show PP / EP / XP really removes the markers from the plot
     and puts them back; Physical Distance adds its annotations and clears them
  U  an analysis Update brings the 2D Plot to the front -- from behind the System tab, and when
     the panel was closed by its own tab
  N  Trace Now is a shell action (ribbon, palette) and on the plot's toolbar: it runs the model's
     deferred-trace command
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "PLOT2D_RESULT "
SKIP_MARK = "PLOT2D_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
TK_TOOLBAR = Path("KrakenOS/UI/panels/main_window.py")


def static_checks() -> list:
    from KrakenOS.UI import open3d_toolbar as catalogue
    from KrakenOS.UI.plot2d_toolbar import PLOT_2D, TK_BINDINGS

    source = TK_TOOLBAR.read_text(encoding="utf-8")
    unbound = []
    for variable, commit in TK_BINDINGS.items():
        # the Tk control: `variable=` / `textvariable=self.<var>` with its `command=` / `on_commit=`
        # within the same call
        pattern = rf"variable=self\.{variable},(?:(?!\)\n).)*?(?:command|on_commit)=self\.{commit}\b"
        if not re.search(pattern, source, re.S):
            unbound.append(f"{variable} -> {commit}")
    qt_pairs = {}
    for item in catalogue.walk(PLOT_2D.left + PLOT_2D.right):
        variable = getattr(item, "var", "").partition(".")[2]
        commit = getattr(item, "target", "").partition(".")[2]
        if variable:
            qt_pairs[variable] = commit
    return [["S", not unbound and qt_pairs == TK_BINDINGS,
             f"Tk plot toolbar bindings missing: {unbound}; the Qt row binds the same {len(qt_pairs)} "
             f"variable -> commit pairs as Tk: {qt_pairs == TK_BINDINGS}"]]


def qt_runtime_checks() -> dict:
    import time

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QToolButton

    from KrakenOS.UI.plot2d_toolbar import PLOT_2D
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.ribbon import ribbon_actions

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_scene()
    window.load_layout_path(SCENE)
    editor = window.editor
    rows = []

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.0)
    plot = window.plot2d
    if plot is None:
        return {"rows": [["P", False, "build_scene built no 2D plot"]]}
    rails = window.dock_manager.rails
    dock = window.dock_manager["plot2d"]
    system = window.dock_manager["SystemDock"]
    window.action_manager["trace_now"].trigger()
    settle(1.0)
    drawn = (len(editor.ax.lines), len(editor.ax.collections), len(editor.ax.texts))
    tab = rails.tabs.get("plot2d")
    rows.append(["P", dock.windowTitle() == "2D Plot" and rails.edge_of(dock) == "right" and tab is not None
                 and tab.edge == "right" and dock in window.tabifiedDockWidgets(system)
                 and rails.is_front(system) and not rails.is_front(dock)
                 and editor.figure is plot.figure and editor.canvas is plot.canvas and drawn[0] + drawn[1] >= 20,
                 f"panel {dock.windowTitle()!r} on the {rails.edge_of(dock)} edge, its tab there: "
                 f"{tab is not None and tab.edge == 'right'}; tabbed with System: "
                 f"{dock in window.tabifiedDockWidgets(system)}, System in front: {rails.is_front(system)}; the "
                 f"editor's figure and canvas are the panel's: {editor.figure is plot.figure and editor.canvas is plot.canvas}; "
                 f"drawn (lines, collections, texts): {drawn}"])

    # ---- C: each control drives the model --------------------------------------------------------
    calls: list = []
    labels = {}
    for item in PLOT_2D.left:
        commit = item.target.partition(".")[2]
        original = getattr(editor, commit)
        setattr(editor, commit, (lambda o=original, c=commit: (calls.append(c), o())[1]))
        labels[item.label] = (item.var.partition(".")[2], commit)
    controls = plot.controls
    results = {}
    for label, (variable_name, commit) in labels.items():
        widget = controls.get(label)
        variable = getattr(editor, variable_name)
        before_calls = len(calls)
        if widget is None:
            results[label] = "missing"
            continue
        if hasattr(widget, "setChecked"):
            start = bool(variable.get())
            widget.setChecked(not start)
            settle(0.3)
            wrote = bool(variable.get()) == (not start) and calls[before_calls:] == [commit]
            variable.set(start)                       # a model write repaints the check
            settle(0.1)
            repainted = widget.isChecked() == start
            widget.setChecked(start)                  # (already: no second commit)
            results[label] = wrote and repainted and calls[before_calls + 1:] == []
        else:
            options = [widget.itemText(i) for i in range(widget.count())]
            start = str(variable.get())
            other = next(option for option in options if option != start)
            widget.setCurrentText(other)
            settle(0.3)
            wrote = str(variable.get()) == other and calls[before_calls:] == [commit]
            widget.setCurrentText(start)
            settle(0.3)
            results[label] = wrote and str(variable.get()) == start
    for item in PLOT_2D.left:                        # the real commits back
        editor.__dict__.pop(item.target.partition(".")[2], None)

    def cardinal_count() -> int:
        return len(editor.__dict__.get("_cardinal_marker_artists", []) or [])

    def distance_count() -> int:
        return len(editor.__dict__.get("_physical_distance_artists", []) or [])

    cardinals = controls["Show PP / EP / XP"]
    cardinals.setChecked(True)
    settle(0.5)
    shown = cardinal_count()
    cardinals.setChecked(False)
    settle(0.5)
    hidden = cardinal_count()
    cardinals.setChecked(True)
    settle(0.5)
    again = cardinal_count()
    distances = controls["Physical Distance"]
    distances.setChecked(True)                        # on, by the box (its commit draws them) ...
    settle(0.5)
    with_distances = distance_count()
    distances.setChecked(False)                       # ... and off again (its commit clears them)
    settle(0.3)
    no_distances = distance_count()
    rows.append(["C", all(value is True for value in results.values()) and len(results) == len(PLOT_2D.left)
                 and shown > 0 and hidden == 0 and again == shown and no_distances == 0 and with_distances > 0,
                 f"each control writes its variable and runs its commit once (and repaints): {results}; PP / EP / XP "
                 f"marker artists on {shown} -> off {hidden} -> on {again}; Physical Distance annotations on "
                 f"{with_distances} -> off {no_distances}"])

    # ---- U: an analysis Update shows the plot ---------------------------------------------------
    update = window.analysis_toolbar.update_action
    editor._manual_update_plot = lambda *a, **k: calls.append("update")
    system.raise_()
    settle(0.3)
    behind = rails.is_front(dock)
    update.trigger()
    settle(0.4)
    from_behind = rails.is_front(dock)
    rails.toggle(dock)                                # in front: one click puts its stack away
    settle(0.3)
    closed = dock.isHidden()
    update.trigger()
    settle(0.4)
    from_closed = (rails.is_front(dock), dock.isHidden())
    del editor._manual_update_plot
    rows.append(["U", behind is False and from_behind is True and closed is True and from_closed == (True, False)
                 and calls.count("update") == 2,
                 f"behind the System tab, in front: {behind}; an Update -> in front: {from_behind}; closed by its tab: "
                 f"{closed}; an Update -> (in front, hidden) {from_closed}; the update ran {calls.count('update')}x"])

    # ---- N: Trace Now ---------------------------------------------------------------------------
    traced: list = []
    editor._trace_now = lambda *a, **k: traced.append(1)
    on_bar = window.action_manager["trace_now"] in plot.toolbar.actions()
    button = plot.toolbar.widgetForAction(window.action_manager["trace_now"])
    if isinstance(button, QToolButton):
        from PySide6.QtTest import QTest

        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        settle(0.2)
    del editor._trace_now
    rows.append(["N", on_bar and isinstance(button, QToolButton) and traced == [1]
                 and "trace_now" in ribbon_actions() and "plot_2d" in ribbon_actions(),
                 f"Trace Now on the plot's toolbar: {on_bar}; a click ran the model's deferred trace {len(traced)}x; "
                 f"on the ribbon: Trace Now {'trace_now' in ribbon_actions()}, 2D Plot {'plot_2d' in ribbon_actions()}"])
    return {"rows": rows}


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_plot2d_panel import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])["rows"]
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = static_checks() + _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
