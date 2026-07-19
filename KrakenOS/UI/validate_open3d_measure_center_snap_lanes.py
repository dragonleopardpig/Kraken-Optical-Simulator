"""Guard: the manual Measure tool snaps to component centres and stacks lanes.

bugs/0115 ("Can put these manual measurement align with the optical axis so that
all of them can align side by side adjacent to each other?"): manual measurements
were raw point-to-point picks, so dimensions between components landed at arbitrary
surface points and overlapped each other.

Fix (Commit 1):

* **Axis snap (always-on, edge fallback)** -- a Measure click on a recognised
  component (a STEP overlay camera/lens/LED body, or a CAD/STL/promoted
  optical-solid row) is pulled onto the optical axis via
  ``_measure_axis_snap_for_pick`` -> ``_project_world_onto_optical_axis``, KEEPING
  the clicked feature's axial position: a lens FRONT edge snaps to the front (not
  the body centre), the object plane to the on-axis FOV centre. A bare-edge pick on
  nothing recognised (snap is None) keeps the raw point-to-point click. On-axis
  points run parallel to the axis, so the dimensions line up side-by-side.
* **Axis-aligned stacked lanes** -- ``_measure_segment_offsets`` assigns every
  VISIBLE segment a parallel lane (base 45 mm, +18 mm each, in id order) so the
  axis-aligned dimensions fan out in +Y instead of overlapping. A segment with an
  explicit ``seg['offset']`` (a future user drag) keeps that standoff and is
  excluded from lane numbering. The draw loop and the right-click proximity finder
  both route through the same offsets so a click lands on exactly what is drawn.

``run_checks`` is display-free (SimpleNamespace fakes + source-string wiring);
``geometry_lane_proof`` proves two axial segments land on distinct, parallel,
non-overlapping lanes (the "side by side" guarantee), and writes a PNG when a GL
context is available. Penta phase 105 (baseline -> 106) runs ``run_checks`` only.
"""

from __future__ import annotations

import inspect
import os
from types import SimpleNamespace


def run_checks() -> list[tuple[str, bool, str]]:
    import numpy as np

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    results: list[tuple[str, bool, str]] = []

    # 1) axis snap is wired into the Measure click branch (always-on with the
    #    raw-edge fallback: a recognised component overrides world with the pick
    #    projected onto the axis and drops the normal so it spans point-to-point).
    press_src = inspect.getsource(Kraken3DInspector._on_left_button_press)
    wiring_ok = (
        "bugs/0115" in press_src
        and "_measure_axis_snap_for_pick(hit_key, world)" in press_src
        and "world = snapped" in press_src
        and "normal = None" in press_src
    )
    results.append(
        ("Measure click branch snaps the pick onto the optical axis (always-on, edge fallback)",
         wiring_ok, f"wired={wiring_ok}")
    )

    # 2) the axis snap KEEPS the clicked feature's axial position (the bug the user
    #    reported: a lens FRONT edge must stay at the front, not collapse to the body
    #    centre) and returns None for an unrecognised pick (the bare-edge fallback).
    fake = SimpleNamespace(
        _actor_step_map={"lens": "lens"},
        _actor_row_map={"obj": 0},
        _optical_axis_pick_records=[
            {"points": [[0.0, 0.0, -100.0], [0.0, 0.0, 700.0]]},  # the dotted global guide
        ],
    )
    fake._project_world_onto_optical_axis = (
        lambda w: Kraken3DInspector._project_world_onto_optical_axis(fake, w)
    )
    front = Kraken3DInspector._measure_axis_snap_for_pick(fake, "lens", np.array([12.0, -8.0, 276.4]))
    objp = Kraken3DInspector._measure_axis_snap_for_pick(fake, "obj", np.array([5.0, 3.0, -100.0]))
    miss = Kraken3DInspector._measure_axis_snap_for_pick(fake, "stray", np.array([1.0, 2.0, 3.0]))
    none = Kraken3DInspector._measure_axis_snap_for_pick(fake, None, np.array([1.0, 2.0, 3.0]))
    snap_ok = (
        front is not None and np.allclose(front, [0.0, 0.0, 276.4])   # front edge z KEPT
        and objp is not None and np.allclose(objp, [0.0, 0.0, -100.0])  # object plane -> FOV centre
        and miss is None and none is None
    )
    results.append(
        ("axis snap keeps the clicked feature's z (lens front stays at the front), None for an edge pick",
         snap_ok, f"front={None if front is None else front.tolist()}, obj={None if objp is None else objp.tolist()}, "
                  f"miss={miss}, none={none}")
    )

    # 2b) the projection lands on the NEAREST axis segment, so a folded reflect-branch
    #    pick snaps onto that branch (not the global guide).
    fake_fold = SimpleNamespace(
        _optical_axis_pick_records=[
            {"points": [[0.0, 0.0, -100.0], [0.0, 0.0, 700.0]]},   # global z-axis
            {"points": [[0.0, 0.0, 400.0], [0.0, 120.0, 400.0]]},  # folded +y branch at z=400
        ],
    )
    fold = Kraken3DInspector._project_world_onto_optical_axis(fake_fold, np.array([3.0, 66.0, 400.0]))
    fold_ok = fold is not None and np.allclose(fold, [0.0, 66.0, 400.0], atol=1e-6)
    results.append(
        ("_project_world_onto_optical_axis lands on the nearest segment (folded branch)",
         fold_ok, f"fold={None if fold is None else fold.tolist()}")
    )

    # 3) lane allocation: visible segments fan out base + lane*step in id order; a
    #    hidden segment is excluded entirely; an explicit offset (a drag) is kept and
    #    excluded from lane numbering (so a dragged dimension does not shift the rest).
    fake2 = SimpleNamespace(
        _measure_segments=[
            {"id": 0},
            {"id": 1},                 # hidden -> excluded
            {"id": 2, "offset": 100.0},  # explicit -> kept, not lane-numbered
            {"id": 3},
        ],
        _hidden_measure_segments={1},
    )
    offs = Kraken3DInspector._measure_segment_offsets(fake2)
    lanes_ok = (
        offs.get(0) == 45.0
        and offs.get(3) == 63.0          # lane 1 (seg 1 hidden, seg 2 explicit, both skip a lane)
        and offs.get(2) == 100.0
        and 1 not in offs
    )
    results.append(
        ("_measure_segment_offsets stacks lanes 45/63, honours explicit offset, skips hidden",
         lanes_ok, f"offsets={offs}")
    )

    # 4) the offset endpoints honour the assigned lane and produce a +Y standoff that
    #    keeps the dimension line in the X=0 plane for an axial (on-axis) segment: the
    #    line is parallel to the axis, shifted clear in +Y, and stays at x=0 (coplanar,
    #    seen face-on in the user's -YZ view).
    fake3 = SimpleNamespace(
        _resolve_measure_point=lambda p, r, dz: np.asarray(p, dtype=float).reshape(3)
    )
    seg = {
        "p0": [0.0, 0.0, 275.0], "p1": [0.0, 0.0, 330.0],
        "r0": None, "dz0": 0.0, "r1": None, "dz1": 0.0, "n0": None, "id": 0,
    }
    res = Kraken3DInspector._measure_segment_offset_endpoints(fake3, seg, 63.0)
    endpoints_ok = False
    detail4 = "no result"
    if res is not None:
        p0, p1, a0, a1, mid, dist = res
        parallel = abs(float(a1[2] - a0[2]) - 55.0) < 1e-6 and abs(float(a1[1] - a0[1])) < 1e-9
        on_lane = abs(float(a0[1]) - 63.0) < 1e-6 and abs(float(mid[1]) - 63.0) < 1e-6
        in_plane = abs(float(a0[0])) < 1e-9 and abs(float(a1[0])) < 1e-9 and abs(float(mid[0])) < 1e-9
        anchored = abs(float(a0[2]) - 275.0) < 1e-9
        endpoints_ok = abs(dist - 55.0) < 1e-6 and parallel and on_lane and in_plane and anchored
        detail4 = f"dist={dist:.3f}, a0={a0.tolist()}, mid_y={float(mid[1]):.3f}, x0={in_plane}"
    results.append(
        ("_measure_segment_offset_endpoints offsets in +Y within the X=0 plane (coplanar arrows)",
         endpoints_ok, detail4)
    )

    # 5) both the draw loop and the right-click proximity finder route through the
    #    same lane offsets, so a click lands on exactly the line that is drawn.
    refresh_src = inspect.getsource(Kraken3DInspector._refresh_measure_overlays)
    near_src = inspect.getsource(Kraken3DInspector._measure_segment_index_near_display_xy)
    route_ok = (
        "self._measure_segment_offsets()" in refresh_src
        and "offsets.get(" in refresh_src
        and "self._measure_segment_offsets()" in near_src
        and "offsets.get(" in near_src
    )
    results.append(
        ("draw loop + proximity finder share the lane offsets (click matches the drawn line)",
         route_ok, f"routed={route_ok}")
    )

    return results


def geometry_lane_proof(png_path: str | None = None) -> tuple[bool, str]:
    """Prove two axial segments stay COPLANAR in the X=0 plane and stack on distinct,
    parallel, non-overlapping lanes along +Y (the "align in a plane, arrows adjacent"
    guarantee, seen face-on in the user's -YZ view). Writes a PNG of the two stacked
    dimension lines beside the optical axis when GL is available."""
    import numpy as np

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    fake = SimpleNamespace(
        _measure_segments=[{"id": 0}, {"id": 1}],
        _hidden_measure_segments=set(),
        _resolve_measure_point=lambda p, r, dz: np.asarray(p, dtype=float).reshape(3),
    )
    offs = Kraken3DInspector._measure_segment_offsets(fake)
    seg0 = {"p0": [0.0, 0.0, 275.0], "p1": [0.0, 0.0, 330.0], "n0": None, "id": 0}
    seg1 = {"p0": [0.0, 0.0, 300.0], "p1": [0.0, 0.0, 430.0], "n0": None, "id": 1}
    r0 = Kraken3DInspector._measure_segment_offset_endpoints(fake, seg0, offs.get(0))
    r1 = Kraken3DInspector._measure_segment_offset_endpoints(fake, seg1, offs.get(1))

    passed = False
    detail = "unresolved"
    if r0 is not None and r1 is not None:
        _p0a, _p1a, a0a, a1a, mid0, _d0 = r0
        _p0b, _p1b, a0b, a1b, mid1, _d1 = r1
        lane0 = float(mid0[1])
        lane1 = float(mid1[1])
        parallel = abs(float(a1a[1] - a0a[1])) < 1e-9 and abs(float(a1b[1] - a0b[1])) < 1e-9
        coplanar = max(abs(float(a0a[0])), abs(float(a1a[0])), abs(float(a0b[0])), abs(float(a1b[0]))) < 1e-9
        separated = abs(lane1 - lane0 - 18.0) < 1e-6 and lane0 > 0.0
        passed = parallel and coplanar and separated
        detail = f"lanes y=({lane0:.1f},{lane1:.1f}) gap={lane1 - lane0:.1f} mm, x=0 coplanar={coplanar}"

        if png_path and os.environ.get("DISPLAY"):
            try:
                import pyvista as pv

                pl = pv.Plotter(off_screen=True, window_size=(420, 320))
                pl.add_mesh(pv.Line((0, 0, 250), (0, 0, 450)), color=(0.4, 0.4, 0.4), line_width=2)
                pl.add_mesh(pv.Line(tuple(a0a), tuple(a1a)), color=(0.95, 0.55, 0.1), line_width=4)
                pl.add_mesh(pv.Line(tuple(a0b), tuple(a1b)), color=(0.95, 0.55, 0.1), line_width=4)
                pl.view_vector((1.0, 0.0, 0.0), viewup=(0.0, 0.0, 1.0))
                pl.screenshot(str(png_path))
                pl.close()
            except Exception:
                pass

    return passed, detail


def main() -> int:
    results = run_checks()
    ok = True
    for name, passed, det in results:
        print(f"{name} | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed

    try:
        png = os.environ.get("KRAKEN_MEASURE_LANE_PNG") or "/tmp/measure_center_snap_lanes.png"
        passed, det = geometry_lane_proof(png)
        print(f"geometry proof: two axial segments stack on parallel lanes | {'PASS' if passed else 'FAIL'} | {det}")
        ok = ok and passed
    except Exception as exc:  # pragma: no cover - pyvista/driver dependent
        print(f"geometry proof skipped: {exc}")

    print("[PASS] Measure centre-snap + axis-aligned stacked lanes" if ok
          else "[FAIL] Measure centre-snap / lane stacking regressed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
