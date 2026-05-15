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
class SurfaceMesh3D:
    """A render-ready 3-D optical surface mesh record.

    The mesh payload is intentionally typed as ``Any`` so this geometry module
    stays independent of PyVista/VTK while still providing one shared record
    shape for embedded and legacy 3-D renderers.
    """

    row_index: int = 0
    kind: str = "standard"
    mesh: Any = None
    row: Any = None
    surface: Any = None
    color: tuple[float, float, float] = (0.0, 0.55, 1.0)
    opacity: float = 0.68
    is_stop: bool = False
    is_body: bool = False


@dataclass(slots=True)
class BoundaryFace3D:
    """One optical-solid boundary face in world coordinates."""

    object_id: str = ""
    row_index: int = 0
    trace_surface: int | None = None
    face_id: str = ""
    side_2d: str = ""
    function: str = ""
    port_role: str = ""
    material: str = ""
    coating: str = ""
    split_ratio: float | None = None
    loss: float | None = None
    phase_deg: float | None = None
    area_mm2: float = 0.0
    triangle_count: int = 0
    triangle_indices: tuple[int, ...] = ()
    centroid_local: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    normal_local: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    centroid_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    normal_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    source_stl: str = ""
    diagnostics: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OpticalVolume3D:
    """One closed optical volume that owns boundary faces and media."""

    volume_id: str = ""
    object_id: str = ""
    row_index: int = 0
    trace_surface: int | None = None
    volume_type: str = "optical_solid"
    material: str = ""
    ambient_material: str = "AIR"
    source_stl: str = ""
    boundary_face_ids: tuple[str, ...] = ()
    boundary_face_count: int = 0
    centroid_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    bounds_min_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    bounds_max_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    diagnostics: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SceneSource3D:
    """One source object in the non-sequential scene.

    The implementation maps the Source panel and layout-defined
    ``SETTINGS["scene_sources"]`` records into this shared scene object shape.
    Source objects are intentionally not KrakenOS surface rows; a future visible
    source row in the editor must preserve a separate UI-row to trace-surface
    index map.
    """

    source_id: str = "source:0"
    name: str = "Source 1"
    role: str = "illumination"      # illumination or pupil_field_reference
    model: str = ""
    enabled: bool = True
    physical: bool = True
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=float))
    direction: np.ndarray = field(default_factory=lambda: np.asarray((0.0, 0.0, 1.0), dtype=float))
    ray_count: int = 1
    wavelength: float | None = None
    power: float | None = None
    weight_per_ray: float | None = None
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RayHit3D:
    """One traced ray interaction recorded from KrakenOS raykeeper data."""

    step: int = 0
    branch_id: int = 0
    surface_id: int | None = None
    name: str = ""
    material: str = ""
    point_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    incoming_direction: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    outgoing_direction: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    surface_normal: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    n0: float | None = None
    n1: float | None = None
    distance: float | None = None
    optical_path: float | None = None
    rp: float | None = None
    rs: float | None = None
    tp: float | None = None
    ts: float | None = None
    ttbe: float | None = None
    interaction: str = ""
    interaction_model: str = ""
    interaction_target_surface: int | None = None
    interaction_in_power: float | None = None
    interaction_coeff: float | None = None
    interaction_out_power: float | None = None
    interaction_loss_power: float | None = None
    interaction_bulk: float | None = None
    mesh_cell_id: int | None = None
    mesh_original_cell_id: int | None = None
    mesh_face_id: str = ""
    mesh_face_match_method: str = ""
    mesh_face_match_score: float | None = None
    mesh_face_match_warning: str = ""


@dataclass(slots=True)
class RayBranch3D:
    """A contiguous interaction segment within one traced ray path."""

    branch_id: int = 0
    parent_branch_id: int | None = None
    start_step: int = 0
    end_step: int = 0
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    termination_reason: str = ""


@dataclass(slots=True)
class RayPath3D:
    ray_index: int = 0
    source_ray_index: int | None = None
    source_id: str = ""
    source_name: str = ""
    source_role: str = ""
    source_model: str = ""
    source_position: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    source_direction: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    source_power: float | None = None
    source_weight: float | None = None
    field_index: int = 0
    wavelength: float | None = None
    color: str = "#39FF14"
    points_world: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    reaches_image: bool = False
    branch_id: int = 0
    branch_power: float | None = None
    branch_phase_deg: float | None = None
    branch_jones_p: complex = complex(1.0, 0.0)
    branch_jones_s: complex = complex(0.0, 0.0)
    branch_polarization_xyz: np.ndarray = field(default_factory=lambda: np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128))
    branch_label: str = ""
    branch_path: str = ""
    target_surface: int | None = None
    termination_reason: str = ""
    hits: list[RayHit3D] = field(default_factory=list)
    branches: list[RayBranch3D] = field(default_factory=list)


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
    sources: list[SceneSource3D] = field(default_factory=list)
    scene_row_mapping: Any | None = None
    surface_curves: list[SurfaceCurve3D] = field(default_factory=list)
    surface_meshes: list[SurfaceMesh3D] = field(default_factory=list)
    optical_volumes: list[OpticalVolume3D] = field(default_factory=list)
    boundary_faces: list[BoundaryFace3D] = field(default_factory=list)
    ray_paths: list[RayPath3D] = field(default_factory=list)
    planes: list[PlaneMarker] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    pick_regions: list[PickRegion] = field(default_factory=list)
    bounds: BoundsRect = field(default_factory=BoundsRect)
    has_off_axis: bool = False
    max_half: float = 1.0
    display_orientation: str = "YZ"
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
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    branch_label: str = ""
    branch_path: str = ""


@dataclass
class ProjectedScene2D:
    curves: list[ProjectedCurve2D] = field(default_factory=list)
    rays: list[ProjectedRay2D] = field(default_factory=list)
    planes: list[PlaneMarker] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    pick_regions: list[PickRegion] = field(default_factory=list)
    bounds: BoundsRect = field(default_factory=BoundsRect)
