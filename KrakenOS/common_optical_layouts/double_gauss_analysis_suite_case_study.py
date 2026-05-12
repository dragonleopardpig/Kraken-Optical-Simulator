"""Double Gauss analysis-suite case study layout.

This menu-backed layout reuses the stable Double Gauss prescription and presets
the UI for a single-state analysis walkthrough: Spot, PSF, MTF, Wavefront, and
Zernike.
"""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path


TITLE = "Double Gauss PSF MTF Wavefront Zernike Case Study"

_REFERENCE_PATH = Path(__file__).with_name("double_gauss_lens.py")
_SPEC = importlib.util.spec_from_file_location("_kraken_double_gauss_reference", _REFERENCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load Double Gauss reference layout: {_REFERENCE_PATH}")
_REFERENCE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_REFERENCE)


SETTINGS = deepcopy(getattr(_REFERENCE, "SETTINGS", {}))
SETTINGS.update(
    {
        "object_mode": "Infinity",
        "display_orientation": "Vertical",
        "wavelength": "0.55",
        "ray_count": "17",
        "ray_height_factor": "0.8",
        "analysis_surface": "Auto",
        "aperture_type": "EPD",
        "aperture_value": "4.0",
        "spot_view_mode": "Centroid",
        "show_clipped_rays": True,
        "show_cardinals": True,
        "show_physical_distances": True,
        "field_type": "Angle",
        "field_value": "0.0",
        "field_count": "1",
        "image_diameter_mode": "Auto",
        "analysis_mode": "none",
        "analysis_modes": [],
        "wavefront_style": "Wavefront Function",
        "selected_operands": ["Spot RMS", "MTF @ freq", "Wavefront RMS"],
    }
)

_OPERANDS = deepcopy(SETTINGS.get("operands", {}))
if isinstance(_OPERANDS, dict):
    _OPERANDS.setdefault("Spot RMS", {}).update(
        {"target": "0", "weight": "1", "wavelength": "0.55", "field": "0", "surface": "Auto"}
    )
    _OPERANDS.setdefault("MTF @ freq", {}).update(
        {
            "target": "0.35",
            "weight": "0.5",
            "wavelength": "0.55",
            "field": "0",
            "field_x": "0",
            "field_y": "0",
            "surface": "Auto",
            "frequency": "20",
            "mtf_mode": "Average",
            "mtf_algorithm": "PSF FFT",
        }
    )
    _OPERANDS.setdefault("Wavefront RMS", {}).update(
        {"target": "0", "weight": "0.5", "wavelength": "0.55", "field": "0", "surface": "Auto"}
    )
    SETTINGS["operands"] = _OPERANDS


SURFACES = deepcopy(getattr(_REFERENCE, "SURFACES"))


def build_system():
    """Return a KrakenOS system for script users."""

    return _REFERENCE.build_system()


def build_runtime_system():
    """Return the runtime KrakenOS optical system used by the UI."""

    return _REFERENCE.build_runtime_system()


def build_rays(system):
    """Return the same small preview ray fan as the reference layout."""

    return _REFERENCE.build_rays(system)
