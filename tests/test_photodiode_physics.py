import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


MODULE_PATH = (
    Path(__file__).parents[1] / "KrakenOS" / "Physics" / "photodiode.py"
)
SPEC = importlib.util.spec_from_file_location("photodiode_physics", MODULE_PATH)
photodiode = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = photodiode
SPEC.loader.exec_module(photodiode)


def test_diffusion_length_and_steady_state_profile():
    length_cm = photodiode.diffusion_length(25.0, 1.0e-6)
    assert length_cm == pytest.approx(0.005)

    position_um = np.array([0.0, 50.0, 1000.0])
    profile = photodiode.excess_carrier_profile(
        position_um,
        diffusion_cm2_s=25.0,
        lifetime_s=1.0e-6,
        junction_excess_cm3=1.0e14,
        generation_cm3_s=1.0e18,
    )
    assert profile[0] == pytest.approx(1.0e14)
    assert profile[-1] == pytest.approx(1.0e12, rel=5.0e-5)
    assert np.all(np.diff(profile) < 0.0)


def test_photovoltage_is_the_zero_current_operating_point():
    parameters = photodiode.PhotodiodeParameters()
    generation = 2.5e11
    voltage = photodiode.photovoltage(generation, parameters=parameters)
    current = photodiode.photodiode_current_density(
        voltage,
        parameters=parameters,
        generation_cm3_s=generation,
    )
    assert float(current) == pytest.approx(0.0, abs=1.0e-25)


def test_spectral_cutoff_absorption_and_responsivity_reference_points():
    wavelengths = np.array([0.62, 1.0, 1.24, 1.30])
    response = photodiode.ideal_spectral_response(wavelengths, 1.0)
    assert response.tolist() == [1.0, 1.0, 0.0, 0.0]

    intensity = photodiode.absorption_intensity([100.0], 100.0)
    assert intensity[0] == pytest.approx(np.exp(-1.0))

    responsivity = photodiode.responsivity([0.62, 1.24], 1.0)
    assert responsivity == pytest.approx([0.5, 1.0], rel=2.0e-4)


def test_absorption_power_applies_surface_reflection_before_bulk_absorption():
    surface_reflectance = photodiode.fresnel_reflectance(1.0, 3.5)
    depth_um = np.array([0.0, 100.0])
    power = photodiode.absorption_power(
        depth_um,
        absorption_cm_inv=100.0,
        incident_power_w=0.1,
        surface_reflectance=surface_reflectance,
    )

    assert power[0] == pytest.approx(0.1 * (1.0 - surface_reflectance))
    assert power[1] == pytest.approx(power[0] * np.exp(-1.0))


def test_absorption_depth_for_power_inverts_beer_lambert():
    """bugs/0481: the depth at which the beam falls to an absolute level."""
    surface_reflectance = photodiode.fresnel_reflectance(1.0, 3.5)
    depth_um = photodiode.absorption_depth_for_power(
        1.0e-9,
        absorption_cm_inv=100.0,
        incident_power_w=0.1,
        surface_reflectance=surface_reflectance,
    )

    # It is exactly where the power model says the floor is reached.
    remaining = photodiode.absorption_power(
        depth_um,
        absorption_cm_inv=100.0,
        incident_power_w=0.1,
        surface_reflectance=surface_reflectance,
    )
    assert float(remaining) == pytest.approx(1.0e-9, rel=1.0e-12)

    # A floor already met at the entrance is reached at the surface, not inside.
    assert (
        photodiode.absorption_depth_for_power(1.0, 100.0, 0.1) == 0.0
    )


def test_source_power_moves_the_floor_depth_but_not_the_decay_length():
    """bugs/0481: the reported "depth never changes" is half right, and this is which half.

    Beer-Lambert is multiplicative, so the FRACTIONAL profile is power-independent -- a
    power-dependent ``alpha`` would be a fake. The depth to an ABSOLUTE floor is what moves,
    and it moves by ``ln(10) / alpha`` per decade.
    """
    surface_reflectance = photodiode.fresnel_reflectance(1.0, 3.5)
    position_um = np.array([0.0, 25.0, 100.0, 500.0])

    low = photodiode.absorption_power(
        position_um, 100.0, 1.0e-3, surface_reflectance=surface_reflectance
    )
    high = photodiode.absorption_power(
        position_um, 100.0, 10.0, surface_reflectance=surface_reflectance
    )
    ratio = high / low
    assert ratio == pytest.approx(np.full(position_um.shape, 1.0e4))

    depths = [
        photodiode.absorption_depth_for_power(
            1.0e-9, 100.0, power, surface_reflectance=surface_reflectance
        )
        for power in (0.01, 0.1, 1.0, 10.0)
    ]
    gains = np.diff(depths)
    expected = photodiode.absorption_depth_gain_per_decade(100.0)
    assert expected == pytest.approx(np.log(10.0) / 100.0 * 1.0e4)
    assert gains == pytest.approx(np.full(gains.shape, expected))

    # alpha alone sets the scale: ten times the absorption, a tenth of the gain.
    assert photodiode.absorption_depth_gain_per_decade(
        1000.0
    ) == pytest.approx(expected / 10.0)


def test_silicon_slab_inverse_design_reference_case():
    reflectance = photodiode.fresnel_reflectance(1.0, 3.5)
    log_transmission = photodiode.slab_log10_transmission(
        thickness_mm=8.0,
        absorption_cm_inv=100.0,
        surface_reflectance=reflectance,
    )
    expected_fraction = (1.0 - reflectance) ** 2 * np.exp(-80.0)

    assert 10.0**log_transmission == pytest.approx(expected_fraction)
    assert log_transmission == pytest.approx(np.log10(expected_fraction))

    required_log_w = photodiode.required_source_log10_power(
        target_transmitted_power_w=0.1,
        thickness_mm=8.0,
        absorption_cm_inv=100.0,
        surface_reflectance=reflectance,
    )
    assert required_log_w == pytest.approx(np.log10(0.1 / expected_fraction))
    assert photodiode.slab_log10_transmission(
        8.0, 100.0, surface_reflectance=1.0, surface_count=0
    ) == pytest.approx(-80.0 / np.log(10.0))


def test_green_2008_silicon_slab_matches_1100_nm_lab_scale():
    absorption, refractive_index = photodiode.silicon_optical_properties(
        1100.0
    )
    assert float(absorption) == pytest.approx(3.5)
    assert float(refractive_index) == pytest.approx(3.542)

    monochromatic = photodiode.silicon_slab_transmission(
        thickness_mm=8.0,
        wavelength_nm=1100.0,
    )
    broadband_led = photodiode.silicon_slab_transmission(
        thickness_mm=8.0,
        wavelength_nm=1100.0,
        source_fwhm_nm=50.0,
    )

    assert monochromatic == pytest.approx(0.0286920525)
    assert broadband_led == pytest.approx(0.0504053049)
    assert 3.0 * monochromatic == pytest.approx(0.0860761576)
    assert 0.1 / monochromatic == pytest.approx(3.48528569)
    assert broadband_led > monochromatic


def test_green_2008_silicon_interpolation_and_validation():
    absorption, refractive_index = photodiode.silicon_optical_properties(
        [1100.0, 1105.0, 1110.0]
    )
    assert absorption[1] == pytest.approx(np.sqrt(3.5 * 2.7))
    assert refractive_index[1] == pytest.approx((3.542 + 3.540) / 2.0)

    with pytest.raises(ValueError):
        photodiode.silicon_optical_properties(899.0)
    with pytest.raises(ValueError):
        photodiode.silicon_slab_transmission(8.0, 1100.0, -1.0)


def test_absorption_coefficient_solves_fractional_transmission_target():
    reflectance = photodiode.fresnel_reflectance(1.0, 3.5)
    alpha = photodiode.absorption_coefficient_for_transmission(
        0.10,
        thickness_mm=8.0,
        surface_reflectance=reflectance,
    )
    achieved_log10 = photodiode.slab_log10_transmission(
        8.0,
        alpha,
        surface_reflectance=reflectance,
    )

    assert 10.0**achieved_log10 == pytest.approx(0.10)
    assert alpha == pytest.approx(1.9553, rel=1.0e-4)


def test_quarter_wave_layer_cancels_design_wavelength_reflection():
    substrate_index = 3.5
    film_index = np.sqrt(substrate_index)
    design_wavelength_um = 1.0
    thickness_um = design_wavelength_um / (4.0 * film_index)
    coated = photodiode.single_layer_reflectance(
        [design_wavelength_um],
        index_incident=1.0,
        index_film=film_index,
        index_substrate=substrate_index,
        thickness_um=thickness_um,
    )
    assert coated[0] == pytest.approx(0.0, abs=1.0e-30)
    assert photodiode.fresnel_reflectance(1.0, 3.5) == pytest.approx(
        0.3086419753
    )


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (photodiode.diffusion_length, (-1.0, 1.0)),
        (photodiode.ideal_spectral_response, ([1.0], 0.0)),
        (photodiode.absorption_intensity, ([-1.0], 100.0)),
        (photodiode.absorption_power, ([1.0], 100.0, 1.0, 1.1)),
        (photodiode.absorption_depth_for_power, (0.0, 100.0, 1.0)),
        (photodiode.absorption_depth_for_power, (1.0e-9, 100.0, -1.0)),
        (photodiode.absorption_depth_gain_per_decade, (0.0,)),
        (photodiode.slab_log10_transmission, (-1.0, 100.0)),
        (photodiode.required_source_log10_power, (0.0, 1.0, 100.0)),
        (
            photodiode.absorption_coefficient_for_transmission,
            (1.1, 1.0),
        ),
        (photodiode.responsivity, ([1.0], 1.1)),
    ],
)
def test_invalid_physical_inputs_are_rejected(function, args):
    with pytest.raises(ValueError):
        function(*args)
