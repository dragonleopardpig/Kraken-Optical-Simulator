"""Guard for bugs/0594 -- a lens swap may never leave the camera INSIDE the fold solid.

Flag `flag_20260809_102408_191`: *"swapped a few times with different lens, final swap crash the
camera."* On the frozen, folded ELS-85 scene the detector -- and the camera body glued to it --
ended up inside the right-angle fold prism (recorded sensor world z 49.711, prism z span
41.645..67.071).

The mechanism, established from two recordings and reproduced here by construction: on a frozen
fold the image gap runs BACKWARDS (`world leg = const - thickness`, bugs/0478), so a large booked
thickness COLLAPSES the world leg. Setting the recorded thickness of 125.5793 mm on the as-loaded
scene lands the sensor at world z 49.711 -- the recorded value to the millimetre.

What let it survive: `_swap_auto_refocus_to_best_focus` returned EARLY when
`snap_detector_to_image_plane` refused, skipping BOTH clearance layers. The refusal is a real and
documented outcome (bugs/0566/0575/0577), so the clearance guarantee was conditional on best focus
being reachable -- and a refused refocus left the camera wherever it already was, silently.

Checks:
  A  FIXTURE  -- the recorded thickness reproduces the flagged collision (non-vacuity: if this
                 stops colliding, B proves nothing).
  B  REAL     -- with the refocus REFUSED, the sensor must end up OUT of the fold solid.
  C  REPORT   -- both channels speak: `_swap_refocus_note` carries the refusal, and
                 `_swap_clearance_note` says what the clearance did. A silent correction is
                 nearly as bad as none.
  D  CONTRACT -- the gap writer keys on `_frozen_image_write_refusal` (its own docstring: "the
                 caller keys on the string, never on the bool alone"), and the swap appends
                 `_swap_clearance_note` to the status the user actually sees.
  E  MATRIX   -- across a sequence of real lens swaps the sensor never lands inside the fold
                 solid. This is the door-independent statement; the user hit it on the "final"
                 swap of several.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0594_refused_refocus_still_clears_the_camera
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_ELS85.py"
LENS_DIR = PROJECT_ROOT / "attachment" / "Lens"
SWAP_SEQUENCE = [
    "ELS-85-4.5V16K",
    "PYRITE_56_120_10x_V38_1097277",
    "0703-005-000-40-EXC",
    "PYRITE_45_85_05x-20x_V38_1072517",
]

# The thickness recorded in the flag (pre-0647 scene numbers; the fixture now CONSTRUCTS
# the collision from the live geometry -- these are kept for the report only).
CRASH_THICKNESS_MM = 125.5793
CRASH_SENSOR_Z = 49.711
SENSOR_Z_TOL_MM = 0.05


def _sensor_inside_fold_solid(app):
    """(inside, sensor_world, solid_bounds) for the final image row vs the upstream promoted
    solid. Bodies, not rays: a ray-level check passes straight through an interpenetration."""
    rows = app.rows
    n = len(rows)
    centre = np.asarray(app._split_row_world_center(n - 1), dtype=float)
    bounds = app._promoted_solid_world_bounds(rows[n - 2], row_index=n - 2)
    if bounds is None or not np.all(np.isfinite(centre)):
        return None, centre, bounds
    inside = (
        bounds[0] - 1e-9 <= centre[0] <= bounds[1] + 1e-9
        and bounds[2] - 1e-9 <= centre[1] <= bounds[3] + 1e-9
        and bounds[4] - 1e-9 <= centre[2] <= bounds[5] + 1e-9
    )
    return bool(inside), centre, bounds


def run_checks():
    notes: list[str] = []
    ok = True
    if not SCENE.exists():
        notes.append(f"SKIP: fixture scene missing ({SCENE})")
        return True, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import layout_table_workbench as workbench_module

    # ---- D: source contracts (cheap, and independent of the fixture) -------------------
    src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin._swap_auto_refocus_to_best_focus)
    if "_frozen_image_write_refusal" not in src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0594): the swap refocus ignores _frozen_image_write_refusal -- a "
            "refused clearance write would be reported as a successful one"
        )
    else:
        notes.append("PASS: D1: the swap refocus keys on the frozen-write refusal string")
    # Read CODE, not prose: the fix's own comment contains the word "return", so a raw substring
    # test fires on the explanation of the fix. Strip comment lines first.
    _refused_block = src.split("if not moved:")[-1].split("# bugs/0578")[0]
    _refused_code = [
        line.strip()
        for line in _refused_block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if any(line == "return" or line.startswith("return ") for line in _refused_code):
        ok = False
        notes.append(
            "FAIL: D (bugs/0594): a refused refocus still RETURNS before the clearance layers"
        )
    else:
        notes.append("PASS: D2: a refused refocus falls through to the clearance layers")
    swap_src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    if "_swap_clearance_note" not in swap_src:
        ok = False
        notes.append(
            "FAIL: D (bugs/0594): the swap never surfaces _swap_clearance_note, so the clearance "
            "result cannot reach the user (its old status_var.set was overwritten by the caller)"
        )
    else:
        notes.append("PASS: D3: the swap appends the clearance note to its status message")

    app = None
    try:
        app = KrakenLayoutEditor()
        app.layout_files["_0594"] = SCENE
        app.load_layout_by_name("_0594")
        rows = app.rows
        n = len(rows)

        # ---- A: the fixture really is the flagged collision --------------------------
        # The collision is CONSTRUCTED from the scene's own geometry, not from the
        # recorded thickness: the image gap on this frozen fold runs backwards
        # (world leg = const - thickness, bugs/0478), so the sensor position is LINEAR
        # in the booked thickness -- measure it at two thicknesses and solve for the one
        # that lands the sensor on the fold solid's centre. The recorded 125.5793 mm
        # only collided on the scene numbers of the day; the bugs/0647 datasheet refit
        # re-baked machine_vision_ELS85.py and that fixed number then landed the sensor
        # 100 mm past the prism (phase 452 PASS->FAIL with no code change).
        inside0, centre0, bounds = _sensor_inside_fold_solid(app)
        if inside0 is None:
            notes.append("SKIP: A: fold-solid bounds unavailable on this scene")
            return ok, notes
        t0 = float(rows[n - 2].thickness)
        rows[n - 2].thickness = t0 + 10.0
        _, centre1, _ = _sensor_inside_fold_solid(app)
        slope = (np.asarray(centre1, dtype=float) - np.asarray(centre0, dtype=float)) / 10.0
        target = np.array(
            [(bounds[0] + bounds[1]) / 2.0, (bounds[2] + bounds[3]) / 2.0,
             (bounds[4] + bounds[5]) / 2.0]
        )
        if float(np.dot(slope, slope)) < 1e-12:
            ok = False
            notes.append("FAIL: A (fixture): the booked thickness does not move the sensor at all")
            return ok, notes
        crash_thickness = t0 + float(np.dot(target - np.asarray(centre0, dtype=float), slope)) / float(
            np.dot(slope, slope)
        )
        rows[n - 2].thickness = crash_thickness
        inside, centre, bounds = _sensor_inside_fold_solid(app)
        if not inside:
            ok = False
            notes.append(
                f"FAIL: A (non-vacuity): the constructed thickness {crash_thickness:.4f} mm does "
                f"not put the sensor inside the fold solid (sensor z {centre[2]:.3f}, solid z "
                f"{bounds[4]:.3f}..{bounds[5]:.3f}) -- B would prove nothing"
            )
            return ok, notes
        notes.append(
            f"PASS: A: a constructed thickness of {crash_thickness:.3f} mm reproduces the flagged "
            f"collision (sensor z {centre[2]:.3f} inside the fold solid {bounds[4]:.3f}.."
            f"{bounds[5]:.3f}; the flag recorded {CRASH_THICKNESS_MM} mm -> z {CRASH_SENSOR_Z} "
            f"on the pre-0647 scene)"
        )

        # ---- B/C: a REFUSED refocus must still clear the camera, and say so ----------
        app.snap_detector_to_image_plane = lambda *a, **k: False
        app.__dict__["_snap_detector_refusal"] = "best focus needs more leg than this fold has"
        app._swap_auto_refocus_to_best_focus()

        inside_after, centre_after, bounds_after = _sensor_inside_fold_solid(app)
        if inside_after:
            ok = False
            notes.append(
                f"FAIL: B (bugs/0594): after a REFUSED refocus the sensor is still INSIDE the "
                f"fold solid (z {centre_after[2]:.3f} within {bounds_after[4]:.3f}.."
                f"{bounds_after[5]:.3f}) -- the clearance layers were skipped"
            )
        else:
            notes.append(
                f"PASS: B: a refused refocus still moved the camera clear (sensor z "
                f"{centre_after[2]:.3f}, fold solid {bounds_after[4]:.3f}..{bounds_after[5]:.3f})"
            )

        refocus_note = str(app.__dict__.get("_swap_refocus_note", "") or "")
        clearance_note = str(app.__dict__.get("_swap_clearance_note", "") or "")
        if not refocus_note:
            ok = False
            notes.append("FAIL: C: the refusal reason was dropped (_swap_refocus_note empty)")
        elif not clearance_note:
            ok = False
            notes.append(
                "FAIL: C: the camera was moved but _swap_clearance_note is empty -- a silent "
                "correction leaves the user believing nothing happened"
            )
        else:
            notes.append(f"PASS: C: both channels report ({refocus_note!r} / {clearance_note!r})")

        # ---- E: the invariant across a real swap sequence -----------------------------
        # Reuse the SAME app (one Tk/VTK app per process -- a second instance, or one built
        # after a destroy(), reads as "the product cannot import"). Reload the scene and drop
        # the instance-level refusal stub so the real refocus runs.
        app.__dict__.pop("snap_detector_to_image_plane", None)
        app.__dict__.pop("_snap_detector_refusal", None)
        app.load_layout_by_name("_0594")
        checked = 0
        for name in SWAP_SEQUENCE:
            folder = LENS_DIR / name
            if not folder.exists():
                continue
            try:
                app.swap_imaging_lens_from_folder(str(folder), refresh=False)
            except Exception as exc:
                notes.append(f"NOTE: E: swap {name} raised {type(exc).__name__}: {exc}")
                continue
            checked += 1
            bad, centre_e, bounds_e = _sensor_inside_fold_solid(app)
            if bad:
                ok = False
                notes.append(
                    f"FAIL: E (bugs/0594): after swapping {name} the sensor is INSIDE the "
                    f"fold solid (z {centre_e[2]:.3f} within {bounds_e[4]:.3f}.."
                    f"{bounds_e[5]:.3f})"
                )
                break
        if checked == 0:
            notes.append("SKIP: E: no lens folders from the sequence are present")
        elif ok:
            notes.append(
                f"PASS: E: the sensor stayed clear of the fold solid across {checked} real "
                "lens swaps"
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
    print("Refused-refocus camera-clearance validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
