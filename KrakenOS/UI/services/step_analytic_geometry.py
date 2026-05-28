"""OpenCascade STEP analytic face extraction.

This is the Tier 3 foundation for imported optical STEP solids.  It keeps the
STEP B-Rep face identity before any STL fallback, extracts analytic surface
descriptors, marks coincident multi-solid interior faces, and tessellates each
kept face with stable face-to-triangle ranges.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata


_SURFACE_TYPE_NAMES = {
    0: "plane",
    1: "cylinder",
    2: "cone",
    3: "sphere",
    4: "torus",
    5: "bezier",
    6: "bspline",
    7: "surface_of_revolution",
    8: "surface_of_extrusion",
    9: "offset",
    10: "other",
}


@dataclass(frozen=True)
class StepAnalyticFace:
    """One native STEP B-Rep face with optical-display metadata."""

    face_id: str
    solid_index: int
    source_face_index: int
    surface_type: str
    centroid: tuple[float, float, float]
    normal: tuple[float, float, float]
    area_mm2: float
    bbox: tuple[float, float, float, float, float, float]
    plane_offset_mm: float
    u_range: tuple[float, float]
    v_range: tuple[float, float]
    orientation_reversed: bool = False
    parameters: dict[str, object] = field(default_factory=dict)
    triangle_count: int = 0
    triangle_indices: tuple[int, ...] = ()
    interior_duplicate: bool = False
    duplicate_group: str = ""

    def as_optical_solid_record(self) -> dict[str, object]:
        """Return a face record compatible with current face-role metadata."""

        return {
            "face_id": self.face_id,
            "component_face_id": self.face_id,
            "source_face_id": self.face_id,
            "source_solid_index": int(self.solid_index),
            "source_face_index": int(self.source_face_index),
            "surface_type": self.surface_type,
            "analytic_parameters": dict(self.parameters),
            "interior_duplicate": bool(self.interior_duplicate),
            "duplicate_group": self.duplicate_group,
            "role": "Unassigned",
            "function": "Unassigned",
            "side_2d": "Auto",
            "normal": list(self.normal),
            "centroid": list(self.centroid),
            "area_mm2": float(self.area_mm2),
            "triangle_count": int(self.triangle_count),
            "triangle_indices": list(self.triangle_indices),
            "plane_offset_mm": float(self.plane_offset_mm),
            "port_role": "Auto",
            "fit_reference": "Auto",
            "flip_normal": False,
            "assignment_source": "step_analytic",
            "notes": "OpenCascade STEP analytic face",
        }


@dataclass(frozen=True)
class StepAnalyticDocument:
    """Analytic STEP topology plus a face-aware display tessellation."""

    source_path: Path
    source_format: str
    backend: str
    solid_count: int
    source_face_count: int
    faces: tuple[StepAnalyticFace, ...]
    outer_faces: tuple[StepAnalyticFace, ...]
    triangles: np.ndarray = field(repr=False, compare=False)
    warnings: tuple[str, ...] = ()

    @property
    def interior_duplicate_count(self) -> int:
        return sum(1 for face in self.faces if face.interior_duplicate)

    def optical_solid_face_metadata(self) -> dict[str, object]:
        metadata = normalize_optical_solid_face_metadata(
            {
                "source_step": str(self.source_path),
                "source_backend": self.backend,
                "faces": [face.as_optical_solid_record() for face in self.outer_faces],
            }
        )
        metadata["source_step"] = str(self.source_path)
        metadata["source_backend"] = self.backend
        metadata["source_face_count"] = int(self.source_face_count)
        metadata["outer_face_count"] = int(len(self.outer_faces))
        metadata["interior_duplicate_count"] = int(self.interior_duplicate_count)
        return metadata


@dataclass(frozen=True)
class _RawFace:
    shape: Any
    face: StepAnalyticFace


def _point_tuple(point: object) -> tuple[float, float, float]:
    return (float(point.X()), float(point.Y()), float(point.Z()))


def _direction_tuple(direction: object) -> tuple[float, float, float]:
    return _unit_tuple((float(direction.X()), float(direction.Y()), float(direction.Z())))


def _unit_tuple(values: object) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float).reshape(-1)[:3]
    if arr.size < 3:
        arr = np.pad(arr, (0, 3 - arr.size), mode="constant")
    norm = float(np.linalg.norm(arr))
    if norm <= 1e-12 or not np.isfinite(norm):
        arr = np.asarray((0.0, 0.0, 1.0), dtype=float)
    else:
        arr = arr / norm
    return (float(arr[0]), float(arr[1]), float(arr[2]))


def _finite_range(first: object, last: object) -> tuple[float, float]:
    try:
        a = float(first)
        b = float(last)
    except Exception:
        return (0.0, 1.0)
    if not np.isfinite(a) or not np.isfinite(b):
        return (0.0, 1.0)
    return (a, b)


def _midpoint_parameter(bounds: tuple[float, float]) -> float:
    first, last = bounds
    value = 0.5 * (float(first) + float(last))
    return value if np.isfinite(value) else float(first)


def _explore_shapes(shape: object, top_abs_kind: object):
    from OCC.Core.TopExp import TopExp_Explorer

    explorer = TopExp_Explorer(shape, top_abs_kind)
    while explorer.More():
        yield explorer.Current()
        explorer.Next()


def _face_bbox(face_shape: object) -> tuple[float, float, float, float, float, float]:
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    box.SetGap(0.0)
    brepbndlib.Add(face_shape, box)
    xmin, ymin, zmin, xmax, ymax, zmax = box.Get()
    return (float(xmin), float(ymin), float(zmin), float(xmax), float(ymax), float(zmax))


def _face_area_centroid(face_shape: object) -> tuple[float, tuple[float, float, float]]:
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    props = GProp_GProps()
    brepgprop.SurfaceProperties(face_shape, props)
    return (float(props.Mass()), _point_tuple(props.CentreOfMass()))


def _face_normal(surface: object, face_shape: object, u_range: tuple[float, float], v_range: tuple[float, float]):
    from OCC.Core.BRepLProp import BRepLProp_SLProps
    from OCC.Core.TopAbs import TopAbs_REVERSED

    u = _midpoint_parameter(u_range)
    v = _midpoint_parameter(v_range)
    try:
        props = BRepLProp_SLProps(surface, u, v, 1, 1.0e-7)
        if props.IsNormalDefined():
            normal = np.asarray(_direction_tuple(props.Normal()), dtype=float)
        else:
            normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
    except Exception:
        normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
    reversed_orientation = bool(face_shape.Orientation() == TopAbs_REVERSED)
    if reversed_orientation:
        normal = -normal
    return _unit_tuple(normal), reversed_orientation


def _surface_parameters(surface: object, surface_type: str) -> dict[str, object]:
    params: dict[str, object] = {}
    try:
        if surface_type == "plane":
            plane = surface.Plane()
            params["origin"] = list(_point_tuple(plane.Location()))
            params["axis"] = list(_direction_tuple(plane.Axis().Direction()))
        elif surface_type == "cylinder":
            cylinder = surface.Cylinder()
            params["radius_mm"] = float(cylinder.Radius())
            params["axis_origin"] = list(_point_tuple(cylinder.Axis().Location()))
            params["axis_direction"] = list(_direction_tuple(cylinder.Axis().Direction()))
        elif surface_type == "sphere":
            sphere = surface.Sphere()
            params["radius_mm"] = float(sphere.Radius())
            params["center"] = list(_point_tuple(sphere.Location()))
        elif surface_type == "cone":
            cone = surface.Cone()
            params["reference_radius_mm"] = float(cone.RefRadius())
            params["semi_angle_rad"] = float(cone.SemiAngle())
            params["axis_origin"] = list(_point_tuple(cone.Axis().Location()))
            params["axis_direction"] = list(_direction_tuple(cone.Axis().Direction()))
        elif surface_type == "torus":
            torus = surface.Torus()
            params["major_radius_mm"] = float(torus.MajorRadius())
            params["minor_radius_mm"] = float(torus.MinorRadius())
            params["axis_origin"] = list(_point_tuple(torus.Axis().Location()))
            params["axis_direction"] = list(_direction_tuple(torus.Axis().Direction()))
        elif surface_type == "bspline":
            bspline = surface.BSpline()
            params["u_degree"] = int(bspline.UDegree())
            params["v_degree"] = int(bspline.VDegree())
            params["u_poles"] = int(bspline.NbUPoles())
            params["v_poles"] = int(bspline.NbVPoles())
            params["rational"] = bool(bspline.IsURational() or bspline.IsVRational())
    except Exception:
        params["parameter_error"] = True
    return params


def _duplicate_signature(face: StepAnalyticFace) -> tuple[object, ...]:
    if face.surface_type == "sphere":
        center = tuple(float(np.round(value, 4)) for value in list(face.parameters.get("center", ()))[:3])
        radius = float(np.round(float(face.parameters.get("radius_mm", 0.0) or 0.0), 4))
        area = float(np.round(face.area_mm2, 3))
        return ("sphere", radius, center, area)
    if face.surface_type == "plane":
        normal = np.asarray(face.normal, dtype=float).reshape(3)
        offset = float(face.plane_offset_mm)
        canonical_index = int(np.argmax(np.abs(normal)))
        if normal[canonical_index] < 0.0:
            normal = -normal
            offset = -offset
        return (
            "plane",
            tuple(float(np.round(value, 4)) for value in normal),
            float(np.round(offset, 3)),
            float(np.round(face.area_mm2, 3)),
        )
    rounded_bbox = tuple(float(np.round(value, 3)) for value in face.bbox)
    rounded_area = float(np.round(face.area_mm2, 3))
    return (face.surface_type, rounded_area, rounded_bbox)


def _mark_interior_duplicates(raw_faces: list[_RawFace]) -> dict[str, tuple[bool, str]]:
    groups: dict[tuple[object, ...], list[StepAnalyticFace]] = {}
    for raw in raw_faces:
        groups.setdefault(_duplicate_signature(raw.face), []).append(raw.face)
    marks: dict[str, tuple[bool, str]] = {}
    group_index = 0
    for faces in groups.values():
        if len(faces) < 2:
            continue
        solid_indices = {int(face.solid_index) for face in faces}
        if len(solid_indices) < 2:
            continue
        normals = [np.asarray(face.normal, dtype=float).reshape(3) for face in faces]
        has_opposed_pair = any(
            float(np.dot(normals[i], normals[j])) < -0.90
            for i in range(len(normals))
            for j in range(i + 1, len(normals))
        )
        if not has_opposed_pair:
            continue
        group_index += 1
        duplicate_group = f"I{group_index:03d}"
        for face in faces:
            marks[face.face_id] = (True, duplicate_group)
    return marks


def _triangles_for_face(face_shape: object, *, reversed_orientation: bool) -> list[np.ndarray]:
    from OCC.Core.BRep import BRep_Tool
    from OCC.Core.TopLoc import TopLoc_Location

    location = TopLoc_Location()
    triangulation = BRep_Tool.Triangulation(face_shape, location)
    if triangulation is None:
        return []
    transform = location.Transformation()
    nodes: dict[int, np.ndarray] = {}
    for node_index in range(1, int(triangulation.NbNodes()) + 1):
        point = triangulation.Node(node_index).Transformed(transform)
        nodes[node_index] = np.asarray((point.X(), point.Y(), point.Z()), dtype=float)
    triangles: list[np.ndarray] = []
    for triangle_index in range(1, int(triangulation.NbTriangles()) + 1):
        indices = list(triangulation.Triangle(triangle_index).Get())
        if reversed_orientation and len(indices) == 3:
            indices = [indices[0], indices[2], indices[1]]
        try:
            triangle = np.asarray([nodes[int(index)] for index in indices], dtype=float)
        except Exception:
            continue
        if triangle.shape == (3, 3) and np.all(np.isfinite(triangle)):
            triangles.append(triangle)
    return triangles


def load_step_analytic_document(
    source_path: Path | str,
    *,
    linear_deflection_mm: float = 0.2,
    angular_deflection_rad: float = 0.2,
    skip_internal_duplicates: bool = True,
) -> StepAnalyticDocument:
    """Load STEP topology with analytic face descriptors and face-tagged mesh."""

    try:
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.STEPControl import STEPControl_Reader
        from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
    except Exception as exc:  # pragma: no cover - depends on optional CAD backend
        raise RuntimeError(f"pythonocc-core is required for analytic STEP import: {exc}") from exc

    source = Path(source_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"STEP file not found: {source}")
    if source.suffix.lower() not in {".step", ".stp"}:
        raise ValueError(f"Analytic STEP import only supports STEP/STP files: {source}")

    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != 1:
        raise RuntimeError(f"Could not read STEP file: {source}")
    if reader.TransferRoots() <= 0:
        raise RuntimeError(f"Could not transfer STEP roots: {source}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"STEP file produced a null shape: {source}")

    linear_deflection = max(float(linear_deflection_mm), 1.0e-4)
    angular_deflection = max(float(angular_deflection_rad), 1.0e-4)
    mesher = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesher.Perform()

    solids = list(_explore_shapes(shape, TopAbs_SOLID))
    solid_sources = solids if solids else [shape]
    raw_faces: list[_RawFace] = []
    global_face_index = 0
    for solid_index, solid_shape in enumerate(solid_sources, start=1):
        local_face_index = 0
        for face_shape in _explore_shapes(solid_shape, TopAbs_FACE):
            local_face_index += 1
            global_face_index += 1
            surface = BRepAdaptor_Surface(face_shape)
            surface_type = _SURFACE_TYPE_NAMES.get(int(surface.GetType()), f"geomabs_{int(surface.GetType())}")
            u_range = _finite_range(surface.FirstUParameter(), surface.LastUParameter())
            v_range = _finite_range(surface.FirstVParameter(), surface.LastVParameter())
            area, centroid = _face_area_centroid(face_shape)
            normal, reversed_orientation = _face_normal(surface, face_shape, u_range, v_range)
            plane_offset = float(np.dot(np.asarray(normal, dtype=float), np.asarray(centroid, dtype=float)))
            face_id = f"S{solid_index:03d}/F{local_face_index:03d}" if solids else f"F{local_face_index:03d}"
            raw_faces.append(
                _RawFace(
                    shape=face_shape,
                    face=StepAnalyticFace(
                        face_id=face_id,
                        solid_index=int(solid_index),
                        source_face_index=int(global_face_index),
                        surface_type=surface_type,
                        centroid=centroid,
                        normal=normal,
                        area_mm2=max(float(area), 0.0),
                        bbox=_face_bbox(face_shape),
                        plane_offset_mm=plane_offset,
                        u_range=u_range,
                        v_range=v_range,
                        orientation_reversed=reversed_orientation,
                        parameters=_surface_parameters(surface, surface_type),
                    ),
                )
            )

    duplicate_marks = _mark_interior_duplicates(raw_faces)
    faces: list[StepAnalyticFace] = []
    outer_faces: list[StepAnalyticFace] = []
    triangle_blocks: list[np.ndarray] = []
    next_triangle_index = 0
    for raw in raw_faces:
        is_internal, duplicate_group = duplicate_marks.get(raw.face.face_id, (False, ""))
        face = replace(raw.face, interior_duplicate=bool(is_internal), duplicate_group=duplicate_group)
        include_face = not (bool(skip_internal_duplicates) and bool(is_internal))
        if include_face:
            face_triangles = _triangles_for_face(raw.shape, reversed_orientation=face.orientation_reversed)
            triangle_count = len(face_triangles)
            triangle_indices = tuple(range(next_triangle_index, next_triangle_index + triangle_count))
            next_triangle_index += triangle_count
            if triangle_count:
                triangle_blocks.extend(face_triangles)
            face = replace(face, triangle_count=triangle_count, triangle_indices=triangle_indices)
            outer_faces.append(face)
        faces.append(face)

    triangles = (
        np.asarray(triangle_blocks, dtype=float).reshape((-1, 3, 3))
        if triangle_blocks
        else np.empty((0, 3, 3), dtype=float)
    )
    warnings: list[str] = []
    if not bool(mesher.IsDone()):
        warnings.append("OpenCascade face tessellation reported incomplete meshing.")
    if not outer_faces:
        warnings.append("No outer STEP faces were retained after duplicate filtering.")
    return StepAnalyticDocument(
        source_path=source,
        source_format="STEP",
        backend="OpenCascade",
        solid_count=len(solids),
        source_face_count=len(raw_faces),
        faces=tuple(faces),
        outer_faces=tuple(outer_faces),
        triangles=triangles,
        warnings=tuple(warnings),
    )


def step_analytic_face_metadata(source_path: Path | str) -> dict[str, object]:
    """Return current optical-solid metadata backed by native STEP faces."""

    return load_step_analytic_document(source_path).optical_solid_face_metadata()
