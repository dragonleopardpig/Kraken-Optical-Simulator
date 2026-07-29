"""Small, reusable physics models used by KrakenOS examples and tutorials."""

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

__all__ = [
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
]
