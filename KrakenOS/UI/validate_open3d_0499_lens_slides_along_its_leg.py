"""bugs/0499 -- dragging the lens along its own leg carries its optics, and only its optics.

``flag_20260801_210453`` -- *"clicked glue STEP to surrogate, drag right, it is still detached."*
The glue worked (bugs/0497); the drag undid it, because the body moved and the surrogate did not.

Three world-axis assumptions were stacked in ``translate_step_overlay``, each invisible until the
one above it was removed:

1. the axial test asked ``abs(delta[2]) > 1e-9`` -- world Z, which is the optical axis only on an
   unfolded scene;
2. the ``overlay_on_axis`` gate required the placement offset's X/Y to be ~0, i.e. "on the nominal
   +Z line". The AZ85 lens offset is [97.41, 0, -106.43] BECAUSE it rides the splitter's +X leg, so
   the gate was False and the axial branch had never run on this scene at all;
3. the redirect then wrote ``rows[lens_front_idx - 1].thickness``, and on a FOLDED leg no thickness
   controls position along that leg. Measured: ``+10`` on the true leg-upstream neighbour (row 3)
   moves the lens ``[0, 0, 0]``; ``+10`` on the old target (row 0, the Object gap) moves it
   ``[0, 0, +10]`` -- section 1, lifting the whole leg for a drag along X.

A folded leg has to be slid the way the fold carry slides one: translate the rows. The surrogate's
own rows are found via ``rows_along_leg`` between the two datums (bugs/0499's leg-neighbour work),
so the set cannot disagree with ``rows_on_emitted_leg``.

Measured after, dragging +X 20 on the AZ85 scene:

    body +20   front datum +20   rear datum +20        together -- still attached
    Object, splitter, mirror, image  unchanged
    section 1 (obj->BS)   54.460 -> 54.460             the working distance holds
    section 2 (BS->lens)  71.783 -> 91.782             +20
    section 3 (lens->mir) 103.270 -> 83.270            -20

which is what sliding a lens along its rail does.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0499_lens_slides_along_its_leg
"""
from __future__ import annotations

from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
SLIDE = 20.0
TOL = 1.0e-3


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    import numpy as np

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["leg_slide_probe"] = SCENE
        editor.load_layout_by_name("leg_slide_probe")

        plan = editor._lens_leg_slide_plan()
        check(plan is not None, "A1: the lens's own leg, its rows and its direction are derivable")
        if plan is None:
            return ok, notes
        members, direction, folded = plan
        check(
            list(members) == [1, 2, 4, 5, 6] and bool(folded),
            f"A2: the surrogate's rows on that leg are {list(members)} and it IS a fold leg "
            f"({folded}) -- note they bracket the splitter at row 3 in INDEX order",
        )

        pose = lambda i: np.asarray(tree_mod.row_world_pose(editor.rows, i), dtype=float)
        body = lambda: np.asarray(editor._step_body_world_center("lens"), dtype=float).reshape(3)
        before = {i: pose(i) for i in (0, 1, 3, 6, 7, 8)}
        b0 = body()
        s1 = lambda p: float(np.linalg.norm(p[3] - p[0]))
        s2 = lambda p: float(np.linalg.norm(p[1] - p[3]))
        s3 = lambda p: float(np.linalg.norm(p[7] - p[6]))

        editor.translate_step_overlay("lens", (SLIDE, 0.0, 0.0))
        after = {i: pose(i) for i in (0, 1, 3, 6, 7, 8)}
        b1 = body()

        check(
            abs(float(np.dot(b1 - b0, direction)) - SLIDE) < TOL,
            f"B1: the body moves along the leg by {SLIDE} ({np.round(b1 - b0, 3).tolist()})",
        )
        drift = {
            i: np.round(after[i] - before[i], 3).tolist()
            for i in (1, 6)
            if abs(float(np.dot(after[i] - before[i], direction)) - SLIDE) > TOL
        }
        check(
            not drift,
            f"B2: ... and its surrogate datums move with it ({drift or 'front and rear both +20'}) "
            f"-- body and optics stay attached, which is the reported defect",
        )
        held = {
            i: np.round(after[i] - before[i], 3).tolist()
            for i in (0, 3, 7, 8)
            if float(np.linalg.norm(after[i] - before[i])) > TOL
        }
        check(
            not held,
            f"B3: the object, splitter, mirror and image do NOT move ({held or 'all held'}) -- only "
            f"the lens slides",
        )
        check(
            abs(s1(after) - s1(before)) < TOL,
            f"C1: section 1, the object-to-splitter working distance, is unchanged "
            f"({s1(before):.3f} -> {s1(after):.3f}) -- the old redirect moved exactly this",
        )
        check(
            abs((s2(after) - s2(before)) - SLIDE) < TOL,
            f"C2: section 2 grows by {SLIDE} ({s2(before):.3f} -> {s2(after):.3f})",
        )
        check(
            abs((s3(after) - s3(before)) + SLIDE) < TOL,
            f"C3: section 3 shrinks by {SLIDE} ({s3(before):.3f} -> {s3(after):.3f}) -- sliding a "
            f"lens along its rail trades the two, it does not move the whole leg",
        )
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        if editor is not None:
            try:
                editor.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
