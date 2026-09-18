"""Content and numerical regression checks for the Schaum worked documentation."""

import importlib
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.optimize import brentq, minimize_scalar
from scipy.special import fresnel


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


@pytest.fixture
def illustration_module(monkeypatch):
    monkeypatch.syspath_prepend(str(DOCS))
    return importlib.import_module("generate_schaum_optics_illustrations")


def test_complete_generated_collection_and_vector_assets():
    result = subprocess.run(
        [sys.executable, str(DOCS / "validate_schaum_optics_solutions.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "270 distinct" in result.stdout
    assert "55 SVG" in result.stdout


def test_impulse_plots_include_every_position(illustration_module):
    figure, axes = illustration_module.canvas("Impulse extent regression", panels=1)
    positions = [-3, -2, 2, 3]
    illustration_module.impulses(axes[0], positions, [1] * 4)
    left, right = axes[0].get_xlim()
    assert left < min(positions)
    assert right > max(positions)
    illustration_module.plt.close(figure)


@pytest.mark.parametrize("count", [2, 4, 8, 32])
def test_array_factor_peaks_and_internal_nulls(illustration_module, count):
    assert illustration_module.array_factor([0, 1], count) == pytest.approx([1, 1])
    internal_positions = np.arange(1, count) / count
    assert illustration_module.array_factor(internal_positions, count) == pytest.approx(
        np.zeros(count - 1), abs=1e-25
    )


def test_fresnel_normal_brewster_and_total_internal_reflection(illustration_module):
    reflect_s, reflect_p = illustration_module.fresnel_power(
        np.array([0, np.arctan(1.5)])
    )
    assert reflect_s[0] == pytest.approx(0.04)
    assert reflect_p[0] == pytest.approx(0.04)
    assert reflect_p[1] == pytest.approx(0, abs=1e-25)
    reflect_s, reflect_p = illustration_module.fresnel_power(
        np.deg2rad(np.array([45, 60, 80])), 1.5, 1
    )
    assert reflect_s == pytest.approx(np.ones(3))
    assert reflect_p == pytest.approx(np.ones(3))


def test_camera_conjugates_satisfy_both_lens_and_height_constraints():
    object_distance = 2050.0
    image_distance = 51.25
    assert 1 / object_distance + 1 / image_distance == pytest.approx(1 / 50)
    assert image_distance / object_distance == pytest.approx(25 / 1000)


def test_two_lens_virtual_intermediate_object():
    first_image = 1 / (1 / 9 - 1 / 12)
    second_object = 21 - first_image
    second_image = 1 / (-1 / 18 - 1 / second_object)
    magnification = (-first_image / 12) * (-second_image / second_object)
    assert first_image == pytest.approx(36)
    assert second_object == pytest.approx(-15)
    assert second_image == pytest.approx(90)
    assert magnification == pytest.approx(-18)


def test_quarter_wave_film_design():
    layer_index = np.sqrt(2.409)
    thickness_nm = 589 / (4 * layer_index)
    first_reflection = (1 - layer_index) / (1 + layer_index)
    second_reflection = (layer_index - 2.409) / (layer_index + 2.409)
    roundtrip_phase = 4 * np.pi * layer_index * thickness_nm / 589
    total_reflection = (
        first_reflection + second_reflection * np.exp(1j * roundtrip_phase)
    ) / (1 + first_reflection * second_reflection * np.exp(1j * roundtrip_phase))
    assert abs(total_reflection) ** 2 == pytest.approx(0, abs=1e-25)
    assert thickness_nm == pytest.approx(94.87, abs=0.02)


def test_single_slit_half_irradiance_width():
    half_phase = brentq(lambda phase: (np.sin(phase) / phase) ** 2 - 0.5, 1, 2)
    width_mm = 2 * half_phase / np.pi * 632.8
    assert width_mm == pytest.approx(560.5930533)
    assert 2 * half_phase / np.pi == pytest.approx(0.8858929414)


def test_cornu_chord_off_axis_irradiance():
    sine, cosine = fresnel(np.array([1.0, 1.5]))
    irradiance = (np.diff(sine)[0] ** 2 + np.diff(cosine)[0] ** 2) / 2
    assert irradiance == pytest.approx(0.08959356, abs=1e-8)


def test_maximum_axial_slit_irradiance_and_width():
    def irradiance(half_width):
        sine, cosine = fresnel(half_width)
        return 2 * (sine**2 + cosine**2)

    maximum = minimize_scalar(
        lambda half_width: -irradiance(half_width),
        bounds=(0.7, 1.6),
        method="bounded",
    )
    width_mm = 2 * maximum.x * np.sqrt(500e-9 * 0.8 / 2) * 1000
    assert maximum.x == pytest.approx(1.2093767)
    assert -maximum.fun == pytest.approx(1.8014164)
    assert width_mm == pytest.approx(1.0816994)


def test_opaque_strip_babinet_field_not_intensity_subtraction():
    half_width = 0.001766 / 2 * np.sqrt(2 / 693.4e-9)
    sine, cosine = fresnel(half_width)
    slit_field = 2 * (cosine + 1j * sine) / (1 + 1j)
    strip_irradiance = abs(1 - slit_field) ** 2
    assert strip_irradiance == pytest.approx(0.0840462386)


@pytest.mark.parametrize("harmonic", range(1, 9))
def test_ramp_and_step_fourier_coefficients(harmonic):
    cosine_left = quad(
        lambda position: -np.pi * np.cos(harmonic * position), -np.pi, 0
    )[0]
    cosine_right = quad(
        lambda position: position * np.cos(harmonic * position), 0, np.pi
    )[0]
    sine_left = quad(lambda position: -np.pi * np.sin(harmonic * position), -np.pi, 0)[
        0
    ]
    sine_right = quad(
        lambda position: position * np.sin(harmonic * position), 0, np.pi
    )[0]
    assert (cosine_left + cosine_right) / np.pi == pytest.approx(
        ((-1) ** harmonic - 1) / (np.pi * harmonic**2), abs=1e-12
    )
    assert (sine_left + sine_right) / np.pi == pytest.approx(
        (1 - 2 * (-1) ** harmonic) / harmonic, abs=1e-12
    )


def test_windowed_sine_uses_negative_forward_exponential():
    frequency = 2.3
    carrier = 1.4
    half_width = 1.2
    real_part = quad(
        lambda position: np.sin(carrier * position) * np.cos(frequency * position),
        -half_width,
        half_width,
    )[0]
    imaginary_part = quad(
        lambda position: -np.sin(carrier * position) * np.sin(frequency * position),
        -half_width,
        half_width,
    )[0]
    expected = (
        half_width
        / 1j
        * (
            np.sinc((frequency - carrier) * half_width / np.pi)
            - np.sinc((frequency + carrier) * half_width / np.pi)
        )
    )
    assert real_part + 1j * imaginary_part == pytest.approx(expected)


def test_rectangular_convolution_overlap_and_area():
    coordinate = np.linspace(0, 8, 16001)
    overlap = np.maximum(
        0, np.minimum(2, coordinate - 3) - np.maximum(1, coordinate - 5)
    )
    output = 2 * overlap
    assert output.max() == pytest.approx(2)
    assert np.trapezoid(output, coordinate) == pytest.approx(4)
    assert np.interp([4, 5, 6, 7], coordinate, output) == pytest.approx([0, 2, 2, 0])


def test_hexagonal_mask_pair_sum_multiplicities():
    vertices = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]
    counts = Counter(
        (first[0] + second[0], first[1] + second[1])
        for first in vertices
        for second in vertices
    )
    assert len(counts) == 19
    assert counts[(0, 0)] == 6
    assert Counter(counts.values()) == {1: 6, 2: 12, 6: 1}
    assert sum(counts.values()) == 36
