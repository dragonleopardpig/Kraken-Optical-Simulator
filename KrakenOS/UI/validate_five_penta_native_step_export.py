"""Validate native STEP export for the saved five-penta cascade layout.

This guard loads the saved row-backed five-penta `.py` layout, exports it
through the same native CAD + ray-envelope path used by the UI, and fails if:

1. the exporter falls back to faceted shell geometry;
2. the saved row metadata does not recover the original vendor STEP solids;
3. the exported native bodies are written in a coordinate frame detached from
   the traced raykeeper paths;
4. the exported STEP omits the ray envelope.
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from KrakenOS.UI.layout_editor import _write_step_with_cad_shapes_and_rays
from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts
from KrakenOS.UI.services.cad_step_export import _read_step_shape, _shape_with_affine
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import DEFAULT_LAYOUT_PATH, _load_saved_layout
from KrakenOS.UI.validate_step_native_export import _topology_counts
from KrakenOS.UI.layout_editor import KrakenLayoutEditor


OUTPUT_PATH = Path("/tmp/kraken_five_penta_native_export.step")
MAX_REASONABLE_FACE_COUNT = 1000
MAX_ALIGNMENT_ERROR_MM = 0.75


def _sample_points(points: np.ndarray, limit: int = 600) -> np.ndarray:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] <= limit:
        return pts
    indices = np.linspace(0, pts.shape[0] - 1, limit, dtype=int)
    return pts[indices]


def _nearest_distance_stats(source_points: np.ndarray, target_points: np.ndarray) -> dict[str, float]:
    source = _sample_points(source_points, 600)
    target = _sample_points(target_points, 2000)
    if source.ndim != 2 or target.ndim != 2 or source.shape[0] == 0 or target.shape[0] == 0:
        return {"max": float("inf"), "p95": float("inf"), "mean": float("inf")}
    deltas = source[:, None, :3] - target[None, :, :3]
    distances = np.linalg.norm(deltas, axis=2)
    nearest = np.min(distances, axis=1)
    return {
        "max": float(np.max(nearest)),
        "p95": float(np.percentile(nearest, 95.0)),
        "mean": float(np.mean(nearest)),
    }


def _mesh_with_affine_copy(mesh, matrix: np.ndarray):
    transformed = mesh.copy(deep=True)
    transformed.transform(np.asarray(matrix, dtype=float), inplace=True)
    return transformed


def _roundtrip_export_body_alignment(export_path: Path, target_meshes: list[dict[str, object]]) -> list[dict[str, object]]:
    try:
        import pyvista as pv
        from OCC.Core.Bnd import Bnd_Box
        from OCC.Core.BRepBndLib import brepbndlib
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.StlAPI import StlAPI_Writer
        from OCC.Core.TopAbs import TopAbs_SOLID
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
    except Exception as exc:
        return [{"error": f"roundtrip_unavailable: {exc}"}]

    reader = STEPControl_Reader()
    status = reader.ReadFile(str(export_path))
    if int(status) != 1:
        return [{"error": f"step_read_failed: status={status}"}]
    reader.TransferRoots()
    shape = reader.OneShape()
    if shape.IsNull():
        return [{"error": "step_read_failed: null_shape"}]

    candidates: list[dict[str, object]] = []
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    with TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        solid_index = 0
        while explorer.More():
            solid_index += 1
            solid = topods.Solid(explorer.Current())
            box = Bnd_Box()
            brepbndlib.Add(solid, box)
            xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
            span = np.asarray((xmax - xmin, ymax - ymin, zmax - zmin), dtype=float)
            explorer.Next()
            if float(np.min(span)) <= 5.0 or float(np.max(span)) <= 20.0:
                continue
            stl_path = temp_root / f"solid_{solid_index}.stl"
            BRepMesh_IncrementalMesh(solid, 0.5, False, 0.5, True).Perform()
            StlAPI_Writer().Write(solid, str(stl_path))
            try:
                mesh = pv.read(stl_path)
            except Exception:
                continue
            candidates.append(
                {
                    "solid_index": int(solid_index),
                    "span": [float(value) for value in span],
                    "mesh": mesh,
                }
            )

        if not candidates:
            return [{"error": "no_roundtrip_body_candidates"}]

        remaining = list(candidates)
        alignment: list[dict[str, object]] = []
        for target in target_meshes:
            target_points = np.asarray(target["mesh"].points, dtype=float)
            best_index = -1
            best_stats: dict[str, float] | None = None
            for candidate_index, candidate in enumerate(remaining):
                stats = _nearest_distance_stats(
                    np.asarray(candidate["mesh"].points, dtype=float),
                    target_points,
                )
                if best_stats is None or (
                    float(stats["p95"]),
                    float(stats["mean"]),
                    float(stats["max"]),
                ) < (
                    float(best_stats["p95"]),
                    float(best_stats["mean"]),
                    float(best_stats["max"]),
                ):
                    best_index = candidate_index
                    best_stats = stats
            if best_index < 0 or best_stats is None:
                alignment.append(
                    {
                        "row_index": int(target["row_index"]),
                        "name": str(target["name"]),
                        "error": "no_matching_roundtrip_solid",
                    }
                )
                continue
            candidate = remaining.pop(best_index)
            alignment.append(
                {
                    "row_index": int(target["row_index"]),
                    "name": str(target["name"]),
                    "solid_index": int(candidate["solid_index"]),
                    "span": list(candidate["span"]),
                    "max": float(best_stats["max"]),
                    "p95": float(best_stats["p95"]),
                    "mean": float(best_stats["mean"]),
                }
            )
        return alignment


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
        alignment: list[dict[str, object]] = []
        runtime_target_meshes: list[dict[str, object]] = []
        try:
            import pyvista as pv
        except Exception:
            pv = None
        surfaces = getattr(system, "AAA", None)
        transforms = getattr(system, "TRANS_2A", None)
        if pv is not None and surfaces is not None and transforms is not None:
            block_count = min(len(app.rows), getattr(surfaces, "n_blocks", 0), len(transforms))
            for row_index in range(block_count):
                row = app.rows[row_index]
                source_path = app._resolve_row_saved_step_source_path(row)
                if source_path is None:
                    continue
                matrix = app._row_native_step_alignment_affine(source_path, row_index, system)
                if matrix is None:
                    try:
                        source_mesh = app._load_step_mesh(source_path, largest_component=False)
                        target_mesh = surfaces[row_index].copy(deep=True)
                        matrix = app._mesh_icp_affine(source_mesh, target_mesh)
                    except Exception:
                        matrix = None
                if matrix is None:
                    debug_entry = {"row_index": row_index, "name": row.name, "error": "missing_alignment_matrix"}
                    try:
                        source_mesh = app._load_step_mesh(source_path, largest_component=False)
                        debug_entry["source_points"] = int(getattr(source_mesh, "n_points", 0))
                        debug_entry["source_cells"] = int(getattr(source_mesh, "n_cells", 0))
                        target_mesh = surfaces[row_index].copy(deep=True)
                        debug_entry["world_points"] = int(getattr(target_mesh, "n_points", 0))
                        debug_entry["world_cells"] = int(getattr(target_mesh, "n_cells", 0))
                        debug_entry["icp_world_available"] = bool(app._mesh_icp_affine(source_mesh, target_mesh) is not None)
                    except Exception as exc:
                        debug_entry["debug_error"] = str(exc)
                    alignment.append(
                        debug_entry
                    )
                    continue
                source_mesh = app._load_step_mesh(source_path, largest_component=False)
                world_mesh = _mesh_with_affine_copy(source_mesh, matrix)
                target_mesh = surfaces[row_index].copy(deep=True)
                stats = _nearest_distance_stats(
                    np.asarray(world_mesh.points, dtype=float),
                    np.asarray(target_mesh.points, dtype=float),
                )
                stats.update({"row_index": row_index, "name": row.name})
                alignment.append(stats)
        if surfaces is not None and transforms is not None and pv is not None:
            block_count = min(len(app.rows), getattr(surfaces, "n_blocks", 0), len(transforms))
            for row_index in range(block_count):
                row = app.rows[row_index]
                source_path = app._resolve_row_saved_step_source_path(row)
                if source_path is None:
                    continue
                runtime_target_meshes.append(
                    {
                        "row_index": int(row_index),
                        "name": str(row.name),
                        "mesh": surfaces[row_index].copy(deep=True),
                    }
                )
        native_row_export: list[dict[str, object]] = []
        if surfaces is not None and transforms is not None:
            block_count = min(len(app.rows), getattr(surfaces, "n_blocks", 0), len(transforms))
            for row_index in range(block_count):
                row = app.rows[row_index]
                source_path = app._resolve_row_saved_step_source_path(row)
                if source_path is None:
                    continue
                entry = {
                    "row_index": row_index,
                    "name": row.name,
                    "source_path": str(source_path),
                }
                try:
                    source_mesh = app._load_step_mesh(source_path, largest_component=False)
                    target_mesh = surfaces[row_index].copy(deep=True)
                    z_station = sum(float(getattr(previous_row, "thickness", 0.0) or 0.0) for previous_row in app.rows[:row_index])
                    source_to_trace = np.eye(4, dtype=float)
                    source_to_trace[:3, :3] = np.asarray(
                        rotation_matrix_from_kraken_tilts(
                            float(getattr(row, "tilt_x", 0.0) or 0.0),
                            float(getattr(row, "tilt_y", 0.0) or 0.0),
                            float(getattr(row, "tilt_z", 0.0) or 0.0),
                        ),
                        dtype=float,
                    )
                    source_to_trace[:3, 3] = np.asarray(
                        [
                            float(getattr(row, "desp_x", 0.0) or 0.0),
                            float(getattr(row, "desp_y", 0.0) or 0.0),
                            float(z_station) + float(getattr(row, "desp_z", 0.0) or 0.0),
                        ],
                        dtype=float,
                    )
                    double_transform = np.asarray(transforms[row_index], dtype=float) @ source_to_trace
                    entry["direct_trace_frame_stats"] = _nearest_distance_stats(
                        np.asarray(_mesh_with_affine_copy(source_mesh, source_to_trace).points, dtype=float),
                        np.asarray(target_mesh.points, dtype=float),
                    )
                    entry["legacy_double_transform_stats"] = _nearest_distance_stats(
                        np.asarray(_mesh_with_affine_copy(source_mesh, double_transform).points, dtype=float),
                        np.asarray(target_mesh.points, dtype=float),
                    )
                    matrix = app._row_native_step_alignment_affine(source_path, row_index, system)
                    entry["matrix_ok"] = bool(matrix is not None)
                    if matrix is not None:
                        shape = _read_step_shape(source_path)
                        transformed = _shape_with_affine(shape, matrix)
                        entry["shape_null"] = bool(transformed.IsNull())
                except Exception as exc:
                    entry["error"] = str(exc)
                native_row_export.append(entry)
        analytic_count, cad_count, ray_count = _write_step_with_cad_shapes_and_rays(
            system,
            app.rows,
            cad_shapes,
            ray_polylines,
            OUTPUT_PATH,
        )
        text = OUTPUT_PATH.read_text(encoding="utf-8", errors="ignore")
        topology = _topology_counts(OUTPUT_PATH)
        roundtrip_alignment = _roundtrip_export_body_alignment(OUTPUT_PATH, runtime_target_meshes)
        report = {
            "layout": str(DEFAULT_LAYOUT_PATH),
            "output": str(OUTPUT_PATH),
            "analytic_count": int(analytic_count),
            "cad_count": int(cad_count),
            "cad_shape_items": int(len(cad_shapes)),
            "cad_shape_labels": [str(label) for label, _shape in cad_shapes],
            "ray_count": int(ray_count),
            "manifold_solid_brep": int(text.count("MANIFOLD_SOLID_BREP")),
            "advanced_face": int(text.count("ADVANCED_FACE")),
            "topology": topology,
            "bytes": int(OUTPUT_PATH.stat().st_size if OUTPUT_PATH.exists() else 0),
            "alignment": alignment,
            "roundtrip_alignment": roundtrip_alignment,
            "native_row_export": native_row_export,
            "debug_tail": list(getattr(app, "debug_messages", [])[-20:]),
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
            (
                "native cad alignment stayed on traced bodies",
                bool(alignment) and all(float(item.get("p95", float("inf"))) <= MAX_ALIGNMENT_ERROR_MM for item in alignment),
            ),
            (
                "serialized step bodies stayed on traced bodies",
                bool(roundtrip_alignment)
                and all(float(item.get("p95", float("inf"))) <= MAX_ALIGNMENT_ERROR_MM for item in roundtrip_alignment),
            ),
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
