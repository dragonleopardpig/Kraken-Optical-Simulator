"""Guard for bugs/0570 -- on a coaxial LED+BS scene the beam splitter's REFLECT branch is the
imaging axis, so everything on it is on-beam, and the glued splitter must not slide when the
object distance changes.

Three flags, one afternoon, one root cause chain (machine_vision_Pyrite85_BS):

* flag_20260806_102150 "solve FOV partialy works, rays still defocus at sensor."
* flag_20260806_102258 "right click defocus not working."
* "the BS plate is shifted down. It happened after FOV solve."

``offbeam_free_placed_mirror_row_indices`` walked ONE leg from the straight global +Z and bent
it only at Mirror faces.  A splitter carries a full beam on its reflect branch, and on this
scene that branch IS the imaging axis (``axis:global:split``, +X at z=82.7), so the in-path RA
mirror at x=193 read as "parked clear" 193 mm off the +Z leg.  bugs/0224 then treats an off-beam
mirror as optically inert and ZEROES its row in the straight equivalent -- and that row is the
mirror->sensor gap.  With the image leg gone, ``_real_ray_best_focus_shift_for_rows`` returned
the same 54.593 mm with the sensor 40 mm nearer, unmoved, or 40 mm further: a number that cannot
be a residual.  Everything built on it then failed the way the user saw --
``snap_detector_to_image_plane``'s adaptive loop walked the sensor around for 5 iterations and
stopped wherever it happened to be, and the FOV solve's finisher (bugs/0490) could not land the
focus either.

Separately, the object-side write slid the glued splitter: ``_object_locked_redirect_row`` finds
the illumination unit POSITIONALLY (the row after the object gap) and bugs/0546 established that
a promoted solid's row index is not its geometry -- here the BS is glued to the LED, physically
upstream, with its row at index 6, after the whole lens block.  So the delta went into row 0 and
every WORLD-placed row slid with it while the LED body (an overlay at an absolute offset) stayed.

Checks:
- A PURE (always runs): the splitter-face normal reader; the off-beam walk follows the reflect
  branch (fail-before: the same scene without the splitter marker still calls it off-beam), a
  genuinely parked mirror is still off-beam (bugs/0224 intact), and the illumination unit is
  found by MARKER at any row index, with the hold cancelling an object slide exactly.
- B REAL SCENE (skip-if-absent, needs Tk/Xvfb): on the user's saved layout the RA mirror is not
  off-beam; the best-focus measure RESPONDS to the sensor (1 mm per mm, the property that makes
  it a residual); the snap moves the sensor and leaves a small residual; and a 30x30 solve keeps
  the splitter in its housing while the lens moves.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0570_bs_branch_reaches_the_mirror
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"

FLAG_BS_ROW = 6
FLAG_MIRROR_ROW = 7
FLAG_IMAGE_ROW = 8


def _solid_spec(*, name, function, normal, tilt=(0.0, 0.0, 0.0), desp=(0.0, 0.0, 0.0),
                thickness=0.0, diameter=50.0):
    """A promoted-solid spec as ``_serializable_specs_for_rows`` renders one."""
    return {
        "surface": "Standard",
        "name": name,
        "thickness": float(thickness),
        "diameter": float(diameter),
        "glass": "BK7",
        "tilt_x": float(tilt[0]), "tilt_y": float(tilt[1]), "tilt_z": float(tilt[2]),
        "desp_x": float(desp[0]), "desp_y": float(desp[1]), "desp_z": float(desp[2]),
        "axis_move": 0.0,
        "advanced": {
            "Solid_3d_stl": "/tmp/stub.stl",
            "OpticalSolidFaces": {
                "version": 1,
                "faces": [{
                    "face_id": "S001/F001",
                    "function": function,
                    "role": function,
                    "normal": [float(v) for v in normal],
                    "centroid": [0.0, 0.0, 0.0],
                }],
            },
            "StepOverlayPromotion": {"step_label": "optical"},
        },
    }


def _check_pure(ok, notes) -> None:
    from KrakenOS.UI.services.folded_sequential_fold import (
        offbeam_free_placed_mirror_row_indices,
        splitter_fold_face_normal,
    )

    # A 45-degree splitter turns the +Z beam onto +X; the mirror sits on that branch at
    # x = 200.  ``promoted_mirror_world_center`` puts both at z = 100 (the object gap), and the
    # splitter normal is the one that reflects (0,0,1) onto (1,0,0).
    splitter = _solid_spec(
        name="Promoted OPTICAL STEP optical solid", function="Beam Splitter",
        normal=[np.sqrt(0.5), 0.0, -np.sqrt(0.5)], desp=(0.0, 0.0, 0.0), diameter=77.0,
    )
    on_branch_mirror = _solid_spec(
        name="Promoted OPTICAL STEP optical solid", function="Mirror",
        normal=[-np.sqrt(0.5), 0.0, np.sqrt(0.5)], desp=(200.0, 0.0, 0.0), diameter=25.0,
    )
    parked_mirror = _solid_spec(
        name="Promoted OPTICAL STEP optical solid", function="Mirror",
        normal=[-np.sqrt(0.5), 0.0, np.sqrt(0.5)], desp=(0.0, 400.0, 0.0), diameter=25.0,
    )
    object_spec = {"surface": "Object", "name": "Object", "thickness": 100.0, "diameter": 10.0,
                   "glass": "AIR", "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
                   "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0, "advanced": {}}
    image_spec = dict(object_spec, surface="Image", name="Image", thickness=0.0)

    ok(
        splitter_fold_face_normal(splitter["advanced"]) is not None
        and splitter_fold_face_normal(on_branch_mirror["advanced"]) is None,
        "A1: the splitter-face normal reader finds a Beam Splitter face and ignores a Mirror one",
    )

    specs = [object_spec, splitter, on_branch_mirror, image_spec]
    offbeam = offbeam_free_placed_mirror_row_indices(specs)
    ok(
        2 not in offbeam,
        f"A2 (the fix): a mirror on the SPLITTER'S REFLECT BRANCH is on-beam (off-beam={sorted(offbeam)})",
    )

    # FAIL-BEFORE: strip the splitter marker and the same geometry reads as parked -- which is
    # exactly what the shipped walk did for every beam-splitter scene.
    blind = [dict(s) for s in specs]
    blind[1] = dict(splitter)
    blind[1]["advanced"] = {"Solid_3d_stl": "/tmp/stub.stl", "StepOverlayPromotion": {"step_label": "optical"}}
    ok(
        2 in offbeam_free_placed_mirror_row_indices(blind),
        "A3 (fail-before): with no splitter face to bend at, that same mirror reads as parked "
        "clear -- the bug this guard pins",
    )

    ok(
        2 in offbeam_free_placed_mirror_row_indices([object_spec, splitter, parked_mirror, image_spec]),
        "A4 (bugs/0224 intact): a mirror parked 400 mm off every branch is still off-beam",
    )

    # The illumination unit: found by MARKER at any row index, and held across an object slide.
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, thickness=0.0, promotion=None, desp_z=0.0):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_z = float(desp_z)
        row.axis_move = 0.0
        if promotion is not None:
            row.advanced = {"StepOverlayPromotion": promotion}
        return row

    rows = [
        _row("Object at 1X", 147.432),
        _row("Front Optical Vertex Datum", 1.823),
        _row("Rear Optical Vertex Datum", 93.865),
        _row("Promoted OPTICAL STEP optical solid", 0.0,
             {"step_label": "optical", "station_neutral": True, "beam_splitter": True}, desp_z=-197.896),
        _row("Promoted OPTICAL STEP optical solid", 58.924, {"step_label": "optical"}, desp_z=-198.072),
        _row("Image / Sensor at 1X"),
    ]
    editor = SimpleNamespace(
        rows=rows,
        _optical_led_glued=True,
        _step_path_for_label=lambda label: Path("/tmp/led.step") if label == "led" else None,
    )
    qe = QuickEstimationService(SimpleNamespace(editor=editor))
    ok(
        qe._glued_illumination_unit_rows() == [3],
        f"A5: the glued LED+BS unit is found by MARKER at its real row index "
        f"(got {qe._glued_illumination_unit_rows()}, want [3]) -- not by 'the row after the "
        f"object gap', which bugs/0546 makes meaningless",
    )
    before = float(rows[3].desp_z)
    held = qe._hold_glued_illumination_unit(rows, 25.864)
    ok(
        held == [3] and abs((float(rows[3].desp_z) - before) + 25.864) < 1e-9,
        f"A6: holding it cancels the object slide exactly (desp_z {before:.3f} -> "
        f"{float(rows[3].desp_z):.3f} for a +25.864 mm slide)",
    )


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: machine_vision_Pyrite85_BS.py is not in this checkout (gitignored)")
        return
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import row_placement
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: the editor could not be imported ({type(exc).__name__}: {exc})")
        return

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")
        if len(editor.rows) <= FLAG_IMAGE_ROW:
            notes.append("SKIP: the layout no longer has the flagged row structure")
            return

        offbeam = editor._offbeam_promoted_mirror_rows(editor.rows)
        ok(
            FLAG_MIRROR_ROW not in offbeam,
            f"B1 (the root cause): the in-path RA mirror is NOT read as parked clear "
            f"(off-beam={sorted(offbeam)})",
        )

        # The property that makes the measure a RESIDUAL: it must follow the sensor.
        base_gap = float(editor.rows[FLAG_MIRROR_ROW].thickness)
        first = editor._real_ray_best_focus_shift_for_rows()
        editor.rows[FLAG_MIRROR_ROW].thickness = base_gap + 40.0
        second = editor._real_ray_best_focus_shift_for_rows()
        editor.rows[FLAG_MIRROR_ROW].thickness = base_gap
        ok(
            first is not None and second is not None and abs((float(first) - float(second)) - 40.0) < 0.5,
            f"B2: the best-focus measure FOLLOWS the sensor -- {first} at the current gap, "
            f"{second} 40 mm along it (it returned the identical number at every position "
            f"before, which is why the snap could never converge)",
        )

        sensor_before = np.asarray(row_placement.world_pose(editor, FLAG_IMAGE_ROW).position, dtype=float)
        moved = bool(editor.snap_detector_to_image_plane())
        sensor_after = np.asarray(row_placement.world_pose(editor, FLAG_IMAGE_ROW).position, dtype=float)
        residual = editor._real_ray_best_focus_shift_for_rows()
        ok(
            moved and float(np.linalg.norm(sensor_after - sensor_before)) > 0.5,
            f"B3 (right-click 'remove defocus'): the snap moves the sensor "
            f"({float(np.linalg.norm(sensor_after - sensor_before)):.3f} mm) instead of refusing",
        )
        ok(
            residual is not None and abs(float(residual)) <= 0.5,
            f"B4: ... and lands it AT best focus (residual {residual} mm)",
        )

        # The object side: the glued splitter stays in its housing while the lens moves.
        editor.load_layout_by_name("probe")
        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        pose = lambda i: np.asarray(row_placement.world_pose(editor, i).position, dtype=float)
        bs_before, lens_before = pose(FLAG_BS_ROW), pose(1)
        solved, message = qe.fov_solve("object", "thickness", 30.0, 30.0)
        bs_after, lens_after = pose(FLAG_BS_ROW), pose(1)
        ok(
            bool(solved) and float(np.linalg.norm(bs_after - bs_before)) < 1e-6,
            f"B5 (the report): a 30x30 solve leaves the glued beam splitter exactly where it is "
            f"({float(np.linalg.norm(bs_after - bs_before)):.4f} mm; it slid 28.5 mm before)",
        )
        ok(
            float(np.linalg.norm(lens_after - lens_before)) > 1.0,
            f"B6 (non-vacuity): ... because the LENS moved instead "
            f"({float(np.linalg.norm(lens_after - lens_before)):.3f} mm) -- {message[-60:]}",
        )
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_pure), ("B", _check_real_scene)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("BS-branch on-beam / illumination-hold validation passed.")
        return 0
    print("BS-branch on-beam / illumination-hold validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
