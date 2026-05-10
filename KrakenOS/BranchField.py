from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from types import MappingProxyType
from typing import Mapping

import numpy as np


@dataclass(frozen=True)
class BranchFieldGrid:
    """Scalar complex field sampled on a branch-local rectangular grid.

    The first Phase 8 field contract intentionally uses the same discrete power
    convention as the existing coherent detector and diffraction validators:
    ``total_power = sum(abs(field)**2)``. Later UI code can attach physical
    pixel-area scaling in metadata without changing this stable base contract.
    """

    field: np.ndarray
    x_edges_mm: np.ndarray
    y_edges_mm: np.ndarray
    wavelength_um: float
    refractive_index: float = 1.0
    z_mm: float = 0.0
    label: str = ""
    component: str = "scalar"
    metadata: Mapping[str, object] = dataclass_field(default_factory=dict)

    def __post_init__(self) -> None:
        field = np.asarray(self.field, dtype=np.complex128)
        x_edges = np.asarray(self.x_edges_mm, dtype=float).reshape(-1)
        y_edges = np.asarray(self.y_edges_mm, dtype=float).reshape(-1)
        if field.ndim != 2:
            raise ValueError("BranchFieldGrid.field must be a 2-D complex array.")
        if x_edges.size != field.shape[0] + 1:
            raise ValueError("x_edges_mm must have field.shape[0] + 1 samples.")
        if y_edges.size != field.shape[1] + 1:
            raise ValueError("y_edges_mm must have field.shape[1] + 1 samples.")
        if not np.all(np.isfinite(x_edges)) or not np.all(np.diff(x_edges) > 0.0):
            raise ValueError("x_edges_mm must be finite and strictly increasing.")
        if not np.all(np.isfinite(y_edges)) or not np.all(np.diff(y_edges) > 0.0):
            raise ValueError("y_edges_mm must be finite and strictly increasing.")
        wavelength = float(self.wavelength_um)
        refractive_index = float(self.refractive_index)
        if not np.isfinite(wavelength) or wavelength <= 0.0:
            raise ValueError("wavelength_um must be positive.")
        if not np.isfinite(refractive_index) or refractive_index <= 0.0:
            raise ValueError("refractive_index must be positive.")
        object.__setattr__(self, "field", field)
        object.__setattr__(self, "x_edges_mm", x_edges)
        object.__setattr__(self, "y_edges_mm", y_edges)
        object.__setattr__(self, "wavelength_um", wavelength)
        object.__setattr__(self, "refractive_index", refractive_index)
        object.__setattr__(self, "z_mm", float(self.z_mm))
        object.__setattr__(self, "label", str(self.label or ""))
        object.__setattr__(self, "component", str(self.component or "scalar"))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata or {})))

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.field.shape[0]), int(self.field.shape[1])

    @property
    def x_centers_mm(self) -> np.ndarray:
        return 0.5 * (self.x_edges_mm[:-1] + self.x_edges_mm[1:])

    @property
    def y_centers_mm(self) -> np.ndarray:
        return 0.5 * (self.y_edges_mm[:-1] + self.y_edges_mm[1:])

    @property
    def dx_mm(self) -> float:
        return float(np.median(np.diff(self.x_edges_mm)))

    @property
    def dy_mm(self) -> float:
        return float(np.median(np.diff(self.y_edges_mm)))

    @property
    def intensity(self) -> np.ndarray:
        return np.abs(self.field) ** 2

    @property
    def total_power(self) -> float:
        return float(np.sum(self.intensity))

    @property
    def peak_intensity(self) -> float:
        return float(np.max(self.intensity)) if self.field.size else 0.0

    def centroid_mm(self) -> tuple[float, float]:
        """Return the intensity-weighted field centroid in millimeters."""

        intensity = self.intensity
        power = float(np.sum(intensity))
        if power <= 0.0:
            return float("nan"), float("nan")
        x_grid, y_grid = np.meshgrid(self.x_centers_mm, self.y_centers_mm, indexing="ij")
        x_mean = float(np.sum(x_grid * intensity) / power)
        y_mean = float(np.sum(y_grid * intensity) / power)
        return x_mean, y_mean

    def second_moment_radius_mm(self) -> float:
        """Return the Gaussian-equivalent 1/e^2 radius from second moments."""

        intensity = self.intensity
        power = float(np.sum(intensity))
        if power <= 0.0:
            return float("nan")
        x_grid, y_grid = np.meshgrid(self.x_centers_mm, self.y_centers_mm, indexing="ij")
        x_mean, y_mean = self.centroid_mm()
        variance = float(np.sum(((x_grid - x_mean) ** 2 + (y_grid - y_mean) ** 2) * intensity) / power)
        return float(np.sqrt(max(2.0 * variance, 0.0)))

    def with_field(
        self,
        field: np.ndarray,
        *,
        z_mm: float | None = None,
        label: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> "BranchFieldGrid":
        next_metadata = dict(self.metadata)
        if metadata:
            next_metadata.update(dict(metadata))
        return BranchFieldGrid(
            field=np.asarray(field, dtype=np.complex128),
            x_edges_mm=self.x_edges_mm,
            y_edges_mm=self.y_edges_mm,
            wavelength_um=self.wavelength_um,
            refractive_index=self.refractive_index,
            z_mm=self.z_mm if z_mm is None else float(z_mm),
            label=self.label if label is None else str(label),
            component=self.component,
            metadata=next_metadata,
        )


@dataclass(frozen=True)
class GaussianModeOverlap:
    overlap: complex
    efficiency: float
    phase_rad: float
    field_power: float
    mode_power: float


def branch_field_from_detector_data(
    data: Mapping[str, object],
    *,
    component: str = "field",
    wavelength_um: float | None = None,
    label: str | None = None,
) -> BranchFieldGrid:
    """Build a ``BranchFieldGrid`` from UI coherent-detector data."""

    if component not in data:
        raise KeyError(f"Detector data does not contain component {component!r}.")
    wavelength = float(wavelength_um if wavelength_um is not None else data.get("wavelength_um", 0.0) or 0.0)
    if wavelength <= 0.0:
        raise ValueError("wavelength_um is required when detector data does not carry it.")
    metadata = {
        "filter_text": str(data.get("filter_text", "") or ""),
        "terminal_label": str(data.get("terminal_label", "") or ""),
        "coordinate_label": str(data.get("coordinate_label", "") or ""),
        "coherence_mode": str(data.get("coherence_mode", "") or ""),
        "sample_count": int(data.get("sample_count", 0) or 0),
        "bins": int(data.get("bins", 0) or 0),
    }
    return BranchFieldGrid(
        field=np.asarray(data[component], dtype=np.complex128),
        x_edges_mm=np.asarray(data["x_edges"], dtype=float),
        y_edges_mm=np.asarray(data["y_edges"], dtype=float),
        wavelength_um=wavelength,
        refractive_index=1.0,
        label=label or str(data.get("terminal_label", "") or "Detector branch field"),
        component=component,
        metadata=metadata,
    )


def make_gaussian_tem00_field(
    *,
    x_edges_mm: np.ndarray,
    y_edges_mm: np.ndarray,
    wavelength_um: float,
    waist_radius_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
    power: float = 1.0,
    refractive_index: float = 1.0,
    phase_rad: float = 0.0,
    label: str = "Gaussian TEM00",
) -> BranchFieldGrid:
    """Create a normalized waist-plane scalar TEM00 field on the given grid."""

    waist = float(waist_radius_mm)
    if not np.isfinite(waist) or waist <= 0.0:
        raise ValueError("waist_radius_mm must be positive.")
    target_power = float(power)
    if not np.isfinite(target_power) or target_power <= 0.0:
        raise ValueError("power must be positive.")
    x_edges = np.asarray(x_edges_mm, dtype=float)
    y_edges = np.asarray(y_edges_mm, dtype=float)
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    y_centers = 0.5 * (y_edges[:-1] + y_edges[1:])
    x_grid, y_grid = np.meshgrid(x_centers, y_centers, indexing="ij")
    radius_sq = (x_grid - float(center_x_mm)) ** 2 + (y_grid - float(center_y_mm)) ** 2
    field = np.exp(-radius_sq / (waist * waist)).astype(np.complex128) * np.exp(1j * float(phase_rad))
    current_power = float(np.sum(np.abs(field) ** 2))
    if current_power <= 0.0:
        raise ValueError("Gaussian field has zero sampled power on this grid.")
    field *= np.sqrt(target_power / current_power)
    return BranchFieldGrid(
        field=field,
        x_edges_mm=x_edges,
        y_edges_mm=y_edges,
        wavelength_um=float(wavelength_um),
        refractive_index=float(refractive_index),
        label=label,
        component="scalar",
        metadata={
            "model": "TEM00 waist-plane scalar Gaussian",
            "waist_radius_mm": float(waist_radius_mm),
            "center_x_mm": float(center_x_mm),
            "center_y_mm": float(center_y_mm),
        },
    )


def propagate_branch_field(
    grid: BranchFieldGrid,
    distance_mm: float,
    *,
    model: str = "paraxial",
) -> BranchFieldGrid:
    """Propagate a scalar branch field through homogeneous free space.

    ``model='paraxial'`` uses the Fresnel transfer function with unitary FFT
    normalization, so the discrete power convention is conserved exactly up to
    floating point roundoff.
    """

    model_text = str(model or "paraxial").strip().lower()
    if model_text != "paraxial":
        raise ValueError("Only model='paraxial' is implemented in the first Phase 8 field slice.")
    z_mm = float(distance_mm)
    if not np.isfinite(z_mm):
        raise ValueError("distance_mm must be finite.")
    field = np.asarray(grid.field, dtype=np.complex128)
    if abs(z_mm) <= 0.0:
        return grid.with_field(field.copy(), z_mm=grid.z_mm, metadata={"propagation_model": "paraxial"})
    wavelength_mm = grid.wavelength_um * 1e-3
    fx = np.fft.fftfreq(field.shape[0], d=grid.dx_mm)
    fy = np.fft.fftfreq(field.shape[1], d=grid.dy_mm)
    fx_grid, fy_grid = np.meshgrid(fx, fy, indexing="ij")
    k = 2.0 * np.pi * grid.refractive_index / wavelength_mm
    transfer = np.exp(1j * k * z_mm) * np.exp(
        -1j * np.pi * wavelength_mm * z_mm * (fx_grid * fx_grid + fy_grid * fy_grid) / grid.refractive_index
    )
    spectrum = np.fft.fft2(field, norm="ortho")
    propagated = np.fft.ifft2(spectrum * transfer, norm="ortho")
    return grid.with_field(
        propagated,
        z_mm=grid.z_mm + z_mm,
        metadata={
            "propagation_model": "paraxial",
            "last_distance_mm": z_mm,
        },
    )


def gaussian_mode_overlap(
    grid: BranchFieldGrid,
    *,
    waist_radius_mm: float,
    center_x_mm: float = 0.0,
    center_y_mm: float = 0.0,
) -> GaussianModeOverlap:
    """Return normalized overlap against a waist-plane TEM00 reference mode."""

    reference = make_gaussian_tem00_field(
        x_edges_mm=grid.x_edges_mm,
        y_edges_mm=grid.y_edges_mm,
        wavelength_um=grid.wavelength_um,
        waist_radius_mm=waist_radius_mm,
        center_x_mm=center_x_mm,
        center_y_mm=center_y_mm,
        power=1.0,
        refractive_index=grid.refractive_index,
        label="TEM00 reference",
    )
    field = np.asarray(grid.field, dtype=np.complex128)
    mode = np.asarray(reference.field, dtype=np.complex128)
    field_power = float(np.sum(np.abs(field) ** 2))
    mode_power = float(np.sum(np.abs(mode) ** 2))
    if field_power <= 0.0 or mode_power <= 0.0:
        raise ValueError("Field and reference mode powers must be positive.")
    overlap = complex(np.vdot(mode, field) / np.sqrt(mode_power * field_power))
    return GaussianModeOverlap(
        overlap=overlap,
        efficiency=float(abs(overlap) ** 2),
        phase_rad=float(np.angle(overlap)),
        field_power=field_power,
        mode_power=mode_power,
    )
