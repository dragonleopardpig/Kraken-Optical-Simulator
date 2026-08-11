"""Guard for bugs/0612 — replacing a camera seats the body on the TRACED sensor.

flag_20260811_204049 ("replace a camera, it dislocate"): `replace_camera_from_folder`
re-imported the STEP at the bugs/0220 straight-axis z and kept only the old transverse
offset, so on a 0433-frozen fold leg (which runs backwards) the new body landed on the
WRONG SIDE of its own sensor — measured: replacing hr25MCX with ITSELF flipped the body
across the sensor plane (z −28.7 → +22.0, distance unchanged). The fix routes the
replace flow through `seat_camera_on_sensor` (traced-beam direction, bugs/0480 ladder),
with the transverse-keep surviving only as the refusal fallback.

Checks:
  A  CONTRACT (display-free) — the replace flow calls seat_camera_on_sensor, and the
     transverse fallback is gated on the "Seat camera:" refusal prefix.
  B  REAL (skipped without the fixtures) — on the frozen Apo75, replacing the camera
     with ITSELF preserves the body-to-sensor VECTOR: same side of the plane (the
     bugs/0612 flip is the failure), same offset within 2 mm.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0612_replace_camera_seats_on_fold
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
CAMERA_FOLDER = PROJECT_ROOT / "attachment" / "Cameras" / "hr25MCX"


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_table_workbench as workbench_module

    src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin.replace_camera_from_folder)
    if "seat_camera_on_sensor" not in src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0612): replace_camera_from_folder no longer seats through "
            "seat_camera_on_sensor -- a frozen fold leg flips the new body across its sensor again"
        )
    elif 'startswith("Seat camera:")' not in src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0612): the transverse fallback is no longer gated on the seat "
            "REFUSAL -- an 'already seated' body gets its axial answer overwritten"
        )
    else:
        notes.append("PASS: A: the replace flow seats on the traced sensor, fallback only on refusal")

    if not SCENE.exists() or not CAMERA_FOLDER.exists():
        notes.append("SKIP: B: fixtures missing (scene or hr25MCX camera folder)")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import row_placement

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["_0612"] = SCENE
        app.load_layout_by_name("_0612")

        def body_vector():
            pos, _rot, _ = row_placement.world_frame(app, len(app.rows) - 1)
            sensor = np.asarray(pos, dtype=float).reshape(3)
            mesh = app._transformed_imported_step_mesh_for_label("camera")
            return np.asarray(mesh.center, dtype=float) - sensor

        before = body_vector()
        result = app.replace_camera_from_folder(folder=str(CAMERA_FOLDER), refresh_open_3d=False)
        if result is None:
            ok = False
            notes.append("FAIL: B: replace_camera_from_folder returned None on the fixture folder")
            return ok, notes
        after = body_vector()
        side = float(np.dot(before, after))
        drift = float(np.linalg.norm(after - before))
        if side <= 0.0:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0612): the body FLIPPED across the sensor plane "
                f"(before {np.round(before, 1).tolist()}, after {np.round(after, 1).tolist()})"
            )
        elif drift > 2.0:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0612): same-camera replace moved the body {drift:.1f} mm "
                f"relative to its sensor (want a no-op within 2 mm)"
            )
        else:
            notes.append(
                f"PASS: B: same-camera replace preserves the body-to-sensor vector "
                f"(drift {drift:.2f} mm, same side)"
            )
    except Exception as exc:  # pragma: no cover - harness failure, not a product failure
        ok = False
        notes.append(f"FAIL: harness error {type(exc).__name__}: {exc}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Replace-camera-seats-on-fold validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
