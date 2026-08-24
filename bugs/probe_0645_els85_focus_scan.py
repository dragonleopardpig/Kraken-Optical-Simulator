"""bugs/0645: WHERE is best focus on the frozen ELS85 scene after the 20x20 FOV solve?

flag_20260824_201012 (original, in focus) + flag_20260824_201312 ("solved for FOV 20x20,
image side ray defocus"). The 20x20 solve is MAGNIFYING (|m|=1.152) -- the untested regime.
The completed repro established: the snap's 0570 pre-flip moved the sensor +82.65 mm, the
re-measured residual DOUBLED (+165.31), the 0577 guard reverted, net sensor movement 0.0000,
and the solve still reported "snapped to the traced focus".

Two hypotheses give OPPOSITE fixes:
  A. the traced focus genuinely sits behind the fold mirror (unreachable negative far leg)
     -> fix = fold-arm recruitment (_apply_folded_image_split near-slide);
  B. first-order physics: magnifying means a LONGER image distance, focus beyond the sensor
     (far leg must GROW, perfectly reachable) and the best-focus-shift MEASURE is what lied
     -> fix = the measure / loop, no recruitment.

This probe takes neither measure's word for it: it SCANS the sensor along its folded leg and
measures the real traced axial spot RMS at each stop (the bugs/0576 method). The as-loaded
scene is the CONTROL (its screenshot is in focus, so the scan minimum must sit at the current
sensor); the post-solve scan then shows the true focus side.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0645_els85_focus_scan.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_ELS85.py"


def _far_and_row(editor):
    split = editor._folded_image_conjugate_split()
    geometry = editor._frozen_image_fold_world_geometry(split)
    return float(geometry["far"]), int(split["far_gap_row"])


def _sensor_world(editor):
    try:
        placement = editor._row_world_placements()[len(editor.rows) - 1]
        return tuple(round(float(v), 4) for v in placement.world_frame[0])
    except Exception:
        try:
            bounds = editor._row_actor_bounds()
            return tuple(round(float(v), 4) for v in bounds[-1][:3])
        except Exception:
            return None


def _axial_spot_rms(editor) -> tuple[float, int]:
    """Axial traced spot RMS at the detector, on the scene exactly as it stands (0576)."""
    try:
        _s, _r, bundle = editor._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception as exc:
        print(f"      trace unavailable ({type(exc).__name__}: {exc})")
        return float("nan"), 0
    launches, ends = [], []
    for path in list(getattr(bundle, "ray_paths", None) or []):
        if str(getattr(path, "termination_reason", "")) != "target_termination":
            continue
        pts = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        launches.append(pts[0, :3])
        ends.append(pts[-1, :3])
    if len(ends) < 4:
        return float("nan"), len(ends)
    try:
        stations = editor._row_z_positions()
        row0 = editor.rows[0]
        object_point = np.array(
            [float(row0.desp_x), float(row0.desp_y), float(stations[0]) + float(row0.desp_z)],
            dtype=float,
        )
    except Exception:
        object_point = np.zeros(3, dtype=float)
    launches = np.asarray(launches, dtype=float)
    offsets = np.linalg.norm(launches - object_point, axis=1)
    nearest = float(np.min(offsets))
    tolerance = max(1.0e-3, 0.02 * float(np.max(offsets) - nearest))
    keep = offsets <= nearest + tolerance
    arr = np.asarray(ends, dtype=float)[keep]
    if arr.shape[0] < 4:
        return float("nan"), int(arr.shape[0])
    return float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean())), int(arr.shape[0])


def _scan(editor, tag: str, stops: int) -> None:
    far_now, far_row = _far_and_row(editor)
    gap_now = float(editor.rows[far_row].thickness)
    const = gap_now + far_now
    print(f"\n{'=' * 72}\n{tag}")
    print(f"  far gap row {far_row}: thickness {gap_now:.4f}, world far {far_now:.4f}, const {const:.4f}")
    print(f"  sensor world: {_sensor_world(editor)}")

    try:
        world = editor._traced_bundle_best_focus_shift()
    except Exception as exc:
        world = f"raised {type(exc).__name__}"
    print(f"  _traced_bundle_best_focus_shift (world frame): {world}")

    print(f"\n  {'world far':>10} {'gap row':>9} {'spot RMS mm':>14} {'axial rays':>11}")
    results = []
    # Scan the WHOLE bookable leg, edge to edge: if the minimum lands on an edge the true
    # focus is outside the leg budget on that side -- the fact hypotheses A and B disagree on.
    lo, hi = 2.0, max(8.0, const - 2.0)
    for far in np.linspace(lo, hi, stops):
        gap = const - float(far)
        if gap < 0.0:
            continue
        editor.rows[far_row].thickness = gap
        editor._invalidate_preview_scene_trace()
        rms, hits = _axial_spot_rms(editor)
        results.append((float(far), rms))
        print(f"  {far:10.3f} {gap:9.3f} {rms:14.6f} {hits:11d}")

    editor.rows[far_row].thickness = gap_now
    editor._invalidate_preview_scene_trace()

    usable = [(f, r) for f, r in results if r == r]
    if not usable:
        print("\n  no usable spot measurements")
        return
    best_far, best_rms = min(usable, key=lambda t: t[1])
    edge = best_far <= usable[0][0] + 1e-6 or best_far >= usable[-1][0] - 1e-6
    side = ""
    if edge:
        side = ("   <-- LOW EDGE: focus is toward/behind the fold mirror (hypothesis A)"
                if best_far <= usable[0][0] + 1e-6
                else "   <-- HIGH EDGE: focus is beyond the leg budget past the sensor (hypothesis B)")
    print(f"\n  BEST FOCUS (coarse): world far {best_far:.3f} mm, spot RMS {best_rms:.6f} mm{side}")
    print(f"  the scene has the sensor at world far {far_now:.3f} mm  ->  off by {far_now - best_far:+.3f} mm")


def main() -> int:
    if not SCENE.exists():
        print("SKIP: scene not present")
        return 0

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")
        inspector = _open_inspector(editor)

        _scan(editor, "AS LOADED -- ELS85 (flag 1, the CONTROL: in focus on screen)", stops=13)

        solved, message = inspector._quick_estimation_service().fov_solve(
            "object", "thickness", 20.0, 20.0, None
        )
        print(f"\nfov_solve 20x20 -> {solved}: {message}")
        print(f"  _snap_detector_refusal: {getattr(editor, '_snap_detector_refusal', '')!r}")

        _scan(editor, "AFTER THE 20x20 SOLVE (flag 2: image side ray defocus)", stops=21)
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
