from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts


@dataclass(frozen=True)
class StlMeshDiagnostics:
    path: str
    file_format: str
    triangle_count: int
    unique_vertex_count: int
    bounds_min: tuple[float, float, float]
    bounds_max: tuple[float, float, float]
    extents: tuple[float, float, float]
    edge_count: int
    boundary_edge_count: int
    nonmanifold_edge_count: int
    degenerate_triangle_count: int
    signed_volume_mm3: float
    winding: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_trace_ready(self) -> bool:
        return (
            not self.errors
            and self.triangle_count > 0
            and self.boundary_edge_count == 0
            and self.nonmanifold_edge_count == 0
            and self.degenerate_triangle_count == 0
            and self.winding != "inverted"
        )


def read_stl_triangle_vertices(path: Path) -> tuple[str, np.ndarray]:
    data = Path(path).expanduser().read_bytes()
    if len(data) >= 84:
        triangle_count = struct.unpack("<I", data[80:84])[0]
        expected_binary_size = 84 + int(triangle_count) * 50
        if triangle_count > 0 and expected_binary_size == len(data):
            # Each 50-byte record is normal(3f) + verts(3x3f) + attr(u2). Read
            # the whole block in one structured frombuffer rather than a
            # per-triangle Python loop -- the loop cost ~1 s on a 0.6 M-triangle
            # vendor body, paid on every face-metadata bake.
            record_dtype = np.dtype(
                [("normal", "<f4", (3,)), ("verts", "<f4", (3, 3)), ("attr", "<u2")]
            )
            records = np.frombuffer(data, dtype=record_dtype, count=int(triangle_count), offset=84)
            triangles = np.ascontiguousarray(records["verts"], dtype=float)
            return "binary", triangles

    text = data.decode("utf-8", errors="ignore")
    vertices: list[tuple[float, float, float]] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 4 and parts[0].lower() == "vertex":
            try:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            except ValueError:
                continue
    if not vertices:
        raise ValueError("No STL vertices were found")
    if len(vertices) % 3:
        raise ValueError(f"ASCII STL vertex count is not divisible by 3: {len(vertices)}")
    return "ascii", np.asarray(vertices, dtype=float).reshape((-1, 3, 3))


def inspect_stl_mesh(path: Path) -> StlMeshDiagnostics:
    path = Path(path).expanduser()
    errors: list[str] = []
    warnings_out: list[str] = []
    try:
        file_format, triangles = read_stl_triangle_vertices(path)
    except Exception as exc:
        return StlMeshDiagnostics(
            path=str(path),
            file_format="unknown",
            triangle_count=0,
            unique_vertex_count=0,
            bounds_min=(0.0, 0.0, 0.0),
            bounds_max=(0.0, 0.0, 0.0),
            extents=(0.0, 0.0, 0.0),
            edge_count=0,
            boundary_edge_count=0,
            nonmanifold_edge_count=0,
            degenerate_triangle_count=0,
            signed_volume_mm3=0.0,
            winding="unknown",
            errors=(str(exc),),
        )

    if triangles.size == 0:
        errors.append("STL contains no triangles")
        bounds_min = bounds_max = extents = np.zeros(3, dtype=float)
    else:
        finite = np.isfinite(triangles)
        if not bool(np.all(finite)):
            errors.append("STL contains non-finite vertex coordinates")
            triangles = np.where(finite, triangles, 0.0)
        flat = triangles.reshape((-1, 3))
        bounds_min = np.min(flat, axis=0)
        bounds_max = np.max(flat, axis=0)
        extents = bounds_max - bounds_min

    max_extent = float(np.max(extents)) if triangles.size else 0.0
    vertex_decimals = 9
    edge_counter: Counter[tuple[tuple[float, float, float], tuple[float, float, float]]] = Counter()
    unique_vertices: set[tuple[float, float, float]] = set()
    degenerate = 0
    signed_volume = 0.0
    area_tolerance = max(max_extent * max_extent * 1e-18, 1e-24)
    for tri in triangles:
        q_vertices = [tuple(float(value) for value in np.round(vertex, vertex_decimals)) for vertex in tri]
        unique_vertices.update(q_vertices)
        v0, v1, v2 = (np.asarray(vertex, dtype=float) for vertex in tri)
        area2 = float(np.linalg.norm(np.cross(v1 - v0, v2 - v0)))
        if area2 <= area_tolerance:
            degenerate += 1
        signed_volume += float(np.dot(v0, np.cross(v1, v2)) / 6.0)
        for a_index, b_index in ((0, 1), (1, 2), (2, 0)):
            a = q_vertices[a_index]
            b = q_vertices[b_index]
            edge_counter[tuple(sorted((a, b)))] += 1

    boundary_edges = sum(1 for count in edge_counter.values() if count == 1)
    nonmanifold_edges = sum(1 for count in edge_counter.values() if count > 2)
    volume_tolerance = max(max_extent**3 * 1e-12, 1e-18)
    if abs(signed_volume) <= volume_tolerance:
        winding = "unknown"
    elif signed_volume < 0.0:
        winding = "inverted"
    else:
        winding = "outward"

    if max_extent <= 0.0:
        errors.append("STL has zero extent")
    elif max_extent < 1e-3:
        warnings_out.append("Mesh is smaller than 1 micron if interpreted as millimetres")
    elif max_extent > 1000.0:
        warnings_out.append("Mesh is larger than 1 metre if interpreted as millimetres")
    if boundary_edges:
        warnings_out.append(f"{boundary_edges} boundary edge(s); mesh is open")
    if nonmanifold_edges:
        warnings_out.append(f"{nonmanifold_edges} non-manifold edge(s)")
    if degenerate:
        warnings_out.append(f"{degenerate} degenerate triangle(s)")
    if winding == "inverted":
        warnings_out.append("Face winding appears inverted; flip normals if refraction exits the wrong side")
    elif winding == "unknown":
        warnings_out.append("Face winding could not be inferred from signed volume")
    if int(triangles.shape[0]) > 200_000:
        warnings_out.append("Large STL may trace slowly in non-sequential mode")

    return StlMeshDiagnostics(
        path=str(path),
        file_format=file_format,
        triangle_count=int(triangles.shape[0]),
        unique_vertex_count=len(unique_vertices),
        bounds_min=tuple(float(value) for value in bounds_min),
        bounds_max=tuple(float(value) for value in bounds_max),
        extents=tuple(float(value) for value in extents),
        edge_count=len(edge_counter),
        boundary_edge_count=boundary_edges,
        nonmanifold_edge_count=nonmanifold_edges,
        degenerate_triangle_count=degenerate,
        signed_volume_mm3=float(signed_volume),
        winding=winding,
        errors=tuple(errors),
        warnings=tuple(warnings_out),
    )


def format_stl_mesh_diagnostics(report: StlMeshDiagnostics) -> str:
    status = "READY" if report.is_trace_ready else "CHECK"
    lines = [
        f"STL mesh diagnostics: {Path(report.path).name}",
        f"Status: {status}",
        f"Path: {report.path}",
        f"Format: {report.file_format}",
        f"Triangles: {report.triangle_count}",
        f"Unique vertices: {report.unique_vertex_count}",
        "Bounds min [mm]: ({:.6g}, {:.6g}, {:.6g})".format(*report.bounds_min),
        "Bounds max [mm]: ({:.6g}, {:.6g}, {:.6g})".format(*report.bounds_max),
        "Extents [mm]: ({:.6g}, {:.6g}, {:.6g})".format(*report.extents),
        f"Edges: {report.edge_count}",
        f"Boundary edges: {report.boundary_edge_count}",
        f"Non-manifold edges: {report.nonmanifold_edge_count}",
        f"Degenerate triangles: {report.degenerate_triangle_count}",
        f"Signed volume [mm^3]: {report.signed_volume_mm3:.6g}",
        f"Face winding: {report.winding}",
    ]
    if report.errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {item}" for item in report.errors)
    if report.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {item}" for item in report.warnings)
    if not report.errors and not report.warnings:
        lines.extend(["", "No mesh warnings. This checks topology and scale only; material and pose still control physical tracing."])
    return "\n".join(lines)


def short_stl_mesh_diagnostics(report: StlMeshDiagnostics) -> str:
    status = "ready" if report.is_trace_ready else "check"
    max_extent = max(report.extents) if report.extents else 0.0
    return (
        f"{status}, {report.triangle_count} tri, max extent {max_extent:.6g} mm, "
        f"boundary={report.boundary_edge_count}, nonmanifold={report.nonmanifold_edge_count}, winding={report.winding}"
    )


def rotated_stl_bounds(path: Path, tilts: tuple[float, float, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    _format, triangles = read_stl_triangle_vertices(Path(path).expanduser())
    if triangles.size == 0:
        zeros = np.zeros(3, dtype=float)
        return zeros, zeros, zeros
    points = triangles.reshape((-1, 3))
    rotation = rotation_matrix_from_kraken_tilts(*tilts)
    rotated = points @ rotation.T
    bounds_min = np.min(rotated, axis=0)
    bounds_max = np.max(rotated, axis=0)
    center = 0.5 * (bounds_min + bounds_max)
    return bounds_min, bounds_max, center


def transformed_stl_points(
    path: Path,
    tilts: tuple[float, float, float],
    desp: tuple[float, float, float],
    z_station: float,
) -> np.ndarray:
    _format, triangles = read_stl_triangle_vertices(Path(path).expanduser())
    if triangles.size == 0:
        return np.empty((0, 3), dtype=float)
    points = triangles.reshape((-1, 3)).astype(float, copy=True)
    rotation = rotation_matrix_from_kraken_tilts(*tilts)
    points = points @ rotation.T
    points[:, 0] += float(desp[0])
    points[:, 1] += float(desp[1])
    points[:, 2] += float(z_station) + float(desp[2])
    return points


def transformed_stl_bounds(
    path: Path,
    tilts: tuple[float, float, float],
    desp: tuple[float, float, float],
    z_station: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = transformed_stl_points(path, tilts, desp, z_station)
    if points.size == 0:
        zeros = np.zeros(3, dtype=float)
        return zeros, zeros, zeros
    bounds_min = np.min(points, axis=0)
    bounds_max = np.max(points, axis=0)
    center = 0.5 * (bounds_min + bounds_max)
    return bounds_min, bounds_max, center


def convex_hull_2d(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[1] < 2:
        return np.empty((0, 2), dtype=float)
    finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    pts = pts[finite, :2]
    if pts.shape[0] == 0:
        return np.empty((0, 2), dtype=float)
    rounded = sorted({(round(float(x), 12), round(float(y), 12)) for x, y in pts})
    if len(rounded) <= 2:
        return np.asarray(rounded, dtype=float)

    def cross(o, a, b) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in rounded:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(rounded):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    if not hull:
        return np.asarray(rounded, dtype=float)
    hull.append(hull[0])
    return np.asarray(hull, dtype=float)
