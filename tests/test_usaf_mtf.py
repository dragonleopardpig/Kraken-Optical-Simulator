import csv
import math

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter1d

from KrakenOS.USAFMTF import USAFElementROI, analyze_usaf_image, usaf_frequency


def _bar_image(period=24, cycles=3, sigma=0.0, orientation="vertical"):
    count = period * cycles
    positions = np.arange(count)
    profile = ((positions % period) < period // 2).astype(float)
    if sigma:
        profile = gaussian_filter1d(profile, sigma=sigma, mode="wrap")
    if orientation == "vertical":
        return np.tile(profile, (30, 1))
    return np.tile(profile[:, None], (1, 30))


def test_usaf_frequency_uses_standard_sixth_root_of_two_sequence():
    assert usaf_frequency(0, 1) == 1.0
    assert usaf_frequency(1, 1) == 2.0
    assert usaf_frequency(-2, 1) == 0.25
    assert usaf_frequency(7, 6) == pytest.approx(228.0701, rel=1e-6)


def test_fourier_fit_recovers_gaussian_mtf_for_both_bar_orientations():
    period = 24
    sigma = 2.0
    expected_mtf = math.exp(-2.0 * math.pi**2 * sigma**2 / period**2)
    vertical = _bar_image(period=period, sigma=sigma, orientation="vertical")
    horizontal = _bar_image(period=period, sigma=sigma, orientation="horizontal")

    vertical_result = analyze_usaf_image(
        vertical,
        [USAFElementROI(0, 1, (0, 0, vertical.shape[1], vertical.shape[0]), "vertical")],
    )
    horizontal_result = analyze_usaf_image(
        horizontal,
        [USAFElementROI(0, 1, (0, 0, horizontal.shape[1], horizontal.shape[0]), "horizontal")],
    )

    x_measurement = vertical_result.measurements[0]
    y_measurement = horizontal_result.measurements[0]
    assert x_measurement.response_axis == "x"
    assert y_measurement.response_axis == "y"
    assert x_measurement.measured_cycles_per_pixel == pytest.approx(1 / period, rel=2e-3)
    assert y_measurement.measured_cycles_per_pixel == pytest.approx(1 / period, rel=2e-3)
    assert x_measurement.mtf == pytest.approx(expected_mtf, abs=0.015)
    assert y_measurement.mtf == pytest.approx(expected_mtf, abs=0.015)
    assert x_measurement.fit_r_squared > 0.999


def test_calibration_reports_object_expected_and_measured_image_frequencies():
    image = _bar_image(period=20)
    result = analyze_usaf_image(
        image,
        [USAFElementROI(0, 1, (0, 0, image.shape[1], image.shape[0]), "vertical")],
        magnification=-0.5,
        pixel_pitch_um=100.0,
    )

    measurement = result.measurements[0]
    assert measurement.object_frequency_lp_mm == 1.0
    assert measurement.expected_image_frequency_lp_mm == 2.0
    assert measurement.measured_image_frequency_lp_mm == pytest.approx(0.5, rel=1e-2)
    assert measurement.frequency_error_percent == pytest.approx(-75.0, rel=2e-3)
    frequency, mtf = result.curve("x", frequency_space="image")
    assert frequency.tolist() == [2.0]
    assert mtf.size == 1


def test_duplicate_frequency_curve_uses_median_and_csv_keeps_measurements(tmp_path):
    image = _bar_image()
    rois = [
        USAFElementROI(0, 1, (0, 0, image.shape[1], image.shape[0]), "vertical", label="center"),
        USAFElementROI(0, 1, (0, 0, image.shape[1], image.shape[0]), "vertical", label="repeat"),
    ]
    result = analyze_usaf_image(image, rois)

    frequency, mtf = result.curve("x")
    assert frequency.tolist() == [1.0]
    assert mtf.size == 1

    output = result.save_csv(tmp_path / "curve.csv")
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["label"] for row in rows] == ["center", "repeat"]
    assert rows[0]["roi"] == f"0,0,{image.shape[1]},{image.shape[0]}"


@pytest.mark.parametrize(
    "element, message",
    [
        (USAFElementROI(0, 1, (0, 0, 20, 20), "vertical"), "outside image bounds"),
        ({"group": 0, "element": 1, "roi": [0, 0, 20, 20], "orientation": "diagonal"}, "orientation"),
    ],
)
def test_invalid_roi_inputs_are_rejected(element, message):
    with pytest.raises(ValueError, match=message):
        analyze_usaf_image(np.ones((10, 10)), [element])


def test_vector_artwork_is_not_mistaken_for_a_captured_image(tmp_path):
    svg = tmp_path / "target.svg"
    svg.write_text("<svg/>", encoding="ascii")
    roi = USAFElementROI(0, 1, (0, 0, 20, 20), "vertical")
    with pytest.raises(ValueError, match="captured raster image"):
        analyze_usaf_image(svg, [roi])


def test_element_at_sensor_nyquist_is_rejected():
    profile = np.tile([0.0, 1.0], 6)
    image = np.tile(profile, (12, 1))
    roi = USAFElementROI(0, 1, (0, 0, 12, 12), "vertical", cycles=6)
    with pytest.raises(ValueError, match="Nyquist"):
        analyze_usaf_image(image, [roi])
