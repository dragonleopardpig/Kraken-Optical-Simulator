from __future__ import annotations

import importlib.util
from pathlib import Path

TITLE = "Wide Field Wavefront Map Example"

_REFERENCE_PATH = Path(__file__).with_name("zemax_double_gauss_28_degree.py")
_SPEC = importlib.util.spec_from_file_location("_kraken_zemax_double_gauss_28", _REFERENCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load reference layout: {_REFERENCE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SETTINGS = dict(_MODULE.SETTINGS)
SETTINGS.update(
    {
        "analysis_mode": "wavefront_map",
        "analysis_modes": ["wavefront_map"],
        "field_type": "Angle",
        "field_value": "14",
        "field_count": "3",
        "ray_count": "7",
        "spot_view_mode": "Centroid",
    }
)

SURFACES = [dict(surface) for surface in _MODULE.SURFACES]
