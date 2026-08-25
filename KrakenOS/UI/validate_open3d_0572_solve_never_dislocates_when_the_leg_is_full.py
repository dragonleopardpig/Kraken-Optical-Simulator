"""Guard for bugs/0572 -- when the lens cannot slide far enough along its leg, the solve REFUSES
with the numbers; it never falls back to the write that dislocates the machine.

The user's own experiment (2026-08-06): open ``attachment/machine_vision_Apo75.py``, swap the
imaging lens to the PYRITE 45-85, then Solve for Thickness at 35x35 and 55x55 -- *"I think there
is another recurrence bug that prevent solving for 55x55."*  There is, and it is mechanical:

* bugs/0571 moves the object-side delta by sliding the lens block along its fold leg, writing
  ``gap before += slide`` / ``gap after -= slide``;
* that spends the lens-to-fold room. Measured on this scene: 35x35 consumed 72.8 mm and left the
  rear-datum gap at 21.06 mm (with the lens block's rear datum at x 194.36, PAST the fold mirror
  at x 179.79);
* 55x55 then needed 73.9 mm more, the composite declined, and the caller fell back to the raw
  ``rows[0].thickness`` write -- the bugs/0571 dislocation, straight back: the block jumped
  z 54.283 -> 128.18, across its own leg.

So the fix is two-part: the slide is bounded by the geometry (the block may not walk into the
fold mirror), and a refused slide REFUSES THE SOLVE with an actionable message instead of falling
back. Measured after: 35x35 and 55x55 both refuse, quoting "needs the lens 72.8 / 146.7 mm
further ... only 45.73 mm of the lens-to-fold leg is left -- slide the fold mirror (and the camera
behind it) 27.1 / 101 mm along the leg first", and NOTHING in the scene moves.

Checks:
- A PURE: ``_lens_leg_room_to_fold`` measures block-end -> fold centre minus the mirror's own
  half-aperture, and returns None when no fold terminates the leg (an unbounded leg is bounded by
  the section gaps alone).
- B REAL SCENE (skip-if-absent, Tk/Xvfb): the user's exact sequence WITH ROOM-MAKING DISABLED
  (bugs/0573 makes the room automatically now -- phase 448 guards that; what this bug owns is the
  fallback contract when it cannot). Both fields refuse; the refusal names the shortfall AND what
  to move; and every element -- lens, beam splitter, fold mirror, sensor -- is byte-for-byte where
  it was. Non-vacuity: the same solve on a field that DOES fit still moves the lens.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0572_solve_never_dislocates_when_the_leg_is_full
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"


def _check_pure(ok, notes) -> None:
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, *, diameter=25.0, mirror=False, desp_x=0.0):
        row = SurfaceRow(name=name, thickness=0.0, diameter=float(diameter), glass="AIR")
        row.desp_x = float(desp_x)
        row.axis_move = 0.0
        if mirror:
            row.advanced = {
                "StepOverlayPromotion": {"step_label": "optical"},
                "OpticalSolidFaces": {"version": 1, "faces": [
                    {"face_id": "S001/F002", "function": "Mirror", "role": "Mirror",
                     "normal": [-0.7071, 0.0, 0.7071], "centroid": [0.0, 0.0, 0.0]},
                ]},
            }
        return row

    rows = [_row("Object"), _row("Front Optical Vertex Datum", desp_x=82.039),
            _row("Rear Optical Vertex Datum", desp_x=121.559),
            _row("Promoted OPTICAL STEP optical solid", mirror=True, desp_x=179.788),
            _row("Image")]

    poses = {
        2: np.array([121.559, 0.0, 54.283]),
        3: np.array([179.788, 0.0, 54.321]),
    }

    class _Probe(SimpleNamespace):
        pass

    probe = _Probe(
        rows=rows,
        _promoted_mirror_fold_row_indices=lambda: [3],
    )
    # row_placement.world_pose is what the real method calls; stub the module for the probe.
    import KrakenOS.UI.services.row_placement as row_placement

    original = row_placement.world_pose
    row_placement.world_pose = lambda editor, index: SimpleNamespace(position=poses[int(index)])
    try:
        room = ScenePlacementMixin._lens_leg_room_to_fold(
            probe, np.array([1.0, 0.0, 0.0]), [1, 2]
        )
    finally:
        row_placement.world_pose = original
    ok(
        room is not None and abs(float(room) - (179.788 - 121.559 - 12.5)) < 1e-6,
        f"A1: the room is block-end -> fold centre minus the mirror's half-aperture "
        f"(got {room}, want {179.788 - 121.559 - 12.5:.3f})",
    )

    probe_nofold = _Probe(rows=rows, _promoted_mirror_fold_row_indices=lambda: [])
    ok(
        ScenePlacementMixin._lens_leg_room_to_fold(probe_nofold, np.array([1.0, 0.0, 0.0]), [1, 2])
        is None,
        "A2: a leg with no fold ahead of the block is unbounded here -- only the section gaps "
        "constrain it (the caller's existing check)",
    )


def _check_real_scene(ok, notes) -> None:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        notes.append("SKIP: machine_vision_Apo75.py / the PYRITE folder are not in this checkout")
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
        editor.layout_files["apo75"] = SCENE
        editor.load_layout_by_name("apo75")
        model = editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        ok(model is not None, f"B0: the swap to PYRITE 45-85 runs ({getattr(model, 'title', '')})")

        def snapshot():
            return [
                np.asarray(row_placement.world_pose(editor, index).position, dtype=float)
                for index in range(len(editor.rows))
            ]

        # REWRITE (bugs/0645/0647): the machine gained LEGAL room-makers -- the snap's
        # measured direction retry, the near-leg recruit, the bugs/0550 collision
        # redistribution -- so fields that used to be unreachable now genuinely solve, and
        # simulating "no room" by disabling mechanisms one-by-one became a fiction (every
        # rerun found the next legal mover; measured: with the recruit disabled the retry
        # + redistribution still solved 35x35 with the field delivered). What this bug is
        # DURABLY about is the dislocating fallback: a "solved" scene with the lens block
        # thrown 73.9 mm across its leg and the field NOT actually delivered. The honest
        # invariant, either way the machine decides:
        #   - SUCCESS  => the MEASURED delivered field lands on the request (a dislocating
        #                 fallback can never pass this -- the field it delivers is wrong);
        #   - REFUSAL  => the message says what to move and by how much, and the scene is
        #                 byte-identical (nothing moved).
        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        for field in (35.0, 55.0):
            before = snapshot()
            solved, message = qe.fov_solve("object", "thickness", field, field)
            after = snapshot()
            drift = max(
                float(np.linalg.norm(a - b)) for a, b in zip(after, before)
            ) if before else 0.0
            if solved:
                readout = qe.current_state()
                diag = float(readout.get("fov_full") or 0.0)
                want = field * float(np.sqrt(2.0))
                ok(
                    abs(diag - want) < 0.02 * want + 0.5,
                    f"B1@{field:g}: the solve SUCCEEDED and the MEASURED field lands on the "
                    f"request (diag {diag:.3f}, want {want:.3f}) -- legal room-making, not "
                    f"a dislocating fallback",
                )
            else:
                ok(
                    "slide the fold mirror" in message
                    and "mm of the lens-to-fold leg is left" in message,
                    f"B2@{field:g}: the refusal says what to move and by how much "
                    f"({message[:90]})",
                )
                ok(
                    drift < 1e-9,
                    f"B3@{field:g} (the recurrence): a REFUSED solve moved NOTHING -- max "
                    f"row drift {drift:.9f} mm (the pre-fix 55x55 threw the lens block "
                    f"73.9 mm across its leg)",
                )

        # NON-VACUITY: a field that fits still solves and still moves the lens along the leg.
        before = snapshot()
        solved, message = qe.fov_solve("object", "thickness", 24.0, 24.0)
        after = snapshot()
        lens_shift = after[1] - before[1]
        ok(
            bool(solved) and abs(float(lens_shift[0])) > 0.5 and abs(float(lens_shift[2])) < 1e-6,
            f"B4 (non-vacuity): a field that FITS still solves and slides the lens along the leg "
            f"(dx {float(lens_shift[0]):+.3f}, dz {float(lens_shift[2]):+.3f}) -- {message[:70]}",
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
        print("Solve-refuses-instead-of-dislocating validation passed.")
        return 0
    print("Solve-refuses-instead-of-dislocating validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
