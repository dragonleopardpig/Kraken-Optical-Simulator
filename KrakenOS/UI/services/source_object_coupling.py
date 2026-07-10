"""bugs/0274 (Stage 3) -- Option-B irradiance-weighted Source -> Object -> Detector coupling.

The factorized approximation: trace the illumination source onto the object ONCE and bin its
irradiance (reusing the 0259-0262 relative-illumination machinery), then weight each
object -> lens imaging ray by the local source irradiance at its object origin.  The source
non-uniformity -- e.g. the MV-150 coaxial dark edges (bugs/0179) -- then rides the ACTUAL detector
image, not just the standalone "Relative illumination" overlay.

Crucially this is ADDITIVE and read-only over the imaging trace: the coupling only re-weights
imaging rays for display; it NEVER redefines the image plane / detector / optical axis (bugs/0266:
illumination must never drive the imaging conjugates).  The source -> object map is binned from the
ISOLATED source records (bugs/0272/0273 emission), so evaluating the coupling cannot disturb the
object-driven imaging state.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.source_illumination_analysis import source_illumination_map_data_from_samples

# Coarse default so the binned irradiance is a SMOOTH rolloff, not a sparse per-ray count map: an
# imaging ray's object origin is (by construction) exactly where a source ray landed, so a fine grid
# over a modest ray budget leaves each origin alone in its bin -> a 0/half/peak staircase, not the
# smooth illumination falloff the coupling must transfer (probe: a 73x73 grid gave ~2 distinct
# weights; a 16x16 grid recovered the fold 0.54 / perp 0.95 dark-edge asymmetry).
DEFAULT_COUPLING_BINS = 16


def object_irradiance_map(
    editor: Any,
    system: Any,
    object_surface_index: int,
    *,
    ray_records: list[dict[str, object]],
    bins: int = DEFAULT_COUPLING_BINS,
) -> dict[str, object] | None:
    """Bin the source -> object irradiance landing on ``object_surface_index`` into a smooth,
    peak-normalized density map.

    Returns ``{density, x_edges, y_edges, extent, coord, hit_count}`` (``density`` is ``[iy, ix]``,
    peak-normalized to ``[0, 1]``) or ``None`` when the object receives no source illumination.
    """
    try:
        object_surface_index = int(object_surface_index)
    except Exception:
        return None
    try:
        samples = editor._source_illumination_hit_samples(
            system, object_surface_index, ray_records=ray_records
        )
    except Exception:
        return None
    x_values = np.asarray(samples.get("x", []), dtype=float)
    if x_values.size == 0:
        return None
    try:
        data = source_illumination_map_data_from_samples(
            samples,
            target_model={"target_surface": object_surface_index, "is_detector": False},
            bins=int(bins),
        )
    except Exception:
        return None
    return {
        "density": np.asarray(data["density"], dtype=float),
        "x_edges": np.asarray(data["x_edges"], dtype=float),
        "y_edges": np.asarray(data["y_edges"], dtype=float),
        "extent": list(data["extent"]),
        "coord": str(samples.get("coord", "world")),
        "hit_count": int(x_values.size),
    }


def sample_irradiance(irradiance_map: dict[str, object] | None, x_local: float, y_local: float) -> float:
    """Nearest-bin sample of the peak-normalized density at object-local ``(x, y)``.

    Returns ``0.0`` for a non-finite coordinate or a point outside the binned extent (no source
    light lands there, so an imaging ray tracing back to it carries no illumination).
    """
    if not irradiance_map:
        return 0.0
    if not (np.isfinite(x_local) and np.isfinite(y_local)):
        return 0.0
    density = np.asarray(irradiance_map["density"], dtype=float)
    x_edges = np.asarray(irradiance_map["x_edges"], dtype=float)
    y_edges = np.asarray(irradiance_map["y_edges"], dtype=float)
    if density.size == 0 or x_edges.size < 2 or y_edges.size < 2:
        return 0.0
    if x_local < x_edges[0] or x_local > x_edges[-1] or y_local < y_edges[0] or y_local > y_edges[-1]:
        return 0.0
    ix = int(np.clip(np.digitize(x_local, x_edges) - 1, 0, density.shape[1] - 1))
    iy = int(np.clip(np.digitize(y_local, y_edges) - 1, 0, density.shape[0] - 1))
    return float(density[iy, ix])


def imaging_ray_object_origin(
    editor: Any, system: Any, object_surface_index: int, record: dict[str, object]
) -> tuple[float, float, bool]:
    """Object-local ``(x, y)`` where an imaging record's ray left the object surface.

    Returns ``(x, y, ok)``.  We take the FIRST hit at the object surface -- the illuminated point
    that scattered / re-emitted toward the imaging optics -- transformed into the SAME surface-local
    frame the source -> object map is binned in (``editor._hit_local_xy``), so origin and map align.
    """
    target = str(int(object_surface_index))
    for hit in (record.get("hits") or []):
        if str(hit.get("surface")) == target:
            x_local, y_local, _coord = editor._hit_local_xy(system, int(object_surface_index), hit)
            if np.isfinite(x_local) and np.isfinite(y_local):
                return float(x_local), float(y_local), True
            break
    return float("nan"), float("nan"), False


def couple_imaging_records(
    editor: Any,
    system: Any,
    object_surface_index: int,
    imaging_records: list[dict[str, object]],
    irradiance_map: dict[str, object] | None,
) -> list[dict[str, object]]:
    """For each imaging record with a valid object origin, return a coupling entry
    ``{record, object_x, object_y, irradiance}``.

    ``irradiance`` in ``[0, 1]`` is the source -> object density at the ray's object origin -- the
    multiplier that imprints the illumination rolloff onto the detector image.
    """
    coupled: list[dict[str, object]] = []
    for record in imaging_records:
        x_local, y_local, ok = imaging_ray_object_origin(editor, system, object_surface_index, record)
        if not ok:
            continue
        coupled.append(
            {
                "record": record,
                "object_x": x_local,
                "object_y": y_local,
                "irradiance": sample_irradiance(irradiance_map, x_local, y_local),
            }
        )
    return coupled


def object_illumination_projection_map(
    editor: Any,
    system: Any,
    object_surface_index: int,
    *,
    ray_records: list[dict[str, object]],
    object_radius: float,
    min_hits: int = 30,
    bins: int | None = None,
) -> dict[str, object] | None:
    """bugs/0286: bin the illumination landing WITHIN the imaged object aperture into a dark-edge
    density map, ready to project onto the sensor.

    Only light inside the object aperture (``object_radius`` mm) is relayed to the sensor by the imaging
    lens, so a source that sprays entirely off-aperture -- e.g. a 45-deg beam-splitter FACE marker whose
    flood lands in an off-axis ring at r ~ 28-44 mm on a 16 mm-radius object -- yields no map, and the
    sensor is correctly left blank (display follows physics; there is genuinely nothing to image). Bins
    over the SURVIVING data footprint (the illumination shape), NOT the whole aperture, so the coaxial
    dark-edge rolloff fills the map instead of shrinking to a central speck ringed by un-illuminated
    aperture. Returns ``{density, x_edges, y_edges, extent, coord, hit_count}`` (``density`` is
    ``[iy, ix]``, peak-normalized) or ``None`` when too little illumination reaches the imaged FOV.
    """
    try:
        object_surface_index = int(object_surface_index)
    except Exception:
        return None
    try:
        samples = editor._source_illumination_hit_samples(
            system, object_surface_index, ray_records=ray_records
        )
    except Exception:
        return None
    x_values = np.asarray(samples.get("x", []), dtype=float)
    y_values = np.asarray(samples.get("y", []), dtype=float)
    if x_values.size == 0 or y_values.size != x_values.size:
        return None
    if object_radius and float(object_radius) > 0.0:
        keep = np.hypot(x_values, y_values) <= float(object_radius)
    else:
        keep = np.ones(x_values.shape, dtype=bool)
    kept = int(np.count_nonzero(keep))
    if kept < int(min_hits):
        return None
    clipped = dict(samples)
    clipped["x"] = x_values[keep]
    clipped["y"] = y_values[keep]
    weights = np.asarray(samples.get("weights", []), dtype=float)
    if weights.size == x_values.size:
        clipped["weights"] = weights[keep]
    # Reindex the per-hit source id/name lists to the SAME clip, else source_illumination_map_data_from_samples'
    # centroid loop indexes a full-length list with the clipped-length mask -> IndexError (the LED case never
    # tripped this because its flood lands wholly inside the aperture, so nothing was clipped away).
    keep_list = keep.tolist()
    for key in ("source_ids", "source_names"):
        seq = samples.get(key)
        if isinstance(seq, (list, tuple)) and len(seq) == x_values.size:
            clipped[key] = [value for value, flag in zip(seq, keep_list) if flag]
    if bins is None:
        # coarse enough that each occupied bin is well populated (the illumination footprint, not the
        # whole aperture, so ~10 hits/bin over the surviving data) yet fine enough to show the rolloff.
        bins = int(np.clip(round(np.sqrt(kept / 12.0)), 6, 20))
    try:
        data = source_illumination_map_data_from_samples(
            clipped,
            target_model={"target_surface": object_surface_index, "is_detector": False},
            bins=int(bins),
        )
    except Exception:
        return None
    return {
        "density": np.asarray(data["density"], dtype=float),
        "x_edges": np.asarray(data["x_edges"], dtype=float),
        "y_edges": np.asarray(data["y_edges"], dtype=float),
        "extent": list(data["extent"]),
        "coord": str(samples.get("coord", "world")),
        "hit_count": kept,
    }


def _terminal_ray(record: dict[str, object]) -> tuple[np.ndarray, np.ndarray] | None:
    """``(origin, unit direction)`` of a record's LAST traced segment, or ``None``.

    Three tiers, best first: the engine-traced ``traced_polyline_world`` (bugs/0272 -- it includes the
    refracted terminal free-flight point, so the direction is the true post-exit one), else the last two
    surface ``hits``, else the launch origin + launch direction (a ray that never met a surface).
    ``origin`` is the LAST REAL interaction point, so "the object plane is ahead" is a clean ``t > 0``.
    """
    poly = record.get("traced_polyline_world")
    points: np.ndarray | None = None
    if poly is not None:
        candidate = np.asarray(poly, dtype=float)
        if candidate.ndim == 2 and candidate.shape[0] >= 2 and candidate.shape[1] == 3:
            points = candidate
    if points is None:
        hits = record.get("hits")
        if isinstance(hits, list) and len(hits) >= 2:
            try:
                points = np.asarray(
                    [[float(h["x"]), float(h["y"]), float(h["z"])] for h in hits[-2:]], dtype=float
                )
            except Exception:
                points = None
    if points is not None:
        origin = points[-2]
        delta = points[-1] - points[-2]
        norm = float(np.linalg.norm(delta))
        if norm > 1e-12 and np.all(np.isfinite(origin)) and np.all(np.isfinite(delta)):
            return origin, delta / norm
    try:
        origin = np.array(
            [float(record["source_x"]), float(record["source_y"]), float(record["source_z"])], dtype=float
        )
        delta = np.array(
            [float(record["source_l"]), float(record["source_m"]), float(record["source_n"])], dtype=float
        )
    except Exception:
        return None
    norm = float(np.linalg.norm(delta))
    if norm <= 1e-12 or not (np.all(np.isfinite(origin)) and np.all(np.isfinite(delta))):
        return None
    return origin, delta / norm


# bugs/0289: terminations that mean "the trace ran out of surfaces while the ray was still flying" --
# the ONLY states the geometric relay may continue. Everything else (absorb, the bugs/0179 UDA
# aperture-stop vignette, hard-stop targets, detector hits) means the ray ENDED ON something and its
# light must not be extended through it. Matches the taxonomy in layout_plot_controller's
# RAY_EVENT_ACTION_LABELS (the Miss/Escape families).
_FREE_FLIGHT_TERMINATIONS = frozenset(
    {"no_next_intersection", "no_hit", "escape", "escaped", "miss", "missed_image", "missed_detector"}
)


def object_plane_illumination_samples(
    editor: Any,
    system: Any,
    object_surface_index: int,
    *,
    ray_records: list[dict[str, object]],
    object_plane_z: float,
    object_radius: float,
    clip_radius: float | None = None,
    plane_tolerance_mm: float = 1e-3,
) -> dict[str, object]:
    """bugs/0288: the illumination that actually reaches the OBJECT PLANE, in the object surface's local
    frame, gathered by two scene-derived mechanisms.

    DIRECT -- an event recorded ON the object surface whose WORLD position really lies on the object
    plane.  The plane test is load-bearing: KrakenOS records a scene source's LAUNCH as an object-surface
    (index 0) event wherever the emitter sits, so without it a coaxial LED parked at the beam splitter
    (z ~ 230 mm, x ~ 90 mm) gets binned as "illumination on the object".  With it, only an emitter that
    genuinely sits on the object plane contributes directly -- the physical statement "this patch of the
    object is self-luminous".

    RELAY -- otherwise geometrically continue the record's terminal traced segment onto the object plane.
    This is the bugs/0287 trace-order-wall bypass: KrakenOS traces in SURFACE-INDEX order, so a flood
    reflecting off a beam splitter (a LATER index) back toward the object (surface 0) runs backward
    through the surface list and is never re-tested against it.  The engine still hands us the ray's true
    outgoing direction, so we complete the last leg ourselves.  Only a ray whose trace ended in FREE
    FLIGHT may be relayed (bugs/0289): a ray that ended ON something -- absorbed at a mechanical face,
    vignetted at an aperture stop (the bugs/0179 UDA block), stopped at a hard-stop target -- deposits its
    light there, and extending it would shine THROUGH the blocker.  A terminal segment that does not
    cross the plane going forward is skipped; near-parallel blow-ups (``|d_z| -> 0`` throws the
    intersection out to ~1e5 mm) fall out at the aperture clip below rather than needing a magic
    distance cut.

    Only light the imaging lens can relay to the sensor matters, so samples are clipped radially.
    ``clip_radius`` (bugs/0289) is the caller's IMAGED-FOV bound -- the sensor half-diagonal divided by
    the paraxial magnification, padded so the binned data extends past the projection window (a clip AT
    the window would leave the boundary bin half-filled and fake a dark rim on an over-filling flood).
    The vendor MV-150 exposed why this must not be the object ROW radius: the row's 32.6 mm disc is
    SMALLER than the 39 mm square the lens actually images (row diameter is a drawing/launch extent,
    not a baffle), so clipping there erased real illumination inside the imaged FOV and would carve a
    fabricated radial rim onto any large footprint.  ``object_radius`` remains the fallback bound when
    the caller has no conjugate.  Light that lands outside the imaged FOV but inside the clip is
    harmless: the sensor projection never samples it, and a footprint living entirely off-window (the
    bugs/0286 marked-45-deg-face ring) dies at the projection's peak gate.  Returns a
    ``source_illumination_map_data_from_samples``-shaped samples dict plus ``direct_count`` /
    ``relayed_count`` diagnostics.
    """
    try:
        object_surface_index = int(object_surface_index)
    except Exception:
        object_surface_index = -1
    target = str(object_surface_index)
    plane_z = float(object_plane_z)
    tol = abs(float(plane_tolerance_mm))
    bound = float(clip_radius) if clip_radius and float(clip_radius) > 0.0 else float(object_radius or 0.0)

    xs: list[float] = []
    ys: list[float] = []
    weights: list[float] = []
    source_ids: list[str] = []
    source_names: list[str] = []
    direct_count = 0
    relayed_count = 0

    def _weight(record: dict[str, object]) -> float:
        try:
            value = float(record.get("source_weight", 1.0))
        except Exception:
            return 1.0
        return value if np.isfinite(value) and value > 0.0 else 1.0

    def _local_xy(hit: dict[str, object]) -> tuple[float, float]:
        try:
            x_local, y_local, _coord = editor._hit_local_xy(system, object_surface_index, hit)
            return float(x_local), float(y_local)
        except Exception:
            return float("nan"), float("nan")

    for record in ray_records or []:
        hit_xy: tuple[float, float] | None = None

        # DIRECT: an object-surface event that genuinely sits on the object plane.
        for hit in (record.get("hits") or []):
            if str(hit.get("surface")) != target:
                continue
            try:
                hit_z = float(hit.get("z"))
            except Exception:
                break
            if abs(hit_z - plane_z) > tol:
                break  # a launch event parked off the object plane -- not object illumination
            candidate = _local_xy(hit)
            if np.isfinite(candidate[0]) and np.isfinite(candidate[1]):
                hit_xy = candidate
                direct_count += 1
            break

        # RELAY: complete the terminal segment onto the object plane -- but only for a ray whose trace
        # ended in FREE FLIGHT. Anything that ended ON a surface (absorb, UDA vignette, hard-stop,
        # detector) deposited its light there; extending it would shine through the blocker.
        if hit_xy is None:
            termination = str(record.get("termination", "")).strip().lower()
            if termination not in _FREE_FLIGHT_TERMINATIONS:
                continue
            terminal = _terminal_ray(record)
            if terminal is None:
                continue
            origin, direction = terminal
            if abs(direction[2]) < 1e-12:
                continue
            travel = (plane_z - origin[2]) / direction[2]
            if travel <= tol:
                continue  # the object plane is behind (or at) the ray's last interaction
            landing = origin + travel * direction
            candidate = _local_xy({"x": landing[0], "y": landing[1], "z": landing[2]})
            if not (np.isfinite(candidate[0]) and np.isfinite(candidate[1])):
                continue
            hit_xy = candidate
            relayed_count += 1

        if hit_xy is None:
            continue
        if bound > 0.0 and float(np.hypot(hit_xy[0], hit_xy[1])) > bound:
            continue
        xs.append(hit_xy[0])
        ys.append(hit_xy[1])
        weights.append(_weight(record))
        source_ids.append(str(record.get("source_id", "") or ""))
        source_names.append(str(record.get("source_name", "") or ""))

    return {
        "x": np.asarray(xs, dtype=float),
        "y": np.asarray(ys, dtype=float),
        "weights": np.asarray(weights, dtype=float),
        "source_ids": source_ids,
        "source_names": source_names,
        "coord": "local",
        "target_surface": object_surface_index,
        "target_name": "",
        "direct_count": int(direct_count),
        "relayed_count": int(relayed_count),
    }


def object_footprint_irradiance_map(
    samples: dict[str, object] | None,
    object_surface_index: int,
    *,
    min_hits: int = 30,
    bins: int | None = None,
) -> dict[str, object] | None:
    """bugs/0288: bin object-plane illumination samples over their OWN footprint into a smooth,
    peak-normalized irradiance map -- the "limited projected area".

    Binning over the surviving data footprint (not the whole aperture) keeps the rolloff resolved rather
    than shrinking it to a central speck ringed by empty aperture bins; the footprint's TRUE extent rides
    in ``x_edges`` / ``y_edges`` so the projection can place it at real scale.  Returns ``None`` when too
    little illumination reaches the imaged aperture.
    """
    if not isinstance(samples, dict):
        return None
    x_values = np.asarray(samples.get("x", []), dtype=float)
    y_values = np.asarray(samples.get("y", []), dtype=float)
    if x_values.size == 0 or y_values.size != x_values.size or x_values.size < int(min_hits):
        return None
    if bins is None:
        # coarse enough that each occupied bin is well populated (~12 hits/bin over the surviving data),
        # fine enough to show the rolloff -- the bugs/0286 adaptive rule.
        bins = int(np.clip(round(np.sqrt(x_values.size / 12.0)), 6, 20))
    try:
        data = source_illumination_map_data_from_samples(
            samples,
            target_model={"target_surface": int(object_surface_index), "is_detector": False},
            bins=int(bins),
        )
    except Exception:
        return None
    return {
        "density": np.asarray(data["density"], dtype=float),
        "x_edges": np.asarray(data["x_edges"], dtype=float),
        "y_edges": np.asarray(data["y_edges"], dtype=float),
        "extent": list(data["extent"]),
        "coord": str(samples.get("coord", "local")),
        "hit_count": int(x_values.size),
        "direct_count": int(samples.get("direct_count", 0) or 0),
        "relayed_count": int(samples.get("relayed_count", 0) or 0),
    }


def _bilinear_zero_outside(
    density: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray, xq: np.ndarray, yq: np.ndarray
) -> np.ndarray:
    """Bilinear sample of ``density`` (``[iy, ix]``) at query points, decaying to 0 outside its extent.

    The grid is padded with a ring of zero bins first, so a query just past the outermost bin CENTRE
    ramps smoothly down to 0 instead of stepping off a cliff.  That ramp is the soft penumbra at the edge
    of the illuminated footprint -- the user asked for a soft roll-off, not a hard mask.
    """
    ny, nx = density.shape
    if nx < 1 or ny < 1:
        return np.zeros_like(xq, dtype=float)
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    dx = float(x_edges[1] - x_edges[0])
    dy = float(y_edges[1] - y_edges[0])
    if not (dx > 0.0 and dy > 0.0):
        return np.zeros_like(xq, dtype=float)
    xc = np.concatenate(([xc[0] - dx], xc, [xc[-1] + dx]))
    yc = np.concatenate(([yc[0] - dy], yc, [yc[-1] + dy]))
    padded = np.zeros((ny + 2, nx + 2), dtype=float)
    padded[1:-1, 1:-1] = density

    ix = np.clip(np.searchsorted(xc, xq) - 1, 0, xc.size - 2)
    iy = np.clip(np.searchsorted(yc, yq) - 1, 0, yc.size - 2)
    tx = np.clip((xq - xc[ix]) / dx, 0.0, 1.0)
    ty = np.clip((yq - yc[iy]) / dy, 0.0, 1.0)
    out = (
        padded[iy, ix] * (1.0 - tx) * (1.0 - ty)
        + padded[iy, ix + 1] * tx * (1.0 - ty)
        + padded[iy + 1, ix] * (1.0 - tx) * ty
        + padded[iy + 1, ix + 1] * tx * ty
    )
    outside = (xq < xc[0]) | (xq > xc[-1]) | (yq < yc[0]) | (yq > yc[-1])
    return np.where(outside, 0.0, out)


def project_footprint_onto_sensor(
    map_data: dict[str, object] | None,
    magnification: float | None,
    sensor_half_w: float,
    sensor_half_h: float,
    *,
    bins: int | None = None,
) -> dict[str, object] | None:
    """bugs/0288: draw the object-plane illumination footprint on the sensor at its TRUE imaged size.

    The lens images object point ``(x, y)`` onto sensor point ``m*(x, y)``, so sampling the object
    footprint at ``o = s/|m|`` for every sensor cell ``s`` paints the illuminated region at its real scale
    and leaves the rest of the sensor DARK.  That dark surround IS the answer to "show dark edges if they
    exist": a footprint that under-fills the imaged FOV reads dark at the rim, one that over-fills it
    reads uniform.  The geometry decides -- there is no explicit gate and no tuned constant.

    Contrast ``project_object_map_onto_sensor`` (bugs/0286), which rescales the footprint's own edges to
    the sensor half-extent and therefore ALWAYS fills the sensor, hiding any under-fill.  That stretch is
    what drew a 10 mm object patch as a full-sensor radial bowl (flags 170554_093 / 170627_720).

    ``magnification`` is the scene's own paraxial conjugate, so nothing here is tuned to a layout.
    Returns ``None`` on a degenerate input, or when the imaged footprint misses the sensor entirely.
    """
    if not isinstance(map_data, dict) or magnification is None:
        return None
    try:
        m = abs(float(magnification))
    except Exception:
        return None
    hw = float(sensor_half_w)
    hh = float(sensor_half_h)
    if not (np.isfinite(m) and m > 1e-9 and hw > 0.0 and hh > 0.0):
        return None
    density = np.asarray(map_data.get("density"), dtype=float)
    x_edges = np.asarray(map_data.get("x_edges"), dtype=float)
    y_edges = np.asarray(map_data.get("y_edges"), dtype=float)
    if density.ndim != 2 or density.size == 0 or x_edges.size < 2 or y_edges.size < 2:
        return None

    if bins is None:
        # Resolve the footprint at roughly its own bin pitch once imaged onto the sensor: a footprint
        # covering a small part of the sensor needs proportionally more sensor bins to stay smooth.
        footprint_half_x = 0.5 * float(x_edges[-1] - x_edges[0]) * m
        footprint_half_y = 0.5 * float(y_edges[-1] - y_edges[0]) * m
        scale = max(hw / max(footprint_half_x, 1e-9), hh / max(footprint_half_y, 1e-9))
        native = max(density.shape[0], density.shape[1])
        bins = int(np.clip(round(native * scale), 12, 48))

    sensor_x_edges = np.linspace(-hw, hw, int(bins) + 1)
    sensor_y_edges = np.linspace(-hh, hh, int(bins) + 1)
    sensor_xc = 0.5 * (sensor_x_edges[:-1] + sensor_x_edges[1:])
    sensor_yc = 0.5 * (sensor_y_edges[:-1] + sensor_y_edges[1:])
    grid_x, grid_y = np.meshgrid(sensor_xc, sensor_yc)  # [iy, ix]
    values = _bilinear_zero_outside(density, x_edges, y_edges, grid_x / m, grid_y / m)
    peak = float(np.max(values)) if values.size else 0.0
    if not (peak > 0.0):
        return None  # the imaged footprint misses the sensor entirely
    return {
        "density": values / peak,
        "x_edges": sensor_x_edges,
        "y_edges": sensor_y_edges,
        "extent": [-hw, hw, -hh, hh],
        "coord": str(map_data.get("coord", "local")),
        "hit_count": int(map_data.get("hit_count", 0)),
    }


def project_object_map_onto_sensor(
    map_data: dict[str, object] | None,
    sensor_half_w: float,
    sensor_half_h: float,
) -> dict[str, object] | None:
    """bugs/0286: rescale an object-illumination map's grid edges to the SENSOR active extent so the
    dark-edge pattern draws at the true sensor size.

    The density grid (the pattern) is untouched -- only the spatial edges are remapped to
    ``[-half, +half]`` per axis, baking in the object -> sensor imaging conjugate as a uniform fill of
    the sensor square. Sizing from the sensor's own half-extent (not the object/FOV footprint) is what
    avoids the bugs/0275 trap of drawing the heatmap quad at the FOV size instead of the sensor size.
    Returns a ``build_source_illumination_overlay``-ready map, or ``None`` on a degenerate input.
    """
    if not isinstance(map_data, dict):
        return None
    density = np.asarray(map_data.get("density"), dtype=float)
    if density.ndim != 2 or density.size == 0:
        return None
    hw = float(sensor_half_w)
    hh = float(sensor_half_h)
    if not (hw > 0.0 and hh > 0.0):
        return None
    ny, nx = density.shape
    return {
        "density": density,
        "x_edges": np.linspace(-hw, hw, nx + 1),
        "y_edges": np.linspace(-hh, hh, ny + 1),
        "extent": [-hw, hw, -hh, hh],
        "coord": str(map_data.get("coord", "local")),
        "hit_count": int(map_data.get("hit_count", 0)),
    }
