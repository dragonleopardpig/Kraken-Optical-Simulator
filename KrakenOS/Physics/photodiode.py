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

# Intrinsic crystalline silicon at 300 K, Green (2008), Table 1.
# The near-band-edge subset covers the wavelength range used by the slab lab.
GREEN_2008_SILICON_WAVELENGTH_NM = np.arange(900.0, 1301.0, 10.0)
GREEN_2008_SILICON_ABSORPTION_CM_INV = np.array(
    [
        303.0,
        271.0,
        240.0,
        209.0,
        183.0,
        156.0,
        134.0,
        113.0,
        96.0,
        79.0,
        64.0,
        51.1,
        39.9,
        30.2,
        22.6,
        16.3,
        11.1,
        8.0,
        6.2,
        4.7,
        3.5,
        2.7,
        2.0,
        1.5,
        1.0,
        0.68,
        0.42,
        0.22,
        6.5e-2,
        3.6e-2,
        2.2e-2,
        1.3e-2,
        8.2e-3,
        4.7e-3,
        2.4e-3,
        1.0e-3,
        3.6e-4,
        2.0e-4,
        1.2e-4,
        7.1e-5,
        4.5e-5,
    ]
)
GREEN_2008_SILICON_REFRACTIVE_INDEX = np.array(
    [
        3.614,
        3.609,
        3.604,
        3.600,
        3.595,
        3.591,
        3.587,
        3.583,
        3.579,
        3.575,
        3.572,
        3.568,
        3.565,
        3.562,
        3.559,
        3.556,
        3.553,
        3.550,
        3.547,
        3.545,
        3.542,
        3.540,
        3.537,
        3.535,
        3.532,
        3.530,
        3.528,
        3.526,
        3.524,
        3.522,
        3.520,
        3.518,
        3.517,
        3.515,
        3.513,
        3.511,
        3.509,
        3.508,
        3.506,
        3.505,
        3.503,
    ]
)


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


def absorption_power(
    position_um,
    absorption_cm_inv: float,
    incident_power_w: float,
    surface_reflectance: float = 0.0,
) -> np.ndarray:
    """Return power remaining after surface reflection and bulk absorption.

    For a beam with constant cross-sectional area, power follows the same
    Beer-Lambert depth dependence as intensity.  ``surface_reflectance`` is
    the fraction removed at the entrance boundary before bulk absorption.
    """

    incident_power_w = _positive("incident_power_w", incident_power_w)
    surface_reflectance = _fraction(
        "surface_reflectance", surface_reflectance
    )
    return absorption_intensity(
        position_um,
        absorption_cm_inv,
        incident_intensity=incident_power_w,
    ) * (1.0 - surface_reflectance)


def absorption_depth_for_power(
    target_power_w: float,
    absorption_cm_inv: float,
    incident_power_w: float,
    surface_reflectance: float = 0.0,
) -> float:
    """Depth in um at which the remaining power has fallen to ``target_power_w``.

    Inverts Equation 3.22 for depth:

        z = ln(P_enter / P_target) / alpha,    P_enter = P_0 (1 - R)

    bugs/0481: this is the only depth in the model that responds to source power, and
    it is why "more power penetrates deeper" is both a misconception and a real effect
    depending on what is asked. The DECAY LENGTH ``1 / alpha`` is set by the material
    alone -- doubling the source power does not move it, because Beer-Lambert is
    multiplicative and the *fractional* profile is identical at every power. What does
    move is the depth at which the beam is still above some ABSOLUTE level (a detector
    noise floor, a damage threshold, a "fully absorbed" criterion), and it moves
    logarithmically: every decade of source power buys a further ``ln(10) / alpha``, so
    at alpha = 100 cm-1 (1 / alpha = 100 um) a decade is worth 230.3 um.

    Returns ``0.0`` when the target is already at or above the power entering the
    material -- the level is reached at the surface, not inside.
    """

    target_power_w = _positive("target_power_w", target_power_w)
    absorption_cm_inv = _positive("absorption_cm_inv", absorption_cm_inv)
    incident_power_w = _positive("incident_power_w", incident_power_w)
    surface_reflectance = _fraction(
        "surface_reflectance", surface_reflectance
    )
    entering_power_w = incident_power_w * (1.0 - surface_reflectance)
    if entering_power_w <= target_power_w:
        return 0.0
    depth_cm = np.log(entering_power_w / target_power_w) / absorption_cm_inv
    return float(depth_cm * 1.0e4)


def absorption_depth_gain_per_decade(absorption_cm_inv: float) -> float:
    """Extra depth in um that one decade of source power buys: ``ln(10) / alpha``.

    bugs/0481: the slope of :func:`absorption_depth_for_power` in log-power, split out
    because it is the number that answers "how much deeper does turning the power up
    actually get me?" without needing a floor to be chosen first.
    """

    absorption_cm_inv = _positive("absorption_cm_inv", absorption_cm_inv)
    return float(np.log(10.0) / absorption_cm_inv * 1.0e4)


def silicon_optical_properties(wavelength_nm):
    """Return Green (2008) ``(alpha, n)`` for intrinsic silicon at 300 K.

    Absorption is interpolated logarithmically because it spans nearly seven
    decades over the table subset.  Refractive index is interpolated linearly.
    """

    wavelength_nm = _finite_array("wavelength_nm", wavelength_nm)
    lower = GREEN_2008_SILICON_WAVELENGTH_NM[0]
    upper = GREEN_2008_SILICON_WAVELENGTH_NM[-1]
    if np.any((wavelength_nm < lower) | (wavelength_nm > upper)):
        raise ValueError(
            f"wavelength_nm must be between {lower:g} and {upper:g}"
        )

    absorption_cm_inv = 10.0 ** np.interp(
        wavelength_nm,
        GREEN_2008_SILICON_WAVELENGTH_NM,
        np.log10(GREEN_2008_SILICON_ABSORPTION_CM_INV),
    )
    refractive_index = np.interp(
        wavelength_nm,
        GREEN_2008_SILICON_WAVELENGTH_NM,
        GREEN_2008_SILICON_REFRACTIVE_INDEX,
    )
    return absorption_cm_inv, refractive_index


def silicon_slab_transmission(
    thickness_mm: float,
    wavelength_nm: float,
    source_fwhm_nm: float = 0.0,
    *,
    include_surface_reflection: bool = True,
) -> float:
    """Return transmitted power fraction for intrinsic silicon at 300 K.

    A zero source FWHM gives a monochromatic calculation.  A non-zero FWHM
    models a Gaussian source spectrum and integrates the transmitted spectral
    power.  For uncoated parallel surfaces, incoherent repeated internal
    reflections are included.  Scattering, coatings, doping, temperature
    shifts, and the detector spectral response are not included.
    """

    thickness_mm = float(thickness_mm)
    if not np.isfinite(thickness_mm) or thickness_mm < 0.0:
        raise ValueError("thickness_mm must be finite and not negative")
    wavelength_nm = float(wavelength_nm)
    if not np.isfinite(wavelength_nm):
        raise ValueError("wavelength_nm must be finite")
    silicon_optical_properties(wavelength_nm)
    source_fwhm_nm = float(source_fwhm_nm)
    if not np.isfinite(source_fwhm_nm) or source_fwhm_nm < 0.0:
        raise ValueError("source_fwhm_nm must be finite and not negative")

    if source_fwhm_nm == 0.0:
        wavelengths_nm = np.array([wavelength_nm])
        weights = None
    else:
        sigma_nm = source_fwhm_nm / (2.0 * np.sqrt(2.0 * np.log(2.0)))
        lower = max(
            GREEN_2008_SILICON_WAVELENGTH_NM[0],
            wavelength_nm - 4.0 * sigma_nm,
        )
        upper = min(
            GREEN_2008_SILICON_WAVELENGTH_NM[-1],
            wavelength_nm + 4.0 * sigma_nm,
        )
        if lower >= upper:
            raise ValueError("source spectrum lies outside the silicon table")
        wavelengths_nm = np.linspace(lower, upper, 401)
        weights = np.exp(
            -0.5 * ((wavelengths_nm - wavelength_nm) / sigma_nm) ** 2
        )

    absorption_cm_inv, refractive_index = silicon_optical_properties(
        wavelengths_nm
    )
    bulk_transmission = np.exp(
        -absorption_cm_inv * thickness_mm * 0.1
    )
    if include_surface_reflection:
        reflectance = ((1.0 - refractive_index) / (
            1.0 + refractive_index
        )) ** 2
        transmission = (
            (1.0 - reflectance) ** 2
            * bulk_transmission
            / (1.0 - (reflectance * bulk_transmission) ** 2)
        )
    else:
        transmission = bulk_transmission

    if weights is None:
        return float(transmission[0])
    return float(
        np.trapezoid(transmission * weights, wavelengths_nm)
        / np.trapezoid(weights, wavelengths_nm)
    )


def slab_log10_transmission(
    thickness_mm: float,
    absorption_cm_inv: float,
    surface_reflectance: float = 0.0,
    surface_count: int = 2,
) -> float:
    """Return ``log10(P_out / P_in)`` for an absorbing slab.

    Each uncoated surface transmits ``1 - R`` and the bulk follows
    Beer-Lambert absorption.  Multiple internal reflections and coherent
    etalon effects are intentionally omitted from this Chapter 3 model.
    """

    thickness_mm = float(thickness_mm)
    if not np.isfinite(thickness_mm) or thickness_mm < 0.0:
        raise ValueError("thickness_mm must be finite and not negative")
    absorption_cm_inv = _positive("absorption_cm_inv", absorption_cm_inv)
    surface_reflectance = _fraction(
        "surface_reflectance", surface_reflectance
    )
    if (
        isinstance(surface_count, bool)
        or int(surface_count) != surface_count
        or surface_count < 0
    ):
        raise ValueError("surface_count must be a non-negative integer")

    if surface_count == 0:
        surface_log10 = 0.0
    elif surface_reflectance == 1.0:
        return float("-inf")
    else:
        surface_log10 = (
            surface_count
            * np.log1p(-surface_reflectance)
            / np.log(10.0)
        )
    bulk_log10 = (
        -absorption_cm_inv * thickness_mm * 0.1 / np.log(10.0)
    )
    return float(surface_log10 + bulk_log10)


def required_source_log10_power(
    target_transmitted_power_w: float,
    thickness_mm: float,
    absorption_cm_inv: float,
    surface_reflectance: float = 0.0,
    surface_count: int = 2,
) -> float:
    """Return ``log10`` of source watts required for an absolute output."""

    target_transmitted_power_w = _positive(
        "target_transmitted_power_w", target_transmitted_power_w
    )
    return float(
        np.log10(target_transmitted_power_w)
        - slab_log10_transmission(
            thickness_mm,
            absorption_cm_inv,
            surface_reflectance,
            surface_count,
        )
    )


def absorption_coefficient_for_transmission(
    transmission_fraction: float,
    thickness_mm: float,
    surface_reflectance: float = 0.0,
    surface_count: int = 2,
) -> float:
    """Return the largest ``alpha`` in cm^-1 that meets a transmission target."""

    transmission_fraction = _positive(
        "transmission_fraction", transmission_fraction
    )
    if transmission_fraction > 1.0:
        raise ValueError("transmission_fraction must not exceed one")
    thickness_mm = _positive("thickness_mm", thickness_mm)
    surface_log10 = slab_log10_transmission(
        0.0,
        absorption_cm_inv=1.0,
        surface_reflectance=surface_reflectance,
        surface_count=surface_count,
    )
    surface_fraction = 10.0**surface_log10
    if transmission_fraction > surface_fraction:
        raise ValueError(
            "surface reflection alone exceeds the permitted transmission loss"
        )
    thickness_cm = thickness_mm * 0.1
    return float(
        -np.log(transmission_fraction / surface_fraction) / thickness_cm
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
