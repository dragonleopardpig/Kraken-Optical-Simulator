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
    linestyle: str = "-"


# ---------------------------------------------------------------------------
# World-space scene objects
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SurfaceCurve3D:
    """A single surface cross-section in scene/world coordinates.

    *points_world* is normally (N, 3) in Kraken world axes ``(X, Y, Z)``.
    Some legacy display-only overlays still use (N, 2) YZ display fallback
    points until their owning builders are lifted to native scene geometry.
    *coordinate_space* records that provenance so the projector can avoid
    drawing display-only geometry as a plausible but false physical slice.
    """

    row_index: int = 0
    kind: str = "standard"          # standard, mirror, aperture, thin_lens, grating, lens_edge, object, image
    points_world: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    style: StyleHint = field(default_factory=StyleHint)
    coordinate_space: str = "world"  # world, legacy_yz_display, folded_yz_display


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
    # When True the mesh is a synthetic "missing CAD asset" placeholder
    # (red wireframe box). The scene refresh draws it with a dedicated
    # style instead of routing through the analytic / glassy paths so
    # the user can immediately tell which rows have unresolved CAD
    # references without digging through ~/.cache/krakenos logs.
    is_missing_placeholder: bool = False


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
class SceneTarget3D:
    """One object, detector, aperture, or analysis target in the scene graph."""

    target_id: str = ""
    name: str = ""
    role: str = "analysis_target"
    row_index: int = 0
    trace_surface: int | None = None
    surface: str = ""
    material: str = ""
    center_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    normal_world: np.ndarray = field(default_factory=lambda: np.asarray((0.0, 0.0, 1.0), dtype=float))
    tangent_world: np.ndarray = field(default_factory=lambda: np.asarray((0.0, 1.0, 0.0), dtype=float))
    diameter: float = 0.0
    active_width_mm: float = 0.0
    active_height_mm: float = 0.0
    detector_bins: str = ""
    pixel_pitch_um: float = 0.0
    is_detector: bool = False
    is_object: bool = False
    is_active_target: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def _unit_vector_or_none(value: Any) -> np.ndarray | None:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector)):
        return None
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return vector / norm


def _target_frame_axes(target: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    try:
        center = np.asarray(getattr(target, "center_world", np.full(3, np.nan)), dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if center.size < 3 or not np.all(np.isfinite(center)):
        return None
    normal = _unit_vector_or_none(getattr(target, "normal_world", None))
    if normal is None:
        normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
    tangent = _unit_vector_or_none(getattr(target, "tangent_world", None))
    if tangent is None:
        tangent = np.asarray((0.0, 1.0, 0.0), dtype=float)
    tangent = tangent - normal * float(np.dot(tangent, normal))
    tangent = _unit_vector_or_none(tangent)
    if tangent is None:
        fallback = np.asarray((1.0, 0.0, 0.0), dtype=float)
        if abs(float(np.dot(fallback, normal))) > 0.95:
            fallback = np.asarray((0.0, 1.0, 0.0), dtype=float)
        tangent = _unit_vector_or_none(fallback - normal * float(np.dot(fallback, normal)))
    if tangent is None:
        return None
    bitangent = _unit_vector_or_none(np.cross(normal, tangent))
    if bitangent is None:
        return None
    return center, tangent, bitangent


def scene_target_active_dimensions(target: Any) -> tuple[float, float] | None:
    """Return active detector width/height in mm, falling back to diameter."""
    try:
        diameter = max(float(getattr(target, "diameter", 0.0) or 0.0), 0.0)
    except Exception:
        diameter = 0.0
    try:
        width = max(float(getattr(target, "active_width_mm", 0.0) or 0.0), 0.0)
    except Exception:
        width = 0.0
    try:
        height = max(float(getattr(target, "active_height_mm", 0.0) or 0.0), 0.0)
    except Exception:
        height = 0.0
    if width <= 1e-12:
        width = diameter
    if height <= 1e-12:
        height = diameter
    if width <= 1e-12 or height <= 1e-12:
        return None
    return float(width), float(height)


def scene_target_active_footprint_polylines(target: Any) -> list[np.ndarray]:
    """Return world-space active detector rectangle and center crosshair."""
    if not bool(getattr(target, "is_detector", False)):
        return []
    dimensions = scene_target_active_dimensions(target)
    axes = _target_frame_axes(target)
    if dimensions is None or axes is None:
        return []
    width, height = dimensions
    center, tangent, bitangent = axes
    half_w = 0.5 * float(width)
    half_h = 0.5 * float(height)
    # tangent is the vertical/meridional axis (default +Y), bitangent the
    # horizontal/sagittal axis: a landscape sensor's width spans bitangent
    # (horizontal) and its height spans tangent (vertical).
    corners = np.vstack(
        (
            center - bitangent * half_w - tangent * half_h,
            center + bitangent * half_w - tangent * half_h,
            center + bitangent * half_w + tangent * half_h,
            center - bitangent * half_w + tangent * half_h,
            center - bitangent * half_w - tangent * half_h,
        )
    )
    cross = max(min(float(min(width, height)) * 0.12, float(max(width, height)) * 0.30), 0.25)
    return [
        corners,
        np.vstack((center - tangent * cross, center + tangent * cross)),
        np.vstack((center - bitangent * cross, center + bitangent * cross)),
    ]


def scene_target_detector_miss_crosshair_polylines(path: Any, target: Any) -> list[np.ndarray]:
    """Return world-space crosshair lines at a missed-detector terminal point."""
    if ray_path_terminal_status_from_events(path) != "missed_detector":
        return []
    event = ray_path_terminal_event(path)
    if event is None:
        return []
    try:
        point = np.asarray(getattr(event, "point_world", np.full(3, np.nan)), dtype=float).reshape(-1)[:3]
    except Exception:
        return []
    if point.size < 3 or not np.all(np.isfinite(point)):
        return []
    dimensions = scene_target_active_dimensions(target)
    axes = _target_frame_axes(target)
    if dimensions is None or axes is None:
        return []
    width, height = dimensions
    _center, tangent, bitangent = axes
    arm = max(min(float(min(width, height)) * 0.18, float(max(width, height)) * 0.35), 0.35)
    return [
        np.vstack((point - tangent * arm, point + tangent * arm)),
        np.vstack((point - bitangent * arm, point + bitangent * arm)),
    ]


@dataclass(slots=True)
class ScenePlacement3D:
    """Row-backed 3-D placement state for direct scene authoring.

    This record is not a separate optical object.  It makes the editable row
    pose, target/solid identity, grid preference, and snap spacing visible to
    scene consumers so future 3-D placement handles can update KrakenOS-native
    state instead of keeping a viewer-only transform.
    """

    placement_id: str = ""
    row_index: int = 0
    trace_surface: int | None = None
    target_id: str = ""
    object_id: str = ""
    source_kind: str = "surface_row"
    center_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    normal_world: np.ndarray = field(default_factory=lambda: np.asarray((0.0, 0.0, 1.0), dtype=float))
    tangent_world: np.ndarray = field(default_factory=lambda: np.asarray((0.0, 1.0, 0.0), dtype=float))
    pose_translation: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=float))
    pose_rotation_deg: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=float))
    anchor: str = "row_pose"
    snap_enabled: bool = False
    snap_mm: float = 1.0
    snap_deg: float = 5.0
    grid_visible: bool = True
    grid_spacing_mm: float = 10.0
    grid_extent_mm: float = 100.0
    metadata: dict[str, Any] = field(default_factory=dict)


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
    volume_id: str = ""
    media_in: str = ""
    media_out: str = ""
    media_transition: str = ""
    media_state_method: str = ""
    media_state_diagnostic: str = ""
    inside_volumes_before: str = ""
    inside_volumes_after: str = ""
    mesh_cell_id: int | None = None
    mesh_original_cell_id: int | None = None
    mesh_face_id: str = ""
    mesh_face_match_method: str = ""
    mesh_face_match_score: float | None = None
    mesh_face_match_warning: str = ""


@dataclass(slots=True)
class RayEvent3D:
    """Canonical read-only ray event mirrored from raykeeper/scene metadata."""

    event_id: str = ""
    event_kind: str = "surface"
    event_type: str = ""
    ray_index: int = 0
    source_ray_index: int | None = None
    source_id: str = ""
    source_name: str = ""
    source_role: str = ""
    source_model: str = ""
    wavelength: float | None = None
    launch_field_requested: int | None = None
    launch_field_effective: int | None = None
    launch_field_basis: str = ""
    launch_field_unit: str = ""
    launch_field_min: float | None = None
    launch_field_max: float | None = None
    launch_field_active: bool | None = None
    launch_ray_count: int | None = None
    launch_pupil_pattern: str = ""
    launch_trace_intent: str = ""
    launch_sampling_mode: str = ""
    branch_id: int = 0
    branch_path: str = ""
    branch_power: float | None = None
    branch_phase_deg: float | None = None
    step: int = 0
    surface_id: int | None = None
    surface_name: str = ""
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
    interaction_model: str = ""
    interaction_target_surface: int | None = None
    interaction_in_power: float | None = None
    interaction_coeff: float | None = None
    interaction_out_power: float | None = None
    interaction_loss_power: float | None = None
    interaction_bulk: float | None = None
    volume_id: str = ""
    media_in: str = ""
    media_out: str = ""
    media_transition: str = ""
    media_state_method: str = ""
    media_state_diagnostic: str = ""
    inside_volumes_before: str = ""
    inside_volumes_after: str = ""
    mesh_cell_id: int | None = None
    mesh_original_cell_id: int | None = None
    mesh_face_id: str = ""
    mesh_face_match_method: str = ""
    mesh_face_match_score: float | None = None
    mesh_face_match_warning: str = ""
    termination_reason: str = ""
    diagnostic: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RayBranch3D:
    """A contiguous interaction segment within one traced ray path."""

    branch_id: int = 0
    parent_branch_id: int | None = None
    start_step: int = 0
    end_step: int = 0
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    termination_reason: str = ""
    termination_diagnostic: str = ""


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
    termination_diagnostic: str = ""
    branch_tree_diagnostic: str = ""
    display_geometry_source: str = ""
    display_geometry_diagnostic: str = ""
    hits: list[RayHit3D] = field(default_factory=list)
    events: list[RayEvent3D] = field(default_factory=list)
    branches: list[RayBranch3D] = field(default_factory=list)


def ray_path_reaches_image_from_events(path: Any) -> bool:
    """Return detector/image reach from the path's terminal event when present."""
    status = ray_path_terminal_status_from_events(path)
    if status:
        return status == "hit_detector"
    return bool(getattr(path, "reaches_image", False))


_NON_REFRACTIVE_STEERING_TOKENS = (
    "reflect",
    "mirror",
    "tir",
    "split",
    "scatter",
    "diffract",
    "grating",
    "fold",
)


def ray_path_has_non_refractive_steering(path: Any) -> bool:
    """Return whether a ray path was deliberately folded by a surface.

    True when any traced surface event reflects / splits / folds the ray (a beam
    splitter, fold mirror, TIR, grating, ...). This distinguishes a genuine
    folded branch -- e.g. a beam-splitter cube's reflected "second path" -- from
    a ray that merely refracted straight through the optics. The same token list
    drives the traced optical-axis builder, so the display filter and the axis
    builder agree on what counts as a fold.
    """
    for event in list(getattr(path, "events", []) or []):
        if str(getattr(event, "event_kind", "") or "") != "surface":
            continue
        text = " ".join(
            (
                str(getattr(event, "event_type", "") or ""),
                str(getattr(event, "interaction_model", "") or ""),
                str(getattr(event, "surface_name", "") or ""),
            )
        ).strip().lower()
        if any(token in text for token in _NON_REFRACTIVE_STEERING_TOKENS):
            return True
    return False


def ray_path_visible_without_clipping_from_events(path: Any) -> bool:
    """Return whether a ray should display with "Show Clipped Rays" OFF.

    With clipping OFF the 3D scene shows the same rays the 2D plot keeps: the
    rays that actually land on the detector, plus any deliberately *folded*
    branch. Everything else -- rays vignetted at an aperture stop or lens rim
    (``stopped``), rays that traversed the optics but missed the detector's
    clear aperture (``missed_detector``), rays absorbed on a surface, and rays
    that escaped the system entirely -- is treated as a clipped ray and hidden
    until the user opts in. This makes the 3D filter agree with 2D, which keeps
    only detector hits when clipping is OFF (bug 0062). Previously the 3D filter
    hid only non-folded *escapes*, so vignetted strays that stopped on a surface
    still rendered in 3D after the user turned clipping off.

    Folds always survive (bugs 0016 / 0018): a ray that underwent a deliberate
    fold -- reflection off a beam splitter / mirror, TIR, grating -- is a real
    branch the user authored, e.g. the beam-splitter's reflected "second path".
    Such a branch often travels nearly parallel to the image plane with no
    downstream detector to land on, yet the user expects to see it, so it stays
    visible even with Show Clipped Rays OFF regardless of its terminal status.
    The bug-0022 don't-blank fallback (in the 3D ray filter) still applies on
    top of this, so a scene whose rays would *all* be hidden shows them anyway.
    """
    status = ray_path_terminal_status_from_events(path)
    if status == "hit_detector":
        return True
    if ray_path_has_non_refractive_steering(path):
        return True
    if status:
        return False
    return bool(getattr(path, "reaches_image", False))


def ray_path_terminal_status_from_events(path: Any) -> str:
    """Return a compact display terminal status from the path's terminal event."""
    for event in reversed(list(getattr(path, "events", []) or [])):
        if str(getattr(event, "event_kind", "") or "") != "terminal":
            continue
        metadata = dict(getattr(event, "metadata", {}) or {})
        folded_status = str(metadata.get("folded_display_status", "") or "").strip().lower()
        folded_authoritative = _metadata_bool(metadata.get("folded_display_authoritative"))
        if folded_authoritative and folded_status in {"hit_detector", "missed_detector", "missed_image", "detector_miss"}:
            return "hit_detector" if folded_status == "hit_detector" else "missed_detector"
        reason = str(
            getattr(event, "termination_reason", "")
            or getattr(event, "event_type", "")
            or ""
        ).strip().lower()
        if (
            _metadata_bool(metadata.get("reaches_image"))
            or _metadata_bool(metadata.get("reaches_detector"))
            or reason in {"image", "detector", "hit_detector"}
        ):
            return "hit_detector"
        if "missed_image" in reason or "missed_detector" in reason:
            return "missed_detector"
        if "absorb" in reason:
            return "absorbed"
        if reason in {"no_hit", "no_next_intersection"}:
            return "escaped"
        if reason:
            return "stopped"
    return "hit_detector" if bool(getattr(path, "reaches_image", False)) else ""


def ray_path_terminal_event(path: Any) -> Any | None:
    """Return the canonical terminal event for a traced ray path, if present."""
    for event in reversed(list(getattr(path, "events", []) or [])):
        if str(getattr(event, "event_kind", "") or "") == "terminal":
            return event
    return None


def ray_path_terminal_metadata(path: Any) -> dict[str, Any]:
    """Return terminal event metadata without exposing viewer state."""
    event = ray_path_terminal_event(path)
    if event is None:
        return {}
    metadata = getattr(event, "metadata", {}) or {}
    return dict(metadata) if isinstance(metadata, dict) else {}


def _finite_float_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return float(number) if np.isfinite(number) else None


def _format_mm(value: Any, *, digits: int = 4) -> str:
    number = _finite_float_or_none(value)
    if number is None:
        return ""
    return f"{number:.{digits}g} mm"


def ray_path_terminal_diagnostic_text(path: Any) -> str:
    """Return a compact diagnostic sentence for the path terminal event."""
    status = ray_path_terminal_status_from_events(path)
    event = ray_path_terminal_event(path)
    metadata = ray_path_terminal_metadata(path)
    if status == "missed_detector":
        surface = metadata.get("detector_miss_surface")
        if surface is None and event is not None:
            surface = getattr(event, "surface_id", None)
        surface_text = f" S{surface}" if surface not in (None, "") else ""
        parts = [f"missed detector{surface_text}"]
        radial = _format_mm(metadata.get("detector_miss_radial_mm"))
        half = _format_mm(metadata.get("detector_miss_half_mm"))
        if radial and half:
            parts.append(f"radial {radial} vs active half {half}")
        distance = _format_mm(metadata.get("detector_miss_distance_mm"))
        if distance:
            parts.append(f"plane distance {distance}")
        x_value = _format_mm(metadata.get("detector_miss_x_mm"))
        y_value = _format_mm(metadata.get("detector_miss_y_mm"))
        if x_value and y_value:
            parts.append(f"local ({x_value}, {y_value})")
        width = _format_mm(metadata.get("detector_miss_active_width_mm"))
        height = _format_mm(metadata.get("detector_miss_active_height_mm"))
        if width and height:
            parts.append(f"active {width} x {height}")
        reason = str(metadata.get("detector_miss_kernel_reason", "") or "").strip()
        if reason:
            parts.append(f"kernel {reason}")
        return " | ".join(parts)

    if status == "hit_detector":
        if event is not None and getattr(event, "surface_id", None) is not None:
            return f"hit detector S{getattr(event, 'surface_id')}"
        return "hit detector"
    reason = ""
    if event is not None:
        reason = str(getattr(event, "termination_reason", "") or getattr(event, "event_type", "") or "").strip()
    if status:
        suffix = f": {reason}" if reason else ""
        return f"{status.replace('_', ' ')}{suffix}"
    return reason


PROJECTED_TERMINAL_STATUS_LABELS = {
    "hit_detector": "Detector hit",
    "missed_detector": "Missed detector",
    "absorbed": "Absorbed",
    "escaped": "Escaped",
    "stopped": "Stopped",
}


def projected_ray_terminal_status(ray: Any) -> str:
    """Return the normalized terminal status for a projected display ray."""
    status = str(getattr(ray, "terminal_status", "") or "").strip().lower()
    if status in PROJECTED_TERMINAL_STATUS_LABELS:
        return status
    return "hit_detector" if bool(getattr(ray, "reaches_image", False)) else "stopped"


def projected_ray_hits_detector(ray: Any) -> bool:
    """Return whether a projected display ray terminates at a detector/image."""
    return projected_ray_terminal_status(ray) == "hit_detector"


def projected_ray_terminal_marker(ray: Any) -> tuple[float, float, str, str] | None:
    """Return the terminal marker point/status for one projected ray.

    Canonical projected terminal events are authoritative. If a ray carries
    event metadata but no terminal event, it is a displayed subsegment rather
    than a terminal path, so no endpoint glyph should be drawn.
    """
    pts = np.asarray(getattr(ray, "points_2d", []), dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 2:
        return None
    events = list(getattr(ray, "events_2d", []) or [])
    terminal_events = [
        event
        for event in events
        if str(getattr(event, "event_kind", "") or "") == "terminal"
    ]
    if terminal_events:
        event = terminal_events[-1]
        point = np.asarray(getattr(event, "point_2d", np.full(2, np.nan)), dtype=float).reshape(-1)
        if point.size < 2 or not np.all(np.isfinite(point[:2])):
            try:
                point_index = int(getattr(event, "point_index", pts.shape[0] - 1))
            except Exception:
                point_index = pts.shape[0] - 1
            point_index = min(max(point_index, 0), pts.shape[0] - 1)
            point = np.asarray(pts[point_index, :2], dtype=float)
        if point.size >= 2 and np.all(np.isfinite(point[:2])):
            terminal_status = str(getattr(event, "terminal_status", "") or "").strip().lower()
            if terminal_status not in PROJECTED_TERMINAL_STATUS_LABELS:
                terminal_status = projected_ray_terminal_status(ray)
            return (
                float(point[0]),
                float(point[1]),
                str(getattr(ray, "color", "#39FF14") or "#39FF14"),
                terminal_status,
            )
        return None
    if events:
        return None
    finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    if not np.any(finite):
        return None
    terminal = pts[finite][-1]
    return (
        float(terminal[0]),
        float(terminal[1]),
        str(getattr(ray, "color", "#39FF14") or "#39FF14"),
        projected_ray_terminal_status(ray),
    )


def _metadata_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "hit",
            "image",
            "detector",
            "hit_detector",
        }
    return bool(value)


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
    point_world: np.ndarray = field(default_factory=lambda: np.full(3, np.nan))
    offset_2d: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=float))
    coordinate_space: str = "yz_display"  # yz_display, folded_yz_display, world
    source_id: str = ""


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
    targets: list[SceneTarget3D] = field(default_factory=list)
    placements: list[ScenePlacement3D] = field(default_factory=list)
    scene_row_mapping: Any | None = None
    surface_curves: list[SurfaceCurve3D] = field(default_factory=list)
    surface_meshes: list[SurfaceMesh3D] = field(default_factory=list)
    optical_volumes: list[OpticalVolume3D] = field(default_factory=list)
    boundary_faces: list[BoundaryFace3D] = field(default_factory=list)
    ray_paths: list[RayPath3D] = field(default_factory=list)
    ray_events: list[RayEvent3D] = field(default_factory=list)
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
    coordinate_space: str = "world"


@dataclass(slots=True)
class ProjectedRayEvent2D:
    """A canonical ray event projected onto the active 2-D display plane."""

    event_id: str = ""
    event_kind: str = "surface"
    event_type: str = ""
    step: int = 0
    surface_id: int | None = None
    mesh_face_id: str = ""
    surface_name: str = ""
    interaction_model: str = ""
    point_index: int = 0
    point_2d: np.ndarray = field(default_factory=lambda: np.full(2, np.nan))
    terminal_status: str = ""


@dataclass(slots=True)
class ProjectedRay2D:
    ray_index: int = 0
    field_index: int = 0
    color: str = "#39FF14"
    points_2d: np.ndarray = field(default_factory=lambda: np.empty((0, 2)))
    draw_behind_surfaces: bool = False
    reaches_image: bool = False
    terminal_status: str = ""
    surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    branch_label: str = ""
    branch_path: str = ""
    source_id: str = ""
    source_name: str = ""
    terminal_surface_ids: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=int))
    events_2d: list[ProjectedRayEvent2D] = field(default_factory=list)


@dataclass
class ProjectedScene2D:
    curves: list[ProjectedCurve2D] = field(default_factory=list)
    rays: list[ProjectedRay2D] = field(default_factory=list)
    planes: list[PlaneMarker] = field(default_factory=list)
    labels: list[LabelSpec] = field(default_factory=list)
    pick_regions: list[PickRegion] = field(default_factory=list)
    bounds: BoundsRect = field(default_factory=BoundsRect)
