"""Display-free guard for task #483: the 3D STEP export writes the physical-
distance (thickness) dimension overlay as solid leader tubes.

The overlay is drawn view-dependently on screen (its off-axis side follows the
live camera), but a STEP file has no camera, so the export re-runs the SAME
``add_overlays`` decision path with a geometry sink and a deterministic view-free
offset -- every dimension's shaft + two leaders are captured as world-space
polylines and tubed by the shared ray-tube builder. No text is baked (STEP can't
carry billboard labels); the offset leader geometry itself reads as the
dimension. Export is gated on the physical-distance toggle and rides the CAD
path (parity with rays).

All checks are headless: the record helper + static offset are exercised
directly, the OCC tubing is driven with synthetic polylines, and the wiring is
asserted structurally.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _topology_solid_count(path: Path) -> int:
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer

    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != 1:
        return -1
    if not reader.TransferRoots():
        return -1
    shape = reader.OneShape()
    if shape is None or shape.IsNull():
        return -1
    count = 0
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def _dimension_leaders(base_lo, base_hi, side, base_offset) -> list[np.ndarray]:
    """The three polylines collect_export_geometry emits per dimension."""
    off = np.asarray(side, dtype=float) * float(base_offset)
    start = np.asarray(base_lo, dtype=float) + off
    end = np.asarray(base_hi, dtype=float) + off
    return [
        np.asarray([start, end], dtype=float),
        np.asarray([base_lo, start], dtype=float),
        np.asarray([base_hi, end], dtype=float),
    ]


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services import cad_step_export as ce
    from KrakenOS.UI.services import layout_import_export as lie
    from KrakenOS.UI.services.open3d_thickness_dimensions import (
        Open3DThicknessDimensionService as Svc,
    )
    from KrakenOS.UI.services.optical_solid_workflow import (
        LayoutOpticalSolidWorkflowMixin as Mixin,
    )

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append((name, bool(passed), str(detail)))

    # --- A. record helper: shaft + two leaders, exact endpoints ---
    svc = Svc.__new__(Svc)
    svc._dimension_geometry_sink = []
    base_lo = np.asarray([0.0, 0.0, 10.0])
    base_hi = np.asarray([0.0, 0.0, 25.0])
    start = np.asarray([-2.0, 0.0, 10.0])
    end = np.asarray([-2.0, 0.0, 25.0])
    ret = svc._record_export_dimension(base_lo, base_hi, start, end)
    sink = svc._dimension_geometry_sink
    check("record returns 1", ret == 1, str(ret))
    check("record appends shaft + 2 leaders", len(sink) == 3, str(len(sink)))
    if len(sink) == 3:
        check("shaft endpoints", np.allclose(sink[0], [start, end]), str(sink[0].tolist()))
        check("leader from base_lo", np.allclose(sink[1], [base_lo, start]), str(sink[1].tolist()))
        check("leader from base_hi", np.allclose(sink[2], [base_hi, end]), str(sink[2].tolist()))

    svc_none = Svc.__new__(Svc)
    svc_none._dimension_geometry_sink = None
    check(
        "record no-op when sink None",
        svc_none._record_export_dimension(base_lo, base_hi, start, end) == 0,
        "",
    )

    # --- A2. _emit_span_dimension (the real funnel) records the OFFSET shaft ---
    svc_emit = Svc.__new__(Svc)
    svc_emit.pv = SimpleNamespace()  # truthy; never used on the sink path
    svc_emit._dimension_geometry_sink = []
    side = np.asarray([-1.0, 0.0, 0.0])
    base_offset = 4.0
    emit_ret = svc_emit._emit_span_dimension(
        row_index=0,
        base_lo=base_lo,
        base_hi=base_hi,
        side=side,
        offset=side * base_offset,
        base_offset=base_offset,
        scene_span=100.0,
        color=(0.0, 0.0, 0.0),
        label="S0 Thickness = 15 mm",
        drag_start=base_lo,
        drag_end=base_hi,
    )
    emit_sink = svc_emit._dimension_geometry_sink
    check("emit records 1 dimension (3 polylines)", emit_ret == 1 and len(emit_sink) == 3, str(len(emit_sink)))
    if len(emit_sink) == 3:
        want_shaft = np.asarray([[-4.0, 0.0, 10.0], [-4.0, 0.0, 25.0]])
        check("emit shaft carries the offset", np.allclose(emit_sink[0], want_shaft), str(emit_sink[0].tolist()))

    # --- B. deterministic view-free offset (no camera) ---
    for axis in ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)):
        a = np.asarray(axis)
        side = Svc.offset_direction(a, view_normal=None, screen_up=None)
        side_again = Svc.offset_direction(a, view_normal=None, screen_up=None)
        unit = abs(float(np.linalg.norm(side)) - 1.0) < 1e-6
        perp = abs(float(np.dot(side, a))) < 1e-6
        stable = np.allclose(side, side_again)
        check(f"offset {axis} unit+perp+deterministic", unit and perp and stable, str(side.tolist()))

    # --- C. the exporter tubes the dimension polylines (real OCC) ---
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

    box = BRepPrimAPI_MakeBox(10.0, 6.0, 4.0).Shape()
    system = SimpleNamespace(SDT=[], TRANS_2A=[])
    out_none = Path("/tmp/kraken_dim_export_none.step")
    out_dims = Path("/tmp/kraken_dim_export_dims.step")
    dims = (
        _dimension_leaders((0, 0, 10), (0, 0, 25), (-1, 0, 0), 3.0)
        + _dimension_leaders((0, 0, 25), (0, 0, 40), (-1, 0, 0), 3.0)
    )
    a0, c0, r0, d0 = ce._write_step_with_cad_shapes_and_rays(
        system, [], [("box", box)], [], out_none,
    )
    a1, c1, r1, d1 = ce._write_step_with_cad_shapes_and_rays(
        system, [], [("box", box)], [], out_dims, dimension_polylines=dims,
    )
    check("no dimensions -> dimension_count 0", d0 == 0, str(d0))
    check("6 leader polylines -> dimension_count 6", d1 == 6, str(d1))
    check("optics/cad/ray counts unchanged by dims", (a1, c1, r1) == (a0, c0, r0), f"{(a0, c0, r0)} vs {(a1, c1, r1)}")
    solids_none = _topology_solid_count(out_none)
    solids_dims = _topology_solid_count(out_dims)
    check("dimension tubes add 6 solids", solids_dims - solids_none == 6, f"{solids_none} -> {solids_dims}")

    # --- D. editor collector gates on the toggle + a live inspector ---
    stub_off = SimpleNamespace(show_physical_distances_var=SimpleNamespace(get=lambda: False))
    check("collector [] when toggle off", Mixin._step_export_dimension_polylines(stub_off, None) == [], "")
    stub_no_inspector = SimpleNamespace(
        show_physical_distances_var=SimpleNamespace(get=lambda: True),
        _three_d_inspector=None,
    )
    check("collector [] when no inspector", Mixin._step_export_dimension_polylines(stub_no_inspector, None) == [], "")

    # --- E. structural wiring (one funnel, view-free on export, CAD path) ---
    emit_src = inspect.getsource(Svc._emit_span_dimension)
    check(
        "emit short-circuits into the sink",
        "_dimension_geometry_sink is not None" in emit_src and "_record_export_dimension" in emit_src,
        "",
    )
    branch_src = inspect.getsource(Svc._branch_distance_overlays)
    check("per-branch overlay records to the sink", "_record_export_dimension" in branch_src, "")
    add_src = inspect.getsource(Svc.add_overlays)
    check(
        "add_overlays forces the view-free offset on export",
        "_dimension_geometry_sink is not None" in add_src and "view_normal = None" in add_src,
        "",
    )
    collect_src = inspect.getsource(Svc.collect_export_geometry)
    check(
        "collector preserves the live spacer map",
        "_trailing_spacer_gap_offset" in collect_src and "prev_spacer" in collect_src,
        "",
    )
    dim_collector_src = inspect.getsource(Mixin._step_export_dimension_polylines)
    check(
        "collector gates on the physical-distance toggle",
        "show_physical_distances_var" in dim_collector_src and "collect_export_geometry" in dim_collector_src,
        "",
    )
    export_src = inspect.getsource(lie.LayoutImportExportMixin.export_3d_step)
    check(
        "export_3d_step collects + passes dimension polylines",
        "_step_export_dimension_polylines" in export_src and "dimension_polylines" in export_src,
        "",
    )
    worker_src = inspect.getsource(lie.LayoutImportExportMixin._start_native_step_export_worker)
    check(
        "worker forwards dimension_polylines to the writer",
        "dimension_polylines=dimension_polylines" in worker_src,
        "",
    )
    writer_src = inspect.getsource(ce._write_step_with_cad_shapes_and_rays)
    check(
        "writer tubes the dimension polylines",
        "dimension_polylines" in writer_src and "dimension_tube_radius_mm" in writer_src,
        "",
    )

    failures = [f"{name} | {detail}" for name, passed, detail in checks if not passed]
    if verbose:
        print("STEP export thickness-dimension guard")
        print("check | status | detail")
        print("--- | --- | ---")
        for name, passed, detail in checks:
            print(f"{name} | {'PASS' if passed else 'FAIL'} | {detail}")
        print(f"total | {len(checks) - len(failures)}/{len(checks)} | ")
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks(verbose=True)
    if not passed:
        print(f"\nFAILED ({len(failures)} checks)")
        return 1
    print("\nSTEP export thickness-dimension validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
