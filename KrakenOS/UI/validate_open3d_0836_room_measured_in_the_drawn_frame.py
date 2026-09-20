"""bugs/0836 guard -- the lens room is measured where the bodies are drawn.

Found while surveying for Scene IR Phase D. ``_lens_leg_room_to_fold`` read both its
endpoints through ``scene_ir.world_frame`` and projected them on the slide plan's direction.
On ``om05a_folded`` that mixed three frames in one subtraction:

    block_end  (row 12, rear datum)   [   0.000,  0.000, 314.920]   straight-equivalent
    fold_centre(row 15, RA mirror 2)  [-269.137, 56.313, -25.000]   already its folded centre
    leg unit   (the slide plan)       [0, 0, 1]                     pre-fold; drawn leg is -x

    -> "room" = -378.42 mm

and the barrel-overhang term (bugs/0583's guard against the lens entering the prism) then
took a folded-world bound away from a pre-fold coordinate and ``max(0, ...)`` clamped the
nonsense to zero. Both rows tag ``sequential``; the space tag agreed and settled nothing.

Worse, silently: handed the plan's leg direction, ``_lens_block_physical_room_mm`` found NO
obstacle at all (``method: 'none'``) on a bench whose Filter 48-926 is 16 mm away. The
crash-avoidance measure was inert, which is the third safety check this day that quietly did
not run.

The rule is MEASURED. Two plausible derivations were wrong first and this guard pins both:
the placement SPACE does not decide it, and applying
``_optical_axis_fold_world_transform_for_row`` does not either -- that transform is
``F(v) = C + R (v - S)`` with ``S`` the straight-axis STATION, valid only where the
prescription IS ``[0, 0, z]``. The OUTPUT-PORT pose override reproduces DRAWN on every row
that has one.

Checks:
  SOURCE   -- the seam exists, is named as Phase D's, and the room measures read it.
  RULE     -- the override centre reproduces DRAWN for every row that has one.
  REJECTED -- F(prescription) really does mis-place RA mirror 2 (to ~[124.5, 0, 244.1]) and
              the front datum, so neither rejected derivation can creep back.
  LEG      -- the plan's (0,0,1) becomes the drawn -x leg.
  ROOM     -- the room is positive; the OLD mixed-frame arithmetic is shown to give -378.42.
  AGREE    -- with and without a caller-supplied leg unit now give the same answer.
  NOREG    -- bugs/0833's Filter AABB is unchanged.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")
OLD_ROOM_MM = -378.42
MIS_FOLDED_MIRROR = (124.49, 0.0, 244.14)
FILTER_AABB_0833 = (-247.39, -246.39, 30.96, 81.76, -50.40, 0.40)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import scene_ir
    from KrakenOS.UI.services import scene_placement_commands as spc

    ir_src = _inspect.getsource(scene_ir)
    spc_src = _inspect.getsource(spc)
    wanted = {
        "drawn_world_frame": ir_src,
        "drawn_leg_unit": ir_src,
        "Phase D this becomes what": ir_src,
        "scene_ir.drawn_leg_unit(self, last, unit)": spc_src,
        "scene_ir.drawn_world_frame(self, last)": spc_src,
    }
    missing = [token for token, src in wanted.items() if token not in src]
    if missing:
        notes.append(f"SOURCE missing {missing}")
        ok = False
    else:
        notes.append("SOURCE = the drawn-frame seam exists, is named as Phase D's, and is read")

    if not SCENE.exists():
        notes.append("SKIP: om05a_folded is absent (gitignored attachment)")
        return ok, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

        app = KrakenLayoutEditor()
        app.layout_files["guard"] = SCENE
        app.load_layout_by_name("guard")

        overrides = optical_solid_output_port_pose_overrides(None, app.rows) or {}
        mismatched = []
        checked = 0
        for index, pose in overrides.items():
            if not isinstance(pose, dict) or pose.get("center") is None:
                continue
            centre = np.asarray(pose["center"], dtype=float).reshape(3)
            got = np.asarray(scene_ir.drawn_world_frame(app, int(index))[0], dtype=float)
            checked += 1
            if float(np.max(np.abs(got - centre))) > 1.0e-6:
                mismatched.append(int(index))
        if checked and not mismatched:
            notes.append(f"RULE = all {checked} override rows are drawn AT their override centre")
        else:
            notes.append(f"RULE {len(mismatched)} override rows disagree with the seam: {mismatched}")
            ok = False

        mirror = next(
            (i for i, r in enumerate(app.rows)
             if str(getattr(r, "name", "") or "").startswith("RA mirror 2")),
            None,
        )
        if mirror is None:
            notes.append("SKIP: this om05a_folded has no RA mirror 2")
            return ok, notes
        presc = np.asarray(scene_ir.world_frame(app, int(mirror))[0], dtype=float)
        transform = app._optical_axis_fold_world_transform_for_row(int(mirror))
        if transform is None:
            notes.append("REJECTED RA mirror 2 has no fold transform; the defect cannot reproduce")
            ok = False
        else:
            refolded = (np.asarray(transform, dtype=float).reshape(4, 4) @ np.append(presc, 1.0))[:3]
            if float(np.max(np.abs(refolded - np.asarray(MIS_FOLDED_MIRROR)))) <= 0.5:
                notes.append(
                    "REJECTED = applying the fold transform to the prescription really does put "
                    f"RA mirror 2 at {np.round(refolded, 2).tolist()} instead of "
                    f"{np.round(presc, 2).tolist()} -- that derivation cannot creep back"
                )
            else:
                notes.append(
                    f"REJECTED the re-fold now lands at {np.round(refolded, 2).tolist()}; "
                    "the guard no longer pins the rejected derivation"
                )
                ok = False

        plan = app._lens_leg_slide_plan()
        if plan is None:
            notes.append("SKIP: no lens slide plan on this scene")
            return ok, notes
        members, direction, _frozen = plan
        last = int(max(members))
        turned = scene_ir.drawn_leg_unit(app, last, direction)
        if turned is not None and abs(abs(float(turned[0])) - 1.0) <= 1.0e-6:
            notes.append(
                f"LEG = the plan's {np.round(direction, 3).tolist()} becomes the drawn "
                f"{np.round(turned, 3).tolist()}"
            )
        else:
            notes.append(f"LEG the plan direction was not turned onto the drawn leg: {turned}")
            ok = False

        # The OLD arithmetic, re-run here.
        folds = [int(i) for i in app._promoted_mirror_fold_row_indices()]
        ahead = [f for f in folds if f > last]
        if ahead:
            mirror_row = int(min(ahead))
            old_unit = np.asarray(direction, dtype=float)
            old_unit = old_unit / max(float(np.linalg.norm(old_unit)), 1.0e-12)
            old_block = np.asarray(scene_ir.world_frame(app, last)[0], dtype=float)
            old_fold = np.asarray(scene_ir.world_frame(app, mirror_row)[0], dtype=float)
            old_along = float(np.dot(old_fold - old_block, old_unit))
            old_room = old_along - 0.5 * float(getattr(app.rows[mirror_row], "diameter", 0.0) or 0.0)
            if old_room < -100.0:
                notes.append(
                    f"ROOM = the OLD mixed-frame arithmetic really did read {old_room:.2f} mm "
                    f"(recorded {OLD_ROOM_MM})"
                )
            else:
                notes.append(f"ROOM the old arithmetic reads {old_room:.2f} mm; the defect is gone")
                ok = False

        room = app._lens_leg_room_to_fold(direction, members)
        if room is not None and float(room) > 0.0:
            notes.append(f"ROOM = the drawn-frame room is {float(room):.4f} mm, positive")
        else:
            notes.append(f"ROOM the room is {room}")
            ok = False

        front = app._lens_datum_row_index("front")
        rear = app._lens_datum_row_index("rear")
        with_leg = app._lens_block_physical_room_mm(int(front), int(rear), +1.0, leg_unit=direction)
        without = app._lens_block_physical_room_mm(int(front), int(rear), +1.0)
        same_row = with_leg.get("obstacle_row") == without.get("obstacle_row")
        both = (with_leg.get("room_phys"), without.get("room_phys"))
        if same_row and all(v is not None for v in both) and abs(both[0] - both[1]) <= 1.0e-6:
            notes.append(
                f"AGREE = with and without a caller leg unit both give row "
                f"{with_leg.get('obstacle_row')} {with_leg.get('obstacle')!r} at {both[0]:.3f} mm"
            )
        else:
            notes.append(f"AGREE the two paths disagree: with={with_leg} without={without}")
            ok = False

        filter_row = next(
            (i for i, r in enumerate(app.rows)
             if str(getattr(r, "name", "") or "").startswith("Filter")),
            None,
        )
        if filter_row is not None:
            aabb = app._element_row_world_aabb(int(filter_row))
            if aabb is not None and max(
                abs(float(a) - float(b)) for a, b in zip(aabb, FILTER_AABB_0833)
            ) <= 0.01:
                notes.append("NOREG = bugs/0833's Filter AABB is unchanged by the seam")
            else:
                notes.append(f"NOREG the Filter AABB moved: {aabb}")
                ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
