#!/usr/bin/env python3
"""Display-free guard: the CA->optical-axis snap auto-completes on a FOLDED scene, where a
promoted mirror splits the ONE optical axis into several dotted guide segments (bugs/0347).

User report (flag_20260717_164901_740, build-stamped 8834ecfa -- the bugs/0346 fix, so a
FRESH app running the fix): "right click snapping still not working." On the machine-vision
AZ85 RA-mirror scene the LED opening sits ~0.77 mm off the axis, yet the right-click snap
left it untouched (recorded axis_offset_xy = [0, 0]).

Root cause
----------
  The scene is folded (``_folded_axis_incoming_fold_point_z`` resolves), so
  ``_optical_axis_records_for_3d(None)`` returns THREE records -- ``axis:global`` plus the
  reflected legs ``axis:global:reflected`` / ``axis:global:reflected:1`` (bugs/0200/0216).
  These are SEGMENTS of one folded axis, not three separate axes. With
  ``_optical_axis_pick_records`` empty at snap time (bugs/0346), the fallback handed all
  three to ``_single_optical_axis_pick_info``, whose ``len(axis_ids) != 1`` gate read them
  as ambiguous and returned ``None`` -> the snap stayed stuck in the unusable two-step arm
  and the off-axis opening never moved. A headless probe reproduced it exactly
  (bugs/probe_0347_menu_snap_natural.py): pick list n=0, source n=3, snap moved 0.0.

Fix
---
  ``_single_optical_axis_pick_info`` counts axes by their BASE id
  (``_base_optical_axis_id`` collapses the ``:reflected[:N]`` fold suffix), so folded
  segments of one axis count as one and auto-complete, while genuinely distinct traced
  beam axes (``axis:ray:...``, no ``:reflected`` marker) stay separate and keep the
  explicit two-step pick.

What it checks
--------------
  1. ``_base_optical_axis_id`` collapses ``axis:global:reflected`` / ``:reflected:1`` to
     ``axis:global`` and leaves ``axis:global`` / ``axis:ray:...`` untouched.
  2. Folded source (axis:global + reflected legs), pick list EMPTY -> payload (the fix),
     and it picks the SEGMENT nearest the opening (axis:global for a near-incoming opening).
  3. Genuinely distinct axes (axis:global + axis:ray:...) -> None (two-step pick kept).
  4. A folded pick list carried directly (no fallback) still auto-completes.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ca_snap_folded_axis_autocomplete

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types

import numpy as np


def _closest_on_segment(pts, c):
    """Closest point on polyline ``pts`` (Nx3) to ``c`` + the local direction."""
    pts = np.asarray(pts, dtype=float)
    c = np.asarray(c, dtype=float).reshape(-1)[:3]
    best_pt = pts[0, :3]
    best_dir = np.asarray([0.0, 0.0, 1.0])
    best_d = float("inf")
    for i in range(pts.shape[0] - 1):
        a = pts[i, :3]
        b = pts[i + 1, :3]
        ab = b - a
        denom = float(np.dot(ab, ab))
        t = 0.0 if denom <= 1e-12 else float(np.clip(np.dot(c - a, ab) / denom, 0.0, 1.0))
        foot = a + t * ab
        d = float(np.linalg.norm(foot - c))
        if d < best_d:
            best_d = d
            best_pt = foot
            norm = float(np.linalg.norm(ab))
            best_dir = ab / norm if norm > 1e-12 else best_dir
    return best_pt, best_dir


def _record(axis_id, points):
    return {"axis_id": axis_id, "axis_label": "Optical Axis", "points": np.asarray(points, dtype=float)}


# axis:global runs +Z through the origin; the two reflected legs live out on +X near the
# fold vertex (z=53), so a near-origin opening is unambiguously closest to axis:global.
def _incoming():
    return _record("axis:global", [[0.0, 0.0, -102.0], [0.0, 0.0, 53.0]])


def _reflected_mid():
    return _record("axis:global:reflected:1", [[0.0, 0.0, 53.0], [80.0, 0.0, 53.0]])


def _reflected_out():
    return _record("axis:global:reflected", [[80.0, 0.0, 53.0], [200.0, 0.0, 53.0]])


def _stub(pick_records, source_records):
    def _source(_bundle):
        return list(source_records or [])

    return types.SimpleNamespace(
        _optical_axis_pick_records=list(pick_records or []),
        _optical_axis_records_for_3d=_source,
        editor=types.SimpleNamespace(_closest_polyline_point_and_direction=_closest_on_segment),
    )


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import open3d_face_assignment as fa_mod

    info = fa_mod.Open3DFaceAssignmentService._single_optical_axis_pick_info
    base = fa_mod._base_optical_axis_id
    failures: list[str] = []

    # 1) base-id collapse.
    cases = {
        "axis:global": "axis:global",
        "axis:global:reflected": "axis:global",
        "axis:global:reflected:1": "axis:global",
        "axis:global:reflected:2": "axis:global",
        "axis:ray:0:segment:2": "axis:ray:0:segment:2",
        "": "",
    }
    for raw, want in cases.items():
        got = base(raw)
        if got != want:
            failures.append(f"FAIL(1): _base_optical_axis_id({raw!r}) -> {got!r}, want {want!r}")

    # 2) Folded source (three segments of one axis), EMPTY pick list -> payload nearest axis:global.
    opening = (0.77, 0.0, 8.0)  # ~0.77 mm off the +Z incoming axis, well before the fold
    svc = _stub([], [_incoming(), _reflected_mid(), _reflected_out()])
    out = info(svc, opening)
    if not isinstance(out, dict):
        failures.append(
            "FAIL(2): a folded scene (axis:global + reflected legs) with an empty pick list must "
            "auto-complete (bugs/0347) -- got None (the stuck-armed 'snapping still not working' bug)"
        )
    else:
        if str(out.get("axis_id", "")) != "axis:global":
            failures.append(
                f"FAIL(2): the folded auto-complete must pick the SEGMENT nearest the opening "
                f"(axis:global), got {out.get('axis_id')!r}"
            )
        pw = np.asarray(out.get("picked_world", []), dtype=float).reshape(-1)
        if pw.size < 3 or not np.allclose(pw[:3], opening):
            failures.append("FAIL(2): picked_world must be the opening centre (its perpendicular foot target)")

    # 3) Genuinely distinct axes -> None (keep the explicit pick).
    svc = _stub([], [_incoming(), _record("axis:ray:0:segment:2", [[0.0, 10.0, -100.0], [0.0, 10.0, 100.0]])])
    if info(svc, opening) is not None:
        failures.append("FAIL(3): genuinely distinct optical axes must NOT auto-pick")

    # 4) A folded pick list carried directly (no fallback) still auto-completes.
    svc = _stub([_incoming(), _reflected_mid(), _reflected_out()], [])
    out = info(svc, opening)
    if not isinstance(out, dict) or str(out.get("axis_id", "")) != "axis:global":
        failures.append("FAIL(4): a folded pick list carried directly must auto-complete on axis:global")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] folded-scene CA->optical-axis snap does not auto-complete")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] a mirror-folded optical axis (axis:global + reflected segments) counts as ONE axis, "
          "so the CA->optical-axis snap auto-completes instead of stranding the two-step pick (bugs/0347)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
