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
            sil = vtk.vtkPolyDataSilhouette()
            sil.SetInputData(source)
            sil.SetDirectionToSpecifiedVector()
            sil.SetVector(*(float(v) for v in np.asarray(view_direction).reshape(3)))
            sil.SetEnableFeatureAngle(0)
            sil.BorderEdgesOn()
            sil.Update()
            strips.extend(polydata_line_strips(sil.GetOutput()))

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
                    chain[0:0] = list(seg[:-1])
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


def _postprocess_layer_polylines(polylines: list[dict], epsilon: float = 0.02) -> list[dict]:
    """Per colour bucket: split at bad points, stitch fragments, simplify, dedupe."""
    by_color: dict[object, list[np.ndarray]] = {}
    frag_seen: set = set()
    for poly in polylines:
        for run in _finite_runs(np.asarray(poly["points"])):
            # Dedupe raw fragments BEFORE stitching (direction-invariant): the same
            # edge extracted by both the silhouette and the feature pass would
            # otherwise stitch into a doubled back-and-forth chain that the
            # post-stitch dedupe cannot see.
            a = tuple(np.round(run[0], 3))
            b = tuple(np.round(run[-1], 3))
            length = float(np.sum(np.linalg.norm(np.diff(run, axis=0), axis=1)))
            fkey = (poly.get("color"), len(run), min(a, b), max(a, b), round(length, 2))
            if fkey in frag_seen:
                continue
            frag_seen.add(fkey)
            by_color.setdefault(poly.get("color"), []).append(run)
    out: list[dict] = []
    seen: set = set()
    for color, strips in by_color.items():
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
    # _actor_step_follow_map keys into BODIES -- ILLUMINATION RAY actors ride their
    # LED via that map (follow_step_label), so the "fix" reclassified ~1100 ray
    # polylines as body line art. The dash-like fragments on the housing bands are
    # legitimate illumination-ray terminations, not broken body lines.

    layers: dict[str, dict[str, object]] = {
        "KRAKEN_RAYS": {"ltype": "CONTINUOUS", "color": 3, "polylines": []},
        "KRAKEN_AXES": {"ltype": "DASHED", "color": 5, "polylines": []},
        "KRAKEN_BODIES": {"ltype": "CONTINUOUS", "color": 8, "polylines": []},
        "KRAKEN_MEASURES": {"ltype": "CONTINUOUS", "color": 30, "polylines": []},
        "KRAKEN_OVERLAYS": {"ltype": "CONTINUOUS", "color": 7, "polylines": []},
    }

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
            strips = mesh_outline_strips(polydata, view_dir, actor_matrix)
            if not strips:
                counts["skipped_heavy"] += 1
                continue
            if layer is None or layer == "KRAKEN_RAYS":
                layer = "KRAKEN_BODIES"
            counts["actors"] += 1
            for strip in strips:
                flat = project_points(strip, view, None)
                layers[layer]["polylines"].append({"points": flat, "color": None})
            continue

        strips = polydata_line_strips(polydata)
        if not strips:
            continue
        if layer is None:
            # Unregistered lines-only actor: a many-segment bundle is ray-like
            # (illumination bundles draw outside the imaging-ray registries); a few
            # segments are a guide/overlay.
            layer = "KRAKEN_RAYS" if len(strips) >= 20 else "KRAKEN_OVERLAYS"
        counts["actors"] += 1
        aci = nearest_aci(color) if color is not None else None
        for strip in strips:
            flat = project_points(strip, view, actor_matrix)
            layers[layer]["polylines"].append(
                {"points": flat, "color": aci if layer == "KRAKEN_RAYS" and aci else None}
            )
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

    # bugs/0650 ("a line should be one vector line"): stitch shared-endpoint fragments
    # into maximal polylines, collapse collinear runs (RDP), drop duplicates.
    for name, spec in layers.items():
        if name.startswith("__"):
            continue
        spec["polylines"] = _postprocess_layer_polylines(spec["polylines"])
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
            tag(0, "POLYLINE"); tag(8, name); tag(66, 1); tag(70, 0)
            color = poly.get("color")
            if color:
                tag(62, int(color))
            for x, y in pts:
                tag(0, "VERTEX"); tag(8, name)
                tag(10, f"{x:.4f}"); tag(20, f"{y:.4f}"); tag(30, "0.0")
            tag(0, "SEQEND")
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
