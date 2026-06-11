"""Geometry core for resizing an imported STEP/CAD solid by dragging a face.

This is the pure-geometry kernel behind the Open 3D "drag a face to grow a
dimension" workflow.  It has no Tk/VTK/editor state; the interaction layer feeds
it extents + a target and renders the result.

Two findings from the real vendor 50 mm cube beam-splitter
(``attachment/prisms/Beam_Splitter/32704/step_32704.step``) drive the design:

* A cube beam-splitter is **two right-angle prisms** (2 solids).  The cemented
  45-deg coating face has normal ``(1, 1, 0)/sqrt2`` -- equal nonzero on two
  principal axes, ~0 on the third.  Preserving the 45-deg coating under a resize
  requires the two axes the diagonal spans to scale by the **same** factor (the
  *coupled* pair); the third axis (the direction the coating is extruded along)
  is **free**.  Coupling both prisms together is automatic because they are one
  shape scaled as a unit, so "growing must go together" falls out for free.

* ``BRepBuilderAPI_GTransform`` with a non-uniform scale silently degrades the
  analytic ``Plane`` faces to ``BSpline`` surfaces, which would hurt the
  downstream face-role / analytic-fit heuristics.  So the resize is applied in
  **mesh space** (scale the vertices) -- exact for box/prism solids, planar
  faces stay planar -- while coupling **detection** reads the clean analytic
  planes off the *original* B-rep.  The mesh-space normal transform here
  (inverse-transpose of a diagonal scale, i.e. ``n / scales`` renormalized)
  reproduces OpenCascade's GTransform normal exactly (cross-checked against the
  vendor part: coupled 55x55x78 -> ``(0.707, 0.707, 0)``; non-coupled 55x50x78
  -> ``(0.673, 0.74, 0)``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

_AXIS_LABELS = ("X", "Y", "Z")


@dataclass(frozen=True)
class ResizeAxes:
    """Axis roles for a coupled (beam-splitter-style) resize.

    ``free_axis`` is the unconstrained depth axis (the coating's extrusion
    direction); ``coupled_axes`` are the two axes the 45-deg diagonal spans and
    that must scale together to keep the coating at 45 deg.
    """

    free_axis: int
    coupled_axes: tuple[int, int]
    coupling_normal: tuple[float, float, float]

    def axis_label(self, axis: int) -> str:
        return _AXIS_LABELS[int(axis)] if 0 <= int(axis) < 3 else str(axis)

    @property
    def free_label(self) -> str:
        return self.axis_label(self.free_axis)

    @property
    def coupled_labels(self) -> tuple[str, str]:
        return (self.axis_label(self.coupled_axes[0]), self.axis_label(self.coupled_axes[1]))


# --------------------------------------------------------------------------- #
# Coupling detection (reads the original B-rep's clean analytic planes)        #
# --------------------------------------------------------------------------- #
def detect_coupling_from_faces(
    faces: Iterable[tuple[Sequence[float], float]],
    *,
    axis_tol: float = 0.06,
    equal_tol: float = 0.06,
    min_component: float = 0.3,
) -> ResizeAxes | None:
    """Find the beam-splitter coating signature among planar faces.

    ``faces`` is an iterable of ``(normal_xyz, area)``.  The coating is the
    largest-area planar face whose unit normal is ~0 on exactly one principal
    axis and ~equal nonzero on the other two (e.g. ``(1, 1, 0)/sqrt2``).  Returns
    the axis roles, or ``None`` when no such face exists (a plain element -> free
    per-axis resize).
    """
    best: ResizeAxes | None = None
    best_area = -1.0
    for normal, area in faces:
        n = np.abs(np.asarray(normal, dtype=float).reshape(-1)[:3])
        norm = float(np.linalg.norm(n))
        if norm <= 0.0 or not np.isfinite(norm):
            continue
        n = n / norm
        order = np.argsort(n)  # ascending: order[0] = smallest component = free candidate
        small, mid, big = n[order[0]], n[order[1]], n[order[2]]
        if (
            small <= axis_tol
            and abs(big - mid) <= equal_tol
            and mid >= min_component
            and float(area) > best_area
        ):
            coupled = tuple(sorted((int(order[1]), int(order[2]))))
            best = ResizeAxes(
                free_axis=int(order[0]),
                coupled_axes=coupled,  # type: ignore[arg-type]
                coupling_normal=tuple(round(float(v), 6) for v in n),  # type: ignore[arg-type]
            )
            best_area = float(area)
    return best


def planar_face_normals_areas(shape) -> list[tuple[tuple[float, float, float], float]]:
    """Sampled ``(normal, area)`` for every planar face of an OCC shape.

    Returns ``[]`` if pythonocc-core is unavailable or the shape has no planar
    faces, so callers can degrade to a free resize without a hard dependency.
    """
    try:
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.BRepGProp import BRepGProp_Face, brepgprop
        from OCC.Core.GeomAbs import GeomAbs_Plane
        from OCC.Core.GProp import GProp_GProps
        from OCC.Core.gp import gp_Pnt, gp_Vec
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
    except Exception:
        return []

    out: list[tuple[tuple[float, float, float], float]] = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = topods.Face(explorer.Current())
        explorer.Next()
        try:
            surface = BRepAdaptor_Surface(face)
            if surface.GetType() != GeomAbs_Plane:
                continue
            u = 0.5 * (surface.FirstUParameter() + surface.LastUParameter())
            v = 0.5 * (surface.FirstVParameter() + surface.LastVParameter())
            point, vec = gp_Pnt(), gp_Vec()
            BRepGProp_Face(face).Normal(u, v, point, vec)
            normal = np.array([vec.X(), vec.Y(), vec.Z()], dtype=float)
            norm = float(np.linalg.norm(normal))
            if norm <= 0.0:
                continue
            normal = normal / norm
            props = GProp_GProps()
            brepgprop.SurfaceProperties(face, props)
            out.append((tuple(float(c) for c in normal), float(props.Mass())))
        except Exception:
            continue
    return out


def detect_coupling(shape) -> ResizeAxes | None:
    """Convenience: detect coupling directly from an OCC shape."""
    return detect_coupling_from_faces(planar_face_normals_areas(shape))


# --------------------------------------------------------------------------- #
# Mesh-space resize math (no OCC; exact for box/prism solids)                  #
# --------------------------------------------------------------------------- #
def extents_of(points: np.ndarray) -> np.ndarray:
    """Axis-aligned extents (size along X/Y/Z) of a point cloud."""
    pts = np.asarray(points, dtype=float)[:, :3]
    return np.maximum(np.max(pts, axis=0) - np.min(pts, axis=0), 0.0)


def axis_scales_for_extents(
    current_extents: Sequence[float],
    target_extents: Sequence[float],
    *,
    min_extent: float = 1e-6,
) -> np.ndarray:
    """Per-axis scale factors mapping ``current_extents`` to ``target_extents``.

    A non-positive or non-finite target leaves that axis at scale 1.0 (the
    caller asked to change only some dimensions).
    """
    current = np.asarray(current_extents, dtype=float).reshape(-1)[:3]
    target = np.asarray(target_extents, dtype=float).reshape(-1)[:3]
    scales = np.ones(3, dtype=float)
    for axis in range(3):
        c, t = current[axis], target[axis]
        if np.isfinite(c) and np.isfinite(t) and c > min_extent and t > 0.0:
            scales[axis] = t / c
    return scales


def coupled_scales(
    axes: ResizeAxes,
    current_extents: Sequence[float],
    *,
    cross_section: float | None = None,
    depth: float | None = None,
    min_extent: float = 1e-6,
) -> np.ndarray:
    """Scale factors for a coupled resize.

    ``cross_section`` is the target size for *both* coupled axes (forces a square
    cross-section, keeping the 45-deg coating exact); ``depth`` is the target
    size of the free axis.  Either may be ``None`` to leave it unchanged.
    """
    current = np.asarray(current_extents, dtype=float).reshape(-1)[:3]
    scales = np.ones(3, dtype=float)
    if cross_section is not None and cross_section > 0.0:
        for axis in axes.coupled_axes:
            if current[axis] > min_extent:
                scales[axis] = float(cross_section) / current[axis]
    if depth is not None and depth > 0.0 and current[axes.free_axis] > min_extent:
        scales[axes.free_axis] = float(depth) / current[axes.free_axis]
    return scales


def anchor_point_for_fixed_face(
    bounds_min: Sequence[float],
    bounds_max: Sequence[float],
    fixed_axis: int,
    fixed_at_max: bool,
) -> np.ndarray:
    """Anchor point that keeps one face fixed while the opposite face moves.

    The dragged face grows outward from the fixed (opposite) face.  Off-axis
    coordinates use the box centre so the body grows symmetrically across the
    other axes.
    """
    lo = np.asarray(bounds_min, dtype=float).reshape(-1)[:3]
    hi = np.asarray(bounds_max, dtype=float).reshape(-1)[:3]
    anchor = 0.5 * (lo + hi)
    anchor[int(fixed_axis)] = hi[int(fixed_axis)] if fixed_at_max else lo[int(fixed_axis)]
    return anchor


def anchored_scale_matrix(scales: Sequence[float], anchor: Sequence[float]) -> np.ndarray:
    """4x4 affine that scales about ``anchor`` (so ``anchor`` stays put)."""
    s = np.asarray(scales, dtype=float).reshape(-1)[:3]
    a = np.asarray(anchor, dtype=float).reshape(-1)[:3]
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = np.diag(s)
    matrix[:3, 3] = a - np.diag(s) @ a
    return matrix


def resize_points(
    points: np.ndarray,
    scales: Sequence[float],
    anchor: Sequence[float],
) -> np.ndarray:
    """Apply an anchored per-axis scale to an ``(N, 3)`` point cloud."""
    pts = np.asarray(points, dtype=float)[:, :3]
    matrix = anchored_scale_matrix(scales, anchor)
    homogeneous = np.column_stack([pts, np.ones(pts.shape[0], dtype=float)])
    return (homogeneous @ matrix.T)[:, :3]


def transform_normal(normal: Sequence[float], scales: Sequence[float]) -> np.ndarray:
    """Transform a surface normal under a diagonal scale (inverse-transpose).

    For a diagonal scale this is ``n / scales`` renormalized -- reproduces
    OpenCascade's GTransform normal exactly.
    """
    n = np.asarray(normal, dtype=float).reshape(-1)[:3]
    s = np.asarray(scales, dtype=float).reshape(-1)[:3]
    safe = np.where(np.abs(s) > 0.0, s, 1.0)
    out = n / safe
    norm = float(np.linalg.norm(out))
    return out / norm if norm > 0.0 else out


def is_coating_preserved(
    coupling_normal: Sequence[float],
    scales: Sequence[float],
    *,
    free_tol: float = 1e-3,
    equal_tol: float = 1e-3,
) -> bool:
    """True if the coating normal stays at 45 deg after ``scales`` are applied.

    The transformed normal must keep ~0 on the free axis and ~equal nonzero on
    the two coupled axes -- the geometric meaning of "still a 45-deg splitter".
    """
    transformed = np.abs(transform_normal(coupling_normal, scales))
    order = np.argsort(transformed)
    small, mid, big = transformed[order[0]], transformed[order[1]], transformed[order[2]]
    return bool(small <= free_tol and abs(big - mid) <= equal_tol)
