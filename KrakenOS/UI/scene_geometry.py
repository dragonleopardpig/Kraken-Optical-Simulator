"""Scene geometry data types for the KrakenOS layout display pipeline.

These are plain dataclasses that carry world-space and projected geometry
between the scene builder, projector, and renderers.  They have no
dependency on matplotlib, VTK, or tkinter.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StyleHint:
    color: str = "#202020"
    linewidth: float = 1.4
    alpha: float = 0.9
    zorder: float = 0.0


# ---------------------------------------------------------------------------
# World-space scene objects
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SurfaceCurve3D:
    """A single surface cross-section in display coordinates.

    *points_world* is (N, 2) for the current 2-D display path.
    Future phases may lift this to (N, 3) for true world coordinates.
    """

    row_index: int = 0
    kind: str = "standard"          # standard, mirror, aperture, thin_lens, grating, lens_edge, object, image
    points_world: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))
    style: StyleHint = field(default_factory=StyleHint)


@dataclass(slots=True)
class RayPath3D:
    ray_index: int = 0
    field_index: int = 0
    wavelength: float | None = None
    color: str = "#39FF14"
    points_world: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    reaches_image: bool = False


@dataclass(slots=True)
class PlaneMarker:
    """Cardinal / reference plane marker.

    *kind*: ``"object"``, ``"image"``, ``"stop"``, ``"front_pp"``,
    ``"back_pp"``, ``"ep"``, ``"xp"``.
    """

    kind: str = "object"
    z_position: float = 0.0
    label: str = ""
    color: str = "#202020"


@dataclass(slots=True)
class LabelSpec:
    text: str = ""
    x: float = 0.0
    y: float = 0.0
    row_index: int | None = None
    fontsize: float = 9.0
    color: str = "#202020"
    ha: str = "center"
    va: str = "bottom"


@dataclass(slots=True)
class PickRegion:
    row_index: int = 0
    polylines: list[np.ndarray] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Bounds
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BoundsRect:
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0

    @classmethod
    def from_points(cls, points_list: list[np.ndarray]) -> BoundsRect:
        xs: list[float] = []
        ys: list[float] = []
        for pts in points_list:
            arr = np.asarray(pts, dtype=float)
            if arr.ndim != 2 or arr.shape[0] == 0:
                continue
            finite = np.isfinite(arr[:, 0]) & np.isfinite(arr[:, 1])
            if np.any(finite):
                xs.extend(arr[finite, 0].tolist())
                ys.extend(arr[finite, 1].tolist())
        if not xs:
            return cls()
        return cls(x_min=min(xs), x_max=max(xs), y_min=min(ys), y_max=max(ys))

    def margin(self, fraction_x: float = 0.08, fraction_y: float = 0.12) -> BoundsRect:
        sx = max(self.x_max - self.x_min, 1.0)
        sy = max(self.y_max - self.y_min, 1.0)
        return BoundsRect(
            x_min=self.x_min - fraction_x * sx,
            x_max=self.x_max + fraction_x * sx,
            y_min=self.y_min - fraction_y * sy,
            y_max=self.y_max + fraction_y * sy,
        )

    @property
    def is_empty(self) -> bool:
        return self.x_min >= self.x_max and self.y_min >= self.y_max


# ---------------------------------------------------------------------------
# Scene bundle — the main output of the scene builder
# ---------------------------------------------------------------------------

@dataclass
class SceneBundle:
    surface_curves: list[SurfaceCurve3D] = field(default_factory=list)
    ray_paths: list[RayPath3D] = field(default_factory=list)
    planes: list[PlaneMarker] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    pick_regions: list[PickRegion] = field(default_factory=list)
    bounds: BoundsRect = field(default_factory=BoundsRect)
    has_off_axis: bool = False
    max_half: float = 1.0
    display_orientation: str = "Vertical"
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Projected (2-D display) objects
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProjectedCurve2D:
    row_index: int = 0
    kind: str = "standard"
    points_2d: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))
    style: StyleHint = field(default_factory=StyleHint)


@dataclass(slots=True)
class ProjectedRay2D:
    ray_index: int = 0
    field_index: int = 0
    color: str = "#39FF14"
    points_2d: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))
    reaches_image: bool = False


@dataclass
class ProjectedScene2D:
    curves: list[ProjectedCurve2D] = field(default_factory=list)
    rays: list[ProjectedRay2D] = field(default_factory=list)
    planes: list[PlaneMarker] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    pick_regions: list[PickRegion] = field(default_factory=list)
    bounds: BoundsRect = field(default_factory=BoundsRect)
