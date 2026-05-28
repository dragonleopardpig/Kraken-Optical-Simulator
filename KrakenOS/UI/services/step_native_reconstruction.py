"""Rebuild supported STEP optical faces as KrakenOS-native surface rows.

This is the Tier 3 bridge between CAD topology and optical prescriptions.  It
uses the OpenCascade B-Rep face records from :mod:`step_analytic_geometry`,
groups split vendor faces into optical surfaces, keeps one representative
cemented interface from duplicated multi-solid faces, and emits ordinary
``SurfaceRow`` records plus diagnostics.

The module is intentionally conservative.  It does not invent glass materials
from geometry, and it reports fit residuals for any spline-to-asphere
reconstruction instead of silently treating a poor fit as exact physics.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from KrakenOS.UI.surface_table_model import SurfaceRow, clone_surface_rows
from KrakenOS.UI.services.step_analytic_geometry import (
    StepAnalyticDocument,
    StepAnalyticFace,
    load_step_analytic_document,
)


STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR = "StepNativeReconstruction"
DEFAULT_ASPHERE_TERMS = 8


@dataclass(frozen=True)
class StepNativeDiagnostic:
    severity: str
    code: str
    message: str
    face_ids: tuple[str, ...] = ()

    def as_record(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "face_ids": list(self.face_ids),
        }


@dataclass(frozen=True)
class StepNativeSurfaceFit:
    surface_id: str
    face_ids: tuple[str, ...]
    source_surface_types: tuple[str, ...]
    native_kind: str
    vertex_z_mm: float
    diameter_mm: float
    rc_mm: float
    conic_k: float
    aspher_data: tuple[float, ...]
    rms_error_mm: float
    max_error_mm: float
    sample_count: int
    supported: bool
    notes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, object]:
        return {
            "surface_id": self.surface_id,
            "face_ids": list(self.face_ids),
            "source_surface_types": list(self.source_surface_types),
            "native_kind": self.native_kind,
            "vertex_z_mm": float(self.vertex_z_mm),
            "diameter_mm": float(self.diameter_mm),
            "rc_mm": float(self.rc_mm),
            "conic_k": float(self.conic_k),
            "aspher_data": list(self.aspher_data),
            "rms_error_mm": float(self.rms_error_mm),
            "max_error_mm": float(self.max_error_mm),
            "sample_count": int(self.sample_count),
            "supported": bool(self.supported),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class StepNativeReconstruction:
    source_path: Path
    axis_direction: tuple[float, float, float]
    axis_origin: tuple[float, float, float]
    basis_x: tuple[float, float, float]
    basis_y: tuple[float, float, float]
    aperture_diameter_mm: float
    rows: tuple[SurfaceRow, ...]
    surface_fits: tuple[StepNativeSurfaceFit, ...]
    diagnostics: tuple[StepNativeDiagnostic, ...]
    trace_ready: bool

    def as_record(self) -> dict[str, object]:
        return {
            "source_step_path": str(self.source_path),
            "axis_direction": list(self.axis_direction),
            "axis_origin": list(self.axis_origin),
            "basis_x": list(self.basis_x),
            "basis_y": list(self.basis_y),
            "aperture_diameter_mm": float(self.aperture_diameter_mm),
            "trace_ready": bool(self.trace_ready),
            "surface_count": int(len(self.surface_fits)),
            "rows": [asdict(row) for row in self.rows],
            "surface_fits": [fit.as_record() for fit in self.surface_fits],
            "diagnostics": [diagnostic.as_record() for diagnostic in self.diagnostics],
        }

    def component_rows(self) -> list[SurfaceRow]:
        return clone_surface_rows(list(self.rows))

    def layout_rows(
        self,
        *,
        object_distance_mm: float = 100.0,
        image_distance_mm: float = 100.0,
    ) -> list[SurfaceRow]:
        rows = self.component_rows()
        aperture = max(float(self.aperture_diameter_mm), 1.0)
        if rows:
            rows[-1].thickness = max(float(image_distance_mm), 0.0)
        return [
            SurfaceRow(surface="Object", name="Object", thickness=max(float(object_distance_mm), 0.0), diameter=aperture, glass="AIR"),
            *rows,
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=aperture, glass="AIR"),
        ]


@dataclass
class _CandidateFace:
    face: StepAnalyticFace
    points: np.ndarray
    local_points: np.ndarray
    z_min: float
    z_max: float
    z_median: float


@dataclass
class _FaceGroup:
    key: tuple[object, ...]
    faces: list[StepAnalyticFace]
    points: list[np.ndarray]
    local_points: list[np.ndarray]


def _unit(values: object, fallback: tuple[float, float, float] = (0.0, 0.0, 1.0)) -> np.ndarray:
    array = np.asarray(values, dtype=float).reshape(-1)[:3]
    if array.size < 3:
        array = np.pad(array, (0, 3 - array.size), mode="constant")
    norm = float(np.linalg.norm(array))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        array = np.asarray(fallback, dtype=float)
        norm = float(np.linalg.norm(array))
    return np.asarray(array / max(norm, 1.0e-12), dtype=float)


def _basis_from_axis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    reference = np.asarray((1.0, 0.0, 0.0), dtype=float)
    if abs(float(np.dot(reference, axis))) > 0.85:
        reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
    basis_x = _unit(np.cross(reference, axis), fallback=(0.0, 1.0, 0.0))
    basis_y = _unit(np.cross(axis, basis_x), fallback=(1.0, 0.0, 0.0))
    return basis_x, basis_y


def _document_axis(document: StepAnalyticDocument) -> tuple[np.ndarray, np.ndarray, float, list[StepNativeDiagnostic]]:
    axis_vectors: list[np.ndarray] = []
    axis_points: list[np.ndarray] = []
    radii: list[float] = []
    weights: list[float] = []
    diagnostics: list[StepNativeDiagnostic] = []
    for face in document.faces:
        if face.surface_type != "cylinder":
            continue
        params = dict(face.parameters or {})
        direction = params.get("axis_direction")
        origin = params.get("axis_origin")
        radius = params.get("radius_mm")
        if direction is None or origin is None or radius is None:
            continue
        vector = _unit(direction)
        if axis_vectors and float(np.dot(vector, axis_vectors[0])) < 0.0:
            vector = -vector
        axis_vectors.append(vector)
        axis_points.append(np.asarray(origin, dtype=float).reshape(-1)[:3])
        radii.append(abs(float(radius)))
        weights.append(max(float(face.area_mm2), 1.0))
    if axis_vectors:
        weight_array = np.asarray(weights, dtype=float)
        axis = _unit(np.average(np.vstack(axis_vectors), axis=0, weights=weight_array))
        axis_origin = np.average(np.vstack(axis_points), axis=0, weights=weight_array)
        aperture_diameter = 2.0 * max(radii)
        return axis, axis_origin, float(aperture_diameter), diagnostics

    all_points = np.asarray(document.triangles, dtype=float).reshape((-1, 3)) if document.triangles.size else np.empty((0, 3))
    if all_points.size:
        mins = np.min(all_points, axis=0)
        maxs = np.max(all_points, axis=0)
        extents = maxs - mins
        axis_index = int(np.argmax(extents))
        axis = np.eye(3)[axis_index]
        axis_origin = 0.5 * (mins + maxs)
        transverse = [index for index in range(3) if index != axis_index]
        aperture_diameter = float(max(extents[transverse]))
    else:
        axis = np.asarray((0.0, 0.0, 1.0), dtype=float)
        axis_origin = np.asarray((0.0, 0.0, 0.0), dtype=float)
        aperture_diameter = 1.0
    diagnostics.append(
        StepNativeDiagnostic(
            "warning",
            "axis_inferred_from_bbox",
            "No cylindrical barrel axis was available; native reconstruction inferred the optical axis from the STEP bounding box.",
        )
    )
    return axis, axis_origin, max(float(aperture_diameter), 1.0), diagnostics


def _localize(points: np.ndarray, origin: np.ndarray, basis_x: np.ndarray, basis_y: np.ndarray, axis: np.ndarray) -> np.ndarray:
    shifted = np.asarray(points, dtype=float).reshape((-1, 3)) - origin.reshape(1, 3)
    return np.column_stack((shifted @ basis_x, shifted @ basis_y, shifted @ axis))


def _triangles_for_face(document: StepAnalyticDocument, face: StepAnalyticFace) -> np.ndarray:
    indices = [int(value) for value in getattr(face, "triangle_indices", ()) if 0 <= int(value) < int(document.triangles.shape[0])]
    if not indices:
        return np.empty((0, 3, 3), dtype=float)
    return np.asarray(document.triangles[indices], dtype=float).reshape((-1, 3, 3))


def _unique_points(triangles: np.ndarray) -> np.ndarray:
    if triangles.size == 0:
        return np.empty((0, 3), dtype=float)
    points = np.asarray(triangles, dtype=float).reshape((-1, 3))
    points = points[np.all(np.isfinite(points), axis=1)]
    if points.size == 0:
        return np.empty((0, 3), dtype=float)
    return np.unique(np.round(points, decimals=9), axis=0)


def _is_side_wall(face: StepAnalyticFace, axis: np.ndarray) -> bool:
    if face.surface_type != "cylinder":
        return False
    direction = dict(face.parameters or {}).get("axis_direction")
    if direction is None:
        return False
    return abs(float(np.dot(_unit(direction), axis))) > 0.90


def _candidate_faces(
    document: StepAnalyticDocument,
    axis: np.ndarray,
    axis_origin: np.ndarray,
    basis_x: np.ndarray,
    basis_y: np.ndarray,
) -> tuple[list[_CandidateFace], list[StepNativeDiagnostic]]:
    candidates: list[_CandidateFace] = []
    diagnostics: list[StepNativeDiagnostic] = []
    for face in document.faces:
        if _is_side_wall(face, axis):
            continue
        triangles = _triangles_for_face(document, face)
        points = _unique_points(triangles)
        if points.shape[0] < 3:
            if face.interior_duplicate:
                continue
            diagnostics.append(
                StepNativeDiagnostic(
                    "warning",
                    "face_without_samples",
                    f"STEP face {face.face_id} had too few tessellation points for native reconstruction.",
                    (face.face_id,),
                )
            )
            continue
        local_points = _localize(points, axis_origin, basis_x, basis_y, axis)
        z_values = local_points[:, 2]
        candidates.append(
            _CandidateFace(
                face=face,
                points=points,
                local_points=local_points,
                z_min=float(np.min(z_values)),
                z_max=float(np.max(z_values)),
                z_median=float(np.median(z_values)),
            )
        )
    if not candidates:
        diagnostics.append(
            StepNativeDiagnostic(
                "error",
                "no_optical_faces",
                "No non-barrel STEP faces were available for native optical reconstruction.",
            )
        )
    return candidates, diagnostics


def _sphere_group_key(face: StepAnalyticFace) -> tuple[object, ...]:
    params = dict(face.parameters or {})
    center = tuple(float(np.round(value, 4)) for value in list(params.get("center", (0.0, 0.0, 0.0)))[:3])
    radius = float(np.round(float(params.get("radius_mm", 0.0) or 0.0), 4))
    return ("sphere", radius, center)


def _plane_group_key(face: StepAnalyticFace) -> tuple[object, ...]:
    return ("plane", float(np.round(face.plane_offset_mm, 4)))


def _candidate_group_key(candidate: _CandidateFace, aperture_diameter_mm: float) -> tuple[object, ...]:
    face = candidate.face
    if face.interior_duplicate and face.duplicate_group:
        return ("duplicate-interface", face.duplicate_group)
    if face.surface_type == "sphere":
        return _sphere_group_key(face)
    if face.surface_type == "plane":
        return _plane_group_key(face)
    bin_size = max(0.05, min(0.25, float(aperture_diameter_mm) / 200.0))
    return (
        face.surface_type,
        int(round(candidate.z_median / bin_size)),
        int(round((candidate.z_max - candidate.z_min) / bin_size)),
    )


def _group_candidates(candidates: Sequence[_CandidateFace], aperture_diameter_mm: float) -> list[_FaceGroup]:
    groups_by_key: dict[tuple[object, ...], _FaceGroup] = {}
    for candidate in candidates:
        key = _candidate_group_key(candidate, aperture_diameter_mm)
        group = groups_by_key.get(key)
        if group is None:
            group = _FaceGroup(key=key, faces=[], points=[], local_points=[])
            groups_by_key[key] = group
        group.faces.append(candidate.face)
        group.points.append(candidate.points)
        group.local_points.append(candidate.local_points)
    return list(groups_by_key.values())


def _conic_sag(r_values: np.ndarray, rc_mm: float, k: float = 0.0) -> np.ndarray:
    r = np.asarray(r_values, dtype=float)
    if abs(float(rc_mm)) <= 1.0e-12:
        return np.zeros_like(r)
    curvature = 1.0 / float(rc_mm)
    in_root = 1.0 - (1.0 + float(k)) * curvature * curvature * r * r
    in_root = np.maximum(in_root, 0.0)
    return (curvature * r * r) / (1.0 + np.sqrt(in_root))


def _asphere_coefficients_from_fit(coefficients: np.ndarray, radius_scale: float, term_count: int) -> tuple[float, ...]:
    values = [0.0] * max(int(term_count), DEFAULT_ASPHERE_TERMS)
    for index in range(1, min(int(term_count), int(coefficients.size - 1)) + 1):
        values[index - 1] = float(coefficients[index]) / (float(radius_scale) ** (2 * index))
    return tuple(float(value) for value in values[:DEFAULT_ASPHERE_TERMS])


def _fit_polynomial_asphere(
    group: _FaceGroup,
    *,
    aperture_diameter_mm: float,
    term_count: int,
) -> StepNativeSurfaceFit:
    local_points = np.vstack(group.local_points)
    radii = np.sqrt(local_points[:, 0] * local_points[:, 0] + local_points[:, 1] * local_points[:, 1])
    z_values = local_points[:, 2]
    valid = np.isfinite(radii) & np.isfinite(z_values)
    radii = radii[valid]
    z_values = z_values[valid]
    if radii.size < max(6, int(term_count) + 1):
        return _unsupported_group_fit(group, "insufficient_samples", "Not enough finite points to fit a native asphere.")
    radius_scale = max(float(np.max(radii)), float(aperture_diameter_mm) * 0.5, 1.0e-6)
    rho2 = (radii / radius_scale) ** 2
    columns = [np.ones_like(rho2)]
    for power in range(1, int(term_count) + 1):
        columns.append(rho2**power)
    design = np.column_stack(columns)
    try:
        coefficients, _residuals, rank, _singular = np.linalg.lstsq(design, z_values, rcond=None)
    except Exception as exc:
        return _unsupported_group_fit(group, "asphere_fit_failed", f"Asphere least-squares fit failed: {exc}")
    predicted = design @ coefficients
    residual = predicted - z_values
    rms = float(np.sqrt(np.mean(residual * residual)))
    max_error = float(np.max(np.abs(residual)))
    tolerance = max(0.005, float(aperture_diameter_mm) * 2.0e-4)
    supported = bool(rank >= min(design.shape) - 1 and rms <= tolerance and max_error <= tolerance * 5.0)
    notes: list[str] = []
    if not supported:
        notes.append(f"fit_tolerance_mm={tolerance:.6g}")
    surface_types = tuple(sorted({str(face.surface_type) for face in group.faces}))
    return StepNativeSurfaceFit(
        surface_id=_surface_id_for_group(group),
        face_ids=tuple(face.face_id for face in group.faces),
        source_surface_types=surface_types,
        native_kind="asphere_polynomial_fit",
        vertex_z_mm=float(coefficients[0]),
        diameter_mm=max(float(np.max(radii) * 2.0), 1.0),
        rc_mm=0.0,
        conic_k=0.0,
        aspher_data=_asphere_coefficients_from_fit(coefficients, radius_scale, int(term_count)),
        rms_error_mm=rms,
        max_error_mm=max_error,
        sample_count=int(radii.size),
        supported=supported,
        notes=tuple(notes),
    )


def _surface_id_for_group(group: _FaceGroup) -> str:
    if group.faces and group.faces[0].interior_duplicate and group.faces[0].duplicate_group:
        return str(group.faces[0].duplicate_group)
    first = group.faces[0].face_id if group.faces else "F000"
    if len(group.faces) == 1:
        return first
    return "+".join(face.face_id for face in group.faces)


def _unsupported_group_fit(group: _FaceGroup, code: str, note: str) -> StepNativeSurfaceFit:
    local_points = np.vstack(group.local_points) if group.local_points else np.empty((0, 3), dtype=float)
    vertex_z = float(np.median(local_points[:, 2])) if local_points.size else 0.0
    radii = np.sqrt(local_points[:, 0] * local_points[:, 0] + local_points[:, 1] * local_points[:, 1]) if local_points.size else np.asarray([0.5])
    return StepNativeSurfaceFit(
        surface_id=_surface_id_for_group(group),
        face_ids=tuple(face.face_id for face in group.faces),
        source_surface_types=tuple(sorted({str(face.surface_type) for face in group.faces})),
        native_kind=code,
        vertex_z_mm=vertex_z,
        diameter_mm=max(float(np.max(radii) * 2.0), 1.0),
        rc_mm=0.0,
        conic_k=0.0,
        aspher_data=(0.0,) * DEFAULT_ASPHERE_TERMS,
        rms_error_mm=float("inf"),
        max_error_mm=float("inf"),
        sample_count=int(local_points.shape[0]) if local_points.ndim == 2 else 0,
        supported=False,
        notes=(note,),
    )


def _fit_sphere_group(
    group: _FaceGroup,
    axis_origin: np.ndarray,
    axis: np.ndarray,
) -> StepNativeSurfaceFit:
    face = group.faces[0]
    params = dict(face.parameters or {})
    radius = abs(float(params.get("radius_mm", 0.0) or 0.0))
    center = np.asarray(params.get("center", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)[:3]
    if center.size < 3 or radius <= 1.0e-9:
        return _unsupported_group_fit(group, "sphere_parameters_missing", "Sphere face did not expose a finite center and radius.")
    center_z = float(np.dot(center - axis_origin, axis))
    local_points = np.vstack(group.local_points)
    z_values = local_points[:, 2]
    median_z = float(np.median(z_values))
    vertices = (center_z - radius, center_z + radius)
    vertex_z = min(vertices, key=lambda value: abs(float(value) - median_z))
    rc = center_z - float(vertex_z)
    radii = np.sqrt(local_points[:, 0] * local_points[:, 0] + local_points[:, 1] * local_points[:, 1])
    predicted = float(vertex_z) + _conic_sag(radii, rc, 0.0)
    residual = predicted - z_values
    return StepNativeSurfaceFit(
        surface_id=_surface_id_for_group(group),
        face_ids=tuple(face.face_id for face in group.faces),
        source_surface_types=tuple(sorted({str(item.surface_type) for item in group.faces})),
        native_kind="sphere_exact",
        vertex_z_mm=float(vertex_z),
        diameter_mm=max(float(np.max(radii) * 2.0), 1.0),
        rc_mm=float(rc),
        conic_k=0.0,
        aspher_data=(0.0,) * DEFAULT_ASPHERE_TERMS,
        rms_error_mm=float(np.sqrt(np.mean(residual * residual))) if residual.size else 0.0,
        max_error_mm=float(np.max(np.abs(residual))) if residual.size else 0.0,
        sample_count=int(local_points.shape[0]),
        supported=True,
    )


def _fit_plane_group(group: _FaceGroup, axis: np.ndarray) -> StepNativeSurfaceFit:
    local_points = np.vstack(group.local_points)
    z_values = local_points[:, 2]
    radii = np.sqrt(local_points[:, 0] * local_points[:, 0] + local_points[:, 1] * local_points[:, 1])
    vertex_z = float(np.median(z_values))
    residual = z_values - vertex_z
    normals = [_unit(face.normal) for face in group.faces]
    axis_alignment = max(abs(float(np.dot(normal, axis))) for normal in normals) if normals else 0.0
    max_error = float(np.max(np.abs(residual))) if residual.size else 0.0
    supported = axis_alignment > 0.95 and max_error <= max(0.002, float(np.max(radii)) * 1.0e-4)
    notes = () if supported else (f"axis_alignment={axis_alignment:.6g}",)
    return StepNativeSurfaceFit(
        surface_id=_surface_id_for_group(group),
        face_ids=tuple(face.face_id for face in group.faces),
        source_surface_types=tuple(sorted({str(item.surface_type) for item in group.faces})),
        native_kind="plane_exact",
        vertex_z_mm=vertex_z,
        diameter_mm=max(float(np.max(radii) * 2.0), 1.0),
        rc_mm=0.0,
        conic_k=0.0,
        aspher_data=(0.0,) * DEFAULT_ASPHERE_TERMS,
        rms_error_mm=float(np.sqrt(np.mean(residual * residual))) if residual.size else 0.0,
        max_error_mm=max_error,
        sample_count=int(local_points.shape[0]),
        supported=supported,
        notes=notes,
    )


def _fit_group(
    group: _FaceGroup,
    *,
    axis_origin: np.ndarray,
    axis: np.ndarray,
    aperture_diameter_mm: float,
    term_count: int,
) -> StepNativeSurfaceFit:
    surface_types = {face.surface_type for face in group.faces}
    if surface_types == {"sphere"}:
        return _fit_sphere_group(group, axis_origin, axis)
    if surface_types == {"plane"}:
        return _fit_plane_group(group, axis)
    if surface_types.issubset({"bspline", "bezier", "surface_of_revolution", "offset", "other"}):
        return _fit_polynomial_asphere(group, aperture_diameter_mm=aperture_diameter_mm, term_count=term_count)
    return _unsupported_group_fit(
        group,
        "unsupported_surface_type",
        f"Unsupported STEP surface types for native reconstruction: {sorted(surface_types)}.",
    )


def _aspher_data_200(values: Iterable[float]) -> list[float]:
    data = [0.0] * 200
    for index, value in enumerate(list(values)[: min(DEFAULT_ASPHERE_TERMS, 200)]):
        data[index] = float(value)
    return data


def _rows_from_fits(
    fits: Sequence[StepNativeSurfaceFit],
    *,
    source_path: Path,
    aperture_diameter_mm: float,
    glass_sequence: Sequence[str] | None,
) -> tuple[SurfaceRow, ...]:
    rows: list[SurfaceRow] = []
    sorted_fits = sorted(fits, key=lambda fit: float(fit.vertex_z_mm))
    element_name = f"Native STEP {source_path.stem}"
    for index, fit in enumerate(sorted_fits):
        next_vertex = float(sorted_fits[index + 1].vertex_z_mm) if index + 1 < len(sorted_fits) else float(fit.vertex_z_mm)
        thickness = max(next_vertex - float(fit.vertex_z_mm), 0.0)
        glass = str(glass_sequence[index]).strip() if glass_sequence is not None and index < len(glass_sequence) else "AIR"
        advanced: dict[str, object] = {
            STEP_NATIVE_RECONSTRUCTION_ADVANCED_ATTR: fit.as_record(),
            "StepNativeSourcePath": str(source_path),
        }
        if any(abs(float(value)) > 0.0 for value in fit.aspher_data):
            advanced["AspherData"] = _aspher_data_200(fit.aspher_data)
        rows.append(
            SurfaceRow(
                label=str(index + 1),
                element=element_name,
                surface="Standard",
                name=f"STEP native {index + 1}: {fit.native_kind}",
                rc=float(fit.rc_mm),
                k=float(fit.conic_k),
                thickness=float(thickness),
                diameter=max(float(fit.diameter_mm), float(aperture_diameter_mm), 1.0),
                drawing=1.0,
                advanced=advanced,
                glass=glass or "AIR",
            )
        )
    return tuple(rows)


def reconstruct_step_native_document(
    document: StepAnalyticDocument,
    *,
    glass_sequence: Sequence[str] | None = None,
    asphere_terms: int = DEFAULT_ASPHERE_TERMS,
) -> StepNativeReconstruction:
    axis, axis_origin, aperture_diameter, diagnostics = _document_axis(document)
    basis_x, basis_y = _basis_from_axis(axis)
    candidates, candidate_diagnostics = _candidate_faces(document, axis, axis_origin, basis_x, basis_y)
    diagnostics.extend(candidate_diagnostics)
    groups = _group_candidates(candidates, aperture_diameter)
    fits = tuple(
        sorted(
            (
                _fit_group(
                    group,
                    axis_origin=axis_origin,
                    axis=axis,
                    aperture_diameter_mm=aperture_diameter,
                    term_count=max(1, int(asphere_terms)),
                )
                for group in groups
            ),
            key=lambda fit: float(fit.vertex_z_mm),
        )
    )
    if not fits:
        diagnostics.append(
            StepNativeDiagnostic("error", "no_native_surfaces", "No STEP faces could be rebuilt as native KrakenOS surfaces.")
        )
    for fit in fits:
        if not fit.supported:
            diagnostics.append(
                StepNativeDiagnostic(
                    "error",
                    "unsupported_native_fit",
                    f"{fit.surface_id} cannot be used as an exact/native optical surface: {', '.join(fit.notes) or fit.native_kind}",
                    fit.face_ids,
                )
            )
    if glass_sequence is None or len(tuple(glass_sequence)) < len(fits):
        diagnostics.append(
            StepNativeDiagnostic(
                "error",
                "material_sequence_required",
                "STEP geometry does not contain enough optical glass data; provide one glass/material after each native surface before tracing.",
            )
        )
    rows = _rows_from_fits(
        fits,
        source_path=document.source_path,
        aperture_diameter_mm=aperture_diameter,
        glass_sequence=glass_sequence,
    )
    trace_ready = bool(fits) and all(fit.supported for fit in fits) and glass_sequence is not None and len(tuple(glass_sequence)) >= len(fits)
    return StepNativeReconstruction(
        source_path=document.source_path,
        axis_direction=tuple(float(value) for value in axis[:3]),
        axis_origin=tuple(float(value) for value in axis_origin[:3]),
        basis_x=tuple(float(value) for value in basis_x[:3]),
        basis_y=tuple(float(value) for value in basis_y[:3]),
        aperture_diameter_mm=float(aperture_diameter),
        rows=rows,
        surface_fits=fits,
        diagnostics=tuple(diagnostics),
        trace_ready=trace_ready,
    )


def reconstruct_step_native_surfaces(
    source_path: Path | str,
    *,
    glass_sequence: Sequence[str] | None = None,
    asphere_terms: int = DEFAULT_ASPHERE_TERMS,
) -> StepNativeReconstruction:
    """Return a native KrakenOS surface stack for supported STEP optical faces."""

    document = load_step_analytic_document(source_path, skip_internal_duplicates=False)
    return reconstruct_step_native_document(
        document,
        glass_sequence=glass_sequence,
        asphere_terms=asphere_terms,
    )
