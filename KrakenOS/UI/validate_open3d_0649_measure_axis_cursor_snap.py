"""Guard for bugs/0649 — the Measure crosshair is the CURSOR's projection onto the axis.

User: "can the mouse pointer merge with the cross hair? Existing behaviour is that the
mouse pointer and crosshair are detached, hard for me to place and click ... And the
cross hair should move only in the direction of the optical axis, I sometime see it can
climb up the BS slope surface."

Old mechanism: the hover X was placed at the 3D axis-projection of a front-most SURFACE
pick (vtkCellPicker). The X therefore sat displaced from the cursor by the full
body-surface-to-axis distance, leapt when the pick depth changed, and over a beam
splitter the sloped diagonal face owned the pick -- the projected X rode up the slope.

Fix: when the cursor is within tolerance of an optical axis in SCREEN space, the axis
wins outright -- hover marker AND click both use `_optical_axis_info_near_display_xy`
(the bugs/0639 helper), whose `picked_world` is by construction the projection of the
cursor onto the nearest axis segment in display coordinates: glued under the pointer,
sliding only along the axis polyline. Surface picks remain the fallback away from axes
(the bugs/0115 keep-the-feature's-z contract); Alt keeps the edge-entity contract.

Checks (display-free):
  A  the hover handler resolves the axis FIRST (before the surface `pickable` branch),
     places the marker at picked_world, and is gated off while Alt-edge is active.
  B  the click handler resolves the axis first too, records picked_world with
     hit_key=None (so the per-component re-snap cannot move it -- hover == click,
     the bugs/0303 contract), and both sites share the same 28 px tolerance.
  C  FUNCTIONAL (stub): picked_world is the cursor's parametric projection onto the
     axis segment -- moving the cursor ALONG the axis moves the point by the same
     parametric amount; moving PERPENDICULAR (e.g. up the BS slope direction) does not
     move it at all; outside tolerance returns None.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0649_measure_axis_cursor_snap
"""

from __future__ import annotations

import inspect
import re

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    hover_src = inspect.getsource(Kraken3DInspector._update_measure_hover_highlight)
    click_src = inspect.getsource(Kraken3DInspector._on_left_button_press)

    # ---------------------------------------------------------------- A: hover
    a_problems = []
    axis_pos = hover_src.find("_optical_axis_info_near_display_xy")
    pickable_pos = hover_src.find("if pickable and sx is not None:")
    if axis_pos < 0 or pickable_pos < 0 or axis_pos > pickable_pos:
        a_problems.append("axis resolution does not run before the surface branch")
    if "_edge_pick_alt_active" not in hover_src.split("if pickable")[0]:
        a_problems.append("the Alt-edge gate is gone (Alt hover would lose its contract)")
    if 'axis_near.get("picked_world")' not in hover_src:
        a_problems.append("the marker is not placed at the cursor's axis projection")
    if a_problems:
        ok = False
        notes.append(f"FAIL: A (bugs/0649): {a_problems}")
    else:
        notes.append("PASS: A: hover gives the axis screen-space priority, marker at picked_world")

    # ---------------------------------------------------------------- B: click
    b_problems = []
    m = re.search(
        r"axis_near = self\._optical_axis_info_near_display_xy\((?:.|\n)*?tolerance_px=([0-9.]+)",
        click_src,
    )
    h = re.search(
        r"axis_near = self\._optical_axis_info_near_display_xy\((?:.|\n)*?tolerance_px=([0-9.]+)",
        hover_src,
    )
    if m is None:
        b_problems.append("the click does not resolve the axis first (hover != click)")
    elif h is None or m.group(1) != h.group(1):
        b_problems.append(
            f"hover/click tolerances diverge ({h.group(1) if h else None} vs {m.group(1)})"
        )
    if m is not None and re.search(
        r"if axis_near is not None:\s*\n\s*world = np\.asarray", click_src
    ) is None:
        b_problems.append("the click does not record picked_world directly")
    if b_problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0649): {b_problems}")
    else:
        notes.append("PASS: B: click records the same axis point the hover X showed (28 px both)")

    # ---------------------------------------------------------------- C: functional stub
    class _Stub:
        # One axis segment: world from (0,0,0) to (100,0,0); display = orthographic
        # (world x -> screen x, world z -> screen y), so "along the axis" is screen +x
        # and "up the BS slope" has a screen-y component.
        _optical_axis_pick_records = [
            {"axis_id": "main", "points": np.array([[0.0, 0.0, 0.0], [100.0, 0.0, 0.0]])}
        ]

        def _world_to_display_2d(self, point):
            p = np.asarray(point, dtype=float).reshape(3)
            return np.array([p[0], p[2]], dtype=float)

        _point_segment_distance_2d = staticmethod(
            Kraken3DInspector.__dict__["_point_segment_distance_2d"].__func__
            if isinstance(Kraken3DInspector.__dict__["_point_segment_distance_2d"], staticmethod)
            else Kraken3DInspector.__dict__["_point_segment_distance_2d"]
        )

    stub = _Stub()
    method = Kraken3DInspector._optical_axis_info_near_display_xy
    c_problems = []
    near1 = method(stub, (30.0, 10.0), tolerance_px=28.0)   # 10 px off-axis at x=30
    near2 = method(stub, (60.0, 10.0), tolerance_px=28.0)   # moved ALONG the axis
    near3 = method(stub, (30.0, 20.0), tolerance_px=28.0)   # moved PERPENDICULAR (slope-ward)
    far = method(stub, (30.0, 60.0), tolerance_px=28.0)     # outside tolerance
    if near1 is None or not np.allclose(near1["picked_world"], [30.0, 0.0, 0.0], atol=1e-9):
        c_problems.append(f"projection wrong at x=30: {None if near1 is None else near1['picked_world']}")
    if near2 is None or not np.allclose(near2["picked_world"], [60.0, 0.0, 0.0], atol=1e-9):
        c_problems.append("moving the cursor along the axis does not slide the point equally")
    if near1 is not None and near3 is not None and not np.allclose(
        near1["picked_world"], near3["picked_world"], atol=1e-9
    ):
        c_problems.append("perpendicular cursor motion moved the point (the BS-slope climb)")
    if far is not None:
        c_problems.append("a cursor far from every axis still snapped")
    if c_problems:
        ok = False
        notes.append(f"FAIL: C (bugs/0649): {c_problems}")
    else:
        notes.append(
            "PASS: C: the point is the cursor's projection -- slides along the axis, "
            "immune to perpendicular (slope-ward) motion, None outside tolerance"
        )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Measure-axis-cursor-snap validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
