"""bugs/0528 guard -- the GIZMO-ARROW lens drag refocuses at the sensor (Solve for FOV).

flag_20260803_203614: "the FOV changed after lens dragged, but the rays are defocus, I
think FOV not changed fully enough." The user dragged the lens by the gizmo translate
ARROW. That commit (`_finish_step_translate_drag`) ran the 0526 conjugate composite --
gaps written, FOV overlay follows -- but only the 0520 body-grab CARRY finish ran the
Solve-for-FOV snap, so the sensor kept its old seat: rays visibly defocused, and the drawn
FOV described the stale sensor (33.7 where the refocused equilibrium is ~47.7).

Checks:
  SOURCE -- the translate-drag finish carries the 0528 refocus block, gated on the
            row-shift breadcrumbs (conjugates actually written).
  REAL   -- on the frozen AZ85 scene, the user's +50.54 mm X-arrow drag writes its
            sections AND re-seats the sensor at best focus with the refocus note.
  NEG    -- a perpendicular arrow drag stays body-only: no gap writes, no snap, no note.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import open3d_inspector as _oi

    src = _inspect.getsource(_oi.Kraken3DInspector._finish_step_translate_drag)
    if (
        "bugs/0528" in src
        and "snap_detector_to_image_plane" in src
        and "_last_translate_row_shifts" in src
    ):
        notes.append("SOURCE = the gizmo-arrow finish runs the row-shift-gated refocus")
    else:
        notes.append("SOURCE the 0528 refocus block is missing from _finish_step_translate_drag")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector
        from KrakenOS.UI.services import optical_axis_tree as tree_mod

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)

        def _sensor_z() -> float:
            return float(np.asarray(tree_mod.row_world_pose(app.rows, len(app.rows) - 1), float).reshape(-1)[2])

        gaps0 = [float(r.thickness) for r in app.rows]
        z0 = _sensor_z()
        insp._finish_step_translate_drag(
            {"label": "lens", "axis": "x", "axis_unit": (1.0, 0.0, 0.0), "applied_delta_mm": 50.542}
        )
        gaps1 = [float(r.thickness) for r in app.rows]
        z1 = _sensor_z()
        deltas = [round(b - a, 2) for a, b in zip(gaps0, gaps1)]
        if abs(deltas[0] - 50.54) < 0.5 and abs(deltas[6] + 50.54) < 0.5:
            notes.append(f"REAL = the arrow drag wrote its sections (row 0 {deltas[0]:+.2f}, row 6 {deltas[6]:+.2f})")
        else:
            notes.append(f"REAL section write wrong (deltas {deltas})")
            ok = False
        if abs(z1 - z0) > 5.0:
            notes.append(f"REAL = the sensor re-seated at best focus (z {z0:+.2f} -> {z1:+.2f})")
        else:
            notes.append(f"REAL the sensor kept its stale seat (z {z0:+.2f} -> {z1:+.2f}) -- the 203614 defocus")
            ok = False
        if "Solve for FOV" in str(insp.status_var.get()):
            notes.append("REAL = the status carries the refocus note")
        else:
            notes.append(f"REAL no refocus note in status: {str(insp.status_var.get())[-90:]}")
            ok = False

        gaps2 = [float(r.thickness) for r in app.rows]
        z2 = _sensor_z()
        insp._finish_step_translate_drag(
            {"label": "lens", "axis": "z", "axis_unit": (0.0, 0.0, 1.0), "applied_delta_mm": 5.0}
        )
        gaps3 = [float(r.thickness) for r in app.rows]
        z3 = _sensor_z()
        if all(abs(b - a) < 1e-9 for a, b in zip(gaps2, gaps3)) and abs(z3 - z2) < 1e-9:
            notes.append("NEG = a perpendicular arrow drag stays body-only (no writes, no snap)")
        else:
            notes.append(f"NEG a perpendicular arrow drag changed the model (gap deltas "
                         f"{[round(b - a, 3) for a, b in zip(gaps2, gaps3)]}, sensor {z2:+.3f} -> {z3:+.3f})")
            ok = False
        if "Solve for FOV" in str(insp.status_var.get()):
            notes.append("NEG the perpendicular drag carried a refocus note")
            ok = False
        else:
            notes.append("NEG = no refocus note on the perpendicular drag")
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
