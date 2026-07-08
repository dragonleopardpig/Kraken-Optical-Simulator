"""Coaxial-LED illumination rays coloured by fate: reaching the FOV (green) vs clipped at the
BS-exit stop (red) -- the REAL traced LED->beam-splitter->object rays, not a synthetic frustum.

The machine-vision coaxial illuminator floods a flat area LED onto a 45 deg beam splitter that folds
the light down onto the object/FOV. The fold-axis clear aperture of the splitter is foreshortened
(55*cos45 ~ 39 mm), so it only just covers the 39x39 FOV: the rays aimed at the fold-axis FOV edges
are clipped at the BS-exit stop and never reach the sensor, which is what darkens the two fold-axis
edges in production. This overlay draws that mechanism directly from the preview trace's per-ray
records -- each LED ray becomes a world-coord polyline (LED origin + its surface hits); rays that reach
the image/detector are green, rays that terminate early (stopped or missed at the BS-exit stop) are
red. Rays killed at the LED's own source aperture (a dot at the emitter plane) carry no story and are
dropped. Pure geometry (numpy); the inspector builds the VTK polylines from the returned arrays.
"""

from __future__ import annotations

import numpy as np

# reaches the FOV / detector (green) vs clipped short at the BS-exit stop (red).
ILLUM_RAY_REACHING_COLOR = (0.16, 0.72, 0.28)
ILLUM_RAY_CLIPPED_COLOR = (0.90, 0.28, 0.12)

# The limiting BS-exit-stop clear aperture (amber outline) -- the opening the green rays pass through,
# foreshortened on the fold axis (the 55*cos45~39 rectangle the red rays are cut on).
ILLUM_APERTURE_COLOR = (0.98, 0.78, 0.12)

# The clear aperture is read off the survivors as a robust high percentile of where they cross the
# stop -- it encloses the passing rays without chasing a lone edge outlier.
ILLUM_APERTURE_PERCENTILE = 98.0

# Per-class draw cap: the production trace launches ~60k LED rays; a few hundred polylines per class is
# plenty to read the fan and keeps the overlay light. Subsampling is deterministic (seeded).
ILLUM_RAY_MAX_PER_CLASS = 240
ILLUM_RAY_SUBSAMPLE_SEED = 7

# A polyline must span at least this far in world z to be drawable. A ray blocked at the LED's own
# source aperture (status "Stop @ S0") collapses to a single dot at the emitter plane; it is not part
# of the BS-clipping story and would render as a zero-length artefact.
ILLUM_RAY_MIN_Z_SPAN_MM = 1.0


def _record_polyline(record, min_z_span):
    """World-coord polyline for one ray: the LED origin followed by each surface hit. None when the ray
    is degenerate (fewer than 2 finite vertices, or collapsed at the source plane)."""
    try:
        start = (
            float(record.get("source_x", 0.0)),
            float(record.get("source_y", 0.0)),
            float(record.get("source_z", 0.0)),
        )
    except Exception:
        return None
    points = [start]
    for hit in (record.get("hits") or []):
        points.append(
            (float(hit.get("x", np.nan)), float(hit.get("y", np.nan)), float(hit.get("z", np.nan)))
        )
    arr = np.asarray(points, dtype=float)
    if arr.shape[0] < 2 or not np.all(np.isfinite(arr)):
        return None
    if float(arr[:, 2].max() - arr[:, 2].min()) < float(min_z_span):
        return None
    return arr


def _reaches_fov(record):
    return bool(record.get("reaches_image") or record.get("reaches_detector") or record.get("reaches_target"))


def _merge_polylines(polylines):
    """Concatenate variable-length polylines into (points (N,3) float, lines (M,) int64) where ``lines``
    is a VTK poly-line cell array ``[m0, i0.., m1, j0.., ...]``. Empty arrays when nothing to draw."""
    if not polylines:
        return np.empty((0, 3), dtype=float), np.empty((0,), dtype=np.int64)
    points = []
    cells: list[int] = []
    offset = 0
    for arr in polylines:
        count = int(arr.shape[0])
        points.append(arr)
        cells.append(count)
        cells.extend(range(offset, offset + count))
        offset += count
    return np.vstack(points), np.asarray(cells, dtype=np.int64)


def _subsample(polylines, cap, rng):
    if cap is None or len(polylines) <= int(cap):
        return polylines
    idx = rng.choice(len(polylines), int(cap), replace=False)
    return [polylines[i] for i in idx]


def _terminals(polylines):
    return np.asarray([pl[-1] for pl in polylines], dtype=float) if polylines else np.empty((0, 3), dtype=float)


def _rectangle_loop(half, z):
    """Closed-loop rectangle (points (5,3), VTK line cell [5,0,1,2,3,4]) of half-extents ``half`` = (hx,
    hy) centred on the axis at plane ``z`` -- an outline the inspector renders like any other polyline."""
    hx, hy = float(half[0]), float(half[1])
    corners = np.array(
        [[-hx, -hy, z], [hx, -hy, z], [hx, hy, z], [-hx, hy, z], [-hx, -hy, z]], dtype=float
    )
    return corners, np.array([5, 0, 1, 2, 3, 4], dtype=np.int64)


def _plane_crossings(polylines, z):
    """(x, y) where each polyline first crosses the plane ``z`` (linear interpolation on the
    straddling segment). Polylines that never reach the plane contribute nothing. Returns (K, 2)."""
    out = []
    for arr in polylines:
        zc = arr[:, 2]
        for i in range(arr.shape[0] - 1):
            z0, z1 = float(zc[i]), float(zc[i + 1])
            if z1 == z0:
                continue
            if (z0 - z) * (z1 - z) <= 0.0:
                t = (z - z0) / (z1 - z0)
                out.append(arr[i, :2] + t * (arr[i + 1, :2] - arr[i, :2]))
                break
    return np.asarray(out, dtype=float) if out else np.empty((0, 2), dtype=float)


def build_source_illumination_rays_overlay(
    records,
    *,
    role="illumination",
    max_per_class=ILLUM_RAY_MAX_PER_CLASS,
    seed=ILLUM_RAY_SUBSAMPLE_SEED,
    min_z_span=ILLUM_RAY_MIN_Z_SPAN_MM,
    detector_z=None,
):
    """Split the LED illumination rays into reaching (green) and clipped (red) polylines and bake the
    VTK line arrays, plus the limiting BS-exit-stop clear aperture (amber outline) read off the
    survivors -- the foreshortened rectangle the red rays are cut on. Returns a spec dict (arrays +
    colours + counts + the clip-plane z + which in-plane axis the clipping falls on + the aperture
    half-extents), or None when there is nothing drawable."""
    if not records:
        return None
    rng = np.random.default_rng(int(seed))
    reaching = []
    clipped = []
    for record in records:
        if role is not None:
            if str(record.get("source_role", "")).strip().lower() != str(role).strip().lower():
                continue
        arr = _record_polyline(record, min_z_span)
        if arr is None:
            continue
        (reaching if _reaches_fov(record) else clipped).append(arr)
    if not reaching and not clipped:
        return None

    reaching_total = len(reaching)
    clipped_total = len(clipped)
    reaching_draw = _subsample(reaching, max_per_class, rng)
    clipped_draw = _subsample(clipped, max_per_class, rng)
    reaching_points, reaching_lines = _merge_polylines(reaching_draw)
    clipped_points, clipped_lines = _merge_polylines(clipped_draw)

    # The clip plane is where the red rays die -- the BS-exit stop (median terminal z, ~75 in the
    # coaxial scene). Naming the fold axis is subtler than "which way do the clipped rays spread":
    # the clipped rays spread WIDER on the unconstrained perpendicular axis (they fill it) than on
    # the foreshortened fold axis they are being cut on, so raw spread points the wrong way. Instead
    # compare against the survivors: the reaching (green) rays that make it through define the clear
    # aperture at the stop, and the clipped (red) rays only stick OUT past that envelope on the
    # foreshortened fold axis. The fold axis is the one with the larger clipped-beyond-survivor margin.
    clip_terminals = _terminals(clipped)
    clip_plane_z = float(np.median(clip_terminals[:, 2])) if clip_terminals.size else None
    clip_axis = None
    aperture_half = None
    clipped_half = None
    aperture_points = np.empty((0, 3), dtype=float)
    aperture_lines = np.empty((0,), dtype=np.int64)
    if clip_plane_z is not None:
        survivor_xy = _plane_crossings(reaching, clip_plane_z)
        clipped_xy = _plane_crossings(clipped, clip_plane_z)
        if survivor_xy.shape[0] >= 8:
            # The clear aperture the green rays actually pass through -- the limiting BS-exit-stop
            # opening, foreshortened on the fold axis. This is the rectangle the red rays are cut on.
            aperture_half = np.percentile(np.abs(survivor_xy), ILLUM_APERTURE_PERCENTILE, axis=0)
            aperture_points, aperture_lines = _rectangle_loop(aperture_half, clip_plane_z)
        if survivor_xy.shape[0] >= 8 and clipped_xy.shape[0] >= 8:
            clipped_half = np.percentile(np.abs(clipped_xy), ILLUM_APERTURE_PERCENTILE, axis=0)
            survivor_env = np.percentile(np.abs(survivor_xy), 95, axis=0)
            clipped_env = np.percentile(np.abs(clipped_xy), 95, axis=0)
            margin = clipped_env - survivor_env  # [x, y]: how far red sticks out past green per axis
            j = int(np.argmax(margin))
            if margin[j] >= 1.0 and margin[j] >= margin[1 - j] + 0.5:
                clip_axis = "X" if j == 0 else "Y"

    return {
        "kind": "source_illumination_rays",
        "reaching_points": reaching_points,
        "reaching_lines": reaching_lines,
        "clipped_points": clipped_points,
        "clipped_lines": clipped_lines,
        "aperture_points": aperture_points,
        "aperture_lines": aperture_lines,
        "reaching_color": ILLUM_RAY_REACHING_COLOR,
        "clipped_color": ILLUM_RAY_CLIPPED_COLOR,
        "aperture_color": ILLUM_APERTURE_COLOR,
        "reaching_total": int(reaching_total),
        "clipped_total": int(clipped_total),
        "reaching_drawn": int(len(reaching_draw)),
        "clipped_drawn": int(len(clipped_draw)),
        "clip_plane_z": clip_plane_z,
        "clip_axis": clip_axis,
        "aperture_half": None if aperture_half is None else [float(aperture_half[0]), float(aperture_half[1])],
        "clipped_half": None if clipped_half is None else [float(clipped_half[0]), float(clipped_half[1])],
        "detector_z": None if detector_z is None else float(detector_z),
    }
