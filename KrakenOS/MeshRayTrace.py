import numpy as np


KRAKEN_ORIGINAL_CELL_ID = "KrakenOriginalCellId"
KRAKEN_FACE_ID = "KrakenFaceId"
KRAKEN_FACE_MATCH_SCORE = "KrakenFaceMatchScore"


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


def _unit_vector(value, fallback=(0.0, 0.0, 1.0)):
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        vector = np.asarray(fallback, dtype=float)
    if vector.size < 3:
        vector = np.pad(vector, (0, 3 - vector.size), mode="constant")
    norm = float(np.linalg.norm(vector))
    if norm <= 1e-12 or not np.isfinite(norm):
        return np.asarray(fallback, dtype=float)
    return vector / norm


def _cell_centers(mesh):
    try:
        centers = np.asarray(mesh.cell_centers().points, dtype=float)
        if centers.ndim == 2 and centers.shape[1] >= 3:
            return centers[:, :3]
    except Exception:
        pass
    return np.empty((0, 3), dtype=float)


def assign_mesh_cell_face_ids(mesh, world_faces, context="mesh"):
    """Attach direct face ids to mesh cells by matching cells to face planes."""
    mesh = raytrace_compatible_mesh(mesh, context=context)
    try:
        cell_count = int(getattr(mesh, "n_cells", 0))
    except Exception:
        return mesh
    if cell_count <= 0:
        return mesh
    try:
        existing = np.asarray(mesh.cell_data.get(KRAKEN_FACE_ID, []), dtype=object).reshape(-1)
        if existing.size == cell_count and any(str(value or "").strip() for value in existing.tolist()):
            return mesh
    except Exception:
        pass

    faces = []
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        face_id = str(face.get("face_id", "") or "").strip()
        if not face_id:
            continue
        try:
            centroid = np.asarray(
                face.get("centroid_world", face.get("centroid", (0.0, 0.0, 0.0))),
                dtype=float,
            ).reshape(-1)[:3]
        except Exception:
            continue
        if centroid.size < 3 or not np.all(np.isfinite(centroid[:3])):
            continue
        normal = _unit_vector(face.get("normal_world", face.get("normal", (0.0, 0.0, 1.0))))
        faces.append((face_id, centroid[:3], normal))
    if not faces:
        return mesh

    centers = _cell_centers(mesh)
    try:
        normals = np.asarray(_with_cell_normals(mesh).cell_normals, dtype=float)
    except Exception:
        normals = np.empty((0, 3), dtype=float)
    if centers.shape[0] != cell_count or normals.shape[0] != cell_count:
        return mesh

    try:
        points = np.asarray(getattr(mesh, "points", ()), dtype=float)
        extents = np.ptp(points[:, :3], axis=0) if points.ndim == 2 and points.shape[0] else np.zeros(3)
    except Exception:
        extents = np.zeros(3)
    max_extent = max(float(np.max(extents)), 1.0)
    plane_tolerance = max(max_extent * 2.0e-3, 0.08)
    normal_tolerance = 0.985

    face_ids = np.full(cell_count, "", dtype=object)
    match_scores = np.full(cell_count, np.inf, dtype=float)
    for cell_index in range(cell_count):
        center = centers[cell_index]
        cell_normal = _unit_vector(normals[cell_index])
        best_face = ""
        best_score = float("inf")
        for face_id, centroid, normal in faces:
            normal_alignment = abs(float(np.dot(cell_normal, normal)))
            if normal_alignment < normal_tolerance:
                continue
            plane_distance = abs(float(np.dot(center - centroid, normal)))
            if plane_distance > plane_tolerance:
                continue
            score = (plane_distance / max(plane_tolerance, 1e-12)) + (1.0 - normal_alignment)
            if score < best_score:
                best_face = face_id
                best_score = score
        if best_face:
            face_ids[cell_index] = best_face
            match_scores[cell_index] = best_score

    try:
        mesh.cell_data[KRAKEN_FACE_ID] = face_ids
        mesh.cell_data[KRAKEN_FACE_MATCH_SCORE] = match_scores
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
