"""Validate saved promoted STEP lenses can trace through native analytic rows.

This covers the common workflow where a vendor lens was inserted as a promoted
STEP/STL row and later reopened from a saved ``.py`` layout.  Display can keep
the saved row contract, but Open 3D tracing should use KrakenOS-native
reconstructed surface rows whenever OpenCascade can recover a trace-ready lens.

Run from the repository root:

    python -m KrakenOS.UI.validate_open3d_saved_step_native_trace
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DCV_STEP = PROJECT_ROOT / "attachment" / "Lens" / "DCV50mm" / "step_32996.stp"


def _fixture_rows(source_path: Path) -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(
            surface="Standard",
            name="Saved promoted DCV STEP solid",
            thickness=40.0,
            diameter=25.0,
            glass="BK7",
            desp_z=-80.0,
            advanced={
                "Solid_3d_stl": "saved_promoted_dcv_fixture.stl",
                "OpticalSolidSourceFormat": "STEP",
                "OpticalSolidSourcePath": str(source_path),
                "StepOverlayPromotion": {
                    "source_step_path": str(source_path),
                    "center_world": [0.0, 0.0, 120.0],
                    "row_thickness_mm": 40.0,
                },
            },
        ),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]


def main() -> int:
    if not DCV_STEP.exists():
        print(f"SKIP: fixture STEP not present: {DCV_STEP}")
        return 0
    failures: list[str] = []
    app = KrakenLayoutEditor(headless=True)
    try:
        app.rows = app._normalized_rows_copy(_fixture_rows(DCV_STEP))
        original_track = sum(float(row.thickness) for row in app.rows)
        rows, records = app._saved_promoted_step_native_trace_rows(app.rows)
        if not records:
            failures.append("saved promoted STEP row was not expanded into trace-native rows")
        if len(rows) <= len(app.rows):
            failures.append(f"native trace row expansion did not add rows: {len(app.rows)} -> {len(rows)}")
        if abs(sum(float(row.thickness) for row in rows) - original_track) > 1.0e-9:
            failures.append("native trace row expansion must preserve total track length")
        curved = [row for row in rows if row.surface == "Standard" and abs(float(row.rc)) > 1.0e-9]
        if len(curved) < 2:
            failures.append("DCV STEP native trace must expose at least two curved refracting surfaces")
        if not any(str(record.get("trace_backend")) == "saved_step_native_analytic_rows" for record in records):
            failures.append("native trace records must report the saved_step_native_analytic_rows backend")
        render_rows = app._preview_render_rows(object())
        if len(render_rows) != len(app.rows):
            failures.append("_preview_render_rows must not switch rows for unrelated scene bundles")
    finally:
        app.destroy()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Saved STEP native trace validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
