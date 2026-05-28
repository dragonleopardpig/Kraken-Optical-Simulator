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
        row_summary = [
            {
                "surface": row.surface,
                "rc": row.rc,
                "thickness": row.thickness,
                "glass": row.glass,
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
                "promotion metadata records source path, materials, and reconstruction diagnostics",
                first_promotion.get("source_step_path") == str(ASPHERIZED_ACHROMAT_STEP.resolve())
                and materials == ("BK7", "F2", "AIR")
                and first_promotion.get("trace_ready") is True
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
