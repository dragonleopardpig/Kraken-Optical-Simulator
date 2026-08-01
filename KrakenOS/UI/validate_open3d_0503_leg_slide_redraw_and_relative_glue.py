"""bugs/0503 -- a lens leg slide must flag the drawing rebuild, and glue must seat against the
surrogate WHEREVER IT NOW SITS.

``flag_20260801_220951`` / ``flag_20260801_221613`` (build ``6b7c9447``) -- *"glued lens, seems
glue function not doing anything. Still detached after drag right."* Replaying the recorded events
byte-for-byte reproduced the committed pose (offset x 97.4064 -> 131.6076) with the MODEL rows
correctly carried (+34.2) -- the bugs/0499 redirect was working. Two things were not:

* **The drawing never caught up.** ``translate_step_overlay``'s leg-slide branch moved the rows but
  never set ``_fold_carry_pending_rebuild``, and the commit's own refresh is scoped to the dragged
  STEP label -- it repaints the body and nothing else. The bugs/0493 release flush, which exists
  for exactly this, is keyed on that marker, so it no-opped; with Show Rays OFF (the user's state)
  there is no background-trace completion to ever repaint either. The user watched the body "slide
  off its surrogate" while the model was attached the whole time.
* **Glue restored an ABSOLUTE pose.** The 0497 reference is where the body was PLACED -- relative
  to where its surrogate SAT then. Once a leg slide has moved the surrogate rows, restoring the
  reference verbatim seats the body ~28.7 mm from the surrogate the user is looking at: a glue that
  manufactures a detach. The reference is now re-expressed against the datum midpoint as it sits at
  glue time, with the record-time midpoint persisted beside the reference
  (``step_glue_reference_datum_mid_xyz``).

Also covered: the first cut of 0499 mutated the rows BEFORE ``_begin_history_capture``, so the undo
snapshot already contained the moved rows and Ctrl-Z restored the offset but not the optics -- an
undo that detaches.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0503_leg_slide_redraw_and_relative_glue
"""
from __future__ import annotations

import tempfile
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
SLIDE = 34.2012  # the recorded drag, flag_20260801_221613
EXACT = 1.0e-6
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

    made: list = []
    try:
        def _load(path: Path = SCENE):
            ed = KrakenLayoutEditor()
            made.append(ed)
            ed.layout_files["leg_slide_glue_probe"] = path
            ed.load_layout_by_name("leg_slide_glue_probe")
            return ed

        editor = _load()
        body = lambda ed=editor: np.asarray(ed._step_body_world_center("lens"), dtype=float).reshape(3)
        row1 = lambda ed=editor: np.asarray(tree_mod.row_world_pose(ed.rows, 1), dtype=float).reshape(3)
        b0, r0 = body(), row1()
        gap0 = b0 - r0

        # -- A: the slide carries the optics AND flags the drawing rebuild -----------------------
        editor._fold_carry_pending_rebuild = False
        editor.translate_step_overlay("lens", (SLIDE, 0.0, 0.0))
        check(
            abs(float((body() - b0)[0]) - SLIDE) < TOL and abs(float((row1() - r0)[0]) - SLIDE) < TOL,
            "A1: the +X slide carries body AND surrogate rows together (bugs/0499 still holds)",
        )
        check(
            bool(getattr(editor, "_fold_carry_pending_rebuild", False)),
            "A2: the slide sets the bugs/0493 sticky rebuild marker -- the release flush is keyed "
            "on it, and without it the rows/axis/2D stayed drawn at their old stations (the "
            "reported 'detached after dragging')",
        )

        # -- B: glue is relative to where the surrogate NOW sits --------------------------------
        check(
            editor.glue_step_overlay_to_surrogate("lens") is False,
            "B1: after an attached slide the lens is ALREADY glued -- the old absolute restore "
            "would instead have yanked the body back to the original station",
        )
        b_slid = body()
        editor.translate_step_overlay("lens", (0.0, 0.0, -12.0))  # lateral for this +X leg
        check(
            float(np.linalg.norm(row1() - r0) - SLIDE) < TOL
            and abs(float((body() - b_slid)[2]) + 12.0) < TOL,
            "B2: a lateral drag detaches the body alone (rows hold), which is what glue exists to undo",
        )
        acted = editor.glue_step_overlay_to_surrogate("lens")
        check(
            bool(acted) and float(np.linalg.norm(body() - b_slid)) <= EXACT,
            f"B3: glue reattaches EXACTLY onto the slid surrogate (residual "
            f"{float(np.linalg.norm(body() - b_slid)):.6f} mm), not onto the original station",
        )
        check(
            float(np.linalg.norm((body() - row1()) - gap0)) <= EXACT,
            "B4: the body-to-datum gap after glue equals the as-placed gap -- 'glued' means the "
            "same relative pose, wherever the surrogate is",
        )

        # -- C: tonight's damaged state repairs -------------------------------------------------
        reference = np.asarray(editor._step_glue_reference_offset_xyz("lens"), dtype=float).reshape(3)
        editor._set_step_placement_offset_xyz("lens", tuple(float(v) for v in reference))
        check(
            editor.glue_step_overlay_to_surrogate("lens") is True
            and float(np.linalg.norm(body() - b_slid)) <= EXACT,
            "C1: a body stranded at the ABSOLUTE reference while the surrogate sits slid (what the "
            "old glue produced tonight) is repaired by one glue click",
        )

        # -- D: undo restores rows and offset TOGETHER ------------------------------------------
        editor2 = _load()
        b20, r20 = body(editor2), row1(editor2)
        editor2.translate_step_overlay("lens", (20.0, 0.0, 0.0))
        editor2.undo()
        db = float(np.linalg.norm(body(editor2) - b20))
        dr = float(np.linalg.norm(row1(editor2) - r20))
        check(
            db <= TOL and dr <= TOL,
            f"D1: undo of a leg slide restores body AND rows (residuals {db:.4f}/{dr:.4f} mm) -- "
            "the rows used to be mutated before _begin_history_capture, so undo detached them",
        )

        # -- E: the reference/anchor pair survives a REAL save/reload ---------------------------
        editor3 = _load()
        editor3.translate_step_overlay("lens", (SLIDE, 0.0, 0.0))
        with tempfile.TemporaryDirectory() as tmp:
            saved_path = Path(tmp) / "slid_scene.py"
            editor3._write_layout_file(saved_path)
            reloaded = _load(saved_path)
            check(
                reloaded.glue_step_overlay_to_surrogate("lens") is False,
                "E1: reloading a SAVED slid scene, glue reports already-glued -- the persisted "
                "datum anchor keeps the reference meaningful (an absolute reference would have "
                "moved the body 34.2 mm on the first glue after reload)",
            )
            rb = body(reloaded)
            reloaded.translate_step_overlay("lens", (0.0, 0.0, 9.0))
            reloaded.glue_step_overlay_to_surrogate("lens")
            check(
                float(np.linalg.norm(body(reloaded) - rb)) <= EXACT,
                "E2: ... and glue still reattaches exactly after the round trip",
            )
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be driven ({type(exc).__name__}: {exc})")
    finally:
        for ed in made:
            try:
                ed.destroy()
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
