"""Validate round lens-like imported STEP face picking contracts."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI import cad_import_service
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services import (
    open3d_face_index_edges,
    open3d_round_lens_pick,
    open3d_scene_refresh,
    open3d_step_overlay_refresh,
)
from KrakenOS.UI.services.open3d_face_index_edges import (
    face_boundary_edges_from_face_index,
    face_outline_from_face_index,
    face_outline_from_face_indices,
    triangle_array_and_face_index,
)
from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
from KrakenOS.UI.services.step_overlay_import import StepOverlayImportService


def _cell_normal(data, cell_id: int) -> np.ndarray | None:
    try:
        cell = data.GetCell(int(cell_id))
        ids = cell.GetPointIds()
        points = np.asarray([data.GetPoint(ids.GetId(index)) for index in range(ids.GetNumberOfIds())], dtype=float)
    except Exception:
        return None
    if points.ndim != 2 or points.shape[0] < 3:
        return None
    normal = np.cross(points[1] - points[0], points[2] - points[0])
    norm = float(np.linalg.norm(normal))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return normal / norm


def main() -> int:
    try:
        import pyvista as pv
    except Exception as exc:
        print(f"Open 3D lens STEP face-pick validation skipped: pyvista unavailable ({exc}).")
        return 0

    failures: list[str] = []
    lens = pv.Cylinder(
        center=(0.0, 0.0, 0.0),
        direction=(0.0, 0.0, 1.0),
        radius=12.5,
        height=4.0,
        resolution=96,
    ).triangulate()
    axis_info = Kraken3DInspector._mesh_round_lens_axis(lens)
    if axis_info is None:
        failures.append("Round lens-like cylinder was not classified as lens-like.")
    else:
        _center, axis, _points = axis_info
        seed = None
        for cell_id in range(int(lens.GetNumberOfCells())):
            normal = _cell_normal(lens, cell_id)
            if normal is not None and abs(float(np.dot(normal, axis))) > 0.75:
                seed = cell_id
                break
        if seed is None:
            failures.append("Could not find a round lens cap cell for validation.")
        else:
            feature = Kraken3DInspector._round_lens_feature_for_cell(lens, seed)
            if feature is None:
                failures.append("Round lens cap cell did not return a grouped optical face feature.")
            else:
                center, outline, normal = feature
                if len(center) != 3 or not np.all(np.isfinite(center)):
                    failures.append("Grouped lens face center is not finite.")
                if len(normal) != 3 or abs(float(np.dot(normal, axis))) < 0.95:
                    failures.append("Grouped lens face normal is not aligned to the inferred lens axis.")
                if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
                    failures.append("Grouped lens face did not produce a clean outline.")

    duplicated_points_mesh = pv.PolyData(
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=float,
        ),
        np.asarray([3, 0, 1, 2, 3, 3, 4, 5], dtype=np.int64),
    )
    duplicated_points_mesh.cell_data["kraken_step_face_index"] = np.asarray([0, 1], dtype=np.int32)
    triangles, face_index = triangle_array_and_face_index(duplicated_points_mesh)
    if triangles.shape != (2, 3, 3) or tuple(int(value) for value in face_index) != (0, 1):
        failures.append("Face-index helper did not preserve duplicated analytic mesh triangle IDs.")
    boundary = face_boundary_edges_from_face_index(duplicated_points_mesh, include_open_boundaries=False)
    if boundary is None or int(getattr(boundary, "n_cells", 0)) != 1:
        failures.append("Face-index edge extraction did not return only the true boundary between analytic faces.")
    outline = face_outline_from_face_index(duplicated_points_mesh, 0)
    if outline is None or int(getattr(outline, "n_cells", 0)) != 3:
        failures.append("Face-index outline extraction did not outline the selected analytic face.")
    grouped_outline = face_outline_from_face_indices(duplicated_points_mesh, (0, 1))
    if grouped_outline is None or int(getattr(grouped_outline, "n_cells", 0)) != 4:
        failures.append("Face-index outline extraction did not merge split analytic face groups.")

    project_root = Path(__file__).resolve().parents[2]
    fixture_paths = (
        project_root / "attachment" / "Lens" / "Achromatic_Lenses" / "step_32323.stp",
        project_root / "attachment" / "Lens" / "aspherized-achromatic-lenses" / "step_49665.step",
    )
    if shutil.which("gmsh") is None:
        print("Open 3D lens STEP face-pick validation: skipping vendor STEP conversion probe because gmsh is unavailable.")
    else:
        with tempfile.TemporaryDirectory(prefix="kraken-lens-step-pick-") as tmp_dir:
            for fixture in fixture_paths:
                if not fixture.exists():
                    print(f"Open 3D lens STEP face-pick validation: skipping missing fixture {fixture}.")
                    continue
                target = Path(tmp_dir) / f"{fixture.stem}.stl"
                cad_import_service.convert_step_to_stl(fixture, target)
                if not cad_import_service.stl_mesh_has_facets(target):
                    failures.append(f"Vendor lens STEP converted to an empty STL: {fixture}")
                    continue
                mesh = pv.read(str(target)).extract_surface(algorithm="dataset_surface").triangulate()
                if int(getattr(mesh, "n_cells", 0)) <= 0:
                    failures.append(f"Vendor lens STEP converted to a mesh with no cells: {fixture}")
                    continue
                if Kraken3DInspector._mesh_round_lens_axis(mesh) is None:
                    failures.append(f"Vendor lens STEP was not classified as a round lens-like body: {fixture}")

    cad_source = __import__("inspect").getsource(cad_import_service)
    if '"-2"' not in cad_source or '"-0"' in cad_source:
        failures.append("STEP conversion must run gmsh meshing with -2, not the no-mesh -0 mode.")
    if "stl_mesh_has_facets" not in cad_source:
        failures.append("STEP conversion must reject cached or newly converted empty STL files.")

    inspector_source = __import__("inspect").getsource(Kraken3DInspector)
    if "_kraken_round_lens_like_step_body" not in inspector_source or "prop.SetEdgeVisibility(0)" not in inspector_source:
        failures.append("Round lens-like STEP selection must suppress raw polygon edge visibility.")
    if "pick_row_index is not None" not in inspector_source or "track_row_index is not None" not in inspector_source:
        failures.append("Round lens-like row-backed optical solids must suppress raw polygon edge visibility too.")
    if "_step_label_is_round_lens_like" not in inspector_source:
        failures.append("Round lens-like STEP labels must bypass tiny-facet metadata picking.")
    if "if self._step_label_is_round_lens_like(label):" not in inspector_source:
        failures.append("Round lens-like STEP clicks must fall back directly to smooth display-region picking.")
    if "_round_lens_feature_for_cell" not in inspector_source or "_mesh_round_lens_axis" not in inspector_source:
        failures.append("Round lens-like STEP face grouping helpers are missing.")
    round_lens_pick_source = __import__("inspect").getsource(open3d_round_lens_pick)
    if "round_lens_feature_for_display_xy" not in round_lens_pick_source or "outer +axis face" not in round_lens_pick_source:
        failures.append("Round lens-like STEP display picking must select exterior cap faces instead of interior tessellation patches.")
    if "_step_feature_pick_for_display_xy" not in inspector_source:
        failures.append("STEP face hover/click code must share the display-safe STEP feature picker.")
    face_index_source = __import__("inspect").getsource(open3d_face_index_edges)
    if "_display_feature_edges_mesh" not in inspector_source or "face_boundary_edges_from_face_index" not in face_index_source:
        failures.append("Open 3D feature-edge drawing must prefer analytic face-index boundaries.")
    if "face_outline_from_face_indices" not in inspector_source:
        failures.append("Open 3D STEP hover outlines must use displayed analytic face-index boundaries.")
    if "face_pick_from_display_mesh" not in inspector_source or "triangle_array_and_face_index" not in face_index_source:
        failures.append("Open 3D STEP ray picking must use displayed analytic face-index triangles before STL fallback.")
    if "camera.Azimuth(dx_f * degrees_per_pixel)" not in inspector_source or "camera.Elevation(-dy_f * degrees_per_pixel)" not in inspector_source:
        failures.append("Open 3D fixed left-drag camera rotation must use the restored screen-following sign convention.")
    refresh_source = __import__("inspect").getsource(open3d_step_overlay_refresh)
    if "boundary_edges=not round_lens_like" not in refresh_source:
        failures.append("Round lens-like STEP rendering must suppress tessellation patch-boundary edge overlays.")
    scene_refresh_source = __import__("inspect").getsource(open3d_scene_refresh)
    if "row_round_lens_like" not in scene_refresh_source or "boundary_edges=row_edge_boundary_edges" not in scene_refresh_source:
        failures.append("Row-backed round lens-like optical solids must suppress tessellation patch-boundary edge overlays.")
    if "round_lens_like = bool(self._mesh_round_lens_axis(cad_mesh) is not None)" not in scene_refresh_source or "boundary_edges=not round_lens_like" not in scene_refresh_source:
        failures.append("Imported round lens-like STEP overlays must suppress tessellation patch-boundary edge overlays in full scene refreshes.")
    interaction_class_source = __import__("inspect").getsource(Open3DInteractionService)
    interaction_source = __import__("inspect").getsource(Open3DInteractionService._on_mouse_move)
    if "carry_label = self._step_carry_label()" not in interaction_source or "target_label = str(carry_label)" not in interaction_source:
        failures.append("Carry-mode imported STEP hover must pick the active STEP face, not only rotation handles.")
    if "_step_feature_pick_for_display_xy" not in interaction_source:
        failures.append("Active imported STEP hover must use the display-safe STEP feature picker.")
    if "_step_feature_pick_for_display_xy" not in interaction_class_source:
        failures.append("Imported STEP click selection must use the display-safe STEP feature picker.")
    import_source = __import__("inspect").getsource(StepOverlayImportService.import_optical_step)
    if "_optical_prescription_sidecars" not in import_source or "STEP has no glass prescription" not in import_source:
        failures.append("Optical STEP import should warn when a sidecar prescription is needed for designed lens focus.")

    if failures:
        print("Open 3D lens STEP face-pick validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Open 3D lens STEP face-pick validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
