"""bugs/0625 verification -- a plain LOAD re-measures the delivered field (scale + centre).

flag_20260817_080138 ("object side still mising 2 launch rays"): the user LOADS the saved
Apo75 scene and traces -- no solve. The load cleared the learned machine state and nothing
re-measured it, so the launch grid sat on the RAW first order, decentred: the x=-27.6
column lost every ray (flag census: 134 arrivals / 38 missed_image / ray_actor_count 7 --
7 of 9 field pencils). The fix extends the bugs/0608 doctrine to loaders: a load
re-measures the delivered magnification AND learns the delivered field centre
(3-probe Jacobian, bugs/0613-verified), and the launch grid + drawn FOV square recentre.

This probe replays the user's exact workflow (load, NO solve) and verifies:
  1. the load learned a correction and a field centre (debug lines printed);
  2. instrument view: every grid pair lands rays, centroids bracket the sensor centre;
  3. display bundle: every one of the 9 field pencils has arrivals -- no dead pencil.

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0625_field_center_verify.py
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_Apo75.py")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    debug_log: list[str] = []
    original_debug = app.append_debug

    def _capture_debug(message, *args, **kwargs):
        debug_log.append(str(message))
        return original_debug(message, *args, **kwargs)

    app.append_debug = _capture_debug
    try:
        app.layout_files["scene"] = SCENE
        started = time.monotonic()
        app.load_layout_by_name("scene")
        load_seconds = time.monotonic() - started
        correction = getattr(app, "_folded_m_correction_state", None)
        centre = getattr(app, "_folded_field_center_state", None)
        print(f"scene loaded: {SCENE.name}  ({len(app.rows)} rows)  load took {load_seconds:.1f}s")
        print(f"post-load state: correction={correction}  learned centre={centre}")
        for line in debug_log:
            if "re-measure" in line.lower() or "field-centre" in line.lower():
                print(f"  debug: {line}")

        pairs = app._sample_imaging_field_grid_pairs()
        print(f"\nlaunch grid ({len(pairs)} pairs):")
        for pair in pairs:
            print(f"  ({pair[0]:8.2f}, {pair[1]:8.2f})")

        # ------------------------------------------------ 1. instrument view
        wavelength = float(app._current_wavelength())
        acceptance = app._world_launch_acceptance(wavelength)
        pupil_distance = app._world_launch_pupil_distance_cached(wavelength, float(acceptance))
        half_side = 23.04 / 2.0
        print(f"\ninstrument landings (sensor-local, half-side {half_side:.2f} mm):")
        centroids = []
        empty_pairs = 0
        for pair_x, pair_y in pairs:
            # The grid pairs are in PupilCalc 'height' convention (launch from -Field);
            # the world-order instrument takes WORLD offsets -- negate at the boundary.
            fx, fy = -float(pair_x), -float(pair_y)
            bundle = app._world_order_field_bundle(
                "hexapolar", float(fx), float(fy), 30, float(acceptance), pupil_distance)
            x_l, y_l, _z, _l, _m, _n = app._world_order_trace_landings(wavelength, bundle)
            x_l = np.asarray(x_l, dtype=float)
            y_l = np.asarray(y_l, dtype=float)
            n_tot = int(x_l.size)
            on = int(np.sum((np.abs(x_l) <= half_side) & (np.abs(y_l) <= half_side))) if n_tot else 0
            if n_tot:
                cx, cy = float(np.mean(x_l)), float(np.mean(y_l))
                centroids.append((cx, cy))
                print(f"  field ({fx:7.2f},{fy:7.2f}) -> {n_tot:3d} landings, {on:3d} on glass, "
                      f"centroid ({cx:7.2f},{cy:7.2f})")
            else:
                empty_pairs += 1
                print(f"  field ({fx:7.2f},{fy:7.2f}) -> NO LANDINGS")
        if centroids:
            xs = [c[0] for c in centroids]
            ys = [c[1] for c in centroids]
            print(f"  centroid spread: x [{min(xs):.2f}, {max(xs):.2f}]  y [{min(ys):.2f}, {max(ys):.2f}]")

        # ------------------------------------------------ 2. display bundle, per PENCIL
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        bundle = insp.__dict__.get("_current_scene_bundle")
        paths = list(getattr(bundle, "ray_paths", None) or [])
        census: dict[str, int] = {}
        pencils: dict[tuple[float, float], dict[str, int]] = {}
        for path in paths:
            reason = str(getattr(path, "termination_reason", "") or "(none)")
            census[reason] = census.get(reason, 0) + 1
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 1:
                continue
            key = (round(float(pts[0][0]), 1), round(float(pts[0][1]), 1))
            stats = pencils.setdefault(key, {})
            stats[reason] = stats.get(reason, 0) + 1
        print(f"\ndisplay bundle: {len(paths)} paths  census: {census}")
        print("per launch pencil (world x,y of first point):")
        dead_pencils = 0
        for key in sorted(pencils):
            stats = pencils[key]
            total = sum(stats.values())
            arrived = stats.get("target_termination", 0)
            flagword = ""
            if arrived == 0:
                dead_pencils += 1
                flagword = "   <-- NO ARRIVALS (a missing field spot)"
            print(f"  ({key[0]:8.1f},{key[1]:8.1f}): total {total:3d}  arrived {arrived:3d}  "
                  f"missed {stats.get('missed_image', 0):3d}  "
                  f"vignetted {stats.get('aperture_stop_vignette', 0):3d}  "
                  f"stray {stats.get('no_next_intersection', 0):3d}{flagword}")

        print("\n--- verdict ---")
        ok = True
        if correction is None:
            print("FAIL: the load did not learn a magnification correction")
            ok = False
        if centre is None:
            print("FAIL: the load did not learn a field centre")
            ok = False
        if empty_pairs:
            print(f"FAIL: {empty_pairs} grid pair(s) land nothing through the instrument")
            ok = False
        if dead_pencils:
            print(f"FAIL: {dead_pencils} of {len(pencils)} display pencils have no arrivals "
                  "(the flagged symptom: missing field spots)")
            ok = False
        if ok:
            arrived_total = census.get("target_termination", 0)
            print(f"PASS: load learned correction {correction:.4g} + centre "
                  f"{tuple(round(v, 2) for v in centre)}; all {len(pencils)} pencils arrive "
                  f"({arrived_total} arrivals vs 134 at flag time); no missing field spot")
        return 0 if ok else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
