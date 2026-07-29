"""Equation-based photodiode models from Chapter 3 of Photonics Essentials.

The functions use centimetres for semiconductor transport quantities and
micrometres for optical wavelength and plotted distance.  They intentionally
model the ideal equations in the chapter; they are not a replacement for a
device manufacturer's measured data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ELEMENTARY_CHARGE_C = 1.602176634e-19
BOLTZMANN_EV_K = 8.617333262145e-5
HC_EV_UM = 1.2398419843320026


def _positive(name: str, value: float) -> float:
    value = float(value)
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and greater than zero")
    return value


def _fraction(name: str, value: float) -> float:
    value = float(value)
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return value


def _finite_array(name: str, value) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def diffusion_length(diffusion_cm2_s: float, lifetime_s: float) -> float:
    """Return the diffusion length ``sqrt(D * tau)`` in centimetres."""

    diffusion_cm2_s = _positive("diffusion_cm2_s", diffusion_cm2_s)
    lifetime_s = _positive("lifetime_s", lifetime_s)
    return float(np.sqrt(diffusion_cm2_s * lifetime_s))


def excess_carrier_profile(
    position_um,
    *,
    diffusion_cm2_s: float,
    lifetime_s: float,
    junction_excess_cm3: float,
    generation_cm3_s: float = 0.0,
) -> np.ndarray:
    """Evaluate the steady-state excess-carrier profile in Equation 3.11."""

    position_um = _finite_array("position_um", position_um)
    if np.any(position_um < 0.0):
        raise ValueError("position_um must not be negative")
    lifetime_s = _positive("lifetime_s", lifetime_s)
    generation_cm3_s = float(generation_cm3_s)
    junction_excess_cm3 = float(junction_excess_cm3)
    if generation_cm3_s < 0.0 or junction_excess_cm3 < 0.0:
        raise ValueError("carrier concentrations and generation must not be negative")

    length_cm = diffusion_length(diffusion_cm2_s, lifetime_s)
    position_cm = position_um * 1.0e-4
    bulk_excess = generation_cm3_s * lifetime_s
    return (
        (junction_excess_cm3 - bulk_excess)
        * np.exp(-position_cm / length_cm)
        + bulk_excess
    )


def ideal_spectral_response(wavelength_um, bandgap_ev: float) -> np.ndarray:
    """Evaluate the ideal threshold response from Equations 3.19 and 3.21."""

    wavelength_um = _finite_array("wavelength_um", wavelength_um)
    if np.any(wavelength_um <= 0.0):
        raise ValueError("wavelength_um must be greater than zero")
    bandgap_ev = _positive("bandgap_ev", bandgap_ev)
    return (wavelength_um <= HC_EV_UM / bandgap_ev).astype(float)


def absorption_intensity(
    position_um,
    absorption_cm_inv: float,
    incident_intensity: float = 1.0,
) -> np.ndarray:
    """Evaluate Beer-Lambert absorption, Equation 3.22."""

    position_um = _finite_array("position_um", position_um)
    if np.any(position_um < 0.0):
        raise ValueError("position_um must not be negative")
    absorption_cm_inv = _positive("absorption_cm_inv", absorption_cm_inv)
    incident_intensity = _positive("incident_intensity", incident_intensity)
    return incident_intensity * np.exp(
        -absorption_cm_inv * position_um * 1.0e-4
    )


def responsivity(
    wavelength_um,
    quantum_efficiency: float,
    bandgap_ev: float | None = None,
) -> np.ndarray:
    """Return photodiode responsivity in A/W from Equation 3.27."""

    wavelength_um = _finite_array("wavelength_um", wavelength_um)
    if np.any(wavelength_um <= 0.0):
        raise ValueError("wavelength_um must be greater than zero")
    quantum_efficiency = _fraction("quantum_efficiency", quantum_efficiency)
    result = quantum_efficiency * wavelength_um / HC_EV_UM
    if bandgap_ev is not None:
        result = result * ideal_spectral_response(wavelength_um, bandgap_ev)
    return result


def fresnel_reflectance(index_incident: float, index_substrate: float) -> float:
    """Return normal-incidence power reflectance from Equation 3.30."""

    index_incident = _positive("index_incident", index_incident)
    index_substrate = _positive("index_substrate", index_substrate)
    return ((index_incident - index_substrate) / (
        index_incident + index_substrate
    )) ** 2


def single_layer_reflectance(
    wavelength_um,
    *,
    index_incident: float,
    index_film: float,
    index_substrate: float,
    thickness_um: float,
) -> np.ndarray:
    """Return normal-incidence reflectance of one lossless coating layer."""

    wavelength_um = _finite_array("wavelength_um", wavelength_um)
    if np.any(wavelength_um <= 0.0):
        raise ValueError("wavelength_um must be greater than zero")
    index_incident = _positive("index_incident", index_incident)
    index_film = _positive("index_film", index_film)
    index_substrate = _positive("index_substrate", index_substrate)
    thickness_um = _positive("thickness_um", thickness_um)

    r01 = (index_incident - index_film) / (index_incident + index_film)
    r12 = (index_film - index_substrate) / (index_film + index_substrate)
    phase = np.exp(4j * np.pi * index_film * thickness_um / wavelength_um)
    amplitude = (r01 + r12 * phase) / (1.0 + r01 * r12 * phase)
    return np.abs(amplitude) ** 2


def qualitative_quantum_efficiency(
    wavelength_um,
    *,
    short_edge_um: float,
    bandgap_ev: float,
    peak_efficiency: float,
    edge_width_um: float,
) -> np.ndarray:
    """Return a smooth teaching model for a measured-like detector response.

    This is deliberately labelled qualitative.  It supplies the two rounded
    absorption edges seen in measured curves without claiming to reproduce a
    particular device or digitized data from the book.
    """

    wavelength_um = _finite_array("wavelength_um", wavelength_um)
    short_edge_um = _positive("short_edge_um", short_edge_um)
    bandgap_ev = _positive("bandgap_ev", bandgap_ev)
    peak_efficiency = _fraction("peak_efficiency", peak_efficiency)
    edge_width_um = _positive("edge_width_um", edge_width_um)
    cutoff_um = HC_EV_UM / bandgap_ev
    short_gate = 1.0 / (
        1.0 + np.exp(-(wavelength_um - short_edge_um) / edge_width_um)
    )
    long_gate = 1.0 / (
        1.0 + np.exp((wavelength_um - cutoff_um) / edge_width_um)
    )
    return peak_efficiency * short_gate * long_gate


@dataclass(frozen=True)
class PhotodiodeParameters:
    """Transport parameters for Equations 3.13, 3.14, and 3.18."""

    diffusion_cm2_s: float = 25.0
    lifetime_s: float = 1.0e-6
    intrinsic_carriers_cm3: float = 1.0e10
    acceptor_density_cm3: float = 1.0e16
    temperature_k: float = 300.0
    ideality_factor: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "diffusion_cm2_s",
            "lifetime_s",
            "intrinsic_carriers_cm3",
            "acceptor_density_cm3",
            "temperature_k",
            "ideality_factor",
        ):
            _positive(name, getattr(self, name))

    @property
    def diffusion_length_cm(self) -> float:
        return diffusion_length(self.diffusion_cm2_s, self.lifetime_s)

    @property
    def saturation_current_density_a_cm2(self) -> float:
        """Return ``q D n_i^2 / (L N_A)`` from Equation 3.13."""

        return (
            ELEMENTARY_CHARGE_C
            * self.diffusion_cm2_s
            * self.intrinsic_carriers_cm3**2
            / (self.diffusion_length_cm * self.acceptor_density_cm3)
        )


def photodiode_current_density(
    voltage_v,
    *,
    parameters: PhotodiodeParameters = PhotodiodeParameters(),
    generation_cm3_s: float = 0.0,
) -> np.ndarray:
    """Return total current density from Equation 3.14 in A/cm^2."""

    voltage_v = _finite_array("voltage_v", voltage_v)
    generation_cm3_s = float(generation_cm3_s)
    if generation_cm3_s < 0.0 or not np.isfinite(generation_cm3_s):
        raise ValueError("generation_cm3_s must be finite and not negative")

    exponent = voltage_v / (
        parameters.ideality_factor
        * BOLTZMANN_EV_K
        * parameters.temperature_k
    )
    diode = parameters.saturation_current_density_a_cm2 * np.expm1(
        np.clip(exponent, -745.0, 700.0)
    )
    photocurrent = (
        ELEMENTARY_CHARGE_C
        * parameters.diffusion_length_cm
        * generation_cm3_s
    )
    return diode - photocurrent


def photovoltage(
    generation_cm3_s,
    *,
    parameters: PhotodiodeParameters = PhotodiodeParameters(),
) -> np.ndarray:
    """Return open-circuit voltage from Equation 3.18."""

    generation_cm3_s = _finite_array("generation_cm3_s", generation_cm3_s)
    if np.any(generation_cm3_s < 0.0):
        raise ValueError("generation_cm3_s must not be negative")
    photocurrent = (
        ELEMENTARY_CHARGE_C
        * parameters.diffusion_length_cm
        * generation_cm3_s
    )
    return (
        parameters.ideality_factor
        * BOLTZMANN_EV_K
        * parameters.temperature_k
        * np.log1p(
            photocurrent / parameters.saturation_current_density_a_cm2
        )
    )
