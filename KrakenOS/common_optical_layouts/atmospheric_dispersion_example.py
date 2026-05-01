from __future__ import annotations

import importlib.util
from pathlib import Path

TITLE = "Atmospheric Dispersion Example"

_REFERENCE_PATH = Path(__file__).with_name("zemax_double_gauss_28_degree.py")
_SPEC = importlib.util.spec_from_file_location("_kraken_zemax_double_gauss_28", _REFERENCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Could not load reference layout: {_REFERENCE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

SETTINGS = dict(_MODULE.SETTINGS)
SETTINGS.update(
    {
        "analysis_mode": "atmosphere",
        "analysis_modes": ["atmosphere"],
        "wavelength": "0.55",
        "atmos_wavelength_min": "0.45",
        "atmos_wavelength_max": "0.75",
        "atmos_wavelength_count": "13",
        "atmos_zenith_deg": "55",
        "atmos_temperature_k": "283.15",
        "atmos_pressure_pa": "101300",
        "atmos_humidity": "0.5",
        "atmos_co2_ppm": "400",
        "atmos_latitude_deg": "31",
        "atmos_altitude_m": "2800",
    }
)

SURFACES = [dict(surface) for surface in _MODULE.SURFACES]
