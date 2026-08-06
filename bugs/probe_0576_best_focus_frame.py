"""bugs/0576: WHERE is best focus on the frozen Apo75->PYRITE scene, measured on the real scene?

The snap has two candidate measures and, on a frozen scene, picks the station-frame one first:

  _real_ray_best_focus_shift_for_rows()  traces _folded_optical_solid_straight_equivalent_rows,
                                         which keeps the THICKNESSES and drops the placement;
  _traced_bundle_best_focus_shift()      walks the bundle that actually traced, in world.

On a 0433-frozen fold the first one is not tracing this scene: the bugs/0571 compensated slide
grows the lens block's stations and cancels them again past the block, so the prescription's
lens->sensor spacing and the world path disagree outright. This probe does not take either
measure's word for it -- it SCANS the sensor along its own folded leg and measures the real
traced spot RMS at each stop, so "best focus" is an observation.

Flag 1 (the as-loaded Apo75, which the screenshot shows in focus) is the CONTROL: if the scan is
a valid measurement, flag 1 must show its minimum at the sensor's current position. Without that
control a monotone curve cannot be told from a broken measurement.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0576_best_focus_frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"


def _far_and_row(editor):
    split = editor._folded_image_conjugate_split()
    geometry = editor._frozen_image_fold_world_geometry(split)
    return float(geometry["far"]), int(split["far_gap_row"])


def _axial_spot_rms(editor) -> tuple[float, int]:
    """Axial traced spot RMS at the detector, on the scene exactly as it stands.

    The WORLD-frame observation: it traces the real scene (desp, tilts, fold and all) and
    measures where the axial rays actually land. The axial field is picked RELATIVE TO THE
    OBJECT ROW -- this scene's object is not at the world origin, so the 0470 validator's
    ``norm(pts[0]) > 1`` filter would keep nothing.
    """
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


def _scan(editor, tag: str) -> None:
    far_now, far_row = _far_and_row(editor)
    gap_now = float(editor.rows[far_row].thickness)
    const = gap_now + far_now
    print(f"\n{'=' * 72}\n{tag}")
    print(f"  far gap row {far_row}: thickness {gap_now:.4f}, world far {far_now:.4f}, const {const:.4f}")

    try:
        station = editor._real_ray_best_focus_shift_for_rows()
    except Exception as exc:
        station = f"raised {type(exc).__name__}"
    try:
        world = editor._traced_bundle_best_focus_shift()
    except Exception as exc:
        world = f"raised {type(exc).__name__}"
    print(f"  _real_ray_best_focus_shift_for_rows (station frame) : {station}")
    print(f"  _traced_bundle_best_focus_shift     (world frame)   : {world}")

    print(f"\n  {'world far':>10} {'gap row':>9} {'spot RMS mm':>14} {'axial rays':>11}")
    results = []
    lo, hi = 2.0, max(8.0, const - 2.0)
    for far in np.linspace(lo, hi, 25):
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
    print(f"\n  BEST FOCUS (coarse): world far {best_far:.3f} mm, spot RMS {best_rms:.6f} mm"
          f"{'   <-- AT A SCAN EDGE, the true minimum is outside the leg budget' if edge else ''}")
    print(f"  the scene has the sensor at world far {far_now:.3f} mm  ->  off by {far_now - best_far:+.3f} mm")


def main() -> int:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        print("SKIP: scene or lens folder not present")
        return 0

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")
        # The preview trace only produces a bundle with the inspector open (the 0470 validator's
        # harness) -- without it every ray comes back no_next_intersection.
        inspector = _open_inspector(editor)

        # CONTROL: flag 1, the state whose screenshot is in focus.
        _scan(editor, "AS LOADED -- Apo75 (flag 1, the CONTROL: in focus on screen)")

        editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        _scan(editor, "AFTER THE SWAP -- PYRITE 85 (flag 2)")

        solved, message = inspector._quick_estimation_service().fov_solve(
            "object", "thickness", 23.0, 23.0, None
        )
        print(f"\nfov_solve -> {solved}: {message}")
        _scan(editor, "AFTER THE SOLVE (flag 3)")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
