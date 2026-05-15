import numpy as np


KRAKEN_ORIGINAL_CELL_ID = "KrakenOriginalCellId"
KRAKEN_FACE_ID = "KrakenFaceId"


class MeshRayTraceError(RuntimeError):
    """Raised when a scene mesh cannot satisfy KrakenOS ray-intersection needs."""


def _mesh_type_name(mesh):
    try:
        return type(mesh).__name__
    except Exception:
        return "<unknown>"


def _extract_surface(mesh):
    try:
        return mesh.extract_surface(algorithm="dataset_surface")
    except TypeError:
        return mesh.extract_surface()


def _with_cell_normals(mesh):
    try:
        normals = np.asarray(mesh.cell_normals, dtype=float)
        if normals.ndim == 2 and normals.shape[1] == 3:
            return mesh
    except Exception:
        pass
    if not hasattr(mesh, "compute_normals"):
        return mesh
    try:
        return mesh.compute_normals(
            cell_normals=True,
            point_normals=True,
            split_vertices=True,
            flip_normals=False,
            consistent_normals=True,
            auto_orient_normals=False,
            non_manifold_traversal=True,
            feature_angle=30.0,
            inplace=False,
        )
    except TypeError:
        try:
            return mesh.compute_normals(cell_normals=True, point_normals=True, inplace=False)
        except Exception:
            return mesh
    except Exception:
        return mesh


def _ensure_original_cell_ids(mesh):
    try:
        cell_count = int(getattr(mesh, "n_cells", 0))
    except Exception:
        return mesh
    if cell_count <= 0:
        return mesh
    try:
        existing = np.asarray(mesh.cell_data.get(KRAKEN_ORIGINAL_CELL_ID, []), dtype=int).reshape(-1)
        if existing.size == cell_count:
            return mesh
    except Exception:
        pass
    try:
        if "orig" in mesh.cell_data:
            original = np.asarray(mesh.cell_data["orig"], dtype=int).reshape(-1)
        elif "vtkOriginalCellIds" in mesh.cell_data:
            original = np.asarray(mesh.cell_data["vtkOriginalCellIds"], dtype=int).reshape(-1)
        else:
            original = np.arange(cell_count, dtype=int)
        if original.size != cell_count:
            original = np.arange(cell_count, dtype=int)
        mesh.cell_data[KRAKEN_ORIGINAL_CELL_ID] = original
    except Exception:
        pass
    return mesh


def raytrace_compatible_mesh(mesh, context="mesh"):
    """Return a PyVista mesh that supports ray_trace and cell normals.

    KrakenOS scene geometry can originate from native surfaces, UDA polygons,
    STL solids, or transformed/custom PyVista datasets. Some of those arrive as
    UnstructuredGrid objects, which are visible in the scene but do not expose
    the ray_trace method used by the non-sequential engine. This adapter makes
    the trace contract explicit at the shared geometry boundary.
    """
    if mesh is None:
        raise MeshRayTraceError(f"{context}: missing mesh; cannot trace intersections.")

    candidate = _ensure_original_cell_ids(mesh)
    converted = False
    if not hasattr(candidate, "ray_trace"):
        if hasattr(candidate, "extract_surface"):
            candidate = _extract_surface(candidate)
            converted = True
        else:
            raise MeshRayTraceError(
                f"{context}: {_mesh_type_name(mesh)} has no ray_trace or extract_surface method."
            )

    if converted:
        for method_name in ("triangulate", "clean"):
            method = getattr(candidate, method_name, None)
            if callable(method):
                try:
                    candidate = method()
                except Exception:
                    pass

    candidate = _ensure_original_cell_ids(candidate)
    if not hasattr(candidate, "ray_trace"):
        raise MeshRayTraceError(
            f"{context}: {_mesh_type_name(mesh)} could not be converted to ray-traceable PolyData."
        )

    return _with_cell_normals(candidate)


def trace_mesh_ray(mesh, start, stop, context="mesh"):
    tracer = raytrace_compatible_mesh(mesh, context=context)
    try:
        return tracer, tracer.ray_trace(start, stop)
    except Exception as exc:
        raise MeshRayTraceError(
            f"{context}: ray_trace failed on {_mesh_type_name(tracer)}: {exc}"
        ) from exc


def mesh_hit_cell_metadata(mesh, cell_id):
    try:
        index = int(cell_id)
    except Exception:
        index = -1
    metadata = {
        "cell_id": index,
        "original_cell_id": -1,
        "face_id": "",
    }
    if index < 0:
        return metadata
    try:
        original = np.asarray(mesh.cell_data.get(KRAKEN_ORIGINAL_CELL_ID, []), dtype=int).reshape(-1)
        if index < original.size:
            metadata["original_cell_id"] = int(original[index])
    except Exception:
        pass
    try:
        face_ids = np.asarray(mesh.cell_data.get(KRAKEN_FACE_ID, []), dtype=object).reshape(-1)
        if index < face_ids.size:
            metadata["face_id"] = str(face_ids[index] or "").strip()
    except Exception:
        pass
    return metadata
