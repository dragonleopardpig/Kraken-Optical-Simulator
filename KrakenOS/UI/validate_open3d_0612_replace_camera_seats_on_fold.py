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

    # bugs/0614 moved the seat into the IMPORT flow (import_camera_step wipes every offset,
    # so the plain import dislocated too -- 186.8 mm measured); the replace flow delegates.
    import_src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin.import_vendor_camera_from_folder)
    replace_src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin.replace_camera_from_folder)
    if "seat_camera_on_sensor" not in import_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0612/0614): import_vendor_camera_from_folder no longer seats through "
            "seat_camera_on_sensor -- a frozen fold leg dislocates the imported body again"
        )
    elif 'startswith("Seat camera:")' not in import_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0612): the transverse fallback is no longer gated on the seat "
            "REFUSAL -- an 'already seated' body gets its axial answer overwritten"
        )
    elif import_src.index("seat_camera_on_sensor") > import_src.index("_relearn_folded_m_correction_after_swap"):
        ok = False
        notes.append(
            "FAIL: A (bugs/0614): the seat runs AFTER the 0608 re-measure -- a dislocated "
            "body vignettes the probe and poisons the learned correction (+81.6% measured)"
        )
    elif "import_vendor_camera_from_folder" not in replace_src:
        ok = False
        notes.append("FAIL: A (bugs/0612): the replace flow no longer delegates to the seating import flow")
    else:
        notes.append("PASS: A: the import flow seats before the re-measure; replace delegates to it")

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
        # Both camera flows must be a placement no-op with the SAME camera: the replace
        # flow (bugs/0612) and the plain import flow (bugs/0614 -- the flag's actual door,
        # which wiped the transverse glue offset and flipped the axial sign: 186.8 mm).
        for flow_name, flow in (
            ("replace", lambda: app.replace_camera_from_folder(folder=str(CAMERA_FOLDER), refresh_open_3d=False)),
            ("import", lambda: app.import_vendor_camera_from_folder(str(CAMERA_FOLDER), refresh_open_3d=False)),
        ):
            result = flow()
            if result is None:
                ok = False
                notes.append(f"FAIL: B[{flow_name}]: returned None on the fixture folder")
                return ok, notes
            after = body_vector()
            side = float(np.dot(before, after))
            drift = float(np.linalg.norm(after - before))
            if side <= 0.0:
                ok = False
                notes.append(
                    f"FAIL: B[{flow_name}] (bugs/0612/0614): the body FLIPPED across the sensor "
                    f"plane (before {np.round(before, 1).tolist()}, after {np.round(after, 1).tolist()})"
                )
            elif drift > 2.0:
                ok = False
                notes.append(
                    f"FAIL: B[{flow_name}] (bugs/0612/0614): same-camera {flow_name} moved the "
                    f"body {drift:.1f} mm relative to its sensor (want a no-op within 2 mm)"
                )
            else:
                notes.append(
                    f"PASS: B[{flow_name}]: same-camera {flow_name} preserves the body-to-sensor "
                    f"vector (drift {drift:.2f} mm, same side)"
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
