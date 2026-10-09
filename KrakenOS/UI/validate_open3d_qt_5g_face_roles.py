"""Phase 5g part 2 guard (docs/design_qt_migration.md, bugs/0934): the CAD/STL face-roles editor
opens in the Qt shell, over the same `FaceRolesSession` the Tk dialog renders. In a real Qt shell on
the Edmund 42779 vendor prism row, driven with REAL Qt input:

  O  Edit -> "Assign CAD/STL Optical Faces" on the prism row opens the Qt dialog, and no Tk window
     does (the model hands its session to the shell's hook)
  V  the Qt face table shows the session's cells for every face, and clicking a row selects that
     face in the session and loads its form
  F  choosing a (different) function in the Qt combo and typing a loss + Return persist to the row's face
     metadata at once, and the debounced Open 3D retrace FIRES under Qt -- once, on the host's
     timer (a Tk timer never fires in the Qt shell)
  P  a real left click in the Qt VTK preview selects the face it hit; a real left DRAG orbits the
     camera and selects nothing
  S  Save Roles (the Qt button) auto-orients the row from the Input Port face, and the dialog
     keeps the save's message on screen
  T  the same actions through the Tk view and through the Qt view leave the SAME face metadata:
     one session implementation, two renderings
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5G_RESULT "
SKIP_MARK = "QT5G_SKIP "
SPLITTER = "Partial Reflecting / Transmitting"   # the combo label of a Beam Splitter face


def _prism_rows(editor) -> None:
    from KrakenOS.UI import capture_vendor_prism_case_study_screenshots as cap

    mesh, *_rest = cap._mesh_vendor_prism(Path("attachment/cad_cache"))
    cap._configure_app(editor, mesh, cap._metadata_for_mesh(mesh))


def _saved_faces(editor) -> dict:
    attr = "OpticalSolidFaces"
    keep = ("side_2d", "function", "port_role", "loss", "split_ratio", "flip_normal")
    return {f["face_id"]: {k: f.get(k) for k in keep} for f in editor.rows[1].advanced[attr]["faces"]}


def _row_point(tree, item):
    """A point on ``item``'s row that is inside the viewport: the row rect spans every column
    (wider than the pane), so its centre can lie off to the right where a click lands on nothing."""
    from PySide6.QtCore import QPoint

    rect = tree.visualItemRect(item)
    return QPoint(rect.left() + 20, rect.center().y())


def qt_runtime_checks() -> list:
    import time

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    editor = window.editor
    _prism_rows(editor)
    window.refresh_from_model()
    for _ in range(20):
        app.processEvents()
    rows = []

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    retraces: list = []
    editor._refresh_open_3d_views = lambda force_retrace=False, **_kw: retraces.append(bool(force_retrace))

    # O -- the menu action on the selected prism row
    window.rows_view.setCurrentIndex(window.rows_view.model().index(1, 0))
    import tkinter as tk
    window.action_manager["face_roles"].trigger()
    settle(0.8)
    dialog = getattr(window, "last_face_roles_dialog", None)
    # an editor built with no Tk root (KRAKEN_QT_TK_FREE=all, bugs/0999) cannot have opened a Tk window
    tk_windows = [] if editor.root is None else [
        w for w in editor.winfo_children()
        if isinstance(w, tk.Toplevel) and "CAD/STL Optical Faces" in str(w.title()) and w.winfo_viewable()]
    rows.append(["O", dialog is not None and dialog.isVisible() and not tk_windows and dialog.preview is not None,
                 f"Qt dialog open: {dialog is not None and dialog.isVisible()}; VTK preview: "
                 f"{dialog is not None and dialog.preview is not None}; Tk face windows shown: {len(tk_windows)}"])
    if dialog is None:
        return rows
    session = dialog.session
    index = {r["face_id"]: i for i, r in enumerate(session.records)}

    # V -- the table is the session's rows; a real click selects
    cells = [[item.text(c) for c in range(len(dialog.columns))] for item in dialog.items]
    wanted = [[r[k] for k in dialog.columns] for r in session.rows()]
    QTest.mouseClick(dialog.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     _row_point(dialog.tree, dialog.items[index["F003"]]))
    settle(0.2)
    rows.append(["V", cells == wanted and session.selection == [index["F003"]] and session.validation.startswith("F003"),
                 f"table cells == session rows: {cells == wanted}; a click on F003 selected {session.selection} "
                 f"({session.validation[:40]!r})"])

    # F -- a combo choice + a typed loss persist now; ONE retrace fires on the Qt timer
    retraces.clear()
    combo = dialog.combos["function"]
    combo.setCurrentIndex(combo.findText(SPLITTER))        # a real item, different from F003's own
    combo.activated.emit(combo.currentIndex())
    loss = dialog.entries["loss"]
    loss.setFocus()
    loss.selectAll()
    QTest.keyClicks(loss, "0.25")
    QTest.keyClick(loss, Qt.Key.Key_Return)
    immediate = _saved_faces(editor)["F003"]
    before = len(retraces)
    settle(0.8)
    rows.append(["F", immediate["function"] == "Beam Splitter" and abs(float(immediate["loss"]) - 0.25) < 1e-9
                 and before == 0 and retraces == [True],
                 f"row metadata at once: function={immediate['function']!r} loss={immediate['loss']}; retraces "
                 f"before the timer {before}, after {retraces}"])

    # P -- a real click picks (a face that is NOT already selected, so the click must change it),
    # a real drag orbits
    widget = dialog.vtk_widget
    preview = dialog.preview
    renderer = preview.renderer
    ratio = float(widget._getPixelRatio()) if hasattr(widget, "_getPixelRatio") else 1.0
    height = widget.GetRenderWindow().GetSize()[1]
    point, expected = None, None
    for i in range(len(session.records)):
        face = session.world_face(i)
        if face is None:
            continue
        renderer.SetWorldPoint(*face["centroid_world"], 1.0)
        renderer.WorldToDisplay()
        x, y, _z = renderer.GetDisplayPoint()
        candidate = QPoint(int(round(x / ratio)), int(round((height - 1 - y) / ratio)))
        hit, _hit_point = preview.pick(*dialog.vtk_point(candidate))
        if hit is not None and [hit] != session.selection:
            point, expected = candidate, hit
            break
    if point is None:
        return rows + [["P", False, "no face centre in the preview picks a face other than the selected one"]]
    QTest.mouseClick(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    settle(0.2)
    clicked = list(session.selection)
    camera = renderer.GetActiveCamera()
    before_position = tuple(camera.GetPosition())
    selection_before = list(session.selection)
    QTest.mousePress(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
    for step in range(1, 9):
        QTest.mouseMove(widget, point + QPoint(step * 8, step * 3))
        app.processEvents()
    QTest.mouseRelease(widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point + QPoint(64, 24))
    settle(0.2)
    moved = sum((a - b) ** 2 for a, b in zip(before_position, camera.GetPosition())) ** 0.5
    rows.append(["P", expected is not None and clicked == [expected] and moved > 1e-3 and session.selection == selection_before,
                 f"a click on face {expected}'s centre selected {clicked}; a drag moved "
                 f"the camera {moved:.3g} mm and left the selection {session.selection}"])

    # S -- Save Roles from the Qt button, auto-orient from the Input Port
    QTest.mouseClick(dialog.tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     _row_point(dialog.tree, dialog.items[index["F005"]]))
    settle(0.2)
    QTest.mouseClick(dialog.buttons["Save Roles"], Qt.MouseButton.LeftButton)
    settle(0.3)
    le = session.le
    world = {f["face_id"]: f for f in le.optical_solid_face_world_records(editor.rows[1], editor._stl_row_z_station(1), assigned_only=False)}
    normal_z = float(world["F005"]["normal_world"][2])
    shown = dialog.validation.text()
    rows.append(["S", normal_z < -0.99 and shown.startswith("Saved roles. Auto-oriented"),
                 f"F005 world normal z after Save = {normal_z:.4f}; the dialog reads {shown[:50]!r}"])
    qt_faces = _saved_faces(editor)
    dialog.close()
    return rows + [["_faces", True, json.dumps(qt_faces)]]


def tk_runtime_checks() -> list:
    """The Qt run's actions through the TK view, for T."""
    import time

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.update()
    _prism_rows(editor)
    editor._refresh_open_3d_views = lambda force_retrace=False, **_kw: None
    editor.open_optical_solid_face_role_editor(1)
    end = time.time() + 1.0
    while time.time() < end:
        editor.update()
        time.sleep(0.02)
    view = editor._main_optical_solid_face_roles_dialog()._view
    session = view.session
    index = {r["face_id"]: i for i, r in enumerate(session.records)}
    view.tree.selection_set(f"face_{index['F003']}")
    view.tree.focus(f"face_{index['F003']}")
    editor.update()
    view.combos["function"].set(SPLITTER)
    view.combos["function"].event_generate("<<ComboboxSelected>>")
    editor.update()
    entry = view.entries["loss"]
    entry.delete(0, "end")
    entry.insert(0, "0.25")
    entry.focus_force()          # Tk delivers a key event to the FOCUSED widget only, as a user types
    editor.update()
    entry.event_generate("<Return>")
    editor.update()
    view.tree.selection_set(f"face_{index['F005']}")
    view.tree.focus(f"face_{index['F005']}")
    editor.update()
    # the Qt run's P step clicked F005 too before saving; the save itself is the same button
    view._act(session.save_roles)
    editor.update()
    return [["_faces", True, json.dumps(_saved_faces(editor))]]


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
        "from KrakenOS.UI.validate_open3d_qt_5g_face_roles import tk_runtime_checks, qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1200,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        return True, [f"SKIP = {PRISM_42779_STEP} absent"]
    qt_rows = _run("qt_runtime_checks()")
    tk_rows = _run("tk_runtime_checks()")
    qt_faces = next((json.loads(d) for k, _ok, d in qt_rows if k == "_faces"), None)
    tk_faces = next((json.loads(d) for k, _ok, d in tk_rows if k == "_faces"), None)
    rows = [r for r in qt_rows + tk_rows if r[0] != "_faces"]
    differ = sorted(f for f in (qt_faces or {}) if (qt_faces or {}).get(f) != (tk_faces or {}).get(f))
    rows.append(["T", qt_faces is not None and tk_faces is not None and not differ,
                 f"Tk and Qt runs saved the same metadata for {len(qt_faces or {})} faces; differing: "
                 + "; ".join(f"{f} Qt {(qt_faces or {}).get(f)} Tk {(tk_faces or {}).get(f)}" for f in differ[:2])])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
