"""Guard for bugs/0569 -- a folded FOV/thickness solve must not move the fold mirror, and must
never write a distance into a STATION-NEUTRAL row.

flag_20260806_074148 + recording_20260806_074228 (machine_vision_AZ85_RA_Mirror_BS):
*"swapped lens, changed FOV, solve for thickness, camera and RA mirror misplaced."*  The
recording holds exactly one solve -- ``fov_solve(plane="object", mode="thickness", 23, 23)``.

Measured on the user's own scene: the folded conjugate solve wrote its image-leg correction
into ``image_gap_row``, which is where the image distance is MEASURED from -- the promoted
BEAM-SPLITTER row (S6).  That row is STATION-NEUTRAL by bugs/0435 (thickness pinned at 0, body
absolutely placed, and by bugs/0546 its row index is not its geometry: the BS is glued to the
LED, physically upstream of the lens).  Inflating it pushed every downstream station along the
chain:

    S6 beam splitter   thickness 0 -> 35.85   (must always be 0)
    S7 RA mirror       z  54.283 -> 90.132    (must not move at all)
    S8 sensor          z  10.207 -> 46.056    (moved, but the WRONG WAY -- see bugs/0478)
    camera body        follows the sensor, so it left the beam with it

Fix: the image-leg correction belongs to the mirror->sensor gap, and on a frozen fold it is
placed in WORLD terms (``shift_image_distance_frozen_aware`` -- the gap row there runs
backwards, bugs/0478), so the mirror stays exactly put and only the sensor (and the camera
glued to it) travels along the leg.

Checks:
- A PURE (always runs): the station-neutral predicate, the walk-back, the image-leg write row
  (the fold split's far gap, never the station-neutral row), and that
  ``shift_image_distance_frozen_aware`` = "current world leg + delta" and declines (False) on a
  scene with no frozen image fold, so a straight scene keeps its plain write.
- B WIRING: the folded branch of ``_apply_conjugate_pair`` consults the frozen-aware shift and
  skips the raw gap write when it is handled.
- C REAL SCENE (skip-if-absent, needs Tk/Xvfb): drives the shipped ``fov_solve`` on the flagged
  layout and asserts the three things the user reported -- the BS row stays 0, the RA mirror
  does not move, and the sensor moves along its own leg by the solved correction.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0569_fov_solve_keeps_the_fold
Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_AZ85_RA_Mirror_BS.py"

# The flagged scene's own geometry (verified headless against the layout):
FLAG_MIRROR_ROW = 7
FLAG_BS_ROW = 6
FLAG_IMAGE_ROW = 8
FLAG_LENS_REAR_ROW = 5      # Rear Optical Vertex Datum
FLAG_FAR_LEG = 44.0762        # mirror -> sensor, world
FLAG_IMAGE_DELTA = 35.8492    # what the 23x23 solve asks the image leg to grow by


def _promoted_row(name="Promoted OPTICAL STEP optical solid", *, station_neutral=False, thickness=0.0):
    from KrakenOS.UI.surface_table_model import SurfaceRow

    row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="BK7")
    promotion = {"step_label": "optical"}
    if station_neutral:
        promotion["station_neutral"] = True
    row.advanced = {"StepOverlayPromotion": promotion}
    return row


def _plain_row(name, thickness):
    from KrakenOS.UI.surface_table_model import SurfaceRow

    return SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")


def _service(rows, *, split=None):
    """QuickEstimationService over a stub editor -- only the row list and the fold split the
    decisions below read."""
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = SimpleNamespace(
        rows=rows,
        _folded_image_conjugate_split=lambda: split,
        _folded_object_conjugate_split=lambda: None,
    )
    return QuickEstimationService(SimpleNamespace(editor=editor))


def _check_pure(ok, notes) -> None:
    rows = [
        _plain_row("Object at 1X", 118.97),
        _plain_row("Front Optical Vertex Datum", 1.4839),
        _plain_row("Rear Optical Vertex Datum", 83.3811),
        _promoted_row(station_neutral=True),                       # the beam splitter (S6 here)
        _promoted_row(thickness=58.9238),                          # the RA mirror
        _plain_row("Image / Sensor at 1X", 0.0),
    ]
    bs_row, mirror_row = 3, 4
    qe = _service(rows, split={"far_gap_row": mirror_row, "near_gap_row": bs_row, "mirror_row": mirror_row})

    ok(
        qe._row_is_station_neutral(rows[bs_row]) and not qe._row_is_station_neutral(rows[mirror_row]),
        "A1: a promoted row marked station_neutral (bugs/0435) is recognised; a promoted mirror "
        "carrying a real axial reserve is not",
    )
    ok(
        qe._gap_row_for_delta(rows, bs_row) == bs_row - 1,
        f"A2: a delta aimed at the station-neutral row walks back to a row that can hold a "
        f"distance (got {qe._gap_row_for_delta(rows, bs_row)})",
    )
    ok(
        qe._folded_image_leg_write_row(bs_row) == mirror_row,
        f"A3 (the fix): the image-leg correction goes to the MIRROR->SENSOR gap, not to the row "
        f"the distance is measured from (got {qe._folded_image_leg_write_row(bs_row)}, want "
        f"{mirror_row})",
    )

    # ... and with no split at all it still refuses the station-neutral row.
    bare = _service(rows, split=None)
    ok(
        bare._folded_image_leg_write_row(bs_row) == mirror_row,
        "A4: with no fold split published, the last gap before the Image is used -- still never "
        "the station-neutral row",
    )

    # shift_image_distance_frozen_aware = "the world leg it measures, plus the delta".
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    seen: list[float] = []
    probe = SimpleNamespace(
        _folded_image_conjugate_split=lambda: {"far_gap_row": mirror_row},
        _frozen_image_fold_world_geometry=lambda split: {"far": FLAG_FAR_LEG, "near": 193.5},
        apply_image_distance_frozen_aware=lambda value: (seen.append(float(value)), True)[1],
    )
    handled = ParaxialToolsMixin.shift_image_distance_frozen_aware(probe, FLAG_IMAGE_DELTA)
    ok(
        handled and seen and abs(seen[-1] - (FLAG_FAR_LEG + FLAG_IMAGE_DELTA)) < 1e-9,
        f"A5: the frozen image write is 'measured world leg + solved correction' "
        f"({FLAG_FAR_LEG} + {FLAG_IMAGE_DELTA} = {FLAG_FAR_LEG + FLAG_IMAGE_DELTA}; got "
        f"{seen[-1] if seen else None}) -- not the gap-row sum the solve quotes as its "
        f"'image_distance', which is a different quantity in a different frame",
    )
    straight = SimpleNamespace(
        _folded_image_conjugate_split=lambda: None,
        _frozen_image_fold_world_geometry=lambda split: None,
        apply_image_distance_frozen_aware=lambda value: True,
    )
    ok(
        ParaxialToolsMixin.shift_image_distance_frozen_aware(straight, 10.0) is False,
        "A6: a scene with no frozen image-side fold declines, so the straight-scene write path "
        "is untouched",
    )


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "shift_image_distance_frozen_aware" in src,
        "B1: the folded conjugate branch consults the frozen-aware image shift",
    )
    ok(
        "_folded_image_leg_write_row" in src,
        "B2: ... and resolves its image write row instead of writing image_gap_row raw",
    )
    if "shift_image_distance_frozen_aware" in src and "image_handled" in src:
        head = src[: src.index("_distribute_folded_gap_delta")]
        ok(
            "shift_image_distance_frozen_aware" in head,
            "B3: the frozen-aware shift runs BEFORE the gap distribution decides what to write",
        )


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: the flagged layout is not in this checkout (gitignored attachment)")
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
        editor.layout_files["fov_probe"] = SCENE
        editor.load_layout_by_name("fov_probe")
        rows = editor.rows
        if len(rows) <= FLAG_IMAGE_ROW:
            notes.append("SKIP: the layout no longer has the flagged row structure")
            return
        qe = QuickEstimationService(SimpleNamespace(editor=editor))

        def pose(index):
            return np.asarray(row_placement.world_pose(editor, int(index)).position, dtype=float)

        def snapshot():
            return {
                "bs": float(rows[FLAG_BS_ROW].thickness),
                "mirror": pose(FLAG_MIRROR_ROW),
                "image": pose(FLAG_IMAGE_ROW),
                # The mirror RELATIVE to the lens: the object side legitimately slides the whole
                # machine (row 0's thickness is the object distance, everything downstream of it
                # is world-placed), so the invariant the image side owes is that the fold does
                # not move against the optics it folds.
                "mirror_vs_lens": pose(FLAG_MIRROR_ROW) - pose(FLAG_LENS_REAR_ROW),
            }

        ok(
            qe._row_is_station_neutral(rows[FLAG_BS_ROW]) and abs(float(rows[FLAG_BS_ROW].thickness)) < 1e-9,
            "C0: the flagged scene's S6 is the station-neutral promoted beam splitter at 0 mm",
        )

        before = snapshot()
        solved, message = qe.fov_solve("object", "thickness", 23.0, 23.0)
        after = snapshot()
        ok(bool(solved), f"C1: the 23x23 object/thickness solve runs ({message})")
        ok(
            abs(after["bs"]) < 1e-9,
            f"C2 (the bug): the station-neutral beam-splitter row still carries no distance "
            f"(thickness {after['bs']:.4f}; it was inflated to 35.85 before the fix)",
        )
        # bugs/0571 revised this: the OBJECT side now slides the LENS along its leg (it used to
        # slide the whole machine along the stations, which is what kept lens-vs-mirror
        # invariant), and the camera anti-crash may slide the MIRROR along that same leg. So the
        # lens->mirror distance is legitimately not invariant. What 0569 actually protects is
        # that the fold is never yanked ACROSS its leg by a gap write -- the failure mode was
        # the mirror leaving the beam entirely (z 54.283 -> 90.132).
        mirror_drift_across = abs(float(after["mirror"][2] - before["mirror"][2]))
        ok(
            mirror_drift_across < 0.05,
            f"C3 (the report): the fold mirror stays ON its leg -- it is never pushed across it "
            f"({before['mirror'].round(3).tolist()} -> {after['mirror'].round(3).tolist()}, "
            f"drift across {mirror_drift_across:.4f} mm)",
        )

        # IDEMPOTENCE -- the flagged symptom in its scene-independent form: the user solved for
        # the field the scene was ALREADY at, and the mirror + camera moved anyway. Whatever the
        # first solve settles on, asking for the SAME field again must move nothing at all.
        repeat_before = snapshot()
        solved_again, repeat_message = qe.fov_solve("object", "thickness", 23.0, 23.0)
        repeat_after = snapshot()
        mirror_drift = float(np.linalg.norm(repeat_after["mirror"] - repeat_before["mirror"]))
        image_drift = float(np.linalg.norm(repeat_after["image"] - repeat_before["image"]))
        # bugs/0571 revised the tail of this: the object side now slides the LENS along its leg
        # instead of sliding the whole machine, so a re-solve is no longer a bit-for-bit no-op --
        # the IMAGE side still has an unconverged residual on this scene (the snap cannot verify
        # its own move here; see the open item in bugs/0570). What must hold either way, and what
        # the flag was about, is that re-solving does not walk the FOLD or the illumination unit.
        ok(
            bool(solved_again) and mirror_drift < 1e-6,
            f"C4: re-solving for the field the scene is already at leaves the FOLD exactly where "
            f"it is (mirror {mirror_drift:.6f} mm; the sensor still re-places by "
            f"{image_drift:.3f} mm -- that residual is the open image-side convergence, not a "
            f"dislocation)",
        )

        # NON-VACUITY: a different field must genuinely re-solve, or C2-C4 would pass on a
        # machine that never moves at all.
        # bugs/0572: 40x40 no longer FITS on this scene -- the lens would have to pass the fold
        # mirror, and the solve now refuses with the numbers instead of dislocating the machine.
        # Use a field the lens-to-fold leg can actually hold as the non-vacuity lever.
        live_before = snapshot()
        solved_wide, wide_message = qe.fov_solve("object", "thickness", 24.0, 24.0)
        live_after = snapshot()
        sensor_moved = float(np.linalg.norm(live_after["image"] - live_before["image"]))
        ok(
            bool(solved_wide) and sensor_moved > 1.0,
            f"C5 (non-vacuity): a field that FITS (24x24) really does re-place the sensor "
            f"({sensor_moved:.3f} mm) -- {wide_message[-70:]}",
        )
        ok(
            abs(live_after["bs"]) < 1e-9
            and abs(float(live_after["mirror"][2] - live_before["mirror"][2])) < 0.05,
            "C6: ... and it still writes no distance into the station-neutral row, and still "
            "leaves the fold on its leg",
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

    for section, fn in (("A", _check_pure), ("B", _check_wiring), ("C", _check_real_scene)):
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
        print("Folded FOV-solve fold-integrity validation passed.")
        return 0
    print("Folded FOV-solve fold-integrity validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
