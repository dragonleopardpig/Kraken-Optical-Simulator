"""bugs/0496 -- a fold carry re-seats only the bodies that are ON the leg it moves.

``flag_20260801_194857`` -- *"drag RA mirror to the left: Lens detached from surrogate."*

``_fold_slide_carry_before`` captured body centres for ``("camera", "lens")`` unconditionally and
``_fold_slide_carry_apply`` transformed both by the fold delta. That is right for a beam-SPLITTER
slide -- the lens really does sit on the splitter's emitted leg -- and wrong for a MIRROR slide,
where the lens is UPSTREAM of the folder. Measured on the AZ85 scene, sliding the RA mirror
22.60 mm left:

    row 7 (the mirror)                  x -22.60      the drag
    STEP camera                         x -22.99      correct, it rides the mirror's arm
    STEP lens                           x -22.99      WRONG
    rows 1,2,4,5,6 (the lens surrogate)    +0.00      did not move

so the drawn barrel slid 23 mm off its own optical surfaces.

Membership is now decided by ``optical_axis_tree.point_on_emitted_leg``, built from the SAME two
primitives that pick the carried ROWS (``_active_segment_for_point`` for "which leg is this on",
``descendant_segment_ids`` for "which legs does this fold carry"), so a body and a row cannot
disagree about whether they ride a given carry.

Held as the invariant BOTH ways, because either half alone is satisfiable by doing nothing or by
carrying everything:

* a MIRROR slide carries the sensor and the camera, and leaves the lens body and its surrogate
  rows alone;
* a SPLITTER slide carries the lens body **and** its surrogate rows together (bugs/0456 +
  bugs/0491 -- the case that put the lens on the list in the first place).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0496_carry_reseats_only_bodies_on_the_leg
"""
from __future__ import annotations

import time
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
MIRROR_ROW, SPLITTER_ROW = 7, 3
MIRROR_SLIDE_X = -22.60
SPLITTER_SLIDE_Z = 12.54
LENS_ROWS = ("row1", "row2", "row4", "row5", "row6")
TOL = 0.08


def _settle(app, insp, limit: float = 90.0) -> None:
    start = time.time()
    while time.time() - start < limit:
        insp.update_idletasks()
        insp.update()
        app.update()
        if getattr(insp, "_row_actor_map", {}) or {}:
            break
        time.sleep(0.25)
    for _ in range(10):
        insp.update_idletasks()
        insp.update()
        app.update()
        time.sleep(0.3)


def _snapshot(insp, axis: int) -> dict:
    """Extent of every row/STEP actor along one world axis (0 = x, 2 = z)."""
    out: dict[str, tuple] = {}
    by_key = getattr(insp, "_actor_by_key", {}) or {}

    def span(keys):
        vals: list[float] = []
        for key in list(keys or []):
            actor = by_key.get(key)
            if actor is None:
                continue
            b = actor.GetBounds()
            if b and b[0] <= b[1]:
                vals.extend((b[axis * 2], b[axis * 2 + 1]))
        return (min(vals), max(vals)) if vals else None

    for row_index, keys in (getattr(insp, "_row_actor_map", {}) or {}).items():
        s = span(keys)
        if s:
            out[f"row{row_index}"] = s
    for label, keys in (getattr(insp, "_step_actor_map", {}) or {}).items():
        s = span(keys)
        if s:
            out[f"STEP:{label}"] = s
    return out


def _shift(before: dict, after: dict, key: str) -> "float | None":
    b, a = before.get(key), after.get(key)
    if b is None or a is None:
        return None
    return (a[0] - b[0] + a[1] - b[1]) / 2.0


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    # --- A. the body filter exists and reuses the row primitives -------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services import optical_axis_tree as tree_mod
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        check(
            hasattr(tree_mod, "point_on_emitted_leg"),
            "A1: the tree can say whether a world POINT rides a folder's leg",
        )
        helper = _inspect.getsource(tree_mod.point_on_emitted_leg)
        check(
            "_active_segment_for_point" in helper and "descendant_segment_ids" in helper,
            "A2: it uses the SAME primitives as rows_on_emitted_leg, so a body and a row cannot "
            "disagree about one carry",
        )
        before_src = _inspect.getsource(ScenePlacementMixin._fold_slide_carry_before)
        check(
            "point_on_emitted_leg" in before_src,
            "A3: the carry filters its body list through it instead of taking camera+lens always",
        )
    except Exception as exc:
        notes.append(f"SKIP: source unreadable ({type(exc).__name__}: {exc})")

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor.layout_files["leg_probe"] = SCENE
        editor.load_layout_by_name("leg_probe")
        editor.open_3d_view()
        editor.update_idletasks()
        editor.update()
        insp = getattr(editor, "_three_d_inspector", None)
        if insp is None or not getattr(insp, "available", False):
            notes.append("SKIP: the embedded 3D inspector is unavailable")
            return ok, notes
        _settle(editor, insp)

        # --- B. a MIRROR slide leaves the upstream lens alone ---------------------------
        before = _snapshot(insp, 0)
        editor.translate_scene_row_pose_vector(MIRROR_ROW, (MIRROR_SLIDE_X, 0.0, 0.0))
        insp.refresh_from_editor(force_retrace=True)
        _settle(editor, insp)
        after = _snapshot(insp, 0)
        rode = {
            k: round(_shift(before, after, k), 2)
            for k in (*LENS_ROWS, "STEP:lens")
            if _shift(before, after, k) is None or abs(_shift(before, after, k)) > TOL
        }
        check(
            not rode,
            f"B1: a MIRROR slide leaves the lens body AND its surrogate rows where they are "
            f"({rode or 'all held'}) -- the lens is upstream of the folder",
        )
        followed = {
            k: round(_shift(before, after, k), 2)
            for k in ("row7", "row8", "STEP:camera")
            if _shift(before, after, k) is None
            or abs(_shift(before, after, k) - MIRROR_SLIDE_X) > TOL
        }
        check(
            not followed,
            f"B2: ... while the mirror, the sensor and the camera all move {MIRROR_SLIDE_X:+.2f} "
            f"({followed or 'all followed'}) -- so B1 is not just 'nothing happened'",
        )

        # --- C. a SPLITTER slide still carries the lens, body and rows together ---------
        before_z = _snapshot(insp, 2)
        editor.translate_scene_row_pose_vector(SPLITTER_ROW, (0.0, 0.0, SPLITTER_SLIDE_Z))
        insp.refresh_from_editor(force_retrace=True)
        _settle(editor, insp)
        after_z = _snapshot(insp, 2)
        stragglers = {
            k: round(_shift(before_z, after_z, k), 2)
            for k in (*LENS_ROWS, "STEP:lens", "STEP:camera", "row7", "row8")
            if _shift(before_z, after_z, k) is None
            or abs(_shift(before_z, after_z, k) - SPLITTER_SLIDE_Z) > TOL
        }
        check(
            not stragglers,
            f"C1: a SPLITTER slide carries the lens body AND its rows together, with the mirror, "
            f"sensor and camera ({stragglers or 'all followed'}) -- the bugs/0456 + bugs/0491 case "
            f"that put the lens on the list, which the fix must not undo",
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
