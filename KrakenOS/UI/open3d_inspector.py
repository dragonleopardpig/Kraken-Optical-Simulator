"""Embedded Open 3D inspector window for the Tk layout editor.

The inspector is intentionally kept as a Tk/VTK coordinator, but it no longer
lives inside ``layout_editor.py``.  The main editor owns optical state; this
module owns the embedded Open 3D window, actor lifecycle, interaction routing,
and panel wiring.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

import numpy as np

from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL, camera_names
from KrakenOS.UI.layout_plot_controller import ray_event_display_label
from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
from KrakenOS.UI.scene_builder import build_scene_placements
from KrakenOS.UI.scene_geometry import (
    SceneBundle,
    ScenePlacement3D,
    SurfaceMesh3D,
    ray_path_has_non_refractive_steering,
)
from KrakenOS.UI.scene_placement import SCENE_PLACEMENT_ADVANCED_ATTR
from KrakenOS.UI.scene_projector import normalize_projection_plane
from KrakenOS.UI.services.cad_scene_cache import CadSceneCache
from KrakenOS.UI.services.open3d_carry_grip import Open3DCarryGripService
from KrakenOS.UI.services.open3d_debug_tools import Open3DDebugToolsMixin
from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
from KrakenOS.UI.services.open3d_face_index_edges import (
    cached_display_feature_edges as _display_feature_edges_mesh,
    face_pick_from_display_mesh,
    face_indices_for_record,
    face_outline_from_face_indices,
    triangles_for_face_indices,
)
from KrakenOS.UI.services.open3d_face_pick import FaceRayPick, pick_face_from_ray
from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
from KrakenOS.UI.services.open3d_live_refresh import DEFAULT_LIVE_REFRESH_DELAY_MS, Open3DLiveRefreshService
from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
from KrakenOS.UI.services.open3d_round_lens_pick import step_feature_pick_for_display_xy
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.open3d_abstract_widget import WidgetRegistry
from KrakenOS.UI.services.open3d_application_logic import Open3DApplicationLogic
from KrakenOS.UI.services.open3d_event_recorder import Open3DEventRecorder
from KrakenOS.UI.services.open3d_placement_widget import (
    PlacementRotateWidget,
    PlacementTranslateWidget,
)
from KrakenOS.UI.services.open3d_step_rotation_widget import StepRotationHandleWidget
from KrakenOS.UI.services.open3d_thickness_widget import ThicknessDimensionWidget
from KrakenOS.UI.services.open3d_interaction_mode import (
    InteractionMode,
    InteractionModeState,
    derive_interaction_mode,
)
from KrakenOS.UI.services.open3d_selection_model import SelectionModel
from KrakenOS.UI.services.open3d_selection_representation import SelectionRepresentation
from KrakenOS.UI.services.open3d_selection_view import SelectionView
from KrakenOS.UI.services.open3d_step_overlay_refresh import Open3DStepOverlayRefreshService
from KrakenOS.UI.services.open3d_step_rotation_handles import Open3DStepRotationHandleService
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService, StepFeatureSelection
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
from KrakenOS.UI.services.open3d_timing import (
    open3d_timing_event,
    open3d_trace_enabled,
    open3d_trace_event,
    reset_open3d_timing_log,
    start_open3d_heartbeat,
)
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
from KrakenOS.UI.services.optical_solid_geometry import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED,
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_ROLE_DEFAULT,
    OPTICAL_SOLID_FACE_SIDE_DEFAULT,
    OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES,
    STL_AXIS_TO_LAYOUT_Z_TILTS,
    OpticalSolidFaceMarker,
    OpticalSolidVirtualPlaneMarker,
    _float_or_default,
    _legacy_role_from_optical_solid_face_function,
    _normalize_optical_solid_face_function,
    _normalize_optical_solid_face_port_role,
    _normalize_optical_solid_face_side,
    _normalize_optical_solid_virtual_plane_kind,
    _optical_solid_face_function_display,
    _optical_solid_face_marker_label,
    _optical_solid_face_port_role,
    _point3_tuple,
    _read_stl_triangle_vertices,
    _rotation_matrix_from_kraken_tilts,
    _unit_vector_tuple,
    normalize_optical_solid_face_metadata,
    normalize_optical_solid_face_record,
    normalize_optical_solid_virtual_plane_record,
    optical_solid_face_role_color,
    optical_solid_face_world_markers,
    optical_solid_virtual_plane_color,
    optical_solid_virtual_plane_world_markers,
    convex_hull_2d,
)
from KrakenOS.UI.services.ray_display_geometry import (
    _clean_polyline_points,
    _dotted_axis_records_from_ray_path,
    _finite_bounds_array,
    _optical_axis_z_span,
)
from KrakenOS.UI.services.element_scene_metadata import (
    SCENE_NORMAL_TARGET_CHOICES,
    SCENE_NORMAL_TARGET_LABELS,
    _normalize_scene_normal_target_kind,
)
from KrakenOS.UI.source_trace_helpers import (
    PUPIL_PATTERN_VALUES,
    SOURCE_DIRECTION_PRESET_VALUES,
    SOURCE_MODEL_VALUES,
)
from KrakenOS.UI.services.step_overlay_labels import (
    STEP_OVERLAY_LABELS,
    STEP_OVERLAY_LABEL_SET,
    is_step_overlay_decoration,
)
from KrakenOS.UI.surface_table_model import SurfaceRow, surface_row_to_spec
from KrakenOS.UI.services.offbeam_optical_solid import offbeam_neutralized_body_transform
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_runtime_transform_override
from KrakenOS.UI import optical_solid_metadata

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"
STEP_CARRY_GRID_FREE = "Free"
FIELD_TYPE_CANONICAL_VALUES = (
    "Angle",
    "Object Height",
    "Paraxial Image Height",
    "Real Image Height",
)

pv = None
vtkTkRenderWindowInteractor = None
vtkOrientationMarkerWidget = None
vtkAxesActor = None
vtkActor = None
vtkCellPicker = None
vtkPropPicker = None
vtkDataSetMapper = None
vtkRenderer = None
vtkTextActor = None
vtkBillboardTextActor3D = None
_VTK_TK_UNAVAILABLE_REASON = ""


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _layout_editor_class():
    return _layout_module().KrakenLayoutEditor


def _load_3d_backends() -> None:
    global pv, vtkTkRenderWindowInteractor, vtkOrientationMarkerWidget
    global vtkAxesActor, vtkActor, vtkCellPicker, vtkPropPicker, vtkDataSetMapper, vtkRenderer, vtkTextActor, vtkBillboardTextActor3D
    global _VTK_TK_UNAVAILABLE_REASON
    layout_editor_module = _layout_module()
    layout_editor_module._load_3d_backends()
    pv = layout_editor_module.pv
    vtkTkRenderWindowInteractor = layout_editor_module.vtkTkRenderWindowInteractor
    vtkOrientationMarkerWidget = layout_editor_module.vtkOrientationMarkerWidget
    vtkAxesActor = layout_editor_module.vtkAxesActor
    vtkActor = layout_editor_module.vtkActor
    vtkCellPicker = layout_editor_module.vtkCellPicker
    vtkPropPicker = layout_editor_module.vtkPropPicker
    vtkDataSetMapper = layout_editor_module.vtkDataSetMapper
    vtkRenderer = layout_editor_module.vtkRenderer
    vtkTextActor = layout_editor_module.vtkTextActor
    vtkBillboardTextActor3D = layout_editor_module.vtkBillboardTextActor3D
    _VTK_TK_UNAVAILABLE_REASON = layout_editor_module._VTK_TK_UNAVAILABLE_REASON


def _prepare_vtk_tk_widget(master: tk.Misc) -> None:
    _layout_module()._prepare_vtk_tk_widget(master)


def _dotted_axis_mesh_from_points(points, *, dash_count: int = 96) -> object | None:
    return _layout_module()._dotted_axis_mesh_from_points(points, dash_count=dash_count)


def _color_to_rgb_tuple(color: object) -> tuple[float, float, float]:
    if isinstance(color, str):
        text = color.strip()
        if text.startswith("#") and len(text) == 7:
            try:
                return (
                    int(text[1:3], 16) / 255.0,
                    int(text[3:5], 16) / 255.0,
                    int(text[5:7], 16) / 255.0,
                )
            except ValueError:
                pass
    try:
        values = tuple(float(value) for value in color)  # type: ignore[arg-type]
        if len(values) >= 3:
            return values[:3]
    except Exception:
        pass
    return (0.0, 0.55, 1.0)


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "..."
    return text


class Kraken3DInspector(Open3DDebugToolsMixin, tk.Toplevel):
    # Pick state lives on a SelectionModel that survives RemoveAllViewProps().
    # These five properties are compatibility shims so existing call sites
    # (`self._picked_row_index = X`, `self._picked_step_label`, ...) keep
    # working unchanged.
    @property
    def _picked_row_index(self) -> int | None:
        return self._selection_model.picked_row_index

    @_picked_row_index.setter
    def _picked_row_index(self, value: int | None) -> None:
        self._selection_model.picked_row_index = None if value is None else int(value)

    @property
    def _picked_row_indices(self) -> set[int]:
        return self._selection_model.picked_row_indices

    @_picked_row_indices.setter
    def _picked_row_indices(self, value) -> None:
        self._selection_model.picked_row_indices = set(int(v) for v in (value or []))

    @property
    def _picked_step_label(self) -> str | None:
        return self._selection_model.picked_step_label

    @_picked_step_label.setter
    def _picked_step_label(self, value: str | None) -> None:
        self._selection_model.picked_step_label = None if value is None else str(value)

    @property
    def _picked_ray_index(self) -> int | None:
        return self._selection_model.picked_ray_index

    @_picked_ray_index.setter
    def _picked_ray_index(self, value: int | None) -> None:
        self._selection_model.picked_ray_index = None if value is None else int(value)

    @property
    def _picked_optical_axis_id(self) -> str | None:
        return self._selection_model.picked_optical_axis_id

    @_picked_optical_axis_id.setter
    def _picked_optical_axis_id(self, value: str | None) -> None:
        self._selection_model.picked_optical_axis_id = None if value is None else str(value)

    # ------------------------------------------------------------------
    # Phase 10: pick-mode booleans become InteractionMode-backed properties.
    # Each setter promotes its mode to active (True) or steps down to IDLE
    # (False) so the 10+ mutually exclusive booleans stay consistent and
    # observers of _interaction_mode_state get notified on every change.

    def _set_pick_mode_flag(self, mode: InteractionMode, value: bool) -> None:
        if bool(value):
            self._interaction_mode_state.set_mode(mode)
        elif self._interaction_mode_state.mode == mode:
            self._interaction_mode_state.set_mode(InteractionMode.IDLE)

    @property
    def _source_target_pick_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.SOURCE_TARGET

    @_source_target_pick_mode.setter
    def _source_target_pick_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.SOURCE_TARGET, value)

    @property
    def _center_row_to_ray_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.CENTER_ROW_TO_RAY

    @_center_row_to_ray_mode.setter
    def _center_row_to_ray_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.CENTER_ROW_TO_RAY, value)

    @property
    def _placement_target_pick_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.PLACEMENT_TARGET

    @_placement_target_pick_mode.setter
    def _placement_target_pick_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.PLACEMENT_TARGET, value)

    @property
    def _placement_orient_pick_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.PLACEMENT_ORIENT

    @_placement_orient_pick_mode.setter
    def _placement_orient_pick_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.PLACEMENT_ORIENT, value)

    @property
    def _placement_orient_ray_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.PLACEMENT_ORIENT_RAY

    @_placement_orient_ray_mode.setter
    def _placement_orient_ray_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.PLACEMENT_ORIENT_RAY, value)

    @property
    def _step_carry_snap_ray_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.STEP_CARRY_SNAP_RAY

    @_step_carry_snap_ray_mode.setter
    def _step_carry_snap_ray_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.STEP_CARRY_SNAP_RAY, value)

    @property
    def _step_carry_snap_target_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.STEP_CARRY_SNAP_TARGET

    @_step_carry_snap_target_mode.setter
    def _step_carry_snap_target_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.STEP_CARRY_SNAP_TARGET, value)

    @property
    def _step_normal_axis_pick_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.STEP_NORMAL_AXIS_PICK

    @_step_normal_axis_pick_mode.setter
    def _step_normal_axis_pick_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.STEP_NORMAL_AXIS_PICK, value)

    @property
    def _step_surface_center_axis_pick_mode(self) -> bool:
        return self._interaction_mode_state.mode == InteractionMode.STEP_SURFACE_CENTER_AXIS_PICK

    @_step_surface_center_axis_pick_mode.setter
    def _step_surface_center_axis_pick_mode(self, value: bool) -> None:
        self._set_pick_mode_flag(InteractionMode.STEP_SURFACE_CENTER_AXIS_PICK, value)

    def __init__(self, editor: "KrakenLayoutEditor") -> None:
        _load_3d_backends()
        super().__init__(editor)
        self.editor = editor
        self.available = False
        self.unavailable_reason = ""
        self.title("KrakenOS 3D Inspector")
        self.geometry("1100x780")
        self.minsize(720, 520)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._renderer = None
        self._vtk_widget = None
        self._vtk_interactor = None
        self._orientation_widget = None
        self._picker = None
        self._prop_picker = None
        self._selection_model = SelectionModel()
        self._selection_representation = SelectionRepresentation(self)
        self._selection_view = SelectionView(self, self._selection_model)
        self._selection_view.attach()
        self._interaction_mode_state = InteractionModeState()
        self._widget_registry = WidgetRegistry()
        self._widget_registry.add(StepRotationHandleWidget(self))
        self._widget_registry.add(PlacementRotateWidget(self))
        self._widget_registry.add(PlacementTranslateWidget(self))
        self._widget_registry.add(ThicknessDimensionWidget(self))
        self._application_logic = Open3DApplicationLogic(self)
        self._event_recorder = Open3DEventRecorder(self)
        self.recorder_button_var = tk.StringVar(value="● Record bug")
        self._actor_row_map: dict[str, int] = {}
        self._row_actor_map: dict[int, list[str]] = {}
        self._actor_ray_map: dict[str, int] = {}
        self._ray_actor_map: dict[int, list[str]] = {}
        self._actor_optical_axis_map: dict[str, dict[str, object]] = {}
        self._optical_axis_actor_map: dict[str, list[str]] = {}
        self._optical_axis_pick_records: list[dict[str, object]] = []
        # Cache of the last live-trace's per-segment axis records so
        # rays-off refreshes can still show the cascade's folded
        # geometry. Cleared whenever rows change (refresh_from_editor
        # invalidates it indirectly through the cache key check inside
        # _optical_axis_records_for_3d).
        self._cached_traced_axis_records: list[dict[str, object]] = []
        self._cached_traced_axis_signature: tuple = ()
        self._optical_axis_highlight_actor = None
        self._actor_by_key: dict[str, object] = {}
        self._actor_step_map: dict[str, str] = {}
        self._step_actor_map: dict[str, list[str]] = {}
        # Scene-component browser hide/unhide: rows + STEP labels whose body
        # actors are kept invisible (re-applied after every refresh).
        self._hidden_scene_rows: set[int] = set()
        self._hidden_step_labels: set[str] = set()
        self._actor_step_follow_map: dict[str, str] = {}
        self._step_follow_actor_map: dict[str, list[str]] = {}
        self._actor_step_rotate_map: dict[str, tuple[str, str, float]] = {}
        self._actor_step_rotate_visual_keys: set[str] = set()
        self._actor_step_translate_map: dict[str, tuple[str, str, float]] = {}
        self._actor_placement_move_map: dict[str, tuple[int, str, float]] = {}
        self._actor_placement_rotate_map: dict[str, tuple[int, str, float]] = {}
        self._actor_placement_rotate_visual_keys: set[str] = set()
        self._actor_placement_move_visual_keys: set[str] = set()
        self._placement_handle_selected_row_index: int | None = None
        self._actor_thickness_dimension_map: dict[str, int] = {}
        self._thickness_dimension_actor_map: dict[int, list[str]] = {}
        self._thickness_dimension_drag_map: dict[str, dict[str, object]] = {}
        self._step_feature_cache: dict[tuple[str, int], tuple[np.ndarray, object | None, np.ndarray | None] | None] = {}
        self._cad_scene_cache = CadSceneCache()
        self._current_scene_bundle: SceneBundle | None = None
        self._current_system = None
        self._current_rays = None
        self._current_row_names: list[str] = []
        self._last_refresh_sampling_mode: str | None = None
        self._ray_event_label_actors: list[object] = []
        self._galvo_scan_after_id: str | None = None
        self._galvo_scan_actors: list[object] = []
        self._galvo_scan_frames: list[dict[str, object]] = []
        self._galvo_scan_frame_index = 0
        self._hover_rotation_handle_key: str | None = None
        self._hover_step_actor = None
        self._hover_step_outline_actor = None
        self._hover_step_cell_key = None
        self._mode_badge_actor = None
        self._trace_summary_actor = None
        self._placement_grid_status_actor = None
        self._hover_status_actor = None
        self._step_rotation_active_label: str | None = None
        # Multi-select set of STEP labels whose rotation gizmos are live.
        # `_step_rotation_active_label` is the primary (last-clicked) member;
        # Shift+click adds/toggles extra members. A plain click collapses this
        # back to a single label so prior gizmos are torn down (bugs/0049).
        self._selected_step_labels: set[str] = set()
        # Compatibility name: this is now an embedded side-panel widget, not a
        # separate popup, so it cannot disappear behind a fullscreen main UI.
        self._stl_placement_popup: tk.Widget | None = None
        self._stl_placement_status_var: tk.StringVar | None = None
        self._camera_preset = self._camera_preset_for_display_orientation()
        self._stl_placement_row_index: int | None = None
        self._stl_placement_dirty = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index: int | None = None
        self._center_row_to_ray_face_id: str = ""
        self._source_target_pick_mode = False
        self._placement_target_pick_mode = False
        self._placement_target_row_index: int | None = None
        self._placement_target_face_id: str = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index: int | None = None
        self._placement_orient_face_id: str = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index: int | None = None
        self._placement_orient_ray_face_id: str = ""
        self._ctrl_left_camera_active = False
        self._left_drag_active = False
        self._left_drag_start_xy: tuple[int, int] | None = None
        self._left_drag_last_xy: tuple[int, int] | None = None
        self._left_drag_moved = False
        self._middle_drag_active = False
        self._middle_drag_last_xy: tuple[int, int] | None = None
        self._mouse_move_last_ts = 0.0
        self._mouse_move_min_interval_s = 0.035
        self._placement_drag_state: dict[str, object] | None = None
        self._thickness_drag_state: dict[str, object] | None = None
        self._step_carry_active_label: str | None = None
        self._step_carry_drag_state: dict[str, object] | None = None
        self._step_carry_follow_state: dict[str, object] | None = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_normal_axis_anchor_mode = "body_center"
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_grid_label: str | None = None
        self._step_carry_grid_spacing_mm: float | None = None
        self._step_carry_hold_after_id: str | None = None
        self._step_carry_hold_candidate_label: str | None = None
        self._step_carry_hold_press_xy: tuple[int, int] | None = None
        self._step_carry_hold_pick_world: tuple[float, float, float] | None = None
        self._row_carry_hold_after_id: str | None = None
        self._row_carry_hold_candidate_index: int | None = None
        self._row_carry_hold_press_xy: tuple[int, int] | None = None
        self._row_carry_hold_pick_world: tuple[float, float, float] | None = None
        self._row_carry_drag_state: dict[str, object] | None = None
        self._axis_slide_drag_state: dict[str, object] | None = None
        self._step_translate_drag_state: dict[str, object] | None = None
        self._step_translate_gap_actors: list[Any] = []
        # bugs/0053: re-anchor a thickness/distance dimension endpoint. Ctrl-click
        # a dimension arrow to enter a modal pick (the nearer endpoint then follows
        # the bare mouse, no button held); a plain click on a surface/edge commits.
        # `_dimension_anchor_drag_state` is only the transient entry-gesture flag
        # that suppresses camera orbit while the Ctrl button is still down.
        self._dimension_anchor_drag_state: dict[str, object] | None = None
        self._dimension_anchor_pick_mode = False
        self._dimension_anchor_pick_state: dict[str, object] | None = None
        self._dimension_anchor_preview_actors: list[Any] = []
        self._dimension_anchor_snap_highlight_row: int | None = None
        self._open3d_carry_grip_service = Open3DCarryGripService(self)
        self._selected_step_feature: StepFeatureSelection | None = None
        self._selected_step_feature_label: str | None = None
        self._selected_step_feature_center_world: tuple[float, float, float] | None = None
        self._selected_step_feature_surface_center_world: tuple[float, float, float] | None = None
        self._selected_step_feature_normal_world: tuple[float, float, float] | None = None
        self._last_valid_surface_mesh_items: list[SurfaceMesh3D] = []
        self._last_valid_surface_mesh_row_count = 0
        self._open3d_debug_seq = 0
        self._open3d_timing_slow_ms = 100.0
        self._open3d_timing_log_path = reset_open3d_timing_log(reason="inspector_init")
        # Deep-trace mode (KRAKEN_OPEN3D_TRACE=1). The heartbeat thread
        # writes an "alive" event every 250 ms so a main-thread stall
        # in VTK / pythonocc / Tk becomes a visible gap in the log
        # rather than looking identical to "no user activity". The
        # heartbeat is harmless in normal use (one extra JSON line per
        # quarter-second) but we only run it when the env var is set so
        # the typical session leaves no trace noise.
        self._open3d_heartbeat_stop = None
        if open3d_trace_enabled():
            try:
                self._open3d_heartbeat_stop = start_open3d_heartbeat()
            except Exception as exc:
                open3d_timing_event(
                    "heartbeat_start_failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
            open3d_trace_event(
                "inspector_init_trace_mode",
                pid=int(os.getpid()),
            )
        self._show_rays_before_axis_pick = False
        self.stl_axis_var = tk.StringVar(value="+Z")
        self.orient_axis_var = tk.StringVar(value="+Z")
        self.normal_target_var = tk.StringVar(value=SCENE_NORMAL_TARGET_LABELS["detector"])
        self.step_carry_grid_var = tk.StringVar(value=STEP_CARRY_GRID_FREE)
        self.rotation_step_deg_var = tk.StringVar(value="90")
        self.show_rays_var = tk.BooleanVar(value=True)
        self.ray_pick_enabled_var = tk.BooleanVar(value=False)
        self.show_rotation_handles_var = tk.BooleanVar(value=True)
        self.show_reference_surfaces_var = tk.BooleanVar(value=False)
        self.show_detector_overlays_var = tk.BooleanVar(value=False)
        self.show_terminal_diagnostics_var = tk.BooleanVar(value=False)
        self.show_placement_handles_var = tk.BooleanVar(value=False)
        self.slide_along_axis_mode_var = tk.BooleanVar(value=False)
        self.show_live_controls_panel_var = tk.BooleanVar(value=True)
        self.show_scene_components_panel_var = tk.BooleanVar(value=True)
        self.live_mode_var = tk.BooleanVar(value=False)
        self.quick_estimation_var = tk.BooleanVar(value=False)
        self._quick_estimation_service_instance = None
        self._quick_estimation_readout_vars: dict[str, tk.StringVar] = {}
        self.status_var = tk.StringVar(value="3D inspector ready")

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(1, weight=1)

        if vtkTkRenderWindowInteractor is None or vtkRenderer is None:
            self.unavailable_reason = _VTK_TK_UNAVAILABLE_REASON or "Embedded VTK/Tk viewer unavailable."
            self.status_var.set(self.unavailable_reason)
            return

        host = None
        try:
            self._build_open3d_top_controls(self)

            main_pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
            main_pane.grid(row=1, column=1, sticky="nsew", padx=0, pady=8)
            self._open3d_main_pane = main_pane

            # 2D-style collapse: thin restore-arrow frames at the left/right edges
            # (shown only while the corresponding panel is collapsed).
            left_restore = ttk.Frame(self, padding=(2, 8, 2, 8))
            ttk.Button(left_restore, text="▶", width=2, command=self.toggle_live_controls_panel).grid(row=0, column=0, sticky="n")
            left_restore.grid(row=1, column=0, sticky="ns", padx=(8, 0))
            left_restore.grid_remove()
            self._open3d_left_restore_frame = left_restore

            right_restore = ttk.Frame(self, padding=(2, 8, 2, 8))
            ttk.Button(right_restore, text="◀", width=2, command=self.toggle_scene_components_panel).grid(row=0, column=0, sticky="n")
            right_restore.grid(row=1, column=2, sticky="ns", padx=(0, 8))
            right_restore.grid_remove()
            self._open3d_right_restore_frame = right_restore

            live_panel = ttk.LabelFrame(self, text="Live Controls", padding=8)
            live_panel.columnconfigure(0, weight=1)
            live_panel.rowconfigure(1, weight=1)
            live_panel.configure(width=320)
            self._open3d_live_panel_host = live_panel
            self._build_live_left_panel(live_panel)

            host = ttk.Frame(self, padding=0)
            host.columnconfigure(0, weight=1)
            host.rowconfigure(0, weight=1)
            self._open3d_viewport_host = host

            step_admin_panel = ttk.LabelFrame(self, text="Scene Components", padding=8)
            step_admin_panel.columnconfigure(0, weight=1)
            step_admin_panel.rowconfigure(0, weight=1)
            step_admin_panel.configure(width=300)
            self._open3d_step_admin_panel_host = step_admin_panel
            self._build_step_admin_right_panel(step_admin_panel)

            main_pane.add(live_panel, weight=0)
            main_pane.add(host, weight=1)
            main_pane.add(step_admin_panel, weight=0)

            _prepare_vtk_tk_widget(host)
            self._vtk_widget = vtkTkRenderWindowInteractor(host, width=1100, height=720)
            self._vtk_widget.grid(row=0, column=0, sticky="nsew")
            render_window = self._vtk_widget.GetRenderWindow()
            self._renderer = vtkRenderer()
            render_window.AddRenderer(self._renderer)
            self._renderer.SetBackground(1.0, 1.0, 1.0)

            self._vtk_interactor = render_window.GetInteractor()
            if self._vtk_interactor is not None:
                self._vtk_interactor.AddObserver("LeftButtonPressEvent", self._on_left_button_press)
                self._vtk_interactor.AddObserver("MouseMoveEvent", self._on_mouse_move)
                self._vtk_interactor.AddObserver("KeyPressEvent", self._on_key_press)
                # bugs/0048: orbit/zoom can swing the far scene geometry behind a
                # too-close camera; keep the camera clear of the scene so the
                # converging cone is never near-clipped during interaction.
                self._vtk_interactor.AddObserver("InteractionEvent", self._on_camera_interaction)
                self._vtk_interactor.AddObserver("EndInteractionEvent", self._on_camera_interaction)
            # Deep-trace VTK render-window resize: maximising the Open
            # 3D window is a known trigger for hover-freeze reports, so
            # we log every Configure / Resize so the post-mortem can
            # tell whether the freeze starts on the resize event itself
            # or only on the next mouse-move after it.
            if open3d_trace_enabled():
                self._bind_trace_window_observers(render_window)
                self._bind_trace_tk_configure()

            if vtkCellPicker is not None:
                self._picker = vtkCellPicker()
                self._picker.SetTolerance(0.0015)
            if vtkPropPicker is not None:
                self._prop_picker = vtkPropPicker()

            if vtkOrientationMarkerWidget is not None and vtkAxesActor is not None and self._vtk_interactor is not None:
                axes = vtkAxesActor()
                self._orientation_widget = vtkOrientationMarkerWidget()
                self._orientation_widget.SetOrientationMarker(axes)
                self._orientation_widget.SetInteractor(self._vtk_interactor)
                self._orientation_widget.SetViewport(0.0, 0.0, 0.18, 0.18)
                self._orientation_widget.SetEnabled(1)
                self._orientation_widget.InteractiveOff()

            self._vtk_widget.Initialize()
            self._install_pick_only_left_click_bindings()
            self.bind("<Escape>", self._cancel_active_3d_operation_event)
            self._vtk_widget.bind("<Escape>", self._cancel_active_3d_operation_event, add="+")
            self.bind("<Delete>", self._delete_selected_step_event)
            self.bind("<BackSpace>", self._delete_selected_step_event)
            self._vtk_widget.bind("<Delete>", self._delete_selected_step_event, add="+")
            self._vtk_widget.bind("<BackSpace>", self._delete_selected_step_event, add="+")
            # Flag-bug hotkey: bind at both Toplevel and 3D-pane level so
            # `s` works whether focus is on the renderer or just inside
            # the inspector window. The VTK observer in `_on_key_press`
            # also handles `s`, but Tk's focus model means a non-focused
            # render pane (e.g. after the user clicked the Record
            # button) silently swallows the key without firing the VTK
            # observer.
            self.bind("<KeyPress-s>", self._flag_bug_event)
            self.bind("<KeyPress-S>", self._flag_bug_event)
            self._vtk_widget.bind("<KeyPress-s>", self._flag_bug_event, add="+")
            self._vtk_widget.bind("<KeyPress-S>", self._flag_bug_event, add="+")
            ttk.Label(self, textvariable=self.status_var, padding=(8, 0, 8, 8)).grid(row=2, column=0, columnspan=3, sticky="ew")
            self.available = True
        except Exception as exc:
            self.unavailable_reason = _short_error_message(exc)
            self.status_var.set(f"Embedded 3D unavailable: {self.unavailable_reason}")
            try:
                if host is not None:
                    host.destroy()
            except Exception:
                pass

    @staticmethod
    def _open3d_pane_present(paned: ttk.Panedwindow | None, child: tk.Widget | None) -> bool:
        if paned is None or child is None:
            return False
        child_name = str(child)
        return any(str(pane) == child_name for pane in paned.panes())

    def _set_open3d_side_panel_visible(self, panel: str, visible: bool) -> None:
        paned = getattr(self, "_open3d_main_pane", None)
        if paned is None:
            return
        if panel == "live":
            widget = getattr(self, "_open3d_live_panel_host", None)
            variable = self.show_live_controls_panel_var
            insert_index = 0
            label = "Live Controls"
        elif panel == "components":
            widget = getattr(self, "_open3d_step_admin_panel_host", None)
            variable = self.show_scene_components_panel_var
            insert_index = None
            label = "Scene Components"
        else:
            return
        if widget is None:
            variable.set(False)
            return
        present = self._open3d_pane_present(paned, widget)
        if visible and not present:
            if insert_index is None:
                paned.add(widget, weight=0)
            else:
                paned.insert(insert_index, widget, weight=0)
            variable.set(True)
            self.status_var.set(f"{label} panel shown.")
        elif not visible and present:
            paned.forget(widget)
            variable.set(False)
            self.status_var.set(f"{label} panel hidden.")
        else:
            variable.set(present)
        # Show the edge restore arrow only while the panel is collapsed.
        restore = getattr(
            self, "_open3d_left_restore_frame" if panel == "live" else "_open3d_right_restore_frame", None
        )
        if restore is not None:
            if self._open3d_pane_present(paned, widget):
                restore.grid_remove()
            else:
                restore.grid()
        try:
            self.update_idletasks()
        except Exception:
            pass
        self.render()

    def _on_open3d_panel_visibility_changed(self) -> None:
        self._set_open3d_side_panel_visible("live", bool(self.show_live_controls_panel_var.get()))
        self._set_open3d_side_panel_visible("components", bool(self.show_scene_components_panel_var.get()))

    def toggle_live_controls_panel(self) -> None:
        visible = not self._open3d_pane_present(
            getattr(self, "_open3d_main_pane", None),
            getattr(self, "_open3d_live_panel_host", None),
        )
        self._set_open3d_side_panel_visible("live", visible)

    def toggle_scene_components_panel(self) -> None:
        visible = not self._open3d_pane_present(
            getattr(self, "_open3d_main_pane", None),
            getattr(self, "_open3d_step_admin_panel_host", None),
        )
        self._set_open3d_side_panel_visible("components", visible)

    def _open3d_top_controls_panel(self) -> Open3DTopControlsPanel:
        panel = getattr(self, "_open3d_top_controls_panel_instance", None)
        if panel is None:
            panel = Open3DTopControlsPanel(self, normal_target_choices=SCENE_NORMAL_TARGET_CHOICES)
            self._open3d_top_controls_panel_instance = panel
        return panel

    def _open3d_thickness_dimension_service(self) -> Open3DThicknessDimensionService:
        service = getattr(self, "_open3d_thickness_dimension_service_instance", None)
        if service is None:
            service = Open3DThicknessDimensionService(
                self,
                pv_module=pv,
                billboard_text_actor_cls=vtkBillboardTextActor3D,
            )
            self._open3d_thickness_dimension_service_instance = service
        return service

    def _quick_estimation_service(self):
        service = getattr(self, "_quick_estimation_service_instance", None)
        if service is None:
            from KrakenOS.UI.services.quick_estimation import QuickEstimationService

            service = QuickEstimationService(self)
            self._quick_estimation_service_instance = service
        return service

    def _open3d_solve_service(self):
        service = getattr(self, "_open3d_solve_service_instance", None)
        if service is None:
            from KrakenOS.UI.services.open3d_solve import Open3DSolveService

            service = Open3DSolveService(self)
            self._open3d_solve_service_instance = service
        return service

    def _toggle_quick_estimation(self) -> None:
        service = self._quick_estimation_service()
        if self.quick_estimation_var.get():
            service.update_readout()
            self.status_var.set(service._role_summary())
        else:
            self.status_var.set("Quick Estimation off -- thickness edits no longer re-solve the conjugate.")

    def _open3d_step_rotation_handle_service(self) -> Open3DStepRotationHandleService:
        if pv is None:
            _load_3d_backends()
        if not hasattr(self, "_actor_by_key"):
            self._actor_by_key = {}
        if not hasattr(self, "_actor_step_follow_map"):
            self._actor_step_follow_map = {}
        if not hasattr(self, "_step_follow_actor_map"):
            self._step_follow_actor_map = {}
        if not hasattr(self, "_actor_step_rotate_map"):
            self._actor_step_rotate_map = {}
        if not hasattr(self, "_actor_step_rotate_visual_keys"):
            self._actor_step_rotate_visual_keys = set()
        if not hasattr(self, "_hover_rotation_handle_key"):
            self._hover_rotation_handle_key = None
        service = getattr(self, "_open3d_step_rotation_handle_service_instance", None)
        if service is None or getattr(service, "pv", None) is not pv:
            service = Open3DStepRotationHandleService(
                self,
                pv_module=pv,
                valid_labels=STEP_OVERLAY_LABEL_SET,
            )
            self._open3d_step_rotation_handle_service_instance = service
        return service

    def _open3d_step_overlay_refresh_service(self) -> Open3DStepOverlayRefreshService:
        service = getattr(self, "_open3d_step_overlay_refresh_service_instance", None)
        if service is None:
            service = Open3DStepOverlayRefreshService(self)
            self._open3d_step_overlay_refresh_service_instance = service
        return service

    def _open3d_live_refresh_service(self) -> Open3DLiveRefreshService:
        service = getattr(self, "_open3d_live_refresh_service_instance", None)
        if service is None:
            service = Open3DLiveRefreshService(self)
            self._open3d_live_refresh_service_instance = service
        return service

    def _build_open3d_top_controls(self, parent: tk.Widget) -> ttk.Frame:
        return self._open3d_top_controls_panel().build(parent)

    def _open3d_live_controls_panel(self) -> Open3DLiveControlsPanel:
        panel = getattr(self, "_open3d_live_controls_panel_instance", None)
        if panel is None:
            panel = Open3DLiveControlsPanel(
                self,
                source_model_values=SOURCE_MODEL_VALUES,
                pupil_pattern_values=PUPIL_PATTERN_VALUES,
                field_type_values=FIELD_TYPE_CANONICAL_VALUES,
                source_direction_preset_values=SOURCE_DIRECTION_PRESET_VALUES,
                camera_none_label=CAMERA_NONE_LABEL,
                camera_names=camera_names,
            )
            self._open3d_live_controls_panel_instance = panel
        return panel

    def _build_live_left_panel(self, parent: tk.Widget) -> None:
        self._open3d_live_controls_panel().build(parent)

    def _open3d_step_admin_panel(self) -> Open3DStepAdminPanel:
        panel = getattr(self, "_open3d_step_admin_panel_instance", None)
        if panel is None:
            panel = Open3DStepAdminPanel(self)
            self._open3d_step_admin_panel_instance = panel
        return panel

    def _build_step_admin_right_panel(self, parent: tk.Widget) -> ttk.Frame:
        return self._open3d_step_admin_panel().build(parent)

    def refresh_step_admin_panel(self) -> None:
        panel = getattr(self, "_open3d_step_admin_panel_instance", None)
        if panel is None:
            return
        try:
            panel.refresh()
        except Exception as exc:
            self.editor.append_debug(f"Open 3D STEP admin refresh failed: {exc}")

    def sync_step_admin_canvas_selection(self, iid: str) -> None:
        """bugs/0063: mirror a direct 3D-canvas pick into the STEP admin browser
        so the "Selected Element" action buttons enable just as a browser-tree
        click does. The canvas pick already applied the editor/inspector
        selection + gizmo; this only syncs the panel's selection + button state."""
        panel = getattr(self, "_open3d_step_admin_panel_instance", None)
        if panel is None:
            return
        try:
            panel.select_from_canvas(iid)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D STEP admin canvas-sync failed: {exc}")

    def _open3d_browser_iid_for_table_row(self, row_index: int) -> str:
        """bugs/0063: the browser iid for a canvas-picked editable-table row --
        promoted STEP optical solids list as ``row:N``; every other drawn row
        (including element-group children) lists as ``scene-row:N`` (see
        Open3DStepAdminPanel.refresh)."""
        rows = list(getattr(self.editor, "rows", []) or [])
        if not (0 <= row_index < len(rows)):
            return ""
        try:
            if self.editor._is_open3d_promoted_optical_solid_row(rows[row_index]):
                return f"row:{row_index}"
        except Exception:
            pass
        return f"scene-row:{row_index}"

    def _editor_var(self, name: str, default: str = ""):
        return self._open3d_live_controls_panel().editor_var(name, default)

    def _live_labeled_entry(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        label: str,
        var_name: str,
        *,
        sync_fields: bool = False,
        width: int = 10,
    ) -> ttk.Entry:
        return self._open3d_live_controls_panel().live_labeled_entry(
            parent,
            row,
            column,
            label,
            var_name,
            sync_fields=sync_fields,
            width=width,
        )

    def _live_labeled_combo(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        label: str,
        var_name: str,
        values,
        *,
        handler=None,
        width: int = 12,
    ) -> ttk.Combobox:
        return self._open3d_live_controls_panel().live_labeled_combo(
            parent,
            row,
            column,
            label,
            var_name,
            values,
            handler=handler,
            width=width,
        )

    def _build_live_source_controls(self, parent: tk.Widget) -> None:
        self._open3d_live_controls_panel().build_source_controls(parent)

    def _build_live_field_controls(self, parent: tk.Widget) -> None:
        self._open3d_live_controls_panel().build_field_controls(parent)

    def _build_live_trace_controls(self, parent: tk.Widget) -> None:
        self._open3d_live_controls_panel().build_trace_controls(parent)

    def _build_live_step_controls(self, parent: tk.Widget) -> None:
        self._open3d_live_controls_panel().build_step_controls(parent)

    def _commit_live_control_update(self, *, sync_fields: bool = False, handler=None) -> None:
        try:
            if handler is not None:
                handler()
            elif sync_fields:
                self.editor._sync_object_controls()
                self.editor._mark_plot_update_pending()
            else:
                self.editor._sync_left_mode_controls()
                self.editor._mark_plot_update_pending()
        except Exception as exc:
            self.editor.append_debug(f"Open 3D live control commit failed: {exc}")
            self.status_var.set(f"Live control failed: {_short_error_message(exc)}")
            return
        self.schedule_live_refresh("3D controls")

    def _on_live_mode_toggled(self) -> None:
        if self._live_mode_enabled():
            self.status_var.set("Live Mode enabled: source edits and row-backed placement retrace the 3D scene.")
            self.schedule_live_refresh("enabled", delay_ms=0)
        else:
            self._cancel_live_refresh()
            self.status_var.set("Live Mode disabled.")

    def _trace_live_now(self) -> None:
        if self._live_mode_enabled():
            self.schedule_live_refresh("manual", delay_ms=0)
            return
        try:
            try:
                self.editor._sync_object_controls()
                self.editor._sync_left_mode_controls()
            except Exception:
                pass
            self._refresh_trace_now_scene("manual")
        except Exception as exc:
            self.status_var.set(f"3D trace failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D trace-now failed: {exc}")

    def _live_mode_enabled(self) -> bool:
        try:
            return bool(self.live_mode_var.get())
        except Exception:
            return False

    def _cancel_live_refresh(self) -> None:
        self._open3d_live_refresh_service().cancel()

    def schedule_live_refresh(self, reason: str = "", *, delay_ms: int = DEFAULT_LIVE_REFRESH_DELAY_MS) -> bool:
        return self._open3d_live_refresh_service().schedule(reason, delay_ms=delay_ms)

    def _run_live_refresh(self) -> None:
        self._open3d_live_refresh_service().run()

    def _flush_pending_placement_drag_for_live(self) -> None:
        """bugs/0024: commit an in-progress placement-translate drag's accumulated
        offset into the model so the Live Mode trace that follows reflects the
        dragged pose.

        Model-only (``translate_scene_row_pose``); the live preview that calls
        this is the retrace, so we do not retrace here. The pending offset is
        reset so the next drag steps accumulate from the just-committed pose, and
        ``_finish_placement_drag`` on release commits only the remaining tail.
        Rotation drags already retrace per step, so they are left alone.
        Best-effort: any failure leaves the deferred-on-release behaviour intact.
        """
        state = self._placement_drag_state
        if state is None or str(state.get("kind")) == "rotate":
            return
        try:
            pending = float(state.get("pending_translate_mm", 0.0))
        except Exception:
            return
        if abs(pending) <= 1.0e-9:
            return
        try:
            self.editor.translate_scene_row_pose(
                int(state.get("row_index", -1)), str(state.get("axis", "")), pending
            )
            state["pending_translate_mm"] = 0.0
        except Exception:
            pass

    def _refresh_live_preview_scene(self, reason: str) -> None:
        self._flush_pending_placement_drag_for_live()
        result = self.editor._open3d_trace_refresh_service().build_live_preview(self)
        # bugs/0024: mid-placement-drag, the bodies/handles don't change (the
        # dragged one tracks the cursor via its cheap actor transform), so update
        # only the ray actors -- skipping the ~2 s full rebuild keeps the drag
        # preview interactive. The full scene rebuilds on release.
        if self._placement_drag_state is not None:
            self._refresh_rays_only(result.rays, result.scene_bundle)
        else:
            self.refresh_scene(
                result.system,
                result.rays,
                result.row_names,
                scene_bundle=result.scene_bundle,
                reset_camera=False,
            )
        live_records = list(getattr(self.editor, "_last_live_step_overlay_trace_records", []) or [])
        suffix = " with transient optical STEP" if live_records else ""
        self.editor.status_var.set(f"Live Mode trace updated{suffix} ({reason}).")
        self._debug_trace(
            "live_mode_refresh",
            reason=reason,
            transient_step_overlays=len(live_records),
        )

    def _refresh_trace_now_scene(self, reason: str) -> None:
        if not bool(self.show_rays_var.get()):
            self.show_rays_var.set(True)
        self.editor._open3d_trace_refresh_service().mark_step_overlay_physics_preview_ready("optical")
        result = self.editor._open3d_trace_refresh_service().build_trace_now_preview(self)
        self.refresh_scene(
            result.system,
            result.rays,
            result.row_names,
            scene_bundle=result.scene_bundle,
            reset_camera=False,
        )
        live_records = list(getattr(self.editor, "_last_live_step_overlay_trace_records", []) or [])
        suffix = " with transient optical STEP" if live_records else ""
        mode = str(result.sampling_mode or self._active_refresh_sampling_mode() or "default")
        status = f"Open 3D Trace Now updated{suffix} ({reason}, {mode})."
        self.status_var.set(status)
        self.editor.status_var.set(status)
        self._debug_trace(
            "trace_now_refresh",
            reason=reason,
            sampling_mode=mode,
            transient_step_overlays=len(live_records),
        )

    @staticmethod
    def _camera_preset_from_display_orientation(orientation: str) -> str:
        plane = normalize_projection_plane(orientation)
        if plane == "XZ":
            return "xz"
        if plane == "XY":
            return "xy"
        return "zy"

    def _camera_preset_for_display_orientation(self) -> str:
        try:
            orientation = self.editor._current_display_orientation()
        except Exception:
            orientation = "YZ"
        return self._camera_preset_from_display_orientation(str(orientation or "YZ"))

    def _mouse_bindings_service(self) -> Open3DMouseBindingsService:
        service = self.__dict__.get("_mouse_bindings_service_instance")
        if service is None:
            service = Open3DMouseBindingsService(self)
            self._mouse_bindings_service_instance = service
        return service

    def _install_pick_only_left_click_bindings(self) -> None:
        return self._mouse_bindings_service()._install_pick_only_left_click_bindings()

    def _right_click_face_ray_context(self, display_xy, event=None) -> dict[str, object] | None:
        try:
            x, y = display_xy
            display_xy = (float(x), float(y))
        except Exception:
            return None
        candidates: list[tuple[float, int, dict[str, object]]] = []
        for label_order, label in enumerate(STEP_OVERLAY_LABELS):
            label = str(label).strip().lower()
            if self.editor._step_path_for_label(label) is None:
                continue
            try:
                pick = self._step_face_ray_pick_for_display_xy(label, display_xy)
            except Exception:
                pick = None
            if pick is None:
                continue
            candidates.append(
                (
                    float(pick.distance),
                    int(label_order),
                    {
                        "actor": None,
                        "actor_key": None,
                        "cell_id": -1,
                        "feature": self._feature_from_face_ray_pick(pick),
                        "row_index": None,
                        "step_label": label,
                        "point_world": np.asarray(pick.point_world, dtype=float).reshape(3),
                        "normal_world": np.asarray(pick.normal_world, dtype=float).reshape(3),
                        "display_xy": display_xy,
                        "event": event,
                    },
                )
            )
        for row_index, _row in enumerate(list(self.editor.rows or [])):
            if self.editor._file_backed_stl_row_at(int(row_index)) is None:
                continue
            try:
                pick = self._row_face_ray_pick_for_display_xy(int(row_index), display_xy)
            except Exception:
                pick = None
            if pick is None:
                continue
            candidates.append(
                (
                    float(pick.distance),
                    int(len(STEP_OVERLAY_LABELS) + row_index),
                    {
                        "actor": None,
                        "actor_key": None,
                        "cell_id": -1,
                        "feature": self._feature_from_face_ray_pick(pick),
                        "row_index": int(row_index),
                        "step_label": "",
                        "point_world": np.asarray(pick.point_world, dtype=float).reshape(3),
                        "normal_world": np.asarray(pick.normal_world, dtype=float).reshape(3),
                        "display_xy": display_xy,
                        "event": event,
                    },
                )
            )
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        return candidates[0][2]

    def _resolve_picked_step_overlay(self, step_label, row_index):
        """Map a picked transient live-trace ROW back to its STEP-overlay label (bugs/0089).

        After an axis-snap marks an imported STEP overlay physics-preview-ready it
        is folded into the trace and ALSO drawn as a transient live-trace row (rays
        on). A right-click that lands on that row actor resolves no ``step_label``
        and the row is not file-backed, so the context menu falls through to
        "requires a file-backed CAD/STL row" -- the promote / face-assign options
        vanish. When the picked row is a live-trace overlay, treat it as the STEP
        overlay (and drop the row index) so the overlay menu still appears.
        Returns ``(step_label, row_index)``.
        """
        if step_label is None and row_index is not None:
            try:
                live_label = (self._live_trace_step_overlay_label_by_row() or {}).get(int(row_index))
            except Exception:
                live_label = None
            if live_label:
                return str(live_label), None
        return step_label, row_index

    def _right_click_pick_context(self, event) -> dict[str, object] | None:
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        try:
            self._vtk_interactor.SetEventInformationFlipY(int(event.x), int(event.y), 0, 0, chr(0), 0, None)
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
            actor_key = self._actor_key(actor)
            pick_point = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            cell_id = int(self._picker.GetCellId())
        except Exception:
            return None
        if actor_key is None:
            return self._right_click_face_ray_context((float(x), float(y)), event=event)
        if pick_point.size < 3 or not np.all(np.isfinite(pick_point[:3])):
            pick_point = np.asarray([], dtype=float)
        row_index = self._actor_row_map.get(actor_key)
        step_label = self._actor_step_map.get(actor_key)
        # bugs/0089: a physics-preview-ready STEP overlay is also drawn as a
        # transient live-trace row; a right-click on that row must still open the
        # overlay's promote / face-assign menu.
        step_label, row_index = self._resolve_picked_step_overlay(step_label, row_index)
        persistent_file_backed = False
        if row_index is not None:
            try:
                persistent_file_backed = self.editor._file_backed_stl_row_at(int(row_index)) is not None
            except Exception:
                persistent_file_backed = False
        feature = None
        if step_label is None and not persistent_file_backed:
            feature = self._picked_feature_info_cached(actor, self._picker, actor_key=actor_key, cell_id=cell_id)
        feature_center = np.asarray([], dtype=float)
        feature_normal = np.asarray([], dtype=float)
        if feature is not None:
            try:
                feature_center = np.asarray(feature[0], dtype=float).reshape(-1)[:3]
                feature_normal = np.asarray(feature[2], dtype=float).reshape(-1)[:3]
            except Exception:
                feature_center = np.asarray([], dtype=float)
                feature_normal = np.asarray([], dtype=float)
        if feature_center.size >= 3 and np.all(np.isfinite(feature_center[:3])):
            target_point = feature_center[:3]
        elif pick_point.size >= 3:
            target_point = pick_point[:3]
        else:
            target_point = np.asarray([], dtype=float)
        normal = None
        if feature_normal.size >= 3 and np.all(np.isfinite(feature_normal[:3])):
            norm = float(np.linalg.norm(feature_normal[:3]))
            if np.isfinite(norm) and norm > 1e-12:
                normal = feature_normal[:3] / norm
        context = {
            "actor": actor,
            "actor_key": actor_key,
            "cell_id": int(cell_id),
            "feature": feature,
            "row_index": row_index,
            "step_label": step_label,
            "point_world": target_point,
            "normal_world": normal,
            "display_xy": (float(x), float(y)),
            "event": event,
        }
        if step_label is None and (row_index is None or not persistent_file_backed):
            fallback = self._right_click_face_ray_context((float(x), float(y)), event=event)
            if fallback is not None:
                return fallback
        return context

    @staticmethod
    def _ray_event_mesh_face_id(event: object) -> str:
        metadata = getattr(event, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        return str(
            getattr(event, "mesh_face_id", "")
            or getattr(event, "face_id", "")
            or metadata.get("mesh_face_id", "")
            or metadata.get("face_id", "")
            or ""
        ).strip()

    def _row_face_record_for_context(self, row_index: int, face_id: str) -> dict[str, object] | None:
        face_id = str(face_id or "").strip()
        if not face_id:
            return None
        try:
            row, _path, metadata = self.editor._optical_solid_face_metadata_for_row(int(row_index))
        except Exception:
            return None
        transform = self._runtime_transform_for_row(self.__dict__.get("_current_system"), int(row_index))
        if transform is not None:
            faces = self._runtime_world_face_records_for_pick(row, metadata, transform)
        else:
            faces = self.editor._optical_solid_face_records_for_temp_row(row, int(row_index), metadata)
        for record in list(faces or []):
            if str(record.get("face_id", "") or "").strip() == face_id:
                return dict(record)
        return None

    def _traced_row_face_hit_near_display_xy(
        self,
        row_index: int,
        display_xy,
        *,
        tolerance_px: float = 42.0,
    ) -> dict[str, object] | None:
        scene_bundle = getattr(self, "_current_scene_bundle", None)
        if scene_bundle is None:
            return None
        try:
            event_xy = np.asarray(display_xy, dtype=float).reshape(-1)[:2]
        except Exception:
            return None
        if event_xy.size < 2 or not np.all(np.isfinite(event_xy[:2])):
            return None
        best: tuple[float, dict[str, object]] | None = None
        for path in list(getattr(scene_bundle, "ray_paths", []) or []):
            for event in list(getattr(path, "events", []) or []):
                if str(getattr(event, "event_kind", "") or "") != "surface":
                    continue
                try:
                    surface_id = int(getattr(event, "surface_id", -1))
                except Exception:
                    continue
                if surface_id != int(row_index):
                    continue
                face_id = self._ray_event_mesh_face_id(event)
                if not face_id:
                    continue
                point = np.asarray(getattr(event, "point_world", ()), dtype=float).reshape(-1)[:3]
                if point.size < 3 or not np.all(np.isfinite(point[:3])):
                    continue
                display = self._world_to_display_2d(point[:3])
                if display is None or display.size < 2 or not np.all(np.isfinite(display[:2])):
                    continue
                distance_px = float(np.linalg.norm(display[:2] - event_xy[:2]))
                if not np.isfinite(distance_px) or distance_px > float(tolerance_px):
                    continue
                normal = np.asarray(getattr(event, "surface_normal", ()), dtype=float).reshape(-1)[:3]
                if normal.size < 3 or not np.all(np.isfinite(normal[:3])):
                    normal = np.asarray([], dtype=float)
                candidate = {
                    "face_id": face_id,
                    "point_world": np.asarray(point[:3], dtype=float),
                    "normal_world": np.asarray(normal[:3], dtype=float) if normal.size >= 3 else None,
                    "event_type": str(getattr(event, "event_type", "") or ""),
                    "distance_px": distance_px,
                    "ray_index": int(getattr(path, "ray_index", -1) or -1),
                    "step": int(getattr(event, "step", 0) or 0),
                    "face": self._row_face_record_for_context(int(row_index), face_id),
                }
                if best is None or distance_px < best[0]:
                    best = (distance_px, candidate)
        return None if best is None else best[1]

    @staticmethod
    def _open3d_surface_function_menu_items() -> tuple[str, ...]:
        return (
            optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_UNCOATED,
            optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR,
            optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_SPLITTER,
            optical_solid_metadata.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ABSORB,
            OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
        )

    def _on_show_rays_changed(self) -> None:
        self._debug_trace("show_rays_toggled", show_rays=bool(self.show_rays_var.get()), counts=self._debug_actor_counts())
        if self.editor._open3d_trace_refresh_service().can_reuse_current_scene_for_show_rays(self):
            self._debug_trace(
                "show_rays_fast_toggle_refresh",
                show_rays=bool(self.show_rays_var.get()),
                transient_step_overlays=len(self._live_trace_step_overlay_labels()),
            )
            self.refresh_scene(
                self.__dict__.get("_current_system"),
                self.__dict__.get("_current_rays"),
                list(self.__dict__.get("_current_row_names", []) or []),
                scene_bundle=self.__dict__.get("_current_scene_bundle"),
                reset_camera=False,
            )
            return
        self.refresh_from_editor()

    def _ray_pick_enabled(self) -> bool:
        try:
            return bool(self.ray_pick_enabled_var.get())
        except Exception:
            return False

    def _on_ray_pick_changed(self) -> None:
        enabled = self._ray_pick_enabled()
        if not enabled:
            self._set_ray_highlight(None)
            self.status_var.set("Ray picking disabled. Use the Pick rays toggle before opening Ray Inspector from the 3D canvas.")
        else:
            self.status_var.set("Ray picking enabled. Click a traced ray to open Ray Inspector.")
        self.render()

    def _on_scene_visibility_changed(self) -> None:
        self._debug_trace(
            "scene_visibility_toggled",
            show_rays=bool(self.show_rays_var.get()),
            show_reference_surfaces=bool(self.show_reference_surfaces_var.get()),
            show_detector_overlays=bool(self.show_detector_overlays_var.get()),
            show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get()),
            show_placement_handles=bool(self.show_placement_handles_var.get()),
            show_thickness_dimensions=bool(self.editor.show_physical_distances_var.get()),
            counts=self._debug_actor_counts(),
        )
        self.refresh_from_editor()

    def _on_clipped_rays_changed(self) -> None:
        # "Show clipped rays" is the *shared* 2D var (KrakenLayoutEditor.
        # show_clipped_rays_var), bound here via _editor_var so the 3D toggle and
        # the 2D checkbox flip the same tk.BooleanVar -- bidirectional sync, the
        # bug-0059 ray-count pattern. The 3D ray-line filter already reads this
        # var (three_d_scene_tools._iter_3d_scene_ray_records); the 3D view simply
        # had no control to flip it (bugs/0061). Mark the 2D plot pending so the
        # main window redraws to match, then refresh the 3D scene to apply the
        # filter immediately.
        try:
            self.editor._mark_plot_update_pending()
        except Exception as exc:
            self.editor.append_debug(f"Open 3D clipped-rays 2D sync failed: {exc}")
        self._on_scene_visibility_changed()

    def _face_assignment_service(self) -> Open3DFaceAssignmentService:
        service = self.__dict__.get("_face_assignment_service_instance")
        if service is None:
            service = Open3DFaceAssignmentService(self)
            self._face_assignment_service_instance = service
        return service

    def _show_surface_function_context_menu(self, event) -> str:
        return self._face_assignment_service()._show_surface_function_context_menu(event)

    def _assign_row_face_function_from_context(
        self,
        row_index: int,
        point_world,
        normal_world,
        function_label: str,
        *,
        face_id: str = "",
    ) -> None:
        return self._face_assignment_service()._assign_row_face_function_from_context(
            row_index,
            point_world,
            normal_world,
            function_label,
            face_id=face_id,
        )

    def _promote_step_from_context(self, label: str) -> None:
        return self._face_assignment_service()._promote_step_from_context(label)

    def _promote_step_and_assign_face_function(
        self,
        label: str,
        point_world,
        normal_world,
        function_label: str,
        *,
        face_id: str = "",
    ) -> None:
        return self._face_assignment_service()._promote_step_and_assign_face_function(
            label,
            point_world,
            normal_world,
            function_label,
            face_id=face_id,
        )

    def _placement_handle_info_for_actor_key(self, actor_key: str | None) -> tuple[str, int, str, float] | None:
        if actor_key is None:
            return None
        placement_rotate = self._actor_placement_rotate_map.get(actor_key)
        if placement_rotate is not None:
            row_index, axis, delta_deg = placement_rotate
            return "rotate", int(row_index), str(axis), float(delta_deg)
        placement_move = self._actor_placement_move_map.get(actor_key)
        if placement_move is not None:
            row_index, axis, delta_mm = placement_move
            return "translate", int(row_index), str(axis), float(delta_mm)
        return None

    def _placement_drag_state_from_current_pick(self) -> dict[str, object] | None:
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        if (
            self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or self._dimension_anchor_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        ):
            return None
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
        except Exception:
            return None
        info = self._placement_handle_info_for_actor_key(self._actor_key(actor))
        if info is None:
            return None
        kind, row_index, axis, signed_step = info
        direction = self._placement_drag_display_direction(kind, axis, signed_step, actor)
        self.status_var.set(
            "Drag S{row} placement {kind} {axis}; click without dragging for one snap step.".format(
                row=int(row_index),
                kind="rotation" if kind == "rotate" else "translation",
                axis=str(axis).upper(),
            )
        )
        return {
            "kind": kind,
            "row_index": int(row_index),
            "axis": str(axis).strip().lower(),
            "signed_step": float(signed_step),
            "display_direction": direction,
            "pixel_accumulator": 0.0,
            "applied_steps": 0,
        }

    @staticmethod
    def _event_control_pressed(event) -> bool:
        try:
            return bool(int(getattr(event, "state", 0)) & 0x0004)
        except Exception:
            return False

    @staticmethod
    def _placement_axis_vector(axis: str) -> np.ndarray:
        axis_key = str(axis or "").strip().lower()
        if axis_key == "x":
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        if axis_key == "y":
            return np.asarray((0.0, 1.0, 0.0), dtype=float)
        return np.asarray((0.0, 0.0, 1.0), dtype=float)

    def _world_to_display_2d(self, point: np.ndarray) -> np.ndarray | None:
        if self._renderer is None:
            return None
        try:
            values = np.asarray(point, dtype=float).reshape(-1)
            if values.size < 3 or not np.all(np.isfinite(values[:3])):
                return None
            self._renderer.SetWorldPoint(float(values[0]), float(values[1]), float(values[2]), 1.0)
            self._renderer.WorldToDisplay()
            display = np.asarray(self._renderer.GetDisplayPoint(), dtype=float).reshape(-1)
            if display.size < 2 or not np.all(np.isfinite(display[:2])):
                return None
            return display[:2]
        except Exception:
            return None

    @staticmethod
    def _point_segment_distance_2d(point, start, end) -> tuple[float, float]:
        p = np.asarray(point, dtype=float).reshape(2)
        a = np.asarray(start, dtype=float).reshape(2)
        b = np.asarray(end, dtype=float).reshape(2)
        segment = b - a
        length_sq = float(np.dot(segment, segment))
        if not np.isfinite(length_sq) or length_sq <= 1e-12:
            return float(np.linalg.norm(p - a)), 0.0
        t = float(np.clip(np.dot(p - a, segment) / length_sq, 0.0, 1.0))
        closest = a + t * segment
        return float(np.linalg.norm(p - closest)), t

    def _optical_axis_info_near_display_xy(self, display_xy, *, tolerance_px: float = 22.0) -> dict[str, object] | None:
        try:
            event_xy = np.asarray(display_xy, dtype=float).reshape(-1)[:2]
        except Exception:
            return None
        if event_xy.size < 2 or not np.all(np.isfinite(event_xy[:2])):
            return None
        best: tuple[float, dict[str, object]] | None = None
        for record in list(self._optical_axis_pick_records or []):
            points = np.asarray(record.get("points"), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                continue
            display_points: list[np.ndarray | None] = []
            for point in points[:, :3]:
                display = self._world_to_display_2d(point)
                if display is None or display.size < 2 or not np.all(np.isfinite(display[:2])):
                    display_points.append(None)
                else:
                    display_points.append(np.asarray(display[:2], dtype=float))
            for index in range(len(points) - 1):
                start = display_points[index]
                end = display_points[index + 1]
                if start is None or end is None:
                    continue
                try:
                    distance, t = self._point_segment_distance_2d(event_xy[:2], start[:2], end[:2])
                except Exception:
                    continue
                if not np.isfinite(distance) or distance > float(tolerance_px):
                    continue
                start_world = points[index, :3]
                end_world = points[index + 1, :3]
                picked_world = np.asarray(start_world + t * (end_world - start_world), dtype=float)
                axis_info = dict(record)
                axis_info["picked_world"] = picked_world
                axis_info["picked_display_xy"] = tuple(float(value) for value in event_xy[:2])
                if best is None or distance < best[0]:
                    best = (float(distance), axis_info)
        return best[1] if best is not None else None

    def _tk_xy_to_vtk_display_xy(self, xy) -> tuple[float, float] | None:
        if self._vtk_widget is None:
            return None
        try:
            x, y = np.asarray(xy, dtype=float).reshape(-1)[:2]
        except Exception:
            return None
        if not (np.isfinite(x) and np.isfinite(y)):
            return None
        try:
            width, height = self._vtk_widget.GetRenderWindow().GetSize()
        except Exception:
            try:
                width = int(self._vtk_widget.winfo_width())
                height = int(self._vtk_widget.winfo_height())
            except Exception:
                return None
        width = max(int(width), 1)
        height = max(int(height), 1)
        return (
            float(min(max(float(x), 0.0), float(width - 1))),
            float(min(max(float(height - 1) - float(y), 0.0), float(height - 1))),
        )

    def _display_to_world_3d(self, display_xy, display_z: float) -> np.ndarray | None:
        if self._renderer is None:
            return None
        try:
            x, y = np.asarray(display_xy, dtype=float).reshape(-1)[:2]
            z = float(display_z)
        except Exception:
            return None
        if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(z)):
            return None
        try:
            self._renderer.SetDisplayPoint(float(x), float(y), float(z))
            self._renderer.DisplayToWorld()
            world = np.asarray(self._renderer.GetWorldPoint(), dtype=float).reshape(-1)
            if world.size < 4 or not np.all(np.isfinite(world[:4])) or abs(float(world[3])) <= 1e-12:
                return None
            return np.asarray(world[:3] / float(world[3]), dtype=float)
        except Exception:
            return None

    def _display_pick_ray(self, display_xy) -> tuple[np.ndarray, np.ndarray] | None:
        near = self._display_to_world_3d(display_xy, 0.0)
        far = self._display_to_world_3d(display_xy, 1.0)
        if near is None or far is None:
            return None
        direction = self._normalized_vector(far[:3] - near[:3])
        if direction is None:
            return None
        return np.asarray(near[:3], dtype=float), np.asarray(direction[:3], dtype=float)

    @staticmethod
    def _normalized_vector(values) -> np.ndarray | None:
        try:
            vector = np.asarray(values, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
            return None
        norm = float(np.linalg.norm(vector[:3]))
        if not np.isfinite(norm) or norm <= 1e-12:
            return None
        return np.asarray(vector[:3] / norm, dtype=float)

    def _camera_view_normal(self) -> np.ndarray | None:
        if self._renderer is None:
            return None
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return None
        try:
            position = np.asarray(camera.GetPosition(), dtype=float).reshape(-1)[:3]
            focal = np.asarray(camera.GetFocalPoint(), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        return self._normalized_vector(focal[:3] - position[:3])

    def _cursor_plane_point(self, tk_xy, plane_origin, plane_normal) -> np.ndarray | None:
        display_xy = self._tk_xy_to_vtk_display_xy(tk_xy)
        if display_xy is None:
            return None
        near = self._display_to_world_3d(display_xy, 0.0)
        far = self._display_to_world_3d(display_xy, 1.0)
        if near is None or far is None:
            return None
        try:
            plane_origin_values = np.asarray(plane_origin, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        normal = self._normalized_vector(plane_normal)
        direction = self._normalized_vector(far[:3] - near[:3])
        if (
            normal is None
            or direction is None
            or plane_origin_values.size < 3
            or not np.all(np.isfinite(plane_origin_values[:3]))
        ):
            return None
        denom = float(np.dot(direction, normal))
        if not np.isfinite(denom) or abs(denom) <= 1e-9:
            return None
        distance = float(np.dot(plane_origin_values[:3] - near[:3], normal) / denom)
        if not np.isfinite(distance):
            return None
        return np.asarray(near[:3] + direction * distance, dtype=float)

    @staticmethod
    def _step_carry_hold_delay_ms() -> int:
        return Open3DStepStateService.carry_hold_delay_ms()

    def _set_step_carry_cursor(self, active: bool) -> None:
        try:
            if self._vtk_widget is not None:
                if active:
                    try:
                        self._vtk_widget.configure(cursor="none")
                    except Exception:
                        self._vtk_widget.configure(cursor="fleur")
                else:
                    self._vtk_widget.configure(cursor="")
        except Exception:
            pass
        try:
            if self._vtk_interactor is not None:
                self._vtk_interactor.SetCurrentCursor(9 if active else 0)
        except Exception:
            pass

    def _step_overlay_center_world(self, label: str) -> np.ndarray | None:
        try:
            mesh = self.editor._transformed_imported_step_mesh_for_label(str(label).strip().lower())
        except Exception:
            mesh = None
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        try:
            bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
            if bounds.size == 6 and np.all(np.isfinite(bounds)):
                return np.asarray(
                    (
                        0.5 * (float(bounds[0]) + float(bounds[1])),
                        0.5 * (float(bounds[2]) + float(bounds[3])),
                        0.5 * (float(bounds[4]) + float(bounds[5])),
                    ),
                    dtype=float,
                )
        except Exception:
            pass
        try:
            points = np.asarray(mesh.points, dtype=float)
            if points.ndim == 2 and points.shape[1] >= 3 and points.shape[0] > 0:
                center = np.mean(points[:, :3], axis=0)
                if np.all(np.isfinite(center)):
                    return np.asarray(center, dtype=float)
        except Exception:
            pass
        return None

    def _cancel_step_carry_hold_timer(self) -> None:
        after_id = self._step_carry_hold_after_id
        self._step_carry_hold_after_id = None
        self._step_carry_hold_candidate_label = None
        self._step_carry_hold_press_xy = None
        self._step_carry_hold_pick_world = None
        if after_id is None or self._vtk_widget is None:
            return
        try:
            self._vtk_widget.after_cancel(after_id)
        except Exception:
            pass

    def _cancel_row_carry_hold_timer(self) -> None:
        after_id = self._row_carry_hold_after_id
        self._row_carry_hold_after_id = None
        self._row_carry_hold_candidate_index = None
        self._row_carry_hold_press_xy = None
        self._row_carry_hold_pick_world = None
        if after_id is None or self._vtk_widget is None:
            return
        try:
            self._vtk_widget.after_cancel(after_id)
        except Exception:
            pass

    def _row_actor_center_world(self, row_index: int) -> np.ndarray | None:
        bounds_min = np.asarray((np.inf, np.inf, np.inf), dtype=float)
        bounds_max = np.asarray((-np.inf, -np.inf, -np.inf), dtype=float)
        found = False
        for actor_key in list(self._row_actor_map.get(int(row_index), []) or []):
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            try:
                bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
            except Exception:
                continue
            if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                continue
            bounds_min = np.minimum(bounds_min, (bounds[0], bounds[2], bounds[4]))
            bounds_max = np.maximum(bounds_max, (bounds[1], bounds[3], bounds[5]))
            found = True
        if not found:
            return None
        return np.asarray(0.5 * (bounds_min + bounds_max), dtype=float)

    def _row_carry_index_from_current_pick(self) -> int | None:
        self._row_carry_hold_pick_world = None
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        if (
            self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or self._dimension_anchor_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        ):
            return None
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
            actor_key = self._actor_key(actor)
            pick_world = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if actor_key is None:
            return None
        if (
            actor_key in self._actor_step_map
            or actor_key in self._actor_step_rotate_map
            or actor_key in self._actor_step_translate_map
            or actor_key in self._actor_placement_move_map
            or actor_key in self._actor_placement_rotate_map
            or actor_key in self._actor_optical_axis_map
            or actor_key in self._actor_ray_map
        ):
            return None
        row_index = self._actor_row_map.get(actor_key)
        if row_index is None:
            return None
        try:
            row_index = int(row_index)
        except Exception:
            return None
        if self.editor._file_backed_stl_row_at(row_index) is None and not self._is_detector_carry_row(row_index):
            return None
        if pick_world.size >= 3 and np.all(np.isfinite(pick_world[:3])):
            self._row_carry_hold_pick_world = tuple(float(value) for value in pick_world[:3])
        return row_index

    def _arm_row_carry_hold(self, row_index: int, press_xy: tuple[int, int]) -> None:
        if self._vtk_widget is None:
            return
        try:
            row_index = int(row_index)
        except Exception:
            return
        is_detector = self._is_detector_carry_row(row_index)
        if self.editor._file_backed_stl_row_at(row_index) is None and not is_detector:
            return
        self._cancel_row_carry_hold_timer()
        self._row_carry_hold_candidate_index = row_index
        self._row_carry_hold_press_xy = (int(press_xy[0]), int(press_xy[1]))
        if is_detector:
            self.status_var.set(f"Hold S{row_index} (detector) briefly to grab it; drag along the optical axis to defocus; release to drop.")
        else:
            self.status_var.set(f"Hold S{row_index} briefly to lift the promoted optical solid; drag freely; release to drop.")
        try:
            self._row_carry_hold_after_id = self._vtk_widget.after(
                self._step_carry_hold_delay_ms(),
                self._activate_row_carry_hold,
            )
        except Exception as exc:
            self.editor.append_debug(f"Open 3D row carry hold timer failed: {exc}")

    def _step_carry_label_from_current_pick(self) -> str | None:
        self._step_carry_hold_pick_world = None
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        if (
            self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or self._dimension_anchor_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        ):
            return None
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor_key = self._actor_key(self._picker.GetActor())
            pick_world = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
        except Exception:
            actor_key = None
            pick_world = np.asarray([], dtype=float)
        if actor_key is None or actor_key in self._actor_step_rotate_map or actor_key in self._actor_step_translate_map:
            return None
        if actor_key in self._actor_placement_move_map or actor_key in self._actor_placement_rotate_map:
            return None
        label = str(self._actor_step_map.get(actor_key) or "").strip().lower()
        if label in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(label) is not None:
            if pick_world.size >= 3 and np.all(np.isfinite(pick_world[:3])):
                self._step_carry_hold_pick_world = tuple(float(value) for value in pick_world[:3])
            return label
        return None

    def _arm_step_carry_hold(self, label: str, press_xy: tuple[int, int]) -> None:
        if self._vtk_widget is None:
            return
        transition = self.editor._open3d_step_state_service().prepare_carry_hold_arm(label, press_xy)
        if not transition.has_label or not transition.has_press_xy:
            if transition.status:
                self.status_var.set(transition.status)
            return
        self._cancel_step_carry_hold_timer()
        self._step_carry_hold_candidate_label = transition.label
        self._step_carry_hold_press_xy = transition.press_xy
        if transition.status:
            self.status_var.set(transition.status)
        try:
            self._step_carry_hold_after_id = self._vtk_widget.after(
                self._step_carry_hold_delay_ms(),
                self._activate_step_carry_hold,
            )
        except Exception as exc:
            self.editor.append_debug(f"STEP carry hold timer failed: {exc}")

    def _activate_step_carry_hold(self) -> None:
        self._step_carry_hold_after_id = None
        request = self.editor._open3d_step_state_service().consume_carry_hold_request(
            self._step_carry_hold_candidate_label,
            self._step_carry_hold_press_xy,
            self._step_carry_hold_pick_world,
        )
        self._step_carry_hold_candidate_label = None
        self._step_carry_hold_press_xy = None
        self._step_carry_hold_pick_world = None
        if not self._left_drag_active or not request.has_label:
            return
        label = request.label
        press_xy = request.press_xy if request.has_press_xy else None
        pick_world = request.pick_world if request.has_pick_world else None
        center_world = self._step_overlay_center_world(label)
        state = self._new_step_carry_motion_state(label)
        plane_normal = self._camera_view_normal() if center_world is not None else None
        anchor_world = None
        if center_world is not None and plane_normal is not None:
            anchor_xy = self._left_drag_last_xy or press_xy
            if anchor_xy is not None:
                anchor_world = self._cursor_plane_point(anchor_xy, center_world[:3], plane_normal[:3])
        transition = self.editor._open3d_step_state_service().prepare_carry_hold_state(
            label,
            state,
            left_drag_active=self._left_drag_active,
            press_xy=press_xy,
            last_xy=self._left_drag_last_xy,
            center_world=center_world,
            pick_world=pick_world,
            plane_normal=plane_normal,
            anchor_world=anchor_world,
        )
        if not transition.has_state:
            if transition.status:
                self.status_var.set(transition.status)
            return
        state = transition.state
        label = transition.label
        self._step_carry_active_label = label
        self._step_carry_drag_state = state
        self._step_carry_follow_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self.editor.select_step_component(label)
        self._set_step_highlight(label, render=False)
        self.show_step_rotation_handler(label)
        self._set_step_carry_cursor(True)
        if transition.has_grip_world:
            self._open3d_carry_grip_service.show(transition.grip_world)
        self._update_mode_badge()
        if transition.status:
            self.status_var.set(transition.status)

    def _new_row_carry_motion_state(self, row_index: int) -> dict[str, object] | None:
        center_world = self._row_actor_center_world(row_index)
        plane_normal = self._camera_view_normal()
        if self._is_detector_carry_row(row_index):
            # Detector (Image-row) drag handle: reuse the carry plumbing but motion is axial-only
            # (+Z optical axis) and applied to the last gap, so the detector slides to defocus while
            # the camera stays glued to it (item 1/2).
            if center_world is not None:
                center = np.asarray(center_world, dtype=float).reshape(-1)[:3]
            else:
                det_z = sum(float(r.thickness) for r in self.editor.rows[:-1])  # on-axis detector station
                center = np.array([0.0, 0.0, float(det_z)], dtype=float)
            if plane_normal is None:
                return None
            normal = np.asarray(plane_normal, dtype=float).reshape(-1)[:3]
            if center.size < 3 or normal.size < 3 or not np.all(np.isfinite(center)) or not np.all(np.isfinite(normal)):
                return None
            return {
                "row_index": int(row_index),
                "detector_carry": True,
                "center_world": tuple(float(v) for v in center[:3]),
                "start_center_world": tuple(float(v) for v in center[:3]),
                "drag_plane_origin": tuple(float(v) for v in center[:3]),
                "drag_plane_normal": tuple(float(v) for v in normal[:3]),
                "applied_steps": 0,
                "history_started": False,
            }
        return self.editor._open3d_step_state_service().row_carry_motion_state(
            row_index,
            center_world=center_world,
            plane_normal=plane_normal,
        )

    def _is_detector_carry_row(self, row_index) -> bool:
        """The detector = the final on-axis Image row; eligible for the dedicated axial drag handle."""
        try:
            idx = int(row_index)
        except Exception:
            return False
        rows = getattr(self.editor, "rows", None) or []
        if len(rows) < 3 or idx != len(rows) - 1:
            return False
        last = rows[idx]
        return (
            str(getattr(last, "surface", "") or "") == "Image"
            and abs(float(getattr(last, "desp_y", 0.0) or 0.0)) <= 1e-6
            and abs(float(getattr(last, "desp_z", 0.0) or 0.0)) <= 1e-6
        )

    def _activate_row_carry_hold(self) -> None:
        self._row_carry_hold_after_id = None
        row_index = self._row_carry_hold_candidate_index
        press_xy = self._row_carry_hold_press_xy
        pick_world = self._row_carry_hold_pick_world
        self._row_carry_hold_candidate_index = None
        self._row_carry_hold_press_xy = None
        self._row_carry_hold_pick_world = None
        if not self._left_drag_active or row_index is None:
            return
        state = self._new_row_carry_motion_state(int(row_index))
        if state is None:
            self.status_var.set(f"Carry S{int(row_index)}: selected row is not a movable promoted optical solid.")
            return
        if bool(state.get("detector_carry")):
            self._activate_detector_carry_hold(state, press_xy)
            return
        center_world = np.asarray(state["center_world"], dtype=float).reshape(3)
        plane_normal = np.asarray(state["drag_plane_normal"], dtype=float).reshape(3)
        anchor_xy = self._left_drag_last_xy or press_xy
        anchor_world = None
        if anchor_xy is not None:
            anchor_world = self._cursor_plane_point(anchor_xy, center_world[:3], plane_normal[:3])
        transition = self.editor._open3d_step_state_service().prepare_row_carry_hold_state(
            row_index,
            state,
            left_drag_active=self._left_drag_active,
            press_xy=press_xy,
            last_xy=self._left_drag_last_xy,
            pick_world=pick_world,
            anchor_world=anchor_world,
        )
        if not transition.has_state:
            if transition.status:
                self.status_var.set(transition.status)
            return
        state = transition.state
        self._row_carry_drag_state = state
        self._step_carry_drag_state = None
        self._step_carry_follow_state = None
        self._set_step_hover_outline(None, None, render=False)
        self._update_hover_status("", render=False)
        self._set_step_carry_cursor(True)
        if transition.has_grip_world:
            self._open3d_carry_grip_service.show(transition.grip_world)
        self.editor._select_table_row(int(row_index))
        self.highlight_row(int(row_index))
        self._update_mode_badge()
        if transition.status:
            self.status_var.set(transition.status)

    def _translate_row_actors(self, row_index: int, delta_xyz) -> int:
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
        except Exception:
            return 0
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            return 0
        moved = 0
        for actor_key in list(dict.fromkeys(self._row_actor_map.get(int(row_index), []) or [])):
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            try:
                actor.AddPosition(float(delta[0]), float(delta[1]), float(delta[2]))
                moved += 1
            except Exception as exc:
                self.editor.append_debug(f"3D row carry actor move failed for S{int(row_index)}: {exc}")
        if moved:
            try:
                self._reset_camera_clipping_range_for_scene()
            except Exception:
                pass
            self.render()
        return moved

    def _translate_placement_handle_actors(self, row_index: int, delta_xyz) -> int:
        """bugs/0012: move a row's placement Move/Rotate handle actors by the same
        cheap ``AddPosition`` as its body during a live placement drag, so the
        gizmo tracks the lens instead of staying behind (no rebuild/retrace)."""
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
        except Exception:
            return 0
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            return 0
        moved = 0
        for handle_map in (self._actor_placement_move_map, self._actor_placement_rotate_map):
            for actor_key, info in list(handle_map.items()):
                try:
                    if int(info[0]) != int(row_index):
                        continue
                except Exception:
                    continue
                actor = self._actor_by_key.get(actor_key)
                if actor is None:
                    continue
                try:
                    actor.AddPosition(float(delta[0]), float(delta[1]), float(delta[2]))
                    moved += 1
                except Exception:
                    pass
        return moved

    def _apply_row_carry_drag_motion(self, *, current_xy: tuple[int, int] | None = None) -> None:
        state = self._row_carry_drag_state
        if state is None or current_xy is None:
            return
        try:
            plane_origin = np.asarray(state.get("drag_plane_origin"), dtype=float).reshape(-1)[:3]
            plane_normal = np.asarray(state.get("drag_plane_normal"), dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if plane_origin.size < 3 or plane_normal.size < 3:
            return
        cursor_world = self._cursor_plane_point(current_xy, plane_origin[:3], plane_normal[:3])
        if cursor_world is None:
            return
        if self._hover_step_outline_actor is not None or self._hover_step_cell_key is not None:
            self._set_step_hover_outline(None, None, render=False)
            self._update_hover_status("", render=False)
        _scene_center, scene_span = self._scene_bounds()
        movement = self.editor._open3d_step_state_service().row_carry_plane_motion_delta(
            state,
            cursor_world=cursor_world,
            scene_span=float(scene_span),
        )
        if movement is None:
            return
        if movement.debug_message:
            self.editor.append_debug(movement.debug_message)
            return
        if not movement.has_delta:
            return
        if not bool(state.get("history_started", False)):
            try:
                self.editor._begin_history_capture()
                state["history_started"] = True
            except Exception:
                pass
        row_index = int(movement.row_index)
        delta = np.asarray(movement.delta_xyz, dtype=float).reshape(-1)[:3]
        if bool(state.get("detector_carry")):
            axial = float(delta[2])   # +Z optical axis -> the image-distance (last) gap
            if abs(axial) > 1e-9:
                self.editor.rows[-2].thickness = float(self.editor.rows[-2].thickness) + axial
                axial_vec = np.array([0.0, 0.0, axial], dtype=float)
                if self._translate_row_actors(row_index, axial_vec) <= 0:
                    self.editor._invalidate_preview_scene_trace()
                    self.refresh_from_editor()
                self._open3d_carry_grip_service.update_after_delta(state, axial_vec)
                c = np.asarray(state.get("center_world"), dtype=float).reshape(-1)[:3]
                state["center_world"] = (float(c[0]), float(c[1]), float(c[2] + axial))
                state["applied_steps"] = int(state.get("applied_steps", 0)) + 1
            return
        try:
            self.editor.translate_scene_row_pose_vector(
                row_index,
                delta[:3],
                record_history=False,
                sync_table=False,
            )
        except Exception as exc:
            self.status_var.set(f"Row carry failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D row carry failed: {exc}")
            return
        if self._translate_row_actors(row_index, delta[:3]) <= 0:
            self.refresh_from_editor()
        self._open3d_carry_grip_service.update_after_delta(state, delta[:3])
        self.editor._open3d_step_state_service().apply_row_carry_motion_delta(state, movement)

    def _finish_row_carry_drag(self, state: dict[str, object]) -> None:
        if bool(state.get("detector_carry")):
            self._finish_detector_carry_drag(state)
            return
        transition = self.editor._open3d_step_state_service().row_carry_finish_transition(state)
        if transition is None:
            return
        try:
            self.editor._commit_history_capture()
        except Exception:
            pass
        row_index = int(transition.row_index)
        self._row_carry_drag_state = None
        self._set_step_carry_cursor(False)
        self._set_step_hover_outline(None, None, render=False)
        self._update_hover_status("", render=False)
        self._open3d_carry_grip_service.clear(render=False)
        self._update_mode_badge()
        if row_index >= 0:
            self._stl_placement_row_index = row_index
            self._stl_placement_dirty = True
            try:
                self.editor._sync_table()
                self.editor._select_table_row(row_index)
            except Exception:
                pass
        if not transition.moved:
            self.status_var.set(transition.status)
            return
        try:
            self.refresh_from_editor()
            self.highlight_row(row_index)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D row carry final refresh failed: {exc}")
        self.status_var.set(transition.status)

    def _activate_detector_carry_hold(self, state: dict[str, object], press_xy) -> None:
        """Set up the detector (Image-row) axial carry: anchor the drag plane at the press point so
        the subsequent motion slides the detector along the optical axis (item 1/2 detector handle)."""
        center_world = np.asarray(state["center_world"], dtype=float).reshape(3)
        plane_normal = np.asarray(state["drag_plane_normal"], dtype=float).reshape(3)
        anchor_xy = self._left_drag_last_xy or press_xy
        anchor_world = None
        if anchor_xy is not None:
            anchor_world = self._cursor_plane_point(anchor_xy, center_world[:3], plane_normal[:3])
        if anchor_world is None:
            anchor_world = center_world[:3]
        state["drag_anchor_world"] = tuple(float(v) for v in np.asarray(anchor_world, dtype=float).reshape(-1)[:3])
        self._row_carry_drag_state = state
        self._step_carry_drag_state = None
        self._step_carry_follow_state = None
        self._set_step_hover_outline(None, None, render=False)
        self._update_hover_status("", render=False)
        self._set_step_carry_cursor(True)
        try:
            grip = np.asarray(state.get("center_world"), dtype=float).reshape(-1)[:3]
            if grip.size >= 3 and np.all(np.isfinite(grip[:3])):
                self._open3d_carry_grip_service.show(grip[:3])
        except Exception:
            pass
        self._update_mode_badge()
        self.status_var.set("Carrying the detector: drag along the optical axis to defocus; release to drop.")

    def _finish_detector_carry_drag(self, state: dict[str, object]) -> None:
        moved = int(state.get("applied_steps", 0)) > 0
        if bool(state.get("history_started", False)):
            try:
                self.editor._commit_history_capture()
            except Exception:
                pass
        self._row_carry_drag_state = None
        self._set_step_carry_cursor(False)
        self._set_step_hover_outline(None, None, render=False)
        self._update_hover_status("", render=False)
        self._open3d_carry_grip_service.clear(render=False)
        self._update_mode_badge()
        if not moved:
            self.status_var.set("Detector drop: no movement.")
            return
        try:
            self.editor._sync_table()
        except Exception:
            pass
        try:
            self.refresh_from_editor(force_retrace=True)
        except Exception as exc:
            self.editor.append_debug(f"Detector carry final refresh failed: {exc}")
        try:
            det_z = sum(float(r.thickness) for r in self.editor.rows[:-1])
            img_z = self.editor._paraxial_image_plane_z()
            if img_z is not None:
                self.status_var.set(f"Detector at z={det_z:.4g} mm (defocus {det_z - float(img_z):+.4g} mm from best focus).")
            else:
                self.status_var.set(f"Detector at z={det_z:.4g} mm.")
        except Exception:
            self.status_var.set("Detector moved.")

    def _current_widget_pointer_xy(self) -> tuple[int, int] | None:
        if self._vtk_widget is not None:
            try:
                x = int(self._vtk_widget.winfo_pointerx() - self._vtk_widget.winfo_rootx())
                y = int(self._vtk_widget.winfo_pointery() - self._vtk_widget.winfo_rooty())
                width = max(int(self._vtk_widget.winfo_width()), 1)
                height = max(int(self._vtk_widget.winfo_height()), 1)
                if 0 <= x <= width and 0 <= y <= height:
                    return (x, y)
            except Exception:
                pass
        return None

    def _current_interactor_xy(self) -> tuple[int, int] | None:
        pointer_xy = self._current_widget_pointer_xy()
        if pointer_xy is not None:
            return pointer_xy
        if self._vtk_interactor is None:
            return None
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            return (int(x), int(y))
        except Exception:
            return None

    def _new_step_carry_follow_state(self, label: str) -> dict[str, object] | None:
        state = self._new_step_carry_motion_state(label)
        if state is None:
            return None
        center_world = self._step_overlay_center_world(label)
        plane_normal = self._camera_view_normal()
        current_xy = self._current_widget_pointer_xy()
        if center_world is None or plane_normal is None:
            return state
        anchor_world = None
        if current_xy is not None:
            anchor_world = self._cursor_plane_point(current_xy, center_world[:3], plane_normal[:3])
        transition = self.editor._open3d_step_state_service().prepare_carry_follow_state(
            state,
            center_world=center_world,
            plane_normal=plane_normal,
            anchor_world=anchor_world,
            attach_to_cursor_on_next_motion=current_xy is None,
        )
        if transition is None:
            return state
        if transition.has_initial_delta:
            try:
                delta = np.asarray(transition.initial_delta_xyz, dtype=float).reshape(-1)[:3]
            except Exception:
                delta = np.asarray([], dtype=float)
            if delta.size >= 3 and np.all(np.isfinite(delta[:3])):
                try:
                    self.editor._begin_history_capture()
                    state["history_started"] = True
                except Exception:
                    pass
                self.editor.translate_step_overlay(label, delta, grid_spacing_mm=None, refresh=False, record_history=False)
                if self._translate_step_overlay_actors(label, delta) <= 0:
                    self.refresh_from_editor()
        return transition.state

    def _start_step_carry_follow(self, label: str) -> None:
        label = str(label).strip().lower()
        state = self._new_step_carry_follow_state(label)
        self._step_carry_active_label = label if state is not None else None
        self._step_carry_follow_state = state
        self._step_carry_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_step_carry_cursor(state is not None)
        if state is not None:
            try:
                grip = np.asarray(state.get("grip_world"), dtype=float).reshape(-1)[:3]
                if grip.size >= 3 and np.all(np.isfinite(grip[:3])):
                    self._open3d_carry_grip_service.show(grip[:3])
            except Exception:
                pass
        self._update_mode_badge()

    def _apply_step_carry_follow_motion(self) -> None:
        state = self._step_carry_follow_state
        current_xy = self._current_interactor_xy()
        if state is None or current_xy is None:
            return
        self._set_step_carry_cursor(True)
        if bool(state.get("attach_to_cursor_on_next_motion", False)):
            try:
                center_world = np.asarray(state.get("center_world"), dtype=float).reshape(-1)[:3]
                plane_origin = np.asarray(state.get("drag_plane_origin"), dtype=float).reshape(-1)[:3]
                plane_normal = np.asarray(state.get("drag_plane_normal"), dtype=float).reshape(-1)[:3]
            except Exception:
                center_world = plane_origin = plane_normal = np.asarray([], dtype=float)
            cursor_world = None
            if center_world.size >= 3 and plane_origin.size >= 3 and plane_normal.size >= 3:
                cursor_world = self._cursor_plane_point(current_xy, plane_origin[:3], plane_normal[:3])
            if cursor_world is not None:
                delta = np.asarray(cursor_world[:3] - center_world[:3], dtype=float)
                if np.any(np.abs(delta[:3]) > 1e-12):
                    if not bool(state.get("history_started", False)):
                        try:
                            self.editor._begin_history_capture()
                            state["history_started"] = True
                        except Exception:
                            pass
                    label = str(state.get("label", "")).strip().lower()
                    self.editor.translate_step_overlay(label, delta, grid_spacing_mm=None, refresh=False, record_history=False)
                    if self._translate_step_overlay_actors(label, delta) <= 0:
                        self.refresh_from_editor()
                    self._open3d_carry_grip_service.update_after_delta(state, delta)
                state["center_world"] = tuple(float(value) for value in np.asarray(cursor_world, dtype=float).reshape(-1)[:3])
                state["start_center_world"] = tuple(float(value) for value in np.asarray(cursor_world, dtype=float).reshape(-1)[:3])
                state["drag_plane_origin"] = tuple(float(value) for value in np.asarray(cursor_world, dtype=float).reshape(-1)[:3])
                state["drag_anchor_world"] = tuple(float(value) for value in np.asarray(cursor_world, dtype=float).reshape(-1)[:3])
                state["attach_to_cursor_on_next_motion"] = False
                return
        self._apply_step_carry_plane_motion_state(state, current_xy)

    def _placement_drag_display_direction(self, kind: str, axis: str, signed_step: float, actor) -> np.ndarray:
        sign = 1.0 if float(signed_step) >= 0.0 else -1.0
        try:
            origin = np.asarray(actor.GetCenter(), dtype=float).reshape(-1)[:3]
        except Exception:
            origin = None
        if origin is None or origin.size < 3 or not np.all(np.isfinite(origin[:3])):
            origin = self._scene_bounds()[0]
        if str(kind) == "rotate":
            basis = self._scene_placement_rotation_basis(axis)
            world_direction = basis[1] * sign if basis is not None else self._placement_axis_vector(axis) * sign
        else:
            world_direction = self._placement_axis_vector(axis) * sign
        start = self._world_to_display_2d(origin)
        end = self._world_to_display_2d(np.asarray(origin, dtype=float) + np.asarray(world_direction, dtype=float))
        if start is not None and end is not None:
            direction = np.asarray(end, dtype=float) - np.asarray(start, dtype=float)
            norm = float(np.linalg.norm(direction))
            if np.isfinite(norm) and norm > 1e-6:
                return direction / norm
        fallbacks = {
            "x": np.asarray((1.0, 0.0), dtype=float),
            "y": np.asarray((0.0, 1.0), dtype=float),
            "z": np.asarray((1.0, 1.0), dtype=float),
        }
        fallback = fallbacks.get(str(axis or "").strip().lower(), np.asarray((1.0, 0.0), dtype=float))
        fallback = fallback * sign
        norm = float(np.linalg.norm(fallback))
        return fallback / norm if norm > 1e-12 else np.asarray((1.0, 0.0), dtype=float)

    @staticmethod
    def _placement_drag_pixels_per_step() -> float:
        return 18.0

    def _step_carry_grid_mode(self) -> str:
        return STEP_CARRY_GRID_FREE

    def _step_carry_snap_enabled(self) -> bool:
        return False

    def _step_carry_spacing_from_mode(self, auto_spacing: float) -> float:
        return self.editor._open3d_step_state_service().carry_spacing_from_auto(auto_spacing)

    def _on_step_carry_grid_selected(self, *_args) -> None:
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        label = self._step_carry_label()
        if label is None:
            self.status_var.set("STEP carry uses free drag movement.")
            return
        self.refresh_from_editor()
        self.status_var.set(f"Carry {label.upper()} STEP: free movement; hold-drag STEP to move.")

    def _translate_step_overlay_actors(self, label: str, delta_xyz) -> int:
        label = str(label).strip().lower()
        try:
            delta = np.asarray(delta_xyz, dtype=float).reshape(-1)[:3]
        except Exception:
            return 0
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])):
            return 0
        actor_keys = list(dict.fromkeys(self._step_follow_actor_map.get(label, []) or []))
        moved = 0
        for actor_key in actor_keys:
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            try:
                actor.AddPosition(float(delta[0]), float(delta[1]), float(delta[2]))
                moved += 1
            except Exception as exc:
                self.editor.append_debug(f"3D STEP carry actor move failed for {label}: {exc}")
        if moved:
            # bugs/0050: the cached face hover outline is baked at the body's
            # pre-move pose; once the body slides out from under it, that gold
            # edge highlight is stranded at the old location. Drop it on the
            # move (the next hover re-derives it from the now-current metadata).
            if self._hover_step_outline_actor is not None or self._hover_step_cell_key is not None:
                self._set_step_hover_outline(None, None, render=False)
            try:
                self._reset_camera_clipping_range_for_scene()
            except Exception:
                pass
            self.render()
        return moved

    def _remove_step_overlay_actors(self, label: str) -> int:
        return self._open3d_step_overlay_refresh_service()._remove_step_overlay_actors(label)

    def refresh_imported_step_overlay(self, label: str, *, render: bool = True) -> bool:
        return self._open3d_step_overlay_refresh_service().refresh_imported_step_overlay(label, render=render)

    def _new_step_carry_motion_state(self, label: str) -> dict[str, object] | None:
        axes = self._camera_screen_world_axes()
        if axes is None:
            return None
        spacing = self._step_carry_grid_spacing(label)
        return self.editor._open3d_step_state_service().carry_motion_state(
            label,
            screen_axes=axes,
            spacing=spacing,
        )

    def _step_carry_label(self) -> str | None:
        label = self.editor._open3d_step_state_service().resolve_active_carry_label(
            self._step_carry_active_label,
        )
        return label or None

    def _step_carry_grid_spacing(self, label: str, mesh=None) -> float:
        label = str(label).strip().lower()
        if mesh is None and self._step_carry_grid_label == label:
            try:
                stored = float(self._step_carry_grid_spacing_mm or 0.0)
                if np.isfinite(stored) and stored > 0.0:
                    return stored
            except Exception:
                pass
        _center, scene_span = self._scene_bounds()
        step_extent = 0.0
        if mesh is not None:
            try:
                bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
                if bounds.size == 6 and np.all(np.isfinite(bounds)) and bounds[0] <= bounds[1]:
                    step_extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 0.0)
            except Exception:
                step_extent = 0.0
        return self.editor._open3d_step_state_service().carry_spacing_for_scene(
            scene_span=float(scene_span),
            step_extent=float(step_extent),
        )

    @staticmethod
    def _polyline_point_and_along(points: np.ndarray, target: np.ndarray) -> dict[str, object] | None:
        pts = np.asarray(points, dtype=float)
        tgt = np.asarray(target, dtype=float).reshape(-1)[:3]
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3 or tgt.size < 3:
            return None
        if not (np.all(np.isfinite(pts[:, :3])) and np.all(np.isfinite(tgt[:3]))):
            return None
        best: dict[str, object] | None = None
        along_before = 0.0
        for start, end in zip(pts[:-1, :3], pts[1:, :3], strict=False):
            segment = np.asarray(end - start, dtype=float)
            length = float(np.linalg.norm(segment))
            if not np.isfinite(length) or length <= 1e-12:
                continue
            fraction = float(np.dot(tgt[:3] - start, segment) / (length * length))
            fraction = min(max(fraction, 0.0), 1.0)
            point = np.asarray(start + segment * fraction, dtype=float)
            distance = float(np.linalg.norm(tgt[:3] - point[:3]))
            if best is None or distance < float(best["distance"]):
                best = {
                    "point": point,
                    "direction": segment / length,
                    "along": float(along_before + fraction * length),
                    "distance": distance,
                    "points": pts[:, :3],
                }
            along_before += length
        return best

    @staticmethod
    def _polyline_point_at_along(points: np.ndarray, along: float) -> np.ndarray | None:
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3 or not np.all(np.isfinite(pts[:, :3])):
            return None
        remaining = max(float(along), 0.0)
        last = np.asarray(pts[0, :3], dtype=float)
        for start, end in zip(pts[:-1, :3], pts[1:, :3], strict=False):
            segment = np.asarray(end - start, dtype=float)
            length = float(np.linalg.norm(segment))
            if not np.isfinite(length) or length <= 1e-12:
                continue
            if remaining <= length:
                return np.asarray(start + segment * (remaining / length), dtype=float)
            remaining -= length
            last = np.asarray(end, dtype=float)
        return last

    def _step_carry_ray_capture_radius(self, spacing: float) -> float:
        _scene_center, scene_span = self._scene_bounds()
        return max(float(spacing) * 4.0, float(scene_span) * 0.035, 1.0)

    @staticmethod
    def _step_carry_ray_record_from_points(ray_index: int, points) -> dict[str, object] | None:
        try:
            pts = np.asarray(points, dtype=float)
        except Exception:
            return None
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            return None
        pts = np.asarray(pts[:, :3], dtype=float)
        if not np.all(np.isfinite(pts)):
            return None
        starts = pts[:-1]
        ends = pts[1:]
        segments = ends - starts
        lengths = np.linalg.norm(segments, axis=1)
        valid = np.isfinite(lengths) & (lengths > 1e-12)
        if not np.any(valid):
            return None
        starts = starts[valid]
        segments = segments[valid]
        lengths = lengths[valid]
        along_starts = np.concatenate(([0.0], np.cumsum(lengths[:-1])))
        bbox_min = np.min(pts, axis=0)
        bbox_max = np.max(pts, axis=0)
        return {
            "ray_index": int(ray_index),
            "points": pts,
            "segment_starts": starts,
            "segment_vectors": segments,
            "segment_lengths": lengths,
            "segment_inv_length_sq": 1.0 / np.maximum(lengths * lengths, 1e-24),
            "segment_along_starts": along_starts,
            "bbox_min": bbox_min,
            "bbox_max": bbox_max,
        }

    def _step_carry_selected_ray_index(self) -> int | None:
        try:
            if self._picked_ray_index is not None:
                return int(self._picked_ray_index)
        except Exception:
            pass
        try:
            selected = self.editor._selected_ray_index_from_ui()
            return int(selected) if selected is not None else None
        except Exception:
            return None

    def _step_carry_ray_constraint_records(
        self,
        preferred_ray_index: int | None = None,
    ) -> list[dict[str, object]]:
        try:
            records = self.editor._iter_3d_scene_ray_records(
                getattr(self.editor, "last_rays", None),
                getattr(self.editor, "_last_scene_bundle", None),
            )
        except Exception:
            records = []
        cached: list[dict[str, object]] = []
        preferred = int(preferred_ray_index) if preferred_ray_index is not None else None
        for ray_index, _color, points, _terminal_status in records:
            try:
                index = int(ray_index)
            except Exception:
                continue
            if preferred is not None and index != preferred:
                continue
            record = self._step_carry_ray_record_from_points(index, points)
            if record is not None:
                cached.append(record)
        return cached

    @staticmethod
    def _step_carry_bbox_distance(target: np.ndarray, record: dict[str, object]) -> float:
        try:
            lower = np.asarray(record.get("bbox_min"), dtype=float).reshape(-1)[:3]
            upper = np.asarray(record.get("bbox_max"), dtype=float).reshape(-1)[:3]
        except Exception:
            return 0.0
        if lower.size < 3 or upper.size < 3 or not (np.all(np.isfinite(lower)) and np.all(np.isfinite(upper))):
            return 0.0
        outside = np.maximum(np.maximum(lower[:3] - target[:3], target[:3] - upper[:3]), 0.0)
        return float(np.linalg.norm(outside))

    @staticmethod
    def _step_carry_cached_polyline_hit(
        record: dict[str, object],
        target: np.ndarray,
    ) -> dict[str, object] | None:
        try:
            starts = np.asarray(record.get("segment_starts"), dtype=float)
            segments = np.asarray(record.get("segment_vectors"), dtype=float)
            lengths = np.asarray(record.get("segment_lengths"), dtype=float)
            inv_length_sq = np.asarray(record.get("segment_inv_length_sq"), dtype=float)
            along_starts = np.asarray(record.get("segment_along_starts"), dtype=float)
            points = np.asarray(record.get("points"), dtype=float)
        except Exception:
            return None
        if (
            starts.ndim != 2
            or segments.ndim != 2
            or starts.shape != segments.shape
            or starts.shape[0] == 0
            or starts.shape[1] < 3
            or lengths.shape[0] != starts.shape[0]
            or inv_length_sq.shape[0] != starts.shape[0]
            or along_starts.shape[0] != starts.shape[0]
            or points.ndim != 2
            or points.shape[0] < 2
        ):
            return None
        fractions = np.einsum("ij,ij->i", target[:3] - starts[:, :3], segments[:, :3]) * inv_length_sq
        fractions = np.clip(fractions, 0.0, 1.0)
        candidates = starts[:, :3] + segments[:, :3] * fractions[:, None]
        deltas = candidates - target[:3]
        distances_sq = np.einsum("ij,ij->i", deltas, deltas)
        if distances_sq.size == 0 or not np.any(np.isfinite(distances_sq)):
            return None
        segment_index = int(np.nanargmin(distances_sq))
        length = float(lengths[segment_index])
        if not np.isfinite(length) or length <= 1e-12:
            return None
        fraction = float(fractions[segment_index])
        segment = np.asarray(segments[segment_index, :3], dtype=float)
        return {
            "point": np.asarray(candidates[segment_index, :3], dtype=float),
            "direction": segment / length,
            "along": float(along_starts[segment_index] + fraction * length),
            "distance": float(np.sqrt(max(float(distances_sq[segment_index]), 0.0))),
            "points": points[:, :3],
            "ray_index": int(record.get("ray_index", -1)),
        }

    def _nearest_step_carry_ray_constraint(
        self,
        point,
        *,
        preferred_ray_index: int | None = None,
        records: list[dict[str, object]] | None = None,
        max_distance: float | None = None,
    ) -> dict[str, object] | None:
        try:
            target = np.asarray(point, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if target.size < 3 or not np.all(np.isfinite(target[:3])):
            return None
        if records is None:
            records = self._step_carry_ray_constraint_records(preferred_ray_index)
        try:
            distance_limit = float(max_distance) if max_distance is not None else None
        except Exception:
            distance_limit = None
        best: dict[str, object] | None = None
        for record in records:
            try:
                index = int(record.get("ray_index", -1))
            except Exception:
                continue
            if preferred_ray_index is not None and index != int(preferred_ray_index):
                continue
            if distance_limit is not None and self._step_carry_bbox_distance(target[:3], record) > distance_limit:
                continue
            hit = self._step_carry_cached_polyline_hit(record, target[:3])
            if hit is None:
                continue
            if distance_limit is not None and float(hit.get("distance", float("inf"))) > distance_limit:
                continue
            if best is None or float(hit["distance"]) < float(best["distance"]):
                best = hit
        return best

    def _step_carry_ray_records_for_state(
        self,
        state: dict[str, object],
        preferred_ray_index: int | None,
    ) -> list[dict[str, object]]:
        records = state.get("ray_constraint_records")
        preferred = int(preferred_ray_index) if preferred_ray_index is not None else None
        cached_preferred = state.get("ray_constraint_preferred_index")
        try:
            cached_preferred = int(cached_preferred) if cached_preferred is not None else None
        except Exception:
            cached_preferred = None
        if isinstance(records, list) and cached_preferred == preferred:
            return records
        records = self._step_carry_ray_constraint_records(preferred_ray_index=preferred)
        state["ray_constraint_records"] = records
        state["ray_constraint_preferred_index"] = preferred
        return records

    def _step_carry_ray_target(self, state: dict[str, object], candidate_center: np.ndarray) -> dict[str, object] | None:
        try:
            spacing = float(state.get("spacing", 0.0))
        except Exception:
            spacing = 0.0
        preferred_ray = None
        try:
            if state.get("ray_constraint_index") is not None:
                preferred_ray = int(state["ray_constraint_index"])
            elif self._picked_ray_index is not None:
                preferred_ray = int(self._picked_ray_index)
        except Exception:
            preferred_ray = None
        if preferred_ray is None:
            preferred_ray = self._step_carry_selected_ray_index()
        records = self._step_carry_ray_records_for_state(state, preferred_ray)
        capture_radius = self._step_carry_ray_capture_radius(spacing)
        hit = self._nearest_step_carry_ray_constraint(
            candidate_center,
            preferred_ray_index=preferred_ray,
            records=records,
            max_distance=None if preferred_ray is not None else capture_radius,
        )
        if hit is None and preferred_ray is None:
            return None
        if hit is None:
            return None
        ray_index = int(hit["ray_index"])
        if state.get("ray_constraint_index") != ray_index:
            try:
                start_center = np.asarray(state.get("start_center_world"), dtype=float).reshape(-1)[:3]
                anchor = self._polyline_point_and_along(np.asarray(hit["points"], dtype=float), start_center[:3])
                anchor_along = float(anchor["along"]) if anchor is not None else float(hit["along"])
            except Exception:
                anchor_along = float(hit["along"])
            state["ray_constraint_index"] = ray_index
            state["ray_anchor_along"] = float(anchor_along)
            captured_records = [record for record in records if int(record.get("ray_index", -1)) == ray_index]
            if captured_records:
                state["ray_constraint_records"] = captured_records
                state["ray_constraint_preferred_index"] = ray_index
        anchor_along = float(state.get("ray_anchor_along", hit["along"]))
        raw_along_delta = float(hit["along"]) - anchor_along
        if np.isfinite(spacing) and spacing > 1e-12:
            along_delta = float(np.round(raw_along_delta / spacing) * spacing)
        else:
            along_delta = raw_along_delta
        target = self._polyline_point_at_along(np.asarray(hit["points"], dtype=float), anchor_along + along_delta)
        if target is None:
            return None
        return {
            "target": np.asarray(target, dtype=float),
            "ray_index": ray_index,
            "distance": float(hit["distance"]),
            "along_delta": float(along_delta),
        }

    def _step_carry_grid_extent(self, mesh=None) -> float:
        _center, scene_span = self._scene_bounds()
        step_extent = 0.0
        if mesh is not None:
            try:
                bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
                if bounds.size == 6 and np.all(np.isfinite(bounds)) and bounds[0] <= bounds[1]:
                    step_extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 0.0)
            except Exception:
                step_extent = 0.0
        return max(float(scene_span) * 1.15, float(step_extent) * 4.0, 20.0)

    def _camera_screen_world_axes(self) -> tuple[np.ndarray, np.ndarray] | None:
        if self._renderer is None:
            return None
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return None
        try:
            position = np.asarray(camera.GetPosition(), dtype=float)
            focal = np.asarray(camera.GetFocalPoint(), dtype=float)
            up = np.asarray(camera.GetViewUp(), dtype=float)
            view = focal - position
            view /= max(float(np.linalg.norm(view)), 1e-12)
            up = up - view * float(np.dot(up, view))
            up /= max(float(np.linalg.norm(up)), 1e-12)
            right = np.cross(view, up)
            right /= max(float(np.linalg.norm(right)), 1e-12)
            return right, up
        except Exception:
            return None

    @staticmethod
    def _step_carry_pixels_per_grid_step() -> float:
        return 22.0

    def _apply_step_carry_motion_delta(self, state: dict[str, object], movement) -> int | None:
        if movement is None:
            return None
        if getattr(movement, "debug_message", ""):
            self.editor.append_debug(str(movement.debug_message))
        try:
            applied_steps = int(getattr(movement, "applied_steps", 0))
        except Exception:
            applied_steps = 0
        if not getattr(movement, "has_delta", False):
            return applied_steps
        label = str(getattr(movement, "label", "") or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return applied_steps
        try:
            delta = np.asarray(getattr(movement, "delta_xyz"), dtype=float).reshape(-1)[:3]
        except Exception:
            return applied_steps
        if delta.size < 3 or not np.all(np.isfinite(delta[:3])) or not np.any(np.abs(delta[:3]) > 1e-12):
            return applied_steps
        if not bool(state.get("history_started", False)):
            try:
                self.editor._begin_history_capture()
                state["history_started"] = True
            except Exception:
                pass
        grid_spacing = getattr(movement, "grid_spacing_mm", None)
        self.editor.translate_step_overlay(
            label,
            delta,
            grid_spacing_mm=grid_spacing,
            refresh=False,
            record_history=False,
        )
        if self._translate_step_overlay_actors(label, delta) <= 0:
            self.refresh_from_editor(force_retrace=bool(getattr(movement, "force_refresh", False)))
        self._open3d_carry_grip_service.update_after_delta(state, delta)
        live_message = str(getattr(movement, "live_refresh_message", "") or "")
        if live_message:
            self.schedule_live_refresh(live_message)
        return applied_steps

    def _apply_step_carry_motion_state(self, state: dict[str, object] | None, dx: int | float, dy: int | float) -> int:
        if state is None:
            return 0
        movement = self.editor._open3d_step_state_service().carry_pixel_motion_delta(
            state,
            dx=dx,
            dy=dy,
            pixels_per_step=self._step_carry_pixels_per_grid_step(),
        )
        applied = self._apply_step_carry_motion_delta(state, movement)
        return int(applied or 0)

    def _apply_step_carry_plane_motion_state(self, state: dict[str, object] | None, current_xy) -> int | None:
        if state is None or current_xy is None:
            return None
        try:
            plane_origin = np.asarray(state.get("drag_plane_origin"), dtype=float).reshape(-1)[:3]
            plane_normal = np.asarray(state.get("drag_plane_normal"), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if plane_origin.size < 3 or plane_normal.size < 3:
            return None
        cursor_world = self._cursor_plane_point(current_xy, plane_origin[:3], plane_normal[:3])
        if cursor_world is None:
            return None
        _scene_center, scene_span = self._scene_bounds()
        movement = self.editor._open3d_step_state_service().carry_plane_motion_delta(
            state,
            cursor_world=cursor_world,
            scene_span=float(scene_span),
        )
        return self._apply_step_carry_motion_delta(state, movement)

    def _apply_step_carry_drag_motion(
        self,
        dx: int | float,
        dy: int | float,
        *,
        current_xy: tuple[int, int] | None = None,
    ) -> None:
        state = self._step_carry_drag_state
        if current_xy is not None:
            applied = self._apply_step_carry_plane_motion_state(state, current_xy)
            if applied is not None:
                return
        self._apply_step_carry_motion_state(state, dx, dy)

    def _finish_step_carry_drag(self, state: dict[str, object]) -> None:
        transition = self.editor._open3d_step_state_service().carry_finish_transition(state)
        if transition is None:
            return
        try:
            self.editor._commit_history_capture()
        except Exception:
            pass
        self._step_carry_active_label = None
        self._set_step_carry_cursor(False)
        self._open3d_carry_grip_service.clear(render=False)
        self._update_mode_badge()
        if transition.moved:
            try:
                physics_requested = self.editor._open3d_trace_refresh_service().inspector_physics_requested(self)
                self.refresh_from_editor(force_retrace=physics_requested)
            except Exception as exc:
                self.editor.append_debug(f"STEP carry final refresh failed: {exc}")
            if transition.live_refresh_message:
                self.schedule_live_refresh(transition.live_refresh_message, delay_ms=0)
        self.status_var.set(transition.status)

    def _apply_placement_drag_motion(self, dx: int | float, dy: int | float) -> None:
        state = self._placement_drag_state
        if state is None:
            return
        try:
            # Tk event Y grows downward, while VTK display coordinates grow upward.
            cursor_delta = np.asarray((float(dx), -float(dy)), dtype=float)
            direction = np.asarray(state.get("display_direction"), dtype=float).reshape(-1)[:2]
            signed_pixels = float(np.dot(cursor_delta, direction))
        except Exception:
            return
        if not np.isfinite(signed_pixels) or abs(signed_pixels) <= 1e-12:
            return
        pixels_per_step = self._placement_drag_pixels_per_step()
        accumulator = float(state.get("pixel_accumulator", 0.0)) + signed_pixels
        steps = int(accumulator / pixels_per_step)
        if steps == 0:
            state["pixel_accumulator"] = accumulator
            return
        state["pixel_accumulator"] = accumulator - float(steps) * pixels_per_step
        state["applied_steps"] = int(state.get("applied_steps", 0)) + abs(int(steps))
        row_index = int(state.get("row_index", -1))
        axis = str(state.get("axis", ""))
        delta = float(steps) * float(state.get("signed_step", 0.0))
        if str(state.get("kind")) == "rotate":
            self._apply_scene_placement_rotate_handle(row_index, axis, delta)
        else:
            # bugs/0012 (+ 20:37/20:38 follow-ups): a promoted optical-solid row
            # forces a full optical retrace on every refresh (~0.5 s), and even a
            # bare model commit (translate_scene_row_pose -> _sync_table) costs
            # ~0.3 s, so doing either per drag step made the axial slide "compute
            # hard but never move". Move the body AND its Move/Rotate handles
            # together with a cheap actor transform (AddPosition, no retrace,
            # ~5 ms) so the lens and its gizmo track the cursor, and defer the
            # single model commit + heavy refresh to _finish_placement_drag.
            axis_unit = self._placement_axis_vector(axis)
            self._translate_placement_handle_actors(row_index, axis_unit * float(delta))
            self._translate_row_actors(row_index, axis_unit * float(delta))
            state["pending_translate_mm"] = float(state.get("pending_translate_mm", 0.0)) + float(delta)
            # Live leading-gap readout for the gizmo slide, matching the
            # imported-STEP drag and axis-slide mode (flag_20260604_111615_630).
            self._update_placement_drag_gap_overlay(state)
            # bugs/0024: with Live Mode ON, also drive a debounced live retrace so
            # the rays react to the element as it is dragged. The body still
            # tracks the cursor smoothly via the cheap actor transform above; the
            # ~180 ms debounce coalesces the heavier trace, and
            # _refresh_live_preview_scene flushes this pending offset into the
            # model first so the trace reflects the dragged pose. Live Mode OFF
            # keeps the bug-0012 deferred behaviour (trace only on release).
            if self._live_mode_enabled():
                # Sparse fan during the drag so the live trace is snappy; the
                # full-fidelity bundle is restored by _finish_placement_drag on
                # release (which clears this override).
                self.editor._drag_preview_ray_count_override = 3
                self.schedule_live_refresh("placement drag")

    def _finish_placement_drag(self, state: dict[str, object]) -> None:
        # bugs/0024: the drag preview traced a sparse fan; clear the override so
        # the on-release commit retraces the full-fidelity bundle.
        try:
            self.editor._drag_preview_ray_count_override = None
        except Exception:
            pass
        try:
            applied_steps = int(state.get("applied_steps", 0))
            row_index = int(state.get("row_index", -1))
            kind = "rotation" if str(state.get("kind")) == "rotate" else "translation"
            axis = str(state.get("axis", "")).upper()
        except Exception:
            return
        # Drop the transient live-gap overlay drawn during the slide. render=True
        # is self-gating (renders only if gap actors existed), so a drag that
        # nets to zero -- no commit, hence no refresh-render below -- still can't
        # leave a ghost arrow behind.
        self._clear_step_translate_drag_overlay(render=True)
        # bugs/0012: the drag only moved the body + handles via a cheap actor
        # transform (no model change). Commit the accumulated slide once here --
        # a single model update + the one heavy promoted-solid retrace -- which
        # rebuilds the body and handles from the committed pose so the new
        # position sticks (no revert on release).
        pending = float(state.get("pending_translate_mm", 0.0))
        if str(state.get("kind")) != "rotate" and abs(pending) > 1.0e-9:
            try:
                self._apply_scene_placement_translate_handle(
                    row_index, str(state.get("axis", "")).strip().lower(), pending
                )
            except Exception as exc:
                self.editor.append_debug(f"Placement translate commit failed for S{row_index}: {exc}")
        if applied_steps <= 0:
            self.status_var.set(f"Placement {kind} drag S{row_index} {axis}: no snap step crossed.")
        else:
            self.status_var.set(f"Placement {kind} drag S{row_index} {axis}: applied {applied_steps} snap step(s).")

    def _step_translate_state_from_current_pick(self) -> dict[str, object] | None:
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        if (
            self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or self._dimension_anchor_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        ):
            return None
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
        except Exception:
            return None
        actor_key = self._actor_key(actor) if actor is not None else None
        if actor_key is None:
            return None
        info = self._actor_step_translate_map.get(actor_key)
        if info is None:
            return None
        label, axis, _step_mm = info
        label = str(label).strip().lower()
        axis = str(axis).strip().lower()
        if self.editor._step_path_for_label(label) is None:
            return None
        # Project a 1 mm world-axis step to the screen once at press (the camera
        # is fixed for the drag): the unit screen direction plus pixels-per-mm
        # let the body track the cursor 1:1 along the axis.
        try:
            origin = np.asarray(actor.GetCenter(), dtype=float).reshape(-1)[:3]
        except Exception:
            origin = None
        if origin is None or origin.size < 3 or not np.all(np.isfinite(origin[:3])):
            origin = self._scene_bounds()[0]
        axis_unit = self._placement_axis_vector(axis)
        start2d = self._world_to_display_2d(np.asarray(origin, dtype=float))
        end2d = self._world_to_display_2d(np.asarray(origin, dtype=float) + axis_unit)
        pixels_per_mm = 0.0
        unit_dir = None
        if start2d is not None and end2d is not None:
            diff = np.asarray(end2d, dtype=float) - np.asarray(start2d, dtype=float)
            norm = float(np.linalg.norm(diff))
            if np.isfinite(norm) and norm > 1e-6:
                pixels_per_mm = norm
                unit_dir = diff / norm
        if unit_dir is None:
            unit_dir = self._placement_drag_display_direction("translate", axis, 1.0, actor)
            pixels_per_mm = float(self._placement_drag_pixels_per_step())
        self._step_rotation_active_label = label
        display = self.editor._step_overlay_display_label(label).upper()
        self.status_var.set(
            f"Drag {display} STEP along {axis.upper()} to move freely; release to commit."
        )
        return {
            "label": label,
            "axis": axis,
            "axis_unit": np.asarray(axis_unit, dtype=float),
            "display_direction": np.asarray(unit_dir, dtype=float),
            "pixels_per_mm": float(pixels_per_mm),
            "applied_delta_mm": 0.0,
        }

    def _apply_step_translate_drag_motion(self, dx: int | float, dy: int | float) -> None:
        state = self._step_translate_drag_state
        if state is None:
            return
        try:
            cursor_delta = np.asarray((float(dx), -float(dy)), dtype=float)
            direction = np.asarray(state.get("display_direction"), dtype=float).reshape(-1)[:2]
            signed_pixels = float(np.dot(cursor_delta, direction))
        except Exception:
            return
        if not np.isfinite(signed_pixels) or abs(signed_pixels) <= 1.0e-9:
            return
        pixels_per_mm = float(state.get("pixels_per_mm", 0.0))
        if not np.isfinite(pixels_per_mm) or pixels_per_mm <= 1.0e-9:
            return
        mm_inc = signed_pixels / pixels_per_mm
        if not np.isfinite(mm_inc) or abs(mm_inc) <= 1.0e-9:
            return
        axis_unit = np.asarray(state.get("axis_unit"), dtype=float).reshape(-1)[:3]
        delta_xyz = axis_unit * float(mm_inc)
        if self._translate_step_overlay_actors(str(state.get("label", "")), delta_xyz) <= 0:
            return
        state["applied_delta_mm"] = float(state.get("applied_delta_mm", 0.0)) + float(mm_inc)
        self._update_step_translate_drag_overlay(state)

    def _finish_step_translate_drag(self, state: dict[str, object]) -> None:
        label = str(state.get("label", "")).strip().lower()
        axis = str(state.get("axis", "")).strip().lower()
        total_mm = float(state.get("applied_delta_mm", 0.0))
        self._clear_step_translate_drag_overlay()
        display = self.editor._step_overlay_display_label(label).upper() if label else "STEP"
        if not label or abs(total_mm) <= 1.0e-9:
            self.status_var.set(f"{display} STEP move: no movement applied.")
            if label:
                try:
                    self.refresh_imported_step_overlay(label)
                except Exception:
                    pass
            return
        axis_unit = np.asarray(state.get("axis_unit"), dtype=float).reshape(-1)[:3]
        delta_xyz = axis_unit * total_mm
        try:
            physics_requested = bool(
                self.editor._open3d_trace_refresh_service().inspector_physics_requested(self)
            )
        except Exception:
            physics_requested = True
        try:
            self.editor.translate_step_overlay(
                label,
                (float(delta_xyz[0]), float(delta_xyz[1]), float(delta_xyz[2])),
                refresh=physics_requested,
                record_history=True,
            )
        except Exception as exc:
            self.editor.append_debug(f"STEP translate commit failed for {label}: {exc}")
            return
        if not physics_requested:
            # bugs/0011: the persistent thickness dimensions span every
            # component (Object/Image rows plus any imported body), so the
            # per-label partial overlay refresh moves the body but leaves the
            # "gap = .. mm" arrows anchored at the body's pre-move position --
            # the live drag readout was correct, only the committed overlay
            # went stale. When the dimensions are shown, do a full refresh so
            # they recompute at the new position; keep the fast per-label path
            # when they're hidden.
            dims_shown = False
            try:
                dims_shown = bool(self.editor.show_physical_distances_var.get())
            except Exception:
                dims_shown = False
            refreshed = False
            if not dims_shown:
                try:
                    refreshed = bool(self.refresh_imported_step_overlay(label))
                except Exception as exc:
                    self.editor.append_debug(f"STEP translate partial refresh failed for {label}: {exc}")
            if not refreshed:
                try:
                    self.refresh_from_editor(force_retrace=False)
                except Exception as exc:
                    self.editor.append_debug(f"STEP translate fallback refresh failed for {label}: {exc}")
        self.status_var.set(f"{display} STEP moved {axis.upper()} {total_mm:+.4g} mm.")

    # ------------------------------------------------------------------
    # bugs/0053: re-anchor a thickness/distance dimension endpoint onto a
    # surface/edge to re-anchor what it measures to. MEASUREMENT only -- the
    # optical model (rows[i].thickness) is never changed. The interaction is a
    # modal click-toggle: Ctrl-click a dimension arrow to start (the nearer
    # endpoint then follows the BARE mouse, no button held); a plain click on a
    # surface/edge commits. The object/LED row's object-side endpoint feeds the
    # existing object-edge reference instead.
    def _dimension_anchor_state_from_current_pick(self) -> dict[str, object] | None:
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
            actor_key = self._actor_key(actor)
        except Exception:
            return None
        if actor_key is None:
            return None
        record = self._thickness_dimension_drag_map.get(actor_key)
        if not isinstance(record, dict):
            return None
        try:
            row_index = int(record.get("row_index", -1))
            start = np.asarray(record.get("start"), dtype=float).reshape(-1)[:3]
            end = np.asarray(record.get("end"), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if row_index < 0 or start.size < 3 or end.size < 3:
            return None
        if not (np.all(np.isfinite(start)) and np.all(np.isfinite(end))):
            return None
        # Choose the endpoint nearer the cursor in display space.
        start_2d = self._world_to_display_2d(start)
        end_2d = self._world_to_display_2d(end)
        cursor = np.asarray((float(x), float(y)), dtype=float)
        endpoint = "start"
        if start_2d is not None and end_2d is not None:
            d_start = float(np.linalg.norm(np.asarray(start_2d, dtype=float)[:2] - cursor))
            d_end = float(np.linalg.norm(np.asarray(end_2d, dtype=float)[:2] - cursor))
            endpoint = "start" if d_start <= d_end else "end"
        moving = start if endpoint == "start" else end
        fixed = end if endpoint == "start" else start
        return {
            "row_index": row_index,
            "endpoint": endpoint,
            "fixed_world": tuple(float(v) for v in fixed[:3]),
            "moving_world": tuple(float(v) for v in moving[:3]),
            "snapped_world": None,
        }

    def _dimension_anchor_display_label(self, row_index: int) -> str:
        if row_index == 0 and getattr(self.editor, "imported_led_step_path", None) is not None:
            try:
                return self.editor._step_overlay_display_label("led").upper()
            except Exception:
                return "LED"
        return f"S{int(row_index)}"

    def _begin_dimension_anchor_pick_from_current_pick(self) -> bool:
        """Enter the modal re-anchor on a Ctrl-click that landed on a dimension
        arrow. Returns True if a dimension endpoint was picked (so the caller
        suppresses camera orbit), False otherwise (Ctrl-click on empty -> orbit)."""
        state = self._dimension_anchor_state_from_current_pick()
        if state is None:
            return False
        self._dimension_anchor_pick_mode = True
        self._dimension_anchor_pick_state = state
        label = self._dimension_anchor_display_label(int(state.get("row_index", -1)))
        endpoint = str(state.get("endpoint", "end"))
        self.status_var.set(
            f"Re-anchor {label} dimension ({endpoint}): move the mouse onto a surface/edge "
            f"(no button held), then click to set the measured location. Esc cancels."
        )
        try:
            self._set_axis_pick_cursor(True)
        except Exception:
            pass
        # Draw the live arrow immediately at the current pose so the user sees the
        # real measured dimension move (not a separate bare line).
        self._apply_dimension_anchor_pick_motion()
        try:
            self._update_mode_badge()
        except Exception:
            pass
        return True

    def _apply_dimension_anchor_pick_motion(self) -> None:
        """Bare-mouse live update while re-anchoring: snap the moving endpoint to
        the surface/edge under the cursor, redraw the real dimension arrow, and
        highlight the snap target."""
        state = self._dimension_anchor_pick_state
        if state is None or self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return
        try:
            x, y = self._vtk_interactor.GetEventPosition()
        except Exception:
            return
        fixed = np.asarray(state.get("fixed_world"), dtype=float).reshape(-1)[:3]
        moving = np.asarray(state.get("moving_world"), dtype=float).reshape(-1)[:3]
        snapped = None
        snapped_label = ""
        hit_key = None
        # Snap to whatever pickable surface/body sits under the cursor; ignore the
        # dimension arrows/gizmo handles + the live preview themselves.
        try:
            self._picker.Pick(x, y, 0.0, self._renderer)
            hit = self._picker.GetActor()
            hit_key = self._actor_key(hit)
            ignore = (
                hit_key is not None
                and (
                    hit_key in self._actor_thickness_dimension_map
                    or hit_key in self._actor_step_rotate_map
                    or hit_key in self._actor_step_translate_map
                )
            )
            if hit is not None and not ignore:
                pos = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
                if pos.size >= 3 and np.all(np.isfinite(pos)):
                    snapped = pos
                    step_label = self._actor_step_map.get(hit_key) if hit_key is not None else None
                    snapped_label = str(step_label).upper() if step_label else ""
            else:
                hit_key = None
        except Exception:
            snapped = None
            hit_key = None
        if snapped is None:
            # No surface under the cursor: project the cursor ray onto the
            # dimension's axial line through the moving endpoint (axis runs along Z).
            ray = self._display_pick_ray((x, y))
            if ray is not None:
                origin, direction = ray
                direction = np.asarray(direction, dtype=float).reshape(-1)[:3]
                if abs(float(direction[2])) > 1e-9:
                    t = (float(moving[2]) - float(origin[2])) / float(direction[2])
                    pt = np.asarray(origin, dtype=float).reshape(-1)[:3] + t * direction
                    snapped = np.array([float(moving[0]), float(moving[1]), float(pt[2])], dtype=float)
        if snapped is None:
            return
        # Keep the arrow on the optical axis (matching the committed overlay): only
        # the snapped Z moves the moving endpoint; X/Y stay on the axis.
        moving_q = np.array([float(moving[0]), float(moving[1]), float(snapped[2])], dtype=float)
        state["snapped_world"] = tuple(float(v) for v in snapped[:3])
        state["moving_axial_world"] = tuple(float(v) for v in moving_q[:3])
        measured = abs(float(snapped[2] - fixed[2]))
        state["measured_mm"] = float(measured)
        self._update_dimension_anchor_preview(int(state.get("row_index", -1)), fixed, moving_q)
        self._set_dimension_anchor_snap_highlight(hit_key, x, y)
        label = self._dimension_anchor_display_label(int(state.get("row_index", -1)))
        suffix = f" -> {snapped_label}" if snapped_label else ""
        self.status_var.set(f"{label} measured = {measured:.6g} mm{suffix} (click a surface/edge to set).")

    def _update_dimension_anchor_preview(self, row_index, fixed_world, moving_world) -> None:
        """Live preview that looks like the COMMITTED magenta dimension: a real
        double-headed arrow (with arrowheads), leader lines, and a measured
        label, offset off the optical axis exactly like the persistent overlay."""
        self._clear_dimension_anchor_preview(render=False)
        svc = self._open3d_thickness_dimension_service()
        if svc is None or pv is None or self._renderer is None:
            return
        try:
            q0 = np.asarray(fixed_world, dtype=float).reshape(-1)[:3]
            q1 = np.asarray(moving_world, dtype=float).reshape(-1)[:3]
            segment = q1 - q0
            seg_len = float(np.linalg.norm(segment))
            if not np.isfinite(seg_len) or seg_len <= 1e-9:
                return
            _center, scene_span = self._row_scene_bounds()
            base_offset = max(float(scene_span) * 0.08, 2.0)
            try:
                view_normal = self._camera_view_normal()
            except Exception:
                view_normal = None
            try:
                screen_axes = self._camera_screen_world_axes()
            except Exception:
                screen_axes = None
            screen_up = screen_axes[1] if screen_axes else None
            side = svc.offset_direction(segment, view_normal=view_normal, screen_up=screen_up)
            row_band = 1.0 + 0.38 * float(int(row_index) % 3)
            offset = side * base_offset * row_band
            start = q0 + offset
            end = q1 + offset
            color = svc.REANCHOR_DIMENSION_COLOR
            mesh = svc.arrow_mesh(start, end, scene_span=scene_span)
            if mesh is not None:
                actor = self._add_mesh_actor(
                    mesh,
                    color=color,
                    opacity=0.95,
                    flat_shading=True,
                    backface_culling=False,
                )
                if actor is not None:
                    actor.PickableOff()
                    self._dimension_anchor_preview_actors.append(actor)
            for tip, anchor in ((q0, start), (q1, end)):
                leader = self._add_mesh_actor(
                    pv.Line(
                        tuple(float(v) for v in tip),
                        tuple(float(v) for v in anchor),
                    ),
                    color=(0.72, 0.50, 0.70),
                    opacity=0.6,
                    line_width=svc.DIMENSION_LEADER_LINE_WIDTH,
                    backface_culling=False,
                )
                if leader is not None:
                    leader.PickableOff()
                    self._dimension_anchor_preview_actors.append(leader)
            measured = abs(float(q1[2] - q0[2]))
            label = f"{self._dimension_anchor_display_label(int(row_index))} measured = {measured:.6g} mm"
            actor_cls = svc.billboard_text_actor_cls
            if actor_cls is not None:
                label_position = 0.5 * (start + end) + side * max(base_offset * 0.22, 0.8)
                text_actor = actor_cls()
                text_actor.SetInput(str(label))
                text_actor.SetPosition(
                    float(label_position[0]), float(label_position[1]), float(label_position[2])
                )
                try:
                    text_prop = text_actor.GetTextProperty()
                    text_prop.SetFontSize(13)
                    text_prop.SetColor(0.32, 0.04, 0.30)
                    text_prop.SetBackgroundColor(1.0, 1.0, 1.0)
                    text_prop.SetBackgroundOpacity(0.82)
                    text_prop.SetFrame(1)
                    text_prop.SetFrameColor(0.62, 0.18, 0.58)
                except Exception:
                    pass
                text_actor.SetPickable(False)
                self._add_renderer_view_prop(text_actor)
                self._dimension_anchor_preview_actors.append(text_actor)
        except Exception:
            pass
        try:
            self.render()
        except Exception:
            pass

    def _set_dimension_anchor_snap_highlight(self, hit_key, x: int, y: int) -> None:
        """Highlight the surface/edge under the cursor that the endpoint will snap
        to (feedback #3). A STEP body shows its picked-face outline; a KrakenOS
        surface row highlights the row."""
        if hit_key is None:
            self._clear_dimension_anchor_snap_highlight()
            return
        step_label = self._actor_step_map.get(hit_key)
        if step_label is not None:
            try:
                cell_id = int(self._picker.GetCellId())
            except Exception:
                cell_id = -1
            try:
                feature_pick = self._step_feature_pick_for_display_xy(
                    str(step_label), (x, y), actor_key=hit_key, cell_id=cell_id
                )
                feature = feature_pick.get("feature") if feature_pick is not None else None
                outline = (
                    self._hover_overlay_for_feature(feature[0], feature[1])
                    if feature is not None
                    else None
                )
                self._set_step_hover_outline(outline, (hit_key, "reanchor", cell_id), render=False)
            except Exception:
                pass
            if self._dimension_anchor_snap_highlight_row is not None:
                self._set_row_highlight(None)
                self._dimension_anchor_snap_highlight_row = None
            return
        row_index = self._actor_row_map.get(hit_key)
        if row_index is not None:
            self._set_step_hover_outline(None, None, render=False)
            if self._dimension_anchor_snap_highlight_row != int(row_index):
                self._set_row_highlight(int(row_index))
                self._dimension_anchor_snap_highlight_row = int(row_index)
            return
        self._clear_dimension_anchor_snap_highlight()

    def _clear_dimension_anchor_snap_highlight(self) -> None:
        try:
            self._set_step_hover_outline(None, None, render=False)
        except Exception:
            pass
        if self._dimension_anchor_snap_highlight_row is not None:
            try:
                self._set_row_highlight(None)
            except Exception:
                pass
            self._dimension_anchor_snap_highlight_row = None

    def _clear_dimension_anchor_preview(self, *, render: bool = True) -> None:
        for actor in list(self._dimension_anchor_preview_actors):
            try:
                self._remove_renderer_view_prop(actor)
            except Exception:
                pass
        self._dimension_anchor_preview_actors = []
        if render:
            try:
                self.render()
            except Exception:
                pass

    def _exit_dimension_anchor_pick_mode(self, *, render: bool = True) -> None:
        self._dimension_anchor_pick_mode = False
        self._dimension_anchor_pick_state = None
        self._dimension_anchor_drag_state = None
        self._clear_dimension_anchor_preview(render=False)
        self._clear_dimension_anchor_snap_highlight()
        try:
            self._set_axis_pick_cursor(False)
        except Exception:
            pass
        try:
            self._update_mode_badge()
        except Exception:
            pass
        if render:
            try:
                self.render()
            except Exception:
                pass

    def _commit_dimension_anchor_pick(self) -> None:
        """A plain click commits the re-anchor: write the measured override and
        leave the modal pick (feedback #4)."""
        state = self._dimension_anchor_pick_state
        if state is None:
            self._exit_dimension_anchor_pick_mode()
            return
        # Refresh the snap at the exact click position so the committed location
        # matches where the user clicked, not the last hover sample.
        self._apply_dimension_anchor_pick_motion()
        state = self._dimension_anchor_pick_state or state
        snapped = state.get("snapped_world") if isinstance(state, dict) else None
        if snapped is None:
            self.status_var.set("Dimension re-anchor cancelled (click a surface/edge to set it).")
            self._exit_dimension_anchor_pick_mode()
            return
        row_index = int(state.get("row_index", -1))
        endpoint = str(state.get("endpoint", "end"))
        fixed_world = state.get("fixed_world") if isinstance(state, dict) else None
        try:
            fixed_z = float(np.asarray(fixed_world, dtype=float).reshape(-1)[2])
        except Exception:
            fixed_z = None
        self._exit_dimension_anchor_pick_mode(render=False)
        try:
            self.editor.apply_dimension_anchor_override(
                row_index,
                endpoint,
                np.asarray(snapped, dtype=float).reshape(-1)[:3],
                fixed_z=fixed_z,
            )
        except Exception as exc:
            self.editor.append_debug(f"dimension re-anchor commit failed: {exc}")
        try:
            self.render()
        except Exception:
            pass

    def _axial_extent_from_actor_keys(self, actor_keys, axis_unit) -> dict[str, object] | None:
        axis = np.asarray(axis_unit, dtype=float).reshape(-1)[:3]
        norm = float(np.linalg.norm(axis))
        if not np.isfinite(norm) or norm <= 1.0e-12:
            return None
        axis = axis / norm
        mins = np.array((np.inf, np.inf, np.inf), dtype=float)
        maxs = np.array((-np.inf, -np.inf, -np.inf), dtype=float)
        found = False
        for actor_key in list(actor_keys or []):
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            try:
                bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
            except Exception:
                continue
            if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                continue
            mins = np.minimum(mins, (bounds[0], bounds[2], bounds[4]))
            maxs = np.maximum(maxs, (bounds[1], bounds[3], bounds[5]))
            found = True
        if not found or not (np.all(np.isfinite(mins)) and np.all(np.isfinite(maxs))):
            return None
        corners = np.array(
            [
                (mins[0], mins[1], mins[2]),
                (maxs[0], mins[1], mins[2]),
                (mins[0], maxs[1], mins[2]),
                (mins[0], mins[1], maxs[2]),
                (maxs[0], maxs[1], mins[2]),
                (maxs[0], mins[1], maxs[2]),
                (mins[0], maxs[1], maxs[2]),
                (maxs[0], maxs[1], maxs[2]),
            ],
            dtype=float,
        )
        projections = corners @ axis
        centroid = 0.5 * (mins + maxs)
        return {
            "axis": axis,
            "proj_min": float(np.min(projections)),
            "proj_max": float(np.max(projections)),
            "proj_center": float(np.dot(centroid, axis)),
            "centroid": centroid,
            # bugs/0093: does the body's transverse bounds include the optical axis
            # (x=y=0)? An OFF-axis (randomly-parked) overlay must NOT be carved out
            # of a thickness dimension -- it isn't on the beam.
            "straddles_axis": bool(
                (float(mins[0]) <= 0.0 <= float(maxs[0]))
                and (float(mins[1]) <= 0.0 <= float(maxs[1]))
            ),
        }

    def _scene_component_axial_extents(
        self,
        axis_unit,
        *,
        exclude_step: str | None = None,
        exclude_rows: set[int] | None = None,
    ) -> list[dict[str, object]]:
        exclude = str(exclude_step or "").strip().lower()
        skip_rows: set[int] = set()
        for value in exclude_rows or ():
            try:
                skip_rows.add(int(value))
            except Exception:
                continue
        extents: list[dict[str, object]] = []
        for step_label, actor_keys in list(self._step_actor_map.items()):
            if str(step_label).strip().lower() == exclude:
                continue
            extent = self._axial_extent_from_actor_keys(actor_keys, axis_unit)
            if extent is not None:
                extents.append(extent)
        for row_index, actor_keys in list(self._row_actor_map.items()):
            try:
                idx = int(row_index)
            except Exception:
                continue
            if idx < 0 or idx in skip_rows:
                continue
            extent = self._axial_extent_from_actor_keys(actor_keys, axis_unit)
            if extent is not None:
                extents.append(extent)
        return extents

    def _step_overlay_axial_gap(
        self, label: str, axis_unit=None
    ) -> tuple[np.ndarray, np.ndarray, float] | None:
        """Edge-to-edge axial gap between a STEP overlay and the component just
        before it along ``axis_unit`` (defaults to the world optical/Z axis).

        Returns ``(near_point, prev_far_point, gap_mm)`` with both points on the
        dragged component's lateral center line so the dimension reads as a pure
        axial distance. Kept as a clean, side-effect-free seam so a future
        focus/collimation quick-solve can query spacing while sweeping position.
        """
        label = str(label or "").strip().lower()
        if not label:
            return None
        if axis_unit is None:
            axis_unit = (0.0, 0.0, 1.0)
        me = self._axial_extent_from_actor_keys(self._step_actor_map.get(label, []), axis_unit)
        if me is None:
            return None
        axis = me["axis"]
        me_center = float(me["proj_center"])
        previous: dict[str, object] | None = None
        for extent in self._scene_component_axial_extents(axis, exclude_step=label):
            if float(extent["proj_center"]) >= me_center:
                continue
            if previous is None or float(extent["proj_max"]) > float(previous["proj_max"]):
                previous = extent
        if previous is None:
            return None
        base = np.asarray(me["centroid"], dtype=float).reshape(3)
        base_axial = float(np.dot(base, axis))
        near_axial = float(me["proj_min"])
        far_axial = float(previous["proj_max"])
        near_point = base + axis * (near_axial - base_axial)
        prev_far_point = base + axis * (far_axial - base_axial)
        return near_point, prev_far_point, float(near_axial - far_axial)

    def _row_slide_axial_gap(
        self, group_indices, leading_gap_mm: float, axis_unit=None
    ) -> tuple[np.ndarray, np.ndarray, float] | None:
        """Live leading-gap dimension for a promoted optical-solid row slide.

        Unlike the STEP translate overlay, the promoted body's actors do NOT
        move during a continuous drag (the body refresh is debounced), so a
        geometric edge-to-edge read off the actors would be stale. The model is
        mutated every motion frame, though, so ``leading_gap_mm`` (the preceding
        row's post-slide thickness) is the authoritative live spacing.

        The arrow's far end is pinned to the previous *visible* component's far
        edge (static during the drag); the near end is placed exactly
        ``leading_gap_mm`` along the axis from it, so the arrow + label track the
        cursor every frame even while the lens body lags to the next refresh.
        Returns ``(near_point, far_point, gap_mm)`` on the lens group's lateral
        centre line, or ``None`` when there's no preceding component to measure.
        """
        rows = {int(r) for r in (group_indices or []) if r is not None and int(r) >= 0}
        if not rows:
            return None
        if axis_unit is None:
            axis_unit = (0.0, 0.0, 1.0)
        group_keys: list[str] = []
        for r in rows:
            group_keys.extend(self._row_actor_map.get(r, []) or [])
        me = self._axial_extent_from_actor_keys(group_keys, axis_unit)
        if me is None:
            return None
        axis = me["axis"]
        me_center = float(me["proj_center"])
        previous: dict[str, object] | None = None
        for extent in self._scene_component_axial_extents(axis, exclude_rows=rows):
            if float(extent["proj_center"]) >= me_center:
                continue
            if previous is None or float(extent["proj_max"]) > float(previous["proj_max"]):
                previous = extent
        if previous is None:
            return None
        base = np.asarray(me["centroid"], dtype=float).reshape(3)
        base_axial = float(np.dot(base, axis))
        far_axial = float(previous["proj_max"])
        gap = float(leading_gap_mm)
        near_axial = far_axial + gap
        near_point = base + axis * (near_axial - base_axial)
        far_point = base + axis * (far_axial - base_axial)
        return near_point, far_point, gap

    def _row_overlay_axial_gap(
        self, group_indices, axis_unit=None
    ) -> tuple[np.ndarray, np.ndarray, float] | None:
        """Edge-to-edge axial gap for a row group whose body actors are LIVE.

        The placement Move gizmo slides a promoted optical-solid row by moving
        its body actors every frame (``_translate_row_actors`` -> AddPosition,
        bugs/0012), so -- unlike the debounced axis-slide mode that must read the
        live MODEL gap (``_row_slide_axial_gap``) -- the spacing is read
        GEOMETRICALLY off the moved actor bounds, exactly like the imported-STEP
        drag (``_step_overlay_axial_gap``). Finds the previous *visible*
        component along ``axis_unit`` (excluding the dragged group's own rows so
        a sub-body can't be picked as its own predecessor) and returns
        ``(near_point, prev_far_point, gap_mm)`` on the group's lateral centre
        line, or ``None`` when there is nothing before it to measure against.
        """
        rows = {int(r) for r in (group_indices or []) if r is not None and int(r) >= 0}
        if not rows:
            return None
        if axis_unit is None:
            axis_unit = (0.0, 0.0, 1.0)
        group_keys: list[str] = []
        for r in rows:
            group_keys.extend(self._row_actor_map.get(r, []) or [])
        me = self._axial_extent_from_actor_keys(group_keys, axis_unit)
        if me is None:
            return None
        axis = me["axis"]
        me_center = float(me["proj_center"])
        previous: dict[str, object] | None = None
        for extent in self._scene_component_axial_extents(axis, exclude_rows=rows):
            if float(extent["proj_center"]) >= me_center:
                continue
            if previous is None or float(extent["proj_max"]) > float(previous["proj_max"]):
                previous = extent
        base = np.asarray(me["centroid"], dtype=float).reshape(3)
        base_axial = float(np.dot(base, axis))
        near_axial = float(me["proj_min"])
        if previous is not None:
            far_axial = float(previous["proj_max"])
        else:
            # No preceding rendered SOLID body -- e.g. a lone promoted lens with
            # only the non-solid Object surface before it (flag_20260604_111615_630:
            # the recorder scene had row 1 as the ONLY body). Fall back to the
            # previous optical SURFACE position from the model, the same reference
            # the persistent "S{n} Thickness =" dimension uses, so the live gap
            # still appears (and reads identically to that dimension). The surface
            # is static during the drag, so the gap tracks the lens's live near
            # edge exactly as the body-to-body case does.
            far_axial = self._model_previous_surface_axial(min(rows), axis)
            if far_axial is None:
                return None
        near_point = base + axis * (near_axial - base_axial)
        prev_far_point = base + axis * (far_axial - base_axial)
        return near_point, prev_far_point, float(near_axial - far_axial)

    def _model_previous_surface_axial(self, first_row: int, axis_unit) -> float | None:
        """Axial projection of the optical surface just before ``first_row``,
        read from the MODEL (not rendered actors), or ``None`` if there is no
        prior surface. Used by ``_row_overlay_axial_gap`` as the gap reference
        when nothing solid precedes the dragged lens, so the live readout matches
        the persistent "S{n} Thickness =" dimension (which is built from the same
        ``_surface_reference_world_point``)."""
        prev_row = int(first_row) - 1
        if prev_row < 0:
            return None
        try:
            point = np.asarray(
                self.editor._surface_reference_world_point(prev_row), dtype=float
            ).reshape(-1)[:3]
        except Exception:
            return None
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return None
        axis = np.asarray(axis_unit, dtype=float).reshape(-1)[:3]
        return float(np.dot(point, axis))

    def _draw_step_translate_gap_overlay(
        self, near_point, prev_far_point, gap_mm: float
    ) -> None:
        service = self._open3d_thickness_dimension_service()
        if service is None or service.pv is None:
            return
        near = np.asarray(near_point, dtype=float).reshape(3)
        far = np.asarray(prev_far_point, dtype=float).reshape(3)
        segment = near - far
        seg_len = float(np.linalg.norm(segment))
        _center, scene_span = self._row_scene_bounds()
        base_offset = max(float(scene_span) * 0.06, 2.0)
        side = service.offset_direction(
            segment if seg_len > 1.0e-9 else np.asarray((0.0, 0.0, 1.0), dtype=float)
        )
        offset = side * base_offset
        start = far + offset
        end = near + offset
        # Gap dimension colour: emerald green, deliberately distinct from BOTH
        # the optical axis (blue 0,0.43,0.88) and the highlighted optical axis
        # (gold 1.0,0.68,0.05). The old orange (0.95,0.55,0.10) was almost the
        # highlight gold, so the live gap melted into a highlighted axis; green
        # also dodges the pink selection / red edge / gold hover accents (#65).
        color = (0.10, 0.90, 0.45)
        leader_color = (0.50, 0.95, 0.68)
        # Thicker than the persistent dimensions: the live readout still shares
        # the dimension knobs (DIMENSION_LEADER_LINE_WIDTH / arrow_mesh) but
        # scales them up so the moving gap stands out while dragging (#65).
        mesh = service.arrow_mesh(start, end, scene_span=scene_span, thickness_scale=1.8)
        if mesh is not None:
            actor = self._add_mesh_actor(
                mesh, color=color, opacity=0.95, flat_shading=True, backface_culling=False
            )
            if actor is not None:
                self._step_translate_gap_actors.append(actor)
        for tip, anchor in ((far, start), (near, end)):
            try:
                line = service.pv.Line(
                    tuple(float(v) for v in tip), tuple(float(v) for v in anchor)
                )
            except Exception:
                continue
            leader = self._add_mesh_actor(
                line,
                color=leader_color,
                opacity=0.75,
                line_width=service.DIMENSION_LEADER_LINE_WIDTH * 2.0,
                backface_culling=False,
            )
            if leader is not None:
                self._step_translate_gap_actors.append(leader)
        midpoint = 0.5 * (start + end) + side * max(base_offset * 0.25, 0.8)
        self._add_step_translate_gap_label(midpoint, f"gap = {gap_mm:.4g} mm", frame_color=color)

    def _add_step_translate_gap_label(self, position, text: str, *, frame_color=(0.10, 0.90, 0.45)) -> None:
        if self._renderer is None or vtkBillboardTextActor3D is None:
            return
        point = np.asarray(position, dtype=float).reshape(-1)[:3]
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return
        try:
            actor = vtkBillboardTextActor3D()
            actor.SetInput(str(text))
            actor.SetPosition(float(point[0]), float(point[1]), float(point[2]))
            try:
                actor.PickableOff()
            except Exception:
                pass
            try:
                text_prop = actor.GetTextProperty()
                text_prop.SetFontSize(13)
                text_prop.SetColor(0.20, 0.10, 0.0)
                text_prop.SetBackgroundColor(1.0, 0.96, 0.86)
                text_prop.SetBackgroundOpacity(0.85)
                text_prop.SetFrame(1)
                fc = tuple(float(c) for c in frame_color)[:3]
                text_prop.SetFrameColor(fc[0], fc[1], fc[2])
            except Exception:
                pass
            self._add_renderer_view_prop(actor)
            self._step_translate_gap_actors.append(actor)
        except Exception as exc:
            self.editor.append_debug(f"3D STEP gap label skipped: {exc}")

    def _update_step_translate_drag_overlay(self, state: dict[str, object]) -> None:
        label = str(state.get("label", "")).strip().lower()
        axis = str(state.get("axis", "")).strip().lower()
        total_mm = float(state.get("applied_delta_mm", 0.0))
        display = self.editor._step_overlay_display_label(label).upper() if label else "STEP"
        # Rebuild the transient gap dimension each motion. Do NOT render here: the
        # body move already issued a render this event, so the refreshed dimension
        # shows on the next motion frame (one-frame lag, imperceptible) while the
        # body keeps tracking the cursor at one render per event.
        self._clear_step_translate_drag_overlay()
        gap = None
        try:
            gap = self._step_overlay_axial_gap(label, state.get("axis_unit"))
        except Exception as exc:
            self.editor.append_debug(f"STEP translate gap query failed for {label}: {exc}")
            gap = None
        if gap is None:
            self.status_var.set(
                f"{display} STEP {axis.upper()} move: {total_mm:+.4g} mm (release to commit)."
            )
            return
        near_point, prev_far_point, gap_mm = gap
        try:
            self._draw_step_translate_gap_overlay(near_point, prev_far_point, gap_mm)
        except Exception as exc:
            self.editor.append_debug(f"STEP translate gap draw failed for {label}: {exc}")
        self.status_var.set(
            f"{display} STEP {axis.upper()} move {total_mm:+.4g} mm | "
            f"edge gap to previous = {gap_mm:.4g} mm (release to commit)."
        )

    def _clear_step_translate_drag_overlay(self, *, render: bool = False) -> None:
        actors = list(self._step_translate_gap_actors)
        self._step_translate_gap_actors = []
        for actor in actors:
            try:
                self._remove_renderer_view_prop(actor)
            except Exception:
                pass
            actor_key = self._actor_key(actor)
            if actor_key is not None:
                self._actor_by_key.pop(actor_key, None)
        if render and actors:
            try:
                self.render()
            except Exception:
                pass

    def _update_axis_slide_gap_overlay(
        self, state: dict[str, object], result: dict[str, object]
    ) -> None:
        """Redraw the live leading-gap dimension during a promoted-row slide.

        Nothing else renders while the slide drag is in flight (the body refresh
        is debounced), so this clears the previous transient gap actors, draws
        the restyled green arrow + label from the live model gap, and issues the
        one render that makes the moving dimension visible.
        """
        self._clear_step_translate_drag_overlay()
        group = list(state.get("group_indices", [])) or [int(result.get("row_index", -1))]
        try:
            leading_gap = float(result.get("preceding_thickness_after", 0.0))
        except Exception:
            leading_gap = 0.0
        gap = None
        try:
            gap = self._row_slide_axial_gap(group, leading_gap)
        except Exception as exc:
            self.editor.append_debug(f"axis-slide gap query failed: {exc}")
            gap = None
        if gap is not None:
            near_point, far_point, gap_mm = gap
            try:
                self._draw_step_translate_gap_overlay(near_point, far_point, gap_mm)
            except Exception as exc:
                self.editor.append_debug(f"axis-slide gap draw failed: {exc}")
        try:
            self.render()
        except Exception:
            pass

    def _update_placement_drag_gap_overlay(self, state: dict[str, object]) -> None:
        """Live leading-gap dimension while a promoted optical-solid row is slid
        along the optical axis with the placement Move gizmo.

        Without this the gizmo slide showed no live spacing, even though the
        imported-STEP drag and the axis-slide mode both do (recorder flag
        ``flag_20260604_111615_630``: "sliding of promoted analytical lens still
        not showing dynamic gap highlight similar to the unpromoted one").

        Only an axial (Z = optical axis) *translate* is measured: X/Y decenters
        have no axial gap to report, and rotation isn't a slide. The Move-gizmo
        translate moves the body actors live (bugs/0012), so the gap is read
        geometrically off the moved actors (``_row_overlay_axial_gap``). No
        render here -- ``_translate_row_actors`` already issued one this event, so
        the refreshed dimension shows on the next motion frame (the same
        imperceptible one-frame lag as the STEP overlay)."""
        if str(state.get("kind")) == "rotate":
            return
        if str(state.get("axis", "")).strip().lower() != "z":
            return
        try:
            row_index = int(state.get("row_index", -1))
        except Exception:
            return
        if row_index < 0:
            return
        try:
            group = list(self.editor._lens_row_group_for_row(row_index)) or [row_index]
        except Exception:
            group = [row_index]
        self._clear_step_translate_drag_overlay()
        gap = None
        try:
            gap = self._row_overlay_axial_gap(group)
        except Exception as exc:
            self.editor.append_debug(f"placement-slide gap query failed for S{row_index}: {exc}")
            gap = None
        if gap is None:
            return
        near_point, prev_far_point, gap_mm = gap
        try:
            self._draw_step_translate_gap_overlay(near_point, prev_far_point, gap_mm)
        except Exception as exc:
            self.editor.append_debug(f"placement-slide gap draw failed for S{row_index}: {exc}")

    def _axis_slide_mode_active(self) -> bool:
        try:
            return bool(self.slide_along_axis_mode_var.get())
        except Exception:
            return False

    def _toggle_axis_slide_mode(self) -> None:
        if self._axis_slide_mode_active():
            self.status_var.set(
                "Slide along axis: click an optical element body and drag along Z. "
                "Overall track length is preserved; no off-axis or rotation allowed."
            )
        else:
            self._axis_slide_drag_state = None
            self.status_var.set("Slide along axis: off.")

    def _axis_slide_snap_step_for_row(self, row_index: int) -> float:
        try:
            row = self.editor.rows[int(row_index)]
        except Exception:
            return 0.25
        advanced = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        settings = advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}) if isinstance(advanced, dict) else {}
        try:
            snap_enabled = bool(settings.get("snap_enabled", True))
            snap = float(settings.get("snap_mm", 0.25))
        except Exception:
            snap_enabled, snap = True, 0.25
        if not snap_enabled or not np.isfinite(snap) or snap <= 0.0:
            snap = 0.25
        return float(snap)

    def _axis_slide_state_from_current_pick(self) -> dict[str, object] | None:
        if not self._axis_slide_mode_active():
            return None
        if (
            self._picker is None
            or self._renderer is None
            or self._vtk_interactor is None
            or self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or self._dimension_anchor_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        ):
            return None
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
        except Exception:
            return None
        actor_key = self._actor_key(actor) if actor is not None else None
        # If the picker missed entirely (no actor at the click position --
        # off-screen click, click in empty space, etc.), don't guess a
        # row spatially: in a cascade the closest-by-distance row is
        # almost always wrong (it picks whichever element happens to sit
        # near the world origin). Returning None lets the caller fall
        # back to camera orbit instead of silently moving a random row.
        if actor_key is None:
            return None
        row_index = self._actor_row_map.get(actor_key)
        if row_index is None:
            # Edge / wireframe / silhouette actors for a row are tracked-only:
            # they appear in _row_actor_map[row] but not in _actor_row_map.
            # vtkCellPicker often hits one of these on top of the translucent
            # body, so without this lookup the slide gesture silently no-ops
            # when the user clicks the body's outline.
            for candidate_row, actor_keys in (self._row_actor_map or {}).items():
                if actor_key in (actor_keys or []):
                    row_index = candidate_row
                    break
        if row_index is None:
            # The picker hit *something* but it isn't tied to a row in
            # either direction. Use the world hit point to find the row
            # whose actor center is closest, but require the hit to be
            # inside a reasonable radius around that row -- otherwise a
            # click on a decorative actor far from any cascade element
            # would still resolve to "the nearest row", which is the
            # bug the multi-element harness flagged.
            try:
                pick_world = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            except Exception:
                pick_world = None
            if (
                pick_world is None
                or pick_world.size < 3
                or not np.all(np.isfinite(pick_world[:3]))
            ):
                return None
            best: tuple[float, int, float] | None = None
            for candidate_row in (self._row_actor_map or {}).keys():
                try:
                    candidate_row_int = int(candidate_row)
                except Exception:
                    continue
                if not (0 <= candidate_row_int < len(self.editor.rows)):
                    continue
                center = self._row_actor_center_world(candidate_row_int)
                if center is None or center.size < 3 or not np.all(np.isfinite(center[:3])):
                    continue
                dist = float(np.linalg.norm(pick_world[:3] - center[:3]))
                # Estimate this row's body radius from the actor bounds so
                # the spatial test scales with how big the element is.
                row_radius = 1.0
                for actor_key_in_row in list(self._row_actor_map.get(candidate_row_int, []) or []):
                    body_actor = self._actor_by_key.get(actor_key_in_row)
                    if body_actor is None:
                        continue
                    try:
                        bounds = np.asarray(body_actor.GetBounds(), dtype=float).reshape(6)
                    except Exception:
                        continue
                    if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                        continue
                    diag = float(np.linalg.norm(
                        (bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4])
                    ))
                    row_radius = max(row_radius, 0.5 * diag)
                if best is None or dist < best[0]:
                    best = (dist, candidate_row_int, row_radius)
            if best is None:
                return None
            if best[0] > best[2] * 1.5:
                # Hit is too far from the closest row's body radius --
                # decline rather than retarget the gesture.
                return None
            row_index = best[1]
        try:
            row_index = int(row_index)
        except Exception:
            return None
        if not (0 <= row_index < len(self.editor.rows)):
            return None
        row = self.editor.rows[row_index]
        promoted = bool(
            self.editor._file_backed_stl_row_at(row_index) is not None
            or self.editor._is_any_promoted_optical_solid_row(row)
        )
        if not promoted:
            self.status_var.set(
                "Slide along axis ignores S{row}: only promoted optical-solid rows can be slid.".format(row=row_index)
            )
            return None
        group = self.editor._lens_row_group_for_row(row_index)
        if not group or group[0] - 1 < 0 or group[-1] + 1 >= len(self.editor.rows):
            self.status_var.set(
                "Slide along axis rejected: lens needs a preceding and trailing row to absorb the slide."
            )
            return None
        snap_mm = self._axis_slide_snap_step_for_row(row_index)
        direction = self._placement_drag_display_direction("translate", "z", 1.0, actor)
        label = f"lens S{group[0]}" if len(group) == 1 else f"lens group S{group[0]}-S{group[-1]}"
        history_started = False
        try:
            self.editor._begin_history_capture()
            history_started = True
        except Exception:
            history_started = False
        self.status_var.set(
            f"Slide {label} along Z; snap {snap_mm:.6g} mm. Release to commit; Esc cancels."
        )
        return {
            "row_index": row_index,
            "group_indices": list(group),
            "snap_mm": float(snap_mm),
            "display_direction": np.asarray(direction, dtype=float),
            "pixel_accumulator": 0.0,
            "applied_delta_mm": 0.0,
            "history_started": bool(history_started),
            "last_result": None,
        }

    def _apply_axis_slide_drag_motion(self, dx: int | float, dy: int | float) -> None:
        state = self._axis_slide_drag_state
        if state is None:
            return
        try:
            cursor_delta = np.asarray((float(dx), -float(dy)), dtype=float)
            direction = np.asarray(state.get("display_direction"), dtype=float).reshape(-1)[:2]
            signed_pixels = float(np.dot(cursor_delta, direction))
        except Exception:
            return
        if not np.isfinite(signed_pixels) or abs(signed_pixels) <= 1.0e-12:
            return
        pixels_per_step = self._placement_drag_pixels_per_step()
        accumulator = float(state.get("pixel_accumulator", 0.0)) + signed_pixels
        steps = int(accumulator / pixels_per_step)
        if steps == 0:
            state["pixel_accumulator"] = accumulator
            return
        state["pixel_accumulator"] = accumulator - float(steps) * pixels_per_step
        snap_mm = float(state.get("snap_mm", 0.25))
        delta_z = float(steps) * snap_mm
        try:
            result = self.editor.slide_lens_along_axis(
                int(state.get("row_index", -1)),
                delta_z,
                record_history=False,
                sync_table=False,
            )
        except Exception as exc:
            self.status_var.set(f"Slide along axis: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D axis slide failed: {exc}")
            return
        state["applied_delta_mm"] = float(state.get("applied_delta_mm", 0.0)) + delta_z
        state["last_result"] = dict(result)
        group = list(state.get("group_indices", [])) or [int(result.get("row_index", -1))]
        self.status_var.set(
            "Slide S{first}-S{last} along Z: total dz={total:+.6g} mm "
            "(release to redraw; Esc reverts) "
            "(leading S{pre}.thickness={pt:.6g}, trailing S{tr}.thickness={tt:.6g}).".format(
                first=int(group[0]),
                last=int(group[-1]),
                total=float(state.get("applied_delta_mm", 0.0)),
                pre=int(result.get("preceding_row_index", -1)),
                pt=float(result.get("preceding_thickness_after", 0.0)),
                tr=int(result.get("trailing_row_index", -1)),
                tt=float(result.get("trailing_thickness_after", 0.0)),
            )
        )
        self._update_axis_slide_gap_overlay(state, result)

    def _finish_axis_slide_drag(self, state: dict[str, object]) -> None:
        self._clear_step_translate_drag_overlay(render=False)
        try:
            applied_delta = float(state.get("applied_delta_mm", 0.0))
            group = list(state.get("group_indices", []))
        except Exception:
            return
        if abs(applied_delta) <= 1.0e-9 or not group:
            if bool(state.get("history_started", False)):
                try:
                    self.editor._history_pending_state = None
                except Exception:
                    pass
            self.status_var.set("Slide along axis: no movement applied.")
            return
        first = int(group[0])
        last = int(group[-1])
        try:
            self.editor._sync_table()
            self.editor._select_table_indices(group, focus_index=first)
        except Exception:
            pass
        if bool(state.get("history_started", False)):
            try:
                self.editor._commit_history_capture()
            except Exception as exc:
                self.editor.append_debug(f"3D axis slide history commit failed: {exc}")
        try:
            self.refresh_from_editor()
            self.highlight_row(first)
        except Exception as exc:
            self.editor.append_debug(f"3D axis slide finish refresh failed: {exc}")
        label = f"S{first}" if first == last else f"S{first}-S{last}"
        self.status_var.set(f"Slide along axis committed: {label} moved {applied_delta:+.6g} mm along Z.")

    def _rotate_camera_fixed_drag(self, dx: int | float, dy: int | float) -> None:
        """CAD-style orbit: always rotate around world up for Azimuth.

        The Azimuth axis is forced to world up ``(0, 1, 0)`` before every
        rotation, so a left-drag *always* rotates around the world Y
        axis regardless of accumulated state. VTK's stock orbit relies
        on ``OrthogonalizeViewUp`` to keep view-up perpendicular to
        view-direction, but that normalisation can flip sign near
        degenerate angles -- and once view-up flips, the next Azimuth
        rotates the camera in the opposite direction, which is the
        "rotates one way then reverses half-way through the drag"
        symptom reported in step1-5.png.

        Locking view-up to world up before each rotation also matches
        the way most CAD viewers feel: horizontal drag orbits around the
        vertical axis, vertical drag tilts up/down, and the two never
        cross-couple into a roll. Camera position rotates monotonically
        with the cumulative drag direction.

        Rate is 0.10 deg / px so a typical 100 px drag is a gentle
        ~10 deg camera move.
        """
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        try:
            dx_f = float(dx)
            dy_f = float(dy)
        except Exception:
            return
        if abs(dx_f) < 1e-12 and abs(dy_f) < 1e-12:
            return
        degrees_per_pixel = 0.10
        try:
            # Choose a view-up that's PERPENDICULAR to the current view
            # direction. The previous code hardcoded SetViewUp(0,1,0)
            # which is degenerate when the camera looks straight down
            # +/-Y -- the XZ orthographic view. VTK then warns
            # "Resetting view-up since view plane normal is parallel"
            # and the canvas blanks out.
            #
            # Algorithm: prefer world +Y; if it's parallel to the
            # view direction, fall back to +X; if THAT'S parallel,
            # fall back to +Z. One of the three is always orthogonal
            # to any view direction.
            view_up = self._safe_view_up_for_camera(camera)
            camera.SetViewUp(*view_up)
            # "Grab the scene" drag direction (reversed from the old
            # camera-orbit convention you found unintuitive). Drag
            # right -> scene rotates right under the cursor; drag up
            # -> scene tilts up toward the cursor. Achieved by
            # NEGATING the azimuth and dropping the negation on the
            # elevation -- both flips together so the rotation feels
            # like dragging the actual body, not orbiting the camera
            # around it.
            camera.Azimuth(-dx_f * degrees_per_pixel)
            camera.Elevation(dy_f * degrees_per_pixel)
            # Re-lock view-up after Elevation tilts view-direction so
            # the NEXT tick's Azimuth rotates around a stable axis.
            camera.SetViewUp(*self._safe_view_up_for_camera(camera))
            self._reset_camera_clipping_range_for_scene()
            self.render()
        except Exception as exc:
            self.editor.append_debug(f"3D fixed-drag rotation failed: {exc}")

    @staticmethod
    def _safe_view_up_for_camera(camera) -> tuple[float, float, float]:
        """Return a world axis that's safe to use as view-up.

        Strategy: keep the camera's CURRENT view-up if it's still
        safe (not near-parallel to the view direction). Only fall
        back to a fresh axis when the existing up is truly
        degenerate. This avoids the camera "jumping" mid-drag when
        a small rotation shifts the preferred axis (previously +Z
        in XZ view would flip back to +Y after a few degrees,
        producing a discontinuous 90 deg reorient).

        When forced to pick fresh: prefer +Y (the inspector's
        global convention), then +Z, then +X. One of the three is
        always orthogonal-ish to any view direction.
        """
        try:
            cam_pos = np.asarray(camera.GetPosition(), dtype=float).reshape(3)
            focal = np.asarray(camera.GetFocalPoint(), dtype=float).reshape(3)
            current_up = np.asarray(camera.GetViewUp(), dtype=float).reshape(3)
        except Exception:
            return (0.0, 1.0, 0.0)
        view_dir = focal - cam_pos
        norm = float(np.linalg.norm(view_dir))
        if norm < 1e-9:
            return (0.0, 1.0, 0.0)
        view_dir = view_dir / norm
        current_up_norm = float(np.linalg.norm(current_up))
        # Stickiness threshold: keep the current view-up as long as
        # it's at least 15 deg off the view direction (|cos| < 0.966).
        # Switching threshold (below) uses a looser 10 deg gate so
        # we don't oscillate at the boundary.
        if current_up_norm > 1e-9:
            normalised_current = current_up / current_up_norm
            if abs(float(np.dot(normalised_current, view_dir))) < 0.966:
                return (
                    float(normalised_current[0]),
                    float(normalised_current[1]),
                    float(normalised_current[2]),
                )
        # Current up is degenerate or missing -- pick fresh.
        for candidate in (
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 0.0),
        ):
            up = np.asarray(candidate, dtype=float)
            if abs(float(np.dot(up, view_dir))) < 0.985:
                return (float(up[0]), float(up[1]), float(up[2]))
        return (0.0, 1.0, 0.0)

    def _pan_camera_fixed_drag(self, dx: int | float, dy: int | float) -> None:
        """Pan the camera laterally in its current view plane."""
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        try:
            dx_f = float(dx)
            dy_f = float(dy)
        except Exception:
            return
        if abs(dx_f) < 1e-12 and abs(dy_f) < 1e-12:
            return
        try:
            position = np.asarray(camera.GetPosition(), dtype=float).reshape(-1)[:3]
            focal = np.asarray(camera.GetFocalPoint(), dtype=float).reshape(-1)[:3]
            view_up = np.asarray(camera.GetViewUp(), dtype=float).reshape(-1)[:3]
            if position.size < 3 or focal.size < 3 or view_up.size < 3:
                return
            view_dir = focal[:3] - position[:3]
            view_norm = float(np.linalg.norm(view_dir))
            up_norm = float(np.linalg.norm(view_up[:3]))
            if view_norm <= 1e-12 or up_norm <= 1e-12:
                return
            view_dir = view_dir[:3] / view_norm
            view_up = view_up[:3] / up_norm
            right = np.cross(view_dir, view_up)
            right_norm = float(np.linalg.norm(right))
            if right_norm <= 1e-12:
                return
            right = right / right_norm
            view_up = np.cross(right, view_dir)
            up_norm = float(np.linalg.norm(view_up))
            if up_norm <= 1e-12:
                return
            view_up = view_up / up_norm
            try:
                _width, height = self._vtk_widget.GetRenderWindow().GetSize() if self._vtk_widget is not None else self._renderer.GetSize()
            except Exception:
                _width, height = self._renderer.GetSize()
            height = max(float(height), 1.0)
            if int(camera.GetParallelProjection()):
                world_per_pixel = (2.0 * float(camera.GetParallelScale())) / height
            else:
                view_angle = np.deg2rad(float(camera.GetViewAngle()))
                world_per_pixel = (2.0 * view_norm * float(np.tan(0.5 * view_angle))) / height
            if not np.isfinite(world_per_pixel) or world_per_pixel <= 0.0:
                return
            delta = (-dx_f * right + dy_f * view_up) * world_per_pixel
            if not np.all(np.isfinite(delta[:3])):
                return
            camera.SetPosition(*(position[:3] + delta[:3]))
            camera.SetFocalPoint(*(focal[:3] + delta[:3]))
            camera.OrthogonalizeViewUp()
            self._reset_camera_clipping_range_for_scene()
            self.render()
        except Exception as exc:
            self.editor.append_debug(f"3D middle-drag pan failed: {exc}")

    @staticmethod
    def _actor_key(actor) -> str | None:
        if actor is None:
            return None
        try:
            return str(actor.GetAddressAsString(""))
        except Exception:
            return str(id(actor))

    @staticmethod
    def _surface_color(surface) -> tuple[float, float, float]:
        absorb_color = (10 / 256.0, 23 / 256.0, 24 / 256.0)
        mirror_color = (189 / 256.0, 189 / 256.0, 189 / 256.0)
        glass_color = (12 / 256.0, 238 / 256.0, 246 / 256.0)
        try:
            color = tuple(float(v) for v in surface.Color)
            if len(color) == 3 and any(abs(v) > 1e-9 for v in color):
                return color
        except Exception:
            pass
        glass = str(getattr(surface, "Glass", "") or "").upper()
        if glass == "MIRROR":
            return mirror_color
        if glass == "ABSORB":
            return absorb_color
        return glass_color

    @staticmethod
    def _mesh_with_transform(poly, transform) -> pv.DataSet | None:
        try:
            mesh = pv.wrap(poly)
        except Exception:
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface")
        except Exception:
            pass
        try:
            mesh = mesh.copy(deep=True)
        except Exception:
            return None
        try:
            pts = np.asarray(mesh.points, dtype=float)
        except Exception:
            return None
        if pts.size == 0:
            return None
        # Kraken's SYSTEM.AAA blocks are already in display/world coordinates.
        # TRANS_2A is for tracing into local surface coordinates; applying it
        # here doubles the axial positions and moves optical markers away from
        # imported STEP hardware.
        return mesh

    def _set_row_highlight(self, row_index: int | None) -> None:
        self._set_row_highlights([] if row_index is None else [int(row_index)])

    def _set_row_highlights(self, row_indices) -> None:
        self._selection_representation.apply_row_selection(row_indices)

    def highlight_row(self, row_index: int | None) -> None:
        self._set_row_highlight(row_index)
        self.render()

    def highlight_rows(self, row_indices) -> None:
        self._set_row_highlights(row_indices)
        self.render()

    @staticmethod
    def _set_row_actor_selected(actor, selected: bool) -> None:
        if actor is None:
            return
        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None
        if prop is None:
            return
        base = getattr(actor, "_kraken_row_select_style", None)
        if not isinstance(base, dict):
            try:
                base = {
                    "edge_visibility": int(prop.GetEdgeVisibility()),
                    "edge_color": tuple(float(value) for value in prop.GetEdgeColor()),
                    "line_width": float(prop.GetLineWidth()),
                    "opacity": float(prop.GetOpacity()),
                    "ambient": float(prop.GetAmbient()),
                    "diffuse": float(prop.GetDiffuse()),
                    "color": tuple(float(value) for value in prop.GetColor()),
                }
                actor._kraken_row_select_style = base
            except Exception:
                base = {}
        # A baseline-invisible actor (opacity ~0) is a pick-only / hidden
        # companion surface -- e.g. the second, undrawn lens-body
        # representation that backs an analytic lens alongside the visible
        # glassy drum. Selection must leave it untouched: bumping its
        # opacity and painting red triangle edges would resurrect it as a
        # solid "ghost red block" trailing the lens (bugs/0002). An
        # undrawn surface can show no meaningful selection feedback anyway.
        if float(base.get("opacity", 1.0)) <= 1e-3:
            return
        is_file_backed_body = bool(getattr(actor, "_kraken_file_backed_row_body", False))
        is_glassy_lens_body = bool(getattr(actor, "_kraken_glassy_lens_body", False))
        # A round-lens-like solid body (e.g. an aspheric achromat promoted to a
        # file-backed optical solid) is a dense mesh: painting per-triangle red
        # edges on selection reads as a solid red block of "many faces" instead
        # of pink translucent (bugs/0003). It carries the round-lens flag even
        # when it misses the file-backed/glassy flags, so suppress its triangle
        # edges too -- its separate rim/feature-edge actor still outlines it.
        is_round_lens_like = bool(getattr(actor, "_kraken_round_lens_like_step_body", False))
        suppress_select_edges = is_file_backed_body or is_glassy_lens_body or is_round_lens_like
        if selected:
            # "Red + Pink translucent body when selected" -- the
            # face fill flips to pink; outlines flip to red. Two
            # sub-cases because the existing scene draws solid bodies
            # with a SEPARATE feature-edge actor alongside the body
            # mesh actor:
            try:
                if suppress_select_edges:
                    # Dense solid body -- a Solid 3D STL / promoted STEP
                    # solid (file-backed) OR a glassy analytic lens body
                    # (revolved drum, Standard cap, promoted-STEP body
                    # plate). Turning on triangle edges would paint a
                    # dense red wireframe across every triangle of the
                    # body, smothering the pink fill (the symptom
                    # reported on the penta prism and, for analytic
                    # lenses, bugs/0001: "selected become RED, not pink
                    # translucent"). Skip the mesh's triangle edges --
                    # the body's separate feature-edge / rim actor gets
                    # the same selection treatment via
                    # _set_row_actor_selected and provides a clean
                    # outline on its own.
                    prop.SetEdgeVisibility(0)
                    prop.SetLineWidth(float(base.get("line_width", 1.0)))
                else:
                    prop.SetEdgeVisibility(1)
                    prop.SetEdgeColor(1.0, 0.0, 0.0)  # bright red edges
                    prop.SetLineWidth(max(float(base.get("line_width", 1.0)), 5.0))
                # Pink body fill (1.0, 0.45, 0.65). Opacity is bumped
                # well above the baseline 0.68 so the pink reads
                # through other geometry without losing the body.
                prop.SetColor(1.0, 0.45, 0.65)
                prop.SetOpacity(max(float(base.get("opacity", 0.5)), 0.75))
                prop.SetAmbient(max(float(base.get("ambient", 0.0)), 0.35))
                prop.SetDiffuse(max(float(base.get("diffuse", 1.0)), 0.80))
            except Exception:
                pass
            return
        try:
            prop.SetEdgeVisibility(int(base.get("edge_visibility", 0)))
            edge_color = tuple(base.get("edge_color", (0.0, 0.0, 0.0)))
            if len(edge_color) == 3:
                prop.SetEdgeColor(*edge_color)
            prop.SetLineWidth(float(base.get("line_width", 1.0)))
            prop.SetOpacity(float(base.get("opacity", 1.0)))
            prop.SetAmbient(float(base.get("ambient", 0.0)))
            prop.SetDiffuse(float(base.get("diffuse", 1.0)))
            base_color = tuple(base.get("color", ()))
            if len(base_color) == 3:
                prop.SetColor(*base_color)
        except Exception:
            pass

    def _clear_ray_event_label_actors(self, *, render: bool = False) -> None:
        if self._renderer is not None:
            for actor in list(self._ray_event_label_actors):
                self._remove_renderer_view_prop(actor)
        self._ray_event_label_actors = []
        if render:
            self.render()

    def _add_renderer_view_prop(self, actor) -> None:
        if self._renderer is None or actor is None:
            return
        add_view_prop = getattr(self._renderer, "AddViewProp", None)
        if callable(add_view_prop):
            add_view_prop(actor)
            return
        try:
            self._renderer.AddActor(actor)
        except Exception:
            self._renderer.AddActor2D(actor)

    def _remove_renderer_view_prop(self, actor) -> None:
        if self._renderer is None or actor is None:
            return
        remove_view_prop = getattr(self._renderer, "RemoveViewProp", None)
        if callable(remove_view_prop):
            remove_view_prop(actor)
            return
        try:
            self._renderer.RemoveActor(actor)
        except Exception:
            try:
                self._renderer.RemoveActor2D(actor)
            except Exception:
                pass

    @staticmethod
    def _ray_event_world_point(event: object) -> np.ndarray | None:
        try:
            point = np.asarray(getattr(event, "point_world", np.full(3, np.nan)), dtype=float).reshape(-1)
        except Exception:
            return None
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return None
        return np.asarray(point[:3], dtype=float)

    def _add_selected_ray_event_label_actors(self, ray_index: int | None) -> None:
        if self._renderer is None or ray_index is None or vtkBillboardTextActor3D is None:
            return
        paths_by_ray_index = _layout_editor_class()._scene_ray_path_by_index(self._current_scene_bundle)
        path = paths_by_ray_index.get(int(ray_index))
        if path is None:
            return
        events = []
        for event in list(getattr(path, "events", []) or []):
            kind = str(getattr(event, "event_kind", "") or "").strip().lower()
            if kind not in {"surface", "terminal"}:
                continue
            label = ray_event_display_label(event)
            point = self._ray_event_world_point(event)
            if label and point is not None:
                events.append((label, point, kind))
        if not events:
            return
        terminal = [item for item in events if item[2] == "terminal"]
        surface = [item for item in events if item[2] != "terminal"]
        events = surface[:13] + terminal[:1]
        _scene_center, scene_span = self._scene_bounds()
        offset = max(float(scene_span) * 0.006, 0.18)
        for ordinal, (label, point, _kind) in enumerate(events):
            try:
                actor = vtkBillboardTextActor3D()
                actor.SetInput(str(label))
                displacement = np.array(
                    [
                        offset * (1.0 + 0.18 * (ordinal % 3)),
                        offset * (0.4 if ordinal % 2 else -0.4),
                        offset * 0.25,
                    ],
                    dtype=float,
                )
                label_point = point[:3] + displacement
                actor.SetPosition(float(label_point[0]), float(label_point[1]), float(label_point[2]))
                try:
                    actor.PickableOff()
                except Exception:
                    pass
                try:
                    text_prop = actor.GetTextProperty()
                    text_prop.SetFontSize(12)
                    text_prop.SetColor(0.04, 0.08, 0.16)
                    text_prop.SetBackgroundColor(1.0, 1.0, 1.0)
                    text_prop.SetBackgroundOpacity(0.74)
                    text_prop.SetFrame(1)
                    text_prop.SetFrameColor(0.96, 0.45, 0.05)
                except Exception:
                    pass
                self._renderer.AddActor(actor)
                self._ray_event_label_actors.append(actor)
            except Exception as exc:
                self.editor.append_debug(f"3D selected-ray label skipped: {exc}")
                return

    def _set_ray_highlight(self, ray_index: int | None) -> None:
        self._selection_representation.apply_ray_selection(ray_index)

    def _remove_optical_axis_highlight_actor(self) -> bool:
        actor = self._optical_axis_highlight_actor
        self._optical_axis_highlight_actor = None
        if actor is None or self._renderer is None:
            return False
        try:
            actor_key = self._actor_key(actor)
            if actor_key is not None:
                self._actor_by_key.pop(actor_key, None)
        except Exception:
            pass
        try:
            self._renderer.RemoveActor(actor)
            return True
        except Exception:
            return False

    def _set_optical_axis_highlight(self, axis_id: str | None) -> None:
        self._selection_representation.apply_optical_axis_selection(axis_id)

    def _add_mesh_actor(
        self,
        mesh,
        *,
        color: tuple[float, float, float],
        opacity: float = 1.0,
        pick_row_index: int | None = None,
        pick_step_label: str | None = None,
        pick_optical_axis: dict[str, object] | None = None,
        pick_step_rotate: tuple[str, str, float] | None = None,
        pick_step_translate: tuple[str, str, float] | None = None,
        pick_placement_move: tuple[int, str, float] | None = None,
        pick_placement_rotate: tuple[int, str, float] | None = None,
        pick_thickness_dimension: int | None = None,
        follow_step_label: str | None = None,
        track_row_index: int | None = None,
        line_width: float = 1.0,
        wireframe: bool = False,
        flat_shading: bool = False,
        backface_culling: bool = True,
        glassy: bool = False,
    ):
        if self._renderer is None or vtkActor is None or vtkDataSetMapper is None:
            return None
        mapper = vtkDataSetMapper()
        mapper.SetInputData(mesh)
        try:
            mapper.ScalarVisibilityOff()
        except Exception:
            pass
        actor = vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*color)
        prop.SetOpacity(opacity)
        prop.SetLineWidth(line_width)
        if wireframe:
            prop.SetRepresentationToWireframe()
        else:
            if flat_shading:
                prop.SetInterpolationToFlat()
                prop.SetSpecular(0.0)
                prop.SetDiffuse(0.15)
                prop.SetAmbient(0.85)
            elif glassy:
                # Glassy translucent: Phong with a strong narrow
                # highlight for the wet-glass sheen, plus enough
                # ambient/diffuse that thick curved bodies (a sphere,
                # a revolved lens drum) stay bright glass instead of
                # turning into a dark blob on their shadowed side.
                # Caller picks an opacity in the 0.25-0.45 range; this
                # routine only shapes how the visible fraction is lit.
                prop.SetInterpolationToPhong()
                prop.SetAmbient(0.30)
                prop.SetDiffuse(0.82)
                prop.SetSpecular(0.85)
                prop.SetSpecularPower(48.0)
                prop.SetSpecularColor(1.0, 1.0, 1.0)
            else:
                prop.SetInterpolationToPhong()
                prop.SetSpecular(0.18)
                prop.SetSpecularPower(12.0)
        if pick_step_label is not None or pick_row_index is not None or track_row_index is not None:
            try:
                actor._kraken_round_lens_like_step_body = bool(self._mesh_round_lens_axis(mesh) is not None)
            except Exception:
                actor._kraken_round_lens_like_step_body = False
        try:
            if backface_culling:
                prop.BackfaceCullingOn()
            else:
                prop.BackfaceCullingOff()
        except Exception:
            pass
        actor_key = self._actor_key(actor)
        if actor_key is not None:
            self._actor_by_key[actor_key] = actor
            if follow_step_label is not None:
                follow_label = str(follow_step_label).strip().lower()
                if follow_label:
                    self._actor_step_follow_map[actor_key] = follow_label
                    self._step_follow_actor_map.setdefault(follow_label, []).append(actor_key)
            tracked_row = pick_row_index if track_row_index is None else track_row_index
            if tracked_row is not None:
                try:
                    self._row_actor_map.setdefault(int(tracked_row), []).append(actor_key)
                except Exception:
                    pass
        if (
            pick_row_index is None
            and pick_step_label is None
            and pick_optical_axis is None
            and pick_step_rotate is None
            and pick_step_translate is None
            and pick_placement_move is None
            and pick_placement_rotate is None
            and pick_thickness_dimension is None
        ):
            actor.PickableOff()
        else:
            if actor_key is not None and pick_row_index is not None:
                self._actor_row_map[actor_key] = pick_row_index
            if actor_key is not None and pick_step_label is not None:
                step_label = str(pick_step_label)
                self._actor_step_map[actor_key] = step_label
                self._step_actor_map.setdefault(step_label, []).append(actor_key)
            if actor_key is not None and pick_optical_axis is not None:
                axis_info = dict(pick_optical_axis)
                axis_id = str(axis_info.get("axis_id", "") or "").strip()
                if axis_id:
                    self._actor_optical_axis_map[actor_key] = axis_info
                    self._optical_axis_actor_map.setdefault(axis_id, []).append(actor_key)
            if actor_key is not None and pick_step_rotate is not None:
                step_label, axis, delta_deg = pick_step_rotate
                self._actor_step_rotate_map[actor_key] = (str(step_label), str(axis), float(delta_deg))
            if actor_key is not None and pick_step_translate is not None:
                step_label, axis, delta_mm = pick_step_translate
                self._actor_step_translate_map[actor_key] = (str(step_label), str(axis), float(delta_mm))
            if actor_key is not None and pick_placement_move is not None:
                row_index, axis, delta_mm = pick_placement_move
                self._actor_placement_move_map[actor_key] = (int(row_index), str(axis), float(delta_mm))
            if actor_key is not None and pick_placement_rotate is not None:
                row_index, axis, delta_deg = pick_placement_rotate
                self._actor_placement_rotate_map[actor_key] = (int(row_index), str(axis), float(delta_deg))
            if actor_key is not None and pick_thickness_dimension is not None:
                self._register_thickness_dimension_actor(actor, int(pick_thickness_dimension))
        self._renderer.AddActor(actor)
        return actor

    @staticmethod
    def _lens_rim_circle_polyline(mesh, *, segments: int = 144):
        """Return the geometric rim circle of a *circular* lens body.

        A smooth revolved lens body (a sphere, a doublet drum) has no
        sharp feature edges, so feature-edge extraction leaves it without
        an outline. Its true edge is the rim: a real 3-D circle at the
        widest cross-section. Drawing that circle as geometry gives a
        view-independent outline that never disappears as the user orbits
        (unlike a view-dependent silhouette). Returns ``None`` when the
        cross-section is not actually circular (e.g. a square plano-cyl
        plate), so those keep their feature-edge outline instead.

        Tries the strict thin-disc detector first; if that rejects (a
        full sphere has minor/mid==1, a thick lens body has
        thickness/diameter>0.85), falls back to a permissive axis
        detector that still rejects elongated rods. The downstream
        circularity check below filters out rectangular cross-sections
        (the cyl plate) regardless of which detector found the axis.
        """
        if pv is None or mesh is None:
            return None
        info = Kraken3DInspector._mesh_round_lens_axis(mesh)
        if info is None:
            info = Kraken3DInspector._lens_rim_axis_loose(mesh)
        if info is None:
            return None
        center, axis, points = info
        try:
            center = np.asarray(center, dtype=float).reshape(3)
            axis = np.asarray(axis, dtype=float).reshape(3)
            points = np.asarray(points, dtype=float).reshape(-1, 3)
        except Exception:
            return None
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12 or points.shape[0] < 8:
            return None
        axis = axis / axis_norm
        centered = points - center
        proj = centered @ axis
        radial_vecs = centered - np.outer(proj, axis)
        radial = np.linalg.norm(radial_vecs, axis=1)
        rmax = float(np.percentile(radial, 97))
        if rmax <= 1e-9:
            return None
        # 0.8 picks up the rim of a thin revolved drum (the achromat
        # drum's side wall sits at radial == R, dominates the outer
        # band, std/mean tiny). A full sphere's surface points span
        # all radii smoothly, so 0.8 catches a wide band where radial
        # varies from 0.8 R to R and the circularity check below would
        # reject it. Try the wide band first to keep the disc path
        # unchanged, then tighten to 0.92 to admit spheres / thick
        # rotationally-symmetric bodies. The cyl plate's outer ring
        # still exceeds the circularity tolerance at both thresholds.
        outer = None
        ring_r = None
        for outer_threshold in (0.8, 0.92):
            candidate_mask = radial >= outer_threshold * rmax
            if not np.any(candidate_mask):
                continue
            candidate = radial[candidate_mask]
            candidate_mean = float(np.mean(candidate))
            if candidate_mean <= 1e-9:
                continue
            if float(np.std(candidate) / candidate_mean) <= 0.045:
                outer = candidate_mask
                ring_r = candidate
                break
        if outer is None or ring_r is None:
            return None
        ring_mean = float(np.mean(ring_r))
        radius = ring_mean
        rim_axial = float(np.mean(proj[outer]))
        rim_center = center + axis * rim_axial
        ref = np.array([1.0, 0.0, 0.0]) if abs(float(axis[0])) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = np.cross(axis, ref)
        u_norm = float(np.linalg.norm(u))
        if u_norm <= 1e-12:
            return None
        u = u / u_norm
        v = np.cross(axis, u)
        # Reject non-circular rims (e.g. the square plano-cyl plate). A
        # true circular rim spreads across every azimuth; a square's
        # outer band clusters at its four corners, leaving ~90deg gaps.
        # The radial-spread check above can be fooled by the corner-only
        # band at the tighter 0.92 threshold, so guard on angular gaps.
        ring_vecs = radial_vecs[outer]
        ang = np.sort(np.arctan2(ring_vecs @ v, ring_vecs @ u))
        if ang.shape[0] >= 8:
            gaps = np.diff(ang)
            wrap = (ang[0] + 2.0 * np.pi) - ang[-1]
            if float(max(float(np.max(gaps)), float(wrap))) > (np.pi / 4.0):
                return None
        theta = np.linspace(0.0, 2.0 * np.pi, int(segments), endpoint=False)
        circle = (
            rim_center[None, :]
            + radius * (np.cos(theta)[:, None] * u[None, :] + np.sin(theta)[:, None] * v[None, :])
        )
        lines = np.empty(int(segments) + 2, dtype=np.int64)
        lines[0] = int(segments) + 1
        lines[1 : 1 + int(segments)] = np.arange(int(segments), dtype=np.int64)
        lines[-1] = 0
        try:
            return pv.PolyData(circle, lines=lines)
        except Exception:
            return None

    def _register_thickness_dimension_actor(self, actor, row_index: int) -> None:
        actor_key = self._actor_key(actor)
        if actor_key is None:
            return
        self._actor_by_key[actor_key] = actor
        self._actor_thickness_dimension_map[actor_key] = int(row_index)
        self._thickness_dimension_actor_map.setdefault(int(row_index), []).append(actor_key)
        try:
            actor.PickableOn()
        except Exception:
            pass

    def _add_missing_asset_placeholder_actors(self, mesh, row_index: int) -> None:
        """Render the red wireframe placeholder for a missing-CAD row.

        Draws three actors:

        * A faint red translucent body so the row's footprint reads at a
          glance from any orbit angle (otherwise the wireframe alone
          would disappear into the background on a busy scene).
        * A bright red wireframe edge on top, so the row is impossible
          to mistake for a normal glassy lens.
        * Pull the row's surface descriptor into the picker map via the
          standard ``_add_mesh_actor`` path so the user can still click
          on the placeholder and see "this row references a missing CAD
          file" via the existing selection UI.

        We deliberately do not draw a rim circle or feature edges
        here: the placeholder is meant to look obviously wrong, not
        like a half-finished lens.
        """
        if pv is None or mesh is None:
            return
        placeholder_color = (0.92, 0.18, 0.22)
        try:
            body_actor = self._add_mesh_actor(
                mesh,
                color=placeholder_color,
                opacity=0.18,
                pick_row_index=row_index,
                follow_step_label=None,
                backface_culling=False,
            )
        except Exception:
            body_actor = None
        if body_actor is not None:
            try:
                body_actor._kraken_missing_asset_placeholder = True
            except Exception:
                pass
        try:
            edges = mesh.extract_feature_edges(
                feature_angle=10,
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
            )
        except Exception:
            edges = None
        if edges is not None and int(getattr(edges, "n_points", 0)) > 0:
            try:
                self._add_mesh_actor(
                    edges,
                    color=placeholder_color,
                    opacity=1.0,
                    line_width=2.4,
                    track_row_index=row_index,
                    follow_step_label=None,
                )
            except Exception:
                pass

    def _set_step_highlight(self, step_label: str | None, *, render: bool = True) -> None:
        self._selection_representation.apply_step_selection(step_label, render=render)

    def _set_step_highlight_set(self, labels, *, render: bool = True) -> None:
        self._selection_representation.apply_step_selection_set(labels, render=render)

    def _remove_step_rotation_handle_actors(self) -> bool:
        return self._open3d_step_rotation_handle_service().remove_actors()

    def _reconcile_step_rotation_handles(self, labels) -> None:
        visible = {
            str(label).strip().lower()
            for label in (labels or [])
            if str(label).strip() and not self.is_step_label_hidden(str(label).strip().lower())
        }
        self._open3d_step_rotation_handle_service().reconcile_to_labels(visible)

    def _step_rotation_handle_count_for_label(self, label: str) -> int:
        return self._open3d_step_rotation_handle_service().handle_count_for_label(label)

    def _step_label_has_visible_body_actor(self, label: str) -> bool:
        label = str(label or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return False
        # bugs/0027: a hidden element's body actor still exists (SetVisibility 0),
        # so existence alone wrongly let the rotation gizmo pop up on select.
        if self.is_step_label_hidden(label):
            return False
        for actor_key in list(self._step_actor_map.get(label, []) or []):
            if actor_key in self._actor_step_rotate_map or actor_key in self._actor_step_rotate_visual_keys:
                continue
            if self._actor_by_key.get(actor_key) is not None:
                return True
        return False

    def _ensure_step_rotation_handles_for_label(self, label: str) -> int:
        if self.is_step_label_hidden(label):  # bugs/0027: no gizmo on a hidden element
            return 0
        return self._open3d_step_rotation_handle_service().ensure_for_label(label)

    def _remove_placement_rotation_handle_actors(self) -> bool:
        if self._renderer is None:
            return False
        removed = False
        placement_keys = set(self._actor_placement_rotate_map)
        placement_keys.update(self._actor_placement_move_map)
        placement_keys.update(self._actor_placement_rotate_visual_keys)
        placement_keys.update(self._actor_placement_move_visual_keys)
        for actor_key in list(placement_keys):
            actor = self._actor_by_key.pop(actor_key, None)
            self._actor_placement_rotate_map.pop(actor_key, None)
            self._actor_placement_move_map.pop(actor_key, None)
            self._actor_placement_rotate_visual_keys.discard(actor_key)
            self._actor_placement_move_visual_keys.discard(actor_key)
            if actor is None:
                continue
            try:
                self._renderer.RemoveActor(actor)
                removed = True
            except Exception:
                pass
        return removed

    def _show_rotation_handles(self) -> bool:
        try:
            return bool(self.show_rotation_handles_var.get())
        except Exception:
            return True

    def _stl_placement_panel_visible(self) -> bool:
        popup = getattr(self, "_stl_placement_popup", None)
        if popup is None:
            return False
        try:
            return bool(popup.winfo_exists())
        except Exception:
            return False

    def _show_scene_placement_handles(self) -> bool:
        try:
            if bool(self.show_placement_handles_var.get()):
                return True
        except Exception:
            pass
        picked_row_index = getattr(self, "_picked_row_index", None)
        selected_handle_row_index = getattr(self, "_placement_handle_selected_row_index", None)
        try:
            active_row_index = (
                int(picked_row_index)
                if picked_row_index is not None
                else (int(selected_handle_row_index) if selected_handle_row_index is not None else None)
            )
            row_eligible = False
            if active_row_index is not None and 0 <= active_row_index < len(self.editor.rows):
                if self.editor._file_backed_stl_row_at(active_row_index) is not None:
                    row_eligible = True
                else:
                    row_eligible = bool(
                        self.editor._is_any_promoted_optical_solid_row(self.editor.rows[active_row_index])
                    )
            picked_row_has_handles = bool(row_eligible and self._show_rotation_handles())
        except Exception:
            picked_row_has_handles = False
        return bool(
            self._stl_placement_panel_visible()
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or picked_row_has_handles
            or self._placement_drag_state is not None
            or self._row_carry_drag_state is not None
        )

    def _toggle_rotation_handles(self) -> None:
        if self._show_rotation_handles():
            self.refresh_from_editor()
            self.status_var.set("Rotation handles shown.")
            return
        removed = self._remove_step_rotation_handle_actors()
        removed = self._remove_placement_rotation_handle_actors() or removed
        self.status_var.set("Rotation handles hidden.")
        if removed:
            self.render()

    def _rotation_handle_step_deg(self) -> float:
        try:
            value = float(str(self.rotation_step_deg_var.get()).strip())
        except Exception:
            value = 90.0
        if not np.isfinite(value) or value <= 0.0:
            value = 90.0
        value = float(np.clip(abs(value), 1.0, 180.0))
        normalized = f"{value:.0f}" if abs(value - round(value)) < 1e-9 else f"{value:.6g}"
        try:
            if str(self.rotation_step_deg_var.get()).strip() != normalized:
                self.rotation_step_deg_var.set(normalized)
        except Exception:
            pass
        return value

    def _on_rotation_step_changed(self, *_args) -> None:
        step = self._rotation_handle_step_deg()
        if self._show_rotation_handles():
            self.refresh_from_editor()
        self.status_var.set(f"Rotation handles set to +/-{step:.6g} deg.")

    def _clear_open3d_selection(self, *, render: bool = True) -> bool:
        token = self._timing_start("clear_open3d_selection", render=bool(render))
        changed = False
        try:
            try:
                if getattr(self.editor, "_selected_step_label", None) is not None:
                    self.editor._selected_step_label = None
                    changed = True
            except Exception:
                pass
            panel = getattr(self, "_open3d_step_admin_panel_instance", None)
            if panel is not None:
                try:
                    panel.clear_selection(update_properties=False)
                    changed = True
                except Exception as exc:
                    self.editor.append_debug(f"Open 3D STEP admin clear failed: {exc}")
            for attr_name in (
                "_selected_step_feature",
                "_selected_step_feature_label",
                "_selected_step_feature_center_world",
                "_selected_step_feature_surface_center_world",
                "_selected_step_feature_normal_world",
            ):
                if getattr(self, attr_name, None) is not None:
                    setattr(self, attr_name, None)
                    changed = True
            if self._step_rotation_active_label is not None:
                self._close_step_rotation_handler()
                changed = True
            self._set_step_hover_outline(None, None, render=False)
            if self._picked_step_label is not None:
                self._set_step_highlight(None, render=False)
                changed = True
            if self._picked_row_index is not None:
                self._set_row_highlight(None)
                changed = True
            if self._placement_handle_selected_row_index is not None:
                self._placement_handle_selected_row_index = None
                changed = True
            if self._picked_ray_index is not None:
                self._set_ray_highlight(None)
                changed = True
            if self._picked_optical_axis_id is not None:
                self._set_optical_axis_highlight(None)
                changed = True
            if self._remove_step_rotation_handle_actors():
                changed = True
            if self._remove_placement_rotation_handle_actors():
                changed = True
            if changed and render:
                self.render()
            return changed
        finally:
            self._timing_finish(token, changed=bool(changed))

    def clear_face_metadata_hover_state(self, row_index: int | None = None) -> None:
        """Drop transient hover/selection state after CAD face metadata changes."""
        try:
            self._set_step_hover_outline(None, None, render=False)
        except Exception:
            pass
        try:
            self._update_hover_status("", render=False)
        except Exception:
            pass
        try:
            self._step_feature_cache.clear()
        except Exception:
            pass
        try:
            self._cad_scene_cache.clear()
        except Exception:
            pass
        self._hover_step_actor = None
        self._hover_step_cell_key = None
        self._hover_rotation_handle_key = None
        if row_index is None or self._picked_row_index == int(row_index):
            self._set_row_highlight(None)
        self._set_ray_highlight(None)
        self._set_optical_axis_highlight(None)
        self._set_axis_pick_cursor(False)

    def _step_rotation_status_text(self, label: str) -> str:
        label = str(label).strip().lower()
        display = self.editor._step_overlay_display_label(label).upper()
        return (
            f"{display} STEP | "
            f"X={self.editor._step_x_rotation_deg(label):.0f} deg, "
            f"Y={self.editor._step_y_rotation_deg(label):.0f} deg, "
            f"Z={self.editor._step_roll_deg(label):.0f} deg"
        )

    def select_step_overlay_from_admin(self, label: str, *, additive: bool = False) -> bool:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            display = self.editor._step_overlay_display_label(label) if label else "STEP"
            self.status_var.set(f"No imported {display} STEP is available.")
            self.refresh_step_admin_panel()
            return False
        self.editor.select_step_component(label)
        display = self.editor._step_overlay_display_label(label).upper()
        # bugs/0027: a hidden element must not pop up the rotation gizmo when
        # selected from the browser -- you can't manipulate what you can't see.
        # Select for properties only (no highlight, no handles).
        if self.is_step_label_hidden(label):
            # bugs/0049: a Shift+click (additive) on a hidden row must leave the
            # live multi-select intact -- only a plain pick clears it.
            if not additive:
                self._step_rotation_active_label = None
                self._set_step_highlight(None, render=False)
                try:
                    self._close_step_rotation_handler()
                except Exception:
                    pass
            self.refresh_step_admin_panel()
            self.status_var.set(f"{display} STEP is hidden — right-click ▸ Unhide to edit it.")
            try:
                self.render()
            except Exception:
                pass
            return True
        # bugs/0049: Shift+click toggles the overlay into the rotation-gizmo
        # multi-select set (mirrors the 3D canvas); a plain click single-selects.
        if not additive:
            self._step_rotation_active_label = label
            self._set_step_highlight(label, render=False)
        self.show_step_rotation_handler(label, additive=additive)
        self.refresh_step_admin_panel()
        path = self.editor._step_path_for_label(label)
        name = Path(path).name if path is not None else label.upper()
        self.status_var.set(f"Selected {display} STEP: {name}.")
        return True

    def select_promoted_step_row_from_admin(self, row_index: int) -> bool:
        try:
            row_index = int(row_index)
        except Exception:
            row_index = -1
        rows = list(getattr(self.editor, "rows", []) or [])
        if row_index < 0 or row_index >= len(rows):
            self.status_var.set("No promoted STEP row is available.")
            self.refresh_step_admin_panel()
            return False
        row = rows[row_index]
        if not self.editor._is_open3d_promoted_optical_solid_row(row):
            self.status_var.set(f"S{row_index} is not a promoted STEP optical-solid row.")
            self.refresh_step_admin_panel()
            return False
        self.editor._selected_step_label = None
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_rotation_active_label = None
        self._close_step_rotation_handler()
        self._set_step_highlight(None, render=False)
        self.editor._select_table_indices([row_index], focus_index=row_index)
        self.editor._sync_surface_selection(row_index)
        self._stl_placement_row_index = row_index
        self.highlight_row(row_index)
        self.refresh_step_admin_panel()
        self.status_var.set(f"Selected promoted STEP row S{row_index}: {getattr(row, 'name', '') or 'optical solid'}.")
        return True

    def select_scene_row_from_admin(self, row_index: int) -> bool:
        try:
            row_index = int(row_index)
        except Exception:
            row_index = -1
        rows = list(getattr(self.editor, "rows", []) or [])
        if row_index < 0 or row_index >= len(rows):
            self.status_var.set("No editable-table scene row is available.")
            self.refresh_step_admin_panel()
            return False
        row_actor_map = getattr(self, "_row_actor_map", {}) or {}
        if row_index not in row_actor_map and str(row_index) not in row_actor_map:
            self.status_var.set(f"S{row_index} is not currently drawn in Open 3D.")
            self.refresh_step_admin_panel()
            return False
        row = rows[row_index]
        self.editor._selected_step_label = None
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_rotation_active_label = None
        self._close_step_rotation_handler()
        self._set_step_highlight(None, render=False)
        self.editor._select_table_indices([row_index], focus_index=row_index)
        self.editor._sync_surface_selection(row_index)
        self._stl_placement_row_index = row_index if self.editor._file_backed_stl_row_at(row_index) is not None else None
        self.highlight_row(row_index)
        self.refresh_step_admin_panel()
        self.status_var.set(f"Selected scene row S{row_index}: {getattr(row, 'name', '') or getattr(row, 'surface', '') or 'surface'}.")
        return True

    def select_scene_element_from_admin(self, start_index: int, end_index: int) -> bool:
        try:
            start_index = int(start_index)
            end_index = int(end_index)
        except Exception:
            self.status_var.set("No editable-table scene element is available.")
            self.refresh_step_admin_panel()
            return False
        if end_index < start_index:
            start_index, end_index = end_index, start_index
        rows = list(getattr(self.editor, "rows", []) or [])
        row_actor_map = getattr(self, "_row_actor_map", {}) or {}
        visible_indices: list[int] = []
        for row_index in range(start_index, end_index + 1):
            if row_index < 0 or row_index >= len(rows):
                continue
            if row_index in row_actor_map or str(row_index) in row_actor_map:
                visible_indices.append(row_index)
        if not visible_indices:
            self.status_var.set("No visible editable-table rows are available for that scene element.")
            self.refresh_step_admin_panel()
            return False
        first_index = visible_indices[0]
        first_row = rows[first_index]
        self.editor._selected_step_label = None
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_rotation_active_label = None
        self._close_step_rotation_handler()
        self._set_step_highlight(None, render=False)
        self.editor._select_table_indices(visible_indices, focus_index=first_index)
        self.editor._sync_surface_selection(first_index)
        self._stl_placement_row_index = None
        self.highlight_rows(visible_indices)
        self.refresh_step_admin_panel()
        try:
            label = str(self.editor._element_key(first_row) or "").strip()
        except Exception:
            label = str(getattr(first_row, "element", "") or "").strip()
        if not label:
            label = getattr(first_row, "name", "") or getattr(first_row, "surface", "") or "element"
        self.status_var.set(
            f"Selected scene element {label}: S{visible_indices[0]}-S{visible_indices[-1]} "
            f"({len(visible_indices)} visible surface rows)."
        )
        return True

    def import_step_overlay(self, label: str) -> None:
        label = str(label).strip().lower()
        token = self._timing_start("import_step_overlay", label=label)
        importers = {
            "lens": self.editor.import_lens_step,
            "camera": self.editor.import_camera_step,
            "led": self.editor.import_led_step,
        }
        importer = importers.get(label)
        if importer is None:
            self._timing_finish(token, status="no_importer")
            return
        try:
            path = importer(dialog_parent=self, refresh_open_3d=False)
            if path is None:
                self.status_var.set(self.editor.status_var.get())
                self._timing_finish(token, status="cancelled")
                return
            self.editor.select_step_component(label)
            self._step_rotation_active_label = label
            self._step_carry_active_label = label
            self._step_carry_follow_state = None
            self._step_carry_snap_ray_mode = False
            self._step_carry_snap_target_mode = False
            self._step_normal_axis_pick_mode = False
            self._step_surface_center_axis_pick_mode = False
            self._step_carry_grid_label = None
            self._step_carry_grid_spacing_mm = None
            self._selected_step_feature = None
            self._selected_step_feature_label = None
            self._selected_step_feature_center_world = None
            self._selected_step_feature_surface_center_world = None
            self._selected_step_feature_normal_world = None
            self.refresh_from_editor()
            self.show_step_rotation_handler(label)
            self.status_var.set(
                f"{label.upper()} STEP imported: {path.name}. Hold the STEP briefly to lift; "
                "drag freely, release to drop. Click a face and use Snap STEP Normal->Optical Axis for alignment."
            )
            self.refresh_step_admin_panel()
        except Exception as exc:
            self._timing_finish(token, status="error", error=_short_error_message(exc))
            raise
        else:
            self._timing_finish(token, status="ok", path=str(path))

    def import_optical_step_overlay(self) -> None:
        had_existing_overlay = self.editor._step_path_for_label("optical") is not None
        token = self._timing_start("import_optical_step_overlay", had_existing_overlay=bool(had_existing_overlay))
        try:
            path = self.editor.import_optical_step(dialog_parent=self, refresh_open_3d=False)
            if path is None:
                self.status_var.set(self.editor.status_var.get())
                self._timing_finish(token, status="cancelled")
                return
            label = "optical"
            self.editor.select_step_component(label)
            self._step_rotation_active_label = label
            # Mark the carry as active *before* the refresh so the
            # scene's placement-handle gate (in scene_refresh) sees a
            # live carry label and hides the placement handles of any
            # previously promoted optical-solid row. Otherwise the
            # prior row keeps its placement handles in the carry view
            # and the user has to interact with stale UI on top of
            # the just-imported STEP. `_start_step_carry_follow` below
            # finalizes the follow state; if it fails for any reason
            # it resets the label to None. We intentionally leave
            # `_picked_row_index` alone -- clearing it forces the prior
            # row's actor to redraw in its "not picked" wireframe style,
            # which surprises users who see the selected element
            # suddenly change color.
            self._step_carry_active_label = label
            self._step_carry_follow_state = None
            self._step_carry_snap_ray_mode = False
            self._step_carry_snap_target_mode = False
            self._step_normal_axis_pick_mode = False
            self._step_surface_center_axis_pick_mode = False
            self._step_carry_grid_label = None
            self._step_carry_grid_spacing_mm = None
            self._selected_step_feature = None
            self._selected_step_feature_label = None
            self._selected_step_feature_center_world = None
            self._selected_step_feature_surface_center_world = None
            self._selected_step_feature_normal_world = None
            self.refresh_from_editor()
            self.show_step_rotation_handler(label)
            self._start_step_carry_follow(label)
            kept_note = (
                " The previous optical STEP was kept as a promoted optical-solid row."
                if had_existing_overlay
                else ""
            )
            self.status_var.set(
                f"Optical STEP imported: {path.name}. Move the cursor to carry it, click to drop.{kept_note} "
                "Click a face and use Snap STEP Normal->Optical Axis for alignment."
            )
            self.refresh_step_admin_panel()
        except Exception as exc:
            self._timing_finish(token, status="error", error=_short_error_message(exc))
            raise
        else:
            self._timing_finish(token, status="ok", path=str(path))

    def clear_step_imports(self) -> None:
        self.editor.clear_step_imports()
        self._close_step_rotation_handler()
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._row_carry_drag_state = None
        self._cancel_row_carry_hold_timer()
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        self._selected_step_feature = None
        self._selected_step_feature_label = None
        self._selected_step_feature_center_world = None
        self._selected_step_feature_surface_center_world = None
        self._selected_step_feature_normal_world = None
        self._open3d_carry_grip_service.clear(render=False)
        self._set_step_carry_cursor(False)
        self.refresh_from_editor()
        self.status_var.set("Camera/lens/optical/LED STEP imports cleared.")
        self.refresh_step_admin_panel()

    def delete_selected_step(self) -> None:
        """Delete the currently selected imported STEP element.

        Removes a single un-promoted STEP overlay (one of the four import
        slots), or the selected promoted STEP optical-solid row(s), without
        clearing the other STEP imports the way ``Clear STEP Imports`` does.
        """
        service = self.editor._open3d_step_state_service()
        candidate_indices = set(int(index) for index in self.editor._selected_table_indices())
        for candidate in (
            self._picked_row_index,
            self._stl_placement_row_index,
            self._row_carry_hold_candidate_index,
        ):
            if candidate is None:
                continue
            try:
                candidate_indices.add(int(candidate))
            except Exception:
                pass
        selection = service.resolve_delete_selection(
            import_label_candidates=self._delete_target_import_label_candidates(),
            row_index_candidates=sorted(candidate_indices),
        )
        label = selection.import_label
        if label:
            display = self.editor._step_overlay_display_label(label).upper()
            self.editor._begin_history_capture()
            self.editor._clear_imported_step_overlay_state(label)
            self.editor._commit_history_capture()
            self._close_step_rotation_handler()
            self._clear_step_overlay_interaction_state(label)
            self._step_carry_active_label = None
            self._step_carry_follow_state = None
            self._row_carry_drag_state = None
            self._cancel_row_carry_hold_timer()
            self._step_carry_snap_ray_mode = False
            self._step_carry_snap_target_mode = False
            self._step_normal_axis_pick_mode = False
            self._step_surface_center_axis_pick_mode = False
            self._step_carry_grid_label = None
            self._step_carry_grid_spacing_mm = None
            self._selected_step_feature = None
            self._selected_step_feature_label = None
            self._selected_step_feature_center_world = None
            self._selected_step_feature_surface_center_world = None
            self._selected_step_feature_normal_world = None
            self._open3d_carry_grip_service.clear(render=False)
            self._set_step_carry_cursor(False)
            self.editor._live_step_overlay_trace_plan_cache = {}
            self.refresh_from_editor(force_retrace=True)
            self.status_var.set(f"Deleted imported {display} STEP overlay.")
            return
        removed = self.editor.delete_optical_step_rows(selection.row_indices)
        if removed > 0:
            self._picked_row_index = None
            self._picked_row_indices = set()
            self._stl_placement_row_index = None
            self._row_carry_drag_state = None
            self._row_carry_hold_candidate_index = None
            self._cancel_row_carry_hold_timer()
            self.refresh_from_editor(force_retrace=True)
            self.status_var.set(
                f"Deleted {removed} promoted STEP optical-solid "
                f"row{'s' if removed != 1 else ''}."
            )
            return
        self.status_var.set(
            "Delete STEP: select an imported STEP overlay or a promoted "
            "STEP optical-solid row first."
        )

    def _delete_selected_step_event(self, _event=None) -> str:
        try:
            focused = self.focus_get()
        except Exception:
            focused = None
        if isinstance(focused, (ttk.Entry, ttk.Combobox, ttk.Spinbox, tk.Entry, tk.Spinbox, tk.Text)):
            return ""
        self.delete_selected_step()
        return "break"

    def _selected_imported_step_label_candidates(self) -> tuple[object, ...]:
        return (
            self.editor._selected_step_label,
            self._step_rotation_active_label,
            self._step_carry_active_label,
            "optical",
        )

    def _delete_target_import_label_candidates(self) -> tuple[object, ...]:
        # Delete must only target an overlay the user has actually selected or is
        # actively manipulating -- never the bare "optical" fallback used by the
        # non-destructive carry/promote resolvers. With the fallback, a stray
        # Delete/BackSpace in the 3D view (the VTK key handler has no focus guard)
        # silently removed the imported optical lens even with nothing selected.
        return (
            self.editor._selected_step_label,
            self._step_rotation_active_label,
            self._step_carry_active_label,
        )

    def _selected_imported_step_label(self) -> str:
        return self.editor._open3d_step_state_service().selected_import_label(
            self._selected_imported_step_label_candidates()
        )

    def _promote_step_overlay_to_optical_solid_row(
        self,
        label: str,
        *,
        open_face_editor: bool,
        action_label: str,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if is_step_overlay_decoration(label):
            # LED source / camera body are decorations, not optical elements --
            # never promote them into an optical mesh-solid (their heavy CAD
            # would be ray-traced and stall the non-seq trace).
            display = self.editor._step_overlay_display_label(label).upper()
            self.status_var.set(
                f"{display} STEP is a decoration and cannot be promoted to an optical element."
            )
            self._debug_trace(
                "step_overlay_promote_to_row_decoration_blocked",
                label=label,
                action_label=action_label,
            )
            return None
        self._debug_trace(
            "step_overlay_promote_to_row",
            label=label,
            action_label=action_label,
            open_face_editor=bool(open_face_editor),
            counts_before=self._debug_actor_counts(),
        )
        try:
            transition = self.editor._open3d_step_state_service().promote_imported_overlay_to_row(
                label,
                open_face_editor=bool(open_face_editor),
                action_label=action_label,
                # bugs/0079: a UI "Promote to Optical Element" of an on-axis
                # in-path solid places it at its true axial slot (gap-split,
                # lens/image fixed) so its faces refract for the t(1-1/n) focus
                # shift instead of its raw thickness shoving the detector.
                inpath_axial_placement=True,
            )
        except ValueError as exc:
            self.status_var.set(str(exc))
            self._debug_trace("step_overlay_promote_to_row_no_target", label=label, status=str(exc))
            return None
        except Exception as exc:
            self.status_var.set(f"{action_label} STEP failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D STEP {action_label.lower()} failed: {exc}")
            self._debug_trace("step_overlay_promote_to_row_failed", label=label, error=_short_error_message(exc))
            return None
        if transition is None:
            self.status_var.set(self.editor.status_var.get())
            self._debug_trace("step_overlay_promote_to_row_no_result", label=label, status=self.editor.status_var.get())
            return None
        result = transition.raw_result
        self._stl_placement_dirty = True
        self._clear_step_overlay_interaction_state(transition.label)
        row_index = int(transition.row_index)
        try:
            # bugs/0105: a promoted optical-solid row makes every later refresh
            # force a full branched physics retrace (~90s on a beam-splitter
            # scene). Clamp THIS forced retrace to a sparse 3-ray fan so the
            # promote lands fast; the override is cleared below so the next
            # explicit trace restores full ray density. Only the displayed ray
            # COUNT changes -- geometry, branch detectors and the reconciled
            # prescription are unaffected.
            self.editor._promote_preview_ray_count_override = 3
            try:
                self.refresh_from_editor(force_retrace=True)
            finally:
                self.editor._promote_preview_ray_count_override = None
            if row_index >= 0:
                self.highlight_row(row_index)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D STEP {action_label.lower()} refresh failed: {exc}")
        self._debug_trace(
            "step_overlay_promote_to_row_done",
            label=transition.label,
            row_index=row_index,
            action_label=action_label,
            counts_after=self._debug_actor_counts(),
        )
        return result

    def accept_selected_step_placement(self) -> None:
        label = self._selected_imported_step_label()
        result = self._promote_step_overlay_to_optical_solid_row(
            label,
            open_face_editor=False,
            action_label="Accept",
        )
        if result is None:
            return
        row_index = int(result.get("row_index", -1))
        path = Path(str(result.get("mesh_path", "")))
        self.status_var.set(
            f"Accepted {label.upper()} STEP placement as optical solid row S{row_index}: {path.name}. "
            "Hold the promoted solid to move it; use right-click face assignment or Faces before tracing final physics."
        )

    def glue_selected_step_to_surrogate(self) -> None:
        """Re-apply the automatic optical-surrogate glue to the selected STEP
        overlay (clear manual drags so a lens re-centres on its CAD cylinder axis
        / the camera sensor returns to the Image plane / the LED to its object
        station).  Available on the CAD menu and the canvas right-click."""
        label = self._selected_imported_step_label()
        if not label:
            self.status_var.set("Select or import a STEP overlay to glue to its optical surrogate.")
            return
        changed = self.editor.glue_step_overlay_to_surrogate(label)
        # For the lens, also "improve the surrogate" (item 4): the front datum is pinned by the
        # alignment; this glues the REAR datum onto the STEP rear face so the surrogate span matches
        # the vendor CAD (optics + image preserved).
        if str(label).strip().lower() == "lens":
            try:
                if self.editor.improve_lens_surrogate_rear_to_step():
                    changed = True
            except Exception as exc:
                self.editor.append_debug(f"Improve lens surrogate rear datum failed: {exc}")
        self.status_var.set(self.editor.status_var.get())
        if changed:
            try:
                self.refresh_from_editor(force_retrace=True)
            except Exception as exc:
                self.editor.append_debug(f"Glue STEP to surrogate refresh failed: {exc}")

    def promote_selected_step_to_optical_solid_row(self) -> None:
        label = self._selected_imported_step_label()
        result = self._promote_step_overlay_to_optical_solid_row(
            label,
            open_face_editor=True,
            action_label="Promote",
        )
        if result is None:
            return
        row_index = int(result.get("row_index", -1))
        path = Path(str(result.get("mesh_path", "")))
        self.status_var.set(
            f"Promoted {label.upper()} STEP to optical solid row S{row_index}: {path.name}. "
            "Hold the promoted solid to move it; assign optical faces/material, then Update to trace it."
        )

    def _native_step_material_sequence_prompt(self, label: str) -> str | None:
        display_label = self.editor._step_overlay_display_label(label)
        try:
            return simpledialog.askstring(
                "Native STEP Materials",
                (
                    f"Glass/material sequence after each native {display_label} STEP surface.\n"
                    "Example for a cemented achromat: BK7, F2, AIR"
                ),
                initialvalue="BK7, F2, AIR",
                parent=self,
            )
        except Exception:
            return None

    def promote_selected_step_to_native_surface_rows(self, glass_sequence: object | None = None) -> dict[str, object] | None:
        label = self._selected_imported_step_label()
        if not label:
            self.status_var.set("Select or import a STEP overlay before native promotion.")
            return None
        if glass_sequence is None:
            glass_sequence = self._native_step_material_sequence_prompt(label)
        if glass_sequence is None or not str(glass_sequence).strip():
            self.status_var.set("Native STEP promotion cancelled; material sequence is required.")
            return None
        self._debug_trace("step_overlay_promote_to_native_rows", label=label, counts_before=self._debug_actor_counts())
        try:
            result = self.editor.promote_imported_step_to_native_surface_rows(
                label,
                glass_sequence=glass_sequence,
                clear_overlay=True,
                refresh_open_3d=False,
            )
        except Exception as exc:
            self.status_var.set(f"Native STEP promotion failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D native STEP promotion failed: {exc}")
            self._debug_trace("step_overlay_promote_to_native_rows_failed", label=label, error=_short_error_message(exc))
            return None
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            self._debug_trace("step_overlay_promote_to_native_rows_no_result", label=label, status=self.editor.status_var.get())
            return None
        row_indices = [int(value) for value in list(result.get("row_indices", []) or [])]
        self._stl_placement_dirty = True
        self._clear_step_overlay_interaction_state(label)
        try:
            self.refresh_from_editor(force_retrace=True)
            if row_indices:
                self.highlight_row(row_indices[0])
        except Exception as exc:
            self.editor.append_debug(f"Open 3D native STEP promotion refresh failed: {exc}")
        self.status_var.set(
            f"Promoted {label.upper()} STEP to native analytic rows "
            f"{row_indices[0]}-{row_indices[-1] if row_indices else '?'}."
        )
        self._debug_trace(
            "step_overlay_promote_to_native_rows_done",
            label=label,
            row_indices=row_indices,
            counts_after=self._debug_actor_counts(),
        )
        return result

    def _chain_exit_direction_from_trace(self) -> tuple[float, float, float] | None:
        """Probe the current trace for the chief ray's last-segment direction.

        Used by ``promote_selected_step_to_analytic_surfaces`` so the
        emitted analytic rows automatically align with the upstream
        beam direction -- in particular the folded exit beam of a
        prism cascade. When the scene has no rays or no folded path,
        returns ``None`` and the promote service falls back to the
        un-tilted (along +Z) default.
        """
        bundle = self._current_scene_bundle
        if bundle is None:
            return None
        paths = list(getattr(bundle, "ray_paths", []) or [])
        if not paths:
            return None
        # Pick the chief ray: smallest launch-radius from the source.
        def _start_radius(path) -> float:
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 3:
                return float("inf")
            return float(np.hypot(pts[0, 0], pts[0, 1]))

        chief = min(paths, key=_start_radius)
        pts = np.asarray(getattr(chief, "points_world", np.empty((0, 3))), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            return None
        # Last-segment direction. If the trace runs straight along +Z
        # (no folds), this returns (0,0,1) and the promote service
        # naturally falls through to chain_tilt=(0,0,0). Real cascade
        # folds return (-1,0,0) etc. (within snap tolerance).
        seg = pts[-1] - pts[-2]
        norm = float(np.linalg.norm(seg))
        if not np.isfinite(norm) or norm <= 1e-9:
            return None
        d = seg / norm
        return (float(d[0]), float(d[1]), float(d[2]))

    def _analytic_step_material_sequence_prompt(
        self,
        label: str,
        preview: dict,
    ) -> str | None:
        """Show the geometry-fit preview and ask for the glass sequence.

        Some optical components are cemented compounds (an achromat
        doublet has 3 spherical surfaces and 2 glass types), so the
        prompt shows the user exactly how many glasses are expected
        and includes the fitted Rc / thickness for each surface so
        they can confirm the detection looks right before committing.
        """
        display_label = self.editor._step_overlay_display_label(label)
        rows = list(preview.get("rows") or [])
        required = int(preview.get("required_glass_count", 1))
        if not rows:
            return None
        lines = [
            f"{display_label.upper()} STEP -> analytic surfaces",
            "",
            "Fitted surfaces (front -> back):",
        ]
        for index, row in enumerate(rows):
            kind = str(row.get("kind", "surface"))
            rc = float(row.get("rc_mm", 0.0))
            diameter = float(row.get("diameter_mm", 0.0))
            thickness = float(row.get("thickness_mm", 0.0))
            residual = float(row.get("residual_mm", 0.0))
            if kind == "sphere":
                rc_text = f"Rc = {rc:+.4f} mm"
            else:
                rc_text = "Rc = inf (planar)"
            lines.append(
                f"  S{index + 1}  {kind:6s}  {rc_text}  Diameter = {diameter:.2f} mm  "
                f"-> next: {thickness:.3f} mm  (fit residual {residual:.4f} mm)"
            )
        lines.append("")
        if required == 1:
            example = "N-BK7"
            descr = "one glass for this singlet"
        elif required == 2:
            example = "N-BAF10, N-SF10"
            descr = "two glasses for this cemented doublet"
        elif required == 3:
            example = "N-BAF10, N-SF10, N-LAK9"
            descr = "three glasses for this cemented triplet"
        else:
            example = ", ".join(["N-BK7"] * required)
            descr = f"{required} glasses (one per region between adjacent surfaces)"
        lines.append(f"Glass sequence ({descr}). Example: {example}")
        # Pre-fill from a Zemax (.zmx) prescription sidecar next to the
        # source STEP when present (matched to the region count). This is
        # the same convenience the import-time prompt used to offer, now
        # on the explicit promote action so import can stay carry-first.
        initial = example
        try:
            source_path = self.editor._step_path_for_label(label)
            if source_path is not None:
                from KrakenOS.UI.services.step_overlay_import import _parse_zemax_glass_sequence

                sidecars = self.editor._step_overlay_import_service()._optical_prescription_sidecars(source_path)
                for sidecar in sidecars:
                    if sidecar.suffix.lower() != ".zmx":
                        continue
                    parsed = _parse_zemax_glass_sequence(sidecar)
                    if parsed:
                        initial = ", ".join(parsed[:required])
                        lines.append(f"(Pre-filled from sidecar {sidecar.name}.)")
                        break
        except Exception:
            initial = example
        lines.append("(The trailing region after the back surface is set to AIR automatically.)")
        message = "\n".join(lines)
        try:
            return simpledialog.askstring(
                "Promote STEP to Analytic Surfaces",
                message,
                initialvalue=initial,
                parent=self,
            )
        except Exception:
            return None

    def promote_selected_step_to_analytic_surfaces(
        self,
        glass_sequence: object | None = None,
    ) -> dict[str, object] | None:
        """Promote the selected STEP overlay to analytic Standard rows.

        Geometry-only path: sphere/plane fit on every preserved face
        marked Transmit/Port by the auto-assignment heuristic. The
        user only provides the glass material(s); everything else
        (Rc, thickness, diameter) is fit from the mesh, so this works
        on STL imports as well as STEP files.
        """
        label = self._selected_imported_step_label()
        if not label:
            self.status_var.set(
                "Select or import a STEP overlay before analytic promotion."
            )
            return None
        try:
            preview = self.editor.preview_imported_step_analytic_surfaces(label)
        except Exception as exc:
            self.status_var.set(f"Analytic STEP preview failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D analytic STEP preview failed: {exc}")
            return None
        if preview is None:
            self.status_var.set(
                "Analytic STEP promotion: could not auto-detect a front/back "
                "optical pair. Try the Promote STEP to Optical Solid Row path or "
                "assign faces manually via Faces..."
            )
            return None
        if glass_sequence is None:
            glass_sequence = self._analytic_step_material_sequence_prompt(label, preview)
        if glass_sequence is None or not str(glass_sequence).strip():
            self.status_var.set("Analytic STEP promotion cancelled; glass sequence is required.")
            return None
        # Probe the live trace for the chain's exit direction so the
        # promoted rows align with the cascade-folded beam (if any).
        # Returns None for an un-folded chain -> promote service
        # uses its default along +Z, preserving the standalone case.
        chain_exit_direction = self._chain_exit_direction_from_trace()
        try:
            result = self.editor.promote_imported_step_to_analytic_surfaces(
                label,
                glass_sequence=glass_sequence,
                clear_overlay=True,
                refresh_open_3d=False,
                chain_exit_direction=chain_exit_direction,
            )
        except Exception as exc:
            self.status_var.set(f"Analytic STEP promotion failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D analytic STEP promotion failed: {exc}")
            return None
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return None
        row_indices = [int(v) for v in (result.get("row_indices") or [])]
        self._stl_placement_dirty = True
        self._clear_step_overlay_interaction_state(label)
        try:
            self.refresh_from_editor(force_retrace=True)
            if row_indices:
                self.highlight_row(row_indices[0])
        except Exception as exc:
            self.editor.append_debug(f"Open 3D analytic STEP promotion refresh failed: {exc}")
        return result

    def start_selected_step_carry(self) -> None:
        transition = self.editor._open3d_step_state_service().resolve_carry_start(
            (self.editor._selected_step_label, self._step_rotation_active_label),
        )
        if not transition.has_label:
            self.status_var.set(transition.status)
            return
        label = transition.label
        self._step_carry_active_label = label
        self._step_carry_follow_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        self.editor.select_step_component(label)
        self.refresh_from_editor()
        self.show_step_rotation_handler(label)
        self.status_var.set(transition.status)

    def _step_feature_action_selection(
        self,
        *,
        label: str | None = None,
        require_pick_point: bool = True,
        require_surface_center: bool = False,
        require_normal: bool = False,
    ) -> StepFeatureSelection | None:
        service = self.editor._open3d_step_state_service()
        return service.selected_feature_action(
            self._selected_step_feature,
            label_candidates=(
                label,
                self._selected_step_feature_label,
                self.editor._selected_step_label,
                self._step_rotation_active_label,
                self._step_carry_active_label,
            ),
            require_pick_point=require_pick_point,
            require_surface_center=require_surface_center,
            require_normal=require_normal,
        )

    def _clear_selected_step_feature_state(self) -> None:
        self._selected_step_feature = None
        self._selected_step_feature_label = None
        self._selected_step_feature_center_world = None
        self._selected_step_feature_surface_center_world = None
        self._selected_step_feature_normal_world = None

    def snap_selected_step_normal_to_optical_axis(self) -> None:
        """Default snap-to-axis variant: lens body lands where you click.

        Evolution of the default anchor:
        - first iteration: ``surface_center`` -- face centroid lands on
          axis click. The body still extended to one side and didn't
          look "at the click" to the user.
        - second iteration: ``pick_point`` -- the exact spot on the
          face went to the click. Same visual mismatch: the body sat
          to one side, not centered on the cursor.
        - current default: ``body_center`` -- the STEP body centroid
          lands at the cursor world point on the axis, so the lens
          visually lands where the user clicked. Dedicated menu
          entries below preserve the pick-point and surface-center
          variants for users who need either.
        """
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label(
            (
                self._selected_step_feature_label,
                self.editor._selected_step_label,
                self._step_rotation_active_label,
                self._step_carry_active_label,
            )
        )
        if not label:
            self.status_var.set("Snap STEP Normal->Optical Axis: select or import a STEP component first.")
            return
        if self._step_feature_action_selection(label=label, require_pick_point=True, require_normal=True) is None:
            self.status_var.set("Snap STEP Normal->Optical Axis: click a planar STEP face first.")
            return
        self.start_step_normal_axis_pick(label, anchor_mode="body_center")

    def snap_selected_step_pick_point_normal_to_optical_axis(self) -> None:
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label(
            (
                self._selected_step_feature_label,
                self.editor._selected_step_label,
                self._step_rotation_active_label,
                self._step_carry_active_label,
            )
        )
        if not label:
            self.status_var.set("Snap Pick Point Normal->Optical Axis: select or import a STEP component first.")
            return
        if self._step_feature_action_selection(label=label, require_pick_point=True, require_normal=True) is None:
            self.status_var.set("Snap Pick Point Normal->Optical Axis: click a planar STEP face first.")
            return
        self.start_step_normal_axis_pick(label, anchor_mode="pick_point")

    def center_selected_step_surface_to_optical_axis(self) -> None:
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label(
            (
                self._selected_step_feature_label,
                self.editor._selected_step_label,
                self._step_rotation_active_label,
                self._step_carry_active_label,
            )
        )
        if not label:
            self.status_var.set("Center Surface->Optical Axis: select or import a STEP component first.")
            return
        if self._step_feature_action_selection(label=label, require_surface_center=True) is None:
            self.status_var.set("Center Surface->Optical Axis: click a planar STEP face first.")
            return
        self.start_step_surface_center_axis_pick(label)

    def orient_selected_step_face_to_direction(self, direction_label: str) -> None:
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label(
            (
                self._selected_step_feature_label,
                self.editor._selected_step_label,
                self._step_rotation_active_label,
                self._step_carry_active_label,
            )
        )
        if not label:
            self.status_var.set("STEP Face Direction: select or import a STEP component first.")
            return
        selection = self._step_feature_action_selection(
            label=label,
            require_surface_center=True,
            require_normal=True,
        )
        if selection is None:
            self.status_var.set("STEP Face Direction: click a planar STEP face first.")
            return
        try:
            result = self.editor.orient_step_feature_normal_to_direction(
                label,
                selection.surface_center_world,
                selection.normal_world,
                direction_label,
                face_id=selection.face_id,
            )
        except Exception as exc:
            self.status_var.set(f"STEP Face Direction failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D STEP face-direction alignment failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        target_direction = result.get("target_direction", ())
        surface_center = result.get("surface_center", selection.surface_center_world)
        updated = service.step_feature_selection(
            label,
            (surface_center, object(), target_direction),
            surface_center_world=surface_center,
            face_id=selection.face_id,
        )
        if updated is not None:
            self._selected_step_feature = updated
            self._selected_step_feature_label = updated.label
            self._selected_step_feature_center_world = updated.pick_point_world
            self._selected_step_feature_surface_center_world = updated.surface_center_world
            self._selected_step_feature_normal_world = updated.normal_world
        self._step_rotation_active_label = label
        try:
            self.refresh_from_editor()
            self.show_step_rotation_handler(label)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D STEP face-direction refresh failed: {exc}")
        angle_error = float(result.get("angle_error_deg", float("nan")))
        self.status_var.set(
            f"{label.upper()} STEP face normal set to {str(direction_label).strip().title()} "
            f"(error {angle_error:.6g} deg)."
        )

    def _step_body_center_world(self, label: str) -> np.ndarray | None:
        """World-space centroid of an imported STEP body, current pose.

        Used by the `body_center` anchor mode of the snap-to-axis
        workflow so the *body* of the imported lens lands at the
        cursor world point, not just the clicked face. Returns None
        if the live mesh isn't available.
        """
        try:
            mesh = self.editor._transformed_imported_step_mesh_for_label(str(label))
        except Exception:
            return None
        if mesh is None or int(getattr(mesh, "n_points", 0) or 0) <= 0:
            return None
        try:
            pts = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        except Exception:
            pts = np.empty((0, 3), dtype=float)
        if pts.ndim == 2 and pts.shape[0] >= 1 and pts.shape[1] >= 3:
            finite = pts[np.all(np.isfinite(pts[:, :3]), axis=1)]
            if finite.size:
                return np.asarray(finite[:, :3].mean(axis=0), dtype=float).reshape(3)
        # Fall back to bounding-box center if point cloud isn't usable.
        try:
            b = np.asarray(getattr(mesh, "bounds", None), dtype=float).reshape(-1)
        except Exception:
            return None
        if b.size != 6 or not np.all(np.isfinite(b)):
            return None
        return np.asarray(
            [
                0.5 * (b[0] + b[1]),
                0.5 * (b[2] + b[3]),
                0.5 * (b[4] + b[5]),
            ],
            dtype=float,
        )

    def start_step_normal_axis_pick(self, label: str | None = None, *, anchor_mode: str = "body_center") -> None:
        """Arm the click-the-axis-to-snap state machine.

        ``anchor_mode`` controls which point on the STEP lands at the
        cursor world target on the optical axis:

        - ``"body_center"`` (default): the STEP body centroid. The lens
          visually lands where the cursor is. This matches the user's
          intuition of "click here, lens goes here".
        - ``"surface_center"``: the clicked face's centroid lands on
          the axis click. Lens body extends to one side.
        - ``"pick_point"``: the exact point you clicked on the face
          lands on the axis click. Useful for edge-precise alignment.
        """
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label((label, self._selected_step_feature_label))
        if not label:
            self.status_var.set("Snap STEP Normal->Optical Axis: select or import a STEP component first.")
            return
        mode_text = str(anchor_mode).strip().lower()
        if mode_text == "pick_point":
            anchor_mode = "pick_point"
        elif mode_text == "body_center":
            anchor_mode = "body_center"
        else:
            anchor_mode = "surface_center"
        selection = self._step_feature_action_selection(
            label=label,
            require_pick_point=True,
            require_surface_center=(anchor_mode == "surface_center"),
            require_normal=True,
        )
        if selection is None:
            self.status_var.set("Snap STEP Normal->Optical Axis: click a planar STEP face first.")
            return
        self._step_normal_axis_pick_mode = True
        self._step_normal_axis_anchor_mode = anchor_mode
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_follow_state = None
        self._step_carry_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_orient_pick_mode = False
        self._placement_orient_ray_mode = False
        self._set_step_carry_cursor(False)
        self._set_axis_pick_cursor(True)
        self._update_mode_badge()
        self._hide_regular_rays_for_center_axis_pick()
        if anchor_mode == "body_center":
            coordinate = self._step_body_center_world(label)
            anchor_text = "body center"
        elif anchor_mode == "surface_center":
            coordinate = selection.surface_center_world
            anchor_text = "surface center"
        else:
            coordinate = selection.pick_point_world
            anchor_text = "picked point"
        self.status_var.set(
            f"Snap {label.upper()} STEP normal using {anchor_text}: click the dotted Optical Axis guide. "
            f"Anchor={self._world_xyz_text(coordinate)}."
        )

    def start_step_surface_center_axis_pick(self, label: str | None = None) -> None:
        service = self.editor._open3d_step_state_service()
        label = service.selected_import_label((label, self._selected_step_feature_label))
        if not label:
            self.status_var.set("Center Surface->Optical Axis: select or import a STEP component first.")
            return
        selection = self._step_feature_action_selection(label=label, require_surface_center=True)
        if selection is None:
            self.status_var.set("Center Surface->Optical Axis: click a planar STEP face first.")
            return
        self._step_surface_center_axis_pick_mode = True
        self._step_normal_axis_pick_mode = False
        self._step_carry_follow_state = None
        self._step_carry_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_orient_pick_mode = False
        self._placement_orient_ray_mode = False
        self._set_step_carry_cursor(False)
        self._set_axis_pick_cursor(True)
        self._update_mode_badge()
        self._hide_regular_rays_for_center_axis_pick()
        center_text = self._world_xyz_text(selection.surface_center_world)
        self.status_var.set(
            f"Center {label.upper()} STEP surface: click the dotted Optical Axis guide. Surface center={center_text}."
        )

    def _apply_step_normal_axis_pick(self, axis_info: dict[str, object]) -> None:
        mode_text = str(getattr(self, "_step_normal_axis_anchor_mode", "body_center")).strip().lower()
        if mode_text == "pick_point":
            anchor_mode = "pick_point"
        elif mode_text == "surface_center":
            anchor_mode = "surface_center"
        else:
            anchor_mode = "body_center"
        selection = self._step_feature_action_selection(
            require_pick_point=True,
            require_surface_center=(anchor_mode == "surface_center"),
            require_normal=True,
        )
        if selection is None:
            self.status_var.set("Snap STEP Normal->Optical Axis: click a planar STEP face first.")
            return
        label = selection.label
        if anchor_mode == "body_center":
            center = self._step_body_center_world(label)
            if center is None:
                # No live mesh -- fall back to face centroid so we still
                # snap rather than refusing.
                center = selection.surface_center_world
                anchor_mode = "surface_center"
        elif anchor_mode == "pick_point":
            center = selection.pick_point_world
        else:
            center = selection.surface_center_world
        normal = selection.normal_world
        try:
            if anchor_mode == "surface_center" and str(getattr(selection, "face_id", "") or "").strip():
                result = self.editor.snap_step_overlay_face_to_optical_axis(
                    label,
                    axis_info,
                    face_id=str(selection.face_id).strip(),
                )
                axis_frame = None
            else:
                axis_frame = self._optical_axis_frame_from_pick(axis_info, self._picker)
                if axis_frame is None:
                    self.status_var.set("Snap STEP Normal->Optical Axis: could not resolve the clicked optical axis.")
                    return
                result = self.editor.snap_step_feature_normal_to_optical_axis(label, center, normal, axis_frame=axis_frame)
        except Exception as exc:
            self.status_var.set(f"Snap STEP Normal->Optical Axis failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D STEP normal-axis snap failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._step_normal_axis_pick_mode = False
        self._step_normal_axis_anchor_mode = "body_center"
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._clear_selected_step_feature_state()
        # Clear the editor-side STEP selection so the post-snap refresh
        # doesn't re-add the rotation handles the user just escaped from.
        # The Open 3D scene refresh auto-pops rotation handles whenever a
        # STEP overlay is "selected"; without clearing this, the handles
        # silently reappear after every snap success ("rotation handles
        # pop up after previous action").
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        self._step_rotation_active_label = None
        self._set_axis_pick_cursor(False)
        self._set_optical_axis_highlight(None)
        try:
            restore_rays = self._restore_rays_after_step_axis_pick(label)
            self.refresh_from_editor(force_retrace=restore_rays)
            axis_id = str(axis_info.get("axis_id", "") or "").strip()
            if axis_id:
                self._set_optical_axis_highlight(axis_id)
        except Exception as exc:
            self.editor.append_debug(f"3D STEP normal-axis snap refresh failed: {exc}")
        # Defensive sweep: a Tk event handler or live-refresh callback can
        # fire during the next update_idletasks pump and re-select the
        # snapped STEP, which silently re-adds the rotation handles we
        # just cleared. Clear again at the end so the inspector's
        # post-snap state is stable, including actively removing any
        # rotation-handle actors that survived the refresh.
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        self._step_rotation_active_label = None
        try:
            if self._remove_step_rotation_handle_actors():
                self.render()
        except Exception:
            pass
        # Drop the admin panel's remembered overlay row so the next
        # `refresh_step_admin_panel` can't restore an `overlay:<label>`
        # selection that re-fires <<TreeviewSelect>> and re-adds rotation
        # handles. The admin refresh also guards on
        # `editor._selected_step_label`, but clearing here keeps the
        # snap-side state explicit.
        try:
            admin = getattr(self, "_open3d_step_admin_panel_instance", None)
            if admin is not None:
                admin.clear_selection(update_properties=False)
        except Exception:
            pass
        axis_label = str(result.get("axis_label", "optical axis"))
        angle_error = float(result.get("angle_error_deg", float("nan")))
        if anchor_mode == "body_center":
            anchor_text = "body center"
        elif anchor_mode == "pick_point":
            anchor_text = "picked point"
        else:
            anchor_text = "surface center"
        self.status_var.set(
            f"{label.upper()} STEP face normal snapped to {axis_label} using {anchor_text} "
            f"(error {angle_error:.6g} deg). Use 'Step rotation handles' in the toolbar if you need to flip."
        )

    def _apply_step_surface_center_axis_pick(self, axis_info: dict[str, object]) -> None:
        selection = self._step_feature_action_selection(require_surface_center=True)
        if selection is None:
            self.status_var.set("Center Surface->Optical Axis: click a planar STEP face first.")
            return
        label = selection.label
        surface_center = selection.surface_center_world
        axis_frame = self._optical_axis_frame_from_pick(axis_info, self._picker)
        if axis_frame is None:
            self.status_var.set("Center Surface->Optical Axis: could not resolve the clicked optical axis.")
            return
        try:
            center = np.asarray(surface_center, dtype=float).reshape(-1)[:3]
            target = np.asarray(axis_frame["target_point"], dtype=float).reshape(-1)[:3]
        except Exception:
            self.status_var.set("Center Surface->Optical Axis: invalid surface center or axis target.")
            return
        if center.size < 3 or target.size < 3 or not np.all(np.isfinite(center[:3])) or not np.all(np.isfinite(target[:3])):
            self.status_var.set("Center Surface->Optical Axis: invalid surface center or axis target.")
            return
        delta = target[:3] - center[:3]
        try:
            self.editor.translate_step_overlay(label, delta[:3], refresh=False)
            self.editor._record_step_overlay_axis_anchor(
                label,
                face_id=str(getattr(selection, "face_id", "") or "").strip(),
                target_point=target[:3],
                anchor_mode="surface_center",
                axis_frame=axis_frame,
                source="surface_center_axis_snap",
            )
        except Exception as exc:
            self.status_var.set(f"Center Surface->Optical Axis failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D STEP surface-center axis snap failed: {exc}")
            return
        self._step_carry_active_label = None
        self._step_carry_follow_state = None
        self._step_surface_center_axis_pick_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._clear_selected_step_feature_state()
        # See _apply_step_normal_axis_pick: clear the editor-side
        # selection so the post-snap refresh stops re-adding rotation
        # handles around the just-snapped STEP overlay.
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        self._step_rotation_active_label = None
        self._set_axis_pick_cursor(False)
        self._set_optical_axis_highlight(None)
        try:
            restore_rays = self._restore_rays_after_step_axis_pick(label)
            self.refresh_from_editor(force_retrace=restore_rays)
            axis_id = str(axis_info.get("axis_id", "") or "").strip()
            if axis_id:
                self._set_optical_axis_highlight(axis_id)
        except Exception as exc:
            self.editor.append_debug(f"3D STEP surface-center axis snap refresh failed: {exc}")
        # See _apply_step_normal_axis_pick: defensive sweep so refresh
        # callbacks can't re-add rotation handles after the snap.
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        self._step_rotation_active_label = None
        try:
            if self._remove_step_rotation_handle_actors():
                self.render()
        except Exception:
            pass
        # See `_apply_step_normal_axis_pick`: the admin tree's remembered
        # overlay row would otherwise re-fire <<TreeviewSelect>> on the
        # next refresh and silently re-add the rotation handles.
        try:
            admin = getattr(self, "_open3d_step_admin_panel_instance", None)
            if admin is not None:
                admin.clear_selection(update_properties=False)
        except Exception:
            pass
        axis_label = str(axis_frame.get("axis_label", axis_info.get("axis_label", "Optical Axis")) or "Optical Axis")
        self.status_var.set(
            f"{label.upper()} STEP surface center moved to {axis_label}: "
            f"center {self._world_xyz_text(center)} -> target {self._world_xyz_text(target)}. "
            "Use 'Step rotation handles' in the toolbar if you need to flip."
        )

    def _center_row_axis_pick_message(self) -> str:
        if self._center_row_to_ray_index is None:
            return "Center Row->Optical Axis: click the surface/CAD row to move first."
        return "Center Row->Optical Axis: click the dotted Optical Axis guide."

    def _optical_axis_pick_mode_active(self) -> bool:
        return bool(
            self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or (self._center_row_to_ray_mode and self._center_row_to_ray_index is not None)
        )

    def _should_draw_optical_axis_overlays(self) -> bool:
        return True

    def _hide_regular_rays_for_center_axis_pick(self) -> None:
        try:
            showing_rays = bool(self.show_rays_var.get())
            self._show_rays_before_axis_pick = showing_rays
            if showing_rays:
                self.show_rays_var.set(False)
            self.refresh_from_editor()
        except Exception as exc:
            self.editor.append_debug(f"Center Row->Optical Axis ray-hide refresh failed: {exc}")

    def _restore_rays_after_step_axis_pick(self, label: str) -> bool:
        """Restore ray visibility after an axis pick and mark STEP physics-ready."""
        self.editor._open3d_trace_refresh_service().mark_step_overlay_physics_preview_ready(label)
        restore_rays = bool(getattr(self, "_show_rays_before_axis_pick", False))
        self._show_rays_before_axis_pick = False
        if restore_rays:
            self.show_rays_var.set(True)
        return restore_rays

    def _mouse_move_due(self) -> bool:
        now = time.monotonic()
        if now - float(self._mouse_move_last_ts) < float(self._mouse_move_min_interval_s):
            return False
        self._mouse_move_last_ts = now
        return True

    def _center_row_pick_row_ignoring_axis_overlays(self, x: float, y: float) -> int | None:
        pick = self._center_axis_source_pick_ignoring_axis_overlays(x, y)
        row_index = pick.get("row_index") if pick is not None else None
        if row_index is None:
            return None
        return int(row_index)

    def _center_axis_source_pick_ignoring_axis_overlays(self, x: float, y: float) -> dict[str, object] | None:
        if self._renderer is None or self._picker is None:
            return None
        disabled: list[object] = []
        try:
            blocking_keys = set(self._actor_optical_axis_map)
            blocking_keys.update(self._actor_ray_map)
            blocking_keys.update(self._actor_step_rotate_map)
            blocking_keys.update(self._actor_step_rotate_visual_keys)
            blocking_keys.update(self._actor_placement_move_map)
            blocking_keys.update(self._actor_placement_rotate_map)
            blocking_keys.update(self._actor_thickness_dimension_map)
            for actor_key in blocking_keys:
                actor = self._actor_by_key.get(actor_key)
                if actor is None:
                    continue
                try:
                    if int(actor.GetPickable()):
                        actor.PickableOff()
                        disabled.append(actor)
                except Exception:
                    continue
            self._picker.Pick(float(x), float(y), 0.0, self._renderer)
            actor = self._picker.GetActor()
            actor_key = self._actor_key(actor)
            row_index = self._actor_row_map.get(actor_key) if actor_key is not None else None
            step_label = self._actor_step_map.get(actor_key) if actor_key is not None else None
            try:
                cell_id = int(self._picker.GetCellId())
            except Exception:
                cell_id = -1
            try:
                pick_world = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            except Exception:
                pick_world = np.asarray([], dtype=float)
            result = {
                "actor": actor,
                "actor_key": actor_key,
                "row_index": int(row_index) if row_index is not None else None,
                "step_label": str(step_label) if step_label is not None else None,
                "cell_id": int(cell_id),
                "pick_world": pick_world,
            }
            if result["row_index"] is not None:
                row_pick = self._row_face_ray_pick_for_display_xy(int(result["row_index"]), (x, y))
                if row_pick is not None:
                    result["row_face_pick"] = row_pick
            if result["step_label"] is None:
                row_any = self._row_face_pick_any_for_display_xy((x, y))
                if isinstance(row_any, dict):
                    result["row_index"] = int(row_any["row_index"])
                    result["row_face_pick"] = row_any["row_face_pick"]
                    result["row_pick_screen_delta"] = float(row_any.get("screen_delta", float("inf")))
            if result["step_label"] is not None:
                feature_pick = self._step_feature_pick_for_display_xy(
                    str(result["step_label"]),
                    (x, y),
                    actor=actor,
                    actor_key=str(actor_key) if actor_key else None,
                    cell_id=int(cell_id),
                )
                if isinstance(feature_pick, dict):
                    result["feature_pick"] = feature_pick
            if result["row_index"] is None and result["step_label"] is None:
                for disabled_actor in disabled:
                    try:
                        disabled_actor.PickableOn()
                    except Exception:
                        pass
                disabled.clear()
                fallback = self._step_feature_pick_any_for_display_xy((x, y))
                if fallback is not None:
                    result["step_label"] = str(fallback.get("label"))
                    result["feature_pick"] = fallback.get("feature_pick")
                    result["cell_id"] = -1
            return result
        except Exception:
            return None
        finally:
            for actor in disabled:
                try:
                    actor.PickableOn()
                except Exception:
                    pass

    def _row_face_pick_any_for_display_xy(self, display_xy) -> dict[str, object] | None:
        """Pick the most intentional CAD/STL row face through a display ray.

        VTK actor picking returns the nearest prop, which is unstable for
        translucent overlapping prisms and lenses. Center Row workflows need
        the face the cursor is aimed at, so rank row-face ray hits by the
        projected face anchor before falling back to ray distance.
        """
        try:
            cursor = np.asarray(display_xy, dtype=float).reshape(-1)[:2]
        except Exception:
            return None
        if cursor.size < 2 or not np.all(np.isfinite(cursor[:2])):
            return None
        candidates: list[tuple[float, float, int, FaceRayPick]] = []
        for row_index in range(len(self.editor.rows)):
            try:
                if self.editor._file_backed_stl_row_at(int(row_index)) is None:
                    continue
            except Exception:
                continue
            try:
                pick = self._row_face_ray_pick_for_display_xy(int(row_index), cursor)
            except Exception:
                pick = None
            if pick is None:
                continue
            screen_delta = float("inf")
            try:
                center = self._surface_center_from_face_ray_pick(pick)
                display = self._world_to_display_2d(center)
                if display is not None:
                    delta = np.asarray(display[:2], dtype=float) - cursor[:2]
                    screen_delta = float(np.linalg.norm(delta[:2]))
            except Exception:
                screen_delta = float("inf")
            distance = float(getattr(pick, "distance", float("inf")))
            if not np.isfinite(distance):
                distance = float("inf")
            candidates.append((screen_delta, distance, int(row_index), pick))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        screen_delta, distance, row_index, pick = candidates[0]
        return {
            "row_index": int(row_index),
            "row_face_pick": pick,
            "screen_delta": float(screen_delta),
            "distance": float(distance),
        }

    def _step_pick_label_order(self, labels=None) -> list[str]:
        ordered: list[str] = []

        def add(label) -> None:
            value = str(label or "").strip().lower()
            if value and value in STEP_OVERLAY_LABEL_SET and value not in ordered:
                ordered.append(value)

        if labels is not None:
            try:
                for label in labels:
                    add(label)
            except TypeError:
                add(labels)
        add(getattr(self.editor, "_selected_step_label", None))
        add(getattr(self, "_picked_step_label", None))
        add(getattr(self, "_step_rotation_active_label", None))
        add(self._step_carry_label())
        for label in STEP_OVERLAY_LABELS:
            add(label)
        return ordered

    def _live_step_body_world_bounds(self, label):
        """Union world bounds of the LIVE rendered step body actors for ``label``.

        Returns ``(xmin, xmax, ymin, ymax, zmin, zmax)`` or ``None`` when no
        body actor is drawn for the label. Used by the camera-ray fallback pick
        to reject a metadata hit stranded off the rendered body (bugs/0085).
        """
        label = str(label or "").strip().lower()
        actor_map = getattr(self, "_step_actor_map", None)
        actor_keys = actor_map.get(label) if isinstance(actor_map, dict) else None
        if not actor_keys:
            return None
        by_key = getattr(self, "_actor_by_key", None)
        if not isinstance(by_key, dict):
            return None
        bmin = [float("inf")] * 3
        bmax = [float("-inf")] * 3
        found = False
        for actor_key in list(actor_keys):
            actor = by_key.get(actor_key) or by_key.get(str(actor_key))
            if actor is None:
                continue
            try:
                ab = [float(v) for v in actor.GetBounds()[:6]]
            except Exception:
                continue
            if len(ab) < 6 or any(ab[i] > ab[i + 1] for i in (0, 2, 4)):
                continue
            bmin[0] = min(bmin[0], ab[0]); bmax[0] = max(bmax[0], ab[1])
            bmin[1] = min(bmin[1], ab[2]); bmax[1] = max(bmax[1], ab[3])
            bmin[2] = min(bmin[2], ab[4]); bmax[2] = max(bmax[2], ab[5])
            found = True
        if not found:
            return None
        return (bmin[0], bmax[0], bmin[1], bmax[1], bmin[2], bmax[2])

    def _step_fallback_hit_on_live_body(self, label, feature_pick, feature) -> bool:
        """True if a camera-ray fallback pick lands on the rendered body (bugs/0085).

        The fallback reads pose-baked metadata, so when a live-trace overlay's
        display has snapped to its on-axis trace station but the drag offset is
        still in the metadata, the highlighted face floats off the drawn body.
        Only reject when a live body exists AND the face is clearly outside it (a
        few mm of margin tolerates surface-edge hits + the hover view-offset
        nudge); if we cannot resolve a body or a face location, default to
        keeping the pick so translucent-back-face coverage is never lost.

        Discriminate on the face CENTROID (``surface_center``), not the ray hit
        point: a large stale face can partially overlap the on-axis body, so the
        ray hit lands inside the overlap and passes while the outline still
        floats off-body (bugs/0086 -- the post-pivot ghost 0085 missed). The
        centroid is the representative location of the highlighted outline.
        """
        bounds = self._live_step_body_world_bounds(label)
        if bounds is None:
            return True
        hit = None
        if isinstance(feature_pick, dict):
            hit = feature_pick.get("surface_center")
        if hit is None:
            through_pick = feature_pick.get("through_pick") if isinstance(feature_pick, dict) else None
            if through_pick is not None:
                hit = getattr(through_pick, "point_world", None)
        if hit is None and feature is not None:
            try:
                hit = feature[0]
            except Exception:
                hit = None
        if hit is None:
            return True
        try:
            point = np.asarray(hit, dtype=float).reshape(-1)[:3]
        except Exception:
            return True
        if point.size < 3 or not np.all(np.isfinite(point)):
            return True
        span = max(
            bounds[1] - bounds[0],
            bounds[3] - bounds[2],
            bounds[5] - bounds[4],
            1.0,
        )
        margin = max(2.0, 0.05 * float(span))
        return (
            bounds[0] - margin <= point[0] <= bounds[1] + margin
            and bounds[2] - margin <= point[1] <= bounds[3] + margin
            and bounds[4] - margin <= point[2] <= bounds[5] + margin
        )

    def _step_feature_pick_any_for_display_xy(self, display_xy, labels=None) -> dict[str, object] | None:
        """Pick an imported STEP face by display ray, even when VTK returns no actor.

        Transparent prisms can show back/slanted faces that the VTK prop picker
        will not report as the picked actor. The face-aware picker works from
        the camera ray and STEP face metadata, so use it as the coverage
        fallback for hover, click selection, and axis-snap workflows.
        """
        candidates: list[tuple[float, int, str, dict[str, object]]] = []
        for order, label in enumerate(self._step_pick_label_order(labels)):
            if self.is_step_label_hidden(label):
                continue
            try:
                if self.editor._step_path_for_label(label) is None:
                    continue
            except Exception:
                continue
            try:
                feature_pick = self._step_feature_pick_for_display_xy(
                    label,
                    display_xy,
                    actor=None,
                    actor_key=None,
                    cell_id=-1,
                )
            except Exception:
                feature_pick = None
            if not isinstance(feature_pick, dict):
                continue
            feature = feature_pick.get("feature")
            if feature is None:
                continue
            through_pick = feature_pick.get("through_pick")
            # bugs/0085: this fallback fires even when VTK reports no actor,
            # reading pose-baked face metadata rather than the rendered body.
            # When a live-trace overlay's DISPLAY snaps to its on-axis trace
            # station while the manual drag offset still lives in the metadata
            # (the "beam splitter snaps back to axis" flow), the two desync and
            # a hit lands where no body is drawn -- a stranded gold "ghost"
            # selection highlight above the on-axis body. Reject any fallback
            # hit that falls outside the LIVE rendered body so the highlight
            # always reflects what is actually on screen. A genuine hover over
            # the body (incl. a translucent prism's far/internal face) stays
            # inside the body bounds and is unaffected.
            if not self._step_fallback_hit_on_live_body(label, feature_pick, feature):
                continue
            distance = float(order)
            if through_pick is not None:
                try:
                    distance = float(through_pick.distance)
                except Exception:
                    distance = float(order)
            if not np.isfinite(distance):
                distance = float(order)
            candidates.append((float(distance), int(order), label, feature_pick))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[1]))
        _distance, _order, label, feature_pick = candidates[0]
        return {"label": label, "feature_pick": feature_pick}

    def start_step_carry_snap_ray(self) -> None:
        label = str(self.editor._selected_step_label or self._step_rotation_active_label or self._step_carry_active_label or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            self.status_var.set("Snap STEP->Ray: select or import a lens, optical, camera, or LED STEP first.")
            return
        self._step_carry_active_label = label
        self._step_carry_follow_state = None
        self._step_carry_drag_state = None
        self._step_carry_snap_ray_mode = True
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self.editor._cad_axis_pick_any = False
        self.editor._cad_axis_pick_label = None
        self.editor._cad_led_object_edge_pick = False
        self.editor.select_step_component(label)
        self._set_axis_pick_cursor(True)
        self._update_mode_badge()
        self.status_var.set(f"Snap {label.upper()} STEP->Ray: click a traced ray to place the STEP center on that 3D point.")

    def start_step_carry_snap_target(self) -> None:
        label = str(self.editor._selected_step_label or self._step_rotation_active_label or self._step_carry_active_label or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            self.status_var.set("Snap STEP->Target: select or import a lens, optical, camera, or LED STEP first.")
            return
        self._step_carry_active_label = label
        self._step_carry_follow_state = None
        self._step_carry_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = True
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self.editor._cad_axis_pick_any = False
        self.editor._cad_axis_pick_label = None
        self.editor._cad_led_object_edge_pick = False
        self.editor.select_step_component(label)
        self._set_axis_pick_cursor(True)
        self._update_mode_badge()
        self.status_var.set(
            f"Snap {label.upper()} STEP->Target: click a detector/object/active target row or CAD/STL face anchor."
        )

    def stop_step_carry(self) -> None:
        label = self._step_carry_active_label
        self._cancel_step_carry_hold_timer()
        self._cancel_row_carry_hold_timer()
        try:
            self.editor._commit_history_capture()
        except Exception:
            pass
        self._step_carry_active_label = None
        self._step_carry_drag_state = None
        self._step_carry_follow_state = None
        self._row_carry_drag_state = None
        self._axis_slide_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        self._set_step_carry_cursor(False)
        self._open3d_carry_grip_service.clear(render=False)
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()
        self.refresh_from_editor()
        self.status_var.set(self.editor._open3d_step_state_service().carry_drop_status(label))

    def _active_3d_operation_labels(self) -> list[str]:
        labels: list[str] = []
        if self._step_carry_active_label is not None or self._step_carry_follow_state is not None:
            labels.append("STEP carry")
        if self._step_carry_snap_ray_mode:
            labels.append("STEP snap ray")
        if self._step_carry_snap_target_mode:
            labels.append("STEP snap target")
        if self._dimension_anchor_pick_mode:
            labels.append("dimension re-anchor")
        if self._step_normal_axis_pick_mode:
            labels.append("STEP normal axis pick")
        if self._step_surface_center_axis_pick_mode:
            labels.append("STEP surface center axis pick")
        if self._step_carry_hold_after_id is not None:
            labels.append("STEP carry hold")
        if self._row_carry_hold_after_id is not None:
            labels.append("row carry hold")
        if self._source_target_pick_mode:
            labels.append("source target")
        if self._center_row_to_ray_mode:
            labels.append("center row to ray")
        if self._placement_target_pick_mode:
            labels.append("snap row to target")
        if self._placement_orient_pick_mode:
            labels.append("orient row to target")
        if self._placement_orient_ray_mode:
            labels.append("orient row to ray")
        if self._placement_drag_state is not None:
            labels.append("placement drag")
        if self._thickness_drag_state is not None:
            labels.append("thickness drag")
        if self._step_carry_drag_state is not None:
            labels.append("STEP carry drag")
        if self._row_carry_drag_state is not None:
            labels.append("row carry drag")
        if self._axis_slide_drag_state is not None:
            labels.append("axis slide drag")
        if self._middle_drag_active:
            labels.append("view pan")
        thickness_service = getattr(self, "_open3d_thickness_dimension_service_instance", None)
        try:
            if thickness_service is not None and thickness_service.has_inline_editor():
                labels.append("thickness edit")
        except Exception:
            pass
        if bool(getattr(self.editor, "_cad_axis_pick_any", False)) or getattr(self.editor, "_cad_axis_pick_label", None) is not None:
            labels.append("STEP axis pick")
        if bool(getattr(self.editor, "_cad_led_object_edge_pick", False)):
            labels.append("LED edge pick")
        return labels

    def current_interaction_mode(self) -> InteractionMode:
        """Return the active interaction mode as a single enum value.

        Derives from the existing per-mode booleans plus editor flags so
        callers don't have to know which booleans are mutually exclusive.
        Also syncs ``_interaction_mode_state`` so any observers attached
        to that state fire when the derived mode changes.
        """
        mode = derive_interaction_mode(self)
        self._interaction_mode_state.set_mode(mode)
        return mode

    def toggle_bug_recording(self) -> None:
        """Start or stop the interaction recorder used to reproduce bugs.

        First click captures a prelude snapshot (camera, picks, rows,
        STEP paths) and begins logging mouse / key / command events.
        Second click stops the recorder and saves the log to
        ``attachment/recorded_bug_repros/recording_*.json``. The
        button label flips between Record / Stop so the user sees
        whether a capture is in progress.
        """
        recorder = getattr(self, "_event_recorder", None)
        if recorder is None:
            return
        try:
            if recorder.is_recording():
                path = recorder.stop()
                self.recorder_button_var.set("● Record bug")
                if path is not None:
                    self.status_var.set(f"Saved bug recording: {path}")
                    try:
                        self.editor.append_debug(f"Open 3D bug recording saved: {path}")
                    except Exception:
                        pass
                else:
                    self.status_var.set("Bug recording stopped (save failed; see debug log).")
                return
            recorder.start()
            self.recorder_button_var.set("■ Stop recording")
            self.status_var.set(
                "Recording bug repro: every mouse press/move/release and key now logged. "
                "Click 'Stop recording' when done."
            )
        except Exception as exc:
            try:
                self.editor.append_debug(f"Open 3D recorder toggle failed: {exc}")
            except Exception:
                pass

    def discard_bug_recording(self) -> bool:
        """Drop the in-progress recording without writing it to disk.

        No-op when no recording is active. Asks the user to confirm so
        a misclicked button doesn't silently throw away events. Flag
        bundles that the user already saved during the recording are
        kept on disk -- only the events log is discarded.
        """
        recorder = getattr(self, "_event_recorder", None)
        if recorder is None or not recorder.is_recording():
            self.status_var.set("Discard recording: no recording in progress.")
            return False
        try:
            from tkinter import messagebox
            confirm = messagebox.askyesno(
                "Discard recording",
                "Throw away the in-progress recording? Flag bundles you already saved during "
                "this session are kept; only the timeline of mouse/key events is discarded.",
                parent=self,
            )
        except Exception:
            confirm = True
        if not confirm:
            return False
        dropped = recorder.discard()
        try:
            self.recorder_button_var.set("● Record bug")
        except Exception:
            pass
        self.status_var.set(f"Recording discarded ({dropped} events dropped, no file written).")
        return True

    def flag_bug(self) -> Path | None:
        """One-click bug flag: screenshot + scene-state + user description.

        Captures the renderer image and scene snapshot *before* opening
        the description prompt so the saved state matches what the user
        saw when they pressed ``s`` (the cursor-preserving keyboard
        shortcut) or clicked the toolbar button. The cursor's
        render-window position at trigger time is overlaid on the
        screenshot as a crosshair, so a bug like "wrong face highlighted
        under the pointer" is still legible after the user moves the
        mouse to dismiss the prompt. If a recording is active, also
        tags a ``flag`` event into the recording's event stream so the
        post-mortem timeline keeps a marker at the right moment. Bundle
        is written to
        ``attachment/recorded_bug_repros/flag_<timestamp>/``.
        """
        from datetime import datetime
        if self._vtk_widget is None:
            self.status_var.set("Flag bug unavailable: 3D window is not ready.")
            return None
        # Immediate feedback so the user knows `s` was detected even if
        # the screenshot capture or PIL overlay takes a beat.
        self.status_var.set("Flag bug: capturing screenshot, please describe in the dialog...")
        try:
            self.update_idletasks()
        except Exception:
            pass
        recorder = getattr(self, "_event_recorder", None)
        # 1. Capture screenshot + scene state immediately (pre-dialog).
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        bundle_dir = ATTACHMENT_DIR / "recorded_bug_repros" / f"flag_{stamp}"
        try:
            bundle_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self.status_var.set(f"Flag bug failed: {_short_error_message(exc)}")
            return None
        # Cursor in render-window coords. VTK origin is bottom-left so
        # we hold both forms; the PNG overlay converts to top-left.
        cursor_xy_vtk: tuple[int, int] | None = None
        try:
            if self._vtk_interactor is not None:
                cx, cy = self._vtk_interactor.GetEventPosition()
                cursor_xy_vtk = (int(cx), int(cy))
        except Exception:
            cursor_xy_vtk = None
        screenshot_path = bundle_dir / "screenshot.png"
        scene_3d_path = bundle_dir / "scene_3d.png"
        # If a popup dialog (e.g. the CAD/STL face editor) is the focused
        # window, the user is looking at *it*, not the 3D scene -- so save
        # the dialog as screenshot.png and keep the 3D render as
        # scene_3d.png. With no dialog focused this is unchanged: the 3D
        # render is screenshot.png and there is no scene_3d.png.
        dialog_window = None
        try:
            dialog_window = self._focused_foreign_toplevel()
        except Exception:
            dialog_window = None
        vtk_image_path = scene_3d_path if dialog_window is not None else screenshot_path
        scene_render_ok = False
        try:
            from vtkmodules.vtkIOImage import vtkPNGWriter  # type: ignore
            from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter  # type: ignore

            render_window = self._vtk_widget.GetRenderWindow()
            render_window.Render()
            capture = vtkWindowToImageFilter()
            capture.SetInput(render_window)
            try:
                capture.SetInputBufferTypeToRGBA()
            except Exception:
                pass
            try:
                capture.ReadFrontBufferOff()
            except Exception:
                pass
            capture.Update()
            writer = vtkPNGWriter()
            writer.SetFileName(str(vtk_image_path))
            writer.SetInputConnection(capture.GetOutputPort())
            writer.Write()
            scene_render_ok = True
        except Exception as exc:
            self.editor.append_debug(f"Open 3D flag 3D-scene capture failed: {exc}")
            if dialog_window is None:
                self.status_var.set(f"Flag bug screenshot failed: {_short_error_message(exc)}")
                return None
        # When a dialog is in front, capture its own pixels as
        # screenshot.png. If that fails (no screenshot backend on this
        # platform), promote the 3D render to screenshot.png so the bundle
        # always has one.
        screenshot_is_dialog = False
        if dialog_window is not None:
            try:
                if self._capture_toplevel_png(dialog_window, screenshot_path):
                    screenshot_is_dialog = True
            except Exception as exc:
                self.editor.append_debug(f"Open 3D flag dialog capture failed: {exc}")
            if not screenshot_is_dialog and scene_render_ok:
                try:
                    import shutil as _shutil

                    _shutil.copyfile(scene_3d_path, screenshot_path)
                    scene_3d_path.unlink()
                except Exception:
                    pass
                self.editor.append_debug(
                    "Open 3D flag: dialog capture unavailable on this platform; saved the 3D render instead."
                )
        if not screenshot_path.exists():
            self.status_var.set("Flag bug screenshot failed.")
            return None
        # The cursor crosshair marks the pointer in the 3D render window, so
        # overlay it onto whichever file holds that render.
        overlay_target = scene_3d_path if screenshot_is_dialog else screenshot_path
        # 1b. Overlay a cursor crosshair on the PNG so hover-state bugs
        # stay legible. Failures here are non-fatal; the raw screenshot
        # still saves to disk.
        cursor_xy_png: tuple[int, int] | None = None
        if cursor_xy_vtk is not None and scene_render_ok and overlay_target.exists():
            try:
                from PIL import Image, ImageDraw  # type: ignore

                with Image.open(overlay_target) as img:
                    img = img.convert("RGBA")
                    width, height = img.size
                    px = int(cursor_xy_vtk[0])
                    py = int(height - cursor_xy_vtk[1])  # VTK bottom-left -> PNG top-left
                    cursor_xy_png = (px, py)
                    if 0 <= px < width and 0 <= py < height:
                        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(overlay)
                        # Lime-green outer ring + magenta inner ring +
                        # crosshair for high contrast on any background.
                        draw.ellipse((px - 16, py - 16, px + 16, py + 16), outline=(0, 255, 0, 255), width=3)
                        draw.ellipse((px - 7, py - 7, px + 7, py + 7), outline=(255, 0, 255, 255), width=2)
                        draw.line((px - 22, py, px - 8, py), fill=(0, 255, 0, 255), width=2)
                        draw.line((px + 8, py, px + 22, py), fill=(0, 255, 0, 255), width=2)
                        draw.line((px, py - 22, px, py - 8), fill=(0, 255, 0, 255), width=2)
                        draw.line((px, py + 8, px, py + 22), fill=(0, 255, 0, 255), width=2)
                        merged = Image.alpha_composite(img, overlay)
                        merged.save(overlay_target)
            except Exception as exc:
                self.editor.append_debug(f"Open 3D flag cursor overlay failed: {exc}")
        # Scene snapshot via the recorder's existing helper (works
        # whether or not a recording is currently active).
        scene_state: dict[str, object] = {}
        try:
            if recorder is not None:
                snap = recorder.capture_scene_snapshot()
                if snap is not None:
                    from dataclasses import asdict as _asdict
                    scene_state = _asdict(snap)
        except Exception:
            scene_state = {}
        # 2. Save the bundle immediately with an empty description so
        # the screenshot + scene state are safe even if the user is in
        # the middle of a carry/drag and never finishes the dialog.
        # The description prompt is non-modal; the user fills it in
        # whenever convenient (or never -- the bundle is still useful).
        recording_info: dict[str, object] = {"recording_active": False}
        try:
            if recorder is not None and recorder.is_recording():
                recording_info = {
                    "recording_active": True,
                    "elapsed_ms": float(recorder._elapsed_ms()),
                }
        except Exception:
            pass
        cursor_block: dict[str, object] = {}
        if cursor_xy_vtk is not None:
            cursor_block["vtk_xy"] = [int(cursor_xy_vtk[0]), int(cursor_xy_vtk[1])]
        if cursor_xy_png is not None:
            cursor_block["png_xy"] = [int(cursor_xy_png[0]), int(cursor_xy_png[1])]
        try:
            (bundle_dir / "description.txt").write_text("", encoding="utf-8")
        except Exception:
            pass
        state_path = bundle_dir / "state.json"
        try:
            payload = {
                "version": 1,
                "captured_at_iso": datetime.now().isoformat(timespec="seconds"),
                "description": "",
                "screenshot": "screenshot.png",
                "screenshot_kind": "dialog" if screenshot_is_dialog else "scene_3d",
                "cursor": cursor_block,
                "recording": recording_info,
                "scene_state": scene_state,
            }
            if screenshot_is_dialog and scene_3d_path.exists():
                payload["scene_3d"] = "scene_3d.png"
            state_path.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            self.editor.append_debug(f"Open 3D flag state write failed: {exc}")
        # 3. If a recording is active, tag a flag event into the stream
        # immediately (with empty description). The non-modal dialog
        # callback below will mutate the payload in place once the user
        # types something, so the recording timeline ends up with the
        # final description without needing a second event.
        flag_event_payload: dict[str, object] | None = None
        try:
            if recorder is not None and recorder.is_recording():
                event_payload: dict[str, object] = {"bundle_dir": str(bundle_dir)}
                if cursor_block:
                    event_payload["cursor"] = cursor_block
                recorder.record_flag(
                    "",
                    str(screenshot_path),
                    payload=event_payload,
                )
                # Hold a reference to the just-appended event payload so
                # the description, once typed, can be written through
                # without inserting a second flag event.
                try:
                    last_event = recorder.events[-1]
                    if str(last_event.kind) == "flag":
                        flag_event_payload = last_event.payload
                except Exception:
                    flag_event_payload = None
        except Exception as exc:
            self.editor.append_debug(f"Open 3D flag record failed: {exc}")
        self.status_var.set(
            f"Flagged bug: {bundle_dir.name}. Type description in the popup (carry stays live)."
        )
        try:
            self.editor.append_progress(f"Flagged Open 3D bug: {bundle_dir}")
        except Exception:
            pass
        # 4. Open the description dialog NON-MODALLY so any active
        # carry / drag / placement stays interactive while the user
        # types. The popup writes description.txt and updates
        # state.json + the recording event payload on Save.
        self._open_flag_description_dialog(
            bundle_dir=bundle_dir,
            state_path=state_path,
            flag_event_payload=flag_event_payload,
        )
        return bundle_dir

    @staticmethod
    def _classify_dialog_toplevel(focused, own_toplevel, root_toplevel):
        """Decide whether a popup dialog is in front (pure, testable).

        Given the app-wide focused widget plus the windows that are *not*
        popups (the inspector's own Toplevel and the editor root), return
        the Toplevel to screenshot, or ``None`` to fall back to the 3D
        render. A focused widget living in any other Toplevel (e.g. the
        CAD/STL face editor) means the user is looking at that dialog.
        """
        if focused is None:
            return None
        try:
            toplevel = focused.winfo_toplevel()
        except Exception:
            return None
        if toplevel is None or toplevel is own_toplevel or toplevel is root_toplevel:
            return None
        return toplevel

    def _focused_foreign_toplevel(self):
        """Return the focused popup Toplevel (e.g. the face editor) or None.

        ``None`` means capture the 3D scene as today; a window means the
        user pressed ``s`` while a dialog was in front, so that dialog is
        what should be screenshotted.
        """
        try:
            focused = self.focus_get()
        except Exception:
            return None
        try:
            own = self.winfo_toplevel()
        except Exception:
            own = None
        try:
            root = self.editor.winfo_toplevel()
        except Exception:
            root = None
        return self._classify_dialog_toplevel(focused, own, root)

    @staticmethod
    def _capture_toplevel_png(window, out_path) -> bool:
        """Best-effort capture of a Tk Toplevel's pixels to ``out_path``.

        Cross-platform so the in-app ``s`` bug-flag grabs the dialog the
        user is actually looking at on any KrakenOS install, not just this
        dev box. Strategies, first success wins:

          1. ImageMagick ``import -window <xid>`` -- Linux X11 and XWayland
             (Tk is an X client, so a Toplevel has a real X window id).
             Exact window, no monitor-offset math.
          2. ``PIL.ImageGrab.grab(bbox)`` over the window's screen rect --
             native on macOS and Windows (no extra deps); also Linux when a
             backend (gnome-screenshot/grim) is present.
          3. ``grim -g`` over the window rect -- Wayland fallback.

        Returns True only if a non-empty PNG was written.
        """
        import platform
        import shutil
        import subprocess

        if window is None:
            return False
        try:
            window.update_idletasks()
        except Exception:
            pass
        try:
            rx = int(window.winfo_rootx())
            ry = int(window.winfo_rooty())
            width = int(window.winfo_width())
            height = int(window.winfo_height())
        except Exception:
            rx = ry = width = height = 0
        out_path = str(out_path)
        system = platform.system()

        def _wrote_image() -> bool:
            try:
                if not os.path.exists(out_path) or os.path.getsize(out_path) <= 0:
                    return False
            except Exception:
                return False
            try:
                from PIL import Image  # type: ignore

                with Image.open(out_path) as img:
                    img.verify()
            except Exception:
                # File exists and is non-empty; trust it if PIL can't verify.
                return True
            return True

        # 1. Linux X11 / XWayland: capture the exact X window by id.
        if system not in {"Darwin", "Windows"} and os.environ.get("DISPLAY"):
            magick = shutil.which("import")
            try:
                xid = int(window.winfo_id())
            except Exception:
                xid = 0
            if magick and xid:
                try:
                    subprocess.run(
                        [magick, "-window", hex(xid), out_path],
                        check=True,
                        timeout=20,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if _wrote_image():
                        return True
                except Exception:
                    pass

        # 2. Native screen-rectangle grab (macOS/Windows native; Linux if a
        #    backend tool is installed).
        if width > 0 and height > 0:
            try:
                from PIL import ImageGrab  # type: ignore

                image = ImageGrab.grab(bbox=(rx, ry, rx + width, ry + height))
                image.save(out_path)
                if _wrote_image():
                    return True
            except Exception:
                pass

        # 3. Wayland region capture.
        if os.environ.get("WAYLAND_DISPLAY") and width > 0 and height > 0:
            grim = shutil.which("grim")
            if grim:
                try:
                    subprocess.run(
                        [grim, "-g", f"{rx},{ry} {width}x{height}", out_path],
                        check=True,
                        timeout=20,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if _wrote_image():
                        return True
                except Exception:
                    pass

        return False

    def _open_flag_description_dialog(
        self,
        *,
        bundle_dir: Path,
        state_path: Path,
        flag_event_payload: dict[str, object] | None,
    ) -> None:
        """Non-modal Tk dialog for the flag description.

        Stays open without grabbing focus so the user can keep carrying
        a STEP body, finish a placement drag, etc., and circle back to
        type the description later. ``Save`` writes description.txt and
        updates state.json (and the recording event payload, if a
        recording is live). ``Close`` leaves an empty description and
        the bundle behind so the screenshot is still preserved.
        """
        try:
            popup = tk.Toplevel(self)
            popup.title(f"Flag: {bundle_dir.name}")
            popup.transient(self)
            popup.attributes("-topmost", True)
            try:
                popup.geometry("+%d+%d" % (self.winfo_rootx() + 24, self.winfo_rooty() + 24))
            except Exception:
                pass
            frame = ttk.Frame(popup, padding=10)
            frame.pack(fill="both", expand=True)
            ttk.Label(
                frame,
                text=(
                    "Describe the bug (carry / drag stays live while this is open).\n"
                    "Press Save to persist; press Close to keep just the screenshot."
                ),
                justify="left",
            ).pack(anchor="w")
            entry = tk.Text(frame, height=4, width=60, wrap="word")
            entry.pack(fill="both", expand=True, pady=(8, 8))
            try:
                entry.focus_set()
            except Exception:
                pass
            buttons = ttk.Frame(frame)
            buttons.pack(fill="x")

            def _do_save(*_args) -> None:
                text = entry.get("1.0", "end").strip()
                if text:
                    try:
                        (bundle_dir / "description.txt").write_text(text + "\n", encoding="utf-8")
                    except Exception as exc:
                        self.editor.append_debug(f"Open 3D flag description save failed: {exc}")
                    try:
                        if state_path.exists():
                            data = json.loads(state_path.read_text(encoding="utf-8"))
                            data["description"] = text
                            state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                    except Exception as exc:
                        self.editor.append_debug(f"Open 3D flag state update failed: {exc}")
                    if isinstance(flag_event_payload, dict):
                        try:
                            flag_event_payload["description"] = text
                        except Exception:
                            pass
                    self.status_var.set(f"Flag description saved: {bundle_dir.name}")
                else:
                    self.status_var.set(f"Flag kept without description: {bundle_dir.name}")
                try:
                    popup.destroy()
                except Exception:
                    pass

            def _do_close(*_args) -> None:
                try:
                    popup.destroy()
                except Exception:
                    pass

            ttk.Button(buttons, text="Save", command=_do_save).pack(side="right", padx=(8, 0))
            ttk.Button(buttons, text="Close", command=_do_close).pack(side="right")
            entry.bind("<Control-Return>", _do_save)
            popup.bind("<Escape>", _do_close)
            # Explicitly do NOT call grab_set / wait_window: the popup
            # is non-modal so VTK drag/carry events keep flowing.
        except Exception as exc:
            self.editor.append_debug(f"Open 3D flag dialog open failed: {exc}")

    def cancel_active_3d_operation(self) -> bool:
        active_labels = self._active_3d_operation_labels()
        if not active_labels:
            if self._clear_open3d_selection(render=True):
                self.status_var.set("Cleared Open 3D selection.")
                return True
            self.status_var.set("No active Open 3D operation to cancel.")
            return False

        carry_states = [
            self._step_carry_follow_state,
            self._step_carry_drag_state,
            self._row_carry_drag_state,
            self._axis_slide_drag_state,
        ]
        restore_state = None
        if any(isinstance(state, dict) and bool(state.get("history_started", False)) for state in carry_states):
            restore_state = getattr(self.editor, "_history_pending_state", None)

        self._cancel_step_carry_hold_timer()
        self._cancel_row_carry_hold_timer()
        thickness_service = getattr(self, "_open3d_thickness_dimension_service_instance", None)
        try:
            if thickness_service is not None and thickness_service.has_inline_editor():
                thickness_service.cancel_inline_editor()
        except Exception:
            pass
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._placement_drag_state = None
        self._thickness_drag_state = None
        self._step_carry_active_label = None
        self._step_carry_drag_state = None
        self._step_carry_follow_state = None
        self._row_carry_drag_state = None
        self._axis_slide_drag_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        if self._dimension_anchor_pick_mode:
            self._exit_dimension_anchor_pick_mode(render=False)
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        self._left_drag_active = False
        self._left_drag_start_xy = None
        self._left_drag_last_xy = None
        self._left_drag_moved = False
        self._ctrl_left_camera_active = False
        self._middle_drag_active = False
        self._middle_drag_last_xy = None
        self.editor._cad_axis_pick_any = False
        self.editor._cad_axis_pick_label = None
        self.editor._cad_led_object_edge_pick = False
        self._set_step_hover_outline(None, None)
        self._set_optical_axis_highlight(None)
        self._set_step_carry_cursor(False)
        self._open3d_carry_grip_service.clear(render=False)
        self._set_axis_pick_cursor(False)
        self._clear_step_translate_drag_overlay(render=False)
        self._update_mode_badge()

        restored = False
        if isinstance(restore_state, dict):
            try:
                self.editor._restore_history_state(restore_state)
                restored = True
            except Exception as exc:
                self.editor.append_debug(f"Open 3D cancel restore failed: {exc}")
            try:
                self.refresh_from_editor()
            except Exception as exc:
                self.editor.append_debug(f"Open 3D cancel refresh failed: {exc}")
        else:
            try:
                self.editor._history_pending_state = None
            except Exception:
                pass
            try:
                self.refresh_from_editor()
            except Exception as exc:
                self.editor.append_debug(f"Open 3D cancel refresh failed: {exc}")
        selection_cleared = self._clear_open3d_selection(render=False)
        if selection_cleared:
            self.render()
        action_text = ", ".join(dict.fromkeys(active_labels))
        suffix = " and reverted free carry movement" if restored else ""
        selection_suffix = " and cleared selection" if selection_cleared else ""
        self.status_var.set(f"Cancelled {action_text}{suffix}{selection_suffix}.")
        return True

    def _cancel_active_3d_operation_event(self, _event=None) -> str:
        self.cancel_active_3d_operation()
        return "break"

    def _flag_bug_event(self, _event=None) -> str:
        """Tk binding shim for the `s` flag-bug hotkey.

        Returns ``"break"`` to suppress further propagation so VTK's
        default `s` (surface-display toggle) doesn't fire after the
        flag dialog closes.
        """
        try:
            # If focus is inside a text entry (e.g. the row spreadsheet
            # cell editor), let `s` type normally instead of flagging.
            focused = self.focus_get()
            if focused is not None:
                cls = focused.winfo_class()
                if cls in {"Entry", "Text", "TEntry", "TCombobox", "Spinbox", "TSpinbox"}:
                    return ""
        except Exception:
            pass
        self.flag_bug()
        return "break"

    def _on_key_press(self, obj, _event) -> None:
        del obj
        key = ""
        try:
            key = str(self._vtk_interactor.GetKeySym() or "")
        except Exception:
            key = ""
        recorder = getattr(self, "_event_recorder", None)
        if recorder is not None and key:
            try:
                recorder.record_key("key_press", keysym=key, state=0)
            except Exception:
                pass
        if key in {"Escape", "Esc"}:
            self.cancel_active_3d_operation()
        elif key in {"Delete", "BackSpace", "Backspace", "KP_Delete"}:
            self.delete_selected_step()
        elif key in {"s", "S"}:
            # `s` (and shift-S) flag a bug. Triggered via key instead of a
            # toolbar click so the user does not have to move the mouse off
            # the hover-highlighted face / edge / handle they want to
            # report.
            self.flag_bug()

    def show_step_rotation_handler(self, label: str, *, additive: bool = False) -> None:
        label = str(label).strip().lower()
        token = self._timing_start("show_step_rotation_handler", label=label, additive=bool(additive))
        if label not in STEP_OVERLAY_LABEL_SET:
            self._timing_finish(token, status="invalid_label")
            return
        if self.editor._step_path_for_label(label) is None:
            self._timing_finish(token, status="missing_step_path")
            return
        try:
            # Plain click collapses the selection to the clicked label so the
            # previous element's rotation gizmo is torn down (bugs/0049).
            # Shift+click toggles the clicked label into a multi-selection.
            if additive:
                selected = {l for l in self._selected_step_labels if l in STEP_OVERLAY_LABEL_SET}
                if label in selected:
                    selected.discard(label)
                else:
                    selected.add(label)
            else:
                selected = {label}
            if label not in selected:
                # Shift toggled the clicked label off; primary becomes another
                # remaining member, or nothing if the selection is now empty.
                self._step_rotation_active_label = sorted(selected)[0] if selected else None
                self._selected_step_labels = selected
                self._set_step_highlight_set(selected, render=False)
                self._reconcile_step_rotation_handles(selected)
                if self._step_rotation_active_label is None:
                    self.status_var.set("Deselected all STEP rotation handles.")
                else:
                    self.status_var.set(f"{self._step_rotation_status_text(self._step_rotation_active_label)}.")
                self.render()
                self._timing_finish(token, status="toggled_off", handle_count=0)
                return
            self._step_rotation_active_label = label
            self._selected_step_labels = selected
            if self._step_carry_active_label is not None:
                self._step_carry_active_label = label
                self._step_carry_follow_state = None
                self._step_carry_snap_ray_mode = False
                self._step_carry_snap_target_mode = False
                self._step_carry_grid_label = None
                self._step_carry_grid_spacing_mm = None
            self.editor.select_step_component(label)
            self._set_step_highlight_set(selected, render=False)
            if not self._step_label_has_visible_body_actor(label):
                self.refresh_imported_step_overlay(label, render=False)
            if not self._step_label_has_visible_body_actor(label):
                selected.discard(label)
                self._selected_step_labels = selected
                self._step_rotation_active_label = sorted(selected)[0] if selected else None
                self._set_step_highlight_set(selected, render=False)
                self._reconcile_step_rotation_handles(selected)
                self.status_var.set(f"{label.upper()} STEP rotation handles hidden because the STEP body is not visible.")
                self.render()
                self._timing_finish(token, status="missing_visible_step_body")
                return
            self._reconcile_step_rotation_handles(selected)
            handle_count = self._step_rotation_handle_count_for_label(label)
            handle_text = "Use the colored STEP rotation handles, or Center STEP Axis."
            if not self._show_rotation_handles():
                handle_text = "Rotation handles are hidden; enable the toolbar checkbox or use Center STEP Axis."
            elif handle_count <= 0:
                handle_text = "Rotation handles could not be rebuilt for this STEP mesh; use Center STEP Axis or re-open Open 3D."
            self.status_var.set(f"{self._step_rotation_status_text(label)}. {handle_text}")
            self.render()
        except Exception as exc:
            self._timing_finish(token, status="error", error=_short_error_message(exc))
            raise
        else:
            self._timing_finish(token, status="ok", handle_count=int(handle_count))

    def _update_step_rotation_handler_state(self) -> None:
        labels = {
            l
            for l in self._selected_step_labels
            if l in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(str(l)) is not None
        }
        active = self._step_rotation_active_label
        if active in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(str(active)) is not None:
            labels.add(str(active))
        else:
            active = sorted(labels)[0] if labels else None
        self._selected_step_labels = labels
        self._step_rotation_active_label = active
        if not labels:
            self._close_step_rotation_handler()
            return
        if not self._show_rotation_handles():
            self._remove_step_rotation_handle_actors()
        else:
            self._reconcile_step_rotation_handles(labels)

    def _rotate_step_from_handler(self, axis: str, delta_deg: float) -> None:
        label = self._step_rotation_active_label or self.editor._selected_step_label
        if label not in STEP_OVERLAY_LABEL_SET:
            self.status_var.set("STEP rotation: select a STEP component first.")
            return
        self.editor.select_step_component(str(label))
        try:
            physics_requested = bool(
                self.editor._open3d_trace_refresh_service().inspector_physics_requested(self)
            )
        except Exception:
            physics_requested = True
        self.editor.rotate_step_axis(str(label), axis, delta_deg, refresh=physics_requested)
        if not physics_requested and not self.refresh_imported_step_overlay(str(label)):
            self.refresh_from_editor(force_retrace=False)
        self._step_rotation_active_label = str(label)
        self._update_step_rotation_handler_state()

    def _close_step_rotation_handler(self) -> None:
        self._step_rotation_active_label = None
        self._selected_step_labels = set()

    def _clear_step_overlay_interaction_state(self, label: str | None = None) -> None:
        label_text = str(label or "").strip().lower()
        self._cancel_step_carry_hold_timer()
        self._step_carry_active_label = None
        self._step_carry_drag_state = None
        self._step_carry_follow_state = None
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._step_carry_grid_label = None
        self._step_carry_grid_spacing_mm = None
        self._selected_step_feature = None
        self._selected_step_feature_label = None
        self._selected_step_feature_center_world = None
        self._selected_step_feature_surface_center_world = None
        self._selected_step_feature_normal_world = None
        self._close_step_rotation_handler()
        self._set_step_hover_outline(None, None)
        self._set_step_carry_cursor(False)
        self._set_axis_pick_cursor(False)
        self._open3d_carry_grip_service.clear(render=False)
        if label_text:
            try:
                if getattr(self.editor, "_selected_step_label", None) == label_text:
                    self.editor._selected_step_label = None
            except Exception:
                pass
            self._set_step_highlight(None, render=False)

    def _stl_placement_status_text(self, row_index: int) -> str:
        row = self.editor.rows[int(row_index)]
        row_name = str(row.name or row.surface or "CAD/STL solid").strip()
        return (
            f"S{int(row_index)} {row_name}\n"
            f"Tilt=({float(row.tilt_x):.4g}, {float(row.tilt_y):.4g}, {float(row.tilt_z):.4g}) deg | "
            f"Dec=({float(row.desp_x):.4g}, {float(row.desp_y):.4g}, {float(row.desp_z):.4g}) mm"
        )

    def show_stl_placement_handler(self, row_index: int | None = None) -> None:
        if row_index is None:
            row_index = self._active_stl_placement_row_index()
        if row_index is None:
            return
        row_index = int(row_index)
        if self.editor._file_backed_stl_row_at(row_index) is None:
            self.status_var.set("Selected row is not a file-backed optical CAD/STL solid.")
            self._close_stl_placement_handler()
            return

        self._stl_placement_row_index = row_index
        self.editor._select_table_row(row_index)
        self.highlight_row(row_index)

        popup = self._stl_placement_popup
        if popup is None or not bool(getattr(popup, "winfo_exists", lambda: False)()):
            popup = ttk.Frame(self, padding=10, borderwidth=1, relief="groove")
            popup.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=8)
            popup.columnconfigure(0, weight=1)
            self._stl_placement_popup = popup
            self._stl_placement_status_var = tk.StringVar(value="")
            frame = ttk.Frame(popup)
            frame.grid(row=0, column=0, sticky="nsew")
            for column in range(4):
                frame.columnconfigure(column, weight=1)
            ttk.Label(frame, text="CAD/STL placement side panel", font=("", 10, "bold")).grid(
                row=0,
                column=0,
                columnspan=4,
                sticky="w",
            )
            ttk.Label(frame, textvariable=self._stl_placement_status_var, foreground="#334155").grid(
                row=1,
                column=0,
                columnspan=4,
                sticky="w",
                pady=(2, 8),
            )
            ttk.Label(
                frame,
                text=(
                    "What this does: Fit Axis chooses which CAD-local axis should become layout +Z. "
                    "The +/-Rot buttons use the toolbar rotation step to rotate the solid into the expected orientation. "
                    "Center X/Y moves the solid onto the optical axis; Front On Row places its minimum-Z face on the row station. "
                    "Done -> 2D refreshes the main layout with the edited Tilt/Decenter fields."
                ),
                foreground="#475569",
                justify="left",
                wraplength=430,
            ).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
            ttk.Label(frame, text="Fit local axis to +Z").grid(row=3, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Combobox(
                frame,
                textvariable=self.stl_axis_var,
                state="readonly",
                values=tuple(STL_AXIS_TO_LAYOUT_Z_TILTS.keys()),
                width=6,
            ).grid(row=3, column=1, sticky="ew", padx=(0, 4), pady=2)
            ttk.Button(frame, text="Fit Axis", command=self._fit_stl_from_handler).grid(
                row=3,
                column=2,
                columnspan=2,
                sticky="ew",
                pady=2,
            )
            axis_colors = {"x": "#dc2626", "y": "#16a34a", "z": "#2563eb"}
            for row_number, axis in enumerate(("x", "y", "z"), start=4):
                tk.Label(frame, text=f"{axis.upper()} axis", fg=axis_colors[axis], font=("", 10, "bold")).grid(
                    row=row_number,
                    column=0,
                    sticky="w",
                    padx=(0, 8),
                    pady=2,
                )
                ttk.Button(
                    frame,
                    text="-Rot",
                    width=6,
                    command=lambda a=axis: self._rotate_stl_from_handler(a, -self._rotation_handle_step_deg()),
                ).grid(row=row_number, column=1, sticky="ew", padx=(0, 4), pady=2)
                ttk.Button(
                    frame,
                    text="+Rot",
                    width=6,
                    command=lambda a=axis: self._rotate_stl_from_handler(a, self._rotation_handle_step_deg()),
                ).grid(row=row_number, column=2, sticky="ew", padx=(0, 4), pady=2)
            ttk.Button(frame, text="Center X/Y", command=self._center_stl_from_handler).grid(
                row=7,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(8, 0),
                padx=(0, 4),
            )
            ttk.Button(frame, text="Front On Row", command=self._front_stl_from_handler).grid(
                row=7,
                column=2,
                columnspan=2,
                sticky="ew",
                pady=(8, 0),
            )
            ttk.Button(frame, text="Done -> 2D", command=self.finish_stl_placement).grid(
                row=8,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(6, 0),
                padx=(0, 4),
            )
            ttk.Button(frame, text="Close", command=self._close_stl_placement_handler).grid(
                row=8,
                column=2,
                columnspan=2,
                sticky="ew",
                pady=(6, 0),
            )

        self._update_stl_placement_handler_state()
        try:
            popup.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=8)
            popup.tkraise()
            self.update_idletasks()
        except Exception:
            pass
        self.status_var.set(f"CAD/STL placement side panel opened for S{row_index}.")

    def _update_stl_placement_handler_state(self) -> None:
        row_index = self._stl_placement_row_index
        popup = self._stl_placement_popup
        if row_index is None:
            self._close_stl_placement_handler()
            return
        try:
            row_index = int(row_index)
        except Exception:
            self._close_stl_placement_handler()
            return
        if self.editor._file_backed_stl_row_at(row_index) is None:
            self._close_stl_placement_handler()
            return
        if popup is None or not bool(getattr(popup, "winfo_exists", lambda: False)()):
            return
        if self._stl_placement_status_var is not None:
            self._stl_placement_status_var.set(self._stl_placement_status_text(row_index))

    def _fit_stl_from_handler(self) -> None:
        self.fit_selected_stl_axis()
        self._update_stl_placement_handler_state()

    def _rotate_stl_from_handler(self, axis: str, delta_deg: float) -> None:
        self.rotate_selected_stl_pose(axis, delta_deg)
        self._update_stl_placement_handler_state()

    def _center_stl_from_handler(self) -> None:
        self.center_selected_stl_xy()
        self._update_stl_placement_handler_state()

    def _front_stl_from_handler(self) -> None:
        self.place_selected_stl_front_on_row()
        self._update_stl_placement_handler_state()

    def _close_stl_placement_handler(self) -> None:
        popup = self._stl_placement_popup
        self._stl_placement_popup = None
        self._stl_placement_status_var = None
        self._stl_placement_row_index = None
        if popup is not None:
            try:
                popup.destroy()
            except Exception:
                pass

    def _add_ray_actor(
        self,
        mesh,
        *,
        radius: float,
        color: tuple[float, float, float],
        ray_index: int | None = None,
        opacity: float = 0.9,
        line_width: float = 1.2,
    ) -> None:
        if self._renderer is None or vtkActor is None or vtkDataSetMapper is None:
            return
        actor = vtkActor()
        mapper = vtkDataSetMapper()
        mapper.SetInputData(mesh)
        actor.SetMapper(mapper)
        actor.GetProperty().SetLineWidth(float(line_width))
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetOpacity(float(opacity))
        if ray_index is None:
            actor.PickableOff()
        else:
            actor_key = self._actor_key(actor)
            if actor_key is not None:
                self._actor_ray_map[actor_key] = int(ray_index)
                self._ray_actor_map.setdefault(int(ray_index), []).append(actor_key)
            actor.PickableOn()
        self._renderer.AddActor(actor)

    def _add_ray_endpoint_actor(
        self,
        point,
        *,
        radius: float,
        color: tuple[float, float, float],
        ray_index: int | None = None,
        terminal_status: str = "",
    ) -> None:
        if pv is None:
            return
        try:
            center = np.asarray(point, dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if center.size < 3 or not np.all(np.isfinite(center)):
            return
        try:
            marker = pv.Sphere(
                radius=max(float(radius), 0.05),
                center=tuple(center[:3]),
                theta_resolution=16 if terminal_status == "missed_detector" else 12,
                phi_resolution=10 if terminal_status == "missed_detector" else 8,
            )
        except Exception:
            return
        actor = self._add_mesh_actor(
            marker,
            color=color,
            opacity=0.96,
            pick_row_index=None,
            line_width=1.0,
            flat_shading=True,
        )
        if actor is None or ray_index is None:
            return
        try:
            actor_key = self._actor_key(actor)
            if actor_key is not None:
                self._actor_ray_map[actor_key] = int(ray_index)
                self._ray_actor_map.setdefault(int(ray_index), []).append(actor_key)
                actor.PickableOn()
        except Exception:
            pass

    def _augment_bounds_with_scene_overlays(
        self,
        bounds,
        scene_bundle: SceneBundle | None,
    ) -> np.ndarray:
        """Return bounds widened to enclose pending STEP overlays and ray paths.

        The optical-axis Z span must reflect every body that will be on
        screen, not just what is in the renderer at the moment this is
        called. STEP overlay bodies are added to the renderer *after*
        the axis is built; ray endpoints can also sit outside the row
        envelope. Pull both sources from the editor and the scene
        bundle and union them with whatever ComputeVisiblePropBounds
        produced.
        """
        try:
            extent = np.asarray(bounds, dtype=float).reshape(-1)
        except Exception:
            return np.asarray([-10.0, 10.0, -10.0, 10.0, 0.0, 100.0], dtype=float)
        if extent.size != 6 or not np.all(np.isfinite(extent)):
            extent = np.asarray([-10.0, 10.0, -10.0, 10.0, 0.0, 100.0], dtype=float)

        def _union(mesh) -> None:
            nonlocal extent
            if mesh is None or int(getattr(mesh, "n_points", 0) or 0) <= 0:
                return
            try:
                mb = np.asarray(getattr(mesh, "bounds", None), dtype=float).reshape(-1)
            except Exception:
                return
            if mb.size != 6 or not np.all(np.isfinite(mb)):
                return
            extent = np.asarray(
                [
                    min(extent[0], mb[0]),
                    max(extent[1], mb[1]),
                    min(extent[2], mb[2]),
                    max(extent[3], mb[3]),
                    min(extent[4], mb[4]),
                    max(extent[5], mb[5]),
                ],
                dtype=float,
            )

        try:
            promoted = self.editor._promoted_step_source_keys_for_rows(self.editor.rows)
        except Exception:
            promoted = {}
        for label in ("optical", "lens", "camera", "led"):
            try:
                if self.editor._step_path_for_label(label) is None:
                    continue
                if self.editor._step_overlay_matches_promoted_row(label, promoted):
                    # Refresh skips promoted overlays, so don't extend axis
                    # past a body that won't actually be drawn.
                    continue
                _union(self.editor._transformed_imported_step_mesh_for_label(label))
            except Exception:
                continue

        try:
            paths = list(getattr(scene_bundle, "ray_paths", []) or [])
        except Exception:
            paths = []
        for path in paths:
            try:
                pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            except Exception:
                continue
            if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 3:
                continue
            finite = pts[np.all(np.isfinite(pts[:, :3]), axis=1)]
            if finite.size == 0:
                continue
            mn = finite[:, :3].min(axis=0)
            mx = finite[:, :3].max(axis=0)
            extent = np.asarray(
                [
                    min(extent[0], float(mn[0])),
                    max(extent[1], float(mx[0])),
                    min(extent[2], float(mn[1])),
                    max(extent[3], float(mx[1])),
                    min(extent[4], float(mn[2])),
                    max(extent[5], float(mx[2])),
                ],
                dtype=float,
            )

        return extent

    def _optical_axis_records_for_3d(self, scene_bundle: SceneBundle | None) -> list[dict[str, object]]:
        try:
            bounds = np.asarray(self._renderer.ComputeVisiblePropBounds(), dtype=float).reshape(6)
            if bounds.size != 6 or not np.all(np.isfinite(bounds)):
                raise ValueError("invalid bounds")
        except Exception:
            bounds = np.asarray([-10.0, 10.0, -10.0, 10.0, 0.0, 100.0], dtype=float)
        # ComputeVisiblePropBounds only sees actors already in the renderer.
        # The scene-refresh call site invokes us BEFORE STEP overlay actors
        # are added, so a STEP body placed off to the side of the rows
        # leaves the dotted optical axis truncated to the row-only Z span.
        # Predict STEP overlay bounds + sample ray-path bounds and union
        # them in so the axis spans the full populated scene regardless of
        # refresh order.
        bounds = self._augment_bounds_with_scene_overlays(bounds, scene_bundle)
        z0, z1 = _optical_axis_z_span(bounds)
        records = [
            {
                "axis_id": "axis:global",
                "axis_label": "Optical Axis",
                "axis_kind": "dotted_global_guide",
                "branch_path": "",
                "source_id": "",
                "ray_index": -1,
                "points": np.asarray(((0.0, 0.0, z0), (0.0, 0.0, z1)), dtype=float),
            }
        ]
        try:
            show_rays = bool(self.show_rays_var.get())
        except Exception:
            show_rays = False
        # Build a cache signature from the current rows so the cached
        # traced segments stay valid as long as the scene topology
        # hasn't changed. Edits to a row's pose / Rc / glass don't
        # change the signature -- the user can keep the segments
        # while still iterating on parameters -- but row insertions /
        # removals do.
        try:
            cache_signature = tuple(
                (
                    str(getattr(row, "surface", "") or ""),
                    str(getattr(row, "name", "") or ""),
                )
                for row in self.editor.rows
            )
        except Exception:
            cache_signature = ()
        if cache_signature != self._cached_traced_axis_signature:
            self._cached_traced_axis_records = []
            self._cached_traced_axis_signature = cache_signature
        if not show_rays:
            # Serve the cache so the folded cascade segments stay
            # visible when the user toggles rays off. Empty cache =>
            # only the global guide, matching the prior behaviour.
            if self._cached_traced_axis_records:
                records.extend(self._cached_traced_axis_records)
            return records
        allow_traced_axis_guides = bool(getattr(scene_bundle, "has_off_axis", False)) or bool(
            list(getattr(scene_bundle, "optical_volumes", []) or [])
        ) or bool(list(getattr(scene_bundle, "boundary_faces", []) or []))
        if not allow_traced_axis_guides:
            return records
        # One cleaned polyline per path, shared by the filter below and _path_score (run
        # once per path inside sorted(...)) and _path_launch_axis -- avoids cleaning every
        # path 2x+ over the potentially hundreds the per-branch launch emits.
        _pts_cache: dict[int, np.ndarray] = {}

        def _cleaned_points(path) -> np.ndarray:
            key = id(path)
            cached = _pts_cache.get(key)
            if cached is None:
                cached = _clean_polyline_points(getattr(path, "points_world", np.empty((0, 3))))
                _pts_cache[key] = cached
            return cached

        paths = [
            path
            for path in list(getattr(scene_bundle, "ray_paths", []) or [])
            if _cleaned_points(path).shape[0] >= 2
        ]
        if paths:
            def _path_score(path) -> tuple[float, float, float, float, float]:
                points = _cleaned_points(path)
                if points.shape[0] >= 2:
                    launch_radius = float(np.hypot(points[0, 0], points[0, 1]))
                    launch_direction = points[1, :3] - points[0, :3]
                    launch_norm = float(np.linalg.norm(launch_direction))
                    if np.isfinite(launch_norm) and launch_norm > 1e-12:
                        launch_direction = launch_direction / launch_norm
                        launch_tilt = float(np.hypot(launch_direction[0], launch_direction[1]))
                    else:
                        launch_tilt = float("inf")
                else:
                    launch_radius = float("inf")
                    launch_tilt = float("inf")
                try:
                    source_ray = float(getattr(path, "source_ray_index", getattr(path, "ray_index", 0)) or 0)
                except Exception:
                    source_ray = 0.0
                try:
                    power = float(getattr(path, "branch_power", 1.0) or 0.0)
                except Exception:
                    power = 0.0
                try:
                    ray_index = float(getattr(path, "ray_index", 0) or 0)
                except Exception:
                    ray_index = 0.0
                return (launch_radius, launch_tilt, -power, abs(source_ray), abs(ray_index))

            _path_has_non_refractive_steering = ray_path_has_non_refractive_steering

            physical_paths = [
                path
                for path in paths
                if any(
                    str(getattr(event, "event_kind", "") or "") == "surface"
                    and str(getattr(event, "event_type", "") or "").strip().lower()
                    not in {"", "image", "detector", "target"}
                    for event in list(getattr(path, "events", []) or [])
                )
            ]
            physical_paths = [path for path in physical_paths if _path_has_non_refractive_steering(path)]
            # A traced segment only earns a SEPARATE axis when it is genuinely
            # folded -- its direction CHANGED at a reflection/TIR/splitter (a beam
            # splitter's reflected branch, a fold mirror, a penta deviation). The
            # fold is measured against THAT RAY'S OWN LAUNCH DIRECTION, not the
            # global +Z axis (bugs/0083): a finite/off-axis source launches field
            # chief rays tilted several degrees, so their straight-through
            # transmitted segments deviate from +Z by the field angle and would
            # masquerade as folds, each spawning an unwanted extra optical axis.
            # Measured against the ray's launch direction, a straight transmit
            # stays collinear (deviation ~0 -> not a fold) while a real reflection
            # still deviates ~90 deg. For the on-axis chief ray (launch == +Z)
            # this is identical to the old +Z test, so splitter/penta are unchanged.
            global_axis_direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
            fold_collinearity_tol = 0.1  # sin(~5.7 deg)

            def _axis_unit(direction) -> np.ndarray | None:
                try:
                    vector = np.asarray(direction, dtype=float).reshape(3)
                except Exception:
                    return None
                norm = float(np.linalg.norm(vector))
                if not np.isfinite(norm) or norm <= 1e-9:
                    return None
                return vector / norm

            def _path_launch_axis(path) -> np.ndarray:
                points = _cleaned_points(path)
                if points.shape[0] >= 2:
                    launch = _axis_unit(points[1, :3] - points[0, :3])
                    if launch is not None:
                        return launch
                return global_axis_direction

            def _segment_is_genuine_fold(direction, reference_axis) -> bool:
                unit = _axis_unit(direction)
                if unit is None:
                    return False
                reference = _axis_unit(reference_axis)
                if reference is None:
                    reference = global_axis_direction
                transverse = unit - float(np.dot(unit, reference)) * reference
                return float(np.linalg.norm(transverse)) >= fold_collinearity_tol

            if physical_paths:
                # Each distinct folded beam branch deserves its own traced optical
                # axis. A single chief is not enough for a beam splitter: the
                # central ray fans into an on-axis transmit branch (already covered
                # by axis:global) AND a folded reflect branch. If the transmit
                # branch wins the chief score the reflected beam path would get no
                # axis at all. Walk the steered paths in centrality order and keep
                # one representative folded segment per distinct fold DIRECTION,
                # clustering by angular proximity: a branch's field rays fan a few
                # degrees apart and must collapse to one axis, while genuinely
                # different folds (a 90 deg splitter reflection) stay separate.
                max_traced_axes = 6
                fold_merge_cos = 0.966  # cos(~15 deg)
                traced_segments: list[dict[str, object]] = []
                kept_fold_units: list[np.ndarray] = []
                for path in sorted(physical_paths, key=_path_score):
                    launch_axis = _path_launch_axis(path)
                    for segment in _dotted_axis_records_from_ray_path(path, bounds):
                        unit = _axis_unit(segment.get("segment_direction"))
                        if unit is None or not _segment_is_genuine_fold(
                            segment.get("segment_direction"), launch_axis
                        ):
                            continue
                        if any(float(np.dot(unit, kept)) >= fold_merge_cos for kept in kept_fold_units):
                            continue
                        kept_fold_units.append(unit)
                        traced_segments.append(segment)
                    if len(traced_segments) >= max_traced_axes:
                        break
                del traced_segments[max_traced_axes:]
                for axis_number, segment in enumerate(traced_segments, start=2):
                    segment["axis_label"] = f"Optical Axis {axis_number}"
                records.extend(traced_segments)
                # Stash a deep-enough copy so a later rays-off refresh
                # can serve the same segments. Convert numpy point
                # arrays into a plain list so the cache stays portable
                # across refresh cycles.
                cached: list[dict[str, object]] = []
                for seg in traced_segments:
                    seg_copy = dict(seg)
                    pts = seg_copy.get("points")
                    if pts is not None:
                        try:
                            seg_copy["points"] = np.asarray(pts, dtype=float).copy()
                        except Exception:
                            pass
                    cached.append(seg_copy)
                self._cached_traced_axis_records = cached
        return records

    def _add_optical_axis_pick_overlays(self, scene_bundle: SceneBundle | None) -> int:
        if pv is None:
            return 0
        count = 0
        for record in self._optical_axis_records_for_3d(scene_bundle):
            points = np.asarray(record.get("points"), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                continue
            record = dict(record)
            record["points"] = points[:, :3].copy()
            self._optical_axis_pick_records.append(record)
            mesh = _dotted_axis_mesh_from_points(points[:, :3])
            if mesh is None:
                continue
            if int(getattr(mesh, "n_points", 0)) < 2:
                continue
            actor = self._add_mesh_actor(
                mesh,
                color=(0.0, 0.43, 0.88),
                opacity=0.95,
                line_width=3.0 if self._optical_axis_pick_mode_active() else 2.2,
                pick_optical_axis=record,
            )
            if actor is not None:
                count += 1
        return count

    def _optical_axis_frame_from_pick(self, axis_info: dict[str, object], picker) -> dict[str, object] | None:
        points = np.asarray(axis_info.get("points"), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            return None
        picked = np.asarray(axis_info.get("picked_world", ()), dtype=float).reshape(-1)[:3]
        if picked.size < 3 or not np.all(np.isfinite(picked[:3])):
            try:
                picked = np.asarray(picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            except Exception:
                picked = points[0, :3]
        if picked.size < 3 or not np.all(np.isfinite(picked[:3])):
            picked = points[0, :3]
        try:
            target_point, direction = self.editor._closest_polyline_point_and_direction(points[:, :3], picked[:3])
            direction = self.editor._normalized_vector(direction)
        except Exception:
            segment = points[-1, :3] - points[0, :3]
            norm = float(np.linalg.norm(segment))
            if not np.isfinite(norm) or norm <= 1e-12:
                return None
            target_point = picked[:3]
            direction = segment / norm
        payload = dict(axis_info)
        payload["picked_world"] = np.asarray(target_point, dtype=float).reshape(3)
        payload["direction"] = np.asarray(direction, dtype=float).reshape(3)
        try:
            return self.editor._optical_axis_frame_from_record(payload, reference_point=target_point)
        except Exception:
            return {
                "target_point": np.asarray(target_point, dtype=float).reshape(3),
                "direction": np.asarray(direction, dtype=float).reshape(3),
                "axis_label": str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis"),
                "branch_path": str(axis_info.get("branch_path", "") or ""),
                "ray_index": int(axis_info.get("ray_index", -1)),
                "source_id": str(axis_info.get("source_id", "") or ""),
            }

    @staticmethod
    def _face_role_marker_scale(marker: OpticalSolidFaceMarker, scene_radius: float) -> float:
        face_span = np.sqrt(max(float(marker.area_mm2), 1.0))
        lower = max(float(scene_radius) * 0.025, 1.0)
        upper = max(float(scene_radius) * 0.12, lower)
        return float(np.clip(face_span * 0.28, lower, upper))

    def _add_face_role_marker_actor(self, marker: OpticalSolidFaceMarker, *, scene_radius: float) -> bool:
        if pv is None:
            return False
        try:
            start = np.asarray(marker.centroid, dtype=float)
            normal = np.asarray(marker.normal, dtype=float)
            if start.size < 3 or normal.size < 3:
                return False
            normal_norm = float(np.linalg.norm(normal[:3]))
            if normal_norm <= 1e-12 or not np.isfinite(normal_norm):
                return False
            normal = normal[:3] / normal_norm
            length = self._face_role_marker_scale(marker, scene_radius)
            self._add_mesh_actor(
                pv.Sphere(radius=max(length * 0.08, 0.18), center=tuple(start[:3])),
                color=marker.color,
                opacity=0.98,
                flat_shading=True,
            )
            self._add_mesh_actor(
                pv.Arrow(start=tuple(start[:3]), direction=tuple(normal), scale=length),
                color=marker.color,
                opacity=0.96,
                flat_shading=True,
            )
            return True
        except Exception as exc:
            self.editor.append_debug(f"3D optical face marker error: {exc}")
            return False

    def _saved_step_native_display_transform_for_row(self, row_index: int):
        scene_bundle = self.__dict__.get("_current_scene_bundle")
        if scene_bundle is None:
            return None
        if scene_bundle is not self.editor.__dict__.get("_last_saved_step_native_scene_bundle"):
            return None
        item = self.editor._file_backed_stl_row_at(int(row_index))
        if item is None:
            return None
        row, _path = item
        try:
            z_station = self.editor._stl_row_z_station(int(row_index))
            return self.editor._file_backed_row_display_transform(row, float(z_station))
        except Exception:
            return None

    def _runtime_transform_for_row(self, system, row_index: int):
        saved_display_transform = self._saved_step_native_display_transform_for_row(int(row_index))
        if saved_display_transform is not None:
            return saved_display_transform
        override = optical_solid_output_port_runtime_transform_override(system, self.editor.rows, row_index)
        if override is not None:
            return override
        transforms = getattr(system, "TRANS_2A", None) if system is not None else None
        if transforms is None:
            return None
        try:
            if int(row_index) < 0 or int(row_index) >= len(transforms):
                return None
            transform = np.asarray(transforms[int(row_index)], dtype=float).reshape(4, 4)
        except Exception:
            return None
        # bugs/0075: a parked off-beam solid is neutralised out of the trace
        # (bugs/0065/0074), so its build transform TRANS_2A is ON the optical axis.
        # _iter_3d_optical_surface_meshes restores the body's decentered station
        # (bugs/0067), but EVERY other consumer of this shared transform -- the
        # selected-body redraw, assigned-face overlays, face markers, virtual
        # planes, the placement gizmo -- used the raw on-axis transform, so the
        # instant the Face Editor selected the solid the whole cube snapped onto
        # the axis while its row Desp stayed off-axis. Apply the same re-decenter
        # here so the display is consistent (no-op for an on-/near-beam or coated
        # solid, whose build keeps its Desp).
        try:
            built = getattr(system, "SDT", None)
            rows = getattr(self.editor, "rows", None)
            if built is not None and rows is not None and 0 <= int(row_index) < min(len(built), len(rows)):
                redecentered = offbeam_neutralized_body_transform(
                    transform,
                    surface_row_to_spec(rows[int(row_index)]),
                    getattr(built[int(row_index)], "DespX", 0.0),
                    getattr(built[int(row_index)], "DespY", 0.0),
                )
                if redecentered is not None:
                    return redecentered
        except Exception:
            pass
        return transform

    @staticmethod
    def _row_optical_solid_face_metadata(row) -> dict[str, object]:
        advanced = getattr(row, "advanced", {})
        if not isinstance(advanced, dict):
            advanced = {}
        return normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))

    @staticmethod
    def _transform_local_point_and_normal(matrix, point, normal) -> tuple[np.ndarray, np.ndarray] | None:
        try:
            local_point = np.asarray(_point3_tuple(point), dtype=float)
            local_normal = np.asarray(_unit_vector_tuple(normal), dtype=float)
            world_point = np.asarray(matrix, dtype=float).reshape(4, 4) @ np.asarray(
                (float(local_point[0]), float(local_point[1]), float(local_point[2]), 1.0),
                dtype=float,
            )
            world_normal = np.asarray(matrix, dtype=float).reshape(4, 4)[:3, :3] @ local_normal[:3]
            normal_norm = float(np.linalg.norm(world_normal))
            if normal_norm <= 1e-12:
                return None
            world_point = np.asarray(world_point[:3], dtype=float)
            world_normal = np.asarray(world_normal[:3], dtype=float) / normal_norm
            if not (np.all(np.isfinite(world_point)) and np.all(np.isfinite(world_normal))):
                return None
            return world_point, world_normal
        except Exception:
            return None

    @classmethod
    def _face_role_markers_from_runtime_transform(
        cls,
        row,
        transform,
        *,
        assigned_only: bool = True,
    ) -> list[OpticalSolidFaceMarker]:
        try:
            metadata = cls._row_optical_solid_face_metadata(row)
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        except Exception:
            return []
        markers: list[OpticalSolidFaceMarker] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            function = _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            side = _normalize_optical_solid_face_side(face.get("side_2d"))
            role = _legacy_role_from_optical_solid_face_function(function)
            if (
                assigned_only
                and role == OPTICAL_SOLID_FACE_ROLE_DEFAULT
                and function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
                and side == OPTICAL_SOLID_FACE_SIDE_DEFAULT
            ):
                continue
            normal = face.get("normal", (0.0, 0.0, 1.0))
            if bool(face.get("flip_normal", False)):
                normal = -np.asarray(_unit_vector_tuple(normal), dtype=float)
            transformed = cls._transform_local_point_and_normal(matrix, face.get("centroid", (0.0, 0.0, 0.0)), normal)
            if transformed is None:
                continue
            centroid_world, normal_world = transformed
            world_face = dict(face)
            world_face["role"] = role
            world_face["function"] = function
            world_face["side_2d"] = side
            world_face["centroid_world"] = tuple(float(value) for value in centroid_world[:3])
            world_face["normal_world"] = tuple(float(value) for value in normal_world[:3])
            markers.append(
                OpticalSolidFaceMarker(
                    face_id=str(world_face.get("face_id", "") or ""),
                    role=_optical_solid_face_marker_label(world_face),
                    centroid=tuple(float(value) for value in centroid_world[:3]),
                    normal=tuple(float(value) for value in normal_world[:3]),
                    area_mm2=max(_float_or_default(world_face.get("area_mm2"), 0.0), 0.0),
                    split_ratio=float(np.clip(_float_or_default(world_face.get("split_ratio"), 0.5), 0.0, 1.0)),
                    color=optical_solid_face_role_color(role),
                )
            )
        return markers

    @classmethod
    def _virtual_plane_markers_from_runtime_transform(
        cls,
        row,
        transform,
        *,
        assigned_only: bool = True,
    ) -> list[OpticalSolidVirtualPlaneMarker]:
        try:
            metadata = cls._row_optical_solid_face_metadata(row)
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        except Exception:
            return []
        markers: list[OpticalSolidVirtualPlaneMarker] = []
        for plane in list(metadata.get("virtual_planes", []) or []):
            if not isinstance(plane, dict):
                continue
            normalized = normalize_optical_solid_virtual_plane_record(plane)
            kind = _normalize_optical_solid_virtual_plane_kind(normalized.get("kind"))
            if assigned_only and kind not in OPTICAL_SOLID_VIRTUAL_PLANE_KIND_VALUES:
                continue
            transformed = cls._transform_local_point_and_normal(
                matrix,
                normalized.get("point", (0.0, 0.0, 0.0)),
                normalized.get("normal", (0.0, 0.0, 1.0)),
            )
            if transformed is None:
                continue
            centroid_world, normal_world = transformed
            markers.append(
                OpticalSolidVirtualPlaneMarker(
                    plane_id=str(normalized.get("plane_id", "") or ""),
                    kind=kind,
                    centroid=tuple(float(value) for value in centroid_world[:3]),
                    normal=tuple(float(value) for value in normal_world[:3]),
                    aperture_mm=max(_float_or_default(normalized.get("aperture_mm"), 0.0), 0.0),
                    split_ratio=float(np.clip(_float_or_default(normalized.get("split_ratio"), 0.5), 0.0, 1.0)),
                    color=optical_solid_virtual_plane_color(kind),
                )
            )
        return markers

    def _add_optical_solid_face_role_overlays(self, system=None) -> int:
        if self._renderer is None:
            return 0
        z_positions = self.editor._row_z_positions()
        _center, scene_radius = self._scene_bounds()
        count = 0
        for row_index, row in enumerate(self.editor.rows):
            if self.editor._file_backed_stl_row_at(row_index) is None:
                continue
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            transform = self._runtime_transform_for_row(system, row_index)
            markers = (
                self._face_role_markers_from_runtime_transform(row, transform, assigned_only=True)
                if transform is not None
                else optical_solid_face_world_markers(row, z_station, assigned_only=True)
            )
            for marker in markers:
                if self._add_face_role_marker_actor(marker, scene_radius=scene_radius):
                    count += 1
        return count

    @staticmethod
    def _assigned_optical_solid_face(face: dict[str, object]) -> bool:
        if str(face.get("assignment_source", "") or "").strip() == OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED:
            return False
        function = _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        side = _normalize_optical_solid_face_side(face.get("side_2d"))
        role = _legacy_role_from_optical_solid_face_function(function)
        return not (
            role == OPTICAL_SOLID_FACE_ROLE_DEFAULT
            and function == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT
            and side == OPTICAL_SOLID_FACE_SIDE_DEFAULT
        )

    @staticmethod
    def _row_face_metadata_uses_saved_mesh(row) -> bool:
        """Return true when face triangle IDs belong to the saved CAD mesh.

        Promoted imported STEP solids persist face records against the centered
        promoted STL. Kraken's runtime trace mesh can have a different triangle
        order, so reusing those saved face indices on the runtime mesh makes
        selection and role overlays jump to unrelated faces.
        """
        try:
            advanced = dict(getattr(row, "advanced", {}) or {})
        except Exception:
            return False
        promotion = dict(advanced.get("StepOverlayPromotion", {}) or {})
        placement = dict(advanced.get("ScenePlacement", {}) or {})
        return bool(
            str(promotion.get("mesh_coordinates", "") or "").strip() == "local_centered_from_open3d_overlay"
            or str(placement.get("promotion_mesh_coordinates", "") or "").strip() == "local_centered_from_open3d_overlay"
        )

    @staticmethod
    def _world_face_triangles_for_record(
        row,
        triangles: np.ndarray,
        face: dict[str, object],
        *,
        z_station: float,
        transform=None,
        scene_radius: float = 1.0,
    ) -> np.ndarray:
        indices: list[int] = []
        for value in list(face.get("triangle_indices", []) or []):
            try:
                index = int(value)
            except Exception:
                continue
            if 0 <= index < int(triangles.shape[0]):
                indices.append(index)
        if not indices:
            return np.empty((0, 3, 3), dtype=float)
        selected = np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)
        if selected.ndim != 3 or selected.shape[1:] != (3, 3) or selected.shape[0] == 0:
            return np.empty((0, 3, 3), dtype=float)
        normal_local = np.asarray(_unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
        if bool(face.get("flip_normal", False)):
            normal_local = -normal_local
        world = Kraken3DInspector._world_triangles_for_row_pick(
            row,
            selected,
            z_station=z_station,
            transform=transform,
        )
        if world.size == 0:
            return np.empty((0, 3, 3), dtype=float)
        if transform is not None:
            try:
                matrix = np.asarray(transform, dtype=float).reshape(4, 4)
                normal = np.asarray(matrix[:3, :3], dtype=float) @ normal_local[:3]
                normal_norm = float(np.linalg.norm(normal))
                if normal_norm > 1e-12 and np.isfinite(normal_norm):
                    world = world.reshape((-1, 3)) + (normal[:3] / normal_norm) * max(float(scene_radius) * 0.0007, 0.02)
                return world.reshape(selected.shape)
            except Exception:
                return np.empty((0, 3, 3), dtype=float)
        rotation = _rotation_matrix_from_kraken_tilts(
            float(getattr(row, "tilt_x", 0.0)),
            float(getattr(row, "tilt_y", 0.0)),
            float(getattr(row, "tilt_z", 0.0)),
        )
        normal = normal_local @ rotation.T
        normal_norm = float(np.linalg.norm(normal))
        if normal_norm > 1e-12 and np.isfinite(normal_norm):
            world = world.reshape((-1, 3)) + (normal[:3] / normal_norm) * max(float(scene_radius) * 0.0007, 0.02)
        return world.reshape(selected.shape)

    @staticmethod
    def _world_triangles_for_row_pick(
        row,
        triangles: np.ndarray,
        *,
        z_station: float,
        transform=None,
    ) -> np.ndarray:
        selected = np.asarray(triangles, dtype=float)
        if selected.ndim != 3 or selected.shape[1:] != (3, 3) or selected.shape[0] == 0:
            return np.empty((0, 3, 3), dtype=float)
        points = selected.reshape((-1, 3))
        if transform is not None:
            try:
                matrix = np.asarray(transform, dtype=float).reshape(4, 4)
                local_h = np.column_stack((points[:, 0], points[:, 1], points[:, 2], np.ones(points.shape[0], dtype=float)))
                world = (matrix @ local_h.T).T[:, :3]
                if np.all(np.isfinite(world[:, :3])):
                    return world.reshape(selected.shape)
            except Exception:
                return np.empty((0, 3, 3), dtype=float)
        rotation = _rotation_matrix_from_kraken_tilts(
            float(getattr(row, "tilt_x", 0.0)),
            float(getattr(row, "tilt_y", 0.0)),
            float(getattr(row, "tilt_z", 0.0)),
        )
        offset = np.asarray(
            (
                float(getattr(row, "desp_x", 0.0)),
                float(getattr(row, "desp_y", 0.0)),
                float(z_station) + float(getattr(row, "desp_z", 0.0)),
            ),
            dtype=float,
        )
        world = points @ rotation.T + offset
        if not np.all(np.isfinite(world[:, :3])):
            return np.empty((0, 3, 3), dtype=float)
        return world.reshape(selected.shape)

    @staticmethod
    def _polydata_from_triangles(triangles: np.ndarray):
        if pv is None:
            return None
        triangles = np.asarray(triangles, dtype=float)
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
            return None
        points = triangles.reshape((-1, 3))
        if points.shape[0] == 0 or not np.all(np.isfinite(points[:, :3])):
            return None
        faces = np.column_stack(
            (
                np.full(triangles.shape[0], 3, dtype=np.int64),
                np.arange(points.shape[0], dtype=np.int64).reshape((-1, 3)),
            )
        ).ravel()
        return pv.PolyData(points, faces)

    @staticmethod
    def _surface_cell_triangles(mesh) -> np.ndarray:
        if pv is None or mesh is None:
            return np.empty((0, 3, 3), dtype=float)
        try:
            surface = pv.wrap(mesh).extract_surface(algorithm="dataset_surface")
        except Exception:
            try:
                surface = pv.wrap(mesh)
            except Exception:
                return np.empty((0, 3, 3), dtype=float)
        try:
            points = np.asarray(surface.points, dtype=float)
            faces = np.asarray(surface.faces, dtype=np.int64).ravel()
        except Exception:
            return np.empty((0, 3, 3), dtype=float)
        if points.ndim != 2 or points.shape[0] < 3 or points.shape[1] < 3 or faces.size < 4:
            return np.empty((0, 3, 3), dtype=float)
        triangles: list[np.ndarray] = []
        cursor = 0
        while cursor < int(faces.size):
            vertex_count = int(faces[cursor])
            cursor += 1
            if vertex_count < 3 or cursor + vertex_count > int(faces.size):
                break
            indices = np.asarray(faces[cursor : cursor + vertex_count], dtype=np.int64)
            cursor += vertex_count
            if np.any(indices < 0) or np.any(indices >= points.shape[0]):
                continue
            for offset in range(1, vertex_count - 1):
                triangle = points[[indices[0], indices[offset], indices[offset + 1]], :3]
                if np.all(np.isfinite(triangle)):
                    triangles.append(triangle)
        if not triangles:
            return np.empty((0, 3, 3), dtype=float)
        return np.asarray(triangles, dtype=float)

    @staticmethod
    def _runtime_world_face_triangles_for_record(
        system,
        row_index: int,
        face: dict[str, object],
        *,
        scene_radius: float = 1.0,
    ) -> np.ndarray:
        runtime_mesh = _layout_editor_class()._runtime_trace_surface_mesh(system, int(row_index)) if system is not None else None
        if runtime_mesh is None:
            return np.empty((0, 3, 3), dtype=float)
        triangles = Kraken3DInspector._surface_cell_triangles(runtime_mesh)
        if triangles.ndim != 3 or triangles.shape[0] == 0:
            return np.empty((0, 3, 3), dtype=float)
        indices: list[int] = []
        for value in list(face.get("triangle_indices", []) or []):
            try:
                index = int(value)
            except Exception:
                continue
            if 0 <= index < int(triangles.shape[0]):
                indices.append(index)
        if not indices:
            return np.empty((0, 3, 3), dtype=float)
        selected = np.asarray(triangles[np.asarray(indices, dtype=int)], dtype=float)
        if selected.ndim != 3 or selected.shape[1:] != (3, 3) or selected.shape[0] == 0:
            return np.empty((0, 3, 3), dtype=float)
        normals = np.cross(selected[:, 1, :] - selected[:, 0, :], selected[:, 2, :] - selected[:, 0, :])
        normal = np.sum(normals, axis=0)
        norm = float(np.linalg.norm(normal))
        if norm > 1.0e-12 and np.isfinite(norm):
            selected = selected + (normal[:3] / norm) * max(float(scene_radius) * 0.0007, 0.02)
        return selected

    def _add_optical_solid_assigned_face_overlays(self, system=None) -> int:
        if self._renderer is None or pv is None:
            return 0
        z_positions = self.editor._row_z_positions()
        _center, scene_radius = self._scene_bounds()
        count = 0
        for row_index, row in enumerate(self.editor.rows):
            item = self.editor._file_backed_stl_row_at(row_index)
            if item is None:
                continue
            _row, path = item
            try:
                metadata = normalize_optical_solid_face_metadata(
                    (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
                )
                _fmt, triangles = _read_stl_triangle_vertices(path)
                triangles = np.asarray(triangles, dtype=float)
            except Exception as exc:
                self.editor.append_debug(f"3D assigned face overlay unavailable for S{row_index}: {exc}")
                continue
            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
                continue
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            transform = self._runtime_transform_for_row(system, row_index)
            for face in list(metadata.get("faces", []) or []):
                if not isinstance(face, dict):
                    continue
                record = normalize_optical_solid_face_record(face)
                if not self._assigned_optical_solid_face(record):
                    continue
                world_triangles = np.empty((0, 3, 3), dtype=float)
                if not self._row_face_metadata_uses_saved_mesh(row):
                    world_triangles = self._runtime_world_face_triangles_for_record(
                        system,
                        row_index,
                        record,
                        scene_radius=scene_radius,
                    )
                if world_triangles.size == 0:
                    world_triangles = self._world_face_triangles_for_record(
                        row,
                        triangles,
                        record,
                        z_station=z_station,
                        transform=transform,
                        scene_radius=scene_radius,
                    )
                mesh = self._polydata_from_triangles(world_triangles)
                if mesh is None:
                    continue
                function = _normalize_optical_solid_face_function(record.get("function"), legacy_role=record.get("role"))
                role = _legacy_role_from_optical_solid_face_function(function)
                color = optical_solid_face_role_color(role)
                try:
                    self._add_mesh_actor(
                        mesh,
                        color=color,
                        opacity=0.20 if function != OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT else 0.14,
                        flat_shading=True,
                        backface_culling=False,
                        track_row_index=row_index,
                    )
                except Exception:
                    pass
                count += 1
        return count

    @staticmethod
    def _virtual_plane_marker_scale(marker: OpticalSolidVirtualPlaneMarker, scene_radius: float) -> float:
        lower = max(float(scene_radius) * 0.05, 1.5)
        upper = max(float(scene_radius) * 0.28, lower)
        aperture = max(float(marker.aperture_mm), 1.0)
        return float(np.clip(aperture, lower, upper))

    def _add_virtual_plane_marker_actor(self, marker: OpticalSolidVirtualPlaneMarker, *, scene_radius: float) -> bool:
        if pv is None:
            return False
        try:
            center = np.asarray(marker.centroid, dtype=float)
            normal = np.asarray(marker.normal, dtype=float)
            if center.size < 3 or normal.size < 3:
                return False
            norm = float(np.linalg.norm(normal[:3]))
            if norm <= 1e-12 or not np.isfinite(norm):
                return False
            normal = normal[:3] / norm
            size = self._virtual_plane_marker_scale(marker, scene_radius)
            plane = pv.Plane(center=tuple(center[:3]), direction=tuple(normal), i_size=size, j_size=size, i_resolution=1, j_resolution=1)
            self._add_mesh_actor(plane, color=marker.color, opacity=0.16, flat_shading=True)
            try:
                edges = plane.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)
                if int(getattr(edges, "n_points", 0)) > 0:
                    self._add_mesh_actor(edges, color=marker.color, opacity=0.95, line_width=2.0)
            except Exception:
                pass
            self._add_mesh_actor(
                pv.Arrow(start=tuple(center[:3]), direction=tuple(normal), scale=max(size * 0.45, 1.0)),
                color=marker.color,
                opacity=0.94,
                flat_shading=True,
            )
            return True
        except Exception as exc:
            self.editor.append_debug(f"3D optical virtual-plane error: {exc}")
            return False

    def _add_optical_solid_virtual_plane_overlays(self, system=None) -> int:
        if self._renderer is None:
            return 0
        z_positions = self.editor._row_z_positions()
        _center, scene_radius = self._scene_bounds()
        count = 0
        for row_index, row in enumerate(self.editor.rows):
            if self.editor._file_backed_stl_row_at(row_index) is None:
                continue
            z_station = float(z_positions[row_index]) if row_index < len(z_positions) else 0.0
            transform = self._runtime_transform_for_row(system, row_index)
            markers = (
                self._virtual_plane_markers_from_runtime_transform(row, transform, assigned_only=True)
                if transform is not None
                else optical_solid_virtual_plane_world_markers(row, z_station, assigned_only=True)
            )
            for marker in markers:
                if self._add_virtual_plane_marker_actor(marker, scene_radius=scene_radius):
                    count += 1
        return count

    def _visible_actor_bounds(
        self,
        *,
        include_guides: bool = False,
        preferred_keys: set[str] | None = None,
    ) -> np.ndarray | None:
        if self._renderer is None:
            return None
        mins = np.array((np.inf, np.inf, np.inf), dtype=float)
        maxs = np.array((-np.inf, -np.inf, -np.inf), dtype=float)
        found = False

        def consider_actor(actor) -> None:
            nonlocal found, mins, maxs
            if actor is None:
                return
            try:
                if not int(actor.GetVisibility()):
                    return
            except Exception:
                pass
            actor_key = self._actor_key(actor)
            if not include_guides:
                if actor_key is not None and actor_key in self._actor_optical_axis_map:
                    return
                if actor is self._optical_axis_highlight_actor:
                    return
            try:
                bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
            except Exception:
                return
            if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                return
            mins = np.minimum(mins, (bounds[0], bounds[2], bounds[4]))
            maxs = np.maximum(maxs, (bounds[1], bounds[3], bounds[5]))
            found = True

        if preferred_keys:
            for actor_key in sorted(str(key) for key in preferred_keys):
                consider_actor(self._actor_by_key.get(actor_key))
        else:
            actors = self._renderer.GetActors()
            actors.InitTraversal()
            for _ in range(actors.GetNumberOfItems()):
                consider_actor(actors.GetNextActor())
        if not found:
            return None
        return np.asarray((mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]), dtype=float)

    def _camera_fit_bounds(self) -> np.ndarray:
        preferred_keys: set[str] = set()
        for keys in list(self._row_actor_map.values()):
            preferred_keys.update(str(key) for key in list(keys or []))
        for keys in list(self._ray_actor_map.values()):
            preferred_keys.update(str(key) for key in list(keys or []))
        preferred_keys.update(str(key) for key in self._actor_step_map)
        for keys in list(self._step_follow_actor_map.values()):
            preferred_keys.update(str(key) for key in list(keys or []))
        bounds = self._visible_actor_bounds(include_guides=False, preferred_keys=preferred_keys)
        if bounds is None:
            bounds = self._visible_actor_bounds(include_guides=False)
        if bounds is not None:
            return bounds
        try:
            return _finite_bounds_array(self._renderer.ComputeVisiblePropBounds())
        except Exception:
            return _finite_bounds_array(None)

    def _scene_bounds(self) -> tuple[np.ndarray, float]:
        if self._renderer is None:
            return np.zeros(3, dtype=float), 1.0
        bounds = self._visible_actor_bounds(include_guides=False)
        if bounds is None:
            try:
                bounds = np.asarray(self._renderer.ComputeVisiblePropBounds(), dtype=float)
            except Exception:
                bounds = _finite_bounds_array(None)
        if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
            return np.zeros(3, dtype=float), 1.0
        center = np.array(
            [
                0.5 * (bounds[0] + bounds[1]),
                0.5 * (bounds[2] + bounds[3]),
                0.5 * (bounds[4] + bounds[5]),
            ],
            dtype=float,
        )
        radius = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 1.0)
        return center, radius

    def _reset_camera_clipping_range_for_scene(self) -> None:
        if self._renderer is None:
            return
        hidden: list[object] = []
        for actor_key in list(self._actor_optical_axis_map):
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            try:
                if int(actor.GetVisibility()):
                    actor.SetVisibility(False)
                    hidden.append(actor)
            except Exception:
                pass
        actor = self._optical_axis_highlight_actor
        if actor is not None:
            try:
                if int(actor.GetVisibility()):
                    actor.SetVisibility(False)
                    hidden.append(actor)
            except Exception:
                pass
        try:
            self._renderer.ResetCameraClippingRange()
        finally:
            for actor in hidden:
                try:
                    actor.SetVisibility(True)
                except Exception:
                    pass

    def _ensure_parallel_camera_clears_scene(self) -> bool:
        """Keep the camera far enough that the whole scene stays in front of it.

        In parallel projection the camera-to-focal distance does not affect the
        rendered image (only the parallel scale sets the zoom), so we are free to
        dolly the camera back along its view direction. Doing so prevents the far
        scene geometry -- e.g. the converging ray cone's focus at the image plane
        -- from swinging *behind* the camera as the user orbits, where VTK's
        clamped-positive near clip plane would slice it off (bugs/0048). No-op in
        perspective projection, where moving the camera would change the view.
        Returns True if the camera was moved.
        """
        if self._renderer is None:
            return False
        camera = self._renderer.GetActiveCamera()
        if camera is None or not camera.GetParallelProjection():
            return False
        bounds = self._visible_actor_bounds(include_guides=False)
        if (
            bounds is None
            or bounds.size != 6
            or not np.all(np.isfinite(bounds))
            or bounds[0] > bounds[1]
        ):
            return False
        focal = np.asarray(camera.GetFocalPoint(), dtype=float)
        position = np.asarray(camera.GetPosition(), dtype=float)
        view = position - focal
        distance = float(np.linalg.norm(view))
        if distance < 1e-6 or not np.all(np.isfinite(view)):
            return False
        corners = np.array(
            [
                (bounds[i], bounds[j], bounds[k])
                for i in (0, 1)
                for j in (2, 3)
                for k in (4, 5)
            ],
            dtype=float,
        )
        radius = float(
            max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 1.0)
        )
        # Clear the farthest scene corner from the current focal point in any
        # orientation, plus a radius of margin so the near plane never grazes it.
        max_focal_to_corner = float(np.max(np.linalg.norm(corners - focal, axis=1)))
        safe = max(max_focal_to_corner + radius, 50.0)
        if distance >= safe:
            return False
        camera.SetPosition(*(focal + (view / distance) * safe).tolist())
        return True

    def _on_camera_interaction(self, *_args) -> None:
        """Backstop for orbit/zoom: re-clear the scene and refresh the clip range.

        Option A keeps the camera far after every refresh, so a drag normally
        starts far and stays far (rotate preserves distance; parallel zoom only
        changes the scale). This observer covers any residual close-camera case
        and only re-renders when it actually had to move the camera.
        """
        moved = False
        try:
            moved = self._ensure_parallel_camera_clears_scene()
        except Exception:
            moved = False
        try:
            self._reset_camera_clipping_range_for_scene()
        except Exception:
            pass
        if moved:
            self.render()

    def _row_scene_bounds(self) -> tuple[np.ndarray, float]:
        if self._renderer is None:
            return np.zeros(3, dtype=float), 1.0
        mins = np.array((np.inf, np.inf, np.inf), dtype=float)
        maxs = np.array((-np.inf, -np.inf, -np.inf), dtype=float)
        found = False
        for row_index, actor_keys in list(self._row_actor_map.items()):
            try:
                if int(row_index) < 0:
                    continue
            except Exception:
                continue
            for actor_key in list(actor_keys):
                actor = self._actor_by_key.get(actor_key)
                if actor is None:
                    continue
                try:
                    bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
                except Exception:
                    continue
                if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                    continue
                mins = np.minimum(mins, (bounds[0], bounds[2], bounds[4]))
                maxs = np.maximum(maxs, (bounds[1], bounds[3], bounds[5]))
                found = True
        if not found:
            return self._scene_bounds()
        center = 0.5 * (mins + maxs)
        radius = max(float(maxs[0] - mins[0]), float(maxs[1] - mins[1]), float(maxs[2] - mins[2]), 1.0)
        return center, radius

    def _render_aspect(self) -> float:
        if self._vtk_widget is None:
            return 1.4
        try:
            width, height = self._vtk_widget.GetRenderWindow().GetSize()
            return max(float(width) / max(float(height), 1.0), 0.1)
        except Exception:
            return 1.4

    @staticmethod
    def _parallel_scale_for_orthographic_fit(horizontal_span: float, vertical_span: float, aspect: float) -> float:
        aspect = max(float(aspect), 0.1)
        horizontal_scale = float(horizontal_span) / (2.0 * aspect)
        vertical_scale = float(vertical_span) * 0.5
        return max(horizontal_scale, vertical_scale, 1.0) * 1.08

    def set_camera_preset(self, preset: str) -> None:
        self._camera_preset = preset
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        bounds = self._camera_fit_bounds()
        center = np.array(
            [
                0.5 * (bounds[0] + bounds[1]),
                0.5 * (bounds[2] + bounds[3]),
                0.5 * (bounds[4] + bounds[5]),
            ],
            dtype=float,
        )
        radius = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 1.0)
        if bounds.size == 6 and np.all(np.isfinite(bounds)) and bounds[0] <= bounds[1]:
            span_x = float(bounds[1] - bounds[0])
            span_y = float(bounds[3] - bounds[2])
            span_z = float(bounds[5] - bounds[4])
        else:
            span_x = span_y = span_z = radius
        distance = max(radius * 2.2, 50.0)
        aspect = self._render_aspect()
        parallel_scale = None
        # Cardinal viewport naming convention: "+PLANE" / "-PLANE"
        # means LOOKING AT the named plane FROM the +/- normal axis.
        # For example "+yz" -> camera sits on the +X side of the
        # scene looking toward -X, so the YZ plane fills the viewport
        # with +Y up and +Z to the right.
        #
        # Aliases (zy, xy, xz, bottom) kept for backward compatibility
        # with stored preferences and the older toolbar.
        if preset in {"-yz", "zy"}:
            # YZ plane seen from -X side, looking +X.
            position = center + np.array([-distance, 0.0, 0.0], dtype=float)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_z, span_y, aspect)
        elif preset == "+yz":
            # YZ plane seen from +X side, looking -X.
            position = center + np.array([+distance, 0.0, 0.0], dtype=float)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_z, span_y, aspect)
        elif preset in {"+xy", "xy"}:
            # XY plane seen from +Z side, looking -Z (the "top of XY").
            position = center + np.array([0.0, 0.0, +distance], dtype=float)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_x, span_y, aspect)
        elif preset in {"-xy", "bottom"}:
            # XY plane seen from -Z side, looking +Z.
            position = center + np.array([0.0, 0.0, -distance], dtype=float)
            view_up = (0.0, 1.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_x, span_y, aspect)
        elif preset in {"+xz", "xz"}:
            # XZ plane seen from +Y side, looking -Y.
            position = center + np.array([0.0, +distance, 0.0], dtype=float)
            view_up = (1.0, 0.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_z, span_x, aspect)
        elif preset == "-xz":
            # XZ plane seen from -Y side, looking +Y.
            position = center + np.array([0.0, -distance, 0.0], dtype=float)
            view_up = (1.0, 0.0, 0.0)
            parallel_scale = self._parallel_scale_for_orthographic_fit(span_z, span_x, aspect)
        else:
            offset = np.array([-distance * 0.95, distance * 0.55, distance * 0.8], dtype=float)
            position = center + offset
            view_up = (0.0, 1.0, 0.0)
            # bugs/0048: the Iso view must be orthographic like the cardinal
            # presets. A perspective camera sits a finite distance from the
            # scene, so an orbit can swing the far geometry (the image plane and
            # the converging ray cone) behind the camera, where the near clip
            # plane slices it off. Parallel projection renders behind-camera
            # geometry and makes the camera distance visually irrelevant, so the
            # view can never clip on orbit/zoom -- matching the cardinal buttons.
            if bounds.size == 6 and np.all(np.isfinite(bounds)) and bounds[0] <= bounds[1]:
                view_dir = -offset
                view_norm = float(np.linalg.norm(view_dir))
                up_vec = np.array(view_up, dtype=float)
                right = np.cross(view_dir, up_vec)
                right_norm = float(np.linalg.norm(right))
                if view_norm > 1e-9 and right_norm > 1e-9:
                    view_dir = view_dir / view_norm
                    right = right / right_norm
                    true_up = np.cross(right, view_dir)
                    corners = np.array(
                        [
                            (bounds[i], bounds[j], bounds[k])
                            for i in (0, 1)
                            for j in (2, 3)
                            for k in (4, 5)
                        ],
                        dtype=float,
                    )
                    rel = corners - center
                    horizontal_span = float(np.ptp(rel @ right))
                    vertical_span = float(np.ptp(rel @ true_up))
                    parallel_scale = self._parallel_scale_for_orthographic_fit(
                        horizontal_span, vertical_span, aspect
                    )
        camera.SetPosition(*position.tolist())
        camera.SetFocalPoint(*center.tolist())
        camera.SetViewUp(*view_up)
        try:
            camera.SetParallelProjection(1 if parallel_scale is not None else 0)
            if parallel_scale is not None:
                camera.SetParallelScale(float(parallel_scale))
        except Exception:
            pass
        self._reset_camera_clipping_range_for_scene()
        self.render()

    def render(self) -> None:
        if self._vtk_widget is None:
            return
        token = self._timing_start("render")
        try:
            self._vtk_widget.GetRenderWindow().Render()
        except Exception as exc:
            self._timing_finish(token, status="error", error=_short_error_message(exc))
            pass
        else:
            self._timing_finish(token, status="ok")

    def _clear_galvo_scan_animation(self, *, cancel_timer: bool = True, render: bool = False) -> None:
        if cancel_timer:
            after_id = self._galvo_scan_after_id
            self._galvo_scan_after_id = None
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
            self._galvo_scan_frames = []
            self._galvo_scan_frame_index = 0
        if self._renderer is not None:
            for actor in list(self._galvo_scan_actors):
                try:
                    actor_key = self._actor_key(actor)
                    if actor_key is not None:
                        self._actor_by_key.pop(actor_key, None)
                except Exception:
                    pass
                self._remove_renderer_view_prop(actor)
        self._galvo_scan_actors = []
        if render:
            self.render()

    def stop_galvo_scan_animation(self) -> None:
        self._clear_galvo_scan_animation(cancel_timer=True, render=True)
        self.status_var.set("Galvo scan animation stopped.")

    @staticmethod
    def _folded_scan_display_points_to_3d(points, *, orientation: str = "YZ") -> np.ndarray:
        try:
            pts = np.asarray(points, dtype=float)
        except Exception:
            return np.empty((0, 3), dtype=float)
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 2:
            return np.empty((0, 3), dtype=float)
        pts = pts[:, :2]
        if not np.all(np.isfinite(pts)):
            return np.empty((0, 3), dtype=float)
        if str(orientation or "").strip() == "Horizontal":
            return np.column_stack((np.zeros(pts.shape[0]), -pts[:, 0], -pts[:, 1]))
        return np.column_stack((np.zeros(pts.shape[0]), pts[:, 1], pts[:, 0]))

    def _add_galvo_scan_label_actor(self, frame: dict[str, object], color: tuple[float, float, float]) -> None:
        if self._renderer is None or vtkBillboardTextActor3D is None:
            return
        label_point = frame.get("label_point")
        if label_point is None:
            return
        orientation = str(frame.get("orientation", self.editor._current_display_orientation()) or "YZ")
        point = self._folded_scan_display_points_to_3d([label_point], orientation=orientation)
        if point.shape != (1, 3):
            return
        _center, scene_radius = self._scene_bounds()
        label_position = point[0].copy()
        label_position[0] += max(float(scene_radius) * 0.016, 0.45)
        try:
            actor = vtkBillboardTextActor3D()
            actor.SetInput(str(frame.get("label", "galvo scan")))
            actor.SetPosition(float(label_position[0]), float(label_position[1]), float(label_position[2]))
            try:
                actor.PickableOff()
            except Exception:
                pass
            try:
                text_prop = actor.GetTextProperty()
                text_prop.SetFontSize(13)
                text_prop.SetColor(*color)
                text_prop.SetBackgroundColor(1.0, 1.0, 1.0)
                text_prop.SetBackgroundOpacity(0.76)
                text_prop.SetFrame(1)
                text_prop.SetFrameColor(*color)
            except Exception:
                pass
            self._add_renderer_view_prop(actor)
            self._galvo_scan_actors.append(actor)
        except Exception as exc:
            self.editor.append_debug(f"3D galvo scan label skipped: {exc}")

    def _add_galvo_scan_frame_actors(self, frame: dict[str, object]) -> int:
        if self._renderer is None or pv is None:
            return 0
        color = _color_to_rgb_tuple(frame.get("color", "#f97316"))
        orientation = str(frame.get("orientation", self.editor._current_display_orientation()) or "YZ")
        _center, scene_radius = self._scene_bounds()
        ray_inset = _layout_editor_class()._ray_vertex_display_inset(scene_radius)
        count = 0
        for path in list(frame.get("paths", []) or []):
            points_3d = self._folded_scan_display_points_to_3d(path, orientation=orientation)
            mesh = _layout_editor_class()._ray_segment_mesh_for_3d_display(points_3d, vertex_inset=ray_inset)
            if mesh is None or int(getattr(mesh, "n_points", 0)) < 2:
                continue
            actor = self._add_mesh_actor(
                mesh,
                color=color,
                opacity=float(frame.get("alpha", 0.9) or 0.9),
                line_width=max(float(frame.get("linewidth", 1.1) or 1.1) * 2.4, 3.0),
                backface_culling=False,
            )
            if actor is not None:
                self._galvo_scan_actors.append(actor)
                count += 1
        mirror_line = frame.get("mirror_line")
        if mirror_line is not None:
            points_3d = self._folded_scan_display_points_to_3d(mirror_line, orientation=orientation)
            if points_3d.shape[0] >= 2:
                try:
                    mesh = pv.lines_from_points(points_3d[:, :3])
                except Exception:
                    mesh = None
                if mesh is not None and int(getattr(mesh, "n_points", 0)) >= 2:
                    actor = self._add_mesh_actor(
                        mesh,
                        color=color,
                        opacity=0.95,
                        line_width=6.0,
                        backface_culling=False,
                    )
                    if actor is not None:
                        self._galvo_scan_actors.append(actor)
                        count += 1
        self._add_galvo_scan_label_actor(frame, color)
        return count

    def start_galvo_scan_animation(self) -> None:
        if self._renderer is None or pv is None:
            self.status_var.set("Galvo scan animation unavailable: Open 3D renderer is not ready.")
            return
        try:
            max_half = max((max(float(row.diameter) * 0.5, 0.5) for row in self.editor.rows), default=1.0)
            frames = self.editor._folded_scan_overlay_plans(
                max_half,
                system=self.__dict__.get("_current_system"),
            )
        except Exception as exc:
            self.status_var.set(f"Galvo scan animation failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D galvo scan animation failed: {exc}")
            return
        if not frames:
            self.status_var.set("Galvo scan animation unavailable: no folded galvo scan overlay is configured.")
            return
        self._clear_galvo_scan_animation(cancel_timer=True, render=False)
        self._galvo_scan_frames = list(frames)
        self._galvo_scan_frame_index = 0
        self._show_galvo_scan_frame()

    def _show_galvo_scan_frame(self) -> None:
        self._galvo_scan_after_id = None
        if not self._galvo_scan_frames:
            return
        frame_count = len(self._galvo_scan_frames)
        frame_index = int(self._galvo_scan_frame_index) % frame_count
        frame = self._galvo_scan_frames[frame_index]
        self._clear_galvo_scan_animation(cancel_timer=False, render=False)
        actor_count = self._add_galvo_scan_frame_actors(frame)
        label = str(frame.get("label", "") or "").strip()
        tilt = frame.get("tilt_x", None)
        tilt_text = ""
        try:
            tilt_text = f" | TiltX={float(tilt):g} deg"
        except Exception:
            pass
        self.status_var.set(
            f"Galvo scan animation {frame_index + 1}/{frame_count}{tilt_text}"
            f"{' | ' + label if label else ''} | overlay actors={actor_count}"
        )
        self.render()
        self._galvo_scan_frame_index = (frame_index + 1) % frame_count
        try:
            self._galvo_scan_after_id = self.after(720, self._show_galvo_scan_frame)
        except Exception:
            self._galvo_scan_after_id = None

    def save_snapshot(self) -> Path | None:
        if self._vtk_widget is None:
            self.status_var.set("Snapshot unavailable: 3D window is not ready.")
            return None
        try:
            from vtkmodules.vtkIOImage import vtkPNGWriter  # type: ignore
            from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter  # type: ignore

            ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
            selected_path = filedialog.asksaveasfilename(
                parent=self,
                title="Save Open 3D snapshot",
                initialdir=str(ATTACHMENT_DIR),
                initialfile="3D.png",
                defaultextension=".png",
                filetypes=[("PNG image", "*.png")],
            )
            if not selected_path:
                self.status_var.set("Snapshot cancelled")
                return None
            image_path = Path(selected_path).expanduser()
            render_window = self._vtk_widget.GetRenderWindow()
            render_window.Render()
            capture = vtkWindowToImageFilter()
            capture.SetInput(render_window)
            try:
                capture.SetInputBufferTypeToRGBA()
            except Exception:
                pass
            try:
                capture.ReadFrontBufferOff()
            except Exception:
                pass
            capture.Update()
            writer = vtkPNGWriter()
            writer.SetFileName(str(image_path))
            writer.SetInputConnection(capture.GetOutputPort())
            writer.Write()
            if not image_path.exists():
                raise RuntimeError("VTK writer did not create a PNG file")
            self.status_var.set(f"Snapshot saved: {image_path.name}")
            self.editor.append_progress(f"Saved Open 3D snapshot: {image_path}")
            return image_path
        except Exception as exc:
            self.status_var.set(f"Snapshot failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D snapshot failed: {exc}")
            return None

    def _active_mode_badge_text(self) -> str:
        if self._source_target_pick_mode:
            return "SOURCE TARGET\nClick a surface/CAD solid row."
        if self._placement_target_pick_mode:
            if self._placement_target_row_index is not None:
                row_text = f"S{int(self._placement_target_row_index)}"
                face_text = f" [{self._placement_target_face_id}]" if self._placement_target_face_id else ""
                return f"SNAP ROW -> TARGET\n{row_text}{face_text} armed. Click target row/face."
            return "SNAP ROW -> TARGET\nClick movable row/face, then target row/face."
        if self._placement_orient_pick_mode:
            if self._placement_orient_row_index is not None:
                row_text = f"S{int(self._placement_orient_row_index)}"
                face_text = f" [{self._placement_orient_face_id}]" if self._placement_orient_face_id else ""
                return f"ORIENT ROW -> TARGET\n{row_text}{face_text} armed. Click target normal."
            return "ORIENT ROW -> TARGET\nClick movable row/face, then target row/face."
        if self._placement_orient_ray_mode:
            if self._placement_orient_ray_row_index is not None:
                row_text = f"S{int(self._placement_orient_ray_row_index)}"
                face_text = f" [{self._placement_orient_ray_face_id}]" if self._placement_orient_ray_face_id else ""
                return f"ORIENT ROW -> RAY\n{row_text}{face_text} armed. Click target ray."
            return "ORIENT ROW -> RAY\nClick movable row/face, then target ray."
        if bool(getattr(self.editor, "_cad_led_object_edge_pick", False)):
            return "OBJ -> LED\nClick the LED object-edge feature."
        requested_label = getattr(self.editor, "_cad_axis_pick_label", None)
        axis_pick_any = bool(getattr(self.editor, "_cad_axis_pick_any", False))
        if requested_label in STEP_OVERLAY_LABEL_SET:
            return f"CENTER {str(requested_label).upper()} STEP\nClick a STEP feature or KrakenOS surface."
        if axis_pick_any:
            selected_label = getattr(self.editor, "_selected_step_label", None)
            if selected_label in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(str(selected_label)) is not None:
                return f"CENTER STEP AXIS\nClick a STEP feature, or surface for {str(selected_label).upper()}."
            return "CENTER STEP AXIS\nClick a planar/circular STEP feature."
        if self._step_carry_snap_ray_mode:
            snap_label = self._step_carry_label() or str(self.editor._selected_step_label or "").strip().lower()
            snap_text = str(snap_label).upper() if snap_label in STEP_OVERLAY_LABEL_SET else "STEP"
            return f"SNAP {snap_text} STEP -> RAY\nClick a traced ray point."
        if self._step_carry_snap_target_mode:
            snap_label = self._step_carry_label() or str(self.editor._selected_step_label or "").strip().lower()
            snap_text = str(snap_label).upper() if snap_label in STEP_OVERLAY_LABEL_SET else "STEP"
            return f"SNAP {snap_text} STEP -> TARGET\nClick detector/object/target row or face."
        if self._dimension_anchor_pick_mode:
            state = self._dimension_anchor_pick_state if isinstance(self._dimension_anchor_pick_state, dict) else {}
            label = self._dimension_anchor_display_label(int(state.get("row_index", -1)))
            return f"RE-ANCHOR {label} DIMENSION\nMove onto a surface/edge, click to set. Esc cancels."
        if self._step_normal_axis_pick_mode:
            label = str(self._selected_step_feature_label or self.editor._selected_step_label or "STEP").upper()
            mode_text = str(getattr(self, "_step_normal_axis_anchor_mode", "body_center")).strip().lower()
            if mode_text == "pick_point":
                anchor = "PICK POINT"
            elif mode_text == "surface_center":
                anchor = "SURFACE CENTER"
            else:
                anchor = "BODY CENTER"
            return f"SNAP {label} {anchor} NORMAL -> AXIS\nClick the dotted Optical Axis guide."
        if self._step_surface_center_axis_pick_mode:
            label = str(self._selected_step_feature_label or self.editor._selected_step_label or "STEP").upper()
            return f"CENTER {label} SURFACE -> AXIS\nClick the dotted Optical Axis guide."
        carry_label = self._step_carry_label()
        if carry_label is not None:
            carry_text = self.editor._step_overlay_display_label(carry_label).upper()
            return f"CARRY {carry_text} STEP\nHold-drag STEP to move freely on the 3D plane; release to drop."
        if self._center_row_to_ray_mode:
            if self._center_row_to_ray_index is not None:
                return f"CENTER ROW -> OPTICAL AXIS\nS{int(self._center_row_to_ray_index)} armed. Click Optical Axis."
            return "CENTER ROW -> OPTICAL AXIS\nClick surface/CAD row, then Optical Axis."
        return ""

    def _update_mode_badge(self, *, render: bool = True) -> None:
        if self._renderer is None:
            return
        text = self._active_mode_badge_text()
        actor = self._mode_badge_actor
        if not text:
            if actor is not None:
                self._remove_renderer_view_prop(actor)
                self._mode_badge_actor = None
                if render:
                    self.render()
            return
        if actor is None and vtkTextActor is not None:
            try:
                actor = vtkTextActor()
                prop = actor.GetTextProperty()
                prop.SetFontSize(16)
                prop.SetBold(True)
                prop.SetColor(1.0, 1.0, 1.0)
                try:
                    prop.SetBackgroundColor(0.05, 0.09, 0.16)
                    prop.SetBackgroundOpacity(0.84)
                    prop.SetFrame(1)
                    prop.SetFrameColor(0.99, 0.67, 0.16)
                except Exception:
                    pass
                actor.SetPickable(False)
                self._add_renderer_view_prop(actor)
                self._mode_badge_actor = actor
            except Exception as exc:
                self.editor.append_debug(f"3D mode badge unavailable: {exc}")
                self._mode_badge_actor = None
                return
        if actor is None:
            return
        try:
            actor.SetInput(text)
            height = 720
            if self._vtk_widget is not None:
                _width, height = self._vtk_widget.GetRenderWindow().GetSize()
            line_count = max(text.count("\n") + 1, 1)
            actor.SetDisplayPosition(16, max(int(height) - 28 - (line_count * 22), 16))
            actor.SetVisibility(True)
        except Exception as exc:
            self.editor.append_debug(f"3D mode badge update failed: {exc}")
            return
        if render:
            self.render()

    @staticmethod
    def _trace_terminal_label(status: str) -> str:
        status = str(status or "").strip().lower()
        labels = {
            "hit_detector": "detector hit",
            "detector": "detector hit",
            "missed_detector": "detector miss",
            "miss_detector": "detector miss",
            "absorbed": "absorbed",
            "stopped": "stopped",
            "escaped": "escaped",
            "terminated": "terminated",
            "unknown": "unknown",
        }
        return labels.get(status, status.replace("_", " ") or "unknown")

    def _trace_summary_text(
        self,
        terminal_counts: dict[str, int],
        *,
        ray_count: int,
        bounded_ray_count: int,
        suppressed_endpoint_count: int,
        terminal_face_counts: dict[str, int] | None = None,
        terminal_sequence_counts: dict[str, int] | None = None,
    ) -> str:
        if int(ray_count) <= 0 and not terminal_counts:
            return ""
        ordered = [
            "hit_detector",
            "detector",
            "missed_detector",
            "absorbed",
            "stopped",
            "escaped",
            "terminated",
            "unknown",
        ]
        parts: list[str] = []
        seen: set[str] = set()
        for status in ordered:
            count = int(terminal_counts.get(status, 0) or 0)
            if count <= 0:
                continue
            seen.add(status)
            parts.append(f"{self._trace_terminal_label(status)}={count}")
        for status in sorted(str(key) for key in terminal_counts):
            if status in seen:
                continue
            count = int(terminal_counts.get(status, 0) or 0)
            if count > 0:
                parts.append(f"{self._trace_terminal_label(status)}={count}")
        if not parts:
            parts.append("no terminal events")
        suffix: list[str] = []
        if int(bounded_ray_count) > 0:
            suffix.append(f"bounded={int(bounded_ray_count)}")
        if int(suppressed_endpoint_count) > 0:
            suffix.append(f"endpoint markers hidden={int(suppressed_endpoint_count)}")
        face_parts: list[str] = []
        for label, count in sorted(
            (dict(terminal_face_counts or {})).items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:3]:
            text_label = str(label or "").strip()
            if text_label and int(count) > 0:
                face_parts.append(f"{text_label}={int(count)}")
        if face_parts:
            suffix.append("last hit " + ", ".join(face_parts))
        text = f"Ray terminals: {int(ray_count)} rays | " + ", ".join(parts)
        if suffix:
            text += " | " + ", ".join(suffix)
        sequence_parts: list[str] = []
        for label, count in sorted(
            (dict(terminal_sequence_counts or {})).items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        )[:2]:
            text_label = str(label or "").strip()
            if text_label and int(count) > 0:
                sequence_parts.append(f"{text_label}={int(count)}")
        if sequence_parts:
            text += "\nPath: " + "; ".join(sequence_parts)
        return text

    @staticmethod
    def _ray_path_terminal_face_summary(ray_path) -> str:
        surface_events = [
            event
            for event in list(getattr(ray_path, "events", []) or [])
            if str(getattr(event, "event_kind", "") or "") == "surface"
        ]
        if not surface_events:
            return ""
        event = surface_events[-1]
        metadata = getattr(event, "metadata", {}) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        face_id = str(
            getattr(event, "mesh_face_id", "")
            or metadata.get("mesh_face_id", "")
            or metadata.get("face_id", "")
            or ""
        ).strip()
        event_type = str(getattr(event, "event_type", "") or "").strip().lower()
        if not face_id:
            try:
                surface_id = int(getattr(event, "surface_id"))
                face_id = f"S{surface_id}"
            except Exception:
                face_id = "surface"
        if event_type:
            return f"{face_id} {event_type}"
        return face_id

    @staticmethod
    def _ray_path_surface_sequence_summary(ray_path, *, max_events: int = 6) -> str:
        def _event_face_id(event) -> str:
            metadata = getattr(event, "metadata", {}) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            face_id = str(
                getattr(event, "mesh_face_id", "")
                or metadata.get("mesh_face_id", "")
                or metadata.get("face_id", "")
                or ""
            ).strip()
            if face_id:
                return face_id
            try:
                surface_id = int(getattr(event, "surface_id"))
                return f"S{surface_id}"
            except Exception:
                return "surface"

        def _event_action(event) -> str:
            label = str(getattr(event, "event_type", "") or "").strip().lower()
            if label == "reflect_tir":
                return "TIR"
            if label in {"reflect_mirror", "reflection", "reflect"}:
                return "reflect"
            if label in {"refraction", "refract"}:
                return "refract"
            if label in {"transmission", "transmit"}:
                return "transmit"
            if label in {"absorb", "absorption"}:
                return "absorb"
            return label.replace("_", " ") if label else "hit"

        surface_events = [
            event
            for event in list(getattr(ray_path, "events", []) or [])
            if str(getattr(event, "event_kind", "") or "") == "surface"
        ]
        if not surface_events:
            return ""
        parts: list[str] = []
        for event in surface_events[: max(1, int(max_events))]:
            parts.append(f"{_event_face_id(event)} {_event_action(event)}")
        if len(surface_events) > len(parts):
            parts.append("...")
        return " -> ".join(parts)

    def _update_trace_summary(
        self,
        terminal_counts: dict[str, int] | None = None,
        *,
        ray_count: int = 0,
        bounded_ray_count: int = 0,
        suppressed_endpoint_count: int = 0,
        terminal_face_counts: dict[str, int] | None = None,
        terminal_sequence_counts: dict[str, int] | None = None,
        render: bool = True,
    ) -> None:
        if self._renderer is None:
            return
        text = self._trace_summary_text(
            terminal_counts or {},
            ray_count=int(ray_count),
            bounded_ray_count=int(bounded_ray_count),
            suppressed_endpoint_count=int(suppressed_endpoint_count),
            terminal_face_counts=terminal_face_counts,
            terminal_sequence_counts=terminal_sequence_counts,
        )
        actor = self._trace_summary_actor
        if actor is not None:
            self._remove_renderer_view_prop(actor)
            self._trace_summary_actor = None
            if render:
                self.render()
        if not text:
            return
        try:
            status_text = " | ".join(part.strip() for part in str(text).splitlines() if part.strip())
            if status_text:
                # Preserve the "3D scene ready | surfaces=N | rays=M ..." prefix
                # that refresh_scene just set, instead of clobbering it -- users
                # (and tests) rely on the surface/ray counts being readable in
                # the status bar after a refresh.
                existing = ""
                try:
                    existing = str(self.status_var.get() or "").strip()
                except Exception:
                    existing = ""
                if existing.startswith("3D scene ready"):
                    self.status_var.set(f"{existing} | {status_text}")
                else:
                    self.status_var.set(status_text)
        except Exception as exc:
            self.editor.append_debug(f"3D ray terminal summary update failed: {exc}")

    @staticmethod
    def _scene_placement_point(values: object) -> np.ndarray | None:
        try:
            point = np.asarray(values, dtype=float).reshape(-1)
        except Exception:
            return None
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return None
        return np.asarray(point[:3], dtype=float)

    def _row_display_actor_center(self, row_index: int, *, body_only: bool = False) -> np.ndarray | None:
        try:
            row_index = int(row_index)
        except Exception:
            return None
        actor_keys = list(dict.fromkeys(self._row_actor_map.get(row_index, []) or []))
        if not actor_keys:
            return None

        def combined_center(*, require_body: bool) -> np.ndarray | None:
            bounds_list: list[np.ndarray] = []
            for actor_key in actor_keys:
                actor = self._actor_by_key.get(actor_key)
                if actor is None:
                    continue
                if require_body and not bool(getattr(actor, "_kraken_file_backed_row_body", False)):
                    continue
                try:
                    bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
                except Exception:
                    continue
                if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                    continue
                bounds_list.append(bounds)
            if not bounds_list:
                return None
            stacked = np.vstack(bounds_list)
            merged = np.asarray(
                (
                    np.min(stacked[:, 0]),
                    np.max(stacked[:, 1]),
                    np.min(stacked[:, 2]),
                    np.max(stacked[:, 3]),
                    np.min(stacked[:, 4]),
                    np.max(stacked[:, 5]),
                ),
                dtype=float,
            )
            center = np.asarray(
                (
                    0.5 * (merged[0] + merged[1]),
                    0.5 * (merged[2] + merged[3]),
                    0.5 * (merged[4] + merged[5]),
                ),
                dtype=float,
            )
            return center if np.all(np.isfinite(center[:3])) else None

        body_center = combined_center(require_body=True)
        if body_center is not None:
            return body_center
        if bool(body_only):
            return None
        return combined_center(require_body=False)

    def _row_display_body_extent(self, row_index: int) -> float | None:
        """Largest world bounding-box dimension of a row's *visible solid body*,
        excluding gizmo / overlay / label actors. The placement gizmo is sized
        from this so it fits the object (the glass), not the scene grid.

        Accepts any of the three body markers a row body can carry: a
        file-backed STL/STEP solid, an analytic glassy lens drum, or a dense
        round-lens-like optical solid. A STEP promoted to an analytic-lens row
        carries the glassy / round-lens marker but NOT the file-backed one, so
        keying off the file marker alone (as ``_row_display_actor_center``'s
        body branch does) would miss it and the gizmo would fall back to the
        grid extent -- the bugs/0006 'arrows shrink on promotion' regression.
        Returns None when the row has no such body actor.
        """
        try:
            row_index = int(row_index)
        except Exception:
            return None
        actor_keys = list(dict.fromkeys(self._row_actor_map.get(row_index, []) or []))
        if not actor_keys:
            return None
        body_markers = (
            "_kraken_file_backed_row_body",
            "_kraken_glassy_lens_body",
            "_kraken_round_lens_like_step_body",
        )
        bounds_list: list[np.ndarray] = []
        for actor_key in actor_keys:
            actor = self._actor_by_key.get(actor_key)
            if actor is None:
                continue
            if not any(bool(getattr(actor, marker, False)) for marker in body_markers):
                continue
            try:
                bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
            except Exception:
                continue
            if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                continue
            bounds_list.append(bounds)
        if not bounds_list:
            return None
        stacked = np.vstack(bounds_list)
        extent = max(
            float(np.max(stacked[:, 1]) - np.min(stacked[:, 0])),
            float(np.max(stacked[:, 3]) - np.min(stacked[:, 2])),
            float(np.max(stacked[:, 5]) - np.min(stacked[:, 4])),
            1.0,
        )
        return float(extent)

    @staticmethod
    def _transform_translate_arrow_length(extent: float) -> float:
        """Length of a Move-gizmo translate arrow, sized so it clears the
        rotation arcs and stays grabbable. Driven by the *body* extent (the
        visible solid's bounding box), never the scene-grid extent: a STEP
        promoted to an analytic-lens row must keep the same big arrows it had
        as a STEP overlay rather than shrinking to a grid-scaled stub
        (bugs/0006). Mirrors ``Open3DStepRotationHandleService``'s arrow length
        exactly so the gizmo looks identical before and after promotion.
        """
        extent = max(float(extent), 1.0)
        arc_radius = max(extent * 0.62, 3.0)
        return max(extent * 1.05, arc_radius * 1.55)

    def _scene_placements_for_3d(self, scene_bundle: SceneBundle | None) -> list[ScenePlacement3D]:
        if (
            scene_bundle is not None
            and scene_bundle is self.editor.__dict__.get("_last_saved_step_native_scene_bundle")
        ):
            try:
                return build_scene_placements(self.editor.rows, targets=None)
            except Exception:
                return []
        placements = list(getattr(scene_bundle, "placements", []) or []) if scene_bundle is not None else []
        if placements:
            return placements
        try:
            return build_scene_placements(
                self.editor.rows,
                targets=list(getattr(scene_bundle, "targets", []) or []) if scene_bundle is not None else None,
            )
        except Exception:
            return []

    def _primary_scene_placement_for_grid(self, placements: list[ScenePlacement3D]) -> ScenePlacement3D | None:
        visible = [placement for placement in placements if bool(getattr(placement, "grid_visible", True))]
        if not visible:
            return None
        selected_row = self.editor._current_selected_row_index()
        if selected_row is not None:
            for placement in visible:
                try:
                    if int(placement.row_index) == int(selected_row):
                        return placement
                except Exception:
                    continue
        return visible[0]

    @staticmethod
    def _grid_offsets(half_extent: float, spacing: float) -> np.ndarray:
        half = max(float(half_extent), 1.0)
        step = max(float(spacing), 1e-6)
        if half / step > 60:
            step = half / 60.0
        count = int(np.floor(half / step))
        offsets = np.arange(-count, count + 1, dtype=float) * step
        return np.asarray(offsets, dtype=float)

    @staticmethod
    def _add_polyline_segment(points: list[tuple[float, float, float]], lines: list[int], start, end) -> None:
        start_point = tuple(float(value) for value in np.asarray(start, dtype=float).reshape(-1)[:3])
        end_point = tuple(float(value) for value in np.asarray(end, dtype=float).reshape(-1)[:3])
        index = len(points)
        points.extend([start_point, end_point])
        lines.extend([2, index, index + 1])

    def _scene_placement_grid_mesh(self, center: np.ndarray, spacing: float, extent: float):
        if pv is None:
            return None
        half = max(float(extent) * 0.5, max(float(spacing), 1.0))
        offsets = self._grid_offsets(half, spacing)
        x0, x1 = float(center[0] - half), float(center[0] + half)
        y0, y1 = float(center[1] - half), float(center[1] + half)
        z0, z1 = float(center[2] - half), float(center[2] + half)
        points: list[tuple[float, float, float]] = []
        lines: list[int] = []
        for offset in offsets:
            x = float(center[0] + offset)
            y = float(center[1] + offset)
            z = float(center[2] + offset)
            self._add_polyline_segment(points, lines, (x, y0, center[2]), (x, y1, center[2]))
            self._add_polyline_segment(points, lines, (x0, y, center[2]), (x1, y, center[2]))
            self._add_polyline_segment(points, lines, (x, center[1], z0), (x, center[1], z1))
            self._add_polyline_segment(points, lines, (x0, center[1], z), (x1, center[1], z))
            self._add_polyline_segment(points, lines, (center[0], y, z0), (center[0], y, z1))
            self._add_polyline_segment(points, lines, (center[0], y0, z), (center[0], y1, z))
        for start, end in (
            ((x0, center[1], center[2]), (x1, center[1], center[2])),
            ((center[0], y0, center[2]), (center[0], y1, center[2])),
            ((center[0], center[1], z0), (center[0], center[1], z1)),
        ):
            self._add_polyline_segment(points, lines, start, end)
        try:
            return pv.PolyData(np.asarray(points, dtype=float), lines=np.asarray(lines, dtype=np.int64))
        except Exception:
            return None

    def _add_step_carry_grid_overlay(self, label: str, mesh) -> tuple[int, str]:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            return 0, ""
        spacing = self._step_carry_grid_spacing(label, mesh)
        self._step_carry_grid_label = label
        self._step_carry_grid_spacing_mm = float(spacing)
        offset = self.editor._step_placement_offset_xyz(label)
        summary = (
            f"STEP carry: {label.upper()} | free plane movement | "
            f"offset ({offset[0]:.6g}, {offset[1]:.6g}, {offset[2]:.6g}) mm | "
            "Ctrl+drag rotates view"
        )
        return 1, summary

    def _add_scene_placement_grid_overlays(self, scene_bundle: SceneBundle | None) -> tuple[int, str]:
        placements = self._scene_placements_for_3d(scene_bundle)
        primary = self._primary_scene_placement_for_grid(placements)
        if primary is None:
            return 0, ""
        center = self._scene_placement_point(getattr(primary, "center_world", None))
        if center is None:
            centers = [
                point
                for point in (
                    self._scene_placement_point(getattr(placement, "center_world", None))
                    for placement in placements
                )
                if point is not None
            ]
            center = np.mean(np.asarray(centers, dtype=float), axis=0) if centers else np.zeros(3, dtype=float)
        try:
            primary_row = int(primary.row_index)
        except Exception:
            primary_row = -1
        live_step_labels_by_row = self._live_trace_step_overlay_label_by_row()
        if primary_row in live_step_labels_by_row:
            label = str(live_step_labels_by_row.get(primary_row, "")).upper()
            return 0, f"Placement handles: transient {label} STEP uses STEP carry/rotation handles."
        if primary_row >= 0:
            display_center = self._row_display_actor_center(primary_row, body_only=True)
            if display_center is None:
                # Tier 2 STL rows can carry a transient runtime expansion that
                # strips the file-backed marker from the actor; fall back to
                # the row's combined actor bounds so the handles still ride on
                # the visible body rather than on the row's logical pose.
                try:
                    is_file_backed = self._render_row_file_backed(self.editor.rows, primary_row)
                except Exception:
                    is_file_backed = False
                if is_file_backed:
                    display_center = self._row_display_actor_center(primary_row, body_only=False)
            if display_center is not None:
                center = display_center
        spacing = max(float(getattr(primary, "grid_spacing_mm", 10.0) or 10.0), 1e-6)
        extent = max(float(getattr(primary, "grid_extent_mm", spacing) or spacing), spacing)
        if bool(getattr(primary, "snap_enabled", False)):
            snap_text = (
                f"snap {float(getattr(primary, 'snap_mm', 0.0) or 0.0):.6g} mm / "
                f"{float(getattr(primary, 'snap_deg', 0.0) or 0.0):.6g} deg"
            )
        else:
            snap_text = "snap off"
        row_text = f"S{int(primary.row_index)}" if getattr(primary, "row_index", None) is not None else "scene"
        summary = (
            f"Placement handles: {row_text} | spacing {spacing:.6g} mm | extent {extent:.6g} mm | "
            f"{snap_text} | placements {len(placements)}"
        )
        handle_count = self._add_scene_placement_translate_handles(primary, center=center, spacing=spacing, extent=extent)
        handle_count += self._add_scene_placement_rotate_handles(primary, center=center, spacing=spacing, extent=extent)
        if handle_count:
            summary += f" | handles {handle_count}"
        return 0, summary

    def _add_scene_detector_overlays(
        self,
        scene_bundle: SceneBundle | None,
        *,
        include_footprints: bool = True,
        include_miss_crosshairs: bool = True,
    ) -> int:
        count = 0
        display_center, display_radius = self._row_scene_bounds()
        for spec in self.editor._scene_detector_overlay_specs(
            scene_bundle,
            include_footprints=bool(include_footprints),
            include_miss_crosshairs=bool(include_miss_crosshairs),
            cap_miss_crosshairs_to_scene=True,
            display_center=display_center,
            display_radius=display_radius,
        ):
            try:
                points = np.asarray(spec["points"], dtype=float)
                if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                    continue
                mesh = pv.lines_from_points(points[:, :3])
            except Exception:
                continue
            if int(getattr(mesh, "n_points", 0)) < 2:
                continue
            try:
                self._add_mesh_actor(
                    mesh,
                    color=tuple(spec["color"]),
                    opacity=float(spec["opacity"]),
                    pick_row_index=spec.get("row_index") if spec.get("pickable", False) else None,
                    line_width=float(spec["line_width"]),
                )
                count += 1
            except Exception:
                continue
        return count

    def _add_thickness_dimension_overlays(self, system, scene_bundle: SceneBundle | None) -> int:
        return self._open3d_thickness_dimension_service().add_overlays(system, scene_bundle)

    def _quick_estimation_overlay_service(self):
        service = getattr(self, "_quick_estimation_overlay_service_instance", None)
        if service is None:
            from KrakenOS.UI.services.quick_estimation_overlay import QuickEstimationOverlayService

            service = QuickEstimationOverlayService(self, pv_module=pv)
            self._quick_estimation_overlay_service_instance = service
        return service

    def _add_quick_estimation_overlays(self, system, scene_bundle: SceneBundle | None) -> int:
        try:
            return self._quick_estimation_overlay_service().add_overlays(system, scene_bundle)
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Quick Estimation overlays skipped: {exc}")
            return 0

    def _detector_coverage_overlay_service(self):
        service = getattr(self, "_detector_coverage_overlay_service_instance", None)
        if service is None:
            from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

            service = DetectorCoverageOverlayService(self, pv_module=pv)
            self._detector_coverage_overlay_service_instance = service
        return service

    def _add_detector_coverage_overlays(self, system, scene_bundle: SceneBundle | None) -> int:
        try:
            return self._detector_coverage_overlay_service().add_overlays(system, scene_bundle)
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Detector coverage overlays skipped: {exc}")
            return 0

    # -- scene-component browser hide/unhide -------------------------------
    def _set_actor_keys_visible(self, actor_keys, visible: bool) -> None:
        by_key = self.__dict__.get("_actor_by_key", {}) or {}
        for key in actor_keys or []:
            actor = by_key.get(key)
            if actor is None:
                continue
            try:
                actor.SetVisibility(1 if visible else 0)
            except Exception:
                pass

    def _all_actor_keys_for_step_label(self, label) -> set:
        """Every actor tied to an imported STEP label: body (pick), feature
        edges + follow actors, and the selection rotation handles. The edges and
        gizmo register only in the follow / rotate maps, not _step_actor_map, so
        a body-only hide left them behind as residual."""
        label = str(label).strip().lower()
        keys: set = set()
        keys.update(self.__dict__.get("_step_actor_map", {}).get(label, []) or [])
        keys.update(self.__dict__.get("_step_follow_actor_map", {}).get(label, []) or [])
        for key, lbl in (self.__dict__.get("_actor_step_map", {}) or {}).items():
            if str(lbl).strip().lower() == label:
                keys.add(key)
        for key, lbl in (self.__dict__.get("_actor_step_follow_map", {}) or {}).items():
            if str(lbl).strip().lower() == label:
                keys.add(key)
        for key, info in (self.__dict__.get("_actor_step_rotate_map", {}) or {}).items():
            try:
                if str(info[0]).strip().lower() == label:
                    keys.add(key)
            except Exception:
                pass
        return keys

    def _all_actor_keys_for_row(self, row_index: int) -> set:
        row_index = int(row_index)
        keys: set = set(self.__dict__.get("_row_actor_map", {}).get(row_index, []) or [])
        for key, idx in (self.__dict__.get("_actor_row_map", {}) or {}).items():
            try:
                if int(idx) == row_index:
                    keys.add(key)
            except (TypeError, ValueError):
                pass
        return keys

    def _apply_scene_element_visibility(self) -> None:
        """Re-hide the elements the browser marked hidden (actors are rebuilt
        each full refresh, so visibility must be re-applied)."""
        for row_index in list(self._hidden_scene_rows):
            self._set_actor_keys_visible(self._all_actor_keys_for_row(int(row_index)), False)
        for label in list(self._hidden_step_labels):
            self._set_actor_keys_visible(self._all_actor_keys_for_step_label(str(label)), False)

    def is_scene_row_hidden(self, row_index: int) -> bool:
        return int(row_index) in self._hidden_scene_rows

    def is_step_label_hidden(self, label: str) -> bool:
        return str(label).strip().lower() in self._hidden_step_labels

    def set_scene_rows_hidden(self, rows, hidden: bool) -> None:
        for row_index in rows or []:
            try:
                idx = int(row_index)
            except (TypeError, ValueError):
                continue
            if hidden:
                self._hidden_scene_rows.add(idx)
            else:
                self._hidden_scene_rows.discard(idx)
            self._set_actor_keys_visible(self._all_actor_keys_for_row(idx), not hidden)
        try:
            self.render()
        except Exception:
            pass

    def set_step_label_hidden(self, label: str, hidden: bool) -> None:
        label = str(label).strip().lower()
        if hidden:
            self._hidden_step_labels.add(label)
            self._set_actor_keys_visible(self._all_actor_keys_for_step_label(label), False)
            try:
                self.render()
            except Exception:
                pass
        else:
            self._hidden_step_labels.discard(label)
            # while hidden the step's heavy mesh was SKIPPED in the rebuild, so there is no actor to
            # re-show -- rebuild the overlay now. Fall back to the show-actors path if that's unavailable.
            try:
                self.refresh_imported_step_overlay(label)
            except Exception:
                try:
                    self._set_actor_keys_visible(self._all_actor_keys_for_step_label(label), True)
                    self.render()
                except Exception:
                    pass

    @staticmethod
    def _scene_placement_translate_step(placement: ScenePlacement3D, spacing: float) -> float:
        if bool(getattr(placement, "snap_enabled", False)):
            step = float(getattr(placement, "snap_mm", spacing) or spacing)
        else:
            step = float(spacing)
        return max(abs(float(step)), 1e-6)

    @staticmethod
    def _scene_placement_rotate_step(placement: ScenePlacement3D) -> float:
        if bool(getattr(placement, "snap_enabled", False)):
            step = float(getattr(placement, "snap_deg", 5.0) or 5.0)
        else:
            step = 15.0
        return max(abs(float(step)), 1e-6)

    def _add_scene_placement_translate_handles(
        self,
        placement: ScenePlacement3D,
        *,
        center: np.ndarray,
        spacing: float,
        extent: float,
    ) -> int:
        if pv is None:
            return 0
        try:
            row_index = int(placement.row_index)
        except Exception:
            return 0
        if not (0 <= row_index < len(self.editor.rows)):
            return 0
        step = self._scene_placement_translate_step(placement, spacing)
        body_extent = self._row_display_body_extent(row_index)
        if body_extent is not None:
            # File-backed / promoted-lens row: size the arrow to the visible
            # body so it matches the STEP overlay's big arrows instead of
            # shrinking to a grid-scaled stub when the STEP is promoted to a
            # row (bugs/0006).
            length = self._transform_translate_arrow_length(body_extent)
        else:
            # Abstract scene placement with no rendered body: keep the
            # grid-scaled arrow.
            length = max(min(max(float(extent) * 0.18, float(spacing) * 1.5), max(float(extent) * 0.35, 1.0)), 1.0)
        radius = max(length * 0.035, 0.08)
        axes = (
            ("x", np.asarray((1.0, 0.0, 0.0), dtype=float), (0.88, 0.18, 0.18)),
            ("y", np.asarray((0.0, 1.0, 0.0), dtype=float), (0.12, 0.62, 0.24)),
            ("z", np.asarray((0.0, 0.0, 1.0), dtype=float), (0.18, 0.35, 0.88)),
        )
        count = 0
        for axis, direction, color in axes:
            for sign in (-1.0, 1.0):
                try:
                    start = np.asarray(center, dtype=float).reshape(3) + direction * sign * radius * 2.0
                    arrow = pv.Arrow(
                        start=tuple(float(value) for value in start),
                        direction=tuple(float(value) for value in direction * sign),
                        scale=float(length),
                    )
                except Exception:
                    continue
                actor = self._add_mesh_actor(
                    arrow,
                    color=color,
                    opacity=0.82 if sign > 0 else 0.55,
                    pick_placement_move=(row_index, axis, float(sign * step)),
                    flat_shading=True,
                )
                if actor is not None:
                    count += 1
        return count

    @staticmethod
    def _scene_placement_rotation_basis(axis: str) -> tuple[np.ndarray, np.ndarray] | None:
        axis_key = str(axis or "").strip().lower()
        if axis_key == "x":
            return np.asarray((0.0, 1.0, 0.0), dtype=float), np.asarray((0.0, 0.0, 1.0), dtype=float)
        if axis_key == "y":
            return np.asarray((0.0, 0.0, 1.0), dtype=float), np.asarray((1.0, 0.0, 0.0), dtype=float)
        if axis_key == "z":
            return np.asarray((1.0, 0.0, 0.0), dtype=float), np.asarray((0.0, 1.0, 0.0), dtype=float)
        return None

    def _scene_placement_rotation_arc_mesh(
        self,
        *,
        center: np.ndarray,
        axis: str,
        sign: float,
        radius: float,
        tube_radius: float,
        include_arrowheads: bool = True,
    ):
        if pv is None:
            return None
        basis = self._scene_placement_rotation_basis(axis)
        if basis is None:
            return None
        u_axis, v_axis = basis
        if float(sign) >= 0.0:
            angles = np.linspace(np.deg2rad(-90.0), np.deg2rad(90.0), 36)
        else:
            angles = np.linspace(np.deg2rad(90.0), np.deg2rad(270.0), 36)
        center_vec = np.asarray(center, dtype=float).reshape(3)
        points = [
            tuple(float(value) for value in center_vec + float(radius) * (np.cos(theta) * u_axis + np.sin(theta) * v_axis))
            for theta in angles
        ]
        if len(points) < 2:
            return None
        lines = [len(points), *range(len(points))]
        try:
            poly = pv.PolyData(np.asarray(points, dtype=float), lines=np.asarray(lines, dtype=np.int64))
        except Exception:
            return None
        try:
            parts = [poly.tube(radius=float(tube_radius), n_sides=10)]
        except Exception:
            parts = [poly]
        if include_arrowheads:
            try:
                point_array = np.asarray(points, dtype=float)
                arrow_scale = max(float(radius) * 0.11, float(tube_radius) * 6.0, 0.35)
                for index, tangent in (
                    (0, point_array[0] - point_array[1]),
                    (-1, point_array[-1] - point_array[-2]),
                ):
                    norm = float(np.linalg.norm(tangent))
                    if norm <= 1e-12 or not np.isfinite(norm):
                        continue
                    direction = tangent / norm
                    tip_height = max(float(arrow_scale) * 0.78, float(tube_radius) * 8.0)
                    tip_radius = max(float(tube_radius) * 2.0, float(arrow_scale) * 0.075)
                    tip_point = point_array[index]
                    center_point = tip_point - direction * (tip_height * 0.5)
                    parts.append(
                        pv.Cone(
                            center=tuple(float(value) for value in center_point),
                            direction=tuple(float(value) for value in direction),
                            height=float(tip_height),
                            radius=float(tip_radius),
                            resolution=24,
                        )
                    )
            except Exception:
                pass
        merged = parts[0]
        for part in parts[1:]:
            try:
                merged = merged.merge(part)
            except Exception:
                pass
        return merged

    def _scene_placement_rotation_arrowhead_mesh(
        self,
        *,
        center: np.ndarray,
        axis: str,
        sign: float,
        delta_sign: float,
        radius: float,
        tube_radius: float,
    ):
        if pv is None:
            return None
        basis = self._scene_placement_rotation_basis(axis)
        if basis is None:
            return None
        u_axis, v_axis = basis
        if float(sign) >= 0.0:
            angles = np.linspace(np.deg2rad(-90.0), np.deg2rad(90.0), 36)
        else:
            angles = np.linspace(np.deg2rad(90.0), np.deg2rad(270.0), 36)
        center_vec = np.asarray(center, dtype=float).reshape(3)
        point_array = np.asarray(
            [
                center_vec + float(radius) * (np.cos(theta) * u_axis + np.sin(theta) * v_axis)
                for theta in angles
            ],
            dtype=float,
        )
        if point_array.shape[0] < 2:
            return None
        if float(delta_sign) >= 0.0:
            tip_point = point_array[-1]
            tangent = point_array[-1] - point_array[-2]
        else:
            tip_point = point_array[0]
            tangent = point_array[0] - point_array[1]
        norm = float(np.linalg.norm(tangent))
        if norm <= 1e-12 or not np.isfinite(norm):
            return None
        direction = tangent / norm
        arrow_scale = max(float(radius) * 0.24, float(tube_radius) * 14.0, 0.85)
        tip_height = max(float(arrow_scale) * 1.12, float(tube_radius) * 16.0)
        tip_radius = max(float(tube_radius) * 3.8, float(arrow_scale) * 0.15)
        center_point = tip_point - direction * (tip_height * 0.5)
        try:
            return pv.Cone(
                center=tuple(float(value) for value in center_point),
                direction=tuple(float(value) for value in direction),
                height=float(tip_height),
                radius=float(tip_radius),
                resolution=28,
            )
        except Exception:
            return None

    def _add_scene_placement_rotate_handles(
        self,
        placement: ScenePlacement3D,
        *,
        center: np.ndarray,
        spacing: float,
        extent: float,
    ) -> int:
        if pv is None or not self._show_rotation_handles():
            return 0
        try:
            row_index = int(placement.row_index)
        except Exception:
            return 0
        if not (0 <= row_index < len(self.editor.rows)):
            return 0
        step = self._rotation_handle_step_deg()
        # Size the arcs off the visible body when the row has one, so a
        # promoted-lens row's gizmo fits the glass (and the translate arrows,
        # sized the same way, clear the arcs) instead of ballooning to the
        # scene grid (bugs/0006). Abstract placements fall back to grid extent.
        body_extent = self._row_display_body_extent(row_index)
        arc_extent = float(body_extent) if body_extent is not None else float(extent)
        radius = max(float(spacing) * 2.0, arc_extent * 0.28, 2.0)
        radius = min(radius, max(arc_extent * 0.48, 2.0))
        tube_radius = max(radius * 0.018, 0.045)
        axes = (
            ("x", (0.88, 0.18, 0.18)),
            ("y", (0.12, 0.62, 0.24)),
            ("z", (0.18, 0.35, 0.88)),
        )
        count = 0
        for axis, color in axes:
            mesh = self._scene_placement_rotation_arc_mesh(
                center=center,
                axis=axis,
                sign=1.0,
                radius=radius,
                tube_radius=tube_radius,
            )
            if mesh is None:
                continue
            actor = self._add_mesh_actor(
                mesh,
                color=color,
                opacity=0.46,
                pick_placement_rotate=(row_index, axis, float(step)),
                flat_shading=True,
                backface_culling=False,
            )
            if actor is not None:
                count += 1
                arc_key = self._actor_key(actor)
                if arc_key is not None:
                    self._actor_placement_rotate_visual_keys.add(arc_key)
            for delta_deg in (-float(step), float(step)):
                arrow_mesh = self._scene_placement_rotation_arrowhead_mesh(
                    center=center,
                    axis=axis,
                    sign=1.0,
                    delta_sign=float(delta_deg),
                    radius=radius,
                    tube_radius=tube_radius,
                )
                if arrow_mesh is None:
                    continue
                arrow_actor = self._add_mesh_actor(
                    arrow_mesh,
                    color=color,
                    opacity=0.96,
                    pick_placement_rotate=(row_index, axis, float(delta_deg)),
                    flat_shading=True,
                    backface_culling=False,
                )
                if arrow_actor is not None:
                    count += 1
        return count

    @staticmethod
    def _step_rotation_handle_center_and_extent(mesh) -> tuple[np.ndarray, float] | None:
        return Open3DStepRotationHandleService.center_and_extent(mesh)

    def _add_step_rotation_handles(self, label: str, mesh) -> int:
        if self.is_step_label_hidden(label):  # bugs/0027: no gizmo on a hidden element
            return 0
        return self._open3d_step_rotation_handle_service().add_handles(label, mesh)

    def _apply_step_rotation_handle(self, label: str, axis: str, delta_deg: float) -> None:
        self._open3d_step_rotation_handle_service().apply_handle(label, axis, delta_deg)

    def _update_placement_grid_status(self, text: str, *, render: bool = True) -> None:
        if self._renderer is None:
            return
        actor = self._placement_grid_status_actor
        if not text:
            if actor is not None:
                self._remove_renderer_view_prop(actor)
                self._placement_grid_status_actor = None
                if render:
                    self.render()
            return
        if actor is None and vtkTextActor is not None:
            try:
                actor = vtkTextActor()
                prop = actor.GetTextProperty()
                prop.SetFontSize(13)
                prop.SetColor(0.05, 0.09, 0.16)
                try:
                    prop.SetBackgroundColor(1.0, 1.0, 1.0)
                    prop.SetBackgroundOpacity(0.78)
                    prop.SetFrame(1)
                    prop.SetFrameColor(0.46, 0.54, 0.62)
                except Exception:
                    pass
                actor.SetPickable(False)
                self._add_renderer_view_prop(actor)
                self._placement_grid_status_actor = actor
            except Exception as exc:
                self.editor.append_debug(f"3D placement grid status unavailable: {exc}")
                self._placement_grid_status_actor = None
                return
        if actor is None:
            return
        try:
            actor.SetInput(text)
            actor.SetDisplayPosition(16, 18)
            actor.SetVisibility(True)
        except Exception as exc:
            self.editor.append_debug(f"3D placement grid status update failed: {exc}")
            return
        if render:
            self.render()

    def _update_hover_status(self, text: str, *, display_xy=None, render: bool = True) -> None:
        if not open3d_trace_enabled():
            return self._update_hover_status_impl(text, display_xy=display_xy, render=render)
        from KrakenOS.UI.services.open3d_timing import open3d_trace_span as _span
        with _span("update_hover_status", has_text=bool(text), render=bool(render)):
            return self._update_hover_status_impl(text, display_xy=display_xy, render=render)

    def _update_hover_status_impl(self, text: str, *, display_xy=None, render: bool = True) -> None:
        if self._renderer is None:
            return
        text = str(text or "").strip()
        actor = self._hover_status_actor
        if not text:
            if actor is not None:
                self._remove_renderer_view_prop(actor)
                self._hover_status_actor = None
                if render:
                    self.render()
            return
        if actor is None and vtkTextActor is not None:
            try:
                actor = vtkTextActor()
                prop = actor.GetTextProperty()
                prop.SetFontSize(12)
                prop.SetColor(0.04, 0.06, 0.10)
                try:
                    prop.SetBackgroundColor(1.0, 1.0, 1.0)
                    prop.SetBackgroundOpacity(0.88)
                    prop.SetFrame(1)
                    prop.SetFrameColor(0.12, 0.38, 0.70)
                except Exception:
                    pass
                actor.SetPickable(False)
                self._add_renderer_view_prop(actor)
                self._hover_status_actor = actor
            except Exception as exc:
                self.editor.append_debug(f"3D hover status unavailable: {exc}")
                self._hover_status_actor = None
                return
        if actor is None:
            return
        try:
            x, y = (0, 0)
            if display_xy is not None:
                values = tuple(display_xy)
                if len(values) >= 2:
                    x, y = int(values[0]), int(values[1])
            elif self._vtk_interactor is not None:
                x, y = self._vtk_interactor.GetEventPosition()
            width, height = 1100, 720
            try:
                if self._vtk_widget is not None:
                    width, height = self._vtk_widget.GetRenderWindow().GetSize()
                elif self._renderer is not None:
                    width, height = self._renderer.GetSize()
            except Exception:
                pass
            line_count = max(text.count("\n") + 1, 1)
            pos_x = min(max(int(x) + 14, 8), max(int(width) - 330, 8))
            pos_y = min(max(int(y) + 18, 8), max(int(height) - 22 * line_count - 12, 8))
            actor.SetInput(text)
            actor.SetDisplayPosition(pos_x, pos_y)
            actor.SetVisibility(True)
        except Exception as exc:
            self.editor.append_debug(f"3D hover status update failed: {exc}")
            return
        if render:
            self.render()

    @staticmethod
    def _face_hover_status_text(row_index: int, face: dict[str, object]) -> str:
        function = _optical_solid_face_function_display(face.get("function"), legacy_role=face.get("role"))
        port_role = _optical_solid_face_port_role(face)
        face_id = str(face.get("face_id", "") or "face").strip() or "face"
        source = str(face.get("assignment_source", "") or "").strip()
        default_text = " (default)" if source == OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED else ""
        return f"S{int(row_index)} {face_id}\n{function}{default_text}\n{port_role}"

    @staticmethod
    def _world_xyz_text(values, *, digits: int = 5) -> str:
        try:
            point = np.asarray(values, dtype=float).reshape(-1)[:3]
        except Exception:
            point = np.asarray([], dtype=float)
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return "(nan, nan, nan) mm"
        return (
            f"({float(point[0]):.{digits}g}, "
            f"{float(point[1]):.{digits}g}, "
            f"{float(point[2]):.{digits}g}) mm"
        )

    def _scene_refresh_service(self) -> Open3DSceneRefreshService:
        service = self.__dict__.get("_scene_refresh_service_instance")
        if service is None:
            service = Open3DSceneRefreshService(self)
            self._scene_refresh_service_instance = service
        return service

    def refresh_scene(
        self,
        system,
        rays,
        row_names: list[str],
        *,
        scene_bundle: SceneBundle | None = None,
        reset_camera: bool = False,
    ) -> None:
        return self._scene_refresh_service().refresh_scene(
            system,
            rays,
            row_names,
            scene_bundle=scene_bundle,
            reset_camera=reset_camera,
        )

    def _refresh_rays_only(self, rays, scene_bundle: SceneBundle | None = None) -> None:
        # bugs/0024: rays-only partial refresh (skips the body/handle rebuild),
        # used by the Live Mode drag preview.
        return self._scene_refresh_service()._refresh_rays_only(rays, scene_bundle)

    def _live_trace_step_overlay_labels(self) -> set[str]:
        labels: set[str] = set()
        for record in list(getattr(self.editor, "_last_live_step_overlay_trace_records", []) or []):
            if not isinstance(record, dict):
                continue
            if not bool(record.get("transient_live_trace", False)):
                continue
            label = str(record.get("label", "") or "").strip().lower()
            if label in STEP_OVERLAY_LABEL_SET:
                labels.add(label)
        return labels

    def _live_trace_step_overlay_label_by_row(self) -> dict[int, str]:
        labels: dict[int, str] = {}
        for record in list(getattr(self.editor, "_last_live_step_overlay_trace_records", []) or []):
            if not isinstance(record, dict) or not bool(record.get("transient_live_trace", False)):
                continue
            label = str(record.get("label", "") or "").strip().lower()
            if label not in STEP_OVERLAY_LABEL_SET:
                continue
            try:
                row_index = int(record.get("row_index", -1))
            except Exception:
                continue
            if row_index >= 0:
                labels[row_index] = label
        return labels

    def _render_row_file_backed(self, rows: list[SurfaceRow], row_index: int) -> bool:
        try:
            row = rows[int(row_index)]
        except Exception:
            return False
        try:
            path = self.editor._stl_path_from_row(row)
        except Exception:
            return False
        return path is not None and Path(path).exists()

    @staticmethod
    def _display_feature_edges(mesh, *, feature_angle: float = 24.0, boundary_edges: bool = True):
        return _display_feature_edges_mesh(mesh, feature_angle=feature_angle, boundary_edges=boundary_edges)

    def _normalize_sampling_mode_label(self, sampling_mode: object) -> str | None:
        return Open3DTraceRefreshService.normalize_sampling_mode_label(sampling_mode)

    def _remember_refresh_sampling_mode(self, sampling_mode: object) -> None:
        self.editor._open3d_trace_refresh_service().remember_inspector_sampling_mode(self, sampling_mode)

    def _active_refresh_sampling_mode(self) -> str | None:
        return self.editor._open3d_trace_refresh_service().inspector_active_sampling_mode(self)

    def refresh_from_editor(self, *, sampling_mode: str | None = None, force_retrace: bool = False) -> None:
        token = self._timing_start(
            "refresh_from_editor",
            sampling_mode=sampling_mode,
            force_retrace=bool(force_retrace),
        )
        try:
            with self._timing_span("build_inspector_refresh", sampling_mode=sampling_mode, force_retrace=bool(force_retrace)):
                result = self.editor._open3d_trace_refresh_service().build_inspector_refresh(
                    self,
                    sampling_mode=sampling_mode,
                    force_retrace=force_retrace,
                    update_state=True,
                )
            self.refresh_scene(
                result.system,
                result.rays,
                result.row_names,
                scene_bundle=result.scene_bundle,
                reset_camera=False,
            )
            self.editor.status_var.set("3D inspector updated")
        except Exception as exc:
            self.status_var.set(f"3D refresh failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D inspector refresh error: {exc}")
            self._timing_finish(token, status="error", error=_short_error_message(exc))
        else:
            self._timing_finish(token, status="ok")

    def open_selected_optical_faces(self) -> None:
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        if row_index is None:
            self.status_var.set("Faces: select a CAD/STL solid row first.")
            return
        try:
            self.editor.open_optical_solid_face_role_editor(int(row_index))
        except Exception as exc:
            self.status_var.set(f"Faces unavailable: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D Faces action failed: {exc}")

    def start_source_target_pick(self) -> None:
        self._source_target_pick_mode = True
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(True)
        self.status_var.set(
            "Source Target: click a surface/CAD solid. Assigned CAD/STL faces are used when the pick lands near one."
        )
        self._update_mode_badge()

    def start_measure_pick(self) -> None:
        # CAD-style 2-point measure (project_open3d_three_followups): the next two left-clicks
        # on edges/surfaces drop a distance dimension between them.
        self._measure_pick_mode = True
        self._measure_p0 = None
        for _flag in (
            "_source_target_pick_mode", "_center_row_to_ray_mode", "_placement_target_pick_mode",
            "_placement_orient_pick_mode", "_placement_orient_ray_mode", "_step_carry_snap_ray_mode",
            "_step_carry_snap_target_mode", "_step_normal_axis_pick_mode", "_step_surface_center_axis_pick_mode",
        ):
            setattr(self, _flag, False)
        try:
            self._set_axis_pick_cursor(True)
        except Exception:
            pass
        self.status_var.set("Measure: click the FIRST edge/surface.")
        self._update_mode_badge()

    def clear_measurements(self) -> None:
        self._measure_pick_mode = False
        self._measure_p0 = None
        self._measure_segments = []
        try:
            self._set_axis_pick_cursor(False)
        except Exception:
            pass
        self._refresh_measure_overlays()
        self.status_var.set("Measurements cleared.")
        self._update_mode_badge()

    def _measure_row_z_positions(self):
        # live per-row z-stations (recomputed each refresh) -- the anchor that makes measurements track.
        for owner in (getattr(self, "editor", None), self):
            fn = getattr(owner, "_row_z_positions", None)
            if callable(fn):
                try:
                    z = fn()
                    if z:
                        return [float(v) for v in z]
                except Exception:
                    pass
        return None

    def _anchor_measure_point(self, point):
        zpos = self._measure_row_z_positions()
        if not zpos:
            return None, 0.0
        z = float(np.asarray(point, dtype=float).reshape(-1)[2])
        r = int(min(range(len(zpos)), key=lambda i: abs(z - zpos[i])))
        return r, z - zpos[r]

    def _resolve_measure_point(self, p, r, dz):
        out = np.asarray(p, dtype=float).reshape(3).copy()
        if r is not None:
            zpos = self._measure_row_z_positions()
            if zpos and 0 <= int(r) < len(zpos):
                out[2] = zpos[int(r)] + float(dz)
        return out

    def _record_measure_point(self, world, normal=None) -> None:
        point = np.asarray(world, dtype=float).reshape(-1)[:3]
        if point.size < 3 or not np.all(np.isfinite(point)):
            self.status_var.set("Measure: the pick missed -- click ON an edge/surface.")
            return
        # anchor each end to the nearest optical row's z-station so the dimension tracks geometry.
        r, dz = self._anchor_measure_point(point)
        if getattr(self, "_measure_p0", None) is None:
            n0 = None
            if normal is not None:
                n = np.asarray(normal, dtype=float).reshape(-1)[:3]
                if n.size >= 3 and np.all(np.isfinite(n)) and float(np.linalg.norm(n)) > 1e-9:
                    n0 = (n / float(np.linalg.norm(n))).tolist()
            self._measure_p0 = {"p": point.tolist(), "r": r, "dz": float(dz), "n": n0}
            self.status_var.set("Measure: click the SECOND edge/surface.")
            return
        a0 = self._measure_p0
        seg = {
            "p0": list(a0["p"]), "r0": a0["r"], "dz0": a0["dz"], "n0": a0["n"],
            "p1": point.tolist(), "r1": r, "dz1": float(dz),
        }
        segs = list(getattr(self, "_measure_segments", []))
        segs.append(seg)
        self._measure_segments = segs
        self._measure_p0 = None
        self._measure_pick_mode = False
        try:
            self._set_axis_pick_cursor(False)
        except Exception:
            pass
        p0 = self._resolve_measure_point(seg["p0"], seg["r0"], seg["dz0"])
        p1 = self._resolve_measure_point(seg["p1"], seg["r1"], seg["dz1"])
        n0 = np.asarray(seg["n0"], dtype=float) if seg["n0"] else None
        dist = abs(float(np.dot(p1 - p0, n0))) if n0 is not None else float(np.linalg.norm(p1 - p0))
        self._refresh_measure_overlays()
        kind = "normal" if n0 is not None else "point-to-point"
        self.status_var.set(f"Measured {dist:.4g} mm ({kind}, live). Press 'Measure' for another, or 'Clear'.")
        self._update_mode_badge()

    def _refresh_measure_overlays(self) -> None:
        # Idempotent: remove current measure actors, redraw a line + distance label per segment.
        for _actor in getattr(self, "_measure_actors", []):
            try:
                self._remove_renderer_view_prop(_actor)
            except Exception:
                pass
        self._measure_actors = []
        segments = getattr(self, "_measure_segments", [])
        if self._renderer is not None and segments:
            line_cls = mapper_cls = cone_cls = None
            try:
                from vtkmodules.vtkFiltersSources import vtkLineSource as line_cls  # noqa: F811
                from vtkmodules.vtkFiltersSources import vtkConeSource as cone_cls  # noqa: F811
                from vtkmodules.vtkRenderingCore import vtkPolyDataMapper as mapper_cls  # noqa: F811
            except Exception:
                line_cls = mapper_cls = cone_cls = None
            for _seg in segments:
                try:
                    # resolve each end from its anchor so the dimension tracks moved geometry
                    p0 = self._resolve_measure_point(_seg["p0"], _seg.get("r0"), _seg.get("dz0", 0.0))
                    p1raw = self._resolve_measure_point(_seg["p1"], _seg.get("r1"), _seg.get("dz1", 0.0))
                    _n0 = np.asarray(_seg["n0"], dtype=float) if _seg.get("n0") else None
                    if _n0 is not None:
                        p1 = p0 + _n0 * float(np.dot(p1raw - p0, _n0))
                    else:
                        p1 = p1raw
                    dist = float(np.linalg.norm(p1 - p0))
                    # offset the dimension line perpendicular, clear of the geometry (CAD-style);
                    # _seg["offset"] (a future drag) overrides the default standoff.
                    _d = (p1 - p0) / dist if dist > 1e-9 else np.array([0.0, 0.0, 1.0])
                    _od = np.array([0.0, 1.0, 0.0]) - float(np.dot([0.0, 1.0, 0.0], _d)) * _d
                    if float(np.linalg.norm(_od)) < 1e-6:
                        _od = np.array([1.0, 0.0, 0.0]) - float(np.dot([1.0, 0.0, 0.0], _d)) * _d
                    _on = float(np.linalg.norm(_od))
                    _amt = float(_seg.get("offset", max(dist * 0.12, 45.0)))
                    _off = (_od / _on) * _amt if _on > 1e-6 else np.zeros(3)
                    a0 = p0 + _off
                    a1 = p1 + _off
                    mid = (a0 + a1) * 0.5
                    if line_cls is not None and mapper_cls is not None and vtkActor is not None:
                        def _meas_line(s, e, width, color):
                            try:
                                _s = line_cls()
                                _s.SetPoint1(float(s[0]), float(s[1]), float(s[2]))
                                _s.SetPoint2(float(e[0]), float(e[1]), float(e[2]))
                                _m = mapper_cls()
                                _m.SetInputConnection(_s.GetOutputPort())
                                _act = vtkActor()
                                _act.SetMapper(_m)
                                _act.PickableOff()
                                _p = _act.GetProperty()
                                _p.SetColor(*color)
                                _p.SetLineWidth(float(width))
                                self._add_renderer_view_prop(_act)
                                self._measure_actors.append(_act)
                            except Exception:
                                pass
                        _meas_line(a0, a1, 2.0, (0.95, 0.55, 0.1))          # dimension line (offset)
                        _meas_line(p0, a0, 1.0, (0.95, 0.7, 0.4))           # witness line 1
                        _meas_line(p1, a1, 1.0, (0.95, 0.7, 0.4))           # witness line 2
                        # CAD arrowheads (cones) at both ends of the dimension line, pointing outward
                        if cone_cls is not None and dist > 1e-6:
                            ndir = (a1 - a0) / dist
                            head = float(min(max(dist * 0.06, 2.0), 12.0))
                            crad = head * 0.4
                            for _tip, _cd in ((a0, -ndir), (a1, ndir)):
                                try:
                                    _ctr = np.asarray(_tip, dtype=float) - np.asarray(_cd, dtype=float) * (head * 0.5)
                                    _cn = cone_cls()
                                    _cn.SetCenter(float(_ctr[0]), float(_ctr[1]), float(_ctr[2]))
                                    _cn.SetDirection(float(_cd[0]), float(_cd[1]), float(_cd[2]))
                                    _cn.SetHeight(head)
                                    _cn.SetRadius(crad)
                                    _cn.SetResolution(20)
                                    _cm = mapper_cls()
                                    _cm.SetInputConnection(_cn.GetOutputPort())
                                    _ca = vtkActor()
                                    _ca.SetMapper(_cm)
                                    try:
                                        _ca.PickableOff()
                                        _ca.GetProperty().SetColor(0.95, 0.55, 0.1)
                                    except Exception:
                                        pass
                                    self._add_renderer_view_prop(_ca)
                                    self._measure_actors.append(_ca)
                                except Exception:
                                    pass
                    if vtkBillboardTextActor3D is not None:
                        lbl = vtkBillboardTextActor3D()
                        lbl.SetInput(f"↔ {dist:.4g} mm")
                        lbl.SetPosition(float(mid[0]), float(mid[1]), float(mid[2]))
                        try:
                            lbl.PickableOff()
                        except Exception:
                            pass
                        try:
                            tp = lbl.GetTextProperty()
                            tp.SetFontSize(14)
                            tp.SetColor(0.25, 0.08, 0.0)
                            tp.SetBackgroundColor(1.0, 0.93, 0.78)
                            tp.SetBackgroundOpacity(0.9)
                            tp.SetFrame(1)
                            tp.SetFrameColor(0.95, 0.55, 0.1)
                        except Exception:
                            pass
                        self._add_renderer_view_prop(lbl)
                        self._measure_actors.append(lbl)
                except Exception as _exc:
                    try:
                        self.editor.append_debug(f"measure overlay skipped: {_exc}")
                    except Exception:
                        pass
        try:
            self._vtk_widget.GetRenderWindow().Render()
        except Exception:
            pass

    def _apply_source_target_pick(self, row_index: int) -> None:
        self._source_target_pick_mode = False
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()
        row_index = int(row_index)
        face_id = ""
        target_text = f"S{row_index} row center"
        if self.editor._file_backed_stl_row_at(row_index) is not None and self._picker is not None:
            try:
                point = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
            except Exception:
                point = np.empty(0, dtype=float)
            if point.size >= 3 and np.all(np.isfinite(point[:3])):
                matched = self.editor.scene_source_face_anchor_at_world_point(row_index, point[:3])
                if matched is not None:
                    face_id = str(matched.get("face_id", "") or "").strip()
                    if face_id:
                        target_text = f"S{row_index} face {_optical_solid_face_marker_label(matched)} [{face_id}]"
        self.editor._select_table_row(row_index)
        self._set_row_highlight(row_index)
        self._set_ray_highlight(None)
        self.status_var.set(f"Opening Scene Source Manager with {target_text} selected.")
        self.editor.open_scene_source_manager(aim_row_index=row_index, aim_face_id=face_id)

    def _picked_scene_face_id_for_row(self, row_index: int) -> str:
        if self.editor._file_backed_stl_row_at(int(row_index)) is None or self._picker is None:
            return ""
        try:
            point = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
        except Exception:
            point = np.empty(0, dtype=float)
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            return ""
        matched = self.editor.scene_source_face_anchor_at_world_point(int(row_index), point[:3])
        if matched is None:
            return ""
        return str(matched.get("face_id", "") or "").strip()

    def _placement_target_pick_label(self, row_index: int, face_id: str = "") -> str:
        row = self.editor.rows[int(row_index)]
        label = f"S{int(row_index)}: {row.name or row.surface or 'Surface'}"
        if face_id:
            face = self.editor._scene_source_face_anchor_record(int(row_index), str(face_id))
            if face is not None:
                label += f" face {_optical_solid_face_marker_label(face)}"
            label += f" [{face_id}]"
        return label

    def start_placement_target_pick(self) -> None:
        self._placement_target_pick_mode = True
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(True)
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        if row_index is not None and 0 <= int(row_index) < len(self.editor.rows):
            row = self.editor.rows[int(row_index)]
            if row.surface not in {"Object", "Image"}:
                face_id = ""
                if self._picked_row_index is not None and int(self._picked_row_index) == int(row_index):
                    face_id = self._picked_scene_face_id_for_row(int(row_index))
                self._placement_target_row_index = int(row_index)
                self._placement_target_face_id = face_id
                self.status_var.set(
                    f"Snap Row->Target: selected {self._placement_target_pick_label(int(row_index), face_id)}. Click target row/face."
                )
                self._update_mode_badge()
                return
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self.status_var.set("Snap Row->Target: click movable row/face, then click the target row/face.")
        self._update_mode_badge()

    def _apply_placement_target_pick(self, row_index: int) -> None:
        row_index = int(row_index)
        face_id = self._picked_scene_face_id_for_row(row_index)
        if self._placement_target_row_index is None:
            if not (0 <= row_index < len(self.editor.rows)):
                self.status_var.set("Snap Row->Target: click a valid movable row first.")
                return
            row = self.editor.rows[row_index]
            if row.surface in {"Object", "Image"}:
                self.status_var.set("Snap Row->Target: Object/Image rows can be targets, not movable rows.")
                return
            self._placement_target_row_index = row_index
            self._placement_target_face_id = face_id
            self._set_row_highlight(row_index)
            self.editor._select_table_row(row_index)
            self.status_var.set(
                f"Snap Row->Target: selected {self._placement_target_pick_label(row_index, face_id)}. Click target row/face."
            )
            self._update_mode_badge()
            return
        source_row = int(self._placement_target_row_index)
        source_face_id = str(self._placement_target_face_id or "")
        if source_row == row_index and source_face_id == face_id:
            self.status_var.set("Snap Row->Target: target must be different from the selected source anchor.")
            return
        try:
            result = self.editor.snap_scene_row_anchor_to_target(
                source_row,
                row_index,
                row_face_id=source_face_id,
                target_face_id=face_id,
            )
        except Exception as exc:
            self.status_var.set(f"Snap Row->Target failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Snap Row->Target failed: {exc}")
            return
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()
        if self.editor._file_backed_stl_row_at(source_row) is not None:
            self._stl_placement_row_index = source_row
            self._stl_placement_dirty = True
        try:
            self.refresh_from_editor()
            self.highlight_row(source_row)
        except Exception as exc:
            self.editor.append_debug(f"Snap Row->Target refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        self.status_var.set(
            "Snapped {source} to {target_label} at ({x:.6g}, {y:.6g}, {z:.6g}) mm.".format(
                source=self._placement_target_pick_label(source_row, source_face_id),
                target_label=self._placement_target_pick_label(row_index, face_id),
                x=float(target[0]),
                y=float(target[1]),
                z=float(target[2]),
            )
        )

    def start_placement_orient_pick(self) -> None:
        self._placement_orient_pick_mode = True
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(True)
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        if row_index is not None and 0 <= int(row_index) < len(self.editor.rows):
            row = self.editor.rows[int(row_index)]
            if row.surface not in {"Object", "Image"}:
                face_id = ""
                if self._picked_row_index is not None and int(self._picked_row_index) == int(row_index):
                    face_id = self._picked_scene_face_id_for_row(int(row_index))
                self._placement_orient_row_index = int(row_index)
                self._placement_orient_face_id = face_id
                self.status_var.set(
                    f"Orient Row->Target: selected {self._placement_target_pick_label(int(row_index), face_id)}. Click target row/face normal."
                )
                self._update_mode_badge()
                return
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self.status_var.set("Orient Row->Target: click movable row/face, then click the target row/face normal.")
        self._update_mode_badge()

    def _apply_placement_orient_pick(self, row_index: int) -> None:
        row_index = int(row_index)
        face_id = self._picked_scene_face_id_for_row(row_index)
        if self._placement_orient_row_index is None:
            if not (0 <= row_index < len(self.editor.rows)):
                self.status_var.set("Orient Row->Target: click a valid movable row first.")
                return
            row = self.editor.rows[row_index]
            if row.surface in {"Object", "Image"}:
                self.status_var.set("Orient Row->Target: Object/Image rows can be targets, not movable rows.")
                return
            self._placement_orient_row_index = row_index
            self._placement_orient_face_id = face_id
            self._set_row_highlight(row_index)
            self.editor._select_table_row(row_index)
            self.status_var.set(
                f"Orient Row->Target: selected {self._placement_target_pick_label(row_index, face_id)}. Click target row/face normal."
            )
            self._update_mode_badge()
            return
        source_row = int(self._placement_orient_row_index)
        source_face_id = str(self._placement_orient_face_id or "")
        if source_row == row_index and source_face_id == face_id:
            self.status_var.set("Orient Row->Target: target normal must be different from the selected source anchor.")
            return
        try:
            result = self.editor.orient_scene_row_anchor_to_target(
                source_row,
                row_index,
                row_face_id=source_face_id,
                target_face_id=face_id,
            )
        except Exception as exc:
            self.status_var.set(f"Orient Row->Target failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Orient Row->Target failed: {exc}")
            return
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()
        if self.editor._file_backed_stl_row_at(source_row) is not None:
            self._stl_placement_row_index = source_row
            self._stl_placement_dirty = True
        try:
            self.refresh_from_editor()
            self.highlight_row(source_row)
        except Exception as exc:
            self.editor.append_debug(f"Orient Row->Target refresh failed: {exc}")
        angle_error = float(result.get("angle_error_deg", float("nan")))
        self.status_var.set(
            "Oriented {source} normal to {target_label} normal (error {err:.6g} deg).".format(
                source=self._placement_target_pick_label(source_row, source_face_id),
                target_label=self._placement_target_pick_label(row_index, face_id),
                err=angle_error,
            )
        )

    def start_placement_orient_ray_pick(self) -> None:
        self._placement_orient_ray_mode = True
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(True)
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        if row_index is not None and 0 <= int(row_index) < len(self.editor.rows):
            row = self.editor.rows[int(row_index)]
            if row.surface not in {"Object", "Image"}:
                face_id = ""
                if self._picked_row_index is not None and int(self._picked_row_index) == int(row_index):
                    face_id = self._picked_scene_face_id_for_row(int(row_index))
                self._placement_orient_ray_row_index = int(row_index)
                self._placement_orient_ray_face_id = face_id
                self.status_var.set(
                    f"Orient Row->Ray: selected {self._placement_target_pick_label(int(row_index), face_id)}. Click target ray."
                )
                self._update_mode_badge()
                return
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self.status_var.set("Orient Row->Ray: click movable row/face, then click the target ray direction.")
        self._update_mode_badge()

    def _apply_placement_orient_ray_row_pick(self, row_index: int) -> None:
        row_index = int(row_index)
        face_id = self._picked_scene_face_id_for_row(row_index)
        if not (0 <= row_index < len(self.editor.rows)):
            self.status_var.set("Orient Row->Ray: click a valid movable row first.")
            return
        row = self.editor.rows[row_index]
        if row.surface in {"Object", "Image"}:
            self.status_var.set("Orient Row->Ray: Object/Image rows are references; choose a physical surface or CAD/STL row.")
            return
        self._placement_orient_ray_row_index = row_index
        self._placement_orient_ray_face_id = face_id
        self._set_row_highlight(row_index)
        self.editor._select_table_row(row_index)
        self.status_var.set(
            f"Orient Row->Ray: selected {self._placement_target_pick_label(row_index, face_id)}. Click target ray."
        )
        self._update_mode_badge()

    def _apply_placement_orient_ray_pick(self, ray_index: int) -> None:
        source_row = self._placement_orient_ray_row_index
        if source_row is None:
            self.status_var.set("Orient Row->Ray: click a surface/CAD row first, then click the target ray.")
            return
        source_row = int(source_row)
        source_face_id = str(self._placement_orient_ray_face_id or "")
        try:
            reference = self.editor._surface_reference_world_point(source_row, face_id=source_face_id)
            frame = self.editor._ray_frame_near_point(int(ray_index), reference)
            result = self.editor.orient_scene_row_anchor_to_vector(
                source_row,
                frame["direction"],
                row_face_id=source_face_id,
                constraint_kind="target_ray",
                target_label=f"ray {int(ray_index)}",
                metadata={
                    "last_constraint_ray_index": int(ray_index),
                    "last_constraint_target_point": [float(value) for value in np.asarray(frame["target_point"], dtype=float)[:3]],
                    "last_constraint_branch_path": str(frame.get("branch_path", "") or ""),
                    "last_constraint_source_id": str(frame.get("source_id", "") or ""),
                },
            )
        except Exception as exc:
            self.status_var.set(f"Orient Row->Ray failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Orient Row->Ray failed: {exc}")
            return
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()
        if self.editor._file_backed_stl_row_at(source_row) is not None:
            self._stl_placement_row_index = source_row
            self._stl_placement_dirty = True
        try:
            self.refresh_from_editor()
            self.highlight_row(source_row)
        except Exception as exc:
            self.editor.append_debug(f"Orient Row->Ray refresh failed: {exc}")
        angle_error = float(result.get("angle_error_deg", float("nan")))
        self.status_var.set(
            "Oriented {source} normal to ray {ray} direction (error {err:.6g} deg).".format(
                source=self._placement_target_pick_label(source_row, source_face_id),
                ray=int(ray_index),
                err=angle_error,
            )
        )

    def _selected_movable_row_face_for_orientation(self, action_label: str) -> tuple[int, str] | None:
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        if row_index is None or not (0 <= int(row_index) < len(self.editor.rows)):
            self.status_var.set(f"{action_label}: select or click a physical surface/CAD row first.")
            return None
        row_index = int(row_index)
        row = self.editor.rows[row_index]
        if row.surface in {"Object", "Image"}:
            self.status_var.set(f"{action_label}: Object/Image rows are references; choose a physical surface or CAD/STL row.")
            return None
        face_id = ""
        if self._picked_row_index is not None and int(self._picked_row_index) == row_index:
            face_id = self._picked_scene_face_id_for_row(row_index)
        return row_index, face_id

    def _clear_immediate_orientation_modes(self) -> None:
        self._source_target_pick_mode = False
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._set_axis_pick_cursor(False)
        self._update_mode_badge()

    def _finish_immediate_orientation(self, action_label: str, row_index: int, face_id: str, result: dict[str, object]) -> None:
        if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_row_index = int(row_index)
            self._stl_placement_dirty = True
        try:
            self.editor._select_table_row(int(row_index))
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"{action_label} refresh failed: {exc}")
        angle_error = float(result.get("angle_error_deg", float("nan")))
        target_label = str(result.get("target_label", "target vector") or "target vector")
        self.status_var.set(
            "{action}: oriented {source} normal to {target} (error {err:.6g} deg).".format(
                action=action_label,
                source=self._placement_target_pick_label(int(row_index), str(face_id or "")),
                target=target_label,
                err=angle_error,
            )
        )

    def orient_selected_row_to_source_direction(self) -> None:
        action_label = "Orient Row->Source"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        self._clear_immediate_orientation_modes()
        try:
            result = self.editor.orient_scene_row_anchor_to_current_source(row_index, row_face_id=face_id)
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        self._finish_immediate_orientation(action_label, row_index, face_id, result)

    def orient_selected_row_to_path_frame(self) -> None:
        action_label = "Orient Row->Path"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        self._clear_immediate_orientation_modes()
        try:
            result = self.editor.orient_scene_row_anchor_to_current_path_frame(row_index, row_face_id=face_id)
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        self._finish_immediate_orientation(action_label, row_index, face_id, result)

    def orient_selected_row_to_local_axis(self) -> None:
        action_label = "Orient Row->CAD Axis"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        axis = str(self.orient_axis_var.get() or "+Z").strip() or "+Z"
        self._clear_immediate_orientation_modes()
        try:
            result = self.editor.orient_scene_row_anchor_to_local_axis(row_index, axis, row_face_id=face_id)
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        self._finish_immediate_orientation(action_label, row_index, face_id, result)

    def orient_selected_row_to_scene_source(self) -> None:
        action_label = "Orient Row->Scene Source"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        try:
            source_id = self.editor._current_or_first_scene_source_id()
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} source selection failed: {exc}")
            return
        self._clear_immediate_orientation_modes()
        try:
            result = self.editor.orient_scene_row_anchor_to_scene_source(
                row_index,
                source_id,
                row_face_id=face_id,
            )
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        self._finish_immediate_orientation(action_label, row_index, face_id, result)

    def _selected_normal_target_kind(self) -> str:
        return _normalize_scene_normal_target_kind(self.normal_target_var.get())

    def preview_selected_row_normal_target(self) -> None:
        action_label = "Preview Normal"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        target_kind = self._selected_normal_target_kind()
        try:
            result = self.editor.preview_scene_row_anchor_to_named_normal_target(
                row_index,
                target_kind,
                row_face_id=face_id,
            )
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        target_label = str(result.get("target_label", "target normal") or "target normal")
        angle_error = float(result.get("angle_error_deg", float("nan")))
        source_label = self._placement_target_pick_label(int(row_index), str(face_id or ""))
        self.status_var.set(
            "Preview normal: {source} -> {target} (current error {err:.6g} deg).".format(
                source=source_label,
                target=target_label,
                err=angle_error,
            )
        )
        self.editor.append_debug(
            "Preview normal constraint {source} -> {target}: target=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "normal=({nx:.6g},{ny:.6g},{nz:.6g}) error={err:.6g} deg".format(
                source=source_label,
                target=target_label,
                tx=float(result["target_point"][0]),
                ty=float(result["target_point"][1]),
                tz=float(result["target_point"][2]),
                nx=float(result["target_normal"][0]),
                ny=float(result["target_normal"][1]),
                nz=float(result["target_normal"][2]),
                err=angle_error,
            )
        )

    def orient_selected_row_to_named_normal_target(self) -> None:
        action_label = "Orient Row->Normal"
        selected = self._selected_movable_row_face_for_orientation(action_label)
        if selected is None:
            return
        row_index, face_id = selected
        target_kind = self._selected_normal_target_kind()
        self._clear_immediate_orientation_modes()
        try:
            result = self.editor.orient_scene_row_anchor_to_named_normal_target(
                row_index,
                target_kind,
                row_face_id=face_id,
            )
        except Exception as exc:
            self.status_var.set(f"{action_label} failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"{action_label} failed: {exc}")
            return
        self._finish_immediate_orientation(action_label, row_index, face_id, result)

    def start_center_row_to_ray(self) -> None:
        row_index = self._picked_row_index
        if row_index is None:
            row_index = self.editor._current_selected_row_index()
        self._center_row_to_ray_mode = True
        self._source_target_pick_mode = False
        self._placement_target_pick_mode = False
        self._placement_target_row_index = None
        self._placement_target_face_id = ""
        self._placement_orient_pick_mode = False
        self._placement_orient_row_index = None
        self._placement_orient_face_id = ""
        self._placement_orient_ray_mode = False
        self._placement_orient_ray_row_index = None
        self._placement_orient_ray_face_id = ""
        self._step_carry_snap_ray_mode = False
        self._step_carry_snap_target_mode = False
        self._step_normal_axis_pick_mode = False
        self._step_surface_center_axis_pick_mode = False
        self._set_ray_highlight(None)
        self._set_optical_axis_highlight(None)
        self._clear_open3d_selection(render=False)
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        if row_index is not None and 0 <= int(row_index) < len(self.editor.rows):
            row = self.editor.rows[int(row_index)]
            if row.surface not in {"Object", "Image"} and self.editor._file_backed_stl_row_at(int(row_index)) is None:
                self._center_row_to_ray_index = int(row_index)
        self._hide_regular_rays_for_center_axis_pick()
        self._clear_open3d_selection(render=False)
        if self._center_row_to_ray_index is not None:
            self._set_row_highlight(int(self._center_row_to_ray_index))
            stl_note = " assigned optical-face anchor or" if self.editor._file_backed_stl_row_at(int(self._center_row_to_ray_index)) is not None else ""
            self.status_var.set(
                f"Center Row->Optical Axis: selected S{int(self._center_row_to_ray_index)}. Regular rays are hidden; click the dotted Optical Axis guide that should pass through its{stl_note} center."
            )
            self._update_mode_badge()
            return
        self._set_row_highlight(None)
        self.status_var.set("Center Row->Optical Axis: regular rays are hidden; click the CAD/STL face or surface row first, then click the dotted Optical Axis guide.")
        self._update_mode_badge()

    def _apply_center_row_to_ray(self, ray_index: int) -> None:
        row_index = self._center_row_to_ray_index
        if row_index is None:
            self.status_var.set("Center Row->Ray: click a surface/CAD row first, then click the target ray.")
            return
        try:
            face_id = str(self._center_row_to_ray_face_id or "").strip()
            result = self.editor.center_surface_row_on_ray(int(row_index), int(ray_index), face_id=face_id)
        except Exception as exc:
            self.status_var.set(f"Center Row->Ray failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Center Row->Ray failed: {exc}")
            return
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._update_mode_badge()
        if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_dirty = True
            self._stl_placement_row_index = int(row_index)
        try:
            self.editor._select_table_row(int(row_index))
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
            self._set_ray_highlight(int(ray_index))
        except Exception as exc:
            self.editor.append_debug(f"Center Row->Ray refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        anchor_label = str(result.get("anchor_label", "") or result.get("anchor_face_id", "") or "").strip()
        anchor_text = f" using {anchor_label}" if anchor_label else ""
        self.status_var.set(
            "Centered S{row} on ray {ray}{anchor} at ({x:.6g}, {y:.6g}, {z:.6g}) mm. "
            "Click Done -> 2D or Update to refresh plots.".format(
                row=int(row_index),
                ray=int(ray_index),
                anchor=anchor_text,
                x=float(target[0]),
                y=float(target[1]),
                z=float(target[2]),
            )
        )

    def _apply_center_row_to_optical_axis(self, axis_info: dict[str, object]) -> None:
        row_index = self._center_row_to_ray_index
        if row_index is None:
            self.status_var.set("Center Row->Optical Axis: click a surface/CAD row first, then click the dotted Optical Axis guide.")
            return
        try:
            face_id = str(self._center_row_to_ray_face_id or "").strip()
            result = self.editor.center_surface_row_on_optical_axis(int(row_index), axis_info, face_id=face_id)
        except Exception as exc:
            self.status_var.set(f"Center Row->Optical Axis failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Center Row->Optical Axis failed: {exc}")
            return
        self._center_row_to_ray_mode = False
        self._center_row_to_ray_index = None
        self._center_row_to_ray_face_id = ""
        self._update_mode_badge()
        if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_dirty = True
            self._stl_placement_row_index = int(row_index)
        axis_id = str(axis_info.get("axis_id", "") or "").strip()
        try:
            self.editor._select_table_row(int(row_index))
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
            self._set_ray_highlight(None)
            self._set_optical_axis_highlight(axis_id)
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"Center Row->Optical Axis refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        anchor_label = str(result.get("anchor_label", "") or result.get("anchor_face_id", "") or "").strip()
        anchor_text = f" using {anchor_label}" if anchor_label else ""
        axis_label = str(result.get("axis_label", axis_info.get("axis_label", "Optical Axis")) or "Optical Axis")
        self.status_var.set(
            "Centered S{row} on {axis}{anchor} at ({x:.6g}, {y:.6g}, {z:.6g}) mm. "
            "Click Done -> 2D or Update to refresh plots.".format(
                row=int(row_index),
                axis=axis_label,
                anchor=anchor_text,
                x=float(target[0]),
                y=float(target[1]),
                z=float(target[2]),
            )
        )

    def _apply_scene_placement_translate_handle(self, row_index: int, axis: str, delta_mm: float) -> None:
        try:
            result = self.editor.translate_scene_row_pose(int(row_index), str(axis), float(delta_mm))
        except Exception as exc:
            self.status_var.set(f"Placement translate failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D placement translate failed: {exc}")
            return
        if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_row_index = int(row_index)
            self._stl_placement_dirty = True
        try:
            self.editor._select_table_row(int(row_index))
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"3D placement translate refresh failed: {exc}")
        row = self.editor.rows[int(row_index)]
        self.status_var.set(
            "Moved S{row} {axis}{delta:+.6g} mm -> Desp=({x:.6g}, {y:.6g}, {z:.6g}) mm.".format(
                row=int(row_index),
                axis=str(result.get("axis", axis)).upper(),
                delta=float(result.get("delta_mm", delta_mm)),
                x=float(row.desp_x),
                y=float(row.desp_y),
                z=float(row.desp_z),
            )
        )

    def _apply_scene_placement_rotate_handle(self, row_index: int, axis: str, delta_deg: float) -> None:
        try:
            result = self.editor.rotate_scene_row_pose_world_axis(int(row_index), str(axis), float(delta_deg))
        except Exception as exc:
            self.status_var.set(f"Placement rotate failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D placement rotate failed: {exc}")
            return
        if self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_row_index = int(row_index)
            self._stl_placement_dirty = True
        try:
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"3D placement rotate refresh failed: {exc}")
        row = self.editor.rows[int(row_index)]
        self.status_var.set(
            "Rotated S{row} {axis}{delta:+.6g} deg -> Tilt=({x:.6g}, {y:.6g}, {z:.6g}) deg.".format(
                row=int(row_index),
                axis=str(result.get("axis", axis)).upper(),
                delta=float(result.get("delta_deg", delta_deg)),
                x=float(row.tilt_x),
                y=float(row.tilt_y),
                z=float(row.tilt_z),
            )
        )

    def _apply_step_carry_snap_ray(self, target_world_xyz, *, ray_index: int | None = None) -> None:
        label = self._step_carry_label() or str(self.editor._selected_step_label or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            self.status_var.set("Snap STEP->Ray: select or import a lens, optical, camera, or LED STEP first.")
            return
        try:
            result = self.editor.snap_step_overlay_center_to_world_point(label, target_world_xyz, target_kind="ray")
        except Exception as exc:
            self.status_var.set(f"Snap STEP->Ray failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D STEP snap to ray failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        self._step_carry_snap_ray_mode = False
        self._step_carry_active_label = label
        self._step_carry_follow_state = None
        self._set_axis_pick_cursor(False)
        try:
            self.refresh_from_editor()
            if ray_index is not None:
                self._set_ray_highlight(int(ray_index))
        except Exception as exc:
            self.editor.append_debug(f"3D STEP snap-to-ray refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        ray_text = f" ray {int(ray_index)}" if ray_index is not None else " picked ray"
        self.status_var.set(
            f"Snapped {label.upper()} STEP center to{ray_text} at "
            f"({float(target[0]):.6g}, {float(target[1]):.6g}, {float(target[2]):.6g}) mm. "
            "Hold the STEP to lift for free movement."
        )

    def _apply_step_carry_snap_target(self, row_index: int, *, face_id: str = "") -> None:
        label = self._step_carry_label() or str(self.editor._selected_step_label or "").strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET or self.editor._step_path_for_label(label) is None:
            self.status_var.set("Snap STEP->Target: select or import a lens, optical, camera, or LED STEP first.")
            return
        try:
            result = self.editor.snap_step_overlay_center_to_scene_target(
                label,
                int(row_index),
                face_id=str(face_id or ""),
            )
        except Exception as exc:
            self.status_var.set(f"Snap STEP->Target failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D STEP snap to target failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        self._step_carry_snap_target_mode = False
        self._step_carry_active_label = label
        self._step_carry_follow_state = None
        self._set_axis_pick_cursor(False)
        try:
            self.refresh_from_editor()
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"3D STEP snap-to-target refresh failed: {exc}")
        target = result.get("target", (float("nan"), float("nan"), float("nan")))
        target_label = str(result.get("target_label", f"S{int(row_index)}") or f"S{int(row_index)}")
        self.status_var.set(
            f"Snapped {label.upper()} STEP center to {target_label} at "
            f"({float(target[0]):.6g}, {float(target[1]):.6g}, {float(target[2]):.6g}) mm. "
            "Hold the STEP to lift for free movement."
        )

    def _edit_open3d_thickness_dimension(self, row_index: int) -> None:
        self._open3d_thickness_dimension_service().edit_dimension(int(row_index))

    def _thickness_dimension_row_under_cursor(self, event) -> int | None:
        """Row index of the thickness-dimension actor under the right-click, if any."""
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        try:
            self._vtk_interactor.SetEventInformationFlipY(int(event.x), int(event.y), 0, 0, chr(0), 0, None)
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    actor = get_view_prop()
            actor_key = self._actor_key(actor)
        except Exception:
            return None
        if actor_key is None:
            return None
        row_index = self._actor_thickness_dimension_map.get(actor_key)
        return int(row_index) if row_index is not None else None

    def _optical_surface_row_for_actor(self, actor_key) -> int | None:
        """Editor surface-row index for a picked actor, or None when the actor is
        a STEP overlay (incl. its transient live-trace row) (bugs/0091).

        A STEP overlay is NOT an Object/Image plane, and its scene row index does
        NOT index ``editor.rows`` (a live-trace overlay row is INSERTED into the
        traced rows, shifting later indices -- e.g. the overlay lands at scene row
        4 while ``editor.rows[4]`` is the Image). If the Quick-Estimation plane
        menu read that, a right-click on the cube popped the QE menu instead of the
        overlay's promote / face-assign menu.
        """
        if actor_key is None:
            return None
        if actor_key in (self._actor_step_map or {}):
            return None
        row = (self._actor_row_map or {}).get(actor_key)
        if row is None:
            return None
        try:
            if int(row) in (self._live_trace_step_overlay_label_by_row() or {}):
                return None
        except Exception:
            pass
        return int(row)

    def _surface_row_under_cursor(self, event) -> int | None:
        """Editor-table row index of the optical surface actor under the right-click."""
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        try:
            self._vtk_interactor.SetEventInformationFlipY(int(event.x), int(event.y), 0, 0, chr(0), 0, None)
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            actor = self._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    actor = get_view_prop()
            actor_key = self._actor_key(actor)
        except Exception:
            return None
        return self._optical_surface_row_for_actor(actor_key)

    def _maybe_show_quick_estimation_role_menu(self, event) -> bool:
        """Right-click on a conjugate thickness handle OR an Object/Image plane
        shows the Quick Estimation role menu."""
        from KrakenOS.UI.services.quick_estimation import IMAGE_THICKNESS, OBJECT_THICKNESS

        # 1) the thickness dimension arrow (the conjugate gap itself).
        row_index = self._thickness_dimension_row_under_cursor(event)
        if row_index is not None:
            qe = self._quick_estimation_service()
            quantity = qe.quantity_for_thickness_row(int(row_index))
            if quantity is not None:
                self._show_quick_estimation_role_menu(event, quantity)
                return True
        # 2) the Object / Image reference plane (the surface body / sensor).
        srow = self._surface_row_under_cursor(event)
        if srow is not None and 0 <= srow < len(self.editor.rows):
            surface = str(getattr(self.editor.rows[srow], "surface", "") or "")
            if surface == "Object":
                self._show_quick_estimation_role_menu(event, OBJECT_THICKNESS, plane="Object Plane")
                return True
            if surface == "Image":
                self._show_quick_estimation_role_menu(event, IMAGE_THICKNESS, plane="Image Plane")
                return True
        # 3) a branch detector (beam-splitter arm) -> register a vendor STEP camera
        #    (B2): the camera determines the sensor size; the detector blends to it
        #    and the per-branch FOV / sensor quick-estimation follows.
        branch_path = self._branch_detector_under_cursor(event)
        if branch_path:
            self._show_branch_detector_camera_menu(event, str(branch_path))
            return True
        return False

    def _branch_detector_under_cursor(self, event) -> str | None:
        """B2: the branch_path of the branch detector whose plane is under the
        right-click, resolved by the picked world point's nearest branch-detector
        target (branch detectors are scene-index 100000+ targets, not editor rows)."""
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return None
        try:
            self._vtk_interactor.SetEventInformationFlipY(int(event.x), int(event.y), 0, 0, chr(0), 0, None)
            x, y = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(x, y, 0.0, self._renderer)
            if self._picker.GetActor() is None:
                return None
            point = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)
        except Exception:
            return None
        if point.shape != (3,) or not np.all(np.isfinite(point)):
            return None
        bundle = getattr(self.editor, "_last_scene_bundle", None)
        if bundle is None:
            return None
        best_path = None
        best_d = None
        for target in (getattr(bundle, "targets", []) or []):
            meta = getattr(target, "metadata", {}) or {}
            if str(meta.get("target_source", "") or "") != "branch_detector":
                continue
            try:
                center = np.asarray(getattr(target, "center_world", None), dtype=float).reshape(3)
            except Exception:
                continue
            dist = float(np.linalg.norm(point - center))
            half = max(
                float(getattr(target, "active_width_mm", 0.0) or 0.0) / 2.0,
                float(getattr(target, "active_height_mm", 0.0) or 0.0) / 2.0,
                5.0,
            )
            if dist <= half * 1.5 and (best_d is None or dist < best_d):
                best_d = dist
                best_path = meta.get("branch_path")
        return str(best_path) if best_path else None

    def _show_branch_detector_camera_menu(self, event, branch_path: str) -> None:
        """B2 right-click menu: register/unregister a vendor STEP camera (= sensor
        size) on a branch detector."""
        try:
            from KrakenOS.UI.camera_database import camera_names
            names = list(camera_names())
        except Exception:
            names = []
        assignments = dict(getattr(self.editor, "branch_detector_camera_assignments", {}) or {})
        current = assignments.get(branch_path)
        short = branch_path.split("->")[-1].strip() if "->" in branch_path else branch_path
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label=f"Branch detector: {short}", state="disabled")
        if current:
            menu.add_command(label=f"camera sensor: {current}", state="disabled")
        menu.add_separator()
        cam_menu = tk.Menu(menu, tearoff=False)
        for name in names:
            mark = "● " if name == current else "    "
            cam_menu.add_command(label=mark + name, command=lambda n=name, bp=branch_path: self._register_branch_detector_camera(bp, n))
        if names:
            menu.add_cascade(label="Register STEP camera (sensor size)…", menu=cam_menu)
        else:
            menu.add_command(label="Register STEP camera (no cameras in DB)", state="disabled")
        if current:
            menu.add_command(label=f"Unregister camera ({current})", command=lambda bp=branch_path: self._register_branch_detector_camera(bp, None))
        try:
            menu.tk_popup(int(event.x_root), int(event.y_root))
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _register_branch_detector_camera(self, branch_path: str, camera_name: str | None) -> None:
        """B2: set/clear the per-branch camera registration, then retrace so the
        branch detector re-sizes to the vendor sensor (and piece 4 glues the camera
        body onto the plane)."""
        assignments = dict(getattr(self.editor, "branch_detector_camera_assignments", {}) or {})
        if camera_name is None:
            assignments.pop(branch_path, None)
            msg = f"Unregistered camera from {branch_path}"
        else:
            assignments[branch_path] = str(camera_name)
            msg = f"Registered {camera_name} sensor to {branch_path}"
        self.editor.branch_detector_camera_assignments = assignments
        try:
            self.editor._invalidate_preview_scene_trace()
        except Exception:
            pass
        self.refresh_from_editor(force_retrace=True)
        self.status_var.set(msg)

    def _snap_detector_to_image_plane(self) -> None:
        """Right-click 'Snap detector to image plane': move the detector (Image row) onto the
        optics' best focus, removing the simulated defocus (item 2)."""
        try:
            moved = bool(self.editor.snap_detector_to_image_plane())
        except Exception as exc:
            self.status_var.set(f"Snap detector to image plane failed: {exc}")
            return
        try:
            self.status_var.set(self.editor.status_var.get())
        except Exception:
            pass
        if moved:
            self.refresh_from_editor(force_retrace=True)

    def _add_image_plane_camera_menu(self, menu) -> None:
        """Append a 'Register STEP camera (sensor size)' cascade for the single-axis detector,
        mirroring the per-branch camera menu so single-axis + cascade arms are uniform (item 1)."""
        try:
            from KrakenOS.UI.camera_database import camera_names, CAMERA_NONE_LABEL
            names = list(camera_names())
        except Exception:
            names, CAMERA_NONE_LABEL = [], "None"
        try:
            current = str(self.editor._current_camera_model() or "")
        except Exception:
            current = ""
        has_cam = bool(current) and current != CAMERA_NONE_LABEL
        menu.add_separator()
        if has_cam:
            menu.add_command(label=f"camera sensor: {current}", state="disabled")
        if names:
            cam_menu = tk.Menu(menu, tearoff=False)
            for name in names:
                mark = "● " if name == current else "    "
                cam_menu.add_command(label=mark + name, command=lambda n=name: self._register_image_plane_camera(n))
            menu.add_cascade(label="Register STEP camera (sensor size)…", menu=cam_menu)
        else:
            menu.add_command(label="Register STEP camera (no cameras in DB)", state="disabled")
        if has_cam:
            menu.add_command(label=f"Unregister camera ({current})", command=lambda: self._register_image_plane_camera(None))

    def _register_image_plane_camera(self, camera_name) -> None:
        """Assign/clear the vendor camera on the single-axis detector from its right-click. COMBINED
        (item 1): sets the sensor size (camera_model -> the detector resizes) AND imports + displays
        the Camera STEP CAD body (the DB entry carries step_path), glued to the detector. Clearing
        removes both."""
        from pathlib import Path
        try:
            from KrakenOS.UI.camera_database import CAMERA_NONE_LABEL
        except Exception:
            CAMERA_NONE_LABEL = "None"
        try:
            self.editor.camera_model_var.set(str(camera_name) if camera_name else CAMERA_NONE_LABEL)
        except Exception as exc:
            self.status_var.set(f"Register camera failed: {exc}")
            return
        body = None
        if camera_name:
            try:
                record = self.editor._current_camera_record() or {}
                step_path = record.get("step_path")
                if step_path and Path(str(step_path)).exists():
                    body = Path(str(step_path))
            except Exception:
                body = None
        try:
            self.editor.imported_camera_step_path = body   # display the camera CAD body (or clear it)
        except Exception:
            pass
        if camera_name:
            msg = f"Registered {camera_name}: sensor + Camera STEP body" if body else f"Registered {camera_name} sensor (no CAD body found)"
        else:
            msg = "Unregistered detector camera (sensor + body cleared)"
        self.status_var.set(msg)
        try:
            self.editor._invalidate_preview_scene_trace()
        except Exception:
            pass
        self.refresh_from_editor(force_retrace=True)

    def _show_quick_estimation_role_menu(self, event, quantity: str, plane: str | None = None) -> None:
        from KrakenOS.UI.services.quick_estimation import (
            LABELS,
            ROLE_CONSTANT,
            ROLE_DEPENDENT,
            ROLE_INDEPENDENT,
        )

        qe = self._quick_estimation_service()
        menu = tk.Menu(self, tearoff=False)
        title = plane or LABELS.get(quantity, quantity)
        menu.add_command(label=f"{title}  (role: {qe.role(quantity)})", state="disabled")
        if plane:
            menu.add_command(label=f"drives {LABELS.get(quantity, quantity)}", state="disabled")
        menu.add_separator()
        if not qe.is_enabled():
            menu.add_command(label="Enable Quick Estimation", command=lambda: self._set_quick_estimation_role(quantity, qe.role(quantity)))
            menu.add_separator()
        menu.add_command(label="Set Variable — Independent (drive)", command=lambda: self._set_quick_estimation_role(quantity, ROLE_INDEPENDENT))
        menu.add_command(label="Set Variable — Dependent (solve for focus)", command=lambda: self._set_quick_estimation_role(quantity, ROLE_DEPENDENT))
        menu.add_command(label="Set Constant (pin value)", command=lambda: self._set_quick_estimation_role(quantity, ROLE_CONSTANT))
        if plane == "Object Plane":
            menu.add_separator()
            menu.add_command(label="Set Target Object Height (FOV)…", command=self._quick_estimation_set_target_fov)
            menu.add_command(label="Snap object+image distance to this FOV", command=self._quick_estimation_snap_to_fov)
            menu.add_command(label="Configuration table…", command=self._show_quick_estimation_config_table)
        elif plane == "Image Plane":
            # The sensor (Real Image Semi-Height) is the canonical left-panel
            # Field value; editing here writes the same editor var, then retraces.
            menu.add_separator()
            menu.add_command(label="Set sensor semi-height (Field value)…", command=self._quick_estimation_edit_field_value)
            menu.add_command(label="Set Field type…", command=self._quick_estimation_edit_field_type)
            menu.add_separator()
            menu.add_command(label="Snap detector to image plane (remove defocus)", command=self._snap_detector_to_image_plane)
            # Per-detector camera STEP (vendor sensor): right-click the detector to assign a camera,
            # mirroring the per-branch "Register STEP camera" so single-axis and cascade arms are
            # uniform (item 1; user expects camera import from the detector right-click).
            self._add_image_plane_camera_menu(menu)
        try:
            menu.tk_popup(int(event.x_root), int(event.y_root))
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _centered_input_dialog(self, title: str, prompt: str, initial: str) -> str | None:
        """Small screen-centred modal text input reusing the reliable
        _show_centered_dialog placement (works under Wayland/layer-shell)."""
        holder: dict[str, str] = {}
        dialog = tk.Toplevel(self)
        try:
            dialog.withdraw()
            dialog.title(title)
            dialog.transient(self.winfo_toplevel())
            dialog.resizable(False, False)
        except Exception:
            pass
        var = tk.StringVar(value=str(initial))
        ttk.Label(dialog, text=prompt, wraplength=360, justify="left").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )
        entry = ttk.Entry(dialog, textvariable=var, width=20)
        entry.grid(row=1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

        def accept(_event=None):
            holder["value"] = var.get()
            dialog.destroy()

        ttk.Button(dialog, text="OK", command=accept).grid(row=2, column=0, padx=(12, 4), pady=(0, 12), sticky="e")
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(row=2, column=1, padx=(4, 12), pady=(0, 12), sticky="w")
        dialog.bind("<Return>", accept)
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        try:
            dialog.grab_set()
        except Exception:
            pass
        try:
            self.editor._show_centered_dialog(dialog)
        except Exception:
            pass
        try:
            entry.focus_set()
            entry.selection_range(0, "end")
        except Exception:
            pass
        self.wait_window(dialog)
        return holder.get("value")

    def _quick_estimation_edit_field_value(self) -> None:
        try:
            current = str(self.editor.field_value_var.get())
            ftype = str(self.editor.field_type_var.get())
        except Exception:
            current, ftype = "0", "Field"
        value = self._centered_input_dialog(
            "Object Field Value",
            f"Object height / Field value [mm]\n(Field type: {ftype})",
            current,
        )
        if value is None:
            return
        try:
            float(value)
        except (TypeError, ValueError):
            self.status_var.set("Field value must be a number.")
            return
        try:
            self.editor.field_value_var.set(str(value))
            self._commit_live_control_update(sync_fields=True)
            self.status_var.set(f"Field value (object height) set to {value} mm.")
        except Exception as exc:
            self.status_var.set(f"Could not set field value: {exc}")

    def _quick_estimation_edit_field_type(self) -> None:
        try:
            current = str(self.editor.field_type_var.get())
        except Exception:
            current = ""
        value = self._centered_input_dialog(
            "Field Type",
            "Field type (e.g. Object Height, Object Angle, Real Image Height):",
            current,
        )
        if value is None or not str(value).strip():
            return
        try:
            self.editor.field_type_var.set(str(value).strip())
            self._commit_live_control_update(sync_fields=True)
            self.status_var.set(f"Field type set to {value}.")
        except Exception as exc:
            self.status_var.set(f"Could not set field type: {exc}")

    def _quick_estimation_set_target_fov(self) -> None:
        qe = self._quick_estimation_service()
        if not qe.is_enabled():
            self.quick_estimation_var.set(True)
        cur = qe.target_object_semi()
        cur_full = f"{2 * cur:.6g}" if cur else ""
        value = self._centered_input_dialog(
            "Target FOV / Object Height",
            "Object size to image (full Object Height) [mm]; blank = fill the sensor:",
            cur_full,
        )
        if value is None:
            return
        if not str(value).strip():
            qe.set_target_fov(None)
            qe.update_readout()
            self.status_var.set("Target FOV cleared (FOV = fill the sensor).")
            return
        try:
            full = float(value)
        except (TypeError, ValueError):
            self.status_var.set("Object Height must be a number.")
            return
        qe.set_target_fov(full / 2.0)
        qe.update_readout()
        state = qe.current_state()
        fill = state.get("fill_factor")
        if fill is not None:
            self.status_var.set(
                f"Target FOV {full:.6g} mm -> {100 * fill:.1f}% of sensor. "
                "Drag a distance (other auto-solves for focus) or Snap to reach 100%."
            )
        else:
            self.status_var.set(f"Target Object Height set to {full:.6g} mm.")

    def _quick_estimation_snap_to_fov(self) -> None:
        qe = self._quick_estimation_service()
        if not qe.is_enabled():
            self.quick_estimation_var.set(True)
        if not qe.target_object_semi():
            self._quick_estimation_set_target_fov()
            if not qe.target_object_semi():
                return
        self.editor._begin_history_capture()
        ok, msg = qe.snap_to_fov()
        if ok:
            self.editor._sync_table()
            self.editor._commit_history_capture()
            self.editor._invalidate_preview_scene_trace()
            self.editor._sync_trace_state_badge()
            self.refresh_from_editor(force_retrace=True)
            qe.update_readout()
        else:
            self.editor._commit_history_capture()
        self.status_var.set(msg)

    def _open3d_toggle_variable_thickness(self, row_index: int) -> None:
        """Sync a thickness gap's Variable flag (shared with 2D optimization) to
        its checkbox, which Tk has already flipped before calling this."""
        service = self._open3d_solve_service()
        row_index = int(row_index)
        vars_map = getattr(self, "_open3d_variable_thickness_vars", None) or {}
        var = vars_map.get(row_index)
        enabled = bool(var.get()) if var is not None else (not service.is_variable(row_index))
        service.set_variable(row_index, enabled)
        self.status_var.set(f"Thickness row {row_index} marked {'Variable' if enabled else 'fixed'}.")

    def _open3d_run_thickness_solve(self, objective: str) -> None:
        """Solve the Variable thickness gaps for best focus / collimation, then
        retrace (same history + refresh path as Snap to FOV)."""
        service = self._open3d_solve_service()
        self.editor._begin_history_capture()
        try:
            ok, msg = service.solve(objective)
        except Exception as exc:
            self.editor._commit_history_capture()
            self.status_var.set(f"Solve failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D thickness solve failed: {exc}")
            return
        if ok:
            self.editor._sync_table()
            self.editor._commit_history_capture()
            self.editor._invalidate_preview_scene_trace()
            self.editor._sync_trace_state_badge()
            self.refresh_from_editor(force_retrace=True)
            try:
                self._quick_estimation_service().update_readout()
            except Exception:
                pass
        else:
            self.editor._commit_history_capture()
        self.status_var.set(msg)

    def _maybe_open_fov_popup_from_double_click(self, event) -> bool:
        """Double-left-click on the Object/Image plane disk opens the FOV box
        (bugs/0055). Single click still just selects the row."""
        if getattr(self, "_dimension_anchor_pick_mode", False):
            return False
        srow = self._surface_row_under_cursor(event)
        if srow is None or not (0 <= srow < len(self.editor.rows)):
            return False
        surface = str(getattr(self.editor.rows[srow], "surface", "") or "")
        if surface == "Object":
            self.after(1, lambda: self._open_quick_estimation_fov_popup("object"))
            return True
        if surface == "Image":
            self.after(1, lambda: self._open_quick_estimation_fov_popup("image"))
            return True
        return False

    def _open_quick_estimation_fov_popup(self, plane: str) -> None:
        """A small modal box: type the plane's field width x height, then click
        either 'Solve for Thickness' (move the conjugate pair so the field fills /
        maps to the sensor) or 'Solve for Image/Sensor Size' (resize the sensor at
        the current magnification). Fill just Width or just Height -- the blank box
        is derived from the live sensor aspect. bugs/0055, bugs/0057."""
        qe = self._quick_estimation_service()
        if not qe.is_enabled():
            self.quick_estimation_var.set(True)
        if plane == "object":
            title = "Object Plane — Field of View (FOV)"
            prompt = "Object field to image (width x height, mm):"
            wh = qe.object_fov_dimensions()
        else:
            title = "Image Plane — Sensor Size"
            prompt = "Image / sensor size (width x height, mm):"
            wh = qe.sensor_active_dimensions()
        dialog = tk.Toplevel(self)
        try:
            dialog.withdraw()
            dialog.title(title)
            dialog.transient(self.winfo_toplevel())
            dialog.resizable(False, False)
        except Exception:
            pass
        ttk.Label(dialog, text=prompt, wraplength=320, justify="left").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 6), sticky="w"
        )
        w0, h0 = (wh if wh else (0.0, 0.0))
        width_var = tk.StringVar(value=(f"{w0:.6g}" if w0 else ""))
        height_var = tk.StringVar(value=(f"{h0:.6g}" if h0 else ""))
        ttk.Label(dialog, text="Width (mm):").grid(
            row=1, column=0, padx=(12, 4), pady=(0, 4), sticky="e"
        )
        entry = ttk.Entry(dialog, textvariable=width_var, width=12)
        entry.grid(row=1, column=1, padx=(0, 12), pady=(0, 4), sticky="ew")
        ttk.Label(dialog, text="Height (mm):").grid(
            row=2, column=0, padx=(12, 4), pady=(0, 10), sticky="e"
        )
        ttk.Entry(dialog, textvariable=height_var, width=12).grid(
            row=2, column=1, padx=(0, 12), pady=(0, 10), sticky="ew"
        )
        ttk.Label(
            dialog,
            text="Fill just one box — the other is derived from the sensor aspect.",
            foreground="#888888",
            wraplength=320,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="w")
        button_row = 4

        def _read_dim(var, label):
            """Parse one box: blank -> (True, None) so it is derived; a present but
            non-positive / non-numeric value -> (False, None) with a status note."""
            raw = var.get().strip() if var is not None else ""
            if not raw:
                return True, None
            try:
                val = float(raw)
            except (TypeError, ValueError):
                self.status_var.set(f"{label} must be a number (or blank).")
                return False, None
            if not (val > 0):
                self.status_var.set(f"{label} must be positive (or blank).")
                return False, None
            return True, val

        def run(mode):
            ok_w, width = _read_dim(width_var, "Width")
            if not ok_w:
                return
            ok_h, height = _read_dim(height_var, "Height")
            if not ok_h:
                return
            if width is None and height is None:
                self.status_var.set(
                    "Enter a Width or a Height — the other is derived from the sensor aspect."
                )
                return
            aspect = (w0, h0) if (w0 and h0) else None
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()
            self._apply_quick_estimation_fov_solve(plane, mode, width, height, aspect)

        ttk.Button(dialog, text="Solve for Thickness", command=lambda: run("thickness")).grid(
            row=button_row, column=0, padx=(12, 4), pady=(0, 6), sticky="ew"
        )
        ttk.Button(dialog, text="Solve for Image/Sensor Size", command=lambda: run("sensor")).grid(
            row=button_row, column=1, padx=(4, 12), pady=(0, 6), sticky="ew"
        )
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(
            row=button_row + 1, column=0, columnspan=2, padx=12, pady=(0, 12)
        )
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        try:
            dialog.grab_set()
        except Exception:
            pass
        try:
            self.editor._show_centered_dialog(dialog)
        except Exception:
            pass
        try:
            entry.focus_set()
            entry.selection_range(0, "end")
        except Exception:
            pass
        self.wait_window(dialog)

    def _apply_quick_estimation_fov_solve(
        self,
        plane: str,
        mode: str,
        width: float | None,
        height: float | None = None,
        aspect: tuple[float, float] | None = None,
    ) -> None:
        qe = self._quick_estimation_service()
        self.editor._begin_history_capture()
        ok, msg = qe.fov_solve(plane, mode, width, height, aspect)
        if ok:
            try:
                self.editor._sync_table()
            except Exception:
                pass
            try:
                self.editor._sync_object_controls()
            except Exception:
                pass
            self.editor._commit_history_capture()
            try:
                self.editor._invalidate_preview_scene_trace()
                self.editor._sync_trace_state_badge()
            except Exception:
                pass
            self.refresh_from_editor(force_retrace=True)
            qe.update_readout()
        else:
            self.editor._commit_history_capture()
        self.status_var.set(msg)

    def _open_step_overlay_resize_popup(self, step_label: str) -> None:
        """Resize an imported STEP solid by typing its target dimensions.

        A solid with a detected 45-deg coating (a beam-splitter cube) exposes a
        single square **Cross-section** plus a free **Depth**, so the two coupled
        axes grow together and the coating stays at 45 deg (the two prisms grow
        as one).  Any other solid exposes independent Width x Height x Depth.
        This is the "direct edit the thickness" box; the drag-arrow gesture will
        route here too.  (bugs/0064 drag-to-resize.)
        """
        label = str(step_label).strip().lower()
        if self.editor._step_path_for_label(label) is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return
        original = self.editor._step_overlay_original_extents(label)
        if original is None or not np.all(np.isfinite(np.asarray(original, dtype=float))):
            self.status_var.set("Could not read the imported solid's dimensions.")
            return
        axes = self.editor._step_overlay_resize_axes(label)
        spec = self.editor._step_resize_for_label(label)
        current = [float(v) for v in original[:3]]
        if spec and spec.get("target_extents"):
            for i, value in enumerate(spec["target_extents"]):
                if value:
                    current[i] = float(value)
        display = self.editor._step_overlay_display_label(label).upper()
        coupled = axes is not None

        dialog = tk.Toplevel(self)
        try:
            dialog.withdraw()
            dialog.title(f"{display} STEP — Resize Solid")
            dialog.transient(self.winfo_toplevel())
            dialog.resizable(False, False)
        except Exception:
            pass

        if coupled:
            s_axis = axes.coupled_axes[0]
            d_axis = axes.free_axis
            prompt = (
                f"{display} beam-splitter cube — the 45° coating stays square, so the "
                f"cross-section ({axes.coupled_labels[0]}×{axes.coupled_labels[1]}) grows on "
                f"both axes together; the depth ({axes.free_label}) is free."
            )
            fields = [
                ("Cross-section (mm):", current[s_axis]),
                ("Depth (mm):", current[d_axis]),
            ]
        else:
            prompt = f"{display} solid — target outer size (width × height × depth, mm)."
            fields = [
                ("Width (mm):", current[0]),
                ("Height (mm):", current[1]),
                ("Depth (mm):", current[2]),
            ]
        ttk.Label(dialog, text=prompt, wraplength=340, justify="left").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 8), sticky="w"
        )
        entry_vars: list[tk.StringVar] = []
        first_entry = None
        for index, (text, value) in enumerate(fields):
            ttk.Label(dialog, text=text).grid(
                row=1 + index, column=0, padx=(12, 4), pady=(0, 4), sticky="e"
            )
            var = tk.StringVar(value=(f"{value:.6g}" if value else ""))
            entry = ttk.Entry(dialog, textvariable=var, width=12)
            entry.grid(row=1 + index, column=1, padx=(0, 12), pady=(0, 4), sticky="ew")
            entry_vars.append(var)
            if first_entry is None:
                first_entry = entry
        button_row = 1 + len(fields)

        def run() -> None:
            try:
                values = [float(var.get()) for var in entry_vars]
            except (TypeError, ValueError):
                self.status_var.set("Dimensions must be numbers.")
                return
            if not all(v > 0 for v in values):
                self.status_var.set("Dimensions must be positive.")
                return
            target: list[float | None] = [None, None, None]
            if coupled:
                cross, depth = values
                for axis in axes.coupled_axes:
                    target[axis] = cross
                target[axes.free_axis] = depth
                anchor_axis = axes.free_axis
            else:
                target = list(values)  # type: ignore[assignment]
                anchor_axis = None
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()
            self._apply_step_overlay_resize_solve(label, target, anchor_axis, coupled)

        ttk.Button(dialog, text="Resize", command=run).grid(
            row=button_row, column=0, padx=(12, 4), pady=(8, 12), sticky="ew"
        )
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).grid(
            row=button_row, column=1, padx=(4, 12), pady=(8, 12), sticky="ew"
        )
        dialog.bind("<Return>", lambda _e: run())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        try:
            dialog.grab_set()
        except Exception:
            pass
        try:
            self.editor._show_centered_dialog(dialog)
        except Exception:
            pass
        try:
            if first_entry is not None:
                first_entry.focus_set()
                first_entry.selection_range(0, "end")
        except Exception:
            pass
        self.wait_window(dialog)

    def _apply_step_overlay_resize_solve(
        self,
        label: str,
        target_extents,
        anchor_axis: int | None,
        coupled: bool,
    ) -> None:
        self.editor._begin_history_capture()
        try:
            self.editor._set_step_resize_for_label(
                label,
                target_extents,
                anchor_axis=anchor_axis,
                anchor_at_max=False,
                coupled=coupled,
            )
        finally:
            self.editor._commit_history_capture()
        try:
            self.editor._invalidate_preview_scene_trace()
        except Exception:
            pass
        try:
            self.refresh_imported_step_overlay(label)
        except Exception:
            pass
        self.refresh_from_editor(force_retrace=True)
        display = self.editor._step_overlay_display_label(label).upper()
        dims = " × ".join(f"{v:.6g}" if v else "·" for v in target_extents)
        self.status_var.set(f"{display} STEP resized to {dims} mm.")

    def _show_quick_estimation_config_table(self) -> None:
        """Centred table of conjugate configurations (object distance swept;
        image distance solved for focus) so the user can read the combinations."""
        import numpy as _np

        qe = self._quick_estimation_service()
        f = qe.focal_length()
        sensor = qe._sensor_semi()
        if not f or not sensor:
            self.status_var.set("Configuration table needs a valid lens + sensor.")
            return
        rows = self.editor.rows
        obj_row = qe.object_thickness_row()
        img_row = qe.image_thickness_row()
        if obj_row is None or img_row is None:
            return
        saved = (float(rows[obj_row].thickness), float(rows[img_row].thickness))
        records = []
        try:
            for s in _np.linspace(f * 1.25, f * 5.0, 16):
                rows[obj_row].thickness = float(s)
                ok, _note = qe.solve_dependent(obj_row)
                st = qe.current_state()
                records.append(
                    (
                        float(s),
                        st.get("image_distance"),
                        st.get("magnification"),
                        st.get("fov_full"),
                        st.get("working_distance"),
                        not st.get("forbidden"),
                    )
                )
        finally:
            rows[obj_row].thickness, rows[img_row].thickness = saved
            try:
                qe.update_readout()
            except Exception:
                pass

        dialog = tk.Toplevel(self)
        try:
            dialog.withdraw()
            dialog.title("Quick Estimation — configuration table")
            dialog.transient(self.winfo_toplevel())
        except Exception:
            pass
        ttk.Label(
            dialog,
            text=f"Fixed lens f={f:.4g} mm, sensor semi-height {sensor:.4g} mm. "
            "Each row is a focused conjugate; drag toward the one you want.",
            padding=(8, 8, 8, 4),
        ).grid(row=0, column=0, sticky="w")
        cols = ("obj", "img", "mag", "fov", "wd", "valid")
        headers = ("Object dist [mm]", "Image dist [mm]", "Mag |m|", "FOV full [mm]", "Working dist [mm]", "Real image?")
        tree = ttk.Treeview(dialog, columns=cols, show="headings", height=min(len(records), 16))
        for c, h in zip(cols, headers):
            tree.heading(c, text=h)
            tree.column(c, width=120, anchor="center")
        for obj, img, mag, fov, wd, valid in records:
            tree.insert(
                "",
                "end",
                values=(
                    f"{obj:.5g}" if obj is not None else "--",
                    f"{img:.5g}" if img is not None else "--",
                    f"{abs(mag):.4g}" if mag is not None else "--",
                    f"{fov:.5g}" if fov is not None else "--",
                    f"{wd:.5g}" if wd is not None else "--",
                    "yes" if valid else "NO (WD<FL)",
                ),
            )
        tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 6))
        ttk.Button(dialog, text="Close", command=dialog.destroy).grid(row=2, column=0, sticky="e", padx=8, pady=(0, 8))
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        try:
            self.editor._show_centered_dialog(dialog)
        except Exception:
            pass

    def _set_quick_estimation_role(self, quantity: str, role: str) -> None:
        qe = self._quick_estimation_service()
        if not qe.is_enabled():
            self.quick_estimation_var.set(True)
        summary = qe.set_role(quantity, role)
        qe.update_readout()
        panel = self.__dict__.get("_open3d_live_controls_panel_instance")
        if panel is not None and hasattr(panel, "_refresh_quick_estimation_role_combos"):
            try:
                panel._refresh_quick_estimation_role_combos()
            except Exception:
                pass
        if summary:
            self.status_var.set(summary)

    def _update_thickness_hover_highlight(self, x: int, y: int) -> None:
        """Highlight the thickness-dimension handle under the cursor (passive hover)."""
        amap = getattr(self, "_actor_thickness_dimension_map", None)
        if not amap:
            # nothing hoverable -- only clear a stale highlight, no VTK pick.
            if self.__dict__.get("_thickness_hover_actor_key"):
                self._apply_thickness_hover_highlight(None, None, None)
            return
        last = self.__dict__.get("_thickness_hover_xy")
        if last is not None and abs(last[0] - x) < 3 and abs(last[1] - y) < 3:
            return
        self._thickness_hover_xy = (x, y)
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return
        actor = None
        actor_key = None
        try:
            self._vtk_interactor.SetEventInformationFlipY(int(x), int(y), 0, 0, chr(0), 0, None)
            px, py = self._vtk_interactor.GetEventPosition()
            self._picker.Pick(px, py, 0.0, self._renderer)
            actor = self._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    actor = get_view_prop()
            actor_key = self._actor_key(actor)
        except Exception:
            actor = None
            actor_key = None
        row = amap.get(actor_key) if actor_key else None
        if row is None:
            self._apply_thickness_hover_highlight(None, None, None)
        else:
            self._apply_thickness_hover_highlight(actor, actor_key, int(row))

    def _apply_thickness_hover_highlight(self, actor, actor_key, row) -> None:
        if self.__dict__.get("_thickness_hover_actor_key") == actor_key:
            return
        # restore the previously highlighted handle.
        prev = self.__dict__.get("_thickness_hover_restore")
        if prev is not None:
            prev_actor, prev_color = prev
            try:
                prev_actor.GetProperty().SetColor(*prev_color)
            except Exception:
                pass
        self._thickness_hover_restore = None
        self._thickness_hover_actor_key = None
        if actor is not None and row is not None:
            try:
                prop = actor.GetProperty()
                self._thickness_hover_restore = (actor, tuple(prop.GetColor()))
                prop.SetColor(1.0, 0.85, 0.2)  # amber highlight
                self._thickness_hover_actor_key = actor_key
                self.status_var.set(
                    f"S{int(row)} Thickness handle — drag to adjust, click to type, right-click for role."
                )
            except Exception:
                pass
        try:
            self.render()
        except Exception:
            pass

    def _thickness_arrow_actors(self, row_index: int):
        keys = (getattr(self, "_thickness_dimension_actor_map", {}) or {}).get(int(row_index), [])
        actors = []
        for key in keys:
            actor = (getattr(self, "_actor_by_key", {}) or {}).get(key)
            if actor is not None:
                actors.append(actor)
        return actors

    def _start_thickness_forbidden_flash(self, row_index: int, message: str) -> None:
        """Flash a thickness arrow red to warn of a forbidden value (e.g. WD<FL)."""
        if self.__dict__.get("_forbidden_flash_row") == int(row_index):
            return
        self._stop_thickness_forbidden_flash()
        actors = self._thickness_arrow_actors(int(row_index))
        if not actors:
            return
        originals = []
        for actor in actors:
            try:
                originals.append((actor, tuple(actor.GetProperty().GetColor())))
            except Exception:
                pass
        self._forbidden_flash_row = int(row_index)
        self._forbidden_flash_originals = originals
        self._forbidden_flash_on = False
        if message:
            self.status_var.set(f"⛔ {message}")

        def _tick():
            if self.__dict__.get("_forbidden_flash_row") != int(row_index):
                return
            self._forbidden_flash_on = not self.__dict__.get("_forbidden_flash_on", False)
            color = (1.0, 0.1, 0.1) if self._forbidden_flash_on else (1.0, 0.55, 0.0)
            for actor, _orig in self.__dict__.get("_forbidden_flash_originals", []):
                try:
                    actor.GetProperty().SetColor(*color)
                except Exception:
                    pass
            try:
                self.render()
            except Exception:
                pass
            self._forbidden_flash_after = self.after(280, _tick)

        _tick()

    def _stop_thickness_forbidden_flash(self) -> None:
        after_id = self.__dict__.get("_forbidden_flash_after")
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._forbidden_flash_after = None
        for actor, color in self.__dict__.get("_forbidden_flash_originals", []) or []:
            try:
                actor.GetProperty().SetColor(*color)
            except Exception:
                pass
        if self.__dict__.get("_forbidden_flash_row") is not None:
            try:
                self.render()
            except Exception:
                pass
        self._forbidden_flash_row = None
        self._forbidden_flash_originals = []
        self._forbidden_flash_on = False

    def _thickness_drag_state_from_current_pick(self) -> dict[str, object] | None:
        return self._open3d_thickness_dimension_service().drag_state_from_current_pick()

    def _apply_thickness_drag_motion(self, dx: int | float, dy: int | float) -> None:
        self._open3d_thickness_dimension_service().apply_drag_motion(self._thickness_drag_state, dx, dy)

    def _finish_thickness_drag(self, state: dict[str, object]) -> None:
        self._open3d_thickness_dimension_service().finish_drag(state)

    def _interaction_service(self) -> Open3DInteractionService:
        service = self.__dict__.get("_interaction_service_instance")
        if service is None:
            service = Open3DInteractionService(self)
            self._interaction_service_instance = service
        return service

    def _on_left_button_press(self, obj, _event) -> None:
        if (
            getattr(self, "_measure_pick_mode", False)
            and self._picker is not None
            and self._renderer is not None
            and self._vtk_interactor is not None
        ):
            hit_actor = None
            world = None
            normal = None
            try:
                x, y = self._vtk_interactor.GetEventPosition()
                self._picker.Pick(x, y, 0.0, self._renderer)
                hit_actor = self._picker.GetActor()
                world = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
                try:
                    normal = np.asarray(self._picker.GetPickNormal(), dtype=float).reshape(-1)[:3]
                except Exception:
                    normal = None
            except Exception:
                hit_actor = None
                world = None
                normal = None
            if hit_actor is not None and world is not None and world.size >= 3:
                self._record_measure_point(world, normal)
            else:
                self.status_var.set("Measure: click ON an edge/surface (the pick missed).")
            return
        return self._interaction_service()._on_left_button_press(obj, _event)

    def _on_mouse_move(self, obj, _event) -> None:
        # Deep-trace wrap: log every entry / exit, including position
        # and which interaction modes are active. The interaction
        # service applies its own throttle (so the baseline timing log
        # gets one event per ~50 ms), but the deep-trace wrapper has
        # no throttle -- we want one entry per VTK callback so a hang
        # mid-handler shows up as an _on_mouse_move_start with no
        # matching _done.
        if not open3d_trace_enabled():
            return self._interaction_service()._on_mouse_move(obj, _event)
        x = y = -1
        try:
            if self._vtk_interactor is not None:
                x, y = self._vtk_interactor.GetEventPosition()
        except Exception:
            pass
        from KrakenOS.UI.services.open3d_timing import open3d_trace_span as _span

        with _span("inspector_on_mouse_move", x=int(x), y=int(y)):
            return self._interaction_service()._on_mouse_move(obj, _event)

    def _bind_trace_window_observers(self, render_window) -> None:
        """Log every VTK render-window resize / modified event."""
        if render_window is None:
            return
        try:
            render_window.AddObserver("ModifiedEvent", self._on_trace_render_window_modified)
        except Exception:
            pass
        try:
            render_window.AddObserver("WindowResizeEvent", self._on_trace_render_window_resized)
        except Exception:
            pass

    def _on_trace_render_window_modified(self, obj, _event) -> None:
        try:
            size = obj.GetSize() if obj is not None else (-1, -1)
        except Exception:
            size = (-1, -1)
        open3d_trace_event("vtk_render_window_modified", w=int(size[0]), h=int(size[1]))

    def _on_trace_render_window_resized(self, obj, _event) -> None:
        try:
            size = obj.GetSize() if obj is not None else (-1, -1)
        except Exception:
            size = (-1, -1)
        open3d_trace_event("vtk_render_window_resized", w=int(size[0]), h=int(size[1]))

    def _bind_trace_tk_configure(self) -> None:
        """Log every Tk <Configure> on the inspector window itself.

        Captures maximize / restore / window-drag events that VTK's
        own observer chain might miss because Tk forwards them
        asynchronously into the VTK widget.
        """
        try:
            self.bind("<Configure>", self._on_trace_tk_configure, add="+")
        except Exception:
            pass

    def _on_trace_tk_configure(self, event) -> None:
        try:
            width = int(getattr(event, "width", -1))
            height = int(getattr(event, "height", -1))
        except Exception:
            width = height = -1
        try:
            wm_state = self.wm_state()
        except Exception:
            wm_state = ""
        open3d_trace_event(
            "tk_configure",
            w=width,
            h=height,
            wm_state=str(wm_state),
        )

    def _set_axis_pick_cursor(self, hand: bool) -> None:
        try:
            if self._vtk_widget is not None:
                self._vtk_widget.configure(cursor="crosshair" if hand else "")
        except Exception:
            pass
        try:
            if self._vtk_interactor is not None:
                self._vtk_interactor.SetCurrentCursor(9 if hand else 0)
        except Exception:
            pass

    def _set_rotation_handle_hover(self, actor_key: str | None) -> None:
        self._open3d_step_rotation_handle_service().set_hover(actor_key)

    @staticmethod
    def _step_hover_outline_style(has_surface: bool) -> tuple[tuple[float, float, float], float, float]:
        """Style for the STEP face hover highlight: (rgb, opacity, line_width).

        Uses the shared hover-gold accent (1.0, 0.78, 0.08) -- never red. A
        red highlight reads edge-on as a "ghost red edge" bar through the lens
        (bug 0005), and clashes with the pink selection / gold hover language.
        """
        gold = (1.0, 0.78, 0.08)
        if has_surface:
            return gold, 0.42, 4.0
        return gold, 0.9, 4.0

    def _set_step_hover_outline(self, outline_mesh, hover_key, *, render: bool = True) -> None:
        if not open3d_trace_enabled():
            return self._set_step_hover_outline_impl(outline_mesh, hover_key, render=render)
        from KrakenOS.UI.services.open3d_timing import open3d_trace_span as _span
        with _span(
            "set_step_hover_outline",
            has_outline=outline_mesh is not None,
            has_key=hover_key is not None,
            same_key=bool(hover_key is not None and hover_key == self._hover_step_cell_key),
        ):
            return self._set_step_hover_outline_impl(outline_mesh, hover_key, render=render)

    def _set_step_hover_outline_impl(self, outline_mesh, hover_key, *, render: bool = True) -> None:
        if hover_key is not None and hover_key == self._hover_step_cell_key:
            return
        if self._renderer is None:
            return
        if self._hover_step_outline_actor is not None:
            self._remove_renderer_view_prop(self._hover_step_outline_actor)
            self._hover_step_outline_actor = None
        self._hover_step_cell_key = hover_key
        if outline_mesh is not None and int(getattr(outline_mesh, "n_points", 0)) > 0 and vtkActor is not None and vtkDataSetMapper is not None:
            try:
                has_surface = False
                try:
                    has_surface = int(outline_mesh.GetNumberOfPolys()) > 0
                except Exception:
                    try:
                        has_surface = int(getattr(outline_mesh, "n_faces_strict", 0)) > 0
                    except Exception:
                        has_surface = False
                mapper = vtkDataSetMapper()
                mapper.SetInputData(outline_mesh)
                try:
                    mapper.ScalarVisibilityOff()
                except Exception:
                    pass
                actor = vtkActor()
                actor.SetMapper(mapper)
                prop = actor.GetProperty()
                color, opacity, line_width = self._step_hover_outline_style(has_surface)
                prop.SetColor(*color)
                prop.SetOpacity(opacity)
                prop.SetLineWidth(line_width)
                if has_surface:
                    try:
                        prop.EdgeVisibilityOff()
                    except Exception:
                        pass
                try:
                    prop.SetAmbient(1.0)
                    prop.SetDiffuse(0.0)
                    prop.RenderLinesAsTubesOn()
                except Exception:
                    pass
                actor.PickableOff()
                self._add_renderer_view_prop(actor)
                self._hover_step_outline_actor = actor
            except Exception:
                self._hover_step_outline_actor = None
        if render:
            self.render()

    @staticmethod
    def _picked_feature_info(actor, picker) -> tuple[np.ndarray, object | None, np.ndarray | None] | None:
        if actor is None or picker is None:
            return None
        try:
            cell_id = int(picker.GetCellId())
        except Exception:
            cell_id = -1
        if cell_id < 0:
            return None
        try:
            data = actor.GetMapper().GetInput()
        except Exception:
            data = None
        if data is None:
            return None
        try:
            seed_cell = data.GetCell(cell_id)
            seed_ids = seed_cell.GetPointIds()
            seed_points = np.asarray(
                [data.GetPoint(seed_ids.GetId(index)) for index in range(seed_ids.GetNumberOfIds())],
                dtype=float,
            )
        except Exception:
            return None
        if seed_points.ndim != 2 or seed_points.shape[0] < 3:
            center = np.mean(seed_points, axis=0) if seed_points.size else None
            return (center, None, None) if center is not None else None
        normal = np.cross(seed_points[1] - seed_points[0], seed_points[2] - seed_points[0])
        normal_norm = float(np.linalg.norm(normal))
        if normal_norm <= 1e-12:
            return np.mean(seed_points, axis=0), None, None
        normal /= normal_norm
        round_lens_feature = Kraken3DInspector._round_lens_feature_for_cell(data, cell_id)
        if round_lens_feature is not None:
            return round_lens_feature
        seed_center = np.mean(seed_points, axis=0)
        plane_d = float(np.dot(normal, seed_center))
        try:
            bounds = np.asarray(data.GetBounds(), dtype=float)
            span = max(float(bounds[1] - bounds[0]), float(bounds[3] - bounds[2]), float(bounds[5] - bounds[4]), 1.0)
            cell_count = int(data.GetNumberOfCells())
        except Exception:
            span = 1.0
            cell_count = 0
        plane_tol = max(span * 5e-5, 0.02)
        point_to_cells: dict[int, list[int]] = {}
        coplanar_cells: set[int] = set()
        for candidate_id in range(cell_count):
            try:
                cell = data.GetCell(candidate_id)
                ids = cell.GetPointIds()
                pts = np.asarray(
                    [data.GetPoint(ids.GetId(index)) for index in range(ids.GetNumberOfIds())],
                    dtype=float,
                )
            except Exception:
                continue
            if pts.ndim != 2 or pts.shape[0] < 3:
                continue
            cand_normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            cand_norm = float(np.linalg.norm(cand_normal))
            if cand_norm <= 1e-12:
                continue
            cand_normal /= cand_norm
            if abs(float(np.dot(cand_normal, normal))) < 0.985:
                continue
            cand_center = np.mean(pts, axis=0)
            if abs(float(np.dot(normal, cand_center)) - plane_d) > plane_tol:
                continue
            coplanar_cells.add(candidate_id)
            for index in range(ids.GetNumberOfIds()):
                point_to_cells.setdefault(int(ids.GetId(index)), []).append(candidate_id)
        if cell_id not in coplanar_cells:
            smooth_component = Kraken3DInspector._smooth_component_for_cell(data, cell_id)
            if smooth_component:
                try:
                    point_ids: set[int] = set()
                    for candidate_id in smooth_component:
                        ids = data.GetCell(candidate_id).GetPointIds()
                        for index in range(ids.GetNumberOfIds()):
                            point_ids.add(int(ids.GetId(index)))
                    points = np.asarray([data.GetPoint(point_id) for point_id in point_ids], dtype=float)
                    center = 0.5 * (np.min(points, axis=0) + np.max(points, axis=0))
                    return center, Kraken3DInspector._outline_for_cells(data, smooth_component, feature_edges=False), normal.copy()
                except Exception:
                    pass
            return seed_center, Kraken3DInspector._outline_for_cells(data, {cell_id}, feature_edges=False), normal.copy()
        component: set[int] = set()
        queue = [cell_id]
        while queue:
            candidate_id = queue.pop()
            if candidate_id in component:
                continue
            component.add(candidate_id)
            try:
                ids = data.GetCell(candidate_id).GetPointIds()
                for index in range(ids.GetNumberOfIds()):
                    for neighbor in point_to_cells.get(int(ids.GetId(index)), []):
                        if neighbor not in component:
                            queue.append(neighbor)
            except Exception:
                continue
        point_ids: set[int] = set()
        for candidate_id in component:
            try:
                ids = data.GetCell(candidate_id).GetPointIds()
                for index in range(ids.GetNumberOfIds()):
                    point_ids.add(int(ids.GetId(index)))
            except Exception:
                continue
        if len(component) <= 2:
            smooth_component = Kraken3DInspector._smooth_component_for_cell(data, cell_id)
            if len(smooth_component) > len(component):
                component = smooth_component
                point_ids = set()
                for candidate_id in component:
                    try:
                        ids = data.GetCell(candidate_id).GetPointIds()
                        for index in range(ids.GetNumberOfIds()):
                            point_ids.add(int(ids.GetId(index)))
                    except Exception:
                        continue
        if not point_ids:
            return seed_center, Kraken3DInspector._outline_for_cells(data, component, feature_edges=False), normal.copy()
        points = np.asarray([data.GetPoint(point_id) for point_id in point_ids], dtype=float)
        center = 0.5 * (np.min(points, axis=0) + np.max(points, axis=0))
        return center, Kraken3DInspector._outline_for_cells(data, component, feature_edges=False), normal.copy()

    def _picked_feature_info_cached(
        self,
        actor,
        picker,
        *,
        actor_key: str | None = None,
        cell_id: int | None = None,
    ) -> tuple[np.ndarray, object | None, np.ndarray | None] | None:
        if actor is None or picker is None:
            return None
        if actor_key is None:
            actor_key = self._actor_key(actor)
        if actor_key is None:
            return self._picked_feature_info(actor, picker)
        if cell_id is None:
            try:
                cell_id = int(picker.GetCellId())
            except Exception:
                cell_id = -1
        if int(cell_id) < 0:
            return None
        cache_key = (str(actor_key), int(cell_id))
        if cache_key in self._step_feature_cache:
            return self._step_feature_cache[cache_key]
        if len(self._step_feature_cache) > 2048:
            self._step_feature_cache.clear()
        feature = self._picked_feature_info(actor, picker)
        self._step_feature_cache[cache_key] = feature
        return feature

    @staticmethod
    def _picked_feature_center(actor, picker) -> np.ndarray | None:
        feature = Kraken3DInspector._picked_feature_info(actor, picker)
        return feature[0] if feature is not None else None

    def _remember_selected_step_feature(self, label: str, feature, *, surface_center_world=None, face_id: str = "") -> bool:
        selection = self.editor._open3d_step_state_service().step_feature_selection(
            label,
            feature,
            surface_center_world=surface_center_world,
            face_id=face_id,
        )
        if selection is None:
            return False
        self._selected_step_feature = selection
        self._selected_step_feature_label = selection.label
        self._selected_step_feature_center_world = selection.pick_point_world
        self._selected_step_feature_surface_center_world = selection.surface_center_world
        self._selected_step_feature_normal_world = selection.normal_world
        return True

    @staticmethod
    def _mesh_round_lens_axis(data) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        if data is None:
            return None
        try:
            points = np.asarray(getattr(data, "points", None), dtype=float)
        except Exception:
            try:
                points = np.asarray([data.GetPoint(index) for index in range(int(data.GetNumberOfPoints()))], dtype=float)
            except Exception:
                return None
        if points.ndim != 2 or points.shape[0] < 24 or points.shape[0] > 120000 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            return None
        center = np.mean(points[:, :3], axis=0)
        centered = points[:, :3] - center
        try:
            _u, singular, vh = np.linalg.svd(centered, full_matrices=False)
        except Exception:
            return None
        if singular.size < 3 or vh.shape != (3, 3):
            return None
        major = float(max(singular[0], 1e-12))
        mid = float(max(singular[1], 1e-12))
        minor = float(max(singular[2], 1e-12))
        if major / mid > 1.75 or minor / mid > 0.78:
            return None
        axis = np.asarray(vh[2], dtype=float)
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12 or not np.isfinite(axis_norm):
            return None
        axis = axis / axis_norm
        projections = centered @ axis
        if not np.all(np.isfinite(projections)):
            return None
        thickness = float(np.max(projections) - np.min(projections))
        radial = centered - np.outer(projections, axis)
        radial_norm = np.linalg.norm(radial, axis=1)
        diameter = 2.0 * float(np.percentile(radial_norm, 95))
        if diameter <= 1e-9 or thickness <= 1e-9 or thickness / diameter > 0.85:
            return None
        return center, axis, points[:, :3]

    @staticmethod
    def _lens_rim_axis_loose(data) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """Permissive rim-axis detector for promoted-STEP lens bodies.

        The strict `_mesh_round_lens_axis` is tuned for thin auto-
        revolved BBB drums and rejects anything that doesn't read as a
        thin disc -- full spheres (ball-lens body STL, minor/mid==1),
        thick lens bodies (DCV with edge thickness near radius, where
        thickness/diameter exceeds 0.85), and so on. The rim-circle
        path needs to accept those: a sphere's rim is just a great
        circle perpendicular to any axis, and a thick rotationally
        symmetric body still has a well-defined widest cross-section.
        Only `major/mid > 1.75` is retained, to keep rejecting clearly
        elongated rods. The downstream `std/mean > 0.045` circularity
        check in `_lens_rim_circle_polyline` still rejects rectangular
        cross-sections (plano-cyl plate), so this fallback never emits
        a rim circle for a square body.
        """
        if data is None:
            return None
        try:
            points = np.asarray(getattr(data, "points", None), dtype=float)
        except Exception:
            try:
                points = np.asarray(
                    [data.GetPoint(index) for index in range(int(data.GetNumberOfPoints()))],
                    dtype=float,
                )
            except Exception:
                return None
        if (
            points.ndim != 2
            or points.shape[0] < 24
            or points.shape[0] > 120000
            or points.shape[1] < 3
            or not np.all(np.isfinite(points[:, :3]))
        ):
            return None
        center = np.mean(points[:, :3], axis=0)
        centered = points[:, :3] - center
        try:
            _u, singular, vh = np.linalg.svd(centered, full_matrices=False)
        except Exception:
            return None
        if singular.size < 3 or vh.shape != (3, 3):
            return None
        major = float(max(singular[0], 1e-12))
        mid = float(max(singular[1], 1e-12))
        if major / mid > 1.75:
            return None
        axis = np.asarray(vh[2], dtype=float)
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12 or not np.isfinite(axis_norm):
            return None
        axis = axis / axis_norm
        return center, axis, points[:, :3]

    @staticmethod
    def _round_lens_feature_for_cell(data, seed_cell_id: int):
        axis_info = Kraken3DInspector._mesh_round_lens_axis(data)
        if axis_info is None:
            return None
        object_center, axis, _points = axis_info
        try:
            seed_cell_id = int(seed_cell_id)
            cell_count = int(data.GetNumberOfCells())
            seed_cell = data.GetCell(seed_cell_id)
            seed_ids = seed_cell.GetPointIds()
            seed_points = np.asarray(
                [data.GetPoint(seed_ids.GetId(index)) for index in range(seed_ids.GetNumberOfIds())],
                dtype=float,
            )
        except Exception:
            return None
        if seed_points.ndim != 2 or seed_points.shape[0] < 3:
            return None
        seed_normal = np.cross(seed_points[1] - seed_points[0], seed_points[2] - seed_points[0])
        seed_norm = float(np.linalg.norm(seed_normal))
        if seed_norm <= 1e-12 or not np.isfinite(seed_norm):
            return None
        seed_normal = seed_normal / seed_norm
        normal_dot = float(np.dot(seed_normal, axis))
        if abs(normal_dot) < 0.18:
            return None
        face_normal = axis if normal_dot >= 0.0 else -axis
        cell_normals: dict[int, np.ndarray] = {}
        cell_point_ids: dict[int, tuple[int, ...]] = {}
        point_to_cells: dict[int, list[int]] = {}
        for candidate_id in range(cell_count):
            try:
                cell = data.GetCell(candidate_id)
                ids = cell.GetPointIds()
                point_ids = tuple(int(ids.GetId(index)) for index in range(ids.GetNumberOfIds()))
                pts = np.asarray([data.GetPoint(point_id) for point_id in point_ids], dtype=float)
            except Exception:
                continue
            if pts.ndim != 2 or pts.shape[0] < 3:
                continue
            candidate_normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            candidate_norm = float(np.linalg.norm(candidate_normal))
            if candidate_norm <= 1e-12 or not np.isfinite(candidate_norm):
                continue
            candidate_normal = candidate_normal / candidate_norm
            if float(np.dot(candidate_normal, face_normal)) < 0.16:
                continue
            candidate_center = np.mean(pts, axis=0)
            if float(np.dot(candidate_center - object_center, face_normal)) < -1e-6:
                continue
            cell_normals[candidate_id] = candidate_normal
            cell_point_ids[candidate_id] = point_ids
            for point_id in point_ids:
                point_to_cells.setdefault(int(point_id), []).append(candidate_id)
        if seed_cell_id not in cell_normals:
            return None
        component: set[int] = set()
        queue = [seed_cell_id]
        while queue:
            candidate_id = queue.pop()
            if candidate_id in component or candidate_id not in cell_normals:
                continue
            component.add(candidate_id)
            for point_id in cell_point_ids.get(candidate_id, ()):
                for neighbor_id in point_to_cells.get(int(point_id), []):
                    if neighbor_id not in component and neighbor_id in cell_normals:
                        queue.append(neighbor_id)
        if len(component) < 6:
            return None
        point_ids: set[int] = set()
        for candidate_id in component:
            point_ids.update(cell_point_ids.get(candidate_id, ()))
        if len(point_ids) < 8:
            return None
        component_points = np.asarray([data.GetPoint(point_id) for point_id in point_ids], dtype=float)
        if component_points.ndim != 2 or component_points.shape[0] < 8:
            return None
        axial = (component_points[:, :3] - object_center.reshape(1, 3)) @ face_normal
        radial_vectors = component_points[:, :3] - (object_center.reshape(1, 3) + np.outer(axial, face_normal))
        radial = np.linalg.norm(radial_vectors, axis=1)
        radial_span = float(np.max(radial) - np.min(radial)) if radial.size else 0.0
        near_axis_limit = float(np.min(radial)) + max(radial_span * 0.08, 1e-4)
        near_axis = axial[radial <= near_axis_limit]
        axial_center = float(np.mean(near_axis)) if near_axis.size else float(np.mean(axial))
        surface_center = object_center + face_normal * axial_center
        outline = Kraken3DInspector._planar_outline_from_points(component_points[:, :3], normal_world=face_normal)
        if outline is None:
            outline = Kraken3DInspector._outline_for_cells(data, component, feature_edges=False)
        return surface_center, outline, face_normal.copy()

    @staticmethod
    def _outline_for_cells(data, cell_ids: set[int], *, feature_edges: bool = True):
        if pv is None or data is None or not cell_ids:
            return None
        try:
            selected = pv.wrap(data).extract_cells(sorted(int(cell_id) for cell_id in cell_ids))
            surface = selected.extract_surface(algorithm="dataset_surface").copy(deep=True)
            outline = surface.extract_feature_edges(
                feature_angle=12,
                boundary_edges=True,
                feature_edges=bool(feature_edges),
                manifold_edges=False,
            )
            if int(getattr(outline, "n_points", 0)) <= 0:
                outline = surface.extract_all_edges()
            if int(getattr(outline, "n_points", 0)) > 0:
                return outline.copy(deep=True)
        except Exception:
            return None
        return None

    @staticmethod
    def _smooth_component_for_cell(data, seed_cell_id: int, *, max_neighbor_angle_deg: float = 35.0) -> set[int]:
        if data is None:
            return set()
        try:
            seed_cell_id = int(seed_cell_id)
            cell_count = int(data.GetNumberOfCells())
        except Exception:
            return set()
        if seed_cell_id < 0 or seed_cell_id >= cell_count:
            return set()
        cell_normals: dict[int, np.ndarray] = {}
        cell_point_ids: dict[int, tuple[int, ...]] = {}
        point_to_cells: dict[int, list[int]] = {}
        for candidate_id in range(cell_count):
            try:
                cell = data.GetCell(candidate_id)
                ids = cell.GetPointIds()
                point_ids = tuple(int(ids.GetId(index)) for index in range(ids.GetNumberOfIds()))
                pts = np.asarray([data.GetPoint(point_id) for point_id in point_ids], dtype=float)
            except Exception:
                continue
            if pts.ndim != 2 or pts.shape[0] < 3:
                continue
            normal = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            norm = float(np.linalg.norm(normal))
            if not np.isfinite(norm) or norm <= 1e-12:
                continue
            normal = np.asarray(normal / norm, dtype=float)
            cell_normals[candidate_id] = normal
            cell_point_ids[candidate_id] = point_ids
            for point_id in point_ids:
                point_to_cells.setdefault(int(point_id), []).append(candidate_id)
        seed_normal = cell_normals.get(seed_cell_id)
        if seed_normal is None:
            return set()
        neighbor_cos = float(np.cos(np.deg2rad(max(float(max_neighbor_angle_deg), 1.0))))
        seed_cos = float(np.cos(np.deg2rad(72.0)))
        component: set[int] = set()
        queue = [seed_cell_id]
        while queue:
            candidate_id = queue.pop()
            if candidate_id in component:
                continue
            candidate_normal = cell_normals.get(candidate_id)
            if candidate_normal is None:
                continue
            if abs(float(np.dot(candidate_normal, seed_normal))) < seed_cos:
                continue
            component.add(candidate_id)
            for point_id in cell_point_ids.get(candidate_id, ()):
                for neighbor_id in point_to_cells.get(int(point_id), []):
                    if neighbor_id in component:
                        continue
                    neighbor_normal = cell_normals.get(neighbor_id)
                    if neighbor_normal is None:
                        continue
                    if abs(float(np.dot(neighbor_normal, candidate_normal))) >= neighbor_cos:
                        queue.append(neighbor_id)
        return component

    @staticmethod
    def _planar_outline_from_points(points, normal_world=None):
        if pv is None:
            _load_3d_backends()
        if pv is None:
            return None
        try:
            point_array = np.asarray(points, dtype=float).reshape((-1, 3))
        except Exception:
            return None
        if point_array.ndim != 2 or point_array.shape[0] < 3 or not np.all(np.isfinite(point_array[:, :3])):
            return None
        try:
            normal = np.asarray(normal_world, dtype=float).reshape(-1)[:3]
        except Exception:
            normal = np.asarray([], dtype=float)
        if normal.size < 3 or not np.all(np.isfinite(normal[:3])) or float(np.linalg.norm(normal[:3])) <= 1e-12:
            centered = point_array[:, :3] - np.mean(point_array[:, :3], axis=0)
            try:
                _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
                normal = np.asarray(vh[-1], dtype=float)
            except Exception:
                normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
        norm = float(np.linalg.norm(normal[:3]))
        if norm <= 1e-12 or not np.isfinite(norm):
            return None
        normal = np.asarray(normal[:3] / norm, dtype=float)
        ref = np.asarray((0.0, 0.0, 1.0), dtype=float) if abs(float(normal[2])) < 0.9 else np.asarray((0.0, 1.0, 0.0), dtype=float)
        u_axis = np.cross(normal, ref)
        u_norm = float(np.linalg.norm(u_axis))
        if u_norm <= 1e-12:
            ref = np.asarray((1.0, 0.0, 0.0), dtype=float)
            u_axis = np.cross(normal, ref)
            u_norm = float(np.linalg.norm(u_axis))
        if u_norm <= 1e-12:
            return None
        u_axis = u_axis / u_norm
        v_axis = np.cross(normal, u_axis)
        v_norm = float(np.linalg.norm(v_axis))
        if v_norm <= 1e-12:
            return None
        v_axis = v_axis / v_norm
        origin = np.mean(point_array[:, :3], axis=0)
        local = np.column_stack(((point_array[:, :3] - origin) @ u_axis, (point_array[:, :3] - origin) @ v_axis))
        try:
            local = np.unique(np.round(local, decimals=9), axis=0)
        except Exception:
            pass
        if local.shape[0] < 3:
            return None
        hull = convex_hull_2d(local)
        if hull.ndim != 2 or hull.shape[0] < 3 or hull.shape[1] < 2:
            return None
        if hull.shape[0] > 3 and float(np.linalg.norm(hull[0, :2] - hull[-1, :2])) <= 1e-8:
            hull = hull[:-1, :]
        hull_world = origin + hull[:, 0:1] * u_axis.reshape(1, 3) + hull[:, 1:2] * v_axis.reshape(1, 3)
        if not np.all(np.isfinite(hull_world[:, :3])):
            return None
        lines: list[int] = []
        for index in range(int(hull_world.shape[0])):
            lines.extend((2, int(index), int((index + 1) % hull_world.shape[0])))
        try:
            return pv.PolyData(np.asarray(hull_world[:, :3], dtype=float), lines=np.asarray(lines, dtype=np.int64))
        except Exception:
            return None

    @staticmethod
    def _planar_outline_from_triangles(triangles, normal_world=None):
        try:
            triangle_array = np.asarray(triangles, dtype=float)
        except Exception:
            return None
        if triangle_array.ndim != 3 or triangle_array.shape[1:] != (3, 3) or triangle_array.shape[0] <= 0:
            return None
        return Kraken3DInspector._planar_outline_from_points(triangle_array.reshape((-1, 3)), normal_world=normal_world)

    @staticmethod
    def _hover_overlay_for_feature(center, outline_mesh):
        if pv is None:
            return outline_mesh
        parts = []
        try:
            if outline_mesh is not None and int(getattr(outline_mesh, "n_points", 0)) > 0:
                outline = pv.wrap(outline_mesh).copy(deep=True)
                parts.append(outline)
        except Exception:
            pass
        if not parts:
            try:
                center = np.asarray(center, dtype=float)
            except Exception:
                center = np.asarray([], dtype=float)
            if center.size >= 3 and np.all(np.isfinite(center[:3])):
                parts.append(
                    pv.Sphere(
                        radius=1.5,
                        center=(float(center[0]), float(center[1]), float(center[2])),
                        theta_resolution=16,
                        phi_resolution=8,
                    )
                )
        if not parts:
            return outline_mesh
        merged = parts[0]
        for part in parts[1:]:
            try:
                merged = merged.merge(part)
            except Exception:
                pass
        return merged

    def _hover_overlay_for_row_face(self, row_index: int, face: dict[str, object] | None):
        if pv is None or not isinstance(face, dict):
            return None
        item = self.editor._file_backed_stl_row_at(int(row_index))
        if item is None:
            return None
        row, path = item
        try:
            _center, scene_radius = self._scene_bounds()
        except Exception:
            scene_radius = 1.0
        world_triangles = np.empty((0, 3, 3), dtype=float)
        if not self._row_face_metadata_uses_saved_mesh(row):
            world_triangles = self._runtime_world_face_triangles_for_record(
                self.__dict__.get("_current_system"),
                int(row_index),
                face,
                scene_radius=float(scene_radius),
            )
        if world_triangles.size == 0:
            try:
                triangles = self._cad_scene_cache.triangle_array(path, _read_stl_triangle_vertices).triangles
            except Exception:
                return None
            if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
                return None
            world_triangles = self._world_face_triangles_for_record(
                row,
                triangles,
                face,
                z_station=self.editor._stl_row_z_station(int(row_index)),
                transform=self._runtime_transform_for_row(self.__dict__.get("_current_system"), int(row_index)),
                scene_radius=float(scene_radius),
            )
        if world_triangles.ndim != 3 or world_triangles.shape[1:] != (3, 3) or world_triangles.shape[0] == 0:
            return None
        face_mesh = self._polydata_from_triangles(world_triangles)
        if face_mesh is None:
            return None
        outline = self._planar_outline_from_triangles(world_triangles, normal_world=None)
        if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
            outline = self._display_feature_edges(face_mesh, feature_angle=8.0)
        if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
            try:
                outline = face_mesh.extract_all_edges()
            except Exception:
                outline = None
        try:
            center = np.mean(np.asarray(world_triangles, dtype=float).reshape((-1, 3)), axis=0)
        except Exception:
            center = face.get("centroid_world", face.get("centroid", ()))
        return self._hover_overlay_for_feature(center, outline)

    def _hover_overlay_for_step_face(self, label: str, face: dict[str, object] | None):
        if pv is None or not isinstance(face, dict):
            return None
        if not open3d_trace_enabled():
            return self._hover_overlay_for_step_face_impl(label, face)
        from KrakenOS.UI.services.open3d_timing import open3d_trace_span as _span
        face_id = str(face.get("face_id", "") or "")[:20]
        with _span("hover_overlay_for_step_face", label=str(label), face_id=face_id):
            return self._hover_overlay_for_step_face_impl(label, face)

    def _hover_overlay_for_step_face_impl(self, label: str, face: dict[str, object] | None):
        if pv is None or not isinstance(face, dict):
            return None
        try:
            display_mesh = self.editor._transformed_imported_step_mesh_for_label(str(label).strip().lower())
            face_indices = face_indices_for_record(display_mesh, face)
            if face_indices:
                outline = None
                face_mesh = None
                selected_triangles = triangles_for_face_indices(display_mesh, face_indices)
                if selected_triangles.size:
                    try:
                        center_for_offset = np.asarray(face.get("centroid_world", face.get("centroid", ())), dtype=float).reshape(-1)[:3]
                        camera = self._renderer.GetActiveCamera() if self._renderer is not None else None
                        camera_position = np.asarray(camera.GetPosition(), dtype=float).reshape(-1)[:3] if camera is not None else np.asarray([])
                        view_direction = camera_position[:3] - center_for_offset[:3]
                        view_norm = float(np.linalg.norm(view_direction))
                        if (
                            center_for_offset.size >= 3
                            and camera_position.size >= 3
                            and np.all(np.isfinite(center_for_offset[:3]))
                            and np.all(np.isfinite(camera_position[:3]))
                            and np.isfinite(view_norm)
                            and view_norm > 1.0e-12
                        ):
                            try:
                                _scene_center, scene_radius = self._scene_bounds()
                            except Exception:
                                scene_radius = 1.0
                            offset = max(float(scene_radius) * 1.0e-4, 1.0e-3)
                            selected_triangles = selected_triangles + (view_direction[:3] / view_norm).reshape((1, 1, 3)) * offset
                    except Exception:
                        pass
                    face_mesh = self._polydata_from_triangles(selected_triangles)
                if str(face.get("assignment_source", "") or "").startswith("step_analytic_axisymmetric_group"):
                    if selected_triangles.size:
                        outline = self._planar_outline_from_triangles(
                            selected_triangles,
                            normal_world=face.get("normal_world", face.get("normal")),
                        )
                if outline is None or int(getattr(outline, "n_points", 0)) <= 0:
                    outline = face_outline_from_face_indices(display_mesh, face_indices)
                overlay = face_mesh
                if outline is not None and int(getattr(outline, "n_points", 0)) > 0:
                    if overlay is not None and int(getattr(overlay, "n_points", 0)) > 0:
                        try:
                            overlay = overlay.merge(outline)
                        except Exception:
                            pass
                    else:
                        overlay = outline
                if overlay is not None and int(getattr(overlay, "n_points", 0)) > 0:
                    center = face.get("centroid_world", face.get("centroid", ()))
                    return self._hover_overlay_for_feature(center, overlay)
        except Exception:
            pass
        try:
            metadata = self.editor._step_overlay_face_metadata(str(label).strip().lower())
            source_stl = Path(str(metadata.get("source_stl", "") or "")).expanduser()
            triangles = self._cad_scene_cache.triangle_array(source_stl, _read_stl_triangle_vertices).triangles
        except Exception:
            return None
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
            return None
        selected_triangles = self._cad_scene_cache.face_triangles(source_stl, face, _read_stl_triangle_vertices)
        if selected_triangles.ndim != 3 or selected_triangles.shape[1:] != (3, 3) or selected_triangles.shape[0] == 0:
            return None

        def build_outline(cached_triangles: np.ndarray):
            face_mesh = self._polydata_from_triangles(cached_triangles)
            if face_mesh is None:
                return None
            outline_mesh = self._planar_outline_from_triangles(
                cached_triangles,
                normal_world=face.get("normal_world", face.get("normal")),
            )
            if outline_mesh is None or int(getattr(outline_mesh, "n_points", 0)) <= 0:
                outline_mesh = self._display_feature_edges(face_mesh, feature_angle=8.0)
            if outline_mesh is None or int(getattr(outline_mesh, "n_points", 0)) <= 0:
                try:
                    outline_mesh = face_mesh.extract_all_edges()
                except Exception:
                    outline_mesh = None
            return outline_mesh

        outline = self._cad_scene_cache.face_outline(source_stl, face, _read_stl_triangle_vertices, build_outline)
        center = face.get("centroid_world", face.get("centroid", ()))
        return self._hover_overlay_for_feature(center, outline)

    def _feature_from_face_ray_pick(self, pick: FaceRayPick, outline_mesh=None):
        return (
            np.asarray(pick.point_world, dtype=float).reshape(3),
            outline_mesh,
            np.asarray(pick.normal_world, dtype=float).reshape(3),
        )

    @staticmethod
    def _surface_center_from_face_ray_pick(pick: FaceRayPick) -> np.ndarray:
        face = dict(getattr(pick, "face", {}) or {})
        for key in ("centroid_world", "centroid"):
            try:
                center = np.asarray(face.get(key), dtype=float).reshape(-1)[:3]
            except Exception:
                center = np.asarray([], dtype=float)
            if center.size >= 3 and np.all(np.isfinite(center[:3])):
                return center[:3]
        return np.asarray(pick.point_world, dtype=float).reshape(3)

    @staticmethod
    def _runtime_world_face_records_for_pick(row, metadata: dict[str, object], transform) -> list[dict[str, object]]:
        faces: list[dict[str, object]] = []
        try:
            matrix = np.asarray(transform, dtype=float).reshape(4, 4)
        except Exception:
            return faces
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = normalize_optical_solid_face_record(face)
            normal = np.asarray(_unit_vector_tuple(record.get("normal", (0.0, 0.0, 1.0))), dtype=float)
            if bool(record.get("flip_normal", False)):
                normal = -normal
            transformed = Kraken3DInspector._transform_local_point_and_normal(
                matrix,
                record.get("centroid", (0.0, 0.0, 0.0)),
                normal,
            )
            if transformed is None:
                continue
            centroid_world, normal_world = transformed
            record["centroid_world"] = tuple(float(value) for value in centroid_world[:3])
            record["normal_world"] = tuple(float(value) for value in normal_world[:3])
            faces.append(record)
        return faces

    def _step_face_ray_pick_for_display_xy(self, label: str, display_xy) -> FaceRayPick | None:
        ray = self._display_pick_ray(display_xy)
        if ray is None:
            return None
        origin, direction = ray
        try:
            metadata = self.editor._step_overlay_face_metadata(str(label).strip().lower())
        except Exception:
            return None
        faces = [face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)]
        pick = face_pick_from_display_mesh(self.editor, label, faces, origin, direction)
        if pick is not None:
            return pick
        try:
            source_stl = Path(str(metadata.get("source_stl", "") or "")).expanduser()
            triangles = self._cad_scene_cache.triangle_array(source_stl, _read_stl_triangle_vertices).triangles
        except Exception:
            return None
        return pick_face_from_ray(
            faces,
            triangles,
            origin,
            direction,
            all_points=triangles.reshape((-1, 3)) if triangles.ndim == 3 else None,
            prefer_internal=True,
        )

    def _step_face_ray_pick_is_tessellation_patch(self, label: str, pick: FaceRayPick | None) -> bool:
        if pick is None:
            return False
        try:
            metadata = self.editor._step_overlay_face_metadata(str(label).strip().lower())
            face_count = len([face for face in list(metadata.get("faces", []) or []) if isinstance(face, dict)])
        except Exception:
            face_count = 0
        if face_count < 40:
            return False
        try:
            triangle_count = len(tuple(pick.face.get("triangle_indices", pick.face.get("cell_indices", ())) or ()))
        except Exception:
            triangle_count = 0
        return triangle_count <= 4

    def _step_label_is_round_lens_like(self, label: str) -> bool:
        label = str(label or "").strip().lower()
        if not label:
            return False
        for actor_key in list(self._step_actor_map.get(label, []) or []):
            actor = self._actor_by_key.get(str(actor_key))
            if actor is not None and bool(getattr(actor, "_kraken_round_lens_like_step_body", False)):
                return True
        return False

    def _step_feature_pick_for_display_xy(
        self,
        label: str,
        display_xy,
        *,
        actor=None,
        actor_key: str | None = None,
        cell_id: int = -1,
    ) -> dict[str, object] | None:
        # A hidden element is inert to face hover/pick: VTK already skips its
        # invisible actors, but this display-mesh / camera-ray pick works from
        # cached face geometry regardless of visibility, so gate it here (the
        # single wrapper every hover/pick/axis-snap path routes through) to stop
        # a hidden STEP popping its gold hover outline + face tooltip (bug 0029).
        if self.is_step_label_hidden(label):
            return None
        return step_feature_pick_for_display_xy(
            self,
            label,
            display_xy,
            actor=actor,
            actor_key=actor_key,
            cell_id=int(cell_id),
        )

    def _coarse_step_face_ray_pick_for_display_xy(self, label: str, display_xy) -> FaceRayPick | None:
        """Return a face pick unless STEP->STL degraded it to a tiny facet.

        Optical lenses often arrive as curved BREP faces but are displayed from
        an STL tessellation. The planar metadata then contains many tiny facets.
        Axis-alignment selection should fall back to a smooth connected display
        region for those cases instead of highlighting one little triangle.
        """
        pick = self._step_face_ray_pick_for_display_xy(label, display_xy)
        if self._step_label_is_round_lens_like(label):
            return None if self._step_face_ray_pick_is_tessellation_patch(label, pick) else pick
        if self._step_face_ray_pick_is_tessellation_patch(label, pick):
            return None
        return pick

    def _row_face_ray_pick_for_display_xy(self, row_index: int, display_xy) -> FaceRayPick | None:
        ray = self._display_pick_ray(display_xy)
        if ray is None:
            return None
        origin, direction = ray
        try:
            row, path, metadata = self.editor._optical_solid_face_metadata_for_row(int(row_index))
            triangles = self._cad_scene_cache.triangle_array(path, _read_stl_triangle_vertices).triangles
        except Exception:
            return None
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3) or triangles.shape[0] == 0:
            return None
        system = self.__dict__.get("_current_system")
        transform = self._runtime_transform_for_row(system, int(row_index))
        runtime_triangles = self._surface_cell_triangles(
            _layout_editor_class()._runtime_trace_surface_mesh(system, int(row_index))
        )
        max_face_triangle_index = -1
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            for value in list(face.get("triangle_indices", face.get("cell_indices", [])) or []):
                try:
                    max_face_triangle_index = max(max_face_triangle_index, int(value))
                except Exception:
                    pass
        if (
            not self._row_face_metadata_uses_saved_mesh(row)
            and runtime_triangles.ndim == 3
            and runtime_triangles.shape[1:] == (3, 3)
            and runtime_triangles.shape[0] > max_face_triangle_index
            and runtime_triangles.shape[0] > 0
        ):
            world_triangles = runtime_triangles
        else:
            world_triangles = self._world_triangles_for_row_pick(
                row,
                triangles,
                z_station=self.editor._stl_row_z_station(int(row_index)),
                transform=transform,
            )
        if world_triangles.size == 0:
            return None
        if transform is not None:
            faces = self._runtime_world_face_records_for_pick(row, metadata, transform)
        else:
            faces = self.editor._optical_solid_face_records_for_temp_row(row, int(row_index), metadata)
        return pick_face_from_ray(
            faces,
            world_triangles,
            origin,
            direction,
            all_points=world_triangles.reshape((-1, 3)),
            prefer_internal=not self._row_face_metadata_uses_saved_mesh(row),
        )

    @staticmethod
    def _set_step_actor_selected(actor, selected: bool) -> None:
        if actor is None:
            return
        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None
        if prop is None:
            return
        base = getattr(actor, "_kraken_step_select_style", None)
        if not isinstance(base, dict):
            try:
                base = {
                    "edge_visibility": int(prop.GetEdgeVisibility()),
                    "edge_color": tuple(float(value) for value in prop.GetEdgeColor()),
                    "color": tuple(float(value) for value in prop.GetColor()),
                    "line_width": float(prop.GetLineWidth()),
                    "opacity": float(prop.GetOpacity()),
                    "ambient": float(prop.GetAmbient()),
                    "diffuse": float(prop.GetDiffuse()),
                }
                actor._kraken_step_select_style = base
            except Exception:
                base = {}
        if selected:
            # bugs/0051: use the app-wide "selected" idiom (pink translucent
            # body, the same as promoted rows / optical solids in
            # _set_row_actor_selected, bugs/0001-0003) instead of the old orange
            # *edge tint* (1.0, 0.48, 0.0). An imported STEP body is a dense
            # tessellation, so per-triangle edges painted a muddy wireframe that
            # filled the body -- it read as a flat orange blob with no edge
            # contrast ("why is this STEP orange, different from the rest?").
            # Suppress the triangle edges and signal selection with a
            # high-contrast pink fill + bumped opacity; the body's own glass-edge
            # rim actor (also tagged with the label) keeps the silhouette.
            try:
                prop.SetEdgeVisibility(0)
                prop.SetLineWidth(float(base.get("line_width", 1.0)))
                prop.SetColor(1.0, 0.45, 0.65)  # pink body fill
                prop.SetOpacity(min(max(float(base.get("opacity", 0.5)), 0.55) + 0.10, 1.0))
                prop.SetAmbient(max(float(base.get("ambient", 0.0)), 0.30))
                prop.SetDiffuse(max(float(base.get("diffuse", 1.0)), 0.80))
            except Exception:
                pass
            return
        try:
            prop.SetEdgeVisibility(int(base.get("edge_visibility", 0)))
            edge_color = tuple(base.get("edge_color", (0.0, 0.0, 0.0)))
            if len(edge_color) == 3:
                prop.SetEdgeColor(*edge_color)
            color = tuple(base.get("color", (1.0, 1.0, 1.0)))
            if len(color) == 3:
                prop.SetColor(*color)
            prop.SetLineWidth(float(base.get("line_width", 1.0)))
            prop.SetOpacity(float(base.get("opacity", 1.0)))
            prop.SetAmbient(float(base.get("ambient", 0.0)))
            prop.SetDiffuse(float(base.get("diffuse", 1.0)))
        except Exception:
            pass

    @staticmethod
    def _set_ray_actor_selected(actor, selected: bool) -> None:
        if actor is None:
            return
        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None
        if prop is None:
            return
        base = getattr(actor, "_kraken_ray_select_style", None)
        if not isinstance(base, dict):
            try:
                base = {
                    "color": tuple(float(value) for value in prop.GetColor()),
                    "line_width": float(prop.GetLineWidth()),
                    "opacity": float(prop.GetOpacity()),
                    "ambient": float(prop.GetAmbient()),
                    "diffuse": float(prop.GetDiffuse()),
                }
                actor._kraken_ray_select_style = base
            except Exception:
                base = {}
        if selected:
            try:
                prop.SetColor(1.0, 0.35, 0.0)
                prop.SetLineWidth(max(float(base.get("line_width", 1.2)), 4.0))
                prop.SetOpacity(1.0)
                prop.SetAmbient(max(float(base.get("ambient", 0.0)), 0.35))
            except Exception:
                pass
            return
        try:
            color = tuple(base.get("color", (0.2, 1.0, 0.2)))
            if len(color) == 3:
                prop.SetColor(*color)
            prop.SetLineWidth(float(base.get("line_width", 1.2)))
            prop.SetOpacity(float(base.get("opacity", 0.9)))
            prop.SetAmbient(float(base.get("ambient", 0.0)))
            prop.SetDiffuse(float(base.get("diffuse", 1.0)))
        except Exception:
            pass

    def start_stl_placement(self, row_index: int, *, refresh: bool = False) -> None:
        try:
            row_index = int(row_index)
        except Exception:
            self.status_var.set("Select a CAD/STL solid row before using placement controls.")
            return
        if self.editor._file_backed_stl_row_at(row_index) is None:
            self.status_var.set("Selected row is not a file-backed optical CAD/STL solid.")
            return
        self._stl_placement_row_index = row_index
        self.editor._select_table_row(row_index)
        self.highlight_row(row_index)
        if refresh:
            self.refresh_from_editor()
        self.show_stl_placement_handler(row_index)
        self.status_var.set(f"CAD/STL placement mode: row {row_index}. Use the placement handler, then Done -> 2D or close this view.")

    def _active_stl_placement_row_index(self) -> int | None:
        if self._stl_placement_row_index is not None:
            if self.editor._file_backed_stl_row_at(self._stl_placement_row_index) is not None:
                return int(self._stl_placement_row_index)
        row_index = self.editor._current_selected_row_index()
        if row_index is not None and self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            self._stl_placement_row_index = int(row_index)
            return int(row_index)
        self.status_var.set("Select an optical CAD/STL row first.")
        return None

    def _refresh_after_stl_pose_change(self, row_index: int, action: str) -> None:
        self._stl_placement_row_index = int(row_index)
        self._stl_placement_dirty = True
        try:
            self.refresh_from_editor()
        except Exception as exc:
            self.status_var.set(f"STL pose updated; 3D refresh failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"3D CAD/STL placement refresh failed: {exc}")
            return
        self.highlight_row(row_index)
        self._update_stl_placement_handler_state()
        self.status_var.set(f"{action} applied to CAD/STL row {row_index}. Close or Done -> 2D to update the 2D layout.")

    def fit_selected_stl_axis(self) -> None:
        row_index = self._active_stl_placement_row_index()
        if row_index is None:
            return
        axis = self.stl_axis_var.get().strip() or "+Z"
        try:
            self.editor.apply_stl_axis_fit(row_index, axis)
        except Exception as exc:
            self.status_var.set(f"STL axis fit failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"STL axis fit failed: {exc}")
            return
        self._refresh_after_stl_pose_change(row_index, f"Fit {axis} -> +Z")

    def rotate_selected_stl_pose(self, axis: str, delta_deg: float) -> None:
        row_index = self._active_stl_placement_row_index()
        if row_index is None:
            return
        try:
            self.editor.rotate_stl_row_pose(row_index, axis, delta_deg)
        except Exception as exc:
            self.status_var.set(f"STL rotation failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"STL rotation failed: {exc}")
            return
        self._refresh_after_stl_pose_change(row_index, f"Rotate {axis.upper()} {float(delta_deg):+.0f} deg")

    def center_selected_stl_xy(self) -> None:
        row_index = self._active_stl_placement_row_index()
        if row_index is None:
            return
        try:
            self.editor.center_stl_row_xy(row_index)
        except Exception as exc:
            self.status_var.set(f"STL centring failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"STL centring failed: {exc}")
            return
        self._refresh_after_stl_pose_change(row_index, "Center X/Y")

    def place_selected_stl_front_on_row(self) -> None:
        row_index = self._active_stl_placement_row_index()
        if row_index is None:
            return
        try:
            self.editor.place_stl_row_front_on_station(row_index)
        except Exception as exc:
            self.status_var.set(f"STL front placement failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"STL front placement failed: {exc}")
            return
        self._refresh_after_stl_pose_change(row_index, "Min Z On Row")

    def finish_stl_placement(self) -> None:
        if self._stl_placement_dirty:
            try:
                self.editor.refresh_plot(
                    suppress_analysis=True,
                    sampling_mode=self._active_refresh_sampling_mode(),
                )
                self._stl_placement_dirty = False
                self.editor.status_var.set("Applied CAD/STL placement to the 2D layout.")
            except Exception as exc:
                self.editor.status_var.set(f"CAD/STL placement saved; 2D refresh failed: {_short_error_message(exc)}")
                self.editor.append_debug(f"CAD/STL placement 2D refresh failed: {exc}")
        self._on_close()

    def _on_close(self) -> None:
        dirty = bool(getattr(self, "_stl_placement_dirty", False))
        refresh_sampling_mode = self._active_refresh_sampling_mode()
        self._stl_placement_dirty = False
        self.editor._three_d_inspector = None
        self._cancel_live_refresh()
        self._cancel_step_carry_hold_timer()
        self._cancel_row_carry_hold_timer()
        self._clear_galvo_scan_animation(cancel_timer=True, render=False)
        self._close_step_rotation_handler()
        self._close_stl_placement_handler()
        try:
            self.editor._cad_axis_pick_any = False
            self.editor._cad_axis_pick_label = None
            self.editor._cad_led_object_edge_pick = False
        except Exception:
            pass
        view = self.__dict__.get("_selection_view")
        if view is not None:
            try:
                view.detach()
            except Exception:
                pass
        self._destroy_vtk_render_window()
        try:
            self.destroy()
        except Exception:
            pass
        if dirty:
            def refresh_2d_after_close() -> None:
                try:
                    self.editor.refresh_plot(
                        suppress_analysis=True,
                        sampling_mode=refresh_sampling_mode,
                    )
                except Exception as exc:
                    self.editor.status_var.set(f"CAD/STL placement saved; 2D refresh failed: {_short_error_message(exc)}")
                    self.editor.append_debug(f"CAD/STL placement close refresh failed: {exc}")

            try:
                self.editor.after(50, refresh_2d_after_close)
                self.editor.status_var.set("3D CAD/STL placement closed; refreshing 2D layout.")
            except Exception as exc:
                self.editor.append_debug(f"CAD/STL placement close refresh failed: {exc}")

    def _destroy_vtk_render_window(self) -> None:
        try:
            if self._orientation_widget is not None:
                self._orientation_widget.EnabledOff()
        except Exception:
            pass
        try:
            if self._vtk_interactor is not None:
                self._vtk_interactor.TerminateApp()
        except Exception:
            pass
        try:
            if self._vtk_widget is not None:
                render_window = self._vtk_widget.GetRenderWindow()
                if render_window is not None:
                    render_window.Finalize()
        except Exception:
            pass
        self._orientation_widget = None
        self._vtk_interactor = None
        self._renderer = None
