"""Shared dimension-annotation geometry for the 3D STEP export (bugs/0316).

The STEP writer (``cad_step_export._write_step_with_cad_shapes_and_rays``) turns
each ``dimension_polylines`` entry into solid tubes by walking its consecutive
segments (``for start, end in zip(pts[:-1], pts[1:])``). Before 0316 the two
dimension overlays emitted only the shaft + two leader lines, so the exported
STEP showed *"only lines, no arrow, no text"* (flag_20260715_125033_313).

This module produces the MISSING pieces as ordinary multi-point polylines so
they ride the exact same tubing path with no writer change:

* open-chevron **arrowheads** at both ends (barb lines, like the on-screen cone
  heads but stroked so the segment-tuber renders them), and
* the numeric **value text** as a vector stroke font (the pythonocc build here
  has no ``OCC.Core.Font``, and per the project's tooling rule we add no external
  font dependency -- a hand-rolled stroke font stays fully in-process).

``dimension_annotation_polylines`` is the single funnel both the blue
physical-distance overlay (``open3d_thickness_dimensions._record_export_dimension``)
and the orange Measure tool (``open3d_inspector.collect_measure_export_geometry``)
call, so the exported STEP tracks the on-screen dimension for BOTH annotation
types. The first three returned polylines are STABLE (shaft, leader, leader) and
byte-for-byte the pre-0316 output, so existing endpoint assertions still hold.
"""

from __future__ import annotations

import numpy as np

# Vector stroke font -----------------------------------------------------------
# Each glyph is a list of strokes; each stroke is a polyline of (x, y) points in
# a unit cell: x in [0, GLYPH_WIDTH], y in [0, 1] with the baseline at y=0.
GLYPH_WIDTH = 0.6
_W = GLYPH_WIDTH

# Seven-segment skeleton -- unambiguous, compact, trivially legible once tubed.
_SEG = {
    "A": [(0.0, 1.0), (_W, 1.0)],   # top
    "B": [(_W, 1.0), (_W, 0.5)],    # upper right
    "C": [(_W, 0.5), (_W, 0.0)],    # lower right
    "D": [(0.0, 0.0), (_W, 0.0)],   # bottom
    "E": [(0.0, 0.5), (0.0, 0.0)],  # lower left
    "F": [(0.0, 1.0), (0.0, 0.5)],  # upper left
    "G": [(0.0, 0.5), (_W, 0.5)],   # middle
}
_DIGIT_SEGMENTS = {
    "0": "ABCDEF",
    "1": "BC",
    "2": "ABGED",
    "3": "ABCDG",
    "4": "FGBC",
    "5": "AFGCD",
    "6": "AFGEDC",
    "7": "ABC",
    "8": "ABCDEFG",
    "9": "ABCDFG",
}

GLYPHS: "dict[str, list[list[tuple[float, float]]]]" = {
    digit: [list(_SEG[name]) for name in segments]
    for digit, segments in _DIGIT_SEGMENTS.items()
}
GLYPHS["."] = [[(_W * 0.5, 0.0), (_W * 0.5, 0.14)]]      # short stub -> reads as a dot
GLYPHS[" "] = []
GLYPHS["-"] = [list(_SEG["G"])]
GLYPHS["+"] = [list(_SEG["G"]), [(_W * 0.5, 0.25), (_W * 0.5, 0.75)]]
GLYPHS["m"] = [
    [(0.0, 0.0), (0.0, 0.6)],           # left stem
    [(0.0, 0.6), (_W, 0.6)],            # top bar
    [(_W * 0.5, 0.6), (_W * 0.5, 0.0)],  # middle stem
    [(_W, 0.6), (_W, 0.0)],             # right stem
]
GLYPHS["e"] = [[(_W, 0.42), (0.0, 0.42), (0.0, 0.12), (_W, 0.12), (_W, 0.28), (0.0, 0.28)]]


def _unit(vec) -> "np.ndarray | None":
    arr = np.asarray(vec, dtype=float).reshape(3)
    norm = float(np.linalg.norm(arr))
    if not np.isfinite(norm) or norm <= 1e-9:
        return None
    return arr / norm


def _perpendicular(direction) -> np.ndarray:
    """A unit vector orthogonal to ``direction`` (deterministic, view-free)."""
    d = _unit(direction)
    if d is None:
        return np.array([0.0, 1.0, 0.0])
    ref = np.array([0.0, 1.0, 0.0])
    if abs(float(np.dot(ref, d))) > 0.9:
        ref = np.array([1.0, 0.0, 0.0])
    perp = _unit(ref - float(np.dot(ref, d)) * d)
    return perp if perp is not None else np.array([0.0, 1.0, 0.0])


def dimension_value_text(span: float) -> str:
    """The label the exported dimension carries -- the numeric span, e.g. ``"32.92 mm"``."""
    return f"{abs(float(span)):.4g} mm"


def stroke_text_polylines(text, origin, x_dir, y_dir, height, *, center=True) -> "list[np.ndarray]":
    """Render ``text`` as world-space stroke polylines in the plane (x_dir, y_dir).

    ``origin`` is the baseline point; when ``center`` the string is centered on it
    along ``x_dir``. Each glyph stroke becomes one polyline (>=2 points)."""
    origin = np.asarray(origin, dtype=float).reshape(3)
    xd = _unit(x_dir)
    yd = _unit(y_dir)
    if xd is None or yd is None or not np.isfinite(height) or height <= 0.0:
        return []
    advance = (GLYPH_WIDTH + 0.28) * float(height)
    cursor = -0.5 * advance * max(len(text), 1) if center else 0.0
    out: "list[np.ndarray]" = []
    for ch in text:
        for stroke in GLYPHS.get(ch, ()):  # unknown chars advance but draw nothing
            pts = [
                origin + xd * (cursor + cx * height) + yd * (cy * height)
                for (cx, cy) in stroke
            ]
            if len(pts) >= 2:
                out.append(np.asarray(pts, dtype=float).reshape(-1, 3))
        cursor += advance
    return out


def arrowhead_barb_polylines(start, end, out_dir, span) -> "list[np.ndarray]":
    """Open-chevron arrowheads (a barb polyline per end), tips at ``start``/``end``."""
    a = np.asarray(start, dtype=float).reshape(3)
    b = np.asarray(end, dtype=float).reshape(3)
    shaft = _unit(b - a)
    if shaft is None:
        return []
    od = _unit(out_dir)
    if od is None:
        od = _perpendicular(shaft)
    head = float(min(max(float(span) * 0.06, 2.0), 12.0))
    wing = head * 0.45
    barbs: "list[np.ndarray]" = []
    for tip, into in ((a, shaft), (b, -shaft)):
        b1 = tip + into * head + od * wing
        b2 = tip + into * head - od * wing
        barbs.append(np.asarray([b1, tip, b2], dtype=float).reshape(3, 3))
    return barbs


def dimension_annotation_polylines(base_lo, base_hi, start, end, *, value=None) -> "list[np.ndarray]":
    """Full export geometry for ONE dimension: shaft + two leaders (STABLE first
    three), then open-chevron arrowheads and the numeric value text.

    ``base_lo``/``base_hi`` are the two measured (surface) points; ``start``/``end``
    are the offset dimension-line endpoints the shaft is drawn between -- the exact
    same four points the on-screen overlay uses. Every returned entry is a 2-or-more
    point polyline the STEP writer tubes segment-by-segment, so the arrowheads and
    text need no writer or plumbing change."""
    lo = np.asarray(base_lo, dtype=float).reshape(3)
    hi = np.asarray(base_hi, dtype=float).reshape(3)
    a = np.asarray(start, dtype=float).reshape(3)
    b = np.asarray(end, dtype=float).reshape(3)

    def _seg(p, q) -> np.ndarray:
        return np.asarray([p, q], dtype=float).reshape(2, 3)

    # STABLE trio -- identical order/endpoints to the pre-0316 collectors.
    polylines: "list[np.ndarray]" = [_seg(a, b), _seg(lo, a), _seg(hi, b)]

    shaft = _unit(b - a)
    span = float(np.linalg.norm(b - a))
    if shaft is None or span <= 1e-9:
        return polylines  # degenerate dimension: keep the trio, nothing to annotate

    out_dir = _unit(a - lo)
    if out_dir is None:
        out_dir = _perpendicular(shaft)

    polylines.extend(arrowhead_barb_polylines(a, b, out_dir, span))

    text = str(value) if value is not None else dimension_value_text(span)
    height = float(min(max(span * 0.10, 3.0), 12.0))
    head = float(min(max(span * 0.06, 2.0), 12.0))
    mid = (a + b) * 0.5
    origin = mid + out_dir * (head + height * 0.5)  # sit the label clear of the barbs
    polylines.extend(stroke_text_polylines(text, origin, shaft, out_dir, height))
    return polylines


# Number of polylines a NON-degenerate dimension contributes for a given value
# string -- used by the guards so their counts track the font, not a magic number.
STABLE_PREFIX = 3  # shaft + two leaders


def annotation_polyline_count(value_text: str) -> int:
    """How many polylines ``dimension_annotation_polylines`` yields for ``value_text``
    (trio + 2 barbs + the stroke count of the text)."""
    strokes = sum(len(GLYPHS.get(ch, ())) for ch in value_text)
    return STABLE_PREFIX + 2 + strokes
