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
