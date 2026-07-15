"""Display-free guard for bugs/0315 -- the 3D STEP export must also carry the
manual Measure-tool dimensions, not just the automatic physical-distance overlay.

flag_20260715_113521_943 ("exported STEP file (with manual thickness overlay, no
saving) ... thickness overlay is not exported"): the user annotated the scene with
the orange Measure tool (``_measure_segments``), but bugs/0313 only exports the
BLUE physical-distance overlay (``show_physical_distances_var``). The measurements
had no export path -- so the STEP opened in FreeCAD with no dimensions
(``thickness_dimension_count: 0`` in the recording confirms the automatic overlay
was off; the on-screen leaders were the orange Measure tool).

Fix (bugs/0315): ``Kraken3DInspector.collect_measure_export_geometry`` yields each
visible measure segment's shaft + two witness polylines -- the SAME geometry
``_refresh_measure_overlays`` draws (reusing ``_measure_segment_offsets`` /
``_measure_segment_offset_endpoints``), minus the label + handle -- and
``_step_export_dimension_polylines`` folds them into ``dimension_polylines``
INDEPENDENT of the physical-distance toggle (a measurement is its own annotation).
The shared ray-tube writer already tubes every entry, so no writer change.

  (A) GEOMETRY: a visible segment -> shaft (offset a0->a1) + witness p0->a0 +
      witness p1->a1, exact endpoints; two segments -> 6 polylines.
  (B) HIDDEN/EMPTY: hidden segments (``_hidden_measure_segments``) are skipped;
      no segments -> [].
  (C) TOGGLE-INDEPENDENT: ``_step_export_dimension_polylines`` returns the measure
      polylines even when the physical-distance toggle is OFF (the fix), combines
      both when it is ON, and [] when the 3D inspector is not open.
  (D) SAME RESOLVER (invariant): the export reuses the exact
      ``_measure_segment_offset_endpoints`` the on-screen draw loop uses, so the
      exported tubes can never drift from the displayed dimension.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_export_measure_dimensions
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


def _seg(sid: int, z0: float, z1: float, offset: float) -> dict:
    """A measure segment with raw endpoints (no row anchor, so the resolver is
    pure math) and an explicit offset (deterministic lane, no camera needed)."""
    return {"id": sid, "p0": [0.0, 0.0, z0], "p1": [0.0, 0.0, z1], "offset": offset}


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as Insp
    from KrakenOS.UI.services.optical_solid_workflow import (
        LayoutOpticalSolidWorkflowMixin as Mixin,
    )

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append((name, bool(passed), str(detail)))

    # --- A. geometry: shaft + two witnesses per visible segment, exact endpoints ---
    insp = Insp.__new__(Insp)
    insp._measure_segments = [_seg(1, 10.0, 25.0, 40.0), _seg(2, 25.0, 40.0, 40.0)]
    insp._hidden_measure_segments = set()
    geo = insp.collect_measure_export_geometry()
    check("A two segments -> 6 polylines", len(geo) == 6, str(len(geo)))
    if len(geo) == 6:
        # segment 1 (offset +Y by 40): shaft, then the two witness leaders.
        check("A shaft is the offset dimension line", np.allclose(geo[0], [[0, 40, 10], [0, 40, 25]]), str(geo[0].tolist()))
        check("A witness from p0 to shaft near end", np.allclose(geo[1], [[0, 0, 10], [0, 40, 10]]), str(geo[1].tolist()))
        check("A witness from p1 to shaft far end", np.allclose(geo[2], [[0, 0, 25], [0, 40, 25]]), str(geo[2].tolist()))
        check("A every polyline is a 2x3 world segment", all(g.shape == (2, 3) for g in geo), "")
        # the two segments occupy different axial spans -- distinct dimensions, not a dup.
        check("A segment 2 shaft is distinct", np.allclose(geo[3], [[0, 40, 25], [0, 40, 40]]), str(geo[3].tolist()))

    # one segment -> exactly 3 polylines
    insp_one = Insp.__new__(Insp)
    insp_one._measure_segments = [_seg(7, 0.0, 12.0, 30.0)]
    insp_one._hidden_measure_segments = set()
    check("A one segment -> 3 polylines", len(insp_one.collect_measure_export_geometry()) == 3, "")

    # --- B. hidden segments skipped; empty -> [] ---
    insp.b_hidden = None
    insp._hidden_measure_segments = {2}
    hidden_geo = insp.collect_measure_export_geometry()
    check("B hidden segment excluded (3 left)", len(hidden_geo) == 3, str(len(hidden_geo)))
    check("B remaining is the visible segment 1", len(hidden_geo) == 3 and np.allclose(hidden_geo[0], [[0, 40, 10], [0, 40, 25]]), "")
    insp_empty = Insp.__new__(Insp)
    insp_empty._measure_segments = []
    insp_empty._hidden_measure_segments = set()
    check("B no segments -> []", insp_empty.collect_measure_export_geometry() == [], "")

    # --- C. _step_export_dimension_polylines: measure dims export toggle-independent ---
    measure_polys = [np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]]), np.asarray([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]])]

    def _phys_service_raise():
        raise AssertionError("physical-distance service must not be touched when the toggle is off")

    insp_off = SimpleNamespace(
        collect_measure_export_geometry=lambda: measure_polys,
        _open3d_thickness_dimension_service=_phys_service_raise,
        _current_scene_bundle=None,
    )
    self_off = SimpleNamespace(
        _three_d_inspector=insp_off,
        show_physical_distances_var=SimpleNamespace(get=lambda: False),
        append_debug=lambda *a, **k: None,
    )
    out_off = Mixin._step_export_dimension_polylines(self_off, None)
    check("C toggle OFF -> measure dims still exported (the fix)", len(out_off) == 2, str(len(out_off)))

    insp_on = SimpleNamespace(
        collect_measure_export_geometry=lambda: measure_polys,
        _open3d_thickness_dimension_service=lambda: SimpleNamespace(
            collect_export_geometry=lambda sysx, sb: [np.asarray([[1.0, 0.0, 0.0], [1.0, 0.0, 2.0]])],
        ),
        _current_scene_bundle=None,
    )
    self_on = SimpleNamespace(
        _three_d_inspector=insp_on,
        show_physical_distances_var=SimpleNamespace(get=lambda: True),
        append_debug=lambda *a, **k: None,
    )
    out_on = Mixin._step_export_dimension_polylines(self_on, None)
    check("C toggle ON -> physical + measure both exported", len(out_on) == 3, str(len(out_on)))

    self_no_insp = SimpleNamespace(
        _three_d_inspector=None,
        show_physical_distances_var=SimpleNamespace(get=lambda: True),
        append_debug=lambda *a, **k: None,
    )
    check("C no 3D inspector -> []", Mixin._step_export_dimension_polylines(self_no_insp, None) == [], "")

    # a measure segment that fails to resolve is skipped, not fatal
    insp_bad = Insp.__new__(Insp)
    insp_bad._measure_segments = [{"id": 3}]  # missing p0/p1 -> resolver returns None
    insp_bad._hidden_measure_segments = set()
    check("C unresolvable segment skipped (not fatal)", insp_bad.collect_measure_export_geometry() == [], "")

    # --- D. same resolver as the on-screen draw loop (export can't drift) ---
    collect_src = inspect.getsource(Insp.collect_measure_export_geometry)
    check(
        "D export reuses the display resolver",
        "_measure_segment_offset_endpoints" in collect_src and "_measure_segment_offsets" in collect_src,
        "",
    )
    draw_src = inspect.getsource(Insp._refresh_measure_overlays)
    check("D on-screen draw uses the same resolver", "_measure_segment_offset_endpoints" in draw_src, "")
    collector_src = inspect.getsource(Mixin._step_export_dimension_polylines)
    check(
        "D export collector calls collect_measure_export_geometry",
        "collect_measure_export_geometry" in collector_src,
        "",
    )
    # the measure absorb must NOT sit under the physical-distance toggle guard.
    idx_toggle = collector_src.find("show_physical_distances_var")
    idx_measure = collector_src.find("collect_measure_export_geometry")
    check(
        "D measure export is not nested under the toggle branch",
        idx_measure > idx_toggle and "if show_var is None or not bool(show_var.get()):\n            return []" not in collector_src,
        "",
    )

    failures = [f"{name} | {detail}" for name, passed, detail in checks if not passed]
    if verbose:
        print("STEP export measure-dimension guard (bugs/0315)")
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
    print("\nSTEP export measure-dimension validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
