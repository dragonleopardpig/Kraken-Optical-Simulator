"""Validate Open 3D STEP overlay promotion to optical solid rows."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, transformed_stl_bounds
from KrakenOS.UI.scene_placement import SCENE_PLACEMENT_ADVANCED_ATTR, normalize_scene_placement_settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"
VALIDATION_CACHE_DIR = Path("/tmp/kraken-step-promotion-cache")


def _mesh_center(mesh) -> np.ndarray:
    bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
    return np.asarray(
        (
            0.5 * (float(bounds[0]) + float(bounds[1])),
            0.5 * (float(bounds[2]) + float(bounds[3])),
            0.5 * (float(bounds[4]) + float(bounds[5])),
        ),
        dtype=float,
    )


def main() -> int:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected tracked STEP fixture: {PRISM_42779_STEP}")

    le.CAD_CACHE_DIR = VALIDATION_CACHE_DIR / "cad"
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_lens_step_path = PRISM_42779_STEP
        app.lens_step_rotation_x_deg = 90.0
        app.lens_step_rotation_y_deg = 0.0
        app.lens_step_rotation_z_deg = 90.0
        app.lens_step_axis_offset_xy = (1.25, -0.75)
        app.lens_step_placement_offset_xyz = (4.0, -2.0, 8.0)
        app.select_step_component("lens")

        overlay_mesh = app._transformed_imported_step_mesh_for_label("lens")
        if overlay_mesh is None or int(getattr(overlay_mesh, "n_points", 0)) <= 0:
            raise AssertionError("Expected a transformed lens STEP overlay mesh.")
        overlay_center = _mesh_center(overlay_mesh)

        result = app.promote_imported_step_to_optical_solid_row(
            "lens",
            insert_at=1,
            open_face_editor=False,
        )
        if result is None:
            raise AssertionError("STEP promotion returned no result.")
        row_index = int(result["row_index"])
        row = app.rows[row_index]
        advanced = dict(row.advanced or {})
        mesh_path = Path(str(advanced.get("Solid_3d_stl", "")))
        if row.surface != "Standard" or not mesh_path.exists() or mesh_path.suffix.lower() != ".stl":
            raise AssertionError(f"Promoted row is not a file-backed optical solid row: {row!r}")
        if abs(float(row.axis_move)) > 1e-12:
            raise AssertionError("Promoted STEP optical solid must not propagate its row pose through AxisMove.")
        if float(row.thickness) <= 0.0:
            raise AssertionError("Promoted STEP optical solid must reserve positive axial thickness.")
        if str(advanced.get("OpticalSolidSourcePath", "")) != str(PRISM_42779_STEP.resolve()):
            raise AssertionError("Promoted row did not preserve the original STEP source path.")
        if str(advanced.get("OpticalSolidSourceFormat", "")).upper() != "STEP":
            raise AssertionError("Promoted row did not preserve STEP source format.")

        promotion = dict(advanced.get("StepOverlayPromotion", {}) or {})
        if promotion.get("step_label") != "lens":
            raise AssertionError(f"Promotion metadata has wrong label: {promotion!r}")
        if promotion.get("mesh_coordinates") != "local_centered_from_open3d_overlay":
            raise AssertionError("Promotion metadata does not declare locally centered mesh coordinates.")
        metadata_center = np.asarray(promotion.get("center_world", (np.nan, np.nan, np.nan)), dtype=float)
        if not np.allclose(metadata_center[:3], overlay_center[:3], atol=1e-6):
            raise AssertionError(f"Promotion center metadata drifted: {metadata_center!r} != {overlay_center!r}")
        if float(promotion.get("row_thickness_mm", 0.0) or 0.0) != float(row.thickness):
            raise AssertionError("Promotion metadata did not preserve the row axial thickness.")

        placement = normalize_scene_placement_settings(advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        if placement.get("promotion_source") != "open3d_step_overlay":
            raise AssertionError(f"ScenePlacement did not preserve promotion source: {placement!r}")
        if placement.get("promotion_step_label") != "lens":
            raise AssertionError(f"ScenePlacement did not preserve STEP label: {placement!r}")

        z_station = app._stl_row_z_station(row_index)
        if row_index + 1 < len(app.rows) and app.rows[row_index + 1].surface == "Image":
            image_station = app._stl_row_z_station(row_index + 1)
            if image_station <= z_station:
                raise AssertionError(
                    "Promoted STEP optical solid did not push the downstream Image station beyond the solid row."
                )
        _bounds_min, _bounds_max, promoted_center = transformed_stl_bounds(
            mesh_path,
            (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)),
            (float(row.desp_x), float(row.desp_y), float(row.desp_z)),
            z_station,
        )
        if not np.allclose(promoted_center[:3], overlay_center[:3], atol=1e-6):
            raise AssertionError(
                "Promoted optical solid row does not land at the original Open 3D STEP overlay center: "
                f"{promoted_center!r} != {overlay_center!r}"
            )
        diagnostics = result.get("diagnostics")
        if diagnostics is None or int(getattr(diagnostics, "triangle_count", 0)) <= 0:
            raise AssertionError(f"Promotion diagnostics missing triangle data: {diagnostics!r}")
    finally:
        app.destroy()

    print("STEP promotion optical solid validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
