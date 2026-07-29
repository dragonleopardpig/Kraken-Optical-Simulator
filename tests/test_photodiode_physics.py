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
        (photodiode.responsivity, ([1.0], 1.1)),
    ],
)
def test_invalid_physical_inputs_are_rejected(function, args):
    with pytest.raises(ValueError):
        function(*args)
