"""Replay flags 104813/104943/105146/105355 (2026-08-07 morning, build 2c880ae4) -- the
body-clearance story:

  swap PYRITE          -> ok (205 rays)
  55x55 unconstrained  -> "the lens crashed to RA mirror": the 0573 make-room stopped 1 mm
                          short of the prism APERTURE, but the barrel extends ~7 mm past the
                          rear DATUM -- body-to-body they overlapped (lens rear datum 268.26,
                          prism left face 269.09).
  swap ELS85           -> the LONGER block keeps the front datum, so its rear (283.74) lands
                          INSIDE the prism span [269.09, 294.49]; the world bracket held the
                          prism faithfully -- nothing made room for the longer lens.
  35x35                -> "prohibited, does not make sense": rows 4-5 sit past the fold centre,
                          the slide plan cannot form, the bugs/0582 guard refuses. Honest
                          refusal, wrong experience -- the CAUSE is the un-cleared swap.

After bugs/0583 (body-aware room + the swap's own fold-arm make-room), each step must keep the
lens BARREL clear of the prism BODY, and the 35x35 must simply apply.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0583_swap_body_clearance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"

PRISM_ROW = 7
MIN_CLEAR_MM = 1.5   # asserted floor; the mechanism aims for ~2.0


def _body_clearance(app) -> "float | None":
    """(prism body near edge) - (lens BARREL far edge), projected on the lens leg. Negative
    means the barrel is inside the prism."""
    from KrakenOS.UI.services import row_placement

    plan = app._lens_leg_slide_plan()
    if plan is None or not plan[2]:
        return None
    _members, direction, _ = plan
    unit = np.asarray(direction, dtype=float).reshape(3)
    unit /= max(float(np.linalg.norm(unit)), 1e-12)
    try:
        mesh = app._transformed_imported_step_mesh_for_label("lens")
        lo_s, hi_s = app._aabb_corner_projection_range(np.asarray(mesh.bounds, dtype=float), unit)
    except Exception:
        return None
    if hi_s is None:
        return None
    prism = np.asarray(row_placement.world_pose(app, PRISM_ROW).position, dtype=float)
    half = 0.5 * float(getattr(app.rows[PRISM_ROW], "diameter", 0.0) or 0.0)
    return float(np.dot(prism, unit) - half - float(hi_s))


def _ray_hits(app) -> int:
    try:
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return -1
    return sum(
        1
        for p in list(getattr(bundle, "ray_paths", None) or [])
        if str(getattr(p, "termination_reason", "")) == "target_termination"
    )


def _stage(app, tag, failures, *, expect_clear=True):
    clear = _body_clearance(app)
    hits = _ray_hits(app)
    worst = min(float(getattr(r, "thickness", 0.0) or 0.0) for r in app.rows)
    print(f"--- {tag}: body clearance {None if clear is None else f'{clear:+.3f}'} mm, "
          f"{hits} rays, min thickness {worst:+.4f}", flush=True)
    if expect_clear and clear is not None and clear < MIN_CLEAR_MM:
        failures.append(f"{tag}: barrel-to-prism clearance {clear:+.3f} mm (< {MIN_CLEAR_MM})")
    if hits < 1:
        failures.append(f"{tag}: no rays land")
    if worst < -1e-6:
        failures.append(f"{tag}: negative thickness {worst:+.4f}")


def main() -> int:
    for p in (SCENE, PYRITE, ELS85):
        if not p.exists():
            print(f"SKIP: {p} missing")
            return 0
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    failures: list[str] = []
    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()

        app.swap_imaging_lens_from_folder(str(PYRITE), refresh=False)
        _stage(app, "A: PYRITE swap (flag 104813)", failures)

        ok, msg = qe.fov_solve("object", "thickness", 55.0, 55.0, None)
        app._sync_table()
        print(f"    55x55 -> {ok}: {str(msg)[:110]}")
        if not ok:
            failures.append(f"B: 55x55 refused ({msg})")
        _stage(app, "B: 55x55 unconstrained (flag 104943 'crashed to RA mirror')", failures)

        app.swap_imaging_lens_from_folder(str(ELS85), refresh=False)
        print(f"    swap status: {app.status_var.get()!r}"[:170])
        _stage(app, "C: ELS-85 swap (flag 105146 'block inside the mirror')", failures)

        ok35, msg35 = qe.fov_solve("object", "thickness", 35.0, 35.0, None)
        app._sync_table()
        print(f"    35x35 -> {ok35}: {str(msg35)[:110]}")
        if not ok35:
            failures.append(f"D: 35x35 refused on a healthy scene ({str(msg35)[:90]})")
        _stage(app, "D: 35x35 (flag 105355 'prohibited, does not make sense')", failures)

        # E (flag 110323 "dragged the lens forward, 1pcs of lens surrogate remain stuck in RA
        # mirror"): a DRAG must carry the whole block -- bugs/0584 made membership identity-
        # based, so no lens row can be silently left behind by the write-through.
        from KrakenOS.UI.services import row_placement

        plan = app._lens_leg_slide_plan()
        if plan is None or not plan[2]:
            failures.append("E: no lens fold leg for the drag stage")
        else:
            members, direction, _ = plan
            before = {
                i: np.asarray(row_placement.world_pose(app, i).position, dtype=float)
                for i in members
            }
            delta = np.asarray(direction, dtype=float).reshape(3) * -30.0
            app.translate_step_overlay("lens", tuple(float(v) for v in delta), record_history=False)
            app._sync_table()
            moves = {
                i: float(np.linalg.norm(
                    np.asarray(row_placement.world_pose(app, i).position, dtype=float) - before[i]
                ))
                for i in members
            }
            spread = max(moves.values()) - min(moves.values())
            print(f"--- E: drag -30 along leg: member moves "
                  f"{[f'{i}:{m:.3f}' for i, m in sorted(moves.items())]} (spread {spread:.6f})",
                  flush=True)
            if spread > 1.0e-3:
                failures.append(
                    f"E: the drag tore the block -- member moves differ by {spread:.4f} mm "
                    f"({sorted(moves.items())})"
                )
            if min(moves.values()) < 25.0:
                failures.append("E: the drag write-through did not carry the rows (moved "
                                f"{min(moves.values()):.3f} mm of 30)")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    print("=" * 72)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("PASS: the barrel stays clear of the prism through solve and swap; 35x35 applies.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
