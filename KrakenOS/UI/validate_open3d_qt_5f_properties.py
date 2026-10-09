"""Phase 5f, part 3c guard (docs/design_qt_migration.md): the Scene Components browser's Properties /
Selected-Element pane reaches the Qt shell from ONE computation, `properties_for`.

In a real Qt shell on om05a_folded. What the pane must show is what `properties_for` worked out;
while the inspector still has its hidden Tk window, the Tk pane there is updated by the same
`_update_properties` and is compared too. Without that window (bugs/0998) there is no Tk pane,
and the claims hold against the model's answer alone:

  P  for a table row and two STEP overlays, the Qt pane shows exactly the five property texts
     and the enabled Selected-Element actions the model worked out (and the Tk pane's, where
     there is one); an overlay enables the face direction, a table row does not -- and the
     overlay case really enables actions (not vacuous)
  F  the Qt face-direction choice orients the picked face toward the CHOSEN direction: the value
     is passed in (`apply_face_direction`), never read from the Tk combobox's variable, which is
     hidden under the shell and never set by Qt
  C  a canvas pick -- which updates the pane without touching the tree -- refreshes the Qt pane too
  S  a clicked tree item is still alive when its own selection signal ends: the editor's refresh
     asks for a rebuild mid-signal, and rebuilding there deleted it -- an intermittent segfault
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5F3C_RESULT "
SKIP_MARK = "QT5F3C_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    dock, insp = window.scene_components, view.inspector
    panel = dock.panel()

    def select(iid: str) -> None:
        dock.items[iid].setSelected(True)
        dock.widget.setCurrentItem(dock.items[iid])
        app.processEvents()

    #: whether the inspector built its hidden Tk pane: it does unless it has no Tk window (bugs/0998)
    tk_pane = bool(panel._property_vars)

    def shown() -> tuple:
        """(the Qt pane's texts, what they must be, its enabled actions, what those must be)."""
        qt_values = {k: w.text() for k, w in dock.property_labels.items()}
        qt_buttons = {k: b.isEnabled() for k, b in dock.action_buttons.items()}
        model = panel._last_properties              # what `_update_properties` last handed every pane
        values = {k: str(v) for k, v in model["values"].items()}
        buttons = {k: bool(model["buttons"].get(k, False)) for k in qt_buttons}
        if tk_pane:                                 # and the Tk pane says the same, as it always did
            tk_values = {k: str(v.get()) for k, v in panel._property_vars.items()}
            tk_buttons = {k: str(b.cget("state")) == "normal" for k, b in panel._selection_buttons.items()}
            if tk_values != values or tk_buttons != buttons:
                return qt_values, {"the Tk pane differs from the model": tk_values}, qt_buttons, tk_buttons
        return qt_values, values, qt_buttons, buttons

    import shiboken6

    rows = []
    table = next((i for i in dock.items if i.startswith("scene-row:")), None)
    overlays = [i for i in dock.items if i.startswith("overlay:")][:2]

    # S -- a click's item outlives its own selection signal: the editor's refresh asks for a
    # rebuild mid-signal, and a synchronous clear() deleted the item Qt was still selecting (the
    # intermittent segfault). This slot runs after the dock's own, still inside the signal; the
    # signals a rebuild itself emits (restoring the selection on the NEW items) are not clicks.
    survived = []
    watched = {}

    def probe() -> None:
        if "item" in watched and not dock._rebuilding:
            survived.append(shiboken6.isValid(watched["item"]))

    dock.widget.itemSelectionChanged.connect(probe)
    for iid in ([table] if table else []) + overlays:
        watched["item"] = dock.items[iid]
        dock.widget.setCurrentItem(watched["item"])
        app.processEvents()
    watched.clear()
    dock.widget.itemSelectionChanged.disconnect(probe)
    rows.append(["S", len(survived) >= 3 and all(survived),
                 f"the clicked item was still alive after each selection signal: {survived}"])
    cases, same, overlay_enables, table_face, overlay_face = [], True, True, None, True
    for iid in ([table] if table else []) + overlays:
        select(iid)
        qv, tv, qb, tb = shown()
        equal = qv == tv and qb == tb
        same = same and equal
        cases.append(f"{iid}: equal={equal} enabled={sum(qb.values())}")
        if iid.startswith("overlay:"):
            overlay_enables = overlay_enables and sum(qb.values()) >= 3
            overlay_face = overlay_face and dock.face_direction.isEnabled()
        else:
            table_face = dock.face_direction.isEnabled()
    rows.append(["P", bool(table) and len(overlays) >= 2 and same and overlay_enables and overlay_face
                 and table_face is False,
                 f"{'; '.join(cases)}; face direction: overlay={overlay_face}, table={table_face}"
                 + ("; the hidden Tk pane says the same" if tk_pane else "; no Tk pane to compare (the inspector has no Tk window)")])

    oriented = []
    original = insp.orient_selected_step_face_to_direction
    insp.orient_selected_step_face_to_direction = lambda direction: oriented.append(direction)
    try:
        select(overlays[0])
        index = dock.face_direction.findText("Up")
        dock.face_direction.setCurrentIndex(index)
        dock.face_direction.activated.emit(index)
        app.processEvents()
    finally:
        insp.orient_selected_step_face_to_direction = original
    hidden_var = str(panel._face_direction_var.get()) if panel._face_direction_var is not None else None
    rows.append(["F", oriented == ["Up"],
                 f"the Qt choice oriented toward {oriented} (the hidden Tk variable still reads {hidden_var!r})"])

    select(table)
    before = dock.property_labels["kind"].text()
    panel.select_from_canvas(overlays[0])
    app.processEvents()
    after = dock.property_labels["kind"].text()
    # against what the MODEL last worked out, not the hidden Tk pane's variable: without the
    # inspector's Tk window (bugs/0998) there is no such variable, and where there is one it was
    # set from this
    worked_out = str(panel._last_properties["values"]["kind"])
    tk_pane = panel._property_vars.get("kind")
    rows.append(["C", before != after and after == worked_out and (tk_pane is None or str(tk_pane.get()) == worked_out),
                 f"a canvas pick moved the Qt pane from {before!r} to {after!r}"
                 + ("" if tk_pane is None else " (and the hidden Tk pane with it)")])
    return rows


def _run() -> list:
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
        "from KrakenOS.UI.validate_open3d_qt_5f_properties import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown: VTK/Qt objects can segfault while
        # being destroyed, and a crash there loses a buffered result line (0932)
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, "timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    rows = _run()
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
