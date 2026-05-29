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

from KrakenOS.UI import layout_editor as layout_editor_module
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
        system, _rays, scene_bundle = app._build_preview_system_rays_bundle(
            sampling_mode="world_envelope",
            update_state=False,
        )
        runtime_records = list(getattr(app, "_last_saved_step_native_trace_records", []) or [])
        if not runtime_records:
            failures.append("runtime Open 3D preview did not record saved STEP native trace rows")
        runtime_rows = app._preview_render_rows(scene_bundle)
        if len(runtime_rows) != len(app.rows):
            failures.append(
                "Open 3D saved STEP native trace must render saved table rows, "
                f"not trace-only native rows ({len(runtime_rows)} != {len(app.rows)})"
            )
        if any(str(getattr(row, "name", "")).startswith("Trace-native ") for row in runtime_rows):
            failures.append("trace-only native row leaked into Open 3D render rows")
        trace_rows = list(getattr(app, "_last_saved_step_native_trace_rows", []) or [])
        if not any(
            bool(
                (
                    row.advanced
                    if isinstance(getattr(row, "advanced", None), dict)
                    else {}
                ).get("StepNativePromotion", {}).get("trace_only")
            )
            for row in trace_rows
        ):
            failures.append("native trace rows must remain marked trace_only for diagnostics")
        if system is None:
            failures.append("runtime Open 3D preview did not build a trace system")
        app.imported_lens_step_path = DCV_STEP
        if not app._step_overlay_matches_promoted_row("lens"):
            failures.append("imported STEP overlay matching a promoted saved row must be suppressible")
        layout_editor_module._load_3d_backends()
        if layout_editor_module.pv is not None:
            display_meshes = list(
                app._scene_surface_meshes(
                    system,
                    scene_bundle,
                    include_reference_surfaces=True,
                )
            )
            if not display_meshes:
                failures.append("saved STEP native Open 3D display did not rebuild file-backed display meshes")
            for mesh_item in display_meshes:
                row_index = int(getattr(mesh_item, "row_index", -1))
                if not (0 <= row_index < len(app.rows)):
                    failures.append(f"display mesh row index leaked from trace rows: {row_index}")
                row = getattr(mesh_item, "row", None)
                advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
                if bool(advanced.get("StepNativePromotion", {}).get("trace_only")):
                    failures.append("trace-only native mesh leaked into Open 3D display meshes")
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
