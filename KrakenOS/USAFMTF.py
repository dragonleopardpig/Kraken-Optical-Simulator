"""Measure an MTF curve from captured USAF-1951 bar-target images.

This module complements :mod:`KrakenOS.PSFCalc`, which calculates MTF from a
simulated point-spread function.  A USAF target contains finite three-bar
square-wave patterns, so each selected element is reduced to a one-dimensional
profile and fitted in the Fourier domain.  The fitted fundamental modulation
is converted to MTF using the square-wave factor pi/4.

The target regions are deliberately explicit.  Automatic chart recognition is
fragile when captures can be cropped, rotated, perspective-distorted, or
partially outside the field of view.  Use one ROI for each horizontal or
vertical three-bar element that should contribute to the curve.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import csv
import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
from scipy.ndimage import rotate
from scipy.optimize import minimize_scalar


__all__ = [
    "USAFElementROI",
    "USAFMTFMeasurement",
    "USAFMTFResult",
    "analyze_usaf_image",
    "load_grayscale_image",
    "measure_usaf_element",
    "usaf_frequency",
]


_ORIENTATIONS = {"horizontal", "vertical"}
_RESPONSE_AXES = {"x", "y"}


def usaf_frequency(group: int, element: int) -> float:
    """Return the USAF-1951 element frequency in line-pairs/mm.

    The standard geometric sequence is
    ``2 ** (group + (element - 1) / 6)``.  Groups may be negative; elements
    range from 1 through 6.
    """

    if isinstance(group, bool) or int(group) != group:
        raise ValueError("USAF group must be an integer")
    if isinstance(element, bool) or int(element) != element or not 1 <= int(element) <= 6:
        raise ValueError("USAF element must be an integer from 1 through 6")
    return float(2.0 ** (int(group) + (int(element) - 1) / 6.0))


@dataclass(frozen=True)
class USAFElementROI:
    """One USAF-1951 three-bar region in image pixel coordinates.

    Parameters
    ----------
    group, element:
        USAF-1951 group and element identifiers.
    roi:
        ``(x0, y0, x1, y1)`` pixel bounds.  The upper bounds are exclusive.
        Include the complete three-bar pattern but exclude labels and the
        orthogonal pattern beside it.
    orientation:
        Direction of the bars, ``"vertical"`` or ``"horizontal"``.  Vertical
        bars measure response along x; horizontal bars measure response along y.
    rotation_deg:
        Counter-clockwise rotation applied to the cropped image before it is
        projected.  This is a correction supplied by the caller, not an
        automatically estimated chart angle.
    cycles:
        Approximate number of line-pair cycles across the ROI.  A closely
        cropped USAF three-bar element normally contains three cycles.
    label:
        Optional identifier included in CSV output.
    """

    group: int
    element: int
    roi: tuple[float, float, float, float]
    orientation: str
    rotation_deg: float = 0.0
    cycles: float = 3.0
    label: str = ""

    def __post_init__(self) -> None:
        usaf_frequency(self.group, self.element)
        orientation = str(self.orientation).strip().lower()
        if orientation not in _ORIENTATIONS:
            raise ValueError("orientation must be 'horizontal' or 'vertical'")
        object.__setattr__(self, "orientation", orientation)

        if len(self.roi) != 4:
            raise ValueError("roi must contain (x0, y0, x1, y1)")
        roi = tuple(float(value) for value in self.roi)
        if not all(math.isfinite(value) for value in roi):
            raise ValueError("roi coordinates must be finite")
        if roi[2] <= roi[0] or roi[3] <= roi[1]:
            raise ValueError("roi must have positive width and height")
        object.__setattr__(self, "roi", roi)

        if not math.isfinite(self.rotation_deg):
            raise ValueError("rotation_deg must be finite")
        if not math.isfinite(self.cycles) or self.cycles <= 0:
            raise ValueError("cycles must be positive")


@dataclass(frozen=True)
class USAFMTFMeasurement:
    """MTF measurement and diagnostics for one USAF element ROI."""

    group: int
    element: int
    label: str
    orientation: str
    response_axis: str
    roi: tuple[float, float, float, float]
    object_frequency_lp_mm: float
    expected_image_frequency_lp_mm: float | None
    measured_image_frequency_lp_mm: float | None
    measured_cycles_per_pixel: float
    pixels_per_cycle: float
    fundamental_modulation: float
    mtf: float
    fit_r_squared: float
    frequency_error_percent: float | None


@dataclass(frozen=True)
class USAFMTFResult:
    """Collection of USAF measurements with plotting and CSV helpers."""

    measurements: tuple[USAFMTFMeasurement, ...]
    magnification: float | None = None
    pixel_pitch_um: float | None = None
    target_contrast: float = 1.0

    def curve(
        self,
        response_axis: str | None = None,
        frequency_space: str = "object",
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return sorted frequencies and median MTF at duplicate frequencies."""

        if response_axis is not None:
            response_axis = str(response_axis).strip().lower()
            if response_axis not in _RESPONSE_AXES:
                raise ValueError("response_axis must be 'x', 'y', or None")
        frequency_space = str(frequency_space).strip().lower()
        if frequency_space not in {"object", "image"}:
            raise ValueError("frequency_space must be 'object' or 'image'")
        if frequency_space == "image" and self.magnification is None:
            raise ValueError("image-space frequency requires magnification")

        pairs = []
        for measurement in self.measurements:
            if response_axis is not None and measurement.response_axis != response_axis:
                continue
            if frequency_space == "object":
                frequency = measurement.object_frequency_lp_mm
            else:
                frequency = measurement.expected_image_frequency_lp_mm
            if frequency is not None:
                pairs.append((float(frequency), float(measurement.mtf)))

        if not pairs:
            return np.asarray([], dtype=float), np.asarray([], dtype=float)

        grouped: dict[float, list[float]] = {}
        for frequency, mtf in pairs:
            grouped.setdefault(frequency, []).append(mtf)
        frequency = np.asarray(sorted(grouped), dtype=float)
        mtf = np.asarray([np.median(grouped[value]) for value in frequency], dtype=float)
        return frequency, mtf

    def save_csv(self, path: str | Path) -> Path:
        """Write all individual measurements and diagnostics to a CSV file."""

        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        names = [item.name for item in fields(USAFMTFMeasurement)]
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=names)
            writer.writeheader()
            for measurement in self.measurements:
                row = {name: getattr(measurement, name) for name in names}
                row["roi"] = ",".join(f"{value:g}" for value in measurement.roi)
                writer.writerow(row)
        return output

    def plot(
        self,
        frequency_space: str = "object",
        include_origin: bool = True,
        ax=None,
    ):
        """Plot x- and y-response MTF curves and return ``(figure, axes)``."""

        import matplotlib.pyplot as plt

        if ax is None:
            figure, ax = plt.subplots(figsize=(7.2, 4.8))
        else:
            figure = ax.figure

        plotted = False
        for response_axis, marker, color in (("x", "o", "#176b87"), ("y", "s", "#c04b2f")):
            frequency, mtf = self.curve(response_axis, frequency_space)
            if frequency.size == 0:
                continue
            if include_origin:
                frequency = np.concatenate(([0.0], frequency))
                mtf = np.concatenate(([1.0], mtf))
            ax.plot(
                frequency,
                mtf,
                marker=marker,
                color=color,
                linewidth=1.8,
                label=f"{response_axis.upper()} response",
            )
            plotted = True

        if not plotted:
            frequency, mtf = self.curve(None, frequency_space)
            if include_origin and frequency.size:
                frequency = np.concatenate(([0.0], frequency))
                mtf = np.concatenate(([1.0], mtf))
            ax.plot(frequency, mtf, marker="o", color="#263238", linewidth=1.8, label="Mean response")

        space_name = "object" if frequency_space == "object" else "image"
        ax.set_xlabel(f"Spatial frequency at {space_name} [line-pairs/mm]")
        ax.set_ylabel("MTF")
        ax.set_title("USAF-1951 captured-image MTF")
        ax.set_ylim(0.0, max(1.05, ax.get_ylim()[1]))
        ax.grid(True, alpha=0.25)
        ax.legend()
        figure.tight_layout()
        return figure, ax


@dataclass(frozen=True)
class _ProfileFit:
    frequency: float
    modulation: float
    r_squared: float


def load_grayscale_image(image: str | Path | np.ndarray) -> np.ndarray:
    """Load a raster image or convert an array to finite grayscale floats.

    RGB data use Rec. 709 luminance weights.  Alpha is ignored.  SVG input is
    intentionally rejected because a captured raster image, not the vector
    target artwork, is required for a system MTF measurement.
    """

    if isinstance(image, (str, Path)):
        path = Path(image)
        if path.suffix.lower() == ".svg":
            raise ValueError("USAF MTF requires a captured raster image; rasterize or photograph the SVG target")
        try:
            from PIL import Image
        except ImportError as exc:  # pragma: no cover - declared package dependency
            raise ImportError("Pillow is required to load captured image files") from exc
        with Image.open(path) as source:
            array = np.asarray(source)
    else:
        array = np.asarray(image)

    if array.ndim == 2:
        grayscale = array.astype(float, copy=False)
    elif array.ndim == 3 and array.shape[2] in {3, 4}:
        rgb = array[..., :3].astype(float)
        grayscale = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    else:
        raise ValueError("image must be a 2-D grayscale or 3/4-channel RGB array")

    if grayscale.size == 0 or not np.any(np.isfinite(grayscale)):
        raise ValueError("image contains no finite pixels")
    return grayscale


def _crop_profile(image: np.ndarray, element: USAFElementROI) -> np.ndarray:
    x0, y0, x1, y1 = (int(round(value)) for value in element.roi)
    height, width = image.shape
    if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
        raise ValueError(
            f"ROI {element.roi} is outside image bounds (width={width}, height={height})"
        )
    crop = np.asarray(image[y0:y1, x0:x1], dtype=float)
    if min(crop.shape) < 3:
        raise ValueError("ROI must be at least 3 pixels wide and high")
    if element.rotation_deg:
        crop = rotate(
            crop,
            float(element.rotation_deg),
            reshape=False,
            order=1,
            mode="constant",
            cval=np.nan,
            prefilter=False,
        )

    projection_axis = 0 if element.orientation == "vertical" else 1
    with np.errstate(invalid="ignore"):
        profile = np.nanmean(crop, axis=projection_axis)
    profile = np.asarray(profile, dtype=float)
    finite = np.isfinite(profile)
    if np.count_nonzero(finite) < 12:
        raise ValueError("ROI modulation axis must contain at least 12 finite pixels")
    if not np.all(finite):
        positions = np.arange(profile.size, dtype=float)
        profile[~finite] = np.interp(positions[~finite], positions[finite], profile[finite])
    if float(np.ptp(profile)) <= np.finfo(float).eps * max(abs(float(np.mean(profile))), 1.0):
        raise ValueError("ROI profile has no measurable contrast")
    return profile


def _profile_design(positions: np.ndarray, frequency: float, harmonics: Sequence[int]) -> np.ndarray:
    columns = [np.ones_like(positions), positions]
    for harmonic in harmonics:
        phase = 2.0 * np.pi * harmonic * frequency * positions
        columns.extend((np.cos(phase), np.sin(phase)))
    return np.column_stack(columns)


def _fit_profile(profile: np.ndarray, cycles: float, search_fraction: float) -> _ProfileFit:
    if not 0.0 <= search_fraction < 0.8:
        raise ValueError("frequency_search_fraction must be in [0, 0.8)")

    count = profile.size
    positions = np.arange(count, dtype=float) - 0.5 * (count - 1)
    expected = float(cycles) / count
    if expected >= 0.5:
        raise ValueError("USAF element is at or above the image Nyquist frequency")
    lower = max(0.5 / count, expected * (1.0 - search_fraction))
    upper = min(0.45, expected * (1.0 + search_fraction))
    if upper <= lower:
        raise ValueError("ROI is too coarsely sampled for the requested number of cycles")

    # Fit odd harmonics together so a non-integer ROI crop does not leak the
    # square-wave third/fifth harmonics into the fundamental coefficient.
    harmonics = tuple(value for value in (1, 3, 5) if value * upper < 0.49)
    if 1 not in harmonics:
        raise ValueError("USAF element is above the image Nyquist frequency")

    def residual(frequency: float) -> float:
        design = _profile_design(positions, frequency, harmonics)
        coefficients = np.linalg.lstsq(design, profile, rcond=None)[0]
        error = profile - design @ coefficients
        return float(error @ error)

    optimum = minimize_scalar(
        residual,
        bounds=(lower, upper),
        method="bounded",
        options={"xatol": max(1e-9, expected * 1e-6)},
    )
    frequency = float(optimum.x)
    design = _profile_design(positions, frequency, harmonics)
    coefficients = np.linalg.lstsq(design, profile, rcond=None)[0]
    fitted = design @ coefficients

    dc = float(coefficients[0])
    amplitude = float(math.hypot(coefficients[2], coefficients[3]))
    scale = abs(dc)
    if scale <= np.finfo(float).eps * max(float(np.max(np.abs(profile))), 1.0):
        raise ValueError("ROI has a zero or invalid mean intensity")
    modulation = amplitude / scale

    residual_sum = float(np.sum((profile - fitted) ** 2))
    total_sum = float(np.sum((profile - np.mean(profile)) ** 2))
    r_squared = 1.0 - residual_sum / total_sum if total_sum > 0.0 else 0.0
    return _ProfileFit(frequency=frequency, modulation=modulation, r_squared=r_squared)


def measure_usaf_element(
    image: str | Path | np.ndarray,
    element: USAFElementROI | Mapping[str, object],
    *,
    magnification: float | None = None,
    pixel_pitch_um: float | None = None,
    target_contrast: float = 1.0,
    frequency_search_fraction: float = 0.25,
) -> USAFMTFMeasurement:
    """Measure one USAF element from a captured image.

    ``magnification`` is the absolute image/object transverse magnification and
    is needed only to report image-space line-pairs/mm.  ``pixel_pitch_um`` is
    optional and independently converts the fitted cycles/pixel to a measured
    sensor frequency.  MTF itself is dimensionless.
    """

    grayscale = load_grayscale_image(image)
    region = _coerce_element(element)
    magnification = _validate_optional_positive("magnification", magnification)
    pixel_pitch_um = _validate_optional_positive("pixel_pitch_um", pixel_pitch_um)
    if not math.isfinite(target_contrast) or not 0.0 < target_contrast <= 1.0:
        raise ValueError("target_contrast must be in (0, 1]")

    profile = _crop_profile(grayscale, region)
    fitted = _fit_profile(profile, region.cycles, frequency_search_fraction)
    frequency = usaf_frequency(region.group, region.element)
    expected_image_frequency = frequency / magnification if magnification is not None else None
    measured_image_frequency = (
        fitted.frequency * 1000.0 / pixel_pitch_um if pixel_pitch_um is not None else None
    )
    frequency_error = None
    if expected_image_frequency is not None and measured_image_frequency is not None:
        frequency_error = 100.0 * (measured_image_frequency / expected_image_frequency - 1.0)

    # A 50% duty-cycle square wave has fundamental modulation 4/pi times its
    # Michelson contrast.  Divide that known target modulation out of the image.
    mtf = (np.pi / 4.0) * fitted.modulation / target_contrast
    response_axis = "x" if region.orientation == "vertical" else "y"
    return USAFMTFMeasurement(
        group=int(region.group),
        element=int(region.element),
        label=str(region.label),
        orientation=region.orientation,
        response_axis=response_axis,
        roi=region.roi,
        object_frequency_lp_mm=frequency,
        expected_image_frequency_lp_mm=expected_image_frequency,
        measured_image_frequency_lp_mm=measured_image_frequency,
        measured_cycles_per_pixel=fitted.frequency,
        pixels_per_cycle=1.0 / fitted.frequency,
        fundamental_modulation=fitted.modulation,
        mtf=float(mtf),
        fit_r_squared=fitted.r_squared,
        frequency_error_percent=frequency_error,
    )


def analyze_usaf_image(
    image: str | Path | np.ndarray,
    elements: Iterable[USAFElementROI | Mapping[str, object]],
    *,
    magnification: float | None = None,
    pixel_pitch_um: float | None = None,
    target_contrast: float = 1.0,
    frequency_search_fraction: float = 0.25,
) -> USAFMTFResult:
    """Measure all supplied USAF element ROIs from one captured image."""

    grayscale = load_grayscale_image(image)
    magnification = _validate_optional_positive("magnification", magnification)
    pixel_pitch_um = _validate_optional_positive("pixel_pitch_um", pixel_pitch_um)
    regions = tuple(_coerce_element(element) for element in elements)
    if not regions:
        raise ValueError("at least one USAF element ROI is required")

    measurements = tuple(
        measure_usaf_element(
            grayscale,
            region,
            magnification=magnification,
            pixel_pitch_um=pixel_pitch_um,
            target_contrast=target_contrast,
            frequency_search_fraction=frequency_search_fraction,
        )
        for region in regions
    )
    return USAFMTFResult(
        measurements=measurements,
        magnification=magnification,
        pixel_pitch_um=pixel_pitch_um,
        target_contrast=float(target_contrast),
    )


def _coerce_element(element: USAFElementROI | Mapping[str, object]) -> USAFElementROI:
    if isinstance(element, USAFElementROI):
        return element
    if isinstance(element, Mapping):
        data = dict(element)
        if "roi" in data:
            data["roi"] = tuple(data["roi"])
        return USAFElementROI(**data)
    raise TypeError("elements must contain USAFElementROI objects or mappings")


def _validate_optional_positive(name: str, value: float | None) -> float | None:
    if value is None:
        return None
    result = abs(float(value)) if name == "magnification" else float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return result


def _build_argument_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="Measure an MTF curve from a captured USAF-1951 raster image and ROI JSON."
    )
    parser.add_argument("image", type=Path, help="Captured PNG, TIFF, JPEG, or other Pillow raster image")
    parser.add_argument("config", type=Path, help="JSON file containing a 'rois' array and optional calibration")
    parser.add_argument("--csv", type=Path, help="Output CSV path (default: <image>_mtf.csv)")
    parser.add_argument("--plot", type=Path, help="Output plot path (default: <image>_mtf.png)")
    parser.add_argument(
        "--frequency-space",
        choices=("object", "image"),
        default="object",
        help="Plot object-space or image-space line-pairs/mm",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line implementation used by :mod:`KrakenOS.USAFMTFCLI`."""

    parser = _build_argument_parser()
    args = parser.parse_args(argv)
    with args.config.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    if not isinstance(config, Mapping) or not isinstance(config.get("rois"), list):
        parser.error("config JSON must be an object containing a 'rois' array")

    result = analyze_usaf_image(
        args.image,
        config["rois"],
        magnification=config.get("magnification"),
        pixel_pitch_um=config.get("pixel_pitch_um"),
        target_contrast=config.get("target_contrast", 1.0),
        frequency_search_fraction=config.get("frequency_search_fraction", 0.25),
    )
    csv_path = args.csv or args.image.with_name(f"{args.image.stem}_mtf.csv")
    plot_path = args.plot or args.image.with_name(f"{args.image.stem}_mtf.png")
    if args.frequency_space == "image" and result.magnification is None:
        parser.error("--frequency-space image requires 'magnification' in the JSON config")
    result.save_csv(csv_path)

    import matplotlib.pyplot as plt

    figure, _axes = result.plot(frequency_space=args.frequency_space)
    figure.savefig(plot_path, dpi=160)
    plt.close(figure)

    print(f"Wrote {csv_path}")
    print(f"Wrote {plot_path}")
    for measurement in result.measurements:
        print(
            f"G{measurement.group} E{measurement.element} {measurement.response_axis.upper()}: "
            f"{measurement.object_frequency_lp_mm:.6g} lp/mm, "
            f"MTF={measurement.mtf:.4f}, R^2={measurement.fit_r_squared:.4f}, "
            f"sampling={measurement.pixels_per_cycle:.2f} px/cycle"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
