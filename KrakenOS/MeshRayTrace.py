import time

import numpy as np


KRAKEN_ORIGINAL_CELL_ID = "KrakenOriginalCellId"
KRAKEN_CELL_NORMALS = "KrakenCellNormals"
KRAKEN_FACE_ID = "KrakenFaceId"
KRAKEN_FACE_MATCH_SCORE = "KrakenFaceMatchScore"
KRAKEN_FACE_MATCH_METHOD = "KrakenFaceMatchMethod"
KRAKEN_FACE_MATCH_WARNING = "KrakenFaceMatchWarning"
PLANE_INFERENCE_FACE_WARNING = (
    "Optical solid face inferred from face plane; exact triangle membership is unavailable."
)
MISSING_FACE_ID_WARNING = "Optical solid mesh hit has no matched face id."
MISSING_FACE_METHOD_WARNING = "Optical solid mesh hit has no face-match provenance."


class MeshRayTraceError(RuntimeError):
    """Raised when a scene mesh cannot satisfy KrakenOS ray-intersection needs."""


_MESH_TRACE_STATS = {"active": False}
_RAYTRACE_COMPATIBLE_MESH_IDS = set()


def reset_mesh_trace_stats(*, active=True):
    """Start or stop lightweight mesh ray-trace counters for one trace window."""
    _MESH_TRACE_STATS.clear()
    _MESH_TRACE_STATS.update(
        {
            "active": bool(active),
            "call_count": 0,
            "total_ms": 0.0,
            "hit_count": 0,
            "error_count": 0,
            "contexts": {},
        }
    )


def mesh_trace_stats_snapshot(*, reset=False, top_n=12):
    """Return a JSON-safe summary of the active mesh ray-trace counters."""
    contexts = _MESH_TRACE_STATS.get("contexts", {}) if isinstance(_MESH_TRACE_STATS, dict) else {}
    top_contexts = []
    if isinstance(contexts, dict):
        rows = sorted(
            contexts.items(),
            key=lambda item: float(item[1].get("total_ms", 0.0)) if isinstance(item[1], dict) else 0.0,
            reverse=True,
        )
        for context, data in rows[: max(0, int(top_n))]:
            if not isinstance(data, dict):
                continue
            top_contexts.append(
                {
                    "context": str(context),
                    "call_count": int(data.get("call_count", 0) or 0),
                    "total_ms": round(float(data.get("total_ms", 0.0) or 0.0), 3),
                    "hit_count": int(data.get("hit_count", 0) or 0),
                    "error_count": int(data.get("error_count", 0) or 0),
                    "max_cells": int(data.get("max_cells", 0) or 0),
                }
            )
    summary = {
        "mesh_ray_call_count": int(_MESH_TRACE_STATS.get("call_count", 0) or 0),
        "mesh_ray_total_ms": round(float(_MESH_TRACE_STATS.get("total_ms", 0.0) or 0.0), 3),
        "mesh_ray_hit_count": int(_MESH_TRACE_STATS.get("hit_count", 0) or 0),
        "mesh_ray_error_count": int(_MESH_TRACE_STATS.get("error_count", 0) or 0),
        "mesh_ray_contexts": top_contexts,
    }
    if reset:
        reset_mesh_trace_stats(active=False)
    return summary


def _record_mesh_trace_stat(context, duration_ms, hit_count=0, cell_count=0, error=False):
    if not bool(_MESH_TRACE_STATS.get("active", False)):
        return
    context_key = str(context or "mesh")
    try:
        duration = float(duration_ms)
    except Exception:
        duration = 0.0
    try:
        hits = int(hit_count)
    except Exception:
        hits = 0
    try:
        cells = int(cell_count)
    except Exception:
        cells = 0
    _MESH_TRACE_STATS["call_count"] = int(_MESH_TRACE_STATS.get("call_count", 0) or 0) + 1
    _MESH_TRACE_STATS["total_ms"] = float(_MESH_TRACE_STATS.get("total_ms", 0.0) or 0.0) + duration
    _MESH_TRACE_STATS["hit_count"] = int(_MESH_TRACE_STATS.get("hit_count", 0) or 0) + max(hits, 0)
    if error:
        _MESH_TRACE_STATS["error_count"] = int(_MESH_TRACE_STATS.get("error_count", 0) or 0) + 1
    contexts = _MESH_TRACE_STATS.setdefault("contexts", {})
    row = contexts.setdefault(
        context_key,
        {
            "call_count": 0,
            "total_ms": 0.0,
            "hit_count": 0,
            "error_count": 0,
            "max_cells": 0,
        },
    )
    row["call_count"] = int(row.get("call_count", 0) or 0) + 1
    row["total_ms"] = float(row.get("total_ms", 0.0) or 0.0) + duration
    row["hit_count"] = int(row.get("hit_count", 0) or 0) + max(hits, 0)
    row["max_cells"] = max(int(row.get("max_cells", 0) or 0), max(cells, 0))
    if error:
        row["error_count"] = int(row.get("error_count", 0) or 0) + 1


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


def mesh_cell_normals(mesh):
    """Cell normals as an ``(n_cells, 3)`` array, computed once and cached on the
    mesh's ``cell_data``.

    PyVista's ``mesh.cell_normals`` property re-runs the full ``compute_normals``
    VTK pipeline on EVERY access. During a non-sequential trace the per-hit normal
    lookup (``InterNormalCalc.__InterNormalSolidObject``) reads it once per
    ray-solid intersection -- hundreds of times for a fine STL solid -- so the
    recompute dominates the trace (~70% of wall on a 49 k-cell cube, measured).
    The mesh geometry is static during a trace, and a resized / re-promoted solid
    is a NEW object, so caching the array in ``cell_data`` (lives and dies with the
    mesh) is safe and makes repeat access O(1). The values are bit-identical to the
    property, so the trace result is unchanged.
    """
    n_cells = 0
    try:
        n_cells = int(getattr(mesh, "n_cells", 0))
    except Exception:
        n_cells = 0
    try:
        cached = mesh.cell_data.get(KRAKEN_CELL_NORMALS)
        if cached is not None:
            arr = np.asarray(cached, dtype=float)
            if arr.ndim == 2 and arr.shape == (n_cells, 3):
                return arr
    except Exception:
        pass
    arr = np.asarray(mesh.cell_normals, dtype=float)
    try:
        if arr.ndim == 2 and arr.shape[0] == n_cells:
            mesh.cell_data[KRAKEN_CELL_NORMALS] = arr
    except Exception:
        pass
    return arr


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


def _face_triangle_indices(face):
    if not isinstance(face, dict):
        return []
    raw = face.get("triangle_indices", face.get("cell_indices", []))
    if raw is None:
        return []
    try:
        if isinstance(raw, np.ndarray):
            raw_values = raw.reshape(-1).tolist()
        elif isinstance(raw, (list, tuple, set)):
            raw_values = list(raw)
        else:
            raw_values = [raw]
    except Exception:
        return []
    output = []
    seen = set()
    for value in raw_values:
        try:
            index = int(value)
        except Exception:
            continue
        if index < 0 or index in seen:
            continue
        seen.add(index)
        output.append(index)
    return output


def _exact_face_id_by_original_cell(world_faces):
    face_by_original_cell = {}
    conflicts = set()
    for face in list(world_faces or []):
        if not isinstance(face, dict):
            continue
        face_id = str(face.get("face_id", "") or "").strip()
        if not face_id:
            continue
        for original_cell_id in _face_triangle_indices(face):
            previous = face_by_original_cell.get(original_cell_id)
            if previous is not None and previous != face_id:
                conflicts.add(original_cell_id)
                continue
            face_by_original_cell[original_cell_id] = face_id
    for original_cell_id in conflicts:
        face_by_original_cell.pop(original_cell_id, None)
    return face_by_original_cell, conflicts


def assign_mesh_cell_face_ids(mesh, world_faces, context="mesh"):
    """Attach direct face ids to mesh cells from face membership, then face planes."""
    mesh = raytrace_compatible_mesh(mesh, context=context)
    try:
        cell_count = int(getattr(mesh, "n_cells", 0))
    except Exception:
        return mesh
    if cell_count <= 0:
        return mesh

    face_ids = np.full(cell_count, "", dtype=object)
    match_scores = np.full(cell_count, np.inf, dtype=float)
    match_methods = np.full(cell_count, "", dtype=object)
    match_warnings = np.full(cell_count, "", dtype=object)
    face_by_original_cell, _conflicts = _exact_face_id_by_original_cell(world_faces)
    if face_by_original_cell:
        try:
            original_cell_ids = np.asarray(mesh.cell_data.get(KRAKEN_ORIGINAL_CELL_ID, []), dtype=int).reshape(-1)
        except Exception:
            original_cell_ids = np.asarray([], dtype=int)
        if original_cell_ids.size == cell_count:
            for cell_index, original_cell_id in enumerate(original_cell_ids.tolist()):
                face_id = face_by_original_cell.get(int(original_cell_id), "")
                if face_id:
                    face_ids[cell_index] = face_id
                    match_scores[cell_index] = 0.0
                    match_methods[cell_index] = "triangle_membership"
            if all(str(value or "").strip() for value in face_ids.tolist()):
                try:
                    mesh.cell_data[KRAKEN_FACE_ID] = face_ids
                    mesh.cell_data[KRAKEN_FACE_MATCH_SCORE] = match_scores
                    mesh.cell_data[KRAKEN_FACE_MATCH_METHOD] = match_methods
                    mesh.cell_data[KRAKEN_FACE_MATCH_WARNING] = match_warnings
                except Exception:
                    pass
                return mesh

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
        if any(str(value or "").strip() for value in face_ids.tolist()):
            try:
                mesh.cell_data[KRAKEN_FACE_ID] = face_ids
                mesh.cell_data[KRAKEN_FACE_MATCH_SCORE] = match_scores
                mesh.cell_data[KRAKEN_FACE_MATCH_METHOD] = match_methods
                mesh.cell_data[KRAKEN_FACE_MATCH_WARNING] = match_warnings
            except Exception:
                pass
        return mesh

    centers = _cell_centers(mesh)
    try:
        normals = np.asarray(_with_cell_normals(mesh).cell_normals, dtype=float)
    except Exception:
        normals = np.empty((0, 3), dtype=float)
    if centers.shape[0] != cell_count or normals.shape[0] != cell_count:
        if any(str(value or "").strip() for value in face_ids.tolist()):
            try:
                mesh.cell_data[KRAKEN_FACE_ID] = face_ids
                mesh.cell_data[KRAKEN_FACE_MATCH_SCORE] = match_scores
                mesh.cell_data[KRAKEN_FACE_MATCH_METHOD] = match_methods
                mesh.cell_data[KRAKEN_FACE_MATCH_WARNING] = match_warnings
            except Exception:
                pass
        return mesh

    try:
        points = np.asarray(getattr(mesh, "points", ()), dtype=float)
        extents = np.ptp(points[:, :3], axis=0) if points.ndim == 2 and points.shape[0] else np.zeros(3)
    except Exception:
        extents = np.zeros(3)
    max_extent = max(float(np.max(extents)), 1.0)
    plane_tolerance = max(max_extent * 2.0e-3, 0.08)
    normal_tolerance = 0.985

    for cell_index in range(cell_count):
        if str(face_ids[cell_index] or "").strip():
            continue
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
            match_methods[cell_index] = "plane_inference"
            match_warnings[cell_index] = PLANE_INFERENCE_FACE_WARNING

    try:
        mesh.cell_data[KRAKEN_FACE_ID] = face_ids
        mesh.cell_data[KRAKEN_FACE_MATCH_SCORE] = match_scores
        mesh.cell_data[KRAKEN_FACE_MATCH_METHOD] = match_methods
        mesh.cell_data[KRAKEN_FACE_MATCH_WARNING] = match_warnings
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

    try:
        if id(mesh) in _RAYTRACE_COMPATIBLE_MESH_IDS and hasattr(mesh, "ray_trace"):
            return mesh
    except Exception:
        pass

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

    candidate = _with_cell_normals(candidate)
    try:
        _RAYTRACE_COMPATIBLE_MESH_IDS.add(id(candidate))
    except Exception:
        pass
    return candidate


def trace_mesh_ray(mesh, start, stop, context="mesh"):
    stats_active = bool(_MESH_TRACE_STATS.get("active", False))
    started = time.perf_counter() if stats_active else 0.0
    tracer = raytrace_compatible_mesh(mesh, context=context)
    try:
        result = tracer.ray_trace(start, stop)
        if stats_active:
            try:
                hit_count = len(result[1])
            except Exception:
                hit_count = 0
            _record_mesh_trace_stat(
                context,
                (time.perf_counter() - started) * 1000.0,
                hit_count=hit_count,
                cell_count=getattr(tracer, "n_cells", 0),
            )
        return tracer, result
    except Exception as exc:
        if stats_active:
            _record_mesh_trace_stat(
                context,
                (time.perf_counter() - started) * 1000.0,
                hit_count=0,
                cell_count=getattr(tracer, "n_cells", 0),
                error=True,
            )
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
        "face_match_method": "",
        "face_match_score": None,
        "face_match_warning": "",
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
    try:
        methods = np.asarray(mesh.cell_data.get(KRAKEN_FACE_MATCH_METHOD, []), dtype=object).reshape(-1)
        if index < methods.size:
            metadata["face_match_method"] = str(methods[index] or "").strip()
    except Exception:
        pass
    try:
        scores = np.asarray(mesh.cell_data.get(KRAKEN_FACE_MATCH_SCORE, []), dtype=float).reshape(-1)
        if index < scores.size and np.isfinite(float(scores[index])):
            metadata["face_match_score"] = float(scores[index])
    except Exception:
        pass
    try:
        warnings = np.asarray(mesh.cell_data.get(KRAKEN_FACE_MATCH_WARNING, []), dtype=object).reshape(-1)
        if index < warnings.size:
            metadata["face_match_warning"] = str(warnings[index] or "").strip()
    except Exception:
        pass
    if not metadata["face_match_warning"]:
        if metadata["face_match_method"] == "plane_inference":
            metadata["face_match_warning"] = PLANE_INFERENCE_FACE_WARNING
        elif metadata["cell_id"] >= 0 and metadata["face_id"] and not metadata["face_match_method"]:
            metadata["face_match_warning"] = MISSING_FACE_METHOD_WARNING
        elif metadata["cell_id"] >= 0 and not metadata["face_id"]:
            metadata["face_match_warning"] = MISSING_FACE_ID_WARNING
    return metadata
