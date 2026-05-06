"""On-axis Wavefront Function check for the Figure 8 F-theta lens."""

from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

TITLE = "F-Theta Lens 50mm Wavefront 0 Deg"

_REFERENCE_PATH = Path(__file__).with_name("f_theta_lens_50mm_figure8.py")
_SPEC = importlib.util.spec_from_file_location("_kraken_f_theta_figure8", _REFERENCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load reference layout: {_REFERENCE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SETTINGS = dict(_MODULE.SETTINGS)
SETTINGS.update(
    {
        "analysis_mode": "wavefront",
        "analysis_modes": ["wavefront"],
        "field_type": "Angle",
        "field_value": "0.0",
        "ray_count": "17",
        "wavefront_style": "Wavefront Function",
        "analysis_surface": "10: F-theta scan plane",
        "layout_note": (
            "Pure sequential Figure 8 F-theta wavefront validation at 0 deg field. "
            "Use this, not the folded Galvo scanner layout, to compare against the "
            "on-axis Zemax Wavefront Function screenshot in attachment/swappy*.png."
        ),
    }
)

SURFACES = deepcopy(_MODULE.SURFACES)
