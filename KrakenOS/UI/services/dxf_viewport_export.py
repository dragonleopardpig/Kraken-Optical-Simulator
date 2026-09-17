"""bugs/0650: export the CURRENT 3D viewport as a DXF (R12) vector drawing.

The user's ask: "The software can now output to STEP file, can you also add output to
DXF or DWG file? Output from the current viewport." DWG is a closed binary format with
no sane in-process writer (the repo rule is in-process libs over external binaries,
bugs/tooling memory), and every CAD package converts DXF<->DWG losslessly -- so the
exporter emits DXF R12 ASCII, the most widely readable dialect (AutoCAD, FreeCAD,
LibreCAD, DraftSight, KiCad importers all accept it), written by hand with zero new
dependencies.

WHAT is exported: the scene as seen from the CURRENT camera, flattened orthographically
into the camera's view plane (view right = +X, view up = +Y), in TRUE millimetres --
distances along the view plane are real scene distances, so the drawing is dimensionable
in CAD. (With a perspective camera the flattening deliberately ignores the perspective
divide: CAD wants true lengths, not screen foreshortening.)

Layer scheme (classified through the inspector's actor registries):
  KRAKEN_RAYS      -- traced ray polylines, per-actor colour
  KRAKEN_AXES      -- optical-axis guides, DASHED linetype
  KRAKEN_BODIES    -- surface/CAD meshes as their FEATURE EDGES (silhouette-ish line
                      art via vtkFeatureEdges; triangle soup would be unusable in CAD)
  KRAKEN_MEASURES  -- measure/dimension line work
  KRAKEN_OVERLAYS  -- everything else drawn as lines (FOV plates, guides, vector text)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# The classic AutoCAD colour index (ACI) anchors we map RGB onto. 7 is the
# foreground colour (black on white / white on black -- correct for line art).
_ACI_ANCHORS: tuple[tuple[int, tuple[float, float, float]], ...] = (
    (1, (1.0, 0.0, 0.0)),      # red
    (2, (1.0, 1.0, 0.0)),      # yellow
    (3, (0.0, 1.0, 0.0)),      # green
    (4, (0.0, 1.0, 1.0)),      # cyan
    (5, (0.0, 0.0, 1.0)),      # blue
    (6, (1.0, 0.0, 1.0)),      # magenta
    (7, (1.0, 1.0, 1.0)),      # white/black foreground
    (8, (0.5, 0.5, 0.5)),      # grey
    (30, (1.0, 0.5, 0.0)),     # orange
    (94, (0.0, 0.5, 0.25)),    # dark green
)


def nearest_aci(rgb) -> int:
    """Nearest AutoCAD colour index for an RGB triple in [0, 1]."""
    try:
        c = np.asarray(rgb, dtype=float).reshape(-1)[:3]
    except Exception:
        return 7
    if c.size < 3 or not np.all(np.isfinite(c)):
        return 7
    best, best_d = 7, float("inf")
    for aci, anchor in _ACI_ANCHORS:
        d = float(np.sum((c - np.asarray(anchor)) ** 2))
        if d < best_d:
            best, best_d = aci, d
    return best


def view_projection_matrix(camera) -> np.ndarray:
    """The camera's 4x4 world->view transform (rotation + translation, no divide)."""
    m = camera.GetViewTransformMatrix()
    out = np.empty((4, 4), dtype=float)
    for i in range(4):
        for j in range(4):
            out[i, j] = float(m.GetElement(i, j))
    return out


def project_points(points, view_matrix, actor_matrix=None) -> np.ndarray:
    """World (or actor-local) Nx3 points -> Nx2 view-plane coordinates in mm."""
    pts = np.asarray(points, dtype=float).reshape(-1, 3)
    homog = np.hstack([pts, np.ones((pts.shape[0], 1))])
    if actor_matrix is not None:
        homog = homog @ np.asarray(actor_matrix, dtype=float).T
    view = homog @ np.asarray(view_matrix, dtype=float).T
    return view[:, :2]


def _vtk_matrix_to_numpy(m) -> np.ndarray | None:
    try:
        out = np.empty((4, 4), dtype=float)
        for i in range(4):
            for j in range(4):
                out[i, j] = float(m.GetElement(i, j))
        if np.allclose(out, np.eye(4)):
            return None
        return out
    except Exception:
        return None


def polydata_line_strips(polydata) -> list[np.ndarray]:
    """Decode a vtkPolyData's LINES into world-point strips (each Nx3)."""
    strips: list[np.ndarray] = []
    try:
        from vtkmodules.util.numpy_support import vtk_to_numpy

        n_pts = int(polydata.GetNumberOfPoints())
        if n_pts == 0:
            return strips
        points = vtk_to_numpy(polydata.GetPoints().GetData()).astype(float).reshape(-1, 3)
        lines = polydata.GetLines()
        if lines is None or lines.GetNumberOfCells() == 0:
            return strips
        flat = vtk_to_numpy(lines.GetData()).astype(np.int64)
    except Exception:
        return strips
    i = 0
    while i < flat.size:
        count = int(flat[i])
        idx = flat[i + 1 : i + 1 + count]
        i += 1 + count
        if count >= 2 and np.all(idx < points.shape[0]):
            strips.append(points[idx])
    return strips


_SILHOUETTE_TILTS = (0.0, 0.01, -0.01)


def _strips_not_already_drawn(
    candidates: list[np.ndarray],
    reference: list[np.ndarray],
    *,
    relative_tol: float = 5e-4,
) -> list[np.ndarray]:
    """bugs/0798: keep only candidate strips the reference pass did NOT already draw.

    Used to union the perturbed silhouettes onto the base one without triplicating every
    contour. A candidate is dropped when every one of its points lies within the tolerance
    of some reference point -- i.e. it retraces a line already present, a few hundredths of
    a millimetre away. The tolerance is RELATIVE to the reference drawing's own extent
    (default 0.05%), so it scales with the view instead of assuming millimetres.
    """
    if not candidates:
        return []
    if not reference:
        return list(candidates)
    try:
        from scipy.spatial import cKDTree
    except Exception:
        return list(candidates)
    def _as_points(strip):
        arr = np.asarray(strip, dtype=float)
        return arr.reshape(-1, arr.shape[-1]) if arr.ndim >= 2 else arr.reshape(-1, 1)

    try:
        ref_runs = [_as_points(s) for s in reference if len(np.asarray(s)) >= 2]
        ref_points = np.vstack(ref_runs)
    except Exception:
        return list(candidates)
    if len(ref_points) == 0:
        return list(candidates)
    span = float(np.max(np.ptp(ref_points, axis=0))) if len(ref_points) > 1 else 0.0
    tol = max(span * float(relative_tol), 1e-9)

    # bugs/0799: the reference may be a SPARSE ring (a union outline is a handful of long
    # edges), so a candidate lying exactly on it can still be half a segment from the
    # nearest reference VERTEX. Sample the reference at the tolerance before testing.
    sampled = [ref_points]
    for run in ref_runs:
        if len(run) < 2:
            continue
        deltas = np.diff(run, axis=0)
        lengths = np.linalg.norm(deltas, axis=1)
        for start, delta, length in zip(run[:-1], deltas, lengths):
            steps = int(length / tol) if tol > 0.0 else 0
            if steps > 1:
                steps = min(steps, 4096)
                fractions = np.linspace(0.0, 1.0, steps, endpoint=False)[1:, None]
                sampled.append(start + fractions * delta)
    ref_points = np.vstack(sampled)

    tree = cKDTree(ref_points)
    kept: list[np.ndarray] = []
    for strip in candidates:
        pts = _as_points(strip)
        if len(pts) < 2 or pts.shape[1] != ref_points.shape[1]:
            kept.append(strip)
            continue
        distances, _ = tree.query(pts)
        if float(np.max(distances)) > tol:
            kept.append(strip)
    return kept


def mesh_outline_strips(
    polydata,
    view_direction=None,
    actor_matrix=None,
    feature_angle: float = 35.0,
    max_polys: int = 400_000,
) -> list[np.ndarray]:
    """A mesh's CAD-drawing line art: view-direction SILHOUETTES + feature/boundary edges.

    bugs/0650 rework (user: "the output lens only have horizontal lines, missing those
    vertical and slanted lines of the housing"): a turned housing's slanted/vertical
    profile in a side view is its SILHOUETTE -- view-dependent contour edges where the
    facets flip facing -- which vtkFeatureEdges (view-independent creases only) can never
    produce. vtkPolyDataSilhouette with the export's own orthographic view direction
    supplies them; feature+boundary edges still add the rims and creases. The mesh's own
    stray LINE cells (tessellation artifacts on CAD display meshes) are deliberately NOT
    exported -- they were the 60k-segment horizontal soup in the user's file.

    ``actor_matrix`` (4x4 numpy or None): applied to the points FIRST so the silhouette
    is computed in world space with the world-space view direction."""
    try:
        n_polys = int(polydata.GetNumberOfPolys())
        if n_polys == 0 or n_polys > int(max_polys):
            return []
        import vtk

        source = polydata
        if actor_matrix is not None:
            m = vtk.vtkMatrix4x4()
            for i in range(4):
                for j in range(4):
                    m.SetElement(i, j, float(actor_matrix[i][j]))
            transform = vtk.vtkTransform()
            transform.SetMatrix(m)
            tf = vtk.vtkTransformPolyDataFilter()
            tf.SetTransform(transform)
            tf.SetInputData(polydata)
            tf.Update()
            source = tf.GetOutput()

        strips: list[np.ndarray] = []
        if view_direction is not None:
            # bugs/0650 round 6 (the user's freecad.png: right-side profile steps
            # missing, left side present -- "compare the symmetry from the center
            # line"): the silhouette test (adjacent facets flipping facing) is a
            # knife-edge at tangency, and OCC tessellation is not mirror-symmetric,
            # so contour edges on one side of a body of revolution can fall exactly
            # on the threshold and vanish while their mirror twins survive. UNION the
            # silhouettes of three slightly perturbed view directions (+-~0.6 deg);
            # the fragment dedupe absorbs the overlap, and edges lost at one
            # direction's threshold are caught by the neighbours.
            base = np.asarray(view_direction, dtype=float).reshape(3)
            norm = float(np.linalg.norm(base)) or 1.0
            base = base / norm
            ortho = np.cross(base, [0.0, 0.0, 1.0])
            if float(np.linalg.norm(ortho)) < 1e-6:
                ortho = np.cross(base, [0.0, 1.0, 0.0])
            ortho = ortho / (float(np.linalg.norm(ortho)) or 1.0)
            # bugs/0798 (user: "many unclosed edges, they are supposed to be closed
            # shape"): the three passes must not TRIPLICATE the contour. Each tilt puts
            # the silhouette on DIFFERENT mesh edges, so the copies land ~0.1 mm apart --
            # measured on the user's own scene, raw strips totalled 129386 mm of line for
            # 46156 mm of unique geometry, and every corner then existed three times in
            # three slightly different places. merge_collinear_segments_2d collapsed the
            # duplicate LENGTH correctly but had to choose between copies at each corner,
            # and chose inconsistently, so the two arms of a corner ended on different
            # copies and no longer met: 2854 joinable endpoints in the raw segments
            # survived as 13, the box outlines came apart, and the stitched chains were
            # left a median 1.38 mm from closing.
            #
            # The perturbations exist to catch contour edges LOST at one direction's
            # tangency threshold (round 6), and a lost edge is one the base pass does not
            # draw AT ALL. So the base silhouette is canonical -- its connectivity is
            # preserved untouched -- and a perturbed fragment is kept only where the base
            # drew nothing near it.
            base_strips: list[np.ndarray] = []
            extra_strips: list[np.ndarray] = []
            for tilt in _SILHOUETTE_TILTS:
                direction = base + tilt * ortho
                direction = direction / (float(np.linalg.norm(direction)) or 1.0)
                sil = vtk.vtkPolyDataSilhouette()
                sil.SetInputData(source)
                sil.SetDirectionToSpecifiedVector()
                sil.SetVector(*(float(v) for v in direction))
                sil.SetEnableFeatureAngle(0)
                sil.BorderEdgesOn()
                sil.Update()
                got = polydata_line_strips(sil.GetOutput())
                (base_strips if not base_strips else extra_strips).extend(got)
            strips.extend(base_strips)
            strips.extend(_strips_not_already_drawn(extra_strips, base_strips))

        fe = vtk.vtkFeatureEdges()
        fe.SetInputData(source)
        fe.BoundaryEdgesOn()
        fe.FeatureEdgesOn()
        fe.SetFeatureAngle(float(feature_angle))
        fe.ManifoldEdgesOff()
        fe.NonManifoldEdgesOn()
        fe.ColoringOff()
        fe.Update()
        strips.extend(polydata_line_strips(fe.GetOutput()))
        return strips
    except Exception:
        return []


class _SceneDepthBuffer:
    """bugs/0802: an orthographic z-buffer of every solid in the view, for hidden-line removal.

    Without it the DXF is a SEE-THROUGH wireframe: every edge of every body is projected,
    front and back. Measured on the user's scene -- 67.5% of the lens body's feature edges and
    **94.2%** of the camera's are occluded by their own body, which is the "camera is also
    quite messy" thicket, and the back-facing ones surfacing inside the lens taper are the
    "stray lines" that no 2D rule could separate from genuine front detail. The discriminator
    is DEPTH, so measure depth.

    Rasterises triangles into a fixed grid once per export; testing a point is then a lookup.
    Cost on that scene: 0.32 s for 11272 triangles, 5.5 s for 231606.
    """

    def __init__(self, view_direction, resolution: int = 1400, tile_min_triangles: int = 1000):
        view = np.asarray(view_direction, dtype=float).reshape(3)
        self.view = view / (float(np.linalg.norm(view)) or 1.0)
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(up, self.view))) > 0.9:
            up = np.array([0.0, 1.0, 0.0])
        self.e0 = np.cross(up, self.view)
        self.e0 = self.e0 / (float(np.linalg.norm(self.e0)) or 1.0)
        self.e1 = np.cross(self.view, self.e0)
        self.resolution = int(resolution)
        self.tile_min_triangles = int(tile_min_triangles)
        self._grids: list[tuple] = []   # per-part tiles: (lo, hi, span, buffer, front, scale)
        self._tris: list[tuple[np.ndarray, np.ndarray]] = []
        self.buffer = None
        self._front = None
        self._origin = None
        self._scale = 1.0
        self._depth_span = 1.0

    def to_plane(self, points) -> np.ndarray:
        a = np.asarray(points, dtype=float).reshape(-1, 3)
        return np.column_stack([a @ self.e0, a @ self.e1])

    def depth_of(self, points) -> np.ndarray:
        a = np.asarray(points, dtype=float).reshape(-1, 3)
        return -(a @ self.view)          # larger = nearer the viewer

    def add_mesh(self, polydata, actor_matrix=None) -> None:
        try:
            import pyvista as pv

            mesh = pv.wrap(polydata)
            points = np.asarray(mesh.points, dtype=float)
            if actor_matrix is not None:
                m = np.asarray(actor_matrix, dtype=float)
                points = (np.hstack([points, np.ones((len(points), 1))]) @ m.T)[:, :3]
            faces = np.asarray(mesh.faces, dtype=np.int64)
            if points.size == 0 or faces.size == 0:
                return
            tris, i = [], 0
            while i < len(faces):
                count = int(faces[i])
                if count == 3:
                    tris.append(faces[i + 1:i + 4])
                i += count + 1
            if not tris:
                return
            self._tris.append((points, np.asarray(tris, dtype=np.int64)))
            self.buffer = None
        except Exception:
            return

    def _rasterise(self, lo, span, meshes):
        """Fill one res x res depth window starting at ``lo`` and ``span`` wide."""
        res = self.resolution
        scale = (res - 1) / span
        buffer = np.full((res, res), -np.inf, dtype=np.float64)
        for points, tris in meshes:
            plane = (self.to_plane(points) - lo) * scale
            depth = self.depth_of(points)
            corners = plane[tris]
            zs = depth[tris]
            cx0, cx1 = corners[:, :, 0].min(axis=1), corners[:, :, 0].max(axis=1)
            cy0, cy1 = corners[:, :, 1].min(axis=1), corners[:, :, 1].max(axis=1)
            keep = (cx1 >= 0) & (cx0 <= res - 1) & (cy1 >= 0) & (cy0 <= res - 1)
            corners, zs = corners[keep], zs[keep]
            if len(corners) == 0:
                continue
            xmin = np.clip(np.floor(corners[:, :, 0].min(axis=1)).astype(int), 0, res - 1)
            xmax = np.clip(np.ceil(corners[:, :, 0].max(axis=1)).astype(int), 0, res - 1)
            ymin = np.clip(np.floor(corners[:, :, 1].min(axis=1)).astype(int), 0, res - 1)
            ymax = np.clip(np.ceil(corners[:, :, 1].max(axis=1)).astype(int), 0, res - 1)
            for k in range(len(corners)):
                x0, x1, y0, y1 = xmin[k], xmax[k], ymin[k], ymax[k]
                if x1 < x0 or y1 < y0:
                    continue
                gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
                a, b, c = corners[k]
                det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                if abs(det) < 1e-12:
                    continue
                l1 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / det
                l2 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / det
                l3 = 1.0 - l1 - l2
                inside = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
                if not inside.any():
                    continue
                z = l1 * zs[k][0] + l2 * zs[k][1] + l3 * zs[k][2]
                view = buffer[y0:y1 + 1, x0:x1 + 1]
                np.maximum(view, np.where(inside, z, -np.inf), out=view)
        # CONSERVATIVE test surface: the FARTHEST front depth in each 3x3 neighbourhood. A line
        # lying ON a rim or silhouette samples pixels the adjacent, slightly nearer triangle
        # covers, and against the raw buffer it flickered hidden/visible at pixel pitch --
        # closed hole rims came apart into dotted runs and flange edges turned dashed (six-view
        # 1880 -> 6219 polylines). A line genuinely BEHIND a face still fails, because that
        # face covers the whole neighbourhood.
        try:
            from scipy.ndimage import minimum_filter

            front = minimum_filter(buffer, size=3, mode="nearest")
        except Exception:
            front = buffer
        return buffer, front, scale

    def _build(self) -> None:
        if not self._tris:
            return
        planes = [self.to_plane(p) for p, _t in self._tris]
        uv = np.vstack(planes)
        lo, hi = uv.min(axis=0), uv.max(axis=0)
        span = float((hi - lo).max()) * 1.002
        if span <= 0.0:
            return
        depths = np.concatenate([self.depth_of(p) for p, _t in self._tris])
        self._depth_span = max(float(depths.max() - depths.min()), 1e-9)
        self.buffer, self._front, self._scale = self._rasterise(lo, span, self._tris)
        self._origin = lo
        # bugs/0803: one grid for the whole view is too coarse for the parts that matter.
        # Measured on the user's viewport export -- 263 mm of scene at 1400 px is 188 um per
        # pixel, so the camera's 53 mm spanned 284 px where the six-view sheet gives it 1396.
        # A detailed body that is meaningfully smaller than the scene gets its OWN full-
        # resolution tile, rasterising every solid that overlaps it (so the lens still hides the
        # camera). Strips spanning several bodies keep using the global grid.
        self._grids = []
        for (points, tris), plane in zip(self._tris, planes):
            if len(tris) < self.tile_min_triangles:
                continue
            m_lo, m_hi = plane.min(axis=0), plane.max(axis=0)
            m_span = float((m_hi - m_lo).max())
            if m_span <= 0.0 or m_span >= 0.8 * span:
                continue
            pad = 0.02 * m_span
            t_lo = m_lo - pad
            t_span = m_span + 2.0 * pad
            t_hi = t_lo + t_span
            overlapping = [
                mesh for mesh, other in zip(self._tris, planes)
                if bool((other.max(axis=0) >= t_lo).all() and (other.min(axis=0) <= t_hi).all())
            ]
            buffer, front, scale = self._rasterise(t_lo, t_span, overlapping)
            self._grids.append((t_lo, t_hi, t_span, buffer, front, scale))

    def _grid_for(self, plane_points):
        """The finest tile that fully contains these projected points, else the global grid."""
        s_lo, s_hi = plane_points.min(axis=0), plane_points.max(axis=0)
        best = None
        for grid in self._grids:
            t_lo, t_hi, t_span = grid[0], grid[1], grid[2]
            if bool((s_lo >= t_lo).all() and (s_hi <= t_hi).all()):
                if best is None or t_span < best[2]:
                    best = grid
        if best is None:
            # The global grid is full resolution only when the view needed no tiles (a
            # single-part sheet); otherwise it is the coarse fallback for strips that span
            # several bodies.
            return self._origin, self.buffer, self._front, self._scale, not self._grids
        return best[0], best[3], best[4], best[5], True

    def visible_runs(self, strip, tolerance_fraction: float = 2e-3) -> list[np.ndarray]:
        """Split a world-space strip into the runs that are NOT hidden behind a solid."""
        if self.buffer is None:
            self._build()
        if self.buffer is None:
            return [np.asarray(strip, dtype=float)]
        points = np.asarray(strip, dtype=float).reshape(-1, 3)
        if len(points) < 2:
            return []
        # Test ALONG each segment, not just at its vertices: a merged straight edge is often
        # one long 2-point segment, and with both ends visible its middle can still pass
        # behind a body. Sample at the buffer's own pixel pitch -- finer cannot be resolved.
        origin, grid_buffer, grid_front, grid_scale, full_resolution = self._grid_for(
            self.to_plane(points)
        )
        pitch = 1.0 / max(float(grid_scale), 1e-12)
        original = points
        samples = [points[:1]]
        vertex_at = [0]              # sample index -> original vertex index, or -1
        for k, (start, end) in enumerate(zip(points[:-1], points[1:])):
            length = float(np.linalg.norm(end - start))
            steps = min(max(int(np.ceil(length / pitch)), 1), 4096)
            fractions = np.linspace(0.0, 1.0, steps + 1)[1:, None]
            chunk = start + fractions * (end - start)
            chunk[-1] = end          # the segment's end IS the next vertex, exactly
            samples.append(chunk)
            vertex_at.extend([-1] * (steps - 1) + [k + 1])
        points = np.vstack(samples)
        vertex_at = np.asarray(vertex_at)
        plane = self.to_plane(points)
        depth = self.depth_of(points)
        res = self.resolution
        px = np.rint((plane - origin) * grid_scale).astype(int)
        # Outside the rasterised extent NOTHING is in front. Clipping such a sample to the
        # border pixel made it inherit that pixel's depth -- a line leaving one side of a body
        # read as hidden all the way out, and the guard's crossing strip came back as one run.
        in_grid = (px[:, 0] >= 0) & (px[:, 0] < res) & (px[:, 1] >= 0) & (px[:, 1] < res)
        surface = grid_front if grid_front is not None else grid_buffer
        front = np.full(len(points), -np.inf)
        front[in_grid] = surface[px[in_grid, 1], px[in_grid, 0]]
        tol = self._depth_span * float(tolerance_fraction)
        visible = (depth >= front - tol) | ~np.isfinite(front)
        # Close hidden gaps of a couple of samples inside a visible line: at the pixel pitch
        # they are rasterisation noise, not occlusion, and left open they cut a continuous
        # edge into dashes.
        if visible.any() and not visible.all():
            max_gap = 2
            index = 0
            n = len(visible)
            while index < n:
                if visible[index]:
                    index += 1
                    continue
                end = index
                while end < n and not visible[end]:
                    end += 1
                if index > 0 and end < n and (end - index) <= max_gap:
                    visible[index:end] = True
                index = end
        # Emit ORIGINAL vertices, not the samples. The samples exist only to decide visibility;
        # returned as geometry they broke everything downstream -- the silhouette copy and the
        # feature copy of one edge used to share identical vertices, so the exact dedupe
        # removed one and the stitcher chained the rest, but resampled at different offsets
        # they stopped matching and every hole rim came out as two interleaved dotted copies
        # (camera six-view 1880 -> 3900 polylines, while the depth test itself cut almost
        # nothing: at most 6 runs per small strip across all six views).
        if visible.all():
            return [original]
        spans: list[tuple[int, int]] = []
        start = None
        for index, flag in enumerate(visible):
            if flag and start is None:
                start = index
            elif not flag and start is not None:
                if index - start >= 2:
                    spans.append((start, index - 1))
                start = None
        if start is not None and len(points) - start >= 2:
            spans.append((start, len(points) - 1))
        runs: list[np.ndarray] = []
        # A piece the depth test CUT that is shorter than three pixels of the grid that cut it
        # is below that test's resolution -- rasterisation noise, not a visibility decision.
        # Measured on the camera six-view: sampling along segments is what recovered 21 real
        # lines over 5 mm, and also what left ~1100 sub-0.5 mm end pieces around hole rims.
        # This was tried once and reverted while the viewport ran on a single 188 um grid (3 px
        # was 0.56 mm there and cost real lines); on per-part tiles it is 40-110 um.
        # Only in a SINGLE-PART view (no tiles were needed). There, a cut is the part hiding
        # itself at a hole rim and the short end pieces are noise -- the camera six-view lost
        # 722 sub-0.5 mm specks while lines over 5 mm went UP, 227 -> 232. In a multi-body
        # view a cut can be a line emerging from behind ANOTHER body, where a short visible
        # piece is real: applied to the viewport, even restricted to its fine tiles, the rule
        # cost 130 -> 127 lines over 5 mm by opening gaps in them. Measured on one scene; the
        # distinction is stated as observed, not as a law.
        min_length = 3.0 * pitch if (full_resolution and not self._grids) else 0.0
        for first, last in spans:
            interior = [
                original[int(vertex_at[i])]
                for i in range(first + 1, last)
                if vertex_at[i] >= 0
            ]
            run = np.vstack([points[first:first + 1], *[v[None, :] for v in interior],
                             points[last:last + 1]]) if interior else points[[first, last]]
            if float(np.sum(np.linalg.norm(np.diff(run, axis=0), axis=1))) < min_length:
                continue
            runs.append(run)
        return runs


def mesh_outline_polygons(
    polydata,
    view_direction,
    actor_matrix=None,
    *,
    simplify_tol: float = 0.02,
    max_polys: int = 400_000,
) -> list[np.ndarray]:
    """bugs/0799: the body's projected outline as CLOSED rings, computed not assembled.

    bugs/0798 left the drawing with no closed shapes at all: the line art is a soup of
    silhouette and feature edges, and a greedy endpoint walk over it cannot decide which
    of several incident edges continues a profile -- measured, the stitched chains ended a
    median 1.38 mm apart, and merging them first only fragmented the graph further
    (416 segments -> 120 chains) while stitching first walked every duplicate into two
    giant scribbles covering 129386 mm of line for 46156 mm of unique geometry.

    A silhouette does not have to be assembled from edges. Project every triangle into the
    view plane and take the BOOLEAN UNION: its boundary IS the outline, closed by
    construction, with one exterior ring per connected body and one interior ring per
    through-hole. Measured on this scene's own meshes: 11272 triangles -> 1 closed ring of
    117 vertices in 0.20 s, and 231606 -> 1 closed ring of 64 vertices in 4.47 s.

    Returns world-space rings (the 2D result lifted back along the view direction at the
    mesh's own depth), so the caller projects them exactly like every other strip. The
    first vertex is repeated as the last, which is how the writer recognises a closed
    polyline.
    """
    try:
        n_polys = int(polydata.GetNumberOfPolys())
        if n_polys == 0 or n_polys > int(max_polys):
            return []
        import shapely

        import pyvista as pv

        mesh = pv.wrap(polydata)
        points = np.asarray(mesh.points, dtype=float)
        if actor_matrix is not None:
            m = np.asarray(actor_matrix, dtype=float)
            points = (np.hstack([points, np.ones((len(points), 1))]) @ m.T)[:, :3]
        faces = np.asarray(mesh.faces, dtype=np.int64)
        if points.size == 0 or faces.size == 0:
            return []

        view = np.asarray(view_direction, dtype=float).reshape(3)
        view = view / (float(np.linalg.norm(view)) or 1.0)
        up = np.array([0.0, 0.0, 1.0])
        if abs(float(np.dot(up, view))) > 0.9:
            up = np.array([0.0, 1.0, 0.0])
        e0 = np.cross(up, view)
        e0 = e0 / (float(np.linalg.norm(e0)) or 1.0)
        e1 = np.cross(view, e0)
        uv = np.column_stack([points @ e0, points @ e1])
        depth = float(np.mean(points @ view))

        tris = []
        i = 0
        while i < len(faces):
            count = int(faces[i])
            if count == 3:
                tris.append(faces[i + 1:i + 4])
            i += count + 1
        if not tris:
            return []
        corners = uv[np.asarray(tris, dtype=np.int64)]
        # Drop edge-on triangles: they carry no area in this view and only slow the union.
        area = 0.5 * np.abs(
            (corners[:, 1, 0] - corners[:, 0, 0]) * (corners[:, 2, 1] - corners[:, 0, 1])
            - (corners[:, 2, 0] - corners[:, 0, 0]) * (corners[:, 1, 1] - corners[:, 0, 1])
        )
        corners = corners[area > 1e-12]
        if len(corners) == 0:
            return []
        merged = shapely.union_all(
            shapely.polygons(np.concatenate([corners, corners[:, :1, :]], axis=1))
        )
        rings: list[np.ndarray] = []
        for geom in getattr(merged, "geoms", [merged]):
            exterior = getattr(geom, "exterior", None)
            if exterior is None:
                continue
            rings.append(np.asarray(exterior.coords, dtype=float))
            rings.extend(np.asarray(r.coords, dtype=float) for r in geom.interiors)
        out: list[np.ndarray] = []
        for ring in rings:
            if len(ring) < 4:
                continue
            if simplify_tol > 0.0:
                try:
                    ring = np.asarray(
                        shapely.simplify(shapely.linearrings(ring), simplify_tol).coords,
                        dtype=float,
                    )
                except Exception:
                    pass
            if len(ring) < 4:
                continue
            # bugs/0804: a ring that encloses no area is not a shape. Seen from the side, the
            # tapered flank's triangles are nearly edge-on, and simplifying their union at
            # simplify_tol collapses thin slivers into collinear points -- 18 of the 21 rings on
            # the user's -yz export enclosed EXACTLY zero area. Being closed, they bypassed both
            # hidden-line removal and post-processing and drew as the stray lines in the taper.
            # Cut at the precision the ring was simplified to: mean width 2A/P below that
            # tolerance is below what this outline can resolve.
            closed_ring = ring if np.allclose(ring[0], ring[-1]) else np.vstack([ring, ring[:1]])
            area = abs(float(np.sum(closed_ring[:-1, 0] * closed_ring[1:, 1]
                                    - closed_ring[1:, 0] * closed_ring[:-1, 1]))) / 2.0
            perimeter = float(np.sum(np.linalg.norm(np.diff(closed_ring, axis=0), axis=1)))
            if perimeter <= 0.0 or 2.0 * area / perimeter < max(float(simplify_tol), 1e-9):
                continue
            out.append(ring[:, 0:1] * e0 + ring[:, 1:2] * e1 + depth * view)
        return out
    except Exception:
        return []


def stitch_strips_2d(strips: list[np.ndarray], tol: float = 1e-3) -> list[np.ndarray]:
    """Chain 2D strips that share endpoints into maximal polylines.

    bugs/0650 (user: "many lines where each of them are assembled of many short line
    segments ... a line should be one vector line"): vtkFeatureEdges and
    vtkPolyDataSilhouette emit every edge as its OWN 2-point cell, so a single straight
    housing line arrived as N separate DXF polylines. Greedy endpoint chaining on a
    quantised-endpoint index rebuilds the connected lines."""
    if not strips:
        return []
    def q(p):
        return (round(float(p[0]) / tol), round(float(p[1]) / tol))

    pool = [np.asarray(s, dtype=float).reshape(-1, 2) for s in strips if len(s) >= 2]
    index: dict[tuple[int, int], list[int]] = {}
    for i, s in enumerate(pool):
        index.setdefault(q(s[0]), []).append(i)
        index.setdefault(q(s[-1]), []).append(i)

    def candidates(tip):
        # bugs/0650 (user: "boxes not closed, missing lines at one side, not symmetry"):
        # a single-bin lookup loses joins whose endpoints straddle a quantisation bin
        # edge -- a floating-point lottery that broke chains asymmetrically. Check the
        # 3x3 bin neighbourhood.
        bx, by = q(tip)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in index.get((bx + dx, by + dy), []):
                    yield j

    used = [False] * len(pool)
    out: list[np.ndarray] = []
    for i in range(len(pool)):
        if used[i]:
            continue
        used[i] = True
        chain = list(pool[i])
        for end in (True, False):  # grow forward from the tail, then from the head
            while True:
                tip = chain[-1] if end else chain[0]
                found = None
                for j in candidates(tip):
                    if used[j]:
                        continue
                    s = pool[j]
                    if np.linalg.norm(s[0] - tip) <= tol:
                        found, seg = j, s
                    elif np.linalg.norm(s[-1] - tip) <= tol:
                        found, seg = j, s[::-1]
                    else:
                        continue
                    break
                if found is None:
                    break
                used[found] = True
                if end:
                    chain.extend(list(seg[1:]))
                else:
                    # ``seg`` is oriented to START at the tip (the tail-growth
                    # convention); a head join must prepend it REVERSED -- ending at
                    # the tip -- or the far endpoint is dropped and the tip
                    # duplicated (bugs/0650 round 8: every head-side join silently
                    # ate one endpoint).
                    chain[0:0] = list(seg[::-1][:-1])
        out.append(np.asarray(chain, dtype=float))
    return out


def simplify_polyline_2d(points: np.ndarray, epsilon: float = 0.02) -> np.ndarray:
    """Ramer-Douglas-Peucker: collinear runs collapse to single vectors; real bends
    (ray kinks at surfaces, silhouette curvature) survive within ``epsilon`` mm."""
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if pts.shape[0] <= 2:
        return pts
    keep = np.zeros(pts.shape[0], dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, pts.shape[0] - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        seg = pts[b] - pts[a]
        length = float(np.hypot(*seg))
        if length <= 1e-12:
            d = np.linalg.norm(pts[a + 1 : b] - pts[a], axis=1)
        else:
            d = np.abs(np.cross(seg / length, pts[a + 1 : b] - pts[a]))
        idx = int(np.argmax(d))
        if float(d[idx]) > float(epsilon):
            mid = a + 1 + idx
            keep[mid] = True
            stack.append((a, mid))
            stack.append((mid, b))
    return pts[keep]


def _finite_runs(points: np.ndarray) -> list[np.ndarray]:
    """Split a polyline at non-finite points instead of dropping it whole.

    bugs/0650 (missing box sides): after stitching, one bad vertex (a degenerate CAD
    point projecting to NaN/inf) used to kill the ENTIRE chained line at the writer's
    finite gate -- a whole housing side vanished because one fragment in its chain was
    poisoned. Splitting keeps every healthy run."""
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    good = np.all(np.isfinite(pts), axis=1)
    runs: list[np.ndarray] = []
    start = None
    for i, g in enumerate(good):
        if g and start is None:
            start = i
        elif not g and start is not None:
            if i - start >= 2:
                runs.append(pts[start:i])
            start = None
    if start is not None and len(pts) - start >= 2:
        runs.append(pts[start:])
    return runs


def merge_collinear_segments_2d(
    segments: list[np.ndarray],
    angle_tol: float = 2e-4,
    perp_tol: float = 0.03,
    gap_tol: float = 0.05,
) -> list[np.ndarray]:
    """Merge straight 2-point fragments that lie on the SAME line and overlap or
    touch into one maximal segment (bugs/0650 round 7).

    A housing edge reaches the export twice -- once from the silhouette pass, once
    from the STEP body's companion edge actor -- and each copy is cut wherever a
    neighbouring feature touches it, so the camera's bottom edge arrived as nine
    overlapping pieces. Endpoint stitching cannot see overlap.

    Round 8 (user: "exported DXF still have broken lines here and there"): the round-7
    single sort by (angle, offset) broke on real geometry -- near-vertical edges carry
    tiny tessellation angle jitter, so segments of OTHER offsets interleave between
    same-line members and the consecutive sweep splits the group (95 overlaps survived
    on the user's own export); and the directed-angle canonical form wraps at +-pi/2,
    splitting one vertical line's members to both ends of the sort. Now: cluster the
    UNDIRECTED angle (mod pi, with an explicit wrap merge of the first/last cluster),
    re-project every cluster member on ONE reference direction, then cluster by offset
    and union the parameter intervals.

    bugs/0798 (user: "many unclosed edges, they are supposed to be closed shape"): the
    union emits REAL endpoints, never re-projected ones. Rounds 7-8 rebuilt every output
    as ``d * t + normal * mean_offset``, i.e. on the cluster's reference direction at the
    group's MEAN offset -- so a segment was moved by up to perp_tol/2 even when it had
    nothing to merge with, and the two arms of a corner, being in different angle
    clusters, were each moved independently. Measured on two arms meeting EXACTLY at
    (50, 0): they came out ending at (50, 0.0125) and (50.0125, 0), a 0.0177 mm gap that
    ``stitch_strips_2d`` (tol 1e-3) can never close -- which is why the user's export
    carried 3206 loose 2-point fragments, 90% of body polylines with a dangling end and
    a median nearest-endpoint gap of 0.0156 mm. Unioning the intervals is the point of
    this function; moving the endpoints was never part of it.
    """
    if not segments:
        return []
    rows = []
    for seg in segments:
        a = np.asarray(seg[0], dtype=float)
        b = np.asarray(seg[-1], dtype=float)
        d = b - a
        length = float(np.hypot(d[0], d[1]))
        if length < 1e-6:
            continue
        phi = float(np.arctan2(d[1], d[0])) % np.pi  # undirected line angle in [0, pi)
        rows.append((phi, a, b))
    if not rows:
        return []
    rows.sort(key=lambda r: r[0])
    # Angle clusters: consecutive sweep over the sorted undirected angles ...
    clusters: list[list[tuple]] = [[rows[0]]]
    for row in rows[1:]:
        if row[0] - clusters[-1][-1][0] <= angle_tol:
            clusters[-1].append(row)
        else:
            clusters.append([row])
    # ... with the 0/pi wrap: a horizontal edge jittering either side of 0 lands in
    # both end clusters; they are the same undirected direction.
    if len(clusters) > 1 and (clusters[0][0][0] + np.pi) - clusters[-1][-1][0] <= angle_tol:
        clusters[0] = clusters.pop() + clusters[0]
    out: list[np.ndarray] = []
    for cluster in clusters:
        d = np.array([np.cos(cluster[0][0]), np.sin(cluster[0][0])])
        normal = np.array([-d[1], d[0]])
        members = []
        for _, a, b in cluster:
            t0, t1 = float(np.dot(d, a)), float(np.dot(d, b))
            offset = 0.5 * (float(np.dot(normal, a)) + float(np.dot(normal, b)))
            # bugs/0798: carry each member's REAL endpoints, ordered along the reference
            # direction, so a merged run can be emitted from points that actually exist.
            lo, hi = (a, b) if t0 <= t1 else (b, a)
            members.append((offset, min(t0, t1), max(t0, t1), lo, hi))
        members.sort(key=lambda m: (m[0], m[1]))
        i = 0
        while i < len(members):
            j = i + 1
            while j < len(members) and members[j][0] - members[j - 1][0] <= perp_tol:
                j += 1
            group = sorted(members[i:j], key=lambda m: m[1])
            cur_t1 = group[0][2]
            cur_p0, cur_p1 = group[0][3], group[0][4]
            for _offset, t0, t1, p_lo, p_hi in group[1:]:
                if t0 <= cur_t1 + gap_tol:
                    if t1 > cur_t1:
                        cur_t1, cur_p1 = t1, p_hi
                else:
                    out.append(np.array([cur_p0, cur_p1]))
                    cur_t1, cur_p0, cur_p1 = t1, p_lo, p_hi
            out.append(np.array([cur_p0, cur_p1]))
            i = j
    return out


def _postprocess_layer_polylines(
    polylines: list[dict], epsilon: float = 0.02, decompose: bool = False
) -> list[dict]:
    """Per colour bucket: split at bad points, stitch fragments, simplify, dedupe.

    ``decompose`` (bugs/0650 round 8, body layers): break every chain into its
    individual segments FIRST so chain-carried collinear pieces join the overlap
    merge too -- a stitched-then-simplified chain is straight-line geometry just like
    a raw fragment, and on the user's export such pieces kept doubling edges the
    round-7 merge never saw. Rays keep their chains (two rays sharing a line are
    still two rays).
    """
    by_color: dict[object, list[np.ndarray]] = {}
    frag_seen: set = set()
    closed_rings: list[dict] = []
    for poly in polylines:
        # bugs/0799: a CLOSED ring is already a finished shape -- decomposing it into
        # segments and re-stitching would hand it back to the very walk that could not
        # close it. Pass it through untouched.
        if poly.get("closed"):
            closed_rings.append(poly)
            continue
        for run in _finite_runs(np.asarray(poly["points"])):
            # Dedupe raw fragments BEFORE stitching (direction-invariant): the same
            # edge extracted by both the silhouette and the feature pass would
            # otherwise stitch into a doubled back-and-forth chain that the
            # post-stitch dedupe cannot see.
            a = tuple(np.round(run[0], 3))
            b = tuple(np.round(run[-1], 3))
            length = float(np.sum(np.linalg.norm(np.diff(run, axis=0), axis=1)))
            fkey = (poly.get("color"), len(run), min(a, b), max(a, b), round(length, 2))
            if fkey in frag_seen or length < 1e-6:
                continue
            frag_seen.add(fkey)
            by_color.setdefault(poly.get("color"), []).append(run)
    out: list[dict] = list(closed_rings)
    seen: set = set()
    for color, strips in by_color.items():
        # Round 7: overlapping collinear pieces of ONE edge (silhouette + companion
        # copies, each cut at every touching feature) become one segment BEFORE the
        # endpoint stitch -- the stitch only ever sees shared endpoints.
        if decompose:
            segments = [
                np.array([p, q]) for run in strips for p, q in zip(run[:-1], run[1:])
            ]
            chains = []
        else:
            segments = [run for run in strips if run.shape[0] == 2]
            chains = [run for run in strips if run.shape[0] != 2]
        strips = merge_collinear_segments_2d(segments) + chains
        for chain in stitch_strips_2d(strips):
            simple = simplify_polyline_2d(chain, epsilon)
            if simple.shape[0] < 2:
                continue
            # Direction-invariant dedupe: the SAME edge found by both the silhouette
            # and the feature-edge pass (often traversed in opposite directions) must
            # collapse to one; distinct mirrored edges keep distinct endpoints.
            a = tuple(np.round(simple[0], 3))
            b = tuple(np.round(simple[-1], 3))
            length = float(np.sum(np.linalg.norm(np.diff(simple, axis=0), axis=1)))
            if length <= 1e-9:
                continue  # bugs/0802: a polyline of zero length has nothing to draw
            key = (color, simple.shape[0], min(a, b), max(a, b), round(length, 2))
            if key in seen:
                continue
            seen.add(key)
            out.append({"points": simple, "color": color})
    return out


def collect_viewport_dxf_layers(inspector) -> dict[str, dict[str, object]]:
    """Walk the inspector's renderer and flatten every visible actor into layered 2D
    polylines in the current camera's view plane."""
    renderer = getattr(inspector, "_renderer", None)
    if renderer is None:
        raise RuntimeError("the 3D view has no renderer")
    camera = renderer.GetActiveCamera()
    view = view_projection_matrix(camera)

    axis_keys = set((getattr(inspector, "_actor_optical_axis_map", None) or {}).keys())
    step_keys = set((getattr(inspector, "_actor_step_map", None) or {}).keys())
    row_keys = set((getattr(inspector, "_actor_row_map", None) or {}).keys())
    # bugs/0650 rework: consult BOTH ray registries -- the merged flush keys
    # _actor_ray_map directly (key -> ray index, -1 for merged) while _ray_actor_map
    # is the per-ray inverse; the first export missed every ray (73k polylines landed
    # unclassified in OVERLAYS on the user's Pyrite90 file).
    ray_keys = set((getattr(inspector, "_actor_ray_map", None) or {}).keys())
    for keys in (getattr(inspector, "_ray_actor_map", None) or {}).values():
        ray_keys.update(keys)
    measure_keys = set((getattr(inspector, "_actor_measure_handle_map", None) or {}).keys())
    # bugs/0650 round 4 (user's DXF.png "still have some open sides"): every STEP body
    # draws a COMPANION edges actor (pre-extracted CAD feature edges, lines-only,
    # unregistered) -- diag'd at 6.9k/30k segments on the Pyrite90 scene. Those carried
    # the body's own crease line-work but the many-segment heuristic misfiled them into
    # KRAKEN_RAYS. The scene dict registers them per label as ("mesh"|"edges", actor):
    # classify BOTH kinds into BODIES.
    cad_body_keys: set = set()
    try:
        scene_info = dict(getattr(inspector, "_kraken_scene", {}) or {})
        for _label, entries in (scene_info.get("cad_step_actors", {}) or {}).items():
            for _kind, cad_actor in list(entries or []):
                try:
                    cad_key = inspector._actor_key(cad_actor)
                except Exception:
                    cad_key = None
                if cad_key:
                    cad_body_keys.add(cad_key)
    except Exception:
        cad_body_keys = set()
    # bugs/0650 round 5 dead end, kept as a warning: do NOT classify
    # _actor_step_follow_map keys into BODIES wholesale -- ILLUMINATION RAY actors ride
    # their LED via that map (follow_step_label), so that "fix" reclassified ~1100 ray
    # polylines as body line art.
    # Round 6 (the user's freecad.png): the correct discriminator is ROW TRACKING. The
    # inspector's _add_mesh_actor registers CAD edge/rim companions with
    # track_row_index -> _row_actor_map (row -> [keys]; NOT the key->row _actor_row_map
    # this collector already reads -- a naming trap), while illumination bundles are
    # follow-only. Row-tracked companions are body line art.
    for keys in (getattr(inspector, "_row_actor_map", None) or {}).values():
        try:
            cad_body_keys.update(keys)
        except Exception:
            pass

    layers: dict[str, dict[str, object]] = {
        "KRAKEN_RAYS": {"ltype": "CONTINUOUS", "color": 3, "polylines": []},
        "KRAKEN_AXES": {"ltype": "DASHED", "color": 5, "polylines": []},
        "KRAKEN_BODIES": {"ltype": "CONTINUOUS", "color": 8, "polylines": []},
        "KRAKEN_MEASURES": {"ltype": "CONTINUOUS", "color": 30, "polylines": []},
        "KRAKEN_OVERLAYS": {"ltype": "CONTINUOUS", "color": 7, "polylines": []},
    }

    # bugs/0650 round 7 (lens.png/camera.png: housing outlines drawn GREEN on the
    # RAYS layer with black silhouette segments bridging their gaps): the STEP bodies'
    # companion edge actors are follow-only (no row -- STEP bodies are not rows), so
    # neither registry classifier could see them; every one of the user's 1120 RAYS
    # polylines was such an edge (ACI 94 = their dark-green display tone). The
    # registry-free discriminator: a lines-only actor whose bounding box lies INSIDE a
    # STEP mesh actor's bounds is that body's edge work; illumination bundles extend
    # far beyond any body. Collect the step-mesh bounds first.
    step_bounds: list[np.ndarray] = []
    try:
        _pp = renderer.GetViewProps()
        _pp.InitTraversal()
        while True:
            _prop = _pp.GetNextProp()
            if _prop is None:
                break
            try:
                _key = inspector._actor_key(_prop)
            except Exception:
                _key = None
            if _key in step_keys and hasattr(_prop, "GetBounds"):
                step_bounds.append(np.asarray(_prop.GetBounds(), dtype=float))
    except Exception:
        step_bounds = []

    def _inside_step_body(actor, margin: float = 2.0) -> bool:
        try:
            b = np.asarray(actor.GetBounds(), dtype=float)
        except Exception:
            return False
        if b.size != 6 or not np.all(np.isfinite(b)):
            return False
        for sb in step_bounds:
            if (
                b[0] >= sb[0] - margin and b[1] <= sb[1] + margin
                and b[2] >= sb[2] - margin and b[3] <= sb[3] + margin
                and b[4] >= sb[4] - margin and b[5] <= sb[5] + margin
            ):
                return True
        return False

    # Walk ALL view props, not just GetActors() -- assemblies and non-vtkActor prop
    # classes carry geometry too (bugs/0650 round 4: bodies invisible to the export
    # cannot close their boxes).
    props = renderer.GetViewProps()
    props.InitTraversal()
    pending = []
    while True:
        prop = props.GetNextProp()
        if prop is None:
            break
        pending.append(prop)
    body_outline_rings: list[np.ndarray] = []
    # bugs/0802: one orthographic z-buffer for the whole view, so the drawing can show only
    # what is actually visible. Filled in the actor sweep below and consulted by every body
    # strip -- including the STEP companion EDGE actors, which is why it is SCENE-wide rather
    # than per mesh (the lens occludes the camera, not just itself).
    depth_buffer = _SceneDepthBuffer(camera.GetDirectionOfProjection())
    counts = {"actors": 0, "skipped_heavy": 0}
    while pending:
        actor = pending.pop(0)
        try:
            parts = actor.GetParts() if hasattr(actor, "GetParts") else None
            if parts is not None:  # vtkAssembly: descend
                parts.InitTraversal()
                while True:
                    part = parts.GetNextProp3D()
                    if part is None:
                        break
                    pending.append(part)
                continue
        except Exception:
            pass
        try:
            if not actor.GetVisibility():
                continue
            mapper = actor.GetMapper() if hasattr(actor, "GetMapper") else None
            polydata = mapper.GetInput() if mapper is not None else None
            if polydata is None:
                continue
        except Exception:
            continue
        key = None
        try:
            key = inspector._actor_key(actor)
        except Exception:
            key = None
        actor_matrix = _vtk_matrix_to_numpy(actor.GetMatrix())
        try:
            color = actor.GetProperty().GetColor()
        except Exception:
            color = None

        if key in axis_keys:
            # bugs/0650: the DRAWN axis is a dash-fragment actor; exporting it produced
            # dozens of 2-point stubs. The model's own continuous polylines are appended
            # after the loop, and the DXF layer's DASHED linetype does the dashing.
            continue
        elif key in ray_keys:
            layer = "KRAKEN_RAYS"
        elif key in measure_keys:
            layer = "KRAKEN_MEASURES"
        elif key in step_keys or key in row_keys or key in cad_body_keys:
            layer = "KRAKEN_BODIES"
        else:
            layer = None  # decided below from the geometry itself

        n_polys = 0
        try:
            n_polys = int(polydata.GetNumberOfPolys())
        except Exception:
            n_polys = 0
        if n_polys:
            # A MESH: silhouettes (view-direction contours -- the slanted/vertical
            # housing profile the first cut missed) + feature/boundary edges. The
            # mesh's own stray LINE cells are tessellation artifacts and are NOT
            # exported (they were the 60k-segment horizontal soup). The actor matrix
            # is baked into the silhouette input, so project without it.
            view_dir = camera.GetDirectionOfProjection()
            depth_buffer.add_mesh(polydata, actor_matrix)  # bugs/0802
            strips = mesh_outline_strips(polydata, view_dir, actor_matrix)
            # bugs/0799: the projected-triangle union gives the body's outline as CLOSED
            # rings. Any silhouette/feature fragment lying ON that boundary is the same
            # line drawn twice, so it is dropped -- the rings carry it, closed.
            rings = mesh_outline_polygons(polydata, view_dir, actor_matrix)
            flat_rings = [project_points(ring, view, None) for ring in rings]
            body_outline_rings.extend(flat_rings)
            flat_strips = [project_points(strip, view, None) for strip in strips]
            if flat_rings:
                # In the VIEW PLANE: the ring is lifted to the mesh's mean depth, so a 3D
                # comparison would measure depth, not the drawing.
                surviving = _strips_not_already_drawn(flat_strips, flat_rings)
                keep = {id(a) for a in surviving}
                pairs = [(w, f) for w, f in zip(strips, flat_strips) if id(f) in keep]
            else:
                pairs = list(zip(strips, flat_strips))
            if not pairs and not flat_rings:
                counts["skipped_heavy"] += 1
                continue
            if layer is None or layer == "KRAKEN_RAYS":
                layer = "KRAKEN_BODIES"
            counts["actors"] += 1
            for flat in flat_rings:
                layers[layer]["polylines"].append(
                    {"points": flat, "color": None, "closed": True}
                )
            for world_strip, flat in pairs:
                # bugs/0802: carry the WORLD points so hidden-line removal can test depth
                # once every solid in the view has been rasterised.
                layers[layer]["polylines"].append(
                    {"points": flat, "color": None, "world": world_strip}
                )
            continue

        strips = polydata_line_strips(polydata)
        if not strips:
            continue
        if layer is None:
            # Unregistered lines-only actor: inside a STEP body's bounds it is that
            # body's companion edge work (round 7); otherwise a many-segment bundle is
            # ray-like (illumination bundles draw outside the imaging-ray registries)
            # and a few segments are a guide/overlay.
            if _inside_step_body(actor):
                layer = "KRAKEN_BODIES"
            else:
                layer = "KRAKEN_RAYS" if len(strips) >= 20 else "KRAKEN_OVERLAYS"
        counts["actors"] += 1
        aci = nearest_aci(color) if color is not None else None
        for strip in strips:
            flat = project_points(strip, view, actor_matrix)
            entry = {"points": flat, "color": aci if layer == "KRAKEN_RAYS" and aci else None}
            if layer == "KRAKEN_BODIES":
                # bugs/0802: a STEP companion EDGE actor is body line art too, and it is the
                # densest source of see-through edges. Give it world points (actor matrix
                # applied, as project_points does) so the depth test can reach it.
                world = np.asarray(strip, dtype=float).reshape(-1, 3)
                if actor_matrix is not None:
                    m = np.asarray(actor_matrix, dtype=float)
                    world = (np.hstack([world, np.ones((len(world), 1))]) @ m.T)[:, :3]
                entry["world"] = world
            layers[layer]["polylines"].append(entry)
    # The axes, from the MODEL records: one continuous polyline each (the layer's
    # DASHED linetype renders the dashes -- geometry stays a single vector line).
    for record in list(getattr(inspector, "_optical_axis_pick_records", None) or []):
        try:
            points = np.asarray(record.get("points"), dtype=float).reshape(-1, 3)
        except Exception:
            continue
        if points.shape[0] < 2:
            continue
        layers["KRAKEN_AXES"]["polylines"].append(
            {"points": project_points(points, view, None), "color": None}
        )

    # bugs/0802: hidden-line removal. Every body strip is split into the runs that are not
    # behind a solid; the closed outline rings are kept whole (an outline is on the silhouette
    # by construction, and a ring cut into runs would stop being a shape). Rays, axes and
    # overlays are NOT filtered -- the 3D view draws them over the scene and the drawing
    # follows the view (bugs/0800).
    body_spec = layers.get("KRAKEN_BODIES")
    if body_spec is not None and depth_buffer.buffer is None:
        depth_buffer._build()
    if body_spec is not None and depth_buffer.buffer is not None:
        kept_polylines: list[dict] = []
        hidden_dropped = 0
        for entry in body_spec["polylines"]:
            if entry.get("closed"):
                kept_polylines.append(entry)
                continue
            world = entry.get("world")
            if world is None:
                kept_polylines.append(entry)
                continue
            runs = depth_buffer.visible_runs(world)
            if not runs:
                hidden_dropped += 1
                continue
            if len(runs) == 1 and len(runs[0]) == len(np.asarray(world)):
                kept_polylines.append(entry)
                continue
            hidden_dropped += 1
            for run in runs:
                kept_polylines.append({
                    "points": project_points(run, view, None),
                    "color": entry.get("color"),
                })
        counts["hidden_lines_removed"] = hidden_dropped
        body_spec["polylines"] = kept_polylines

    # bugs/0799: the STEP bodies also arrive as companion EDGE actors (lines-only
    # polydata), which never pass through the mesh outline path -- so the outline dedupe
    # has to run once over the finished BODIES layer, not per mesh actor. Anything lying
    # on a closed outline ring is that ring drawn again, open.
    if body_outline_rings:
        body_spec = layers.get("KRAKEN_BODIES")
        if body_spec is not None:
            open_art = [q for q in body_spec["polylines"] if not q.get("closed")]
            closed_art = [q for q in body_spec["polylines"] if q.get("closed")]
            surviving = _strips_not_already_drawn(
                [np.asarray(q["points"], dtype=float) for q in open_art],
                body_outline_rings,
            )
            survivor_ids = {id(a) for a in surviving}
            kept_open = [
                q for q, a in zip(open_art,
                                  [np.asarray(q["points"], dtype=float) for q in open_art])
                if id(a) in survivor_ids
            ]
            counts["outline_absorbed"] = len(open_art) - len(kept_open)
            body_spec["polylines"] = closed_art + kept_open

    # bugs/0650 ("a line should be one vector line"): stitch shared-endpoint fragments
    # into maximal polylines, collapse collinear runs (RDP), drop duplicates.
    for name, spec in layers.items():
        if name.startswith("__"):
            continue
        spec["polylines"] = _postprocess_layer_polylines(
            spec["polylines"], decompose=(name == "KRAKEN_BODIES")
        )
    layers["__counts__"] = counts  # type: ignore[assignment]
    return layers


def write_dxf_r12(path, layers: dict[str, dict[str, object]]) -> dict[str, int]:
    """Write layered 2D polylines as a DXF R12 ASCII file. Returns entity counts."""
    real_layers = {k: v for k, v in layers.items() if not k.startswith("__")}
    out: list[str] = []

    def tag(code: int, value) -> None:
        out.append(f"{int(code)}")
        out.append(f"{value}")

    # ---- header ----------------------------------------------------------------
    tag(0, "SECTION"); tag(2, "HEADER")
    tag(9, "$ACADVER"); tag(1, "AC1009")
    tag(0, "ENDSEC")
    # ---- tables: linetypes + layers ---------------------------------------------
    tag(0, "SECTION"); tag(2, "TABLES")
    tag(0, "TABLE"); tag(2, "LTYPE"); tag(70, 2)
    tag(0, "LTYPE"); tag(2, "CONTINUOUS"); tag(70, 0)
    tag(3, "Solid line"); tag(72, 65); tag(73, 0); tag(40, 0.0)
    tag(0, "LTYPE"); tag(2, "DASHED"); tag(70, 0)
    tag(3, "Dashed line __ __ __"); tag(72, 65); tag(73, 2); tag(40, 7.5)
    tag(49, 5.0); tag(49, -2.5)
    tag(0, "ENDTAB")
    tag(0, "TABLE"); tag(2, "LAYER"); tag(70, len(real_layers))
    for name, spec in real_layers.items():
        tag(0, "LAYER"); tag(2, name); tag(70, 0)
        tag(62, int(spec.get("color", 7)))
        tag(6, str(spec.get("ltype", "CONTINUOUS")))
    tag(0, "ENDTAB")
    tag(0, "ENDSEC")
    # ---- entities ---------------------------------------------------------------
    tag(0, "SECTION"); tag(2, "ENTITIES")
    counts: dict[str, int] = {}
    for name, spec in real_layers.items():
        n = 0
        for poly in spec.get("polylines", []):
            pts = np.asarray(poly["points"], dtype=float).reshape(-1, 2)
            if pts.shape[0] < 2 or not np.all(np.isfinite(pts)):
                continue
            # bugs/0799: a polyline whose first vertex repeats as its last IS a closed
            # shape, whether it came from the outline union or from a stitched interior
            # loop (a flange circle closes on itself). DXF says so with bit 1 of group 70
            # and does not repeat the vertex -- CAD then offsets, hatches and area-measures
            # it as a region instead of treating it as a line that happens to meet itself.
            is_closed = len(pts) >= 4 and (
                bool(poly.get("closed")) or bool(np.allclose(pts[0], pts[-1]))
            )
            if is_closed and np.allclose(pts[0], pts[-1]):
                pts = pts[:-1]
            is_closed = is_closed and len(pts) >= 3
            tag(0, "POLYLINE"); tag(8, name); tag(66, 1); tag(70, 1 if is_closed else 0)
            color = poly.get("color")
            if color:
                tag(62, int(color))
            for x, y in pts:
                tag(0, "VERTEX"); tag(8, name)
                tag(10, f"{x:.4f}"); tag(20, f"{y:.4f}"); tag(30, "0.0")
            tag(0, "SEQEND")
            n += 1
        # bugs/0652: view captions for the six-view component sheet -- centre-aligned
        # R12 TEXT (72=1 needs the second alignment point 11/21).
        for txt in spec.get("texts", []):
            x, y = (float(v) for v in txt["pos"])
            tag(0, "TEXT"); tag(8, name)
            tag(10, f"{x:.4f}"); tag(20, f"{y:.4f}"); tag(30, "0.0")
            tag(40, f"{float(txt.get('height', 3.5)):.2f}")
            tag(1, str(txt["text"]))
            tag(72, 1)
            tag(11, f"{x:.4f}"); tag(21, f"{y:.4f}"); tag(31, "0.0")
            n += 1
        counts[name] = n
    tag(0, "ENDSEC")
    tag(0, "EOF")
    Path(path).write_text("\n".join(out) + "\n", encoding="ascii")
    return counts


def export_viewport_to_dxf(inspector, path) -> str:
    """Flatten the inspector's CURRENT view into a DXF R12 file; returns a summary."""
    layers = collect_viewport_dxf_layers(inspector)
    counts = write_dxf_r12(path, layers)
    total = sum(counts.values())
    parts = ", ".join(
        f"{name.replace('KRAKEN_', '').lower()} {n}" for name, n in counts.items() if n
    )
    return (
        f"Exported the current 3D view to {Path(path).name}: {total} polylines "
        f"({parts}). True-scale mm in the view plane; DASHED axes; bodies as feature "
        f"edges. (DXF R12 -- opens in AutoCAD/FreeCAD/LibreCAD; convert to DWG there "
        f"if needed.)"
    )


# ---------------------------------------------------------------------------------
# bugs/0652: right-click a component -> one DXF sheet with all six orthographic
# views (third-angle: TOP over FRONT, BOTTOM under, LEFT/RIGHT beside, BACK past
# RIGHT). World-axis views -- folded scenes keep their legs axis-aligned, so the
# part reads naturally; a tilted BS shows its diagonal, which is the truth.

# (name, view direction INTO the screen, screen right, screen up); for every view
# right x up == -direction (toward the viewer), so the projections are proper
# right-handed camera frames and adjacent views share their common world axis
# (FRONT/LEFT/RIGHT/BACK all have up=+Z; TOP/BOTTOM share FRONT's right=+X).
SIX_VIEW_BASES: tuple = (
    ("FRONT", (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("BACK", (0.0, -1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    ("LEFT", (1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    ("RIGHT", (-1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    ("TOP", (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    ("BOTTOM", (0.0, 0.0, 1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0)),
)


def place_six_views(bounds: dict[str, tuple], gap: float) -> dict[str, tuple]:
    """Third-angle sheet offsets for each view's RAW projected coordinates.

    Raw coordinates already align adjacent views along their shared world axis
    (side views share height = world Z; top/bottom share width = world X), so a
    side view gets only an x shift and top/bottom only a y shift -- the views stay
    PROJECTIONALLY aligned like a drafted sheet, not merely arranged in a grid.
    ``bounds``: name -> (min_x, max_x, min_y, max_y). Views absent from ``bounds``
    are skipped."""
    if "FRONT" not in bounds:
        return {name: (0.0, 0.0) for name in bounds}
    fb = bounds["FRONT"]
    offsets: dict[str, tuple] = {"FRONT": (0.0, 0.0)}
    if "LEFT" in bounds:
        offsets["LEFT"] = (fb[0] - gap - bounds["LEFT"][1], 0.0)
    if "RIGHT" in bounds:
        offsets["RIGHT"] = (fb[1] + gap - bounds["RIGHT"][0], 0.0)
    if "BACK" in bounds:
        if "RIGHT" in bounds:
            anchor = offsets["RIGHT"][0] + bounds["RIGHT"][1]
        else:
            anchor = fb[1]
        offsets["BACK"] = (anchor + gap - bounds["BACK"][0], 0.0)
    if "TOP" in bounds:
        offsets["TOP"] = (0.0, fb[3] + gap - bounds["TOP"][2])
    if "BOTTOM" in bounds:
        offsets["BOTTOM"] = (0.0, fb[2] - gap - bounds["BOTTOM"][3])
    return offsets


def collect_component_six_view_layers(
    inspector, *, step_label: str | None = None, row_indices=None
) -> dict[str, dict[str, object]]:
    """Collect ONE component's geometry as six orthographic view projections.

    The component is named either by its STEP-overlay label or by its row indices
    (a lens block passes its whole row group). Actor selection reuses the bugs/0650
    registries: ``_actor_step_map`` (key -> step label), ``_actor_row_map`` /
    ``_row_actor_map`` for rows, plus the round-7 bounds-containment rule so a STEP
    body's follow-only companion edge actors come along with it."""
    renderer = getattr(inspector, "_renderer", None)
    if renderer is None:
        raise RuntimeError("the 3D view has no renderer")
    step_label = str(step_label).strip().lower() if step_label else None
    row_set = {int(i) for i in (row_indices or [])}
    actor_step = dict(getattr(inspector, "_actor_step_map", None) or {})
    actor_row = dict(getattr(inspector, "_actor_row_map", None) or {})
    row_actor = dict(getattr(inspector, "_row_actor_map", None) or {})
    ray_keys = set(getattr(inspector, "_actor_ray_map", None) or {})
    for keys in (getattr(inspector, "_ray_actor_map", None) or {}).values():
        ray_keys.update(keys)
    axis_keys = set(getattr(inspector, "_actor_optical_axis_map", None) or {})
    want_keys: set = set()
    if step_label:
        want_keys.update(k for k, lab in actor_step.items() if str(lab).strip().lower() == step_label)
    if row_set:
        want_keys.update(k for k, r in actor_row.items() if int(r) in row_set)
        for idx in row_set:
            want_keys.update(row_actor.get(idx, []) or [])

    props = renderer.GetViewProps()
    props.InitTraversal()
    pending = []
    while True:
        prop = props.GetNextProp()
        if prop is None:
            break
        pending.append(prop)
    meshes: list[tuple] = []  # (polydata, actor_matrix)
    line_actors: list[tuple] = []  # (prop, polydata, actor_matrix) -- deferred containment
    mesh_bounds: list[np.ndarray] = []
    while pending:
        actor = pending.pop(0)
        try:
            parts = actor.GetParts() if hasattr(actor, "GetParts") else None
            if parts is not None:
                parts.InitTraversal()
                while True:
                    part = parts.GetNextProp3D()
                    if part is None:
                        break
                    pending.append(part)
                continue
        except Exception:
            pass
        try:
            if not actor.GetVisibility():
                continue
            mapper = actor.GetMapper() if hasattr(actor, "GetMapper") else None
            polydata = mapper.GetInput() if mapper is not None else None
            if polydata is None:
                continue
        except Exception:
            continue
        try:
            key = inspector._actor_key(actor)
        except Exception:
            key = None
        if key in ray_keys or key in axis_keys:
            continue
        actor_matrix = _vtk_matrix_to_numpy(actor.GetMatrix())
        n_polys = 0
        try:
            n_polys = int(polydata.GetNumberOfPolys())
        except Exception:
            n_polys = 0
        if key in want_keys:
            if n_polys:
                meshes.append((polydata, actor_matrix))
                try:
                    mesh_bounds.append(np.asarray(actor.GetBounds(), dtype=float))
                except Exception:
                    pass
            else:
                line_actors.append((polydata, actor_matrix, True))
        elif step_label and n_polys == 0 and key not in actor_step and key not in actor_row:
            # Unregistered lines-only actor: keep it only if it sits inside THIS
            # component's mesh bounds (the round-7 companion-edge rule, scoped to
            # the one body being exported).
            line_actors.append((polydata, actor_matrix, False))
    if not meshes and not any(flag for _, _, flag in line_actors):
        raise RuntimeError("no visible geometry found for this component")

    def _contained(polydata, actor_matrix, margin: float = 2.0) -> bool:
        strips = polydata_line_strips(polydata)
        if not strips:
            return False
        pts = np.vstack(strips)
        if actor_matrix is not None:
            pts = (actor_matrix[:3, :3] @ pts.T).T + actor_matrix[:3, 3]
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        for sb in mesh_bounds:
            if (
                lo[0] >= sb[0] - margin and hi[0] <= sb[1] + margin
                and lo[1] >= sb[2] - margin and hi[1] <= sb[3] + margin
                and lo[2] >= sb[4] - margin and hi[2] <= sb[5] + margin
            ):
                return True
        return False

    line_strips_world: list[np.ndarray] = []
    for polydata, actor_matrix, selected in line_actors:
        if not selected and not _contained(polydata, actor_matrix):
            continue
        for strip in polydata_line_strips(polydata):
            pts = np.asarray(strip, dtype=float)
            if actor_matrix is not None:
                pts = (actor_matrix[:3, :3] @ pts.T).T + actor_matrix[:3, 3]
            line_strips_world.append(pts)

    view_polys: dict[str, list[dict]] = {}
    view_bounds: dict[str, tuple] = {}
    for name, vdir, right, up in SIX_VIEW_BASES:
        right_v = np.asarray(right, dtype=float)
        up_v = np.asarray(up, dtype=float)
        # bugs/0802: a six-view sheet is the worst case for see-through line art -- the user's
        # camera TOP view drew the connector internals, the PCB and the far wall through the
        # body (94.2% of this camera's feature edges are occluded). One depth buffer per view
        # direction; every strip is cut to the runs that are actually visible.
        depth = _SceneDepthBuffer(vdir)
        for polydata, actor_matrix in meshes:
            depth.add_mesh(polydata, actor_matrix)

        def _visible(world_strip):
            runs = depth.visible_runs(world_strip)
            return runs if runs else []

        raw: list[dict] = []
        for polydata, actor_matrix in meshes:
            for strip in mesh_outline_strips(polydata, vdir, actor_matrix):
                for run in _visible(strip):
                    flat = np.stack([run @ right_v, run @ up_v], axis=1)
                    raw.append({"points": flat, "color": None})
        for pts in line_strips_world:
            for run in _visible(pts):
                flat = np.stack([run @ right_v, run @ up_v], axis=1)
                raw.append({"points": flat, "color": None})
        polys = _postprocess_layer_polylines(raw, decompose=True)
        if not polys:
            continue
        allp = np.vstack([q["points"] for q in polys])
        view_polys[name] = polys
        view_bounds[name] = (
            float(allp[:, 0].min()), float(allp[:, 0].max()),
            float(allp[:, 1].min()), float(allp[:, 1].max()),
        )
    if not view_polys:
        raise RuntimeError("the component projected to no line work")

    max_dim = max(
        max(b[1] - b[0], b[3] - b[2]) for b in view_bounds.values()
    )
    gap = max(0.35 * max_dim, 15.0)
    text_height = max(0.05 * max_dim, 2.5)
    offsets = place_six_views(view_bounds, gap)
    layers: dict[str, dict[str, object]] = {
        "KRAKEN_BODIES": {"ltype": "CONTINUOUS", "color": 8, "polylines": []},
        "KRAKEN_LABELS": {"ltype": "CONTINUOUS", "color": 3, "polylines": [], "texts": []},
    }
    for name, polys in view_polys.items():
        ox, oy = offsets.get(name, (0.0, 0.0))
        shift = np.array([ox, oy])
        for q in polys:
            layers["KRAKEN_BODIES"]["polylines"].append(
                {"points": q["points"] + shift, "color": None}
            )
        b = view_bounds[name]
        layers["KRAKEN_LABELS"]["texts"].append(
            {
                "pos": ((b[0] + b[1]) / 2.0 + ox, b[2] + oy - 0.45 * gap),
                "height": text_height,
                "text": name,
            }
        )
    return layers


def export_component_six_view_dxf(
    inspector, path, *, step_label: str | None = None, row_indices=None, display_name: str = ""
) -> str:
    """Write one component's six orthographic views as a DXF R12 sheet; returns a summary."""
    layers = collect_component_six_view_layers(
        inspector, step_label=step_label, row_indices=row_indices
    )
    counts = write_dxf_r12(path, layers)
    views = len(layers["KRAKEN_LABELS"]["texts"])
    what = display_name or (step_label or "component")
    return (
        f"Exported {what} to {Path(path).name}: {views} views "
        f"({counts.get('KRAKEN_BODIES', 0)} polylines), third-angle layout, true-scale "
        f"mm. (DXF R12 -- opens in AutoCAD/FreeCAD/LibreCAD.)"
    )
