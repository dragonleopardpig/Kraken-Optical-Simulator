"""CAD and STEP export geometry helpers for the layout editor."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np


def _rotation_matrix_xyz(angles_deg) -> np.ndarray:
    ax, ay, az = (float(v) for v in angles_deg)
    rx = np.deg2rad(ax)
    ry = np.deg2rad(ay)
    rz = np.deg2rad(az)
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    rot_x = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]], dtype=float)
    rot_y = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]], dtype=float)
    rot_z = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]], dtype=float)
    return rot_z @ rot_y @ rot_x


def _convex_hull_2d(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] != 2:
        return pts
    pts = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    unique = [pts[0]]
    for point in pts[1:]:
        if np.linalg.norm(point - unique[-1]) > 1e-9:
            unique.append(point)
    pts = np.asarray(unique, dtype=float)
    if pts.shape[0] < 3:
        return pts

    def cross(o, a, b) -> float:
        return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    lower: list[np.ndarray] = []
    for point in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0.0:
            lower.pop()
        lower.append(point)
    upper: list[np.ndarray] = []
    for point in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0.0:
            upper.pop()
        upper.append(point)
    hull = np.asarray(lower[:-1] + upper[:-1], dtype=float)
    return hull


def _profile_from_section_points(yz: np.ndarray, bins: int = 180) -> np.ndarray:
    pts = np.asarray(yz, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 8 or pts.shape[1] != 2:
        return np.empty((0, 2), dtype=float)
    pts = pts[np.all(np.isfinite(pts), axis=1)]
    if pts.shape[0] < 8:
        return np.empty((0, 2), dtype=float)
    z_vals = pts[:, 0]
    y_vals = pts[:, 1]
    z_min = float(np.min(z_vals))
    z_max = float(np.max(z_vals))
    if not np.isfinite(z_min) or not np.isfinite(z_max) or z_max <= z_min:
        return np.empty((0, 2), dtype=float)
    edges = np.linspace(z_min, z_max, max(int(bins), 24) + 1)
    top: list[tuple[float, float]] = []
    bot: list[tuple[float, float]] = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (z_vals >= lo) & (z_vals <= hi if hi == edges[-1] else z_vals < hi)
        if not np.any(mask):
            continue
        z_mid = float(np.mean(z_vals[mask]))
        ys = y_vals[mask]
        top.append((z_mid, float(np.max(ys))))
        bot.append((z_mid, float(np.min(ys))))
    if len(top) < 4 or len(bot) < 4:
        return np.empty((0, 2), dtype=float)
    return np.array(top + bot[::-1] + [top[0]], dtype=float)


# ---------------------------------------------------------------------------
# Analytic STEP export helpers
# ---------------------------------------------------------------------------

def _is_surface_revolution_compatible(sdt_surf) -> bool:
    """True when a KrakenOS surface is rotationally symmetric and can be
    exported as an OpenCascade surface of revolution instead of triangles."""
    if getattr(sdt_surf, 'Cylinder_Rxy_Ratio', 1.0) != 1.0:
        return False
    if len(getattr(sdt_surf, 'Error_map', [])) != 0:
        return False
    znk = getattr(sdt_surf, 'ZNK', None)
    if znk is not None and np.any(np.asarray(znk) != 0):
        return False
    extra = getattr(sdt_surf, 'ExtraData', None)
    if extra is not None and np.any(np.asarray(extra) != 0):
        return False
    if str(getattr(sdt_surf, 'Solid_3d_stl', 'None')) != 'None':
        return False
    if getattr(sdt_surf, 'ShiftX', 0.0) != 0.0:
        return False
    if getattr(sdt_surf, 'ShiftY', 0.0) != 0.0:
        return False
    return True


def _compute_revolution_sag(r: float, sdt_surf) -> float:
    """Sag z(r) for a rotationally symmetric KrakenOS surface (conic +
    even-power aspheric + axicon)."""
    import math as _m
    z = 0.0
    Rc = float(getattr(sdt_surf, 'Rc', 0.0))
    k = float(getattr(sdt_surf, 'k', 0.0))
    if Rc != 0.0:
        c = 1.0 / Rc
        s2 = r * r
        in_root = 1.0 - (k + 1.0) * c * c * s2
        z = c * s2 / (1.0 + _m.sqrt(abs(in_root)))
    aspher = getattr(sdt_surf, 'AspherData', None)
    if aspher is not None:
        for i in range(1, 9):
            coeff = float(aspher[i - 1]) if i - 1 < len(aspher) else 0.0
            if coeff != 0.0:
                z += coeff * r ** (2 * i)
    axicon = float(getattr(sdt_surf, 'Axicon', 0.0))
    if axicon != 0.0:
        z += r * _m.tan(_m.radians(axicon))
    return z


def _make_occ_flat_disc(outer_radius: float, inner_radius: float = 0.0):
    """Planar disc (or annulus) as a single OpenCascade ADVANCED_FACE."""
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_MakeEdge,
        BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_MakeWire,
    )
    from OCC.Core.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

    center = gp_Pnt(0.0, 0.0, 0.0)
    axis = gp_Ax2(center, gp_Dir(0.0, 0.0, 1.0))
    outer_edge = BRepBuilderAPI_MakeEdge(gp_Circ(axis, float(outer_radius))).Edge()
    outer_wire = BRepBuilderAPI_MakeWire(outer_edge).Wire()
    fm = BRepBuilderAPI_MakeFace(outer_wire)
    if inner_radius > 1e-9:
        inner_edge = BRepBuilderAPI_MakeEdge(gp_Circ(axis, float(inner_radius))).Edge()
        inner_wire = BRepBuilderAPI_MakeWire(inner_edge).Wire()
        fm.Add(inner_wire)
    return fm.Face() if fm.IsDone() else None


def _make_occ_revolution_face(sdt_surf, n_profile_points: int = 64):
    """Create an OCC face by revolving the sag profile z(r).

    Flat surfaces produce a proper planar disc instead.  Curved surfaces
    (spherical, conic, aspheric, axicon) yield a single SURFACE_OF_REVOLUTION
    — one ADVANCED_FACE instead of thousands of triangles.
    """
    import math as _m
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeRevol
    from OCC.Core.GeomAPI import GeomAPI_PointsToBSpline
    from OCC.Core.TColgp import TColgp_Array1OfPnt
    from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt

    semi_d = float(getattr(sdt_surf, 'Diameter', 0.0)) / 2.0
    semi_in = float(getattr(sdt_surf, 'InDiameter', 0.0)) / 2.0
    if semi_d <= 0:
        return None

    Rc = float(getattr(sdt_surf, 'Rc', 0.0))
    has_aspher = np.any(np.asarray(getattr(sdt_surf, 'AspherData', np.zeros(1))) != 0)
    has_axicon = float(getattr(sdt_surf, 'Axicon', 0.0)) != 0.0

    if Rc == 0.0 and not has_aspher and not has_axicon:
        return _make_occ_flat_disc(semi_d, semi_in)

    # Sample profile in the XZ half-plane
    r_start = max(semi_in, semi_d * 1e-4)
    pts = []
    for i in range(n_profile_points + 1):
        r = r_start + (semi_d - r_start) * i / n_profile_points
        z = _compute_revolution_sag(r, sdt_surf)
        pts.append(gp_Pnt(float(r), 0.0, float(z)))

    arr = TColgp_Array1OfPnt(1, len(pts))
    for i, pt in enumerate(pts):
        arr.SetValue(i + 1, pt)
    try:
        bspline = GeomAPI_PointsToBSpline(arr, 3, 8).Curve()
        edge = BRepBuilderAPI_MakeEdge(bspline).Edge()
    except Exception:
        return None

    axis = gp_Ax1(gp_Pnt(0.0, 0.0, 0.0), gp_Dir(0.0, 0.0, 1.0))
    try:
        revol = BRepPrimAPI_MakeRevol(edge, axis, 2.0 * _m.pi)
        return revol.Shape() if revol.IsDone() else None
    except Exception:
        return None


def _numpy_mat_to_occ_trsf(mat_4x4):
    """Convert a 4x4 numpy affine matrix to gp_Trsf (rotation + translation)."""
    from OCC.Core.gp import gp_Trsf
    m = np.asarray(mat_4x4, dtype=float)
    if m.shape != (4, 4):
        return None
    trsf = gp_Trsf()
    try:
        trsf.SetValues(
            m[0, 0], m[0, 1], m[0, 2], m[0, 3],
            m[1, 0], m[1, 1], m[1, 2], m[1, 3],
            m[2, 0], m[2, 1], m[2, 2], m[2, 3],
        )
    except Exception:
        return None
    return trsf


def _numpy_mat_to_occ_gtrsf(mat_4x4):
    """Convert a 4x4 numpy affine matrix to gp_GTrsf."""
    from OCC.Core.gp import gp_GTrsf

    m = np.asarray(mat_4x4, dtype=float)
    if m.shape != (4, 4):
        return None
    trsf = gp_GTrsf()
    try:
        for row in range(3):
            for column in range(4):
                trsf.SetValue(row + 1, column + 1, float(m[row, column]))
    except Exception:
        return None
    return trsf


def _is_rigid_affine_matrix(mat_4x4, *, atol: float = 1e-6) -> bool:
    m = np.asarray(mat_4x4, dtype=float)
    if m.shape != (4, 4) or not np.all(np.isfinite(m)):
        return False
    if not np.allclose(m[3, :], np.array([0.0, 0.0, 0.0, 1.0], dtype=float), atol=atol):
        return False
    rotation = np.asarray(m[:3, :3], dtype=float)
    try:
        orthogonality = rotation.T @ rotation
        determinant = float(np.linalg.det(rotation))
    except Exception:
        return False
    if not np.allclose(orthogonality, np.eye(3, dtype=float), atol=atol):
        return False
    return abs(abs(determinant) - 1.0) <= 1e-5


def _affine_from_point_sets(source_points: np.ndarray, target_points: np.ndarray, *, max_samples: int = 5000) -> np.ndarray | None:
    source = np.asarray(source_points, dtype=float)
    target = np.asarray(target_points, dtype=float)
    if source.ndim != 2 or target.ndim != 2 or source.shape != target.shape or source.shape[1] < 3:
        return None
    source = source[:, :3]
    target = target[:, :3]
    finite = np.all(np.isfinite(source), axis=1) & np.all(np.isfinite(target), axis=1)
    source = source[finite]
    target = target[finite]
    if source.shape[0] < 4:
        return None
    if source.shape[0] > max_samples:
        indices = np.linspace(0, source.shape[0] - 1, max_samples, dtype=int)
        source = source[indices]
        target = target[indices]
    design = np.column_stack([source, np.ones(source.shape[0], dtype=float)])
    try:
        coeffs, *_ = np.linalg.lstsq(design, target, rcond=None)
    except Exception:
        return None
    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = coeffs[:3, :].T
    matrix[:3, 3] = coeffs[3, :]
    return matrix


def _read_step_shape(path: Path):
    try:
        from OCC.Core.STEPControl import STEPControl_Reader
    except Exception as exc:
        raise RuntimeError(f"pythonocc-core is required for native STEP export: {exc}") from exc
    source = Path(path).expanduser()
    reader = STEPControl_Reader()
    if reader.ReadFile(str(source)) != 1:
        raise RuntimeError(f"Could not read STEP file: {source}")
    if reader.TransferRoots() <= 0:
        raise RuntimeError(f"Could not transfer STEP roots: {source}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"STEP file produced a null shape: {source}")
    return shape


def _shape_with_affine(shape, mat_4x4):
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_GTransform, BRepBuilderAPI_Transform

    if _is_rigid_affine_matrix(mat_4x4):
        trsf = _numpy_mat_to_occ_trsf(mat_4x4)
        if trsf is None:
            raise RuntimeError("Could not build OpenCascade rigid transform")
        transformed = BRepBuilderAPI_Transform(shape, trsf, True)
    else:
        gtrsf = _numpy_mat_to_occ_gtrsf(mat_4x4)
        if gtrsf is None:
            raise RuntimeError("Could not build OpenCascade affine transform")
        transformed = BRepBuilderAPI_GTransform(shape, gtrsf, True)
    if not transformed.IsDone():
        raise RuntimeError("OpenCascade shape transform failed")
    result = transformed.Shape()
    if result.IsNull():
        raise RuntimeError("OpenCascade shape transform produced a null shape")
    return result


def _write_meshes_to_faceted_step(
    mesh_items: list[tuple[str, object]],
    target_path: Path,
    *,
    max_facets_per_mesh: int = 4000,
) -> tuple[int, int]:
    """Write PyVista surface meshes as renderable shell-based STEP.

    This is the compatibility path for imported vendor CAD.  The earlier
    per-triangle compound produced one OPEN_SHELL/shape representation per
    face, which made downstream viewers spend a long time healing tolerances.
    Building one shell per displayed mesh keeps the file renderable in STEP
    viewers while avoiding the AP242 tessellation entities that some viewers
    import but do not draw.
    """
    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.Interface import Interface_Static
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Shell
        from OCC.Core.gp import gp_Pnt
    except Exception as exc:
        raise RuntimeError(f"pythonocc-core is required for STEP export: {exc}") from exc

    target_path = Path(target_path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    mesh_count = 0
    triangle_count = 0

    for _label, mesh in mesh_items:
        prepared_mesh = _mesh_points_and_triangles_for_step(
            mesh,
            max_facets_per_mesh=max_facets_per_mesh,
        )
        if prepared_mesh is None:
            continue
        points, triangles = prepared_mesh
        shell = TopoDS_Shell()
        builder.MakeShell(shell)
        added_for_mesh = 0
        for a, b, c in triangles:
            tri_points = points[[int(a) - 1, int(b) - 1, int(c) - 1], :3]
            polygon = BRepBuilderAPI_MakePolygon()
            for x, y, z in tri_points:
                polygon.Add(gp_Pnt(float(x), float(y), float(z)))
            polygon.Close()
            if not polygon.IsDone():
                continue
            face = BRepBuilderAPI_MakeFace(polygon.Wire())
            if not face.IsDone():
                continue
            builder.Add(shell, face.Face())
            added_for_mesh += 1
        if added_for_mesh:
            builder.Add(compound, shell)
            mesh_count += 1
            triangle_count += added_for_mesh

    if triangle_count <= 0:
        raise RuntimeError("No valid 3D surface triangles were available for STEP export")

    writer = STEPControl_Writer()
    try:
        Interface_Static.SetCVal("write.step.unit", "MM")
    except Exception:
        pass
    try:
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            writer.Transfer(compound, STEPControl_AsIs)
            status = writer.Write(str(target_path))
    except Exception:
        writer.Transfer(compound, STEPControl_AsIs)
        status = writer.Write(str(target_path))
    finally:
        for src_fd, dst_fd in ((locals().get("stdout_fd"), 1), (locals().get("stderr_fd"), 2)):
            if src_fd is None:
                continue
            try:
                os.dup2(int(src_fd), dst_fd)
                os.close(int(src_fd))
            except Exception:
                pass
    if status != IFSelect_RetDone or not target_path.exists() or target_path.stat().st_size <= 0:
        raise RuntimeError("STEP writer failed")
    return mesh_count, triangle_count


def _mesh_points_and_triangles_for_step(
    mesh,
    *,
    max_facets_per_mesh: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    if mesh is None:
        return None
    try:
        surface = mesh.extract_surface(algorithm="dataset_surface").triangulate().clean()
        face_count = int(getattr(surface, "n_cells", 0))
        if face_count > max_facets_per_mesh > 0:
            reduction = 1.0 - (float(max_facets_per_mesh) / float(face_count))
            try:
                surface = surface.decimate_pro(
                    min(max(reduction, 0.0), 0.98),
                    preserve_topology=False,
                ).triangulate().clean()
            except Exception:
                # Some vendor STL meshes have non-manifold regions where VTK
                # decimation fails. Exporting the cleaned triangles is still
                # safer than falling back to per-triangle BRep shells.
                surface = surface.triangulate().clean()
        points = np.asarray(surface.points, dtype=float)
        faces = np.asarray(surface.faces, dtype=int)
    except Exception:
        return None

    if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] < 3 or faces.size == 0:
        return None

    triangles: list[tuple[int, int, int]] = []
    cursor = 0
    while cursor < int(faces.size):
        vertex_count = int(faces[cursor])
        ids = [int(value) for value in faces[cursor + 1: cursor + 1 + vertex_count]]
        cursor += vertex_count + 1
        if vertex_count < 3:
            continue
        for tri_index in range(1, vertex_count - 1):
            tri = (ids[0], ids[tri_index], ids[tri_index + 1])
            tri_points = points[list(tri), :3]
            if not np.all(np.isfinite(tri_points)):
                continue
            area2 = float(np.linalg.norm(np.cross(tri_points[1] - tri_points[0], tri_points[2] - tri_points[0])))
            if area2 <= 1e-12:
                continue
            # Keep triangle indices 1-based so both STEP writers and validators
            # can use them without another conversion pass.
            triangles.append((tri[0] + 1, tri[1] + 1, tri[2] + 1))

    if not triangles:
        return None
    return points[:, :3], np.asarray(triangles, dtype=int)


def occ_shell_shape_from_mesh(mesh, *, max_facets_per_mesh: int = 4000):
    """A single OpenCascade shell (one TopoDS_Shell) tessellating a PyVista mesh.

    bugs/0300: promoted optical-solid rows (the folded BK7 RA prisms) are drawn in
    the 3D inspector from their STL tessellation, not from the shared ``step_*.step``
    template that lives in a different local frame. So the faithful STEP body for such
    a row is that STL, already carried into world by the display transform, written as
    faceted geometry -- deterministic, no ambiguous box-ICP against the template.
    Returns ``None`` when the mesh yields no usable triangles.
    """
    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
        from OCC.Core.TopoDS import TopoDS_Shell
        from OCC.Core.gp import gp_Pnt
    except Exception as exc:
        raise RuntimeError(f"pythonocc-core is required for STEP export: {exc}") from exc

    prepared = _mesh_points_and_triangles_for_step(mesh, max_facets_per_mesh=max_facets_per_mesh)
    if prepared is None:
        return None
    points, triangles = prepared
    builder = BRep_Builder()
    shell = TopoDS_Shell()
    builder.MakeShell(shell)
    added = 0
    for a, b, c in triangles:
        tri_points = points[[int(a) - 1, int(b) - 1, int(c) - 1], :3]
        polygon = BRepBuilderAPI_MakePolygon()
        for x, y, z in tri_points:
            polygon.Add(gp_Pnt(float(x), float(y), float(z)))
        polygon.Close()
        if not polygon.IsDone():
            continue
        face = BRepBuilderAPI_MakeFace(polygon.Wire())
        if not face.IsDone():
            continue
        builder.Add(shell, face.Face())
        added += 1
    if added <= 0:
        return None
    return shell


def _write_step_with_analytic_surfaces(
    system,
    rows: list,
    edge_mesh_items: list[tuple[str, object]],
    target_path: Path,
    *,
    max_edge_facets: int = 300,
    profile_points: int = 64,
) -> tuple[int, int, int]:
    """Write STEP using analytic revolution surfaces for optical elements.

    Optical surfaces that are rotationally symmetric (spherical, conic,
    aspheric, axicon) are exported as a single SURFACE_OF_REVOLUTION face
    each.  Edge geometry and imported meshes use faceted fallback with
    aggressive decimation.

    Returns (analytic_count, faceted_mesh_count, triangle_count).
    """
    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepBuilderAPI import (
            BRepBuilderAPI_MakeFace,
            BRepBuilderAPI_MakePolygon,
            BRepBuilderAPI_Transform,
        )
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.Interface import Interface_Static
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCC.Core.TopoDS import TopoDS_Compound
        from OCC.Core.gp import gp_Pnt
    except Exception as exc:
        raise RuntimeError(f"pythonocc-core is required for STEP export: {exc}") from exc

    target_path = Path(target_path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)

    sdt = getattr(system, 'SDT', [])
    trans_2a = getattr(system, 'TRANS_2A', [])

    analytic_count = 0
    faceted_mesh_count = 0
    tri_count = 0

    # --- Phase 1: analytic optical surfaces ---
    n_surf = min(len(sdt), len(rows))
    for j in range(n_surf):
        # bugs/0300: export the Object/Image reference planes too (they are drawn in
        # the 3D inspector). The Drawing / Diameter guards below drop hidden or
        # degenerate planes, matching the display.
        surf = sdt[j]
        if not getattr(surf, 'Drawing', 1):
            continue
        if float(getattr(surf, 'Diameter', 0)) <= 0:
            continue
        if not _is_surface_revolution_compatible(surf):
            continue

        occ_shape = _make_occ_revolution_face(surf, profile_points)
        if occ_shape is None:
            continue

        if j < len(trans_2a):
            trsf = _numpy_mat_to_occ_trsf(trans_2a[j])
            if trsf is not None:
                try:
                    occ_shape = BRepBuilderAPI_Transform(occ_shape, trsf, True).Shape()
                except Exception:
                    continue

        builder.Add(compound, occ_shape)
        analytic_count += 1

    # --- Phase 2: faceted edge geometry + extras ---
    for _label, mesh in edge_mesh_items:
        if mesh is None:
            continue
        try:
            surface = mesh.extract_surface(algorithm="dataset_surface").triangulate().clean()
            fc = int(getattr(surface, "n_cells", 0))
            if fc > max_edge_facets > 0:
                reduction = 1.0 - float(max_edge_facets) / float(fc)
                try:
                    surface = surface.decimate_pro(
                        min(max(reduction, 0.0), 0.98),
                        preserve_topology=True,
                    ).triangulate().clean()
                except Exception:
                    pass
            points = np.asarray(surface.points, dtype=float)
            faces = np.asarray(surface.faces, dtype=int)
        except Exception:
            continue
        if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] < 3 or faces.size == 0:
            continue
        added = 0
        cursor = 0
        while cursor < int(faces.size):
            vc = int(faces[cursor])
            ids = [int(v) for v in faces[cursor + 1: cursor + 1 + vc]]
            cursor += vc + 1
            if vc < 3:
                continue
            for ti in range(1, vc - 1):
                tri = (ids[0], ids[ti], ids[ti + 1])
                tp = points[list(tri), :3]
                if not np.all(np.isfinite(tp)):
                    continue
                if float(np.linalg.norm(np.cross(tp[1] - tp[0], tp[2] - tp[0]))) <= 1e-12:
                    continue
                polygon = BRepBuilderAPI_MakePolygon()
                for x, y, z in tp:
                    polygon.Add(gp_Pnt(float(x), float(y), float(z)))
                polygon.Close()
                if not polygon.IsDone():
                    continue
                face = BRepBuilderAPI_MakeFace(polygon.Wire())
                if not face.IsDone():
                    continue
                builder.Add(compound, face.Face())
                added += 1
        if added:
            faceted_mesh_count += 1
            tri_count += added

    if analytic_count + tri_count <= 0:
        raise RuntimeError("No valid geometry available for STEP export")

    writer = STEPControl_Writer()
    try:
        Interface_Static.SetCVal("write.step.unit", "MM")
    except Exception:
        pass
    try:
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            writer.Transfer(compound, STEPControl_AsIs)
            status = writer.Write(str(target_path))
    except Exception:
        writer.Transfer(compound, STEPControl_AsIs)
        status = writer.Write(str(target_path))
    finally:
        for src_fd, dst_fd in ((locals().get("stdout_fd"), 1), (locals().get("stderr_fd"), 2)):
            if src_fd is None:
                continue
            try:
                os.dup2(int(src_fd), dst_fd)
                os.close(int(src_fd))
            except Exception:
                pass
    if status != IFSelect_RetDone or not target_path.exists() or target_path.stat().st_size <= 0:
        raise RuntimeError("STEP writer failed")
    return analytic_count, faceted_mesh_count, tri_count


def _write_step_with_cad_shapes_and_rays(
    system,
    rows: list,
    cad_shape_items: list[tuple[str, object]],
    ray_polylines: list[np.ndarray],
    target_path: Path,
    *,
    profile_points: int = 64,
    ray_tube_radius_mm: float | None = None,
    progress_callback=None,
) -> tuple[int, int, int]:
    """Write analytic optics, imported CAD shapes, and visible ray tubes.

    Imported CAD is preserved as native STEP BRep geometry and transformed into
    the same placement used by the UI. Rays are written as thin solid tubes
    rather than wire-only curves because FreeCAD and several mechanical viewers
    can import STEP wires without rendering them as visible objects.
    """
    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepBuilderAPI import (
            BRepBuilderAPI_Transform,
        )
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.Interface import Interface_Static
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCC.Core.TopoDS import TopoDS_Compound
        from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
    except Exception as exc:
        raise RuntimeError(f"pythonocc-core is required for STEP export: {exc}") from exc

    target_path = Path(target_path).expanduser()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)

    sdt = getattr(system, 'SDT', [])
    trans_2a = getattr(system, 'TRANS_2A', [])
    analytic_count = 0
    cad_count = 0
    ray_count = 0

    valid_ray_points: list[np.ndarray] = []
    finite_ray_points: list[np.ndarray] = []
    for points in ray_polylines:
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            continue
        finite_pts = pts[np.all(np.isfinite(pts[:, :3]), axis=1), :3]
        if finite_pts.shape[0] >= 2:
            valid_ray_points.append(pts[:, :3])
            finite_ray_points.append(finite_pts)
    if ray_tube_radius_mm is None:
        if finite_ray_points:
            all_pts = np.vstack(finite_ray_points)
            span = float(np.linalg.norm(np.ptp(all_pts, axis=0)))
            ray_tube_radius_mm = max(0.08, min(0.5, span * 0.00075))
        else:
            ray_tube_radius_mm = 0.1
    ray_tube_radius_mm = max(1e-4, float(ray_tube_radius_mm))

    n_surf = min(len(sdt), len(rows))
    if progress_callback is not None:
        progress_callback("Adding analytic optical surfaces", 1, 5)
    for j in range(n_surf):
        # bugs/0300: the Object plane (and folded Image plane) are drawn in the 3D
        # inspector, so export them too -- as flat reference discs at their traced
        # (folded) placement. The Drawing / Diameter guards below still drop hidden or
        # degenerate planes, matching the display.
        surf = sdt[j]
        if not getattr(surf, 'Drawing', 1):
            continue
        if float(getattr(surf, 'Diameter', 0)) <= 0:
            continue
        if not _is_surface_revolution_compatible(surf):
            continue
        occ_shape = _make_occ_revolution_face(surf, profile_points)
        if occ_shape is None:
            continue
        if j < len(trans_2a):
            trsf = _numpy_mat_to_occ_trsf(trans_2a[j])
            if trsf is not None:
                try:
                    occ_shape = BRepBuilderAPI_Transform(occ_shape, trsf, True).Shape()
                except Exception:
                    continue
        builder.Add(compound, occ_shape)
        analytic_count += 1

    if progress_callback is not None:
        progress_callback("Adding native STEP CAD", 2, 5)
    for _label, shape in cad_shape_items:
        if shape is None:
            continue
        try:
            if not shape.IsNull():
                builder.Add(compound, shape)
                cad_count += 1
        except Exception:
            continue

    if progress_callback is not None:
        progress_callback("Adding ray envelope tubes", 3, 5)
    for points in valid_ray_points:
        pts = np.asarray(points, dtype=float)
        added_segments = 0
        for start, end in zip(pts[:-1], pts[1:]):
            if not np.all(np.isfinite(start)) or not np.all(np.isfinite(end)):
                continue
            delta = end - start
            length = float(np.linalg.norm(delta))
            if length <= 1e-9:
                continue
            direction = delta / length
            cylinder = BRepPrimAPI_MakeCylinder(
                gp_Ax2(
                    gp_Pnt(float(start[0]), float(start[1]), float(start[2])),
                    gp_Dir(float(direction[0]), float(direction[1]), float(direction[2])),
                ),
                ray_tube_radius_mm,
                length,
            )
            try:
                ray_shape = cylinder.Shape()
            except Exception:
                continue
            try:
                if ray_shape.IsNull():
                    continue
            except Exception:
                pass
            builder.Add(compound, ray_shape)
            added_segments += 1
        if added_segments <= 0:
            continue
        ray_count += 1

    if analytic_count + cad_count + ray_count <= 0:
        raise RuntimeError("No valid geometry available for STEP export")

    writer = STEPControl_Writer()
    try:
        Interface_Static.SetCVal("write.step.unit", "MM")
    except Exception:
        pass
    if progress_callback is not None:
        progress_callback("Writing STEP file", 4, 5)
    try:
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), 1)
            os.dup2(devnull.fileno(), 2)
            writer.Transfer(compound, STEPControl_AsIs)
            status = writer.Write(str(target_path))
    except Exception:
        writer.Transfer(compound, STEPControl_AsIs)
        status = writer.Write(str(target_path))
    finally:
        for src_fd, dst_fd in ((locals().get("stdout_fd"), 1), (locals().get("stderr_fd"), 2)):
            if src_fd is None:
                continue
            try:
                os.dup2(int(src_fd), dst_fd)
                os.close(int(src_fd))
            except Exception:
                pass
    if status != IFSelect_RetDone or not target_path.exists() or target_path.stat().st_size <= 0:
        raise RuntimeError("STEP writer failed")
    if progress_callback is not None:
        progress_callback("STEP file complete", 5, 5)
    return analytic_count, cad_count, ray_count
