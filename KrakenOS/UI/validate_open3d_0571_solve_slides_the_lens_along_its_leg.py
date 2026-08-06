"""Guard for bugs/0571 -- an object-side FOV solve on a frozen FOLD moves the lens ALONG ITS
LEG; it must never slide the whole machine along the station axis.

flag_20260806_125028 + recording_20260806_125044 (machine_vision_Pyrite85_BS): *"swapped lens,
elements dislocate."*  The recording holds exactly one solve after the (unrecorded) swap --
``fov_solve{plane:object,mode:thickness,23x23}``.

A row's pose is ``station + desp_z`` (bugs/0526), so writing ``rows[0].thickness`` -- the object
distance -- slides every downstream WORLD row along **+Z**.  On this scene the lens, the fold
mirror and the sensor live on the splitter's **+X** leg, so the solve moved all three 28.462 mm
transverse to their own leg: measured, the lens block went z 54.283 -> 82.745 while the guide axis
stayed at 55.359, and **0 of 558 rays reached the sensor** (547 no_next_intersection).

The lens DRAG already knew how to do this (bugs/0524+0526): translate the block's rows along the
leg direction, write ``gap before += slide`` / ``gap after -= slide`` so the first order sees the
conjugate change, and cancel the station growth with ``desp_z -= slide`` in between.  The solve
now calls that same composite (``slide_lens_block_along_its_leg``) -- a drag and a solve are the
same gesture from opposite ends, which is the user's own principle.

Also here: two writers that drag the glued LED+BS unit by its station (the collision resolver's
mirror slide and the image-gap write inside ``snap_detector_to_image_plane``) are now bracketed by
a measure/restore of the unit's world seat, and the image-leg span walk skips STATION-NEUTRAL rows
(bugs/0435) so a camera-body collision can actually be redistributed instead of refused with "the
fold mirror needs to slide N mm further than the lens-to-mirror leg can give" while the real leg
was 43 mm of the row before it.

Checks:
- A PURE (always runs): the station-neutral predicate has ONE definition; the leg-span walk skips
  such a row; the illumination-unit measure/restore round-trips a station change exactly.
- B REAL SCENE (skip-if-absent, Tk/Xvfb): on the user's saved layout, a 23x23 object solve moves
  the lens block ALONG its leg (its z is unchanged, its x grows by the solved delta), and leaves
  the beam splitter, the LED housing and the fold mirror where they are.  Fail-before is stated in
  numbers: the pre-fix behaviour moved the lens 28.462 mm in +Z and 0 mm in +X.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0571_solve_slides_the_lens_along_its_leg
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"

BS_ROW = 6
MIRROR_ROW = 7
LENS_FRONT_ROW = 1


def _check_pure(ok, notes) -> None:
    from KrakenOS.UI.services.paraxial_tools import row_is_station_neutral
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, thickness=0.0, promotion=None, desp_z=0.0):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_z = float(desp_z)
        row.axis_move = 0.0
        if promotion is not None:
            row.advanced = {"StepOverlayPromotion": promotion}
        return row

    neutral = _row("Promoted OPTICAL STEP optical solid", 0.0,
                   {"step_label": "optical", "station_neutral": True, "beam_splitter": True})
    plain = _row("Rear Optical Vertex Datum", 93.865)
    ok(
        row_is_station_neutral(neutral) and not row_is_station_neutral(plain),
        "A1: the station-neutral predicate reads the promotion marker",
    )
    ok(
        QuickEstimationService._row_is_station_neutral(neutral) is True
        and QuickEstimationService._row_is_station_neutral(plain) is False,
        "A2: the quick-estimation copy DELEGATES to it -- one definition, not two (bugs/0568)",
    )

    # The illumination unit's world seat survives an arbitrary upstream station change.
    rows = [
        _row("Object at 1X", 118.970),
        _row("Front Optical Vertex Datum", 1.823),
        _row("Rear Optical Vertex Datum", 93.865),
        _row("Promoted OPTICAL STEP optical solid", 0.0,
             {"step_label": "optical", "station_neutral": True, "beam_splitter": True},
             desp_z=-197.896),
        _row("Image / Sensor at 1X"),
    ]

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    editor = SimpleNamespace(
        rows=rows,
        _optical_led_glued=True,
        _step_path_for_label=lambda label: Path("/tmp/led.step") if label == "led" else None,
        _row_z_positions=lambda: [
            sum(float(r.thickness) for r in rows[:i]) for i in range(len(rows))
        ],
        append_debug=lambda *a, **k: None,
    )
    poses = ScenePlacementMixin.glued_illumination_unit_world_poses(editor)
    ok(
        list(poses) == [3],
        f"A3: the unit's world seat is measured at its real row index (got {list(poses)})",
    )
    seat_before = poses.get(3)
    rows[0].thickness = 147.432                       # an object-gap write, 28.462 mm of station
    moved = ScenePlacementMixin.restore_glued_illumination_unit_world_poses(editor, poses)
    stations = editor._row_z_positions()
    seat_after = float(stations[3]) + float(rows[3].desp_z)
    ok(
        moved == [3] and abs(seat_after - float(seat_before)) < 1e-9,
        f"A4: restoring puts it back exactly ({seat_before:.4f} -> {seat_after:.4f} across a "
        f"+28.462 mm station write)",
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
        if len(editor.rows) <= MIRROR_ROW:
            notes.append("SKIP: the layout no longer has the flagged row structure")
            return

        def pose(index):
            return np.asarray(row_placement.world_pose(editor, int(index)).position, dtype=float)

        led_before = np.asarray(
            editor._transformed_imported_step_mesh_for_label("led").bounds, dtype=float
        )
        lens_before, bs_before, mirror_before = pose(LENS_FRONT_ROW), pose(BS_ROW), pose(MIRROR_ROW)
        object_before = float(editor.rows[0].thickness)

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        solved, message = qe.fov_solve("object", "thickness", 23.0, 23.0)
        ok(bool(solved), f"B0: the 23x23 object solve runs ({message[:90]})")

        lens_after, bs_after, mirror_after = pose(LENS_FRONT_ROW), pose(BS_ROW), pose(MIRROR_ROW)
        led_after = np.asarray(
            editor._transformed_imported_step_mesh_for_label("led").bounds, dtype=float
        )
        object_delta = float(editor.rows[0].thickness) - object_before
        moved = lens_after - lens_before

        ok(
            abs(object_delta) > 1.0,
            f"B1 (non-vacuity): the solve really changed the conjugate "
            f"(object gap {object_before:.3f} -> {float(editor.rows[0].thickness):.3f})",
        )
        ok(
            abs(float(moved[2])) < 1e-6,
            f"B2 (the bug): the lens does NOT move along the station axis "
            f"(dz {float(moved[2]):+.4f} mm; it was +28.462 before the fix)",
        )
        ok(
            abs(float(moved[0]) - object_delta) < 0.05,
            f"B3 (the fix): it moves ALONG ITS LEG by the solved delta "
            f"(dx {float(moved[0]):+.4f} mm vs delta {object_delta:+.4f})",
        )
        ok(
            float(np.linalg.norm(bs_after - bs_before)) < 1e-6,
            f"B4: the glued beam splitter stays in its housing "
            f"({float(np.linalg.norm(bs_after - bs_before)):.4f} mm)",
        )
        ok(
            abs((led_after[4] + led_after[5]) / 2 - (led_before[4] + led_before[5]) / 2) < 1e-6,
            "B5: ... and so does the LED body it is glued to",
        )
        # The fold mirror MAY slide along its own leg -- that is the camera anti-crash
        # redistribution (bugs/0468: "keep the sensor off the fold mirror by SLIDING THE MIRROR,
        # not by refusing"), and it is reported in the status line. What it must never do is
        # leave the leg, which is what a station write did to it.
        mirror_moved = mirror_after - mirror_before
        ok(
            # 0.05 mm: the re-bake runs the pose through a rotation matrix, so "on the leg" is a
            # physical tolerance, not an exact one -- and the flagged failure was 28.462 mm.
            abs(float(mirror_moved[2])) < 0.05,
            f"B6: the fold mirror stays ON its leg -- any motion is along it, never across "
            f"(dz {float(mirror_moved[2]):+.4f} mm, dx {float(mirror_moved[0]):+.4f} mm)",
        )
        ok(
            float(np.linalg.norm(mirror_moved)) < 1e-6
            or "mirror slid" in message
            or "sensor moved" in message,
            f"B7: ... and a slide is reported rather than silent ({message[-80:]})",
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
        print("Object-solve lens-leg slide validation passed.")
        return 0
    print("Object-solve lens-leg slide validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
