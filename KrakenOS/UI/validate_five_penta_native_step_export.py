"""Validate native STEP export for the saved five-penta cascade layout.

This guard loads the saved row-backed five-penta `.py` layout, exports it
through the same native CAD + ray-envelope path used by the UI, and fails if:

1. the exporter falls back to faceted shell geometry;
2. the saved row metadata does not recover the original vendor STEP solids;
3. the exported STEP omits the ray envelope.
"""

from __future__ import annotations

import json
from pathlib import Path

from KrakenOS.UI.layout_editor import _write_step_with_cad_shapes_and_rays
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import DEFAULT_LAYOUT_PATH, _load_saved_layout
from KrakenOS.UI.validate_step_native_export import _topology_counts
from KrakenOS.UI.layout_editor import KrakenLayoutEditor


OUTPUT_PATH = Path("/tmp/kraken_five_penta_native_export.step")
MAX_REASONABLE_FACE_COUNT = 1000


def main() -> int:
    if not DEFAULT_LAYOUT_PATH.exists():
        print(f"missing saved five-penta layout: {DEFAULT_LAYOUT_PATH}")
        return 1

    app = KrakenLayoutEditor(headless=True)
    try:
        _load_saved_layout(app, DEFAULT_LAYOUT_PATH)
        system = app.build_system()
        cad_shapes = app._collect_native_step_export_shapes(system)
        ray_polylines = app._step_export_ray_polylines(system)
        analytic_count, cad_count, ray_count = _write_step_with_cad_shapes_and_rays(
            system,
            app.rows,
            cad_shapes,
            ray_polylines,
            OUTPUT_PATH,
        )
        text = OUTPUT_PATH.read_text(encoding="utf-8", errors="ignore")
        topology = _topology_counts(OUTPUT_PATH)
        report = {
            "layout": str(DEFAULT_LAYOUT_PATH),
            "output": str(OUTPUT_PATH),
            "analytic_count": int(analytic_count),
            "cad_count": int(cad_count),
            "ray_count": int(ray_count),
            "manifold_solid_brep": int(text.count("MANIFOLD_SOLID_BREP")),
            "advanced_face": int(text.count("ADVANCED_FACE")),
            "topology": topology,
            "bytes": int(OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0),
        }
        print("Five-penta native STEP export validation")
        print(json.dumps(report, indent=2, sort_keys=True))

        checks = [
            ("cad shapes recovered from saved rows", cad_count >= 5),
            ("ray envelope exported", ray_count >= 1),
            ("native brep entities present", report["manifold_solid_brep"] >= 5),
            ("face count stayed well below faceted fallback", report["advanced_face"] < MAX_REASONABLE_FACE_COUNT),
            ("reader transferred shape", topology.get("status") == 1 and topology.get("transferred", 0) >= 1),
            ("reader saw multiple solids", topology.get("solids", 0) >= 10),
        ]
        failed = False
        for label, passed in checks:
            print(f"{label}: {'PASS' if passed else 'FAIL'}")
            failed = failed or not passed
        return 1 if failed else 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
