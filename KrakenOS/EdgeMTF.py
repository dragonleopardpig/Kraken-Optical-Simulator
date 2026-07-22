"""Slanted-edge (ISO 12233 style) MTF from a captured edge image.

Complements :mod:`KrakenOS.USAFMTF` (periodic three-bar targets, one MTF point per element).  A
slanted-edge target yields a WHOLE MTF curve from a single region of interest: the sub-pixel edge slant
supersamples the edge-spread function (ESF), whose derivative is the line-spread function (LSF); the
magnitude of the LSF's Fourier transform, normalised at DC, is the MTF.

The edge should cross the ROI at a few degrees off the pixel grid (the standard 5 deg slant) so the
projection oversamples cleanly.  A near-perfectly-axis-aligned edge still works but with less
super-resolution.  Frequency is reported in cycles/pixel (native), optionally converted to
line-pairs/mm at the sensor when a pixel pitch is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv

import numpy as np

from KrakenOS.USAFMTF import load_grayscale_image

__all__ = ["SlantedEdgeMTFResult", "measure_slanted_edge_mtf"]


@dataclass(frozen=True)
class SlantedEdgeMTFResult:
    """Slanted-edge MTF curve and diagnostics."""

    frequency_cycles_per_px: np.ndarray
    mtf: np.ndarray
    edge_angle_deg: float
    oversample: int
    pixel_pitch_um: float | None = None

    def frequency_lp_mm(self) -> np.ndarray | None:
        """Sensor-plane line-pairs/mm, or ``None`` without a pixel pitch."""
        if self.pixel_pitch_um is None:
            return None
        return self.frequency_cycles_per_px * 1000.0 / float(self.pixel_pitch_um)

    def mtf50_cycles_per_px(self) -> float | None:
        """The frequency where MTF first falls to 0.5 (linear interp), or ``None``."""
        f, m = self.frequency_cycles_per_px, self.mtf
        below = np.nonzero(m < 0.5)[0]
        if below.size == 0 or below[0] == 0:
            return None
        i = int(below[0])
        m0, m1, f0, f1 = m[i - 1], m[i], f[i - 1], f[i]
        if m0 == m1:
            return float(f0)
        return float(f0 + (0.5 - m0) * (f1 - f0) / (m1 - m0))

    def curve(self, frequency_space: str = "pixel") -> tuple[np.ndarray, np.ndarray]:
        space = str(frequency_space).strip().lower()
        if space in {"pixel", "cycles/pixel", "cycles_per_px"}:
            return self.frequency_cycles_per_px, self.mtf
        if space in {"image", "sensor", "lp/mm"}:
            lp = self.frequency_lp_mm()
            if lp is None:
                raise ValueError("sensor-space frequency requires pixel_pitch_um")
            return lp, self.mtf
        raise ValueError("frequency_space must be 'pixel' or 'image'")

    def plot(self, frequency_space: str = "pixel", ax=None):
        import matplotlib.pyplot as plt

        if ax is None:
            figure, ax = plt.subplots(figsize=(7.2, 4.8))
        else:
            figure = ax.figure
        freq, mtf = self.curve(frequency_space)
        ax.plot(freq, mtf, color="#176b87", linewidth=1.8, label="Slanted-edge MTF")
        space = str(frequency_space).strip().lower()
        xlabel = "Spatial frequency [cycles/pixel]" if space == "pixel" else "Spatial frequency at sensor [lp/mm]"
        ax.set_xlabel(xlabel)
        ax.set_ylabel("MTF")
        ax.set_title(f"Slanted-edge MTF (edge {self.edge_angle_deg:.1f}°)")
        ax.set_ylim(0.0, 1.05)
        ax.grid(True, alpha=0.25)
        ax.legend()
        figure.tight_layout()
        return figure, ax

    def save_csv(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        lp = self.frequency_lp_mm()
        with output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            header = ["frequency_cycles_per_px", "mtf"]
            if lp is not None:
                header.insert(1, "frequency_lp_mm")
            writer.writerow(header)
            for index in range(self.frequency_cycles_per_px.size):
                row = [f"{self.frequency_cycles_per_px[index]:.6g}", f"{self.mtf[index]:.6g}"]
                if lp is not None:
                    row.insert(1, f"{lp[index]:.6g}")
                writer.writerow(row)
        return output


def _sub_pixel_edge_positions(crop: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row sub-pixel edge column via the centroid of |d/dx intensity|."""
    rows = np.arange(crop.shape[0], dtype=float)
    gradient = np.abs(np.gradient(crop, axis=1))
    weight = gradient.sum(axis=1)
    columns = np.arange(crop.shape[1], dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        centroid = (gradient * columns).sum(axis=1) / weight
    valid = np.isfinite(centroid) & (weight > 0)
    return rows[valid], centroid[valid]


def measure_slanted_edge_mtf(
    image,
    roi: tuple[float, float, float, float] | None = None,
    *,
    pixel_pitch_um: float | None = None,
    oversample: int = 4,
) -> SlantedEdgeMTFResult:
    """Measure the MTF of a slanted-edge target from a captured image (optionally a ROI).

    ``roi`` is ``(x0, y0, x1, y1)`` in image pixels (exclusive upper bounds); ``None`` uses the whole
    image.  The edge may be near-vertical or near-horizontal -- the stronger-gradient axis is detected
    and the image is transposed so the edge runs down the rows.
    """
    gray = load_grayscale_image(image)
    if roi is not None:
        x0, y0, x1, y1 = (int(round(v)) for v in roi)
        h, w = gray.shape
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 - x0 < 8 or y1 - y0 < 8:
            raise ValueError("slanted-edge ROI must be at least 8x8 px over the edge")
        crop = np.asarray(gray[y0:y1, x0:x1], dtype=float)
    else:
        crop = np.asarray(gray, dtype=float)
    if min(crop.shape) < 8:
        raise ValueError("slanted-edge image must be at least 8x8 px")

    # Detect edge orientation: the edge is perpendicular to the axis with the larger mean |gradient|.
    grad_x = float(np.abs(np.diff(crop, axis=1)).mean())
    grad_y = float(np.abs(np.diff(crop, axis=0)).mean())
    transposed = grad_y > grad_x
    work = crop.T if transposed else crop  # now the edge transitions along columns (per row)

    rows, edge_cols = _sub_pixel_edge_positions(work)
    if rows.size < 4:
        raise ValueError("no measurable edge in the ROI (need a clear dark/bright transition)")
    slope, intercept = np.polyfit(rows, edge_cols, 1)
    edge_angle_deg = float(np.degrees(np.arctan(slope)))

    # Project every pixel onto the edge normal: distance = column - fitted_edge_column(row).
    all_rows = np.arange(work.shape[0], dtype=float)
    fitted_edge = slope * all_rows + intercept
    distance = np.arange(work.shape[1], dtype=float)[None, :] - fitted_edge[:, None]
    distance = distance.ravel()
    values = work.ravel()
    finite = np.isfinite(distance) & np.isfinite(values)
    distance, values = distance[finite], values[finite]

    # Bin into a supersampled ESF (bin width = 1/oversample px), then LSF = d/dx ESF.
    oversample = max(2, int(oversample))
    bin_width = 1.0 / oversample
    lo = np.floor(distance.min() / bin_width)
    hi = np.ceil(distance.max() / bin_width)
    edges = (np.arange(lo, hi + 1) * bin_width)
    counts, _ = np.histogram(distance, bins=edges)
    sums, _ = np.histogram(distance, bins=edges, weights=values)
    occupied = counts > 0
    if occupied.sum() < 16:
        raise ValueError("edge projection is too sparse -- use a larger ROI or a more slanted edge")
    esf = np.full(counts.shape, np.nan)
    esf[occupied] = sums[occupied] / counts[occupied]
    idx = np.arange(esf.size, dtype=float)
    esf = np.interp(idx, idx[occupied], esf[occupied])  # fill empty bins

    lsf = np.diff(esf)
    if not np.any(np.abs(lsf) > 0):
        raise ValueError("edge has no measurable contrast")
    window = np.hanning(lsf.size)
    spectrum = np.abs(np.fft.rfft(lsf * window))
    if spectrum[0] <= 0:
        raise ValueError("degenerate edge spectrum")
    mtf = spectrum / spectrum[0]
    frequency = np.fft.rfftfreq(lsf.size, d=bin_width)  # cycles/pixel

    keep = frequency <= 0.5 + 1e-9  # native Nyquist
    return SlantedEdgeMTFResult(
        frequency_cycles_per_px=frequency[keep],
        mtf=mtf[keep],
        edge_angle_deg=edge_angle_deg,
        oversample=oversample,
        pixel_pitch_um=(float(pixel_pitch_um) if pixel_pitch_um else None),
    )
