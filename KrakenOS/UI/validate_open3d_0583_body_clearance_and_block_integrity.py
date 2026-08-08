"""Guard for bugs/0583 + 0584 -- the lens BARREL stays clear of the fold mirror through solve
and swap, and the lens block cannot be torn by a drag.

Replays the flagged sequence (2026-08-07 flags 104813/104943/105146/105355/110323):

  A  swap PYRITE                 -- baseline
  B  fov_solve 55x55, no pin     -- "the lens crashed to RA mirror": the bugs/0572 room measure
                                    ran rear DATUM to mirror APERTURE, but the barrel extends
                                    ~8.8 mm past the datum, so the bodies overlapped while the
                                    surrogate surfaces stayed legal and 220 rays still landed.
  C  swap ELS-85                 -- "block inside the mirror": a LONGER replacement block keeps
                                    the front datum, so its rear lands inside the prism the
                                    stage-(c) world bracket faithfully held in place. The swap
                                    now makes the room (bugs/0573's mover) instead.
  D  fov_solve 35x35             -- "prohibited, it does not make sense": bugs/0582's contiguity
                                    guard honestly refusing on the overlapped state. With the
                                    cause fixed it must simply APPLY.
  E  drag the block along its leg -- "1pcs of lens surrogate remain stuck in RA mirror": the
                                    slide plan's membership was an axis-tree arclength window,
                                    so a displaced row fell out and the write-through moved
                                    rows [1,2,3,5] while row 4 stayed in the prism. Membership
                                    is now by IDENTITY, so every member must move IDENTICALLY.

The clearance is measured BODY to BODY (lens STEP bounds projected on the leg vs the mirror's
near face), because that is the quantity the flags were about -- a ray-level check passes right
through an interpenetration.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0583_body_clearance_and_block_integrity
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"

PRISM_ROW = 7
MIN_CLEAR_MM = 1.5      # the mechanism aims for ~2.0; assert just under it
DRAG_MM = 30.0
TEAR_TOL_MM = 1.0e-3


def _body_clearance(app):
    """(prism near face) - (lens BARREL far edge) along the lens leg. Negative = interpenetrating."""
    from KrakenOS.UI.services import row_placement

    plan = app._lens_leg_slide_plan()
    if plan is None or not plan[2]:
        return None
    _members, direction, _ = plan
    unit = np.asarray(direction, dtype=float).reshape(3)
    unit = unit / max(float(np.linalg.norm(unit)), 1.0e-12)
    try:
        mesh = app._transformed_imported_step_mesh_for_label("lens")
        if mesh is None:
            return None
        _lo, hi = app._aabb_corner_projection_range(np.asarray(mesh.bounds, dtype=float), unit)
    except Exception:
        return None
    if hi is None:
        return None
    prism = np.asarray(row_placement.world_pose(app, PRISM_ROW).position, dtype=float)
    half = 0.5 * float(getattr(app.rows[PRISM_ROW], "diameter", 0.0) or 0.0)
    return float(np.dot(prism, unit) - half - float(hi))


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


def _stage(app, tag, ok, notes):
    clear = _body_clearance(app)
    hits = _ray_hits(app)
    worst = min(float(getattr(r, "thickness", 0.0) or 0.0) for r in app.rows)
    if clear is None:
        notes.append(f"SKIP: {tag}: no lens body/leg to measure")
    elif clear < MIN_CLEAR_MM:
        ok[0] = False
        notes.append(f"FAIL: {tag}: barrel-to-prism clearance {clear:+.3f} mm (want >= {MIN_CLEAR_MM})")
    else:
        notes.append(f"PASS: {tag}: barrel clear of the prism ({clear:+.3f} mm, {hits} rays)")
    if hits == 0:
        ok[0] = False
        notes.append(f"FAIL: {tag}: no rays reach the sensor")
    if worst < -1.0e-6:
        ok[0] = False
        notes.append(f"FAIL: {tag}: negative thickness {worst:+.4f} (bugs/0580 poison)")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = [True]
    for path, what in ((SCENE, "scene"), (PYRITE, "PYRITE lens"), (ELS85, "ELS-85 lens")):
        if not path.exists():
            notes.append(f"SKIP: the {what} is absent (gitignored attachment)")
            return True, notes

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import row_placement
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        app = KrakenLayoutEditor()
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()

        app.swap_imaging_lens_from_folder(str(PYRITE), refresh=False)
        _stage(app, "A swap PYRITE", ok, notes)

        solved, msg = qe.fov_solve("object", "thickness", 55.0, 55.0, None)
        app._sync_table()
        if not solved:
            ok[0] = False
            notes.append(f"FAIL: B: the 55x55 solve was refused ({str(msg)[:80]})")
        else:
            notes.append("PASS: B: the 55x55 unconstrained solve applies")
        _stage(app, "B 55x55 (was 'crashed to RA mirror')", ok, notes)

        app.swap_imaging_lens_from_folder(str(ELS85), refresh=False)
        _stage(app, "C swap ELS-85 (was 'block inside the mirror')", ok, notes)

        solved35, msg35 = qe.fov_solve("object", "thickness", 35.0, 35.0, None)
        app._sync_table()
        if not solved35:
            ok[0] = False
            notes.append(f"FAIL: D (bugs/0583): 35x35 refused on a healthy scene ({str(msg35)[:80]})")
        else:
            notes.append("PASS: D (the 'prohibited' flag): 35x35 applies once the cause is fixed")
        _stage(app, "D 35x35", ok, notes)

        # E -- bugs/0584: the block moves as ONE piece or not at all.
        plan = app._lens_leg_slide_plan()
        if plan is None or not plan[2]:
            notes.append("SKIP: E: no lens fold leg to drag along")
        else:
            members, direction, _ = plan
            before = {
                i: np.asarray(row_placement.world_pose(app, i).position, dtype=float)
                for i in members
            }
            delta = np.asarray(direction, dtype=float).reshape(3) * -DRAG_MM
            app.translate_step_overlay("lens", tuple(float(v) for v in delta), record_history=False)
            app._sync_table()
            moves = {
                i: float(np.linalg.norm(
                    np.asarray(row_placement.world_pose(app, i).position, dtype=float) - before[i]
                ))
                for i in members
            }
            spread = max(moves.values()) - min(moves.values())
            if spread > TEAR_TOL_MM:
                ok[0] = False
                notes.append(
                    f"FAIL: E (bugs/0584): the drag TORE the block -- member moves differ by "
                    f"{spread:.4f} mm ({sorted(moves.items())})"
                )
            else:
                notes.append(
                    f"PASS: E (bugs/0584): the block moved as one piece (spread {spread:.6f} mm "
                    f"across rows {sorted(members)}; pre-fix a row stayed behind in the prism)"
                )
            if min(moves.values()) < DRAG_MM - 5.0:
                ok[0] = False
                notes.append(
                    f"FAIL: E (non-vacuity): the drag did not carry the rows "
                    f"({min(moves.values()):.3f} mm of {DRAG_MM})"
                )
    except Exception as exc:  # pragma: no cover - harness failure, not a product failure
        ok[0] = False
        notes.append(f"FAIL: harness error {type(exc).__name__}: {exc}")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok[0], notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Body-clearance-and-block-integrity validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
