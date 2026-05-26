"""Zemax sequential text prescription import helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class ZemaxImportDefaults:
    projection_display_mode: str
    source_model: str
    pupil_pattern: str
    gaussian_input_mode: str
    gaussian_waist_side: str
    source_angular_weight: str
    wavefront_style: str
    tolerance_compare_view: str
    atmos_plot_mode: str
    folded_detector_policy: str


def _read_zemax_text(path: Path) -> str:
    payload = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "SURF" in text and ("\n" in text or "\r" in text):
            return text
    raise ValueError(f"{Path(path).name} does not look like a text Zemax .zmx file.")


def _zemax_float(text: str, default: float = 0.0) -> float:
    try:
        value = float(str(text).strip())
    except Exception:
        return float(default)
    if not np.isfinite(value):
        return float(default)
    return float(value)


def _zemax_round(value: float, digits: int = 10) -> float:
    if not np.isfinite(value):
        return 0.0
    rounded = round(float(value), digits)
    return 0.0 if abs(rounded) < 1e-12 else rounded


def _zemax_glass_from_tokens(
    tokens: list[str],
    *,
    known_glass_names: Callable[[], set[str]],
) -> tuple[str, str | None]:
    if not tokens:
        return "AIR", None
    name = str(tokens[0]).strip().strip('"') or "AIR"
    compact = name.upper()
    if compact in {"AIR", "MIRROR", "GRIN", "NVK", "___BLANK"}:
        if compact == "___BLANK" and len(tokens) >= 5:
            try:
                nd = float(tokens[3])
                vd = float(tokens[4])
                if np.isfinite(nd) and np.isfinite(vd) and nd > 0.0:
                    return f"___BLANK,1,0,{nd:.12g},{vd:.12g},0,0,0,0,0,0", f"Zemax embedded glass {name} preserved as ___BLANK n/V data."
            except Exception:
                pass
        return name, None
    if compact in known_glass_names():
        return name, None
    if len(tokens) >= 5:
        try:
            nd = float(tokens[3])
            vd = float(tokens[4])
            if np.isfinite(nd) and np.isfinite(vd) and nd > 0.0:
                return f"nvk,{nd:.12g},{vd:.12g},0", f"Zemax glass {name} converted to embedded n/V data."
        except Exception:
            pass
    return name, f"Zemax glass {name} was not found in KrakenOS catalogs and had no embedded n/V fallback."


def load_zemax_zmx_data(
    path: Path,
    *,
    known_glass_names: Callable[[], set[str]],
    defaults: ZemaxImportDefaults,
) -> dict:
    """Load a sequential Zemax text prescription into Kraken layout dictionaries."""
    path = Path(path)
    text = _read_zemax_text(path)
    unit_scale_by_name = {"MM": 1.0, "IN": 25.4, "CM": 10.0, "M": 1000.0}
    title = path.stem.replace("_", " ").title()
    unit_name = "MM"
    enpd = 0.0
    x_fields: list[float] = []
    y_fields: list[float] = []
    primary_wavelength_index = None
    wavelengths: dict[int, float] = {}
    surfaces: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        key = parts[0].upper()
        if key == "NAME":
            candidate = " ".join(parts[1:]).strip()
            if candidate:
                title = candidate
            continue
        if key == "UNIT" and len(parts) > 1:
            unit_name = parts[1].upper()
            continue
        if key == "ENPD" and len(parts) > 1:
            enpd = _zemax_float(parts[1])
            continue
        if key == "XFLN":
            x_fields = [_zemax_float(value) for value in parts[1:]]
            continue
        if key == "YFLN":
            y_fields = [_zemax_float(value) for value in parts[1:]]
            continue
        if key == "PWAV" and len(parts) > 1:
            try:
                primary_wavelength_index = int(float(parts[1]))
            except Exception:
                primary_wavelength_index = None
            continue
        if key == "WAVM" and len(parts) > 2:
            try:
                wavelengths[int(float(parts[1]))] = _zemax_float(parts[2], 0.55)
            except Exception:
                pass
            continue
        if key == "SURF" and len(parts) > 1:
            if current is not None:
                surfaces.append(current)
            try:
                index = int(float(parts[1]))
            except Exception:
                index = len(surfaces)
            current = {
                "index": index,
                "stop": False,
                "type": "STANDARD",
                "curv": 0.0,
                "coni": 0.0,
                "disz": "0",
                "glass": "AIR",
                "glass_note": None,
                "diam": 0.0,
                "coating": "",
                "parms": {},
                "unsupported": [],
            }
            continue
        if current is None:
            continue
        if key == "STOP":
            current["stop"] = True
        elif key == "TYPE" and len(parts) > 1:
            current["type"] = parts[1].upper()
        elif key == "CURV" and len(parts) > 1:
            current["curv"] = _zemax_float(parts[1])
        elif key == "CONI" and len(parts) > 1:
            current["coni"] = _zemax_float(parts[1])
        elif key == "PARM" and len(parts) > 2:
            try:
                parm_index = int(float(parts[1]))
                if parm_index > 0:
                    current.setdefault("parms", {})[parm_index] = _zemax_float(parts[2])
            except Exception:
                current.setdefault("unsupported", []).append(line)
        elif key in {"XDAT", "YDAT", "SQAP", "CLAP", "OBDC", "ELIP", "APER", "TILT", "DECX", "DECY"}:
            current.setdefault("unsupported", []).append(line)
        elif key == "DISZ" and len(parts) > 1:
            current["disz"] = parts[1]
        elif key == "GLAS" and len(parts) > 1:
            glass, glass_note = _zemax_glass_from_tokens(
                [part.strip('"') for part in parts[1:]],
                known_glass_names=known_glass_names,
            )
            current["glass"] = glass
            current["glass_note"] = glass_note
        elif key == "COAT" and len(parts) > 1:
            current["coating"] = parts[1].strip('"')
        elif key == "DIAM" and len(parts) > 1:
            current["diam"] = _zemax_float(parts[1])
    if current is not None:
        surfaces.append(current)
    if len(surfaces) < 2:
        raise ValueError(f"No sequential SURF records were found in {path.name}. Only text .zmx prescriptions are supported.")

    unit_scale = unit_scale_by_name.get(unit_name, 1.0)
    nonzero_diameters = [
        2.0 * _zemax_float(str(surface.get("diam", 0.0))) * unit_scale
        for surface in surfaces
        if _zemax_float(str(surface.get("diam", 0.0))) > 0.0
    ]
    default_diameter = _zemax_round(nonzero_diameters[0] if nonzero_diameters else 25.0)
    last_index = int(surfaces[-1].get("index", len(surfaces) - 1))
    object_at_infinity = str(surfaces[0].get("disz", "")).strip().upper().startswith("INFINITY")
    rows: list[dict[str, object]] = []
    stop_diameter = 0.0

    for surface in surfaces:
        index = int(surface.get("index", 0))
        curv = _zemax_float(str(surface.get("curv", 0.0)))
        rc = 0.0 if abs(curv) < 1e-12 else unit_scale / curv
        conic = _zemax_float(str(surface.get("coni", 0.0)))
        disz = str(surface.get("disz", "0")).strip()
        thickness = 100.0 if disz.upper().startswith("INFINITY") else _zemax_float(disz) * unit_scale
        diameter = 2.0 * _zemax_float(str(surface.get("diam", 0.0))) * unit_scale
        if diameter <= 0.0:
            diameter = default_diameter
        glass = str(surface.get("glass", "AIR") or "AIR").strip() or "AIR"
        if index == 0:
            surface_type = "Object"
            name = "Object"
            glass = "AIR"
        elif index == last_index:
            surface_type = "Image"
            name = "Image"
            glass = "AIR"
        elif bool(surface.get("stop", False)):
            surface_type = "Aperture"
            name = "Stop"
            glass = "AIR"
            stop_diameter = max(stop_diameter, diameter)
        else:
            surface_type = "Standard"
            name = f"S{index:02d} {glass}" if glass != "AIR" else f"S{index:02d} Air Gap"
        advanced: dict[str, object] = {}
        parms = surface.get("parms", {})
        if isinstance(parms, dict) and parms:
            max_parm = max(int(key) for key in parms)
            aspher = [0.0] * max(max_parm, 1)
            for parm_index, value in sorted(parms.items()):
                if int(parm_index) > 0:
                    aspher[int(parm_index) - 1] = _zemax_float(str(value))
            if any(abs(float(value)) > 1e-15 for value in aspher):
                advanced["AspherData"] = aspher
        notes = []
        coating = str(surface.get("coating", "") or "").strip()
        if coating:
            notes.append(f"Zemax coating: {coating}")
        glass_note = str(surface.get("glass_note", "") or "").strip()
        if glass_note:
            notes.append(glass_note)
        surface_type_name = str(surface.get("type", "") or "").strip().upper()
        if surface_type_name and surface_type_name != "STANDARD":
            notes.append(f"Zemax surface TYPE {surface_type_name} imported as {surface_type}.")
        unsupported = list(surface.get("unsupported", []) or [])
        if unsupported:
            notes.append("Unparsed Zemax aperture/transform data preserved in this note: " + " | ".join(str(item) for item in unsupported[:6]))
        if notes:
            advanced["Note"] = " ".join(notes)
        rows.append(
            {
                "surface": surface_type,
                "name": name,
                "rc": _zemax_round(rc),
                "k": _zemax_round(conic),
                "axicon": 0.0,
                "thickness": _zemax_round(thickness),
                "diameter": _zemax_round(diameter),
                "tilt_x": 0.0,
                "tilt_y": 0.0,
                "tilt_z": 0.0,
                "desp_x": 0.0,
                "desp_y": 0.0,
                "desp_z": 0.0,
                "axis_move": 0.0,
                "glass": glass,
                "optimize_rc": False,
                "optimize_rc_bounds": None,
                "optimize_thickness": False,
                "optimize_thickness_bounds": None,
                "advanced": advanced,
            }
        )

    primary_wavelength = wavelengths.get(primary_wavelength_index or -1)
    if primary_wavelength is None and wavelengths:
        primary_wavelength = wavelengths[min(wavelengths)]
    if primary_wavelength is None:
        primary_wavelength = 0.55
    max_field = max([abs(value) for value in [*x_fields, *y_fields]] or [0.0])
    field_count = max(len(y_fields), len(x_fields), 1)
    aperture_value = enpd * unit_scale if enpd > 0.0 else stop_diameter
    settings = {
        "object_mode": "Infinity" if object_at_infinity else "Finite",
        "display_orientation": "YZ",
        "projection_display_mode": defaults.projection_display_mode,
        "wavelength": f"{primary_wavelength:g}",
        "ray_count": "21",
        "ray_height_factor": "0.8",
        "source_model": defaults.source_model,
        "pupil_pattern": defaults.pupil_pattern,
        "source_radius": "5.0",
        "source_cone_angle": "0.0",
        "gaussian_input_mode": defaults.gaussian_input_mode,
        "gaussian_waist_radius": "0.5",
        "gaussian_waist_offset": "0.0",
        "gaussian_beam_diameter": "1.0",
        "gaussian_full_divergence": "1.0",
        "gaussian_waist_side": defaults.gaussian_waist_side,
        "gaussian_m2": "1.0",
        "pupil_rad": "0.0",
        "pupil_theta": "0.0",
        "source_power": "1.0",
        "source_seed": "1",
        "source_x": "0.0",
        "source_y": "0.0",
        "source_z": "0.0",
        "source_l": "0.0",
        "source_m": "0.0",
        "source_n": "1.0",
        "source_angular_weight": defaults.source_angular_weight,
        "analysis_surface": "Auto",
        "aperture_type": "EPD",
        "aperture_value": f"{_zemax_round(aperture_value):g}",
        "spot_view_mode": "Grid",
        "wavefront_style": defaults.wavefront_style,
        "tolerance_compare_view": defaults.tolerance_compare_view,
        "show_clipped_rays": True,
        "show_cardinals": True,
        "show_physical_distances": False,
        "field_type": "Angle",
        "field_value": f"{max_field:g}",
        "field_count": str(field_count),
        "atmos_plot_mode": defaults.atmos_plot_mode,
        "image_diameter_mode": "Auto",
        "trace_mode": "Auto",
        "folded_detector_policy": defaults.folded_detector_policy,
        "nonseq_target_surface": "Auto",
        "nonseq_ns_limit": "200",
        "nonseq_energy_probability": False,
        "analysis_mode": "none",
        "analysis_modes": [],
        "layout_preview_mode": "none",
        "auto_save_plot": False,
        "external_camera": "None",
        "camera_overlay_mode": "Off",
        "optimization_workers": "Auto",
        "selected_operands": ["Spot RMS"],
        "operands": {
            "Spot RMS": {
                "weight": "1",
                "target": "0",
                "wavelength": f"{primary_wavelength:g}",
                "field": "0",
                "surface": "Auto",
            },
            "MTF @ freq": {
                "weight": "1",
                "target": "0.5",
                "wavelength": f"{primary_wavelength:g}",
                "field": "0",
                "field_x": "0",
                "field_y": "0",
                "surface": "Auto",
                "frequency": "50",
                "mtf_mode": "Average",
                "mtf_algorithm": "Diffraction FFT",
            },
        },
    }
    return {"title": title, "surfaces": rows, "settings": settings, "unit": unit_name}
