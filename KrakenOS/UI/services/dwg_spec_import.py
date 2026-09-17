"""Vendor DWG -> lens spec, read from TEXT entities rather than recognised from pixels.

bugs/0790. Some vendors ship the drawing that the datasheet PDF was exported from. That DWG is a
strictly better source than the PDF: its spec table is TEXT with coordinates, so a label pairs
with the value in its own row by GEOMETRY, with no recognition step and nothing to misread. The
SPO TCL4.0X-65DI-5M is the case that forced this -- its PDF flattens the title block so every
label is orphaned from its value (bugs/0565's failure mode), and OCR of the drawing recovers the
labels but not the small isolated value cells (bugs/0788's failure mode), while its DWG carries
all of them.

A fixed-conjugate telecentric sheet also needs the housing length, which such drawings state as a
bare DIMENSION rather than a table row. They state it in a recognisable place, though: a single
horizontal run of dimensions from the object to the sensor, whose first entry is labelled with the
working distance and whose last entry is the mount's flange focal distance. That last entry is the
corroboration -- it must equal a STANDARD flange to a hundredth of a millimetre, which no
coincidence supplies -- and the entries between it and the WD are the housing.

Pure and headless: one ``dwgread`` subprocess, no Tk, no VTK. Optional -- without libredwg every
entry point returns None and the caller refuses exactly as before.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# The mounts whose flange focal distance is a standard, so a dimension equal to one is evidence.
_FLANGE_MM = {"C": 17.526, "CS": 12.526, "TFL": 17.526, "F": 46.5, "EF": 44.0, "T2": 55.0}
_FLANGE_TOL_MM = 0.01
_DWG_TIMEOUT_S = 120
_ROW_TOL_FACTOR = 0.6      # a row is within this fraction of the text height


def dwg_available() -> bool:
    return bool(shutil.which("dwgread"))


def _clean_dwg_text(raw: str) -> str:
    """Strip AutoCAD inline formatting and resolve its symbol escapes."""
    text = str(raw or "")
    text = re.sub(r"\{\\[^;}]*;", "", text)          # {\fArial|b0|i0|c0|p34;  and  {\C3;
    text = text.replace("}", "").replace("\\P", " ")
    text = text.replace("%%C", "Ø").replace("%%c", "Ø")
    text = text.replace("%%P", "±").replace("%%p", "±")
    text = text.replace("%%D", "°").replace("%%d", "°")
    return re.sub(r"\s+", " ", text).strip()


_PAYLOAD_CACHE: "dict[tuple, dict]" = {}


def _dwg_payload(path: str | Path) -> "dict | None":
    """The drawing as libredwg's JSON, memoised on (path, mtime, size); None on any failure.

    bugs/0807: the cardinals, the chain, the iris and the barrel are all read from ONE drawing
    during one import; each used to spawn its own ``dwgread``.
    """
    if not dwg_available():
        return None
    try:
        resolved = Path(path).resolve()
        stat = resolved.stat()
        key = (str(resolved), stat.st_mtime_ns, stat.st_size)
    except OSError:
        return None
    if key in _PAYLOAD_CACHE:
        return _PAYLOAD_CACHE[key]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "dwg.json"
            subprocess.run(["dwgread", "-O", "JSON", "-o", str(out), str(resolved)],
                           check=True, capture_output=True, timeout=_DWG_TIMEOUT_S)
            payload = json.loads(out.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    if len(_PAYLOAD_CACHE) > 8:
        _PAYLOAD_CACHE.clear()
    _PAYLOAD_CACHE[key] = payload
    return payload


def dwg_text_entities(path: str | Path) -> "list[tuple[float, float, float, str]]":
    """``(x, y, height, text)`` for every TEXT/MTEXT in the drawing; ``[]`` on any failure."""
    payload = _dwg_payload(path)
    if payload is None:
        return []
    items: list[tuple[float, float, float, str]] = []
    for obj in payload.get("OBJECTS", []) or []:
        if not isinstance(obj, dict) or obj.get("entity") not in ("TEXT", "MTEXT"):
            continue
        text = _clean_dwg_text(obj.get("text") or obj.get("text_value") or "")
        if not text:
            continue
        point = obj.get("ins_pt") or obj.get("first_alignment_pt") or None
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            x, y = float(point[0]), float(point[1])
            height = float(obj.get("text_height") or obj.get("extents_height") or 3.0)
        except (TypeError, ValueError):
            continue
        if math.isfinite(x) and math.isfinite(y):
            items.append((x, y, max(height, 1e-3), text))
    return items


def _group_rows(items: "list[tuple[float, float, float, str]]") -> "list[list[tuple[float, str]]]":
    """Group ``(x, y, height, text)`` into drawing ROWS, top-down then left-to-right.

    Sequential over a y-sorted list with a per-row tolerance taken from the entries' own text
    height. An earlier version bucketed each entity by ``y / (its own height)``; because the
    divisor then varied per entity, two views 46 mm apart on the sheet hashed into the SAME
    bucket and the conjugate chain could not be read. One grouping, used by every reader here.
    """
    rows: "list[list[tuple[float, str]]]" = []
    current: "list[tuple[float, str]]" = []
    anchor = None
    for x, y, height, text in sorted(items, key=lambda r: (-r[1], r[0])):
        tol = max(height, 1e-3) * _ROW_TOL_FACTOR
        if anchor is None or abs(y - anchor) <= tol:
            current.append((x, text))
            if anchor is None:
                anchor = y
        else:
            rows.append(current)
            current, anchor = [(x, text)], y
    if current:
        rows.append(current)
    return [sorted(row) for row in rows]


def dwg_spec_text(path: str | Path) -> str:
    """The drawing's text rebuilt into reading order -- rows top-down, left to right.

    This is what lets the ordinary datasheet scrapers read a DWG: ``Optical Mgnification`` and its
    ``4.0X`` end up adjacent because they share a row, not because a page-segmentation mode
    happened to keep them together.
    """
    items = dwg_text_entities(path)
    if not items:
        return ""
    return "\n".join(" ".join(t for _x, t in row) for row in _group_rows(items))


def _first(text: str, pattern: str) -> "float | None":
    """The first capture of ``pattern`` in ``text`` as a float, or None."""
    match = re.search(pattern, text)
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _as_float(token: str) -> "float | None":
    match = re.fullmatch(r"[^\d.-]*(-?\d+(?:\.\d+)?)[^\d]*", token.strip())
    if match is None:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def dwg_conjugate_chain(path: str | Path) -> "dict | None":
    """The object-to-sensor dimension run: ``{wd, housing, flange, mount, total}`` or None.

    The run is identified, not guessed: its FIRST entry carries the working distance as a labelled
    dimension (``WD65 ±2``) and its LAST is a bare number equal to a standard mount's flange focal
    distance. Everything between them is the housing. If the last entry matches no standard
    flange, there is no chain -- the drawing is telling us something we cannot verify, and
    bugs/0565's rule applies.
    """
    items = dwg_text_entities(path)
    if not items:
        return None
    best: "dict | None" = None
    for entries in _group_rows(items):
        if len(entries) < 3:
            continue
        head = re.fullmatch(r"(?i)W\.?D\s*(\d+(?:\.\d+)?)\s*±?\s*\d*(?:\.\d+)?", entries[0][1])
        if head is None:
            continue
        wd = _as_float(head.group(1))
        tail = _as_float(entries[-1][1])
        if wd is None or tail is None:
            continue
        mount = next((name for name, ffd in _FLANGE_MM.items()
                      if abs(tail - ffd) <= _FLANGE_TOL_MM), None)
        if mount is None:
            continue
        middles = [_as_float(t) for _x, t in entries[1:-1]]
        if any(v is None or v <= 0.0 for v in middles):
            continue
        housing = float(sum(middles))
        if not (1.0 <= wd <= 5000.0 and 5.0 <= housing <= 2000.0):
            continue
        chain = {"wd": float(wd), "housing": housing, "flange": float(tail),
                 "mount": mount, "total": float(wd) + housing + float(tail)}
        # the longest verified run wins: a drawing may dimension a sub-assembly too
        if best is None or chain["total"] > best["total"]:
            best = chain
    return best


def _point2(value) -> "tuple[float, float] | None":
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            x, y = float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
        if math.isfinite(x) and math.isfinite(y):
            return x, y
    return None


def _linear_dimensions(payload: dict) -> "list[dict]":
    """Every linear dimension: its two extension-line origins, measured value and override text."""
    dims: "list[dict]" = []
    for obj in payload.get("OBJECTS", []) or []:
        if not isinstance(obj, dict) or not str(obj.get("entity", "")).startswith("DIMENSION_"):
            continue
        p1, p2 = _point2(obj.get("xline1_pt")), _point2(obj.get("xline2_pt"))
        try:
            value = float(obj.get("act_measurement"))
        except (TypeError, ValueError):
            continue
        if p1 is None or p2 is None or not math.isfinite(value) or value <= 0.0:
            continue
        dims.append({"p1": p1, "p2": p2, "value": value,
                     "text": _clean_dwg_text(obj.get("user_text") or "")})
    return dims


def _housing_frame(payload: dict, chain: dict) -> "tuple[int, float, float, float] | None":
    """``(axis, front, sign, scale)``: how the drawing lays the lens out.

    ``axis`` is the sheet coordinate (0 = x, 1 = y) the housing is dimensioned along, ``front``
    the sheet coordinate of the housing's FRONT face, ``sign`` the direction into the lens and
    ``scale`` sheet units per millimetre. The housing dimension is the one whose measurement is
    the chain's housing; its front end is the one that shares an extension line with the
    working-distance dimension -- the drawing's own statement of which end faces the object.
    """
    housing = float(chain["housing"])
    dims = _linear_dimensions(payload)
    wd_dims = [d for d in dims if re.match(r"(?i)\s*W\.?\s*D", d["text"])]
    for dim in dims:
        if abs(dim["value"] - housing) > max(0.1, 1e-3 * housing):
            continue
        axis = 0 if abs(dim["p2"][0] - dim["p1"][0]) >= abs(dim["p2"][1] - dim["p1"][1]) else 1
        span = abs(dim["p2"][axis] - dim["p1"][axis])
        if span <= 0.0:
            continue
        tol = max(1e-6, 1e-3 * span)
        for front, rear in ((dim["p1"][axis], dim["p2"][axis]), (dim["p2"][axis], dim["p1"][axis])):
            if any(abs(w[key][axis] - front) <= tol for w in wd_dims for key in ("p1", "p2")):
                return axis, front, (1.0 if rear > front else -1.0), span / dim["value"]
    return None


def _segment_distance(point, a, b) -> float:
    ax, ay = a
    bx, by = b
    px, py = point
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 <= 0.0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


_STOP_LABEL = re.compile(r"(?i)^\s*(?:iris|aperture(?:\s*stop)?|stop)\b")


def dwg_iris_stop(path: str | Path, chain: "dict | None" = None) -> "dict | None":
    """Where the drawing puts the IRIS, in mm behind the housing's front face; None if it does not.

    bugs/0807. For an object-space telecentric lens the iris IS the aperture stop, and a vendor
    drawing that labels it states the one internal position a first-order surrogate needs. Read
    from geometry, not guessed: the label is the text sitting on a LEADER's landing, the position
    is the leader's arrow TIP projected onto the housing axis (``_housing_frame``), and when that
    tip falls inside a dimensioned ring of the housing run -- the SPO TCL4.0X's 11.6 mm iris ring
    -- the stop is the ring's middle, which does not depend on where the draftsman clicked.
    ``{"stop_mm", "tip_mm", "ring_mm", "label"}``.
    """
    payload = _dwg_payload(path)
    if payload is None:
        return None
    chain = chain if chain is not None else dwg_conjugate_chain(path)
    if not chain:
        return None
    frame = _housing_frame(payload, chain)
    if frame is None:
        return None
    axis, front, sign, scale = frame
    housing = float(chain["housing"])
    labels = [(x, y, h, t) for x, y, h, t in dwg_text_entities(path) if _STOP_LABEL.search(t)]
    if not labels:
        return None
    candidates = []
    for obj in payload.get("OBJECTS", []) or []:
        if not isinstance(obj, dict) or obj.get("entity") != "LEADER":
            continue
        points = [p for p in (_point2(q) for q in (obj.get("points") or [])) if p is not None]
        if len(points) < 2:
            continue
        for x, y, height, text in labels:
            distance = _segment_distance((x, y), points[-2], points[-1])
            if distance <= 3.0 * height:
                candidates.append((distance, points[0], text))
    if not candidates:
        return None
    _distance, tip, label = min(candidates, key=lambda c: c[0])

    def along(coordinate: float) -> float:
        return sign * (coordinate - front) / scale

    tip_mm = along(tip[axis])
    if not (0.0 < tip_mm < housing):
        return None
    ring = None
    for dim in _linear_dimensions(payload):
        # measured ALONG the axis (a diameter or a port offset is not a ring of the housing)
        if abs(abs(dim["p2"][axis] - dim["p1"][axis]) / scale - dim["value"]) > max(0.05, 2e-3 * dim["value"]):
            continue
        lo, hi = sorted((along(dim["p1"][axis]), along(dim["p2"][axis])))
        if lo < -1e-6 or hi > housing + 1e-6 or hi - lo >= housing - 1e-6:
            continue
        if lo <= tip_mm <= hi and (ring is None or hi - lo < ring[1] - ring[0]):
            ring = (lo, hi)
    stop_mm = 0.5 * (ring[0] + ring[1]) if ring is not None else tip_mm
    return {"stop_mm": float(stop_mm), "tip_mm": float(tip_mm),
            "ring_mm": (float(ring[0]), float(ring[1])) if ring is not None else None, "label": label}


def dwg_barrel_radius(path: str | Path, *, before_mm: float, chain: "dict | None" = None) -> "float | None":
    """Half the largest COAXIAL diameter the drawing dimensions in front of ``before_mm``.

    bugs/0807: the front group of a telecentric lens has to pass every field's object-side cone,
    and it cannot be wider than the barrel that holds it. A coaxial diameter is measured ACROSS the
    housing axis; a port's diameter (the SPO's Ø16 coaxial-illumination tube) is measured along it
    and is not counted.
    """
    payload = _dwg_payload(path)
    if payload is None:
        return None
    chain = chain if chain is not None else dwg_conjugate_chain(path)
    if not chain:
        return None
    frame = _housing_frame(payload, chain)
    if frame is None:
        return None
    axis, front, sign, scale = frame
    best = None
    for dim in _linear_dimensions(payload):
        if "Ø" not in dim["text"]:
            continue
        across = abs(dim["p2"][1 - axis] - dim["p1"][1 - axis]) / scale
        along = abs(dim["p2"][axis] - dim["p1"][axis]) / scale
        if abs(across - dim["value"]) > max(0.05, 2e-3 * dim["value"]) or along > 0.05:
            continue
        position = sign * (0.5 * (dim["p1"][axis] + dim["p2"][axis]) - front) / scale
        if 0.0 <= position <= float(before_mm):
            best = max(best or 0.0, 0.5 * dim["value"])
    return best


# Named sensor formats, for the one corroboration a telecentric drawing always carries: it states
# the object field AND the format that field fills, and m = format_width / object_width.
_SENSOR_FORMATS_MM = {
    "1/4": (3.6, 2.7), "1/3": (4.8, 3.6), "1/2.5": (5.76, 4.29), "1/2": (6.4, 4.8),
    "1/1.8": (7.2, 5.4), "2/3": (8.8, 6.6), "1": (12.8, 9.6), "1.1": (14.2, 10.4),
    "4/3": (17.3, 13.0),
}


def dwg_telecentric_cardinals(path: str | Path):
    """First-order cardinals for a fixed-conjugate TELECENTRIC lens, read from its DWG.

    bugs/0790. Returns a ``DatasheetCardinals`` or None. Every number is corroborated by a second,
    independent statement on the same drawing before it is used -- bugs/0565's rule, applied to a
    source that states more than it needs to:

    ``m``      the spec row (``Optical Mgnification | 4.0X``) against the field row
               (``F.O.V : 2.2mm X 1.65mm @ 2/3" ccd camera``): 2.2 x 4.0 = 8.8 = the 2/3 inch
               format's width. A magnification that does not fill the format it names is refused.
    ``F/#``    the spec row against ``N.A``: an object-space telecentric images at
               ``F/# = m / (2 NA_object)``, here 4.0 / (2 x 0.16) = 12.5.
    ``WD``     the spec row (``W.D(mm) | 65``) against the dimension run's own ``WD65 ±2``.
    ``flange`` the dimension run's last entry, which must EQUAL a standard mount's flange focal
               distance (17.526 for the C-mount it names) -- see :func:`dwg_conjugate_chain`.

    The housing length is then the only value with a single source, and it is the remainder of a
    run whose two ends are both verified.
    """
    from KrakenOS.UI.services.datasheet_prescription_import import DatasheetCardinals

    text = dwg_spec_text(path)
    chain = dwg_conjugate_chain(path)
    if not text or chain is None:
        return None
    if re.search(r"(?i)telecentric", text) is None:
        return None
    # magnification: the vendor's own spelling may be a typo ("Mgnification"), so anchor on the
    # tail of the word. A LABEL may be misspelt; the value is corroborated below.
    mag_match = re.search(r"(?i)\bM[a-z]*gnification\s*:?\s*(\d+(?:\.\d+)?)\s*X", text)
    if mag_match is None:
        return None
    mag = _as_float(mag_match.group(1))
    if mag is None or not (0.05 <= mag <= 20.0):
        return None
    # corroborate it against the field row and the format it names
    field = re.search(
        r"(?i)F\.?O\.?V\s*:?\s*(\d+(?:\.\d+)?)\s*mm\s*[xX×]\s*(\d+(?:\.\d+)?)\s*mm[^\n]*?"
        r"(\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)\s*[\"”]", text)
    if field is None:
        return None
    object_w = _as_float(field.group(1))
    fmt = _SENSOR_FORMATS_MM.get(str(field.group(3)).strip())
    if object_w is None or fmt is None:
        return None
    if abs(object_w * mag - fmt[0]) > 0.35:          # 4% of a 2/3 inch width
        return None
    # F-number, corroborated against the numerical aperture
    fno = _first(text, r"(?i)F\s*/\s*#\s*:?\s*(\d+(?:\.\d+)?)")
    na = _first(text, r"(?i)\bN\.?A\.?\s*:?\s*(\d+(?:\.\d+)?)")
    if fno is not None and na is not None and na > 0.0:
        if abs(fno - mag / (2.0 * na)) > max(0.5, 0.05 * fno):
            return None
    # the working distance is stated twice; both must agree
    wd_row = _first(text, r"(?i)W\.?\s*D\.?\s*\(\s*mm\s*\)\s*:?\s*(\d+(?:\.\d+)?)")
    if wd_row is not None and abs(wd_row - chain["wd"]) > 0.51:
        return None
    effl = chain["total"] / (2.0 + mag + 1.0 / mag)
    if not (1.0 <= effl <= 2000.0):
        return None
    # bugs/0792: the registration law says whether the coincident-principal-plane focal length is
    # reachable. Above about 1x it is not, for any lens of this class -- so record that rather
    # than refuse, and let the builder solve for the LENS from the conjugates.
    offset = effl * (1.0 + 1.0 / mag) - chain["wd"]
    conjugate_constrained = not (0.0 < offset < effl)
    cardinals = DatasheetCardinals(effl=round(effl, 4))
    cardinals.telecentric = True
    cardinals.conjugate_constrained = bool(conjugate_constrained)
    cardinals.magnification = -abs(mag)
    cardinals.optimum_wd = chain["wd"]
    cardinals.optimum_wd_mag = abs(mag)
    cardinals.mount_flange_mm = chain["flange"]
    cardinals.span = round(chain["housing"], 4)
    cardinals.fno = fno
    cardinals.image_circle = round(math.hypot(*fmt), 4)
    title = re.search(r"(?i)\b([A-Z]{2,5}\d+(?:\.\d+)?X-[A-Z0-9-]+)\b", text)
    if title is not None:
        cardinals.title = title.group(1)
    # bugs/0807: the drawing may also say where the stop is, and how wide the front barrel is
    try:
        iris = dwg_iris_stop(path, chain=chain)
    except Exception:
        iris = None
    if iris is not None:
        cardinals.stop_from_front_mm = round(iris["stop_mm"], 4)
        ring = iris.get("ring_mm")
        cardinals.stop_ring_mm = (round(ring[0], 4), round(ring[1], 4)) if ring else None
        where = (f"the middle of its {ring[1] - ring[0]:g} mm ring ({ring[0]:g}..{ring[1]:g} mm)"
                 if ring else f"its leader tip ({iris['tip_mm']:.4g} mm)")
        cardinals.stop_source = f"{Path(path).name}: the '{iris['label']}' leader, {where}"
        try:
            cardinals.front_barrel_radius_mm = dwg_barrel_radius(
                path, before_mm=iris["stop_mm"], chain=chain)
        except Exception:
            cardinals.front_barrel_radius_mm = None
    return cardinals
