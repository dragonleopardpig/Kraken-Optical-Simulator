"""Display-free guard for bugs/0316 -- the exported STEP dimensions must carry
ARROWHEADS and the numeric VALUE TEXT, not "only lines".

flag_20260715_125033_313 ("refer freecad.png, the output of the thickness overlay
is only lines, no arrow, no text"): bugs/0313 + 0315 export each dimension as a
shaft + two leader lines only. The STEP writer tubes a polyline segment-by-segment
(``for start, end in zip(pts[:-1], pts[1:])``), so richer geometry needs no writer
change -- it only needs to be EMITTED. The pythonocc build here has no
``OCC.Core.Font`` and the project forbids external deps, so the number is drawn
with an in-process vector stroke font; arrowheads are open barb chevrons.

``dimension_export_geometry.dimension_annotation_polylines(base_lo, base_hi, start,
end)`` is the single funnel both the blue physical-distance overlay
(``_record_export_dimension``) and the orange Measure tool
(``collect_measure_export_geometry``) call.

  (A) STABLE trio: the first three polylines are byte-for-byte the pre-0316 output
      (shaft + two leaders, exact endpoints) -- 0313/0315 endpoint asserts survive.
  (B) ARROWHEADS: two 3-point barb chevrons follow the trio, tips exactly on the
      shaft ends, wings spread in the dimension plane.
  (C) VALUE TEXT: the numeric span (``dimension_value_text``) is stroked; the count
      matches ``annotation_polyline_count`` and every glyph in the string resolves.
  (D) COPLANAR: the ENTIRE annotation (trio + barbs + text) lies in one plane
      (shaft x out_dir) -- it reads as a flat dimension, never a supernatural
      scribble in 3-space.
  (E) REAL WRITER: fed as ``dimension_polylines`` to the OCC writer, every polyline
      tubes (dimension_count == polyline count) and each segment becomes a solid.
  (F) ONE FUNNEL: both collectors route through ``dimension_annotation_polylines``.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_export_dimension_annotations
Exit: 0 = pass, 1 = regression.
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


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as Insp
    from KrakenOS.UI.services import cad_step_export as ce
    from KrakenOS.UI.services import dimension_export_geometry as D
    from KrakenOS.UI.services.open3d_thickness_dimensions import (
        Open3DThicknessDimensionService as Svc,
    )

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append((name, bool(passed), str(detail)))

    # a thickness dimension along +z (span 32.92 mm), offset +y by 45.
    lo = np.array([0.0, 0.0, 0.0])
    hi = np.array([0.0, 0.0, 32.92])
    a = lo + np.array([0.0, 45.0, 0.0])
    b = hi + np.array([0.0, 45.0, 0.0])
    span = float(np.linalg.norm(b - a))
    polys = D.dimension_annotation_polylines(lo, hi, a, b)
    value = D.dimension_value_text(span)

    # --- A. STABLE trio (pre-0316 output, exact endpoints) ---
    check("A shaft is polyline 0", np.allclose(polys[0], [a, b]), str(polys[0].tolist()))
    check("A leader base_lo->start is polyline 1", np.allclose(polys[1], [lo, a]), str(polys[1].tolist()))
    check("A leader base_hi->end is polyline 2", np.allclose(polys[2], [hi, b]), str(polys[2].tolist()))
    check("A every polyline is a finite Nx3 path", all(p.ndim == 2 and p.shape[0] >= 2 and p.shape[1] == 3 and np.all(np.isfinite(p)) for p in polys), "")

    # --- B. arrowheads: two 3-point barb chevrons, tips on the shaft ends ---
    barb0, barb1 = polys[D.STABLE_PREFIX], polys[D.STABLE_PREFIX + 1]
    check("B barb 0 is a 3-point chevron", barb0.shape == (3, 3), str(barb0.shape))
    check("B barb 1 is a 3-point chevron", barb1.shape == (3, 3), str(barb1.shape))
    check("B barb 0 tip sits on shaft start", np.allclose(barb0[1], a), str(barb0[1].tolist()))
    check("B barb 1 tip sits on shaft end", np.allclose(barb1[1], b), str(barb1[1].tolist()))
    # wings straddle the shaft (one on each side of the dimension line)
    shaft_dir = (b - a) / span
    out_dir = (a - lo) / float(np.linalg.norm(a - lo))
    w0a = float(np.dot(barb0[0] - a, out_dir))
    w0b = float(np.dot(barb0[2] - a, out_dir))
    check("B barb wings straddle the shaft", w0a * w0b < 0, f"{w0a:.3f}/{w0b:.3f}")

    # --- C. value text: numeric span, stroked, count matches, glyphs resolve ---
    check("C value text is the numeric span", value == "32.92 mm", value)
    check("C polyline count == annotation_polyline_count", len(polys) == D.annotation_polyline_count(value), f"{len(polys)} vs {D.annotation_polyline_count(value)}")
    text_polys = polys[D.STABLE_PREFIX + 2:]
    expect_strokes = sum(len(D.GLYPHS.get(ch, ())) for ch in value)
    check("C text stroke count == sum of glyph strokes", len(text_polys) == expect_strokes, f"{len(text_polys)} vs {expect_strokes}")
    check("C every glyph in the value resolves", all(ch in D.GLYPHS for ch in value), value)
    check("C space glyph is empty, digits are non-empty", D.GLYPHS[" "] == [] and all(len(D.GLYPHS[str(d)]) >= 2 for d in range(10)), "")
    # formatting rounds via %g and always carries the unit
    check("C dimension_value_text rounds + carries mm", D.dimension_value_text(12.34567) == "12.35 mm" and D.dimension_value_text(5.0) == "5 mm", D.dimension_value_text(12.34567))

    # --- D. the WHOLE annotation is coplanar (flat dimension, not a 3D scribble) ---
    normal = np.cross(shaft_dir, out_dir)
    normal = normal / float(np.linalg.norm(normal))
    max_off = max(float(np.max(np.abs((p - a) @ normal))) for p in polys)
    check("D entire annotation is coplanar", max_off < 1e-6, f"max off-plane {max_off:.2e}")

    # --- E. real OCC writer tubes every polyline; each segment becomes a solid ---
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

    box = BRepPrimAPI_MakeBox(10.0, 6.0, 4.0).Shape()
    system = SimpleNamespace(SDT=[], TRANS_2A=[])
    out_base = Path("/tmp/kraken_dim_annot_base.step")
    out_ann = Path("/tmp/kraken_dim_annot_full.step")
    _, _, _, d_base = ce._write_step_with_cad_shapes_and_rays(system, [], [("box", box)], [], out_base)
    _, _, _, d_ann = ce._write_step_with_cad_shapes_and_rays(system, [], [("box", box)], [], out_ann, dimension_polylines=polys)
    check("E writer counts every annotation polyline", d_ann == len(polys), f"{d_ann} vs {len(polys)}")
    total_segments = sum(int(p.shape[0]) - 1 for p in polys)
    added = _topology_solid_count(out_ann) - _topology_solid_count(out_base)
    check("E every polyline segment becomes a solid tube", added == total_segments, f"{added} vs {total_segments}")

    # --- F. one funnel: both collectors route through the shared helper ---
    rec_src = inspect.getsource(Svc._record_export_dimension)
    check("F physical-distance export uses the shared helper", "dimension_annotation_polylines" in rec_src, "")
    meas_src = inspect.getsource(Insp.collect_measure_export_geometry)
    check("F measure export uses the shared helper", "dimension_annotation_polylines" in meas_src, "")

    # --- G. degenerate dimension keeps the trio, adds nothing ---
    deg = D.dimension_annotation_polylines(lo, lo, a, a)
    check("G degenerate span -> trio only", len(deg) == D.STABLE_PREFIX, str(len(deg)))

    failures = [f"{name} | {detail}" for name, passed, detail in checks if not passed]
    if verbose:
        print("STEP export dimension-annotation guard (bugs/0316)")
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
    print("\nSTEP export dimension-annotation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
