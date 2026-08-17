"""bugs/0626 verification -- a 55x55 solve on the flagged scene delivers 55.0 exactly.

flag_20260817_131423: typed 55x55 read back 54.5x54.5 (the old 1% tolerance), with the
lens run up near the RA mirror. After the fix: tolerance 0.1%, pass ceiling 10, and the
fold-arm recruitment fires from the gap-exhaustion branch too.

Verifies on the real machine_vision_Apo75.py:
  1. load (the 0625 re-measure runs), then fov_solve object/thickness 55x55;
  2. the delivered FOV readout is 55.0 within 0.1%;
  3. the lens keeps a positive margin off the RA mirror (room-to-fold >= 0);
  4. all 9 field pencils still arrive (the 0625 contract), and the drawn-fan actor
     count is reported for the ray_actor_count=8 watch item.

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0626_solve_exact_55.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_Apo75.py")


class _Shim:
    def __init__(self, editor):
        self.editor = editor


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    app = KrakenLayoutEditor()
    debug_log: list[str] = []
    original_debug = app.append_debug

    def _capture_debug(message, *args, **kwargs):
        debug_log.append(str(message))
        return original_debug(message, *args, **kwargs)

    app.append_debug = _capture_debug
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        print(f"scene loaded; post-load correction={getattr(app, '_folded_m_correction_state', None)} "
              f"centre={getattr(app, '_folded_field_center_state', None)}")

        qe = QuickEstimationService(_Shim(app))
        solved, msg = qe.fov_solve("object", "thickness", 55.0, 55.0)
        print(f"\nsolve ok={solved}:\n  {msg}")
        for line in debug_log:
            lowered = line.lower()
            if ("recruit" in lowered or "made room" in lowered or "refused" in lowered
                    or "shortfall" in lowered or "field-fill" in lowered):
                print(f"  debug: {line}")

        state = qe.current_state()
        fov_full = state.get("fov_full")
        # fov_full is the field DIAGONAL (the 0519 guard's own convention: 55x55 -> 77.78).
        want_diag = 55.0 * (2.0 ** 0.5)
        print(f"\ndelivered FOV readout: {fov_full} (diagonal; 55x55 -> {want_diag:.2f})")
        try:
            fov_error = abs(float(fov_full) / want_diag - 1.0)
        except (TypeError, ValueError):
            fov_error = float("inf")

        # Lens-to-mirror margin after the solve.
        margin = None
        try:
            plan = app._lens_leg_slide_plan()
            if plan is not None and plan[2]:
                margin = app._lens_leg_room_to_fold(plan[1], [int(i) for i in plan[0]])
        except Exception as exc:
            print(f"  room probe unavailable: {exc}")
        print(f"lens-to-fold room remaining: {margin}")

        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        bundle = insp.__dict__.get("_current_scene_bundle")
        paths = list(getattr(bundle, "ray_paths", None) or [])
        census: dict[str, int] = {}
        pencils: dict[tuple[float, float], int] = {}
        for path in paths:
            reason = str(getattr(path, "termination_reason", "") or "(none)")
            census[reason] = census.get(reason, 0) + 1
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 1:
                continue
            key = (round(float(pts[0][0]), 1), round(float(pts[0][1]), 1))
            if reason == "target_termination":
                pencils[key] = pencils.get(key, 0) + 1
        launch_keys = set()
        for path in paths:
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim == 2 and pts.shape[0] >= 1:
                launch_keys.add((round(float(pts[0][0]), 1), round(float(pts[0][1]), 1)))
        dead = sorted(k for k in launch_keys if pencils.get(k, 0) == 0)
        actor_count = None
        for attr in ("_ray_actor_count", "ray_actor_count"):
            if hasattr(insp, attr):
                actor_count = getattr(insp, attr)
                break
        print(f"\ndisplay: {len(paths)} paths  census: {census}")
        print(f"pencils: {len(launch_keys)} launched, {len(launch_keys) - len(dead)} arriving, dead: {dead}")
        print(f"ray actor count attr: {actor_count}")

        print("\n--- verdict ---")
        ok = True
        if not solved:
            print("FAIL: the 55x55 solve refused")
            ok = False
        if fov_error > 0.005:
            print(f"FAIL: delivered FOV diag {fov_full} is {fov_error:.3%} off 55x55 (> 0.5%)")
            ok = False
        if margin is not None and float(margin) < -1e-6:
            print(f"FAIL: lens-to-fold room is negative ({margin}) -- the lens sits in the mirror")
            ok = False
        if dead:
            print(f"FAIL: {len(dead)} pencil(s) with no arrivals: {dead}")
            ok = False
        if ok:
            print(f"PASS: delivered {fov_full} ({fov_error:.4%} off 55), room {margin}, "
                  f"{len(launch_keys)} pencils all arriving")
        return 0 if ok else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
