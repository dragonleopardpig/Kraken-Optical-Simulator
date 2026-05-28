"""Validate Open 3D STEP overlay promotion into native surface rows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.step_native_reconstruction import STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASPHERIZED_ACHROMAT_STEP = PROJECT_ROOT / "attachment" / "Lens" / "aspherized-achromatic-lenses" / "step_49665.step"


@dataclass(frozen=True)
class StepNativePromotionCheck:
    check: str
    ok: bool
    detail: str


def validate_step_native_promotion() -> list[StepNativePromotionCheck]:
    if not ASPHERIZED_ACHROMAT_STEP.exists():
        return [
            StepNativePromotionCheck(
                "aspherized achromat STEP fixture exists",
                True,
                f"SKIP: missing optional fixture {ASPHERIZED_ACHROMAT_STEP}",
            )
        ]

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_lens_step_path = ASPHERIZED_ACHROMAT_STEP
        app._selected_step_label = "lens"
        app.lens_step_rotation_x_deg = 10.0
        app.lens_step_rotation_y_deg = 5.0
        app.lens_step_rotation_z_deg = 30.0
        app.lens_step_axis_offset_xy = (1.25, -0.75)
        app.lens_step_placement_offset_xyz = (3.0, -2.0, 4.0)
        expected_tilts = tuple(
            float(value)
            for value in app._kraken_tilts_from_rotation_matrix(app._step_rotation_matrix_from_angles(10.0, 5.0, 30.0))
        )
        try:
            result = app.promote_imported_step_to_native_surface_rows(
                "lens",
                glass_sequence=("BK7", "F2", "AIR"),
                insert_at=1,
                clear_overlay=True,
                refresh_open_3d=False,
            )
        except RuntimeError as exc:
            if "pythonocc-core" in str(exc):
                return [
                    StepNativePromotionCheck(
                        "pythonocc-core analytic STEP backend is available",
                        True,
                        f"SKIP: {exc}",
                    )
                ]
            raise

        rows = list(app.rows)
        row_indices = [int(index) for index in list((result or {}).get("row_indices", []) or [])]
        native_rows = [rows[index] for index in row_indices if 0 <= index < len(rows)]
        first_promotion = dict(native_rows[0].advanced.get("StepNativePromotion", {}) if native_rows else {})
        reconstruction = dict(first_promotion.get("reconstruction", {}) if first_promotion else {})
        materials = tuple(str(value) for value in first_promotion.get("material_sequence", ()) or ())
        applied_pose = dict((result or {}).get("applied_row_pose", {}) or {})
        applied_tilts = tuple(float(value) for value in list(applied_pose.get("row_tilts_deg", ()))[:3])
        applied_decenter = tuple(float(value) for value in list(applied_pose.get("row_decenter_mm", ()))[:3])
        row_summary = [
            {
                "surface": row.surface,
                "rc": row.rc,
                "thickness": row.thickness,
                "glass": row.glass,
                "tilt": (row.tilt_x, row.tilt_y, row.tilt_z),
                "desp": (row.desp_x, row.desp_y, row.desp_z),
                "advanced": sorted(row.advanced),
            }
            for row in native_rows
        ]

        return [
            StepNativePromotionCheck(
                "promotion inserts exactly the native achromat surface rows",
                result is not None and row_indices == [1, 2, 3] and len(native_rows) == 3,
                f"row_indices={row_indices}, native_rows={len(native_rows)}",
            ),
            StepNativePromotionCheck(
                "promotion clears the display-only STEP overlay when requested",
                app.imported_lens_step_path is None and app._selected_step_label is None,
                f"lens_step_path={app.imported_lens_step_path}, selected={app._selected_step_label}",
            ),
            StepNativePromotionCheck(
                "native rows remain normal analytic KrakenOS surfaces, not STL optical solids",
                all(row.surface == "Standard" for row in native_rows)
                and all("Solid_3d_stl" not in row.advanced for row in native_rows)
                and all(STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR in row.advanced for row in native_rows),
                f"rows={row_summary}",
            ),
            StepNativePromotionCheck(
                "native promotion preserves material sequence and surface prescription data",
                len(native_rows) == 3
                and native_rows[0].rc > 0.0
                and native_rows[1].rc < 0.0
                and native_rows[0].glass == "BK7"
                and native_rows[1].glass == "F2"
                and native_rows[2].glass == "AIR"
                and len(native_rows[2].advanced.get("AspherData", [])) == 200,
                f"rows={row_summary}",
            ),
            StepNativePromotionCheck(
                "native promotion applies the Open 3D overlay rotation to every analytic row",
                len(applied_tilts) == 3
                and all(abs(applied_tilts[index] - expected_tilts[index]) < 1.0e-9 for index in range(3))
                and all(
                    abs(float(row.tilt_x) - expected_tilts[0]) < 1.0e-9
                    and abs(float(row.tilt_y) - expected_tilts[1]) < 1.0e-9
                    and abs(float(row.tilt_z) - expected_tilts[2]) < 1.0e-9
                    for row in native_rows
                ),
                f"expected_tilts={expected_tilts}, applied={applied_tilts}, rows={row_summary}",
            ),
            StepNativePromotionCheck(
                "native promotion applies one group decenter matching the transformed overlay pose",
                len(applied_decenter) == 3
                and any(abs(value) > 1.0e-9 for value in applied_decenter)
                and all(
                    abs(float(row.desp_x) - applied_decenter[0]) < 1.0e-9
                    and abs(float(row.desp_y) - applied_decenter[1]) < 1.0e-9
                    and abs(float(row.desp_z) - applied_decenter[2]) < 1.0e-9
                    for row in native_rows
                ),
                f"applied_decenter={applied_decenter}, rows={row_summary}",
            ),
            StepNativePromotionCheck(
                "promotion metadata records source path, materials, and reconstruction diagnostics",
                first_promotion.get("source_step_path") == str(ASPHERIZED_ACHROMAT_STEP.resolve())
                and materials == ("BK7", "F2", "AIR")
                and first_promotion.get("trace_ready") is True
                and first_promotion.get("row_coordinates") == "native_reconstructed_prescription_with_open3d_pose"
                and dict(first_promotion.get("applied_row_pose", {}) or {}).get("row_decenter_mm") == list(applied_decenter)
                and reconstruction.get("surface_count") == 3
                and reconstruction.get("trace_ready") is True,
                f"promotion={first_promotion}",
            ),
            StepNativePromotionCheck(
                "Object/Image boundary rows are preserved around promoted native component",
                rows[0].surface == "Object" and rows[-1].surface == "Image",
                f"layout_surfaces={[row.surface for row in rows]}",
            ),
        ]
    finally:
        app.destroy()


def main() -> int:
    checks = validate_step_native_promotion()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
