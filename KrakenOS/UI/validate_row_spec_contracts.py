"""Validate row-spec contract helpers live outside the Tk editor coordinator."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.services.advanced_surface_attrs import (
    _advanced_surface_attrs_from_spec,
    _canonical_advanced_surface_attr,
)
from KrakenOS.UI.services.row_spec_contracts import _requires_scalar_trace, _row_specs_signature


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (PROJECT_ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    attrs = _advanced_surface_attrs_from_spec(
        {
            "surface": "Standard",
            "advanced": {"beam splitter": {"reflectance": 0.5}, "Element": {"arm": "Common"}},
            "surface_attrs": {"diffuse scatter": {"model": "Lambertian"}},
            "Element": {"arm": "Ignored top-level row label"},
        }
    )
    if attrs.get("BeamSplitter", {}).get("reflectance") != 0.5:
        failures.append("Advanced BeamSplitter alias was not normalized.")
    if attrs.get("DiffuseScatter", {}).get("model") != "Lambertian":
        failures.append("Advanced DiffuseScatter alias was not normalized.")
    if attrs.get("Element", {}).get("arm") != "Common":
        failures.append("Direct Element advanced attribute was not preserved.")
    if _canonical_advanced_surface_attr("solid 3d stl") != "Solid_3d_stl":
        failures.append("Advanced surface compact alias lookup failed.")

    base_specs = [
        {
            "surface": "Standard",
            "name": "S1",
            "rc": 10.0,
            "thickness": 5.0,
            "diameter": 20.0,
            "glass": "BK7",
            "extra_data": np.asarray([1.0, 2.0, 3.0]),
            "advanced": {"Note": "base"},
        }
    ]
    base_signature = _row_specs_signature(base_specs)
    changed_specs = [dict(base_specs[0], advanced={"Note": "changed"})]
    if _row_specs_signature(changed_specs) == base_signature:
        failures.append("Row signature did not include advanced surface attributes.")
    metal_specs = [dict(base_specs[0], _metal_catalogs=[{"name": "Gold custom", "path": "/tmp/gold.csv", "type": 0}])]
    if _row_specs_signature(metal_specs)[0] == base_signature[0]:
        failures.append("Row signature did not include metal catalog metadata.")

    if _requires_scalar_trace([{"surface": "Standard", "tilt_x": 0.0, "axicon": 0.0}]):
        failures.append("Plain centered standard row should not force scalar tracing.")
    if not _requires_scalar_trace([{"surface": "Standard", "tilt_x": 1.0}]):
        failures.append("Tilted row should force scalar tracing.")
    if not _requires_scalar_trace([{"surface": "Beam Splitter"}]):
        failures.append("Beam Splitter row should force scalar tracing.")

    layout_source = _source("KrakenOS/UI/layout_editor.py")
    for forbidden in (
        "def _row_specs_signature(",
        "def _requires_scalar_trace(",
        "def _surface_signature_token(",
        "def _advanced_surface_attrs_from_spec(",
    ):
        if forbidden in layout_source:
            failures.append(f"layout_editor.py still defines {forbidden}")

    bridge_checks = {
        "KrakenOS/UI/services/trace_preview_sampling.py": "_layout_module()._row_specs_signature",
        "KrakenOS/UI/services/three_d_scene_tools.py": "_layout_module()._row_specs_signature",
        "KrakenOS/UI/services/paraxial_tools.py": "_layout_module()._row_specs_signature",
        "KrakenOS/UI/services/analysis_reports.py": "_layout_module()._requires_scalar_trace",
        "KrakenOS/UI/services/trace_preview.py": "le._requires_scalar_trace",
        "KrakenOS/UI/services/layout_import_export.py": "_layout_module()._advanced_surface_attrs_from_spec",
    }
    for relative, forbidden in bridge_checks.items():
        if forbidden in _source(relative):
            failures.append(f"{relative} still bridges through layout_editor for {forbidden}")

    if failures:
        print("Row-spec contract validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Row-spec contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
