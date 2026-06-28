"""Per-field Zemax spot-radius data → field-resolved aberration spots (augmented surrogate).

The on-axis wavefront map (``zemax_wavefront``) gives the augmented surrogate its on-axis
spot, but the same blob then rides every field. A vendor's Zemax "Spot Diagram Data" export
(``Lens/<id>/spot radius/Mag*.txt``) carries the **per-field** RMS spot sizes -- and crucially
the RMS X (sagittal) and RMS Y (tangential/meridional) sizes separately -- so the spot grows
and elongates with field exactly as the real lens does (round on-axis, a radial coma/astig
ellipse toward the edge).

This module is pure numpy: parse the export, then synthesise each field's scatter as an
anisotropic pattern whose RMS-x = the interpolated sagittal size and RMS-y = the tangential
size, rotated so the tangential (meridional) axis points radially outward at that field's
azimuth -- the physically-correct rotationally-symmetric behaviour.
"""

from __future__ import annotations

import re

import numpy as np

_FLOAT = r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?"


def _decode(path) -> str:
    raw = open(path, "rb").read()
    for enc in ("utf-16", "utf-8", "latin-1"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-16", errors="ignore")


def parse_zemax_spot_radius(path) -> "list[dict] | None":
    """Parse a Zemax "Listing of Spot Diagram Data" export into per-field records.

    Returns a list (sorted by field) of ``{field_mm, rms_radius_um, rms_x_um, rms_y_um,
    max_radius_um}`` -- ``field_mm`` is the image-coordinate height (the chief-ray height).
    None if nothing parseable.
    """
    try:
        text = _decode(path)
    except Exception:
        return None
    fields: list[dict] = []
    current: dict = {}

    def _flush():
        if {"field_mm", "rms_x_um", "rms_y_um"} <= set(current):
            fields.append(dict(current))

    for line in text.splitlines():
        if "Image coordinate" in line:
            _flush()
            current.clear()
            nums = re.findall(_FLOAT, line)
            if len(nums) >= 2:
                try:
                    current["field_mm"] = abs(float(nums[1]))  # the Y (height) coordinate
                except ValueError:
                    pass
        elif "RMS Spot Radius" in line:
            m = re.search(_FLOAT, line)
            if m:
                current["rms_radius_um"] = float(m.group())
        elif "RMS Spot X Size" in line:
            m = re.search(_FLOAT, line)
            if m:
                current["rms_x_um"] = float(m.group())
        elif "RMS Spot Y Size" in line:
            m = re.search(_FLOAT, line)
            if m:
                current["rms_y_um"] = float(m.group())
        elif "Max Spot Radius" in line:
            m = re.search(_FLOAT, line)
            if m:
                current["max_radius_um"] = float(m.group())
    _flush()

    fields = [f for f in fields if "field_mm" in f and "rms_x_um" in f and "rms_y_um" in f]
    if not fields:
        return None
    fields.sort(key=lambda f: f["field_mm"])
    return fields


def _unit_rms_hexapolar(n_rings: int = 7) -> np.ndarray:
    """A filled hexapolar point set normalised so RMS-x = RMS-y = 1 (the base spot shape)."""
    pts = [(0.0, 0.0)]
    for k in range(1, n_rings + 1):
        radius = k / n_rings
        for j in range(6 * k):
            ang = 2.0 * np.pi * j / (6 * k)
            pts.append((radius * np.cos(ang), radius * np.sin(ang)))
    p = np.asarray(pts, dtype=float)
    rms_x = float(np.sqrt(np.mean(p[:, 0] ** 2)))
    if rms_x <= 1e-12:
        return p
    return p / rms_x


def field_resolved_scatter(chief_u, chief_v, field_data, *, n_rings: int = 7):
    """Per-field aberration scatters from the Zemax spot-radius records.

    For each chief position ``(u, v)`` (mm, image-plane local), interpolate the sagittal (X)
    and tangential (Y) RMS sizes by the field RADIUS, build an anisotropic spot (RMS-sagittal
    perpendicular to the radius, RMS-tangential along it), and rotate it to the field's
    azimuth. Returns ``(scatters, rms_radius_mm)`` -- ``scatters[i]`` is an ``(N, 2)`` array of
    (du, dv) offsets in mm, ``rms_radius_mm[i]`` the field's RMS spot radius (mm). None if the
    data is unusable.
    """
    chief_u = np.asarray(chief_u, dtype=float).reshape(-1)
    chief_v = np.asarray(chief_v, dtype=float).reshape(-1)
    records = list(field_data or [])
    if chief_u.size == 0 or chief_u.size != chief_v.size or len(records) < 1:
        return None
    fields = np.asarray([r["field_mm"] for r in records], dtype=float)
    rms_x = np.asarray([r["rms_x_um"] for r in records], dtype=float) / 1000.0     # sagittal, mm
    rms_y = np.asarray([r["rms_y_um"] for r in records], dtype=float) / 1000.0     # tangential, mm
    rms_r = np.asarray([r.get("rms_radius_um", float(np.hypot(r["rms_x_um"], r["rms_y_um"]))) for r in records], dtype=float) / 1000.0
    if not np.any(rms_r > 0.0):
        return None
    base = _unit_rms_hexapolar(n_rings)  # (N, 2), RMS-x = RMS-y = 1

    scatters: list[np.ndarray] = []
    rms_radius_mm: list[float] = []
    for cu, cv in zip(chief_u, chief_v):
        r = float(np.hypot(cu, cv))
        theta = float(np.arctan2(cv, cu))
        sag = float(np.interp(r, fields, rms_x))   # perpendicular to the radius
        tan = float(np.interp(r, fields, rms_y))   # along the radius (meridional)
        rad = float(np.interp(r, fields, rms_r))
        s = base[:, 0] * sag   # sagittal offsets
        t = base[:, 1] * tan   # tangential offsets
        ct, st = np.cos(theta), np.sin(theta)
        # tangential axis = (cos, sin) (radial); sagittal axis = (-sin, cos) (perpendicular)
        du = -s * st + t * ct
        dv = s * ct + t * st
        scatters.append(np.column_stack((du, dv)))
        rms_radius_mm.append(rad)
    return scatters, rms_radius_mm
