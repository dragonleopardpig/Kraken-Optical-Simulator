"""Display-free guard: the Qt viewport draws the model's optical elements (bugs/0857,
docs/design_qt_migration.md phase 2).

The shipped shell drew only the imported STEP bodies, so every optical element the model builds --
the RA fold mirrors, the BS cubes, the lens discs, the stop, the LED panels -- was simply absent
from the 3D view. The viewport now draws `_scene_surface_meshes`, the SAME display geometry the
Tk 3D view draws, built from the system the trace runs on.

The Qt half runs in a SUBPROCESS on the xcb platform and needs a DISPLAY; without one, or without
PySide6, the E sections report SKIP.

  E1 every mesh record the model's own collector yields is drawn -- by row, not by count alone,
     so the RA mirror rows are demonstrably among them
  E2 the geometry IS the model's: a drawn actor's bounds equal the record's mesh bounds exactly
     (nothing re-derived, nothing re-transformed on the way to the screen)
  E3 colour and opacity come from the record, not from the viewport
  E4 the aperture stop is drawn as the Tk view draws it -- a RING, through the model's own
     `_legacy_3d_stop_ring_mesh`, not a filled disc
  E5 a scene whose display geometry cannot be built reports the failure and still draws the STEP
     bodies, instead of a silently empty viewport
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
#: this scene's right-angle fold mirrors, by row -- what the user found missing
RA_MIRROR_ROWS = (1, 5, 7, 15, 16, 18)


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.viewport import PREVIEW_SAMPLING

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    editor = window.editor
    viewport = window.viewport
    system, _rays, bundle = editor._build_preview_system_rays_bundle(
        sampling_mode=PREVIEW_SAMPLING, update_state=False)
    items = editor._scene_surface_meshes(system, bundle, include_reference_surfaces=False)

    # ---- E1 everything the model yields is on screen -----------------------------------------
    drawn = viewport.show_editor_scene(editor)
    drawn_rows = sorted({int(index) for index, _name, _points in drawn["elements"]})
    expected_rows = sorted({int(item.row_index) for item in items
                            if item.mesh is not None
                            and int(getattr(item.mesh, "n_points", 0)) > 0})
    ra_present = [index for index in RA_MIRROR_ROWS if index in drawn_rows]
    row("E1", drawn_rows == expected_rows and list(ra_present) == list(RA_MIRROR_ROWS)
        and len(viewport.element_actors) == len(items),
        f"{len(viewport.element_actors)} element actors for {len(items)} mesh records; rows "
        f"{drawn_rows} match the model's {expected_rows}; the RA fold mirrors {ra_present} are "
        f"among them")

    # ---- E2 the geometry is the model's --------------------------------------------------------
    # Pair POSITIONALLY, not by row: a row can yield more than one record (row 13 here yields a
    # disc and a solid body), and a row-keyed lookup would compare an actor against the wrong one.
    drawn_items = [item for item in items
                   if item.mesh is not None and int(getattr(item.mesh, "n_points", 0)) > 0]
    compared = []
    drifted = []
    for actor, item in zip(viewport.element_actors, drawn_items):
        if getattr(item, "is_stop", False) and not getattr(item, "is_body", False):
            continue  # the stop is deliberately re-shaped into a ring; E4 covers it
        actor_bounds = tuple(round(float(v), 9) for v in actor.GetBounds())
        mesh_bounds = tuple(round(float(v), 9) for v in item.mesh.GetBounds())
        if actor_bounds != mesh_bounds:
            drifted.append((int(item.row_index), str(item.row.name), actor_bounds, mesh_bounds))
        elif int(item.row_index) in RA_MIRROR_ROWS:
            compared.append((int(item.row_index), str(item.row.name)))
    row("E2", not drifted and compared
        and len(viewport.element_actors) == len(drawn_items),
        f"every drawn actor's bounds equal its record's mesh bounds -- checked including the RA "
        f"mirrors {compared}" + (f"; DRIFTED {drifted[:2]}" if drifted else ""))

    # ---- E3 colour and opacity come from the record --------------------------------------------
    wrong = []
    for actor, item in zip(viewport.element_actors, drawn_items):
        colour = tuple(round(float(c), 6) for c in actor.GetProperty().GetColor())
        expected = item.color
        if isinstance(expected, (tuple, list)):
            expected = tuple(round(float(c), 6) for c in tuple(expected)[:3])
            if colour != expected:
                wrong.append((int(item.row_index), colour, expected))
        if round(actor.GetProperty().GetOpacity(), 6) != round(float(item.opacity), 6):
            wrong.append((int(item.row_index), "opacity", actor.GetProperty().GetOpacity(),
                          float(item.opacity)))
    row("E3", not wrong,
        f"colour and opacity of all {len(viewport.element_actors)} actors come from the mesh "
        f"records" + (f" -- wrong: {wrong[:2]}" if wrong else ""))

    # ---- E4 the stop is a ring ------------------------------------------------------------------
    stop_detail = "this scene carries no aperture-stop disc"
    stop_ok = True
    for position, item in enumerate(drawn_items):
        if not (getattr(item, "is_stop", False) and not getattr(item, "is_body", False)):
            continue
        ring = editor._legacy_3d_stop_ring_mesh(item.mesh, item.row)
        drawn_points = int(viewport.element_actors[position].GetMapper()
                           .GetInput().GetNumberOfPoints())
        stop_ok = (ring is not None and drawn_points == int(ring.GetNumberOfPoints())
                   and drawn_points != int(item.mesh.GetNumberOfPoints()))
        stop_detail = (f"row {item.row_index} ({item.row.name}) drew {drawn_points} points -- the "
                       f"model's ring "
                       f"({int(ring.GetNumberOfPoints()) if ring is not None else None}), not its "
                       f"filled disc ({int(item.mesh.GetNumberOfPoints())})")
        break
    row("E4", stop_ok, stop_detail)

    # ---- E5 a failure is reported, not silent --------------------------------------------------
    def _raise(*_args, **_kwargs):
        raise RuntimeError("no first-order solution")

    saved = editor._build_preview_system_rays_bundle
    editor._build_preview_system_rays_bundle = _raise
    try:
        failed = window.refresh_from_model()
    finally:
        editor._build_preview_system_rays_bundle = saved
    message = window.statusBar().currentMessage()
    row("E5", failed["error"] and "no first-order solution" in failed["error"]
        and not failed["elements"] and len(failed["bodies"]) >= 3
        and "could not be built" in message,
        f"a model that cannot build its display geometry left the window up, still drew "
        f"{[b[0] for b in failed['bodies']]}, and said so: {message!r}")

    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the viewport needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0857_qt_view_draws_elements import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Qt viewport", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP E1-E5: {rows[0][2]}")
    else:
        for name, passed, detail in rows:
            ok(passed, f"{name}: {detail}")
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
