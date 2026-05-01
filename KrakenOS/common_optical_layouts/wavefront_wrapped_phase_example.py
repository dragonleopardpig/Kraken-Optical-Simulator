from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

TITLE = "Wavefront Wrapped Phase Example"

_REFERENCE_PATH = Path(__file__).with_name("advanced_surface_zernike_example.py")
_SPEC = importlib.util.spec_from_file_location("_kraken_wavefront_wrapped", _REFERENCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load reference layout: {_REFERENCE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SETTINGS = dict(_MODULE.SETTINGS)
SETTINGS.update(
    {
        "analysis_mode": "wavefront",
        "analysis_modes": ["wavefront"],
        "ray_count": "17",
        "wavefront_style": "Wrapped phase",
    }
)

SURFACES = deepcopy(_MODULE.SURFACES)
