"""Physics helpers for KrakenOS.

This package has two halves that must both stay reachable through
``from .Physics import *``:

* ``optics`` -- the legacy ``KrakenOS/Physics.py`` module (dispersion, Fresnel
  energy, paraxial calc). ``KrakenSys``, ``PhysicsClass`` and the top-level
  ``KrakenOS/__init__`` star-import this package and call those names
  unqualified, so anything public in ``optics`` MUST be re-exported here.
* ``photodiode`` -- the newer, self-contained detector models used by the
  examples and tutorials.

The legacy half is re-exported *dynamically* on purpose. When it lived in
``KrakenOS/Physics.py`` it had no ``__all__``, so ``import *`` delivered every
public global; a hand-written list here would silently drop any helper added to
``optics`` later and reintroduce bug 0474 (see ``bugs/``). Deriving the list
from the module keeps the star-import meaning exactly what it always meant.
"""

from . import optics as _optics
from .optics import *  # noqa: F401,F403 -- legacy unqualified API, see docstring

from .photodiode import (
    HC_EV_UM,
    PhotodiodeParameters,
    absorption_intensity,
    diffusion_length,
    excess_carrier_profile,
    fresnel_reflectance,
    ideal_spectral_response,
    photodiode_current_density,
    photovoltage,
    qualitative_quantum_efficiency,
    responsivity,
    single_layer_reflectance,
)

#: Names the photodiode half contributes. Explicit, because it is a curated API.
PHOTODIODE_API = (
    "HC_EV_UM",
    "PhotodiodeParameters",
    "absorption_intensity",
    "diffusion_length",
    "excess_carrier_profile",
    "fresnel_reflectance",
    "ideal_spectral_response",
    "photodiode_current_density",
    "photovoltage",
    "qualitative_quantum_efficiency",
    "responsivity",
    "single_layer_reflectance",
)

#: Names the legacy optics half contributes, derived from the module so it
#: cannot go stale. Mirrors the old module's implicit ``import *`` surface.
OPTICS_API = tuple(
    name for name in sorted(vars(_optics)) if not name.startswith("_")
)

__all__ = list(PHOTODIODE_API) + [
    name for name in OPTICS_API if name not in PHOTODIODE_API
]
