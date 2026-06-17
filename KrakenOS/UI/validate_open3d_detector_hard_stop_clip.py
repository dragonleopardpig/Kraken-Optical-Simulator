#!/usr/bin/env python3
"""Display-free regression for bugs/0088 Phase A: a detector/Image plane is a
HARD STOP for the drawn ray polyline -- no ray is drawn past it (the trace is
unchanged; this is display-only). A ray polyline that crosses a detector plane
within the detector's radial extent is truncated AT the plane; a crossing
outside the extent (a genuine miss past the board) is left alone; with no
detector planes the polyline is unchanged.

Drives the real `scene_projector` clip helpers + `bounded_ray_points_for_scene_display`
with synthetic polylines/planes -- no Xvfb, no VTK.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_detector_hard_stop_clip

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.scene_projector import (
        _clip_polyline_at_detector_planes,
        bounded_ray_points_for_scene_display,
        detector_planes_for_hard_stop,
    )

    failures: list[str] = []
    center = np.array([0.0, 0.0, 100.0])
    normal = np.array([0.0, 0.0, 1.0])  # plane at z=100, facing +Z
    plane_in = [(center, normal, 50.0)]   # generous board: radial limit 50 mm

    # 1) crosses the plane within extent -> truncate AT z=100.
    pts = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 200.0]])
    out, clipped = _clip_polyline_at_detector_planes(pts, plane_in)
    if not clipped:
        failures.append("FAIL: pass-through ray was NOT clipped at the detector plane")
    elif abs(float(out[-1, 2]) - 100.0) > 1e-6 or out.shape[0] != 2:
        failures.append(f"FAIL: clip did not end at z=100: {out.tolist()}")

    # 1b) clip point lands within extent (radial ~0 here).
    if clipped and float(np.hypot(out[-1, 0], out[-1, 1])) > 1e-6:
        failures.append("FAIL: clipped point drifted off the optical axis")

    # 2) crosses the plane OUTSIDE the extent (radial 80 > limit 50) -> NOT clipped.
    pts_far = np.array([[80.0, 0.0, 0.0], [80.0, 0.0, 200.0]])
    out_far, clipped_far = _clip_polyline_at_detector_planes(pts_far, plane_in)
    if clipped_far:
        failures.append("FAIL: a ray missing the detector board (radial 80 > 50) was wrongly clipped")
    if not np.allclose(out_far, pts_far):
        failures.append("FAIL: an out-of-extent ray polyline was modified")

    # 3) no planes -> unchanged.
    out_none, clipped_none = _clip_polyline_at_detector_planes(pts, None)
    if clipped_none or not np.allclose(out_none, pts):
        failures.append("FAIL: polyline changed with no detector planes")
    out_empty, clipped_empty = _clip_polyline_at_detector_planes(pts, [])
    if clipped_empty or not np.allclose(out_empty, pts):
        failures.append("FAIL: polyline changed with an empty detector-plane list")

    # 4) ray ends BEFORE the plane (z up to 80 < 100) -> unchanged.
    pts_short = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 80.0]])
    out_short, clipped_short = _clip_polyline_at_detector_planes(pts_short, plane_in)
    if clipped_short or not np.allclose(out_short, pts_short):
        failures.append("FAIL: a ray ending before the plane was clipped")

    # 5) ray already ENDS exactly on the plane (hit_detector) -> not re-clipped to zero.
    pts_hit = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 100.0]])
    out_hit, clipped_hit = _clip_polyline_at_detector_planes(pts_hit, plane_in)
    if clipped_hit or out_hit.shape[0] != 2:
        failures.append(f"FAIL: a ray ending on the plane was re-clipped: {out_hit.tolist()}")

    # 6) earliest of two planes wins (z=100 board + z=150 board, ray to z=300).
    two = [(np.array([0.0, 0.0, 150.0]), normal, 50.0), (center, normal, 50.0)]
    out2, clipped2 = _clip_polyline_at_detector_planes(np.array([[0, 0, 0], [0, 0, 300.0]]), two)
    if not clipped2 or abs(float(out2[-1, 2]) - 100.0) > 1e-6:
        failures.append(f"FAIL: earliest plane (z=100) did not win: {out2.tolist()}")

    # 7) end-to-end through bounded_ray_points_for_scene_display: an escaped ray
    #    whose tail would shoot past a detector is truncated at the plane.
    esc = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 90.0]])
    bounded_pts, was_bounded = bounded_ray_points_for_scene_display(
        esc, np.zeros(3), 200.0, terminal_status="escaped",
        terminal_direction=(0.0, 0.0, 1.0), detector_planes=plane_in,
    )
    if not was_bounded or float(bounded_pts[-1, 2]) > 100.0 + 1e-6:
        failures.append(f"FAIL: escaped-ray tail drew past the detector plane: end z={float(bounded_pts[-1,2]):.3f}")

    # 8) detector_planes_from_bundle picks up is_detector targets.
    from types import SimpleNamespace
    tgt = SimpleNamespace(
        is_detector=True, center_world=(0.0, 0.0, 100.0), normal_world=(0.0, 0.0, 1.0),
        tangent_world=(1.0, 0.0, 0.0), diameter=20.0, active_width_mm=0.0, active_height_mm=0.0,
    )
    non = SimpleNamespace(
        is_detector=False, center_world=(0.0, 0.0, 50.0), normal_world=(0.0, 0.0, 1.0),
        tangent_world=(1.0, 0.0, 0.0), diameter=20.0, active_width_mm=0.0, active_height_mm=0.0,
    )
    planes = detector_planes_for_hard_stop(SimpleNamespace(targets=[tgt, non]), 200.0)
    if len(planes) != 1:
        failures.append(f"FAIL: expected 1 detector plane from the bundle, got {len(planes)}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0088 detector hard-stop clip")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] detector/Image plane hard-stops the drawn ray polyline (bugs/0088 Phase A)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
