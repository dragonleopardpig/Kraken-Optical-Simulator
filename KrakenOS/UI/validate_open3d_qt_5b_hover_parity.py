"""Phase 5b guard (docs/design_qt_migration.md): hover and pick RESULTS match Tk in the Qt shell.

0906 routed Qt input to the inspector's handlers in the Tk order; 5b is whether what the user SEES
under the pointer is the same. Each scene is swept twice along the identical path of pixels:

  * with real Qt input -- `QMouseEvent` moves, Alt as a `QKeyEvent` plus the Alt modifier;
  * with the Tk bindings' own sequence -- the VTK interactor gets the motion first
    (`SetEventInformationFlipY` + `MouseMoveEvent`, which runs its hover-pick observer and the
    navigation cube), then the `hover` handler is dispatched; Alt as the `alt_press` handler and
    the Alt state bit. That is what the Tk widget does (0906: "a bare move goes to VTK first").

After every move the hover state is snapshotted: every `*hover*` attribute of the inspector, the
hover outline's GEOMETRY (polygons / lines / points -- a face outline and an edge highlight have the
same actor class, so class names alone would pass vacuously), the in-viewport hover text, the
status line, the Alt flag, the navigation cube's hovered cell and arrow. The two sequences must be
identical, step by step. The status line is reset before each sweep: a thickness handle's
message stays after the pointer leaves it (in both shells), so a sweep otherwise inherits the
previous sweep's last message.

  H  om05a_folded with the thickness dimensions shown: a 16 x 10 raster, the navigation cube's
     corner and the projected centre of each thickness-dimension handle -- Qt == Tk, and the sweep
     really hovered scene features, cube cells and thickness handles
  E  the vendor LED STEP (the bugs/0323/0324 face/edge contract): plain and Alt sweeps over its
     outline -- Qt == Tk in both, and Alt changes the highlight (face -> nearest drawn edge) at
     most of the hovered pixels, so the Alt comparison is not vacuous
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5B_RESULT "
SKIP_MARK = "QT5B_SKIP "
OM05A = Path("attachment/om05a_folded.py")
LED_STEP = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP")


def qt_runtime_checks(scene: str) -> list:
    import time

    import numpy as np
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QKeyEvent, QMouseEvent
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.layout_editor import SurfaceRow
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.viewport_events import ALT, ViewportEvent

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    editor = window.editor
    if scene == "om05a":
        window.load_layout_path(OM05A)
    else:
        editor.rows = [
            SurfaceRow(label="0", surface="Object", element="", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
            SurfaceRow(label="1", surface="Image", element="", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
        ]
        editor._sync_table()
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    insp, widget = view.inspector, view.widget
    iren = insp._vtk_interactor
    ratio = view.pixel_ratio() or 1.0
    cube = insp._navigation_cube
    render_window = widget.GetRenderWindow()

    def pump(ms: float = 60.0) -> None:
        end = time.monotonic() + ms / 1000.0
        app.processEvents()
        while time.monotonic() < end:
            time.sleep(0.01)
            app.processEvents()

    def to_widget(point):
        renderer = insp._renderer
        height = render_window.GetSize()[1]
        renderer.SetWorldPoint(float(point[0]), float(point[1]), float(point[2]), 1.0)
        renderer.WorldToDisplay()
        dx, dy, _ = renderer.GetDisplayPoint()
        return int(dx / ratio), int((height - dy) / ratio)

    width, height = widget.width(), widget.height()
    if scene == "om05a":
        editor.show_physical_distances_var.set(True)
        insp.refresh_from_editor(force_retrace=False)
        pump(300)
        points = [(int(width * (i + 0.5) / 16), int(height * (j + 0.5) / 10)) for j in range(10) for i in range(16)]
        points += [(width - 60 + dx, 60 + dy) for dx in (-20, 0, 20) for dy in (-20, 0, 20)]
        for key in list((insp.__dict__.get("_actor_thickness_dimension_map") or {}))[:24]:
            actor = insp._actor_by_key.get(key)
            if actor is None:
                continue
            x, y = to_widget(actor.GetCenter())
            if 2 < x < width - 2 and 2 < y < height - 2:
                points += [(x, y), (2, height // 2)]
        sweeps = (False,)
    else:
        editor.imported_led_step_path = LED_STEP
        editor.select_step_component("led")
        insp.show_rays_var.set(False)
        insp.refresh_from_editor(force_retrace=False)
        pump(300)
        insp._renderer.ResetCamera()
        render_window.Render()
        pump(100)
        bounds = np.asarray(editor._transformed_imported_step_mesh_for_label("led").bounds).reshape(3, 2)
        corners = [to_widget((x, y, z)) for x in bounds[0] for y in bounds[1] for z in bounds[2]]
        xs, ys = [c[0] for c in corners], [c[1] for c in corners]
        x0, x1 = max(5, min(xs)), min(width - 5, max(xs))
        y0, y1 = max(5, min(ys)), min(height - 5, max(ys))
        points = [(int(x0 + (x1 - x0) * (i + 0.5) / 18), int(y0 + (y1 - y0) * (j + 0.5) / 12))
                  for j in range(12) for i in range(18)]
        sweeps = (False, True)

    def simple(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, tuple) and all(isinstance(x, (str, int, float, bool, type(None))) for x in value):
            return list(value)
        return type(value).__name__

    def snapshot() -> dict:
        state = {k: simple(v) for k, v in vars(insp).items() if "hover" in k.lower() and not callable(v)}
        state.pop("_trailing_hover_repick_after_id", None)  # a timer id, not something the user sees
        state["status"] = str(insp.status_var.get())
        text_actor = insp.__dict__.get("_hover_status_actor")
        try:
            state["hover_text"] = text_actor.GetInput() if text_actor is not None else None
        except Exception:
            state["hover_text"] = "?"
        outline = insp.__dict__.get("_hover_step_outline_actor")
        try:
            data = outline.GetMapper().GetInput() if outline is not None else None
            state["outline"] = None if data is None else [int(data.GetNumberOfPolys()), int(data.GetNumberOfLines()),
                                                          int(data.GetNumberOfPoints())]
        except Exception as exc:
            state["outline"] = repr(exc)[:40]
        state["alt"] = bool(insp._edge_pick_alt_active)
        if cube is not None:
            state["cube_cell"] = getattr(cube, "_hover_cell", None)
            state["cube_arrow"] = getattr(cube, "_arrow_hover_actor", None) is not None
        return state

    def qt_move(x, y, alt):
        modifiers = Qt.KeyboardModifier.AltModifier if alt else Qt.KeyboardModifier.NoModifier
        QApplication.sendEvent(widget, QMouseEvent(QEvent.Type.MouseMove, QPointF(x, y),
                                                   QPointF(widget.mapToGlobal(QPoint(x, y))),
                                                   Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, modifiers))

    def qt_alt(down):
        QApplication.sendEvent(widget, QKeyEvent(QEvent.Type.KeyPress if down else QEvent.Type.KeyRelease, Qt.Key.Key_Alt,
                                                 Qt.KeyboardModifier.AltModifier if down else Qt.KeyboardModifier.NoModifier))

    def tk_move(x, y, alt):
        px, py = int(x * ratio), int(y * ratio)
        iren.SetEventInformationFlipY(px, py, 0, 0, chr(0), 0, None)
        iren.MouseMoveEvent()
        insp.dispatch_viewport_event("hover", ViewportEvent(px, py, ALT if alt else 0))

    def tk_alt(down):
        insp.dispatch_viewport_event("alt_press" if down else "alt_release",
                                     ViewportEvent(0, 0, ALT if down else 0, keysym="Alt_L"))

    runs = {}
    for alt in sweeps:
        for mode, move, alt_key in (("qt", qt_move, qt_alt), ("tk", tk_move, tk_alt)):
            move(2, height // 2, False)
            pump(120)
            insp.status_var.set("sweep start")
            if alt:
                alt_key(True)
                pump(60)
            sequence = []
            for x, y in points:
                move(x, y, alt)
                pump(60)
                sequence.append(snapshot())
            if alt:
                alt_key(False)
                pump(60)
            runs[(mode, alt)] = sequence

    rows = []

    def differences(alt):
        # A hover attribute is created lazily the first time it is used, so the sweep that runs
        # first lacks keys the second already has; the inspector reads them with
        # __dict__.get(), so an absent attribute IS None. Compared as JSON: a field can hold a
        # float NaN, and NaN != NaN would call two identical snapshots different.
        def same(a, b):
            keys = set(a) | set(b)
            return json.dumps({k: a.get(k) for k in keys}, sort_keys=True, default=str) == \
                json.dumps({k: b.get(k) for k in keys}, sort_keys=True, default=str)
        return [i for i, (a, b) in enumerate(zip(runs[("qt", alt)], runs[("tk", alt)])) if not same(a, b)]

    hovered = sum(1 for s in runs[("qt", False)] if s.get("_hover_step_cell_key") or s.get("hover_text"))
    if scene == "om05a":
        diff = differences(False)
        cells = sorted({s.get("cube_cell") for s in runs[("qt", False)]} - {-1, None})
        handles = sum(1 for s in runs[("qt", False)] if s.get("_thickness_hover_actor_key"))
        rows.append(["H", not diff and hovered >= 20 and len(cells) >= 3 and handles >= 1,
                     f"om05a_folded, {len(points)} pixels: {len(diff)} differ between Qt input and the Tk "
                     f"sequence; the sweep hovered {hovered} scene features, cube cells {cells} and "
                     f"{handles} thickness handles"])
    else:
        plain, held = differences(False), differences(True)
        changed = sum(1 for a, b in zip(runs[("qt", False)], runs[("qt", True)])
                      if (a.get("outline"), a.get("_hover_step_cell_key")) != (b.get("outline"), b.get("_hover_step_cell_key")))
        alt_flag = all(s.get("alt") for s in runs[("qt", True)]) and all(s.get("alt") for s in runs[("tk", True)])
        rows.append(["E", not plain and not held and alt_flag and hovered >= 20 and changed >= hovered // 2,
                     f"LED STEP, {len(points)} pixels, {hovered} hovered: {len(plain)} differ plain and "
                     f"{len(held)} with Alt; Alt held throughout in both: {alt_flag}; Alt changes the "
                     f"highlight at {changed} pixels"])
    return rows


def _run_qt_subprocess(scene: str) -> tuple[str, list]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_qt_5b_hover_parity import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown: VTK/Qt objects can segfault while
        # being destroyed, and a crash there loses a buffered result line (0932)
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks({scene!r})), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1500, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [[scene, False, "the Qt subprocess timed out after 1500 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [[scene, True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [[scene, False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    missing = [str(p) for p in (OM05A, LED_STEP) if not p.exists()]
    if missing:
        return True, [f"SKIP = fixtures absent: {missing}"]
    for scene in ("om05a", "led"):
        status, rows = _run_qt_subprocess(scene)
        for key, ok, detail in rows:
            passed = passed and bool(ok)
            notes.append(f"{key} = {detail}" if ok else f"{key} FAILED: {detail}")
        if status == "skip":
            notes.append(f"{scene} = the Qt half was skipped (no PySide6 or no display)")
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
