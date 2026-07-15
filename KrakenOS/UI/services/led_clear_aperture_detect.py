"""LED clear-aperture opening auto-detect (bugs/0319 C2).

The one-click "Add Beam Splitter to LED" pipeline must centre the beam splitter
on the LED module's clear-aperture *opening* -- the square rounded-corner window
on the front of the vendor STEP that the user otherwise picks by hand
(``STEP_CLEAR_APERTURE_PICK``, bugs/0134).  This module auto-detects that opening
from the STEP's analytic faces so the pipeline can pre-fill the pick, with the
manual pick kept as the dependable fallback.

Domain facts (grounded on the real ``attachment/LED/OPT-CO90-X-V1.6.2-H.STEP``):
  * The opening is a **planar** face whose bbox is a thin flat window (the plane's
    extent along its own normal is ~0).
  * It is a **rim around a hole**: the planar face area is only a fraction of its
    in-plane bbox (a ~2 mm frame around a ~51 mm square hole => bbox_fill ~0.15),
    which cleanly separates it from solid housing panels (bbox_fill ~1).
  * It is **window-sized** (tens of mm) and faces roughly along a principal axis.
  * An LED STEP that *already carries a BS* has **two** such openings; the bare
    coaxial illuminator has one.  The detector returns every qualifying opening,
    ranked, so the caller can pick the best or let the user disambiguate.

The scorer is pure geometry (no OCC, no editor), so it is unit-testable with
synthetic faces and directly checkable against the real LED STEP's analytic faces.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- opening signature gates (mm / dimensionless), grounded on OPT-CO90 -------
MIN_SPAN_MM = 15.0          # a clear-aperture window is at least this wide
MAX_SPAN_MM = 90.0          # ... and no wider than this (excludes big housing panels)
MAX_PLANE_THICKNESS_MM = 1.5  # a planar face's bbox is ~flat along its own normal
MIN_BBOX_FILL = 0.03        # below this it is a sliver, not a frame
MAX_BBOX_FILL = 0.55        # above this it is a solid panel, not an opening rim
AXIS_ALIGNED_MIN = 0.95     # |max normal component| above this = principal-axis facing
MIN_SCORE = 0.50            # a candidate must clear this to be reported


@dataclass(frozen=True)
class ClearApertureCandidate:
    """One detected clear-aperture opening, ranked by :func:`score_clear_aperture_faces`."""

    face_index: int
    centroid: tuple[float, float, float]
    normal: tuple[float, float, float]
    area_mm2: float
    span_mm: tuple[float, float]
    bbox_fill: float
    squareness: float
    axis_aligned: bool
    score: float


def _bbox_extents(bbox) -> np.ndarray:
    arr = np.asarray(bbox, dtype=float).reshape(-1)
    if arr.size < 6 or not np.all(np.isfinite(arr[:6])):
        return np.asarray((np.nan, np.nan, np.nan), dtype=float)
    return np.maximum(arr[3:6] - arr[0:3], 0.0)


def _face_record(face_index: int, centroid, normal, area_mm2, bbox) -> dict[str, object] | None:
    """Normalise one face into the record schema the scorer consumes, or None."""
    try:
        fid = int(face_index)
    except Exception:
        return None
    try:
        c = np.asarray(centroid, dtype=float).reshape(-1)[:3]
        n = np.asarray(normal, dtype=float).reshape(-1)[:3]
        area = float(area_mm2)
    except Exception:
        return None
    if c.size < 3 or n.size < 3 or not np.all(np.isfinite(c)) or not np.all(np.isfinite(n)):
        return None
    if not np.isfinite(area) or area <= 0.0:
        return None
    extents = _bbox_extents(bbox)
    if not np.all(np.isfinite(extents)):
        return None
    return {
        "face_index": fid,
        "centroid": (float(c[0]), float(c[1]), float(c[2])),
        "normal": (float(n[0]), float(n[1]), float(n[2])),
        "area_mm2": area,
        "extents": extents,
    }


def _score_record(record: dict[str, object]) -> ClearApertureCandidate | None:
    extents = np.asarray(record["extents"], dtype=float)
    ordered = np.sort(extents)          # [thickness, span_a, span_b]
    thickness, span_a, span_b = float(ordered[0]), float(ordered[1]), float(ordered[2])
    # A planar window is ~flat along its own normal (thin bbox in one axis).
    if thickness > MAX_PLANE_THICKNESS_MM:
        return None
    if span_a < MIN_SPAN_MM or span_b > MAX_SPAN_MM:
        return None
    plane_area = span_a * span_b
    if plane_area <= 1e-9:
        return None
    bbox_fill = float(record["area_mm2"]) / plane_area
    # A rim around a hole, not a solid panel and not a sliver.
    if not (MIN_BBOX_FILL < bbox_fill < MAX_BBOX_FILL):
        return None
    squareness = span_a / span_b if span_b > 1e-9 else 0.0
    normal = np.abs(np.asarray(record["normal"], dtype=float))
    axis_component = float(normal.max()) if normal.size else 0.0
    axis_aligned = axis_component > AXIS_ALIGNED_MIN
    # Score: openness (thin rim) dominates, then squareness, then a principal-axis
    # facing bonus -- all normalised to ~[0, 1].
    openness = float(np.clip(1.0 - bbox_fill, 0.0, 1.0))
    axis_bonus = float(np.clip((axis_component - 0.5) / 0.5, 0.0, 1.0))
    score = 0.45 * openness + 0.30 * squareness + 0.25 * axis_bonus
    if score < MIN_SCORE:
        return None
    return ClearApertureCandidate(
        face_index=int(record["face_index"]),
        centroid=tuple(float(v) for v in record["centroid"]),
        normal=tuple(float(v) for v in record["normal"]),
        area_mm2=float(record["area_mm2"]),
        span_mm=(span_a, span_b),
        bbox_fill=bbox_fill,
        squareness=squareness,
        axis_aligned=axis_aligned,
        score=score,
    )


def score_clear_aperture_faces(faces) -> list[ClearApertureCandidate]:
    """Rank clear-aperture opening candidates (best first).

    ``faces`` is an iterable of mappings with ``face_index``, ``centroid``,
    ``normal``, ``area_mm2`` and ``bbox`` (min-xyz, max-xyz).  Faces that fail the
    opening gates are dropped; the rest are returned sorted by descending score
    then descending area (a stable, deterministic order for the caller)."""
    candidates: list[ClearApertureCandidate] = []
    for face in faces or ():
        try:
            record = _face_record(
                face["face_index"], face["centroid"], face["normal"], face["area_mm2"], face["bbox"]
            )
        except (KeyError, TypeError):
            record = None
        if record is None:
            continue
        scored = _score_record(record)
        if scored is not None:
            candidates.append(scored)
    candidates.sort(key=lambda c: (c.score, c.area_mm2), reverse=True)
    return candidates


def clear_aperture_face_records_from_analytic_faces(analytic_faces) -> list[dict[str, object]]:
    """Build scorer records from ``StepAnalyticDocument.outer_faces``.

    The enumeration index is used as ``face_index`` -- it equals the STEP overlay's
    *selection* face index for non-axisymmetric faces (a square/rectangular opening
    is never collapsed by the axisymmetric grouping), which is exactly what
    ``set_step_clear_aperture`` consumes."""
    records: list[dict[str, object]] = []
    for face_index, face in enumerate(analytic_faces or ()):
        if str(getattr(face, "surface_type", "")) != "plane":
            continue
        records.append(
            {
                "face_index": int(face_index),
                "centroid": tuple(getattr(face, "centroid", (0.0, 0.0, 0.0))),
                "normal": tuple(getattr(face, "normal", (0.0, 0.0, 1.0))),
                "area_mm2": float(getattr(face, "area_mm2", 0.0)),
                "bbox": tuple(getattr(face, "bbox", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))),
            }
        )
    return records


def detect_clear_aperture_openings_from_analytic_faces(analytic_faces) -> list[ClearApertureCandidate]:
    """Convenience: analytic outer faces -> ranked clear-aperture candidates."""
    return score_clear_aperture_faces(clear_aperture_face_records_from_analytic_faces(analytic_faces))
