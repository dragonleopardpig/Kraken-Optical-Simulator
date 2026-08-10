"""Guard for bugs/0605 — a ray that misses the sensor must visibly MISS.

flag_20260810_164247_396 (second flag on these pencils, after bugs/0601): on the live
Apo75 bundle the 9 remaining "pencils reaching the detector" were the 9 missed_image
rays (one per field) whose plane crossings sit outside the 23x23 glass rectangle
(half-side 11.5) but inside the 0601 clip's 1.15x half-DIAGONAL disc (18.74) — so the
display hard stop drew a fake arrival for every one.

Fix contract (all display-free):
  A  detector_planes_for_hard_stop carries the in-plane axes + active half-extents.
  B  _clip_polyline_at_detector_planes stops a pass-through crossing ONLY inside the
     true rectangle: beside-the-glass crossings (inside the old disc, outside the
     rectangle) fly on; crossings within the rectangle still stop.
  C  A ray that ENDS on the plane keeps its cap (arrivals never re-clipped).
  D  use_board_limit=True keeps the generous radial board (draw-suppressed branches,
     diffuse scatter — bugs/0182/0506).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0605_pass_by_rays_miss_the_glass
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI import scene_projector as sp

    # ---------------------------------------------------------------- A: plane fields
    builder_src = inspect.getsource(sp.detector_planes_for_hard_stop)
    if "half_w" not in builder_src or "axes[1]" not in builder_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0605): detector_planes_for_hard_stop no longer carries the "
            "rectangle fields — the clip falls back to the padded disc and missed rays "
            "fake arrivals again"
        )
    else:
        notes.append("PASS: A: the hard-stop planes carry in-plane axes + half extents")

    # ---------------------------------------------------------------- B/C/D: mechanics
    center = np.zeros(3)
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])
    bitangent = np.array([0.0, 1.0, 0.0])
    half = 11.5
    half_diag = float(np.hypot(half, half))
    plane = (center, normal, 1.15 * half_diag, 28.8, tangent, bitangent, half, half)

    def ray_through(x, y):
        return np.array([[x, y, -50.0], [x, y, 50.0]])

    # B1: beside the glass (the flagged geometry: r ~ 15 inside the 18.7 disc,
    # outside the 11.5 rectangle) -> flies on, NOT clipped.
    pts, clipped = sp._clip_polyline_at_detector_planes(ray_through(14.9, 2.0), [plane])
    if clipped or pts.shape[0] != 2:
        ok = False
        notes.append(
            "FAIL: B (bugs/0605): a pass-by crossing beside the glass (r inside the "
            "old 1.15x half-diag disc) is still clipped — the flagged fake arrivals are back"
        )
    else:
        notes.append("PASS: B1: a beside-the-glass crossing flies on (visible miss)")
    # B2: within the rectangle -> still hard-stopped at the plane.
    pts, clipped = sp._clip_polyline_at_detector_planes(ray_through(5.0, -7.0), [plane])
    if not clipped or abs(float(pts[-1][2])) > 1e-6:
        ok = False
        notes.append(
            "FAIL: B (bugs/0605): a crossing INSIDE the glass rectangle is no longer "
            "stopped — rays draw straight through the sensor board (bugs/0601 regressed)"
        )
    else:
        notes.append("PASS: B2: a within-the-glass crossing still stops at the board")

    # C: a ray that ENDS on the plane keeps its cap.
    arrival = np.array([[3.0, 3.0, -50.0], [3.0, 3.0, 0.0]])
    pts, clipped = sp._clip_polyline_at_detector_planes(arrival, [plane])
    if clipped or pts.shape[0] != 2:
        ok = False
        notes.append("FAIL: C (bugs/0605): an arriving ray's cap was re-clipped")
    else:
        notes.append("PASS: C: arrivals keep their cap")

    # D: the board limit still governs suppressed/diffuse callers (radial, generous).
    pts, clipped = sp._clip_polyline_at_detector_planes(
        ray_through(14.9, 2.0), [plane], use_board_limit=True
    )
    if not clipped:
        ok = False
        notes.append(
            "FAIL: D (bugs/0605): use_board_limit no longer stops within the radial "
            "board — the scatter starburst escapes past its bounding plane (bugs/0182/0506)"
        )
    else:
        notes.append("PASS: D: the generous radial board still governs suppressed branches")

    # E: a missed_image ray the ENGINE terminated ON the plane beside the glass gains
    # a fly-past tail (the bugs/0553 doctrine) -- the miss becomes visible instead of
    # reading as an arrival pencil; the same status terminating INSIDE the glass (or
    # away from any plane) is left alone.
    beside = np.array([[14.9, 2.0, -50.0], [14.9, 2.0, 0.0]])
    pts, capped = sp.bounded_ray_points_for_scene_display(
        beside, np.zeros(3), 200.0, terminal_status="missed_image", detector_planes=[plane]
    )
    if pts.shape[0] < 3 or abs(float(pts[-1][2])) < 1.0:
        ok = False
        notes.append(
            "FAIL: E (bugs/0605): a missed_image termination beside the glass still ENDS "
            "on the sensor plane — the flagged fake-arrival pencils are back"
        )
    else:
        notes.append(f"PASS: E1: a beside-the-glass miss flies past (tail to z={float(pts[-1][2]):.0f})")
    inside = np.array([[5.0, 5.0, -50.0], [5.0, 5.0, 0.0]])
    pts, capped = sp.bounded_ray_points_for_scene_display(
        inside, np.zeros(3), 200.0, terminal_status="missed_image", detector_planes=[plane]
    )
    if pts.shape[0] != 2 or abs(float(pts[-1][2])) > 1e-6:
        ok = False
        notes.append(
            "FAIL: E (bugs/0605): a missed_image termination INSIDE the glass was extended "
            "— light drawn through the sensor board"
        )
    else:
        notes.append("PASS: E2: an inside-the-glass termination keeps its cap")

    # Legacy 3-tuple planes still work (mechanism harnesses).
    legacy = (center, normal, 20.0)
    pts, clipped = sp._clip_polyline_at_detector_planes(ray_through(5.0, 5.0), [legacy])
    if not clipped:
        ok = False
        notes.append("FAIL: legacy 3-tuple plane no longer clips (harness compatibility)")
    else:
        notes.append("PASS: legacy 3-tuple planes still clip radially")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Pass-by-rays-miss-the-glass validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
