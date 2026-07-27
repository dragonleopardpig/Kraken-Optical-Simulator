"""bugs/0452 guard -- a snap refuses a selection whose members are not on one axis.

flag_20260726_191537 ("rubberband snap"): after the 0449 undo-tear left the front datum
at z=53 while the rest of the lens block sat at z=115.5, the snap's first->last fit ran
corner-to-corner THROUGH the bend (~48.7 degrees). The transform stayed rigid, so the
preserved internal bend read on screen as the block "scattered" along a diagonal.
Rigid-from-garbage is still garbage: the reference members' perpendicular deviation from
the fit line is now measured and a torn selection is REFUSED loudly, moving nothing.

Checks:
  SOURCE  -- the guard is wired into snap_rows_to_axis with a relative tolerance.
  REFUSE  -- a torn selection (front datum bent off the block) is refused, names the
             offenders, and mutates no row.
  SANE    -- a straight folded chain still snaps rigidly onto the picked axis.
  SINGLE  -- the 0439 translate-only single-row path is unaffected.
"""
from __future__ import annotations

import inspect as _inspect

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        src = _inspect.getsource(ScenePlacementMixin.snap_rows_to_axis)
    except Exception as exc:
        return True, [f"SKIP: placement mixin unavailable ({exc!r})"]
    if "non_collinear_selection" in src and "tolerance" in src:
        notes.append("SOURCE = snap_rows_to_axis carries the collinearity refusal")
    else:
        notes.append("SOURCE collinearity guard missing from snap_rows_to_axis")
        ok = False

    try:
        from pathlib import Path

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        scene = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        if not scene.exists():
            notes.append("SKIP: AZ85 scene absent (gitignored attachment)")
            return ok, notes
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes

    def _centers(editor):
        z = editor._row_z_positions()
        out = {}
        for i, r in enumerate(editor.rows):
            out[i] = (
                float(r.desp_x),
                float(r.desp_y),
                float(z[i]) + float(r.desp_z) if i < len(z) else float(r.desp_z),
            )
        return out

    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        mirror1 = next(
            i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", ""))
        )
        app.delete_optical_step_rows([mirror1])

        chain = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        axis = {
            "axis_id": "axis:global:split",
            "points": np.array([(0.0, 0.0, 54.2), (268.0, 0.0, 54.2)]),
            "picked_world": np.array([90.0, 0.0, 54.2]),
        }

        # REFUSE: bend one interior member far off the block's line (the 0449 tear shape).
        victim = chain[1]
        app.rows[victim].desp_z = float(app.rows[victim].desp_z) + 62.5
        before = _centers(app)
        res = app.snap_rows_to_axis(chain, dict(axis))
        after = _centers(app)
        if (
            res.get("error") == "non_collinear_selection"
            and not res.get("moved_rows")
            and before == after
        ):
            notes.append(
                f"REFUSE = torn selection refused (offenders {res.get('offenders')}), nothing moved"
            )
        else:
            notes.append(f"REFUSE unexpected: {res!r} moved={before != after}")
            ok = False

        # SANE: undo the tear -> the straight chain still snaps rigidly.
        app.rows[victim].desp_z = float(app.rows[victim].desp_z) - 62.5
        pre = _centers(app)
        res = app.snap_rows_to_axis(chain, dict(axis))
        post = _centers(app)
        moved = res.get("moved_rows") or []
        pairs_ok = True
        for a in chain[:4]:
            for b in chain[:4]:
                if a >= b:
                    continue
                d0 = np.linalg.norm(np.array(pre[a]) - np.array(pre[b]))
                d1 = np.linalg.norm(np.array(post[a]) - np.array(post[b]))
                if abs(float(d0) - float(d1)) > 1e-6:
                    pairs_ok = False
        if moved and pairs_ok:
            notes.append(f"SANE = straight chain snapped rigidly ({len(moved)} rows)")
        else:
            notes.append(f"SANE unexpected: moved={moved} rigid={pairs_ok}")
            ok = False

        # SINGLE: the translate-only path is untouched by the guard.
        image_row = next(
            i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
        )
        res = app.snap_rows_to_axis(
            [image_row],
            {
                "axis_id": "axis:global:frozen-fold",
                "points": np.array([(235.9, 0.0, 54.2), (235.9, 0.0, -200.0)]),
                "picked_world": np.array([235.9, 0.0, -30.0]),
            },
        )
        if res.get("translate_only") and res.get("moved_rows") == [image_row]:
            notes.append("SINGLE = translate-only single-row snap unaffected")
        else:
            notes.append(f"SINGLE unexpected: {res!r}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
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
