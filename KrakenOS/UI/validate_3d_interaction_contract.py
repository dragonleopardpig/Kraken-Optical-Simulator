"""Validate the embedded 3D mouse-interaction contract."""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import (
    STEP_CARRY_GRID_CHOICES,
    STEP_CARRY_GRID_FREE,
    Kraken3DInspector,
    KrakenLayoutEditor,
    _dotted_axis_records_from_ray_path,
)
from KrakenOS.UI.panels.main_advanced_surface_dialog import MainAdvancedSurfaceDialog
from KrakenOS.UI.panels.main_analysis_controls import MainAnalysisToolbarPanel, MainInformationPanel
from KrakenOS.UI.panels.main_branch_gaussian_q_dialog import MainBranchGaussianQDialog
from KrakenOS.UI.panels.main_branch_throughput_report_dialog import MainBranchThroughputReportDialog
from KrakenOS.UI.panels.main_atmosphere_panel import MainAtmospherePanel
from KrakenOS.UI.panels.main_beam_splitter_dialog import MainBeamSplitterDialog
from KrakenOS.UI.panels.main_coating_material_dialog import MainCoatingMaterialDialog
from KrakenOS.UI.panels.main_context_menu import MainContextMenu
from KrakenOS.UI.panels.main_detector_aperture_report_dialog import MainDetectorApertureReportDialog
from KrakenOS.UI.panels.main_diffuse_scatter_dialog import MainDiffuseScatterDialog
from KrakenOS.UI.panels.main_error_map_dialog import MainErrorMapDialog
from KrakenOS.UI.panels.main_field_controls import MainFieldControlsPanel
from KrakenOS.UI.panels.main_lens_drawing_dialogs import MainLensDrawingDialogs
from KrakenOS.UI.panels.main_optimization_panel import MainOptimizationPanel
from KrakenOS.UI.panels.main_paraxial_analysis_dialogs import MainParaxialAnalysisDialogs
from KrakenOS.UI.panels.main_scene_element_dialogs import MainSceneElementDialogs
from KrakenOS.UI.panels.main_scene_source_manager_dialog import MainSceneSourceManagerDialog
from KrakenOS.UI.panels.main_stock_lens_importer_dialog import MainStockLensImporterDialog
from KrakenOS.UI.panels.main_source_controls import MainSourceControlsPanel
from KrakenOS.UI.panels.main_source_illumination_report_dialog import MainSourceIlluminationReportDialog
from KrakenOS.UI.panels.main_surface_settings_dialogs import MainSurfaceSettingsDialogs
from KrakenOS.UI.panels.main_surface_shape_builder_dialog import MainSurfaceShapeBuilderDialog
from KrakenOS.UI.panels.main_trace_display_controls import MainTraceDisplayControlsPanel
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
from KrakenOS.UI.saved_layout_plot import build_saved_layout_figure
from KrakenOS.UI.scene_builder import _sync_path_display_geometry_from_events
from KrakenOS.UI.scene_geometry import RayEvent3D, RayPath3D
from KrakenOS.UI.scene_projector import bounded_ray_points_for_scene_display, scene_display_center_radius
from KrakenOS.UI.services.open3d_face_pick import pick_face_from_ray
from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService
from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService
from KrakenOS.UI.widgets.tooltips import WidgetTooltip


def _scene_path_preserves_raykeeper_terminal_continuation() -> tuple[bool, str]:
    """Regression guard for prism exits that continue after the last surface event."""
    raw_points = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 10.0],
            [0.0, 3.0, 15.0],
            [0.0, -3.0, 20.0],
            [0.0, 0.0, 25.0],
            [0.0, 0.0, 55.0],
        ],
        dtype=float,
    )
    path = RayPath3D(
        ray_index=0,
        source_position=raw_points[0].copy(),
        points_world=raw_points.copy(),
        surface_ids=np.asarray([1, 1, 1, 1], dtype=int),
        events=[
            RayEvent3D(
                event_kind="surface",
                event_type=event_type,
                surface_id=1,
                point_world=raw_points[index].copy(),
                metadata={"event_source": "raykeeper"},
            )
            for index, event_type in enumerate(
                ["transmission", "reflection", "reflection", "transmission"],
                start=1,
            )
        ],
    )
    _sync_path_display_geometry_from_events(path)
    if path.points_world.shape != raw_points.shape:
        return False, f"points={path.points_world.shape}, expected={raw_points.shape}"
    if not np.allclose(path.points_world[-1], raw_points[-1], rtol=0.0, atol=1e-9):
        return False, "last raw continuation point was dropped"
    if path.surface_ids.shape != (4,):
        return False, f"surface_ids={path.surface_ids.shape}, expected=(4,)"
    if "raykeeper_terminal_continuation" not in path.display_geometry_diagnostic:
        return False, path.display_geometry_diagnostic
    return True, path.display_geometry_diagnostic


def _traced_axis_records_mark_exit_segment() -> tuple[bool, str]:
    points = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 12.0],
            [0.0, 8.0, 20.0],
            [0.0, 16.0, 18.0],
            [0.0, 18.0, 10.0],
            [0.0, 34.0, 8.0],
        ],
        dtype=float,
    )
    events = [
        RayEvent3D(event_kind="surface", event_type="refract", surface_id=1, mesh_face_id="F005"),
        RayEvent3D(event_kind="surface", event_type="reflect", surface_id=1, mesh_face_id="F004"),
        RayEvent3D(event_kind="surface", event_type="reflect", surface_id=1, mesh_face_id="F003"),
        RayEvent3D(event_kind="surface", event_type="refract", surface_id=1, mesh_face_id="F006"),
    ]
    path = RayPath3D(
        ray_index=15,
        source_position=points[0].copy(),
        points_world=points.copy(),
        surface_ids=np.asarray([1, 1, 1, 1], dtype=int),
        events=events,
        branch_path="primary",
        source_id="source:0",
    )
    records = _dotted_axis_records_from_ray_path(path, np.asarray([-10.0, 10.0, -10.0, 40.0, -5.0, 35.0]))
    exit_records = [record for record in records if str(record.get("axis_role", "") or "") == "post_surface"]
    if len(records) != 1 or len(exit_records) != 1:
        return False, f"records={records}"
    exit_record = max(exit_records, key=lambda record: int(record.get("segment_index", -1) or -1))
    midpoint = np.asarray(exit_record.get("segment_midpoint", ()), dtype=float).reshape(-1)
    axis_points = np.asarray(exit_record.get("points", ()), dtype=float)
    ok = (
        str(exit_record.get("from_mesh_face_id", "") or "") == "F006"
        and str(exit_record.get("from_event_type", "") or "") == "refract"
        and int(exit_record.get("segment_index", -1) or -1) == 5
        and midpoint.size >= 3
        and np.all(np.isfinite(midpoint[:3]))
        and axis_points.ndim == 2
        and axis_points.shape[0] == 2
        and float(np.max(np.abs(axis_points[:, :3]))) < 100.0
    )
    return ok, f"exit_record={exit_record}"


def _traced_axis_records_bound_long_escaped_tail() -> tuple[bool, str]:
    points = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 20.0],
            [12.5, -12.5, 45.0],
            [20.0, -12.5, 45.0],
            [-6.0e7, -150.0, 100.0],
        ],
        dtype=float,
    )
    events = [
        RayEvent3D(event_kind="surface", event_type="refract", surface_id=1, mesh_face_id="F005"),
        RayEvent3D(event_kind="surface", event_type="reflect", surface_id=1, mesh_face_id="F004"),
        RayEvent3D(event_kind="surface", event_type="refract", surface_id=1, mesh_face_id="F006"),
    ]
    path = RayPath3D(
        ray_index=0,
        source_position=points[0].copy(),
        points_world=points.copy(),
        surface_ids=np.asarray([1, 1, 1], dtype=int),
        events=events,
        branch_path="primary",
        source_id="source:0",
    )
    bounds = np.asarray([-30.0, 30.0, -30.0, 30.0, -10.0, 70.0], dtype=float)
    records = _dotted_axis_records_from_ray_path(path, bounds)
    if len(records) != 1:
        return False, f"records={records}"
    axis_points = np.asarray(records[0].get("points", ()), dtype=float)
    if axis_points.ndim != 2 or axis_points.shape != (2, 3):
        return False, f"axis_points={axis_points}"
    max_abs = float(np.max(np.abs(axis_points[:, :3])))
    return max_abs < 250.0, f"axis_points={axis_points.tolist()}, max_abs={max_abs:.6g}"


def main() -> int:
    bindings = inspect.getsource(Kraken3DInspector._install_pick_only_left_click_bindings)
    try:
        step_carry_drag_branch = bindings.split("elif self._step_carry_drag_state is not None:", 1)[1].split(
            "else:",
            1,
        )[0]
    except Exception:
        step_carry_drag_branch = ""
    rotation = inspect.getsource(Kraken3DInspector._rotate_camera_fixed_drag)
    camera_pan = inspect.getsource(Kraken3DInspector._pan_camera_fixed_drag)
    pick = inspect.getsource(Kraken3DInspector._on_left_button_press)
    mouse_move = inspect.getsource(Kraken3DInspector._on_mouse_move)
    handler = inspect.getsource(Kraken3DInspector.show_step_rotation_handler)
    handler_rotate = inspect.getsource(Kraken3DInspector._rotate_step_from_handler)
    ensure_step_handles = inspect.getsource(Kraken3DInspector._ensure_step_rotation_handles_for_label)
    step_rotate_handles = inspect.getsource(Kraken3DInspector._add_step_rotation_handles)
    rotation_arc_mesh = inspect.getsource(Kraken3DInspector._scene_placement_rotation_arc_mesh)
    rotation_arrowhead_mesh = inspect.getsource(Kraken3DInspector._scene_placement_rotation_arrowhead_mesh)
    rotation_toggle = inspect.getsource(Kraken3DInspector._toggle_rotation_handles)
    rotation_hover = inspect.getsource(Kraken3DInspector._set_rotation_handle_hover)
    debug_trace = inspect.getsource(Kraken3DInspector._debug_trace)
    show_rays_changed = inspect.getsource(Kraken3DInspector._on_show_rays_changed)
    ray_pick_enabled = inspect.getsource(Kraken3DInspector._ray_pick_enabled)
    ray_pick_changed = inspect.getsource(Kraken3DInspector._on_ray_pick_changed)
    scene_visibility_changed = inspect.getsource(Kraken3DInspector._on_scene_visibility_changed)
    surface_menu = inspect.getsource(Kraken3DInspector._show_surface_function_context_menu)
    context_assign = inspect.getsource(Kraken3DInspector._assign_row_face_function_from_context)
    context_promote_assign = inspect.getsource(Kraken3DInspector._promote_step_and_assign_face_function)
    hover_status = inspect.getsource(Kraken3DInspector._update_hover_status)
    face_hover_status = inspect.getsource(Kraken3DInspector._face_hover_status_text)
    step_rotate_pick = inspect.getsource(Kraken3DInspector._apply_step_rotation_handle)
    step_import = inspect.getsource(Kraken3DInspector.import_step_overlay)
    optical_step_import = inspect.getsource(Kraken3DInspector.import_optical_step_overlay)
    step_carry_grid = inspect.getsource(Kraken3DInspector._add_step_carry_grid_overlay)
    step_carry_spacing = inspect.getsource(Kraken3DInspector._step_carry_grid_spacing)
    step_carry_mode = inspect.getsource(Kraken3DInspector._on_step_carry_grid_selected)
    step_carry_motion = inspect.getsource(Kraken3DInspector._apply_step_carry_motion_state)
    step_carry_plane_motion = inspect.getsource(Kraken3DInspector._apply_step_carry_plane_motion_state)
    step_carry_actor_motion = inspect.getsource(Kraken3DInspector._translate_step_overlay_actors)
    step_carry_drag = inspect.getsource(Kraken3DInspector._apply_step_carry_drag_motion)
    step_carry_cursor_plane = inspect.getsource(Kraken3DInspector._cursor_plane_point)
    step_carry_display_world = inspect.getsource(Kraken3DInspector._display_to_world_3d)
    step_carry_follow_state = inspect.getsource(Kraken3DInspector._new_step_carry_follow_state)
    step_carry_follow_motion = inspect.getsource(Kraken3DInspector._apply_step_carry_follow_motion)
    step_carry_pick_label = inspect.getsource(Kraken3DInspector._step_carry_label_from_current_pick)
    step_carry_hold_arm = inspect.getsource(Kraken3DInspector._arm_step_carry_hold)
    step_carry_hold_activate = inspect.getsource(Kraken3DInspector._activate_step_carry_hold)
    step_carry_hold_cancel = inspect.getsource(Kraken3DInspector._cancel_step_carry_hold_timer)
    step_carry_cursor = inspect.getsource(Kraken3DInspector._set_step_carry_cursor)
    step_carry_center = inspect.getsource(Kraken3DInspector._step_overlay_center_world)
    step_carry_grip_show = inspect.getsource(Kraken3DInspector._show_step_carry_grip_marker)
    step_carry_grip_translate = inspect.getsource(Kraken3DInspector._translate_step_carry_grip_marker)
    step_carry_grip_update = inspect.getsource(Kraken3DInspector._update_step_carry_grip_after_delta)
    step_carry_grip_clear = inspect.getsource(Kraken3DInspector._clear_step_carry_grip_marker)
    step_promote = inspect.getsource(Kraken3DInspector.promote_selected_step_to_optical_solid_row)
    step_promote_helper = inspect.getsource(Kraken3DInspector._promote_step_overlay_to_optical_solid_row)
    delete_step = inspect.getsource(Kraken3DInspector.delete_selected_step)
    delete_step_event = inspect.getsource(Kraken3DInspector._delete_selected_step_event)
    step_carry_start = inspect.getsource(Kraken3DInspector.start_selected_step_carry)
    step_carry_snap_start = inspect.getsource(Kraken3DInspector.start_step_carry_snap_ray)
    step_carry_snap_apply = inspect.getsource(Kraken3DInspector._apply_step_carry_snap_ray)
    step_carry_snap_target_start = inspect.getsource(Kraken3DInspector.start_step_carry_snap_target)
    step_carry_snap_target_apply = inspect.getsource(Kraken3DInspector._apply_step_carry_snap_target)
    step_feature_action_selection = inspect.getsource(Kraken3DInspector._step_feature_action_selection)
    step_normal_snap = inspect.getsource(Kraken3DInspector.snap_selected_step_normal_to_optical_axis)
    step_pick_normal_snap = inspect.getsource(Kraken3DInspector.snap_selected_step_pick_point_normal_to_optical_axis)
    step_normal_axis_start = inspect.getsource(Kraken3DInspector.start_step_normal_axis_pick)
    step_normal_axis_apply = inspect.getsource(Kraken3DInspector._apply_step_normal_axis_pick)
    step_surface_center_action = inspect.getsource(Kraken3DInspector.center_selected_step_surface_to_optical_axis)
    step_surface_center_axis_start = inspect.getsource(Kraken3DInspector.start_step_surface_center_axis_pick)
    step_surface_center_axis_apply = inspect.getsource(Kraken3DInspector._apply_step_surface_center_axis_pick)
    step_surface_center_pick = inspect.getsource(Kraken3DInspector._surface_center_from_face_ray_pick)
    optical_axis_records = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    optical_axis_overlays = inspect.getsource(Kraken3DInspector._add_optical_axis_pick_overlays)
    optical_axis_highlight = inspect.getsource(Kraken3DInspector._set_optical_axis_highlight)
    optical_axis_frame = inspect.getsource(Kraken3DInspector._optical_axis_frame_from_pick)
    optical_axis_screen_pick = inspect.getsource(Kraken3DInspector._optical_axis_info_near_display_xy)
    picked_step_feature = inspect.getsource(Kraken3DInspector._picked_feature_info)
    display_pick_ray = inspect.getsource(Kraken3DInspector._display_pick_ray)
    row_face_ray_pick = inspect.getsource(Kraken3DInspector._row_face_ray_pick_for_display_xy)
    step_face_ray_pick = inspect.getsource(Kraken3DInspector._step_face_ray_pick_for_display_xy)
    face_ray_pick_service = inspect.getsource(pick_face_from_ray)
    remember_step_feature = inspect.getsource(Kraken3DInspector._remember_selected_step_feature)
    step_carry_drop = inspect.getsource(Kraken3DInspector.stop_step_carry)
    operation_cancel = inspect.getsource(Kraken3DInspector.cancel_active_3d_operation)
    clear_selection = inspect.getsource(Kraken3DInspector._clear_open3d_selection)
    remove_step_handles = inspect.getsource(Kraken3DInspector._remove_step_rotation_handle_actors)
    key_press = inspect.getsource(Kraken3DInspector._on_key_press)
    refresh = inspect.getsource(Kraken3DInspector.refresh_scene)
    add_mesh_actor = inspect.getsource(Kraken3DInspector._add_mesh_actor)
    build_ui = inspect.getsource(KrakenLayoutEditor._build_ui)
    main_analysis_toolbar_panel = inspect.getsource(MainAnalysisToolbarPanel)
    main_analysis_toolbar_factory = inspect.getsource(KrakenLayoutEditor._main_analysis_toolbar_panel)
    main_information_panel = inspect.getsource(MainInformationPanel)
    main_information_factory = inspect.getsource(KrakenLayoutEditor._main_information_panel)
    build_results_panel = inspect.getsource(KrakenLayoutEditor._build_results_panel)
    main_atmosphere_panel = inspect.getsource(MainAtmospherePanel)
    main_atmosphere_factory = inspect.getsource(KrakenLayoutEditor._main_atmosphere_panel)
    build_atmosphere_panel = inspect.getsource(KrakenLayoutEditor._build_atmosphere_panel)
    open_atmosphere_dialog = inspect.getsource(KrakenLayoutEditor.open_atmosphere_settings_dialog)
    close_atmosphere_dialog = inspect.getsource(KrakenLayoutEditor._close_atmosphere_settings_dialog)
    main_coating_dialog = inspect.getsource(MainCoatingMaterialDialog)
    main_coating_dialog_factory = inspect.getsource(KrakenLayoutEditor._main_coating_material_dialog)
    open_coating_dialog = inspect.getsource(KrakenLayoutEditor.open_coating_material_editor)
    main_diffuse_dialog = inspect.getsource(MainDiffuseScatterDialog)
    main_diffuse_dialog_factory = inspect.getsource(KrakenLayoutEditor._main_diffuse_scatter_dialog)
    open_diffuse_dialog = inspect.getsource(KrakenLayoutEditor.open_diffuse_scatter_settings)
    main_surface_shape_dialog = inspect.getsource(MainSurfaceShapeBuilderDialog)
    main_surface_shape_factory = inspect.getsource(KrakenLayoutEditor._main_surface_shape_builder_dialog)
    open_surface_shape_builder = inspect.getsource(KrakenLayoutEditor.open_surface_shape_builder)
    main_beam_splitter_dialog = inspect.getsource(MainBeamSplitterDialog)
    main_beam_splitter_factory = inspect.getsource(KrakenLayoutEditor._main_beam_splitter_dialog)
    open_beam_splitter_dialog = inspect.getsource(KrakenLayoutEditor.open_beam_splitter_settings)
    main_error_map_dialog = inspect.getsource(MainErrorMapDialog)
    main_error_map_factory = inspect.getsource(KrakenLayoutEditor._main_error_map_dialog)
    open_error_map_dialog = inspect.getsource(KrakenLayoutEditor.open_error_map_editor)
    main_advanced_surface_dialog = inspect.getsource(MainAdvancedSurfaceDialog)
    main_advanced_surface_factory = inspect.getsource(KrakenLayoutEditor._main_advanced_surface_dialog)
    open_advanced_surface_dialog = inspect.getsource(KrakenLayoutEditor.open_advanced_surface_editor)
    main_surface_settings_dialogs = inspect.getsource(MainSurfaceSettingsDialogs)
    main_surface_settings_factory = inspect.getsource(KrakenLayoutEditor._main_surface_settings_dialogs)
    open_galvo_settings = inspect.getsource(KrakenLayoutEditor.open_galvo_scan_overlay_settings)
    open_surface_additional_settings = inspect.getsource(KrakenLayoutEditor.open_surface_additional_settings)
    open_grating_settings = inspect.getsource(KrakenLayoutEditor._open_grating_settings_editor)
    main_context_menu = inspect.getsource(MainContextMenu)
    main_context_menu_factory = inspect.getsource(KrakenLayoutEditor._main_context_menu)
    show_context_menu = inspect.getsource(KrakenLayoutEditor.show_context_menu)
    main_scene_element_dialogs = inspect.getsource(MainSceneElementDialogs)
    main_scene_element_factory = inspect.getsource(KrakenLayoutEditor._main_scene_element_dialogs)
    open_detector_dialog = inspect.getsource(KrakenLayoutEditor.open_detector_settings)
    open_scene_target_dialog = inspect.getsource(KrakenLayoutEditor.open_scene_target_editor)
    open_path_pose_dialog = inspect.getsource(KrakenLayoutEditor.open_selected_path_local_pose_editor)
    open_element_dialog = inspect.getsource(KrakenLayoutEditor.open_element_settings)
    main_scene_source_dialog = inspect.getsource(MainSceneSourceManagerDialog)
    main_scene_source_factory = inspect.getsource(KrakenLayoutEditor._main_scene_source_manager_dialog)
    open_scene_source_manager = inspect.getsource(KrakenLayoutEditor.open_scene_source_manager)
    main_stock_lens_dialog = inspect.getsource(MainStockLensImporterDialog)
    main_stock_lens_factory = inspect.getsource(KrakenLayoutEditor._main_stock_lens_importer_dialog)
    open_stock_lens_importer = inspect.getsource(KrakenLayoutEditor.open_stock_lens_importer)
    main_branch_throughput_report_dialog = inspect.getsource(MainBranchThroughputReportDialog)
    main_branch_throughput_factory = inspect.getsource(KrakenLayoutEditor._main_branch_throughput_report_dialog)
    open_branch_throughput_report = inspect.getsource(KrakenLayoutEditor.open_branch_throughput_report)
    refresh_branch_throughput_report = inspect.getsource(KrakenLayoutEditor._refresh_branch_throughput_report)
    main_source_illumination_report_dialog = inspect.getsource(MainSourceIlluminationReportDialog)
    main_source_illumination_factory = inspect.getsource(KrakenLayoutEditor._main_source_illumination_report_dialog)
    open_source_illumination_report = inspect.getsource(KrakenLayoutEditor.open_source_illumination_report)
    refresh_source_illumination_report = inspect.getsource(KrakenLayoutEditor._refresh_source_illumination_report)
    main_detector_aperture_report_dialog = inspect.getsource(MainDetectorApertureReportDialog)
    main_detector_aperture_factory = inspect.getsource(KrakenLayoutEditor._main_detector_aperture_report_dialog)
    open_detector_aperture_report = inspect.getsource(KrakenLayoutEditor.open_detector_aperture_report)
    refresh_detector_aperture_report = inspect.getsource(KrakenLayoutEditor._refresh_detector_aperture_report)
    main_branch_gaussian_q_dialog = inspect.getsource(MainBranchGaussianQDialog)
    main_branch_gaussian_q_factory = inspect.getsource(KrakenLayoutEditor._main_branch_gaussian_q_dialog)
    open_branch_gaussian_q_report = inspect.getsource(KrakenLayoutEditor.open_branch_gaussian_q_report)
    refresh_branch_gaussian_q_report = inspect.getsource(KrakenLayoutEditor._refresh_branch_gaussian_q_report)
    main_lens_drawing_dialogs = inspect.getsource(MainLensDrawingDialogs)
    main_lens_drawing_factory = inspect.getsource(KrakenLayoutEditor._main_lens_drawing_dialogs)
    open_lens_drawing_properties = inspect.getsource(KrakenLayoutEditor._open_lens_drawing_surface_properties_dialog)
    export_lens_drawing_wrapper = inspect.getsource(KrakenLayoutEditor.export_lens_drawing)
    main_paraxial_analysis_dialogs = inspect.getsource(MainParaxialAnalysisDialogs)
    main_paraxial_analysis_factory = inspect.getsource(KrakenLayoutEditor._main_paraxial_analysis_dialogs)
    open_gaussian_report = inspect.getsource(KrakenLayoutEditor.open_gaussian_beam_report)
    open_paraxial_calculator = inspect.getsource(KrakenLayoutEditor.open_paraxial_calculator)
    main_optimization_panel = inspect.getsource(MainOptimizationPanel)
    main_optimization_factory = inspect.getsource(KrakenLayoutEditor._main_optimization_panel)
    build_optimization_panel = inspect.getsource(KrakenLayoutEditor._build_optimization_panel)
    main_trace_display_panel = inspect.getsource(MainTraceDisplayControlsPanel)
    main_trace_display_panel_factory = inspect.getsource(KrakenLayoutEditor._main_trace_display_controls_panel)
    build_controls_panel = inspect.getsource(KrakenLayoutEditor._build_controls_panel)
    main_field_panel = inspect.getsource(MainFieldControlsPanel)
    main_field_panel_factory = inspect.getsource(KrakenLayoutEditor._main_field_controls_panel)
    build_field_panel = inspect.getsource(KrakenLayoutEditor._build_field_panel)
    main_source_panel = inspect.getsource(MainSourceControlsPanel)
    main_source_panel_factory = inspect.getsource(KrakenLayoutEditor._main_source_controls_panel)
    build_source_panel = inspect.getsource(KrakenLayoutEditor._build_source_panel)
    thickness_dimensions = inspect.getsource(Open3DThicknessDimensionService.add_overlays)
    thickness_arrow = inspect.getsource(Open3DThicknessDimensionService.arrow_mesh)
    thickness_label = inspect.getsource(Open3DThicknessDimensionService.add_label_actor)
    thickness_edit = inspect.getsource(Open3DThicknessDimensionService.edit_dimension)
    step_admin_source = inspect.getsource(Open3DStepAdminPanel).replace("self.inspector.", "self.")
    step_admin_overlay_select = inspect.getsource(Kraken3DInspector.select_step_overlay_from_admin)
    step_admin_promoted_select = inspect.getsource(Kraken3DInspector.select_promoted_step_row_from_admin)
    row_scene_bounds = inspect.getsource(Kraken3DInspector._row_scene_bounds)
    init = inspect.getsource(Kraken3DInspector.__init__)
    top_controls_source = inspect.getsource(Open3DTopControlsPanel).replace("self.inspector.", "self.")
    init_with_top_controls = init + "\n" + top_controls_source
    try:
        plain_step_select_block = pick.split("if requested_label is None and not axis_pick_any:", 1)[1].split(
            "if requested_label is not None and requested_label != step_label:",
            1,
        )[0]
    except Exception:
        plain_step_select_block = ""
    open3d_display_camera = inspect.getsource(Kraken3DInspector._camera_preset_from_display_orientation)
    legacy_configure = inspect.getsource(KrakenLayoutEditor._configure_legacy_3d_plotter)
    legacy_display_camera = inspect.getsource(KrakenLayoutEditor._legacy_3d_camera_preset_from_display_orientation)
    ray_inspector = inspect.getsource(KrakenLayoutEditor.open_ray_inspector)
    placement_grid = inspect.getsource(Kraken3DInspector._add_scene_placement_grid_overlays)
    show_scene_placement_handles = inspect.getsource(Kraken3DInspector._show_scene_placement_handles)
    placement_grid_mesh = inspect.getsource(Kraken3DInspector._scene_placement_grid_mesh)
    placement_grid_status = inspect.getsource(Kraken3DInspector._update_placement_grid_status)
    detector_overlays = inspect.getsource(Kraken3DInspector._add_scene_detector_overlays)
    placement_handles = inspect.getsource(Kraken3DInspector._add_scene_placement_translate_handles)
    placement_rotate_handles = inspect.getsource(Kraken3DInspector._add_scene_placement_rotate_handles)
    placement_handle_pick = inspect.getsource(Kraken3DInspector._apply_scene_placement_translate_handle)
    placement_rotate_pick = inspect.getsource(Kraken3DInspector._apply_scene_placement_rotate_handle)
    placement_drag_start = inspect.getsource(Kraken3DInspector._placement_drag_state_from_current_pick)
    placement_drag = inspect.getsource(Kraken3DInspector._apply_placement_drag_motion)
    placement_target_start = inspect.getsource(Kraken3DInspector.start_placement_target_pick)
    placement_target_apply = inspect.getsource(Kraken3DInspector._apply_placement_target_pick)
    center_row_axis_start = inspect.getsource(Kraken3DInspector.start_center_row_to_ray)
    center_row_axis_hide = inspect.getsource(Kraken3DInspector._hide_regular_rays_for_center_axis_pick)
    center_row_axis_row_pick = inspect.getsource(Kraken3DInspector._center_row_pick_row_ignoring_axis_overlays)
    center_axis_source_pick = inspect.getsource(Kraken3DInspector._center_axis_source_pick_ignoring_axis_overlays)
    center_row_axis_visibility = inspect.getsource(Kraken3DInspector._should_draw_optical_axis_overlays)
    center_row_axis_apply = inspect.getsource(Kraken3DInspector._apply_center_row_to_optical_axis)
    editor_center_row_axis = inspect.getsource(KrakenLayoutEditor.center_surface_row_on_optical_axis)
    row_actor_highlight = inspect.getsource(Kraken3DInspector._set_row_actor_selected)
    step_feature_cache = inspect.getsource(Kraken3DInspector._picked_feature_info_cached)
    mouse_move_due = inspect.getsource(Kraken3DInspector._mouse_move_due)
    placement_orient_start = inspect.getsource(Kraken3DInspector.start_placement_orient_pick)
    placement_orient_apply = inspect.getsource(Kraken3DInspector._apply_placement_orient_pick)
    placement_orient_ray_start = inspect.getsource(Kraken3DInspector.start_placement_orient_ray_pick)
    placement_orient_ray_apply = inspect.getsource(Kraken3DInspector._apply_placement_orient_ray_pick)
    placement_orient_source = inspect.getsource(Kraken3DInspector.orient_selected_row_to_source_direction)
    placement_orient_path = inspect.getsource(Kraken3DInspector.orient_selected_row_to_path_frame)
    placement_orient_axis = inspect.getsource(Kraken3DInspector.orient_selected_row_to_local_axis)
    placement_orient_scene_source = inspect.getsource(Kraken3DInspector.orient_selected_row_to_scene_source)
    placement_preview_named_normal = inspect.getsource(Kraken3DInspector.preview_selected_row_normal_target)
    placement_orient_named_normal = inspect.getsource(Kraken3DInspector.orient_selected_row_to_named_normal_target)
    editor_translate = inspect.getsource(KrakenLayoutEditor.translate_scene_row_pose)
    editor_rotate = inspect.getsource(KrakenLayoutEditor.rotate_scene_row_pose_world_axis)
    default_uncoated = inspect.getsource(KrakenLayoutEditor._default_uncoated_optical_solid_face_metadata)
    editor_step_translate = inspect.getsource(KrakenLayoutEditor.translate_step_overlay)
    editor_row_translate_vector = inspect.getsource(KrakenLayoutEditor.translate_scene_row_pose_vector)
    editor_step_promote = inspect.getsource(KrakenLayoutEditor.promote_imported_step_to_optical_solid_row)
    editor_step_snap = inspect.getsource(KrakenLayoutEditor.snap_step_overlay_center_to_world_point)
    editor_step_snap_target = inspect.getsource(KrakenLayoutEditor.snap_step_overlay_center_to_scene_target)
    editor_step_normal_snap = inspect.getsource(KrakenLayoutEditor.snap_step_feature_normal_to_optical_axis)
    editor_step_axis_frame = inspect.getsource(KrakenLayoutEditor._step_optical_axis_frame_near_point)
    editor_axis_record_frame = inspect.getsource(KrakenLayoutEditor._optical_axis_frame_from_record)
    editor_step_overlay_axis_snap = inspect.getsource(KrakenLayoutEditor.snap_step_overlay_face_to_optical_axis)
    editor_step_transform = inspect.getsource(KrakenLayoutEditor._cad_mesh_aligned_to_optical_axis)
    editor_snap_target = inspect.getsource(KrakenLayoutEditor.snap_scene_row_anchor_to_target)
    editor_orient_target = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_target)
    editor_orient_vector = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_vector)
    editor_orient_source = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_current_source)
    editor_orient_path = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_current_path_frame)
    editor_orient_axis = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_local_axis)
    editor_orient_scene_source = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_scene_source)
    editor_preview_named_normal = inspect.getsource(KrakenLayoutEditor.preview_scene_row_anchor_to_named_normal_target)
    editor_orient_named_normal = inspect.getsource(KrakenLayoutEditor.orient_scene_row_anchor_to_named_normal_target)
    placement_features = inspect.getsource(KrakenLayoutEditor._scene_placement_features)
    placement_detail = inspect.getsource(KrakenLayoutEditor._scene_placement_detail)
    badge_text = inspect.getsource(Kraken3DInspector._active_mode_badge_text)
    badge_update = inspect.getsource(Kraken3DInspector._update_mode_badge)
    trace_summary_text = inspect.getsource(Kraken3DInspector._trace_summary_text)
    trace_terminal_face_summary = inspect.getsource(Kraken3DInspector._ray_path_terminal_face_summary)
    trace_summary = inspect.getsource(Kraken3DInspector._update_trace_summary)
    optical_axis_records = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    optical_axis_overlays = inspect.getsource(Kraken3DInspector._add_optical_axis_pick_overlays)
    traced_face_context_pick = inspect.getsource(Kraken3DInspector._traced_row_face_hit_near_display_xy)
    stl_handler = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    stl_refresh = inspect.getsource(Kraken3DInspector._refresh_after_stl_pose_change)
    right_click_menu = inspect.getsource(Kraken3DInspector._show_surface_function_context_menu)
    assign_row_face_context = inspect.getsource(Kraken3DInspector._assign_row_face_function_from_context)
    row_carry_pick = inspect.getsource(Kraken3DInspector._row_carry_index_from_current_pick)
    row_carry_activate = inspect.getsource(Kraken3DInspector._activate_row_carry_hold)
    row_carry_apply = inspect.getsource(Kraken3DInspector._apply_row_carry_drag_motion)
    row_carry_finish = inspect.getsource(Kraken3DInspector._finish_row_carry_drag)
    snapshot = inspect.getsource(Kraken3DInspector.save_snapshot)
    refresh_from_editor = inspect.getsource(Kraken3DInspector.refresh_from_editor)
    endpoint_actor = inspect.getsource(Kraken3DInspector._add_ray_endpoint_actor)
    face_overlays = inspect.getsource(Kraken3DInspector._add_optical_solid_face_role_overlays)
    assigned_face_overlays = inspect.getsource(Kraken3DInspector._add_optical_solid_assigned_face_overlays)
    assigned_face_triangles = inspect.getsource(Kraken3DInspector._world_face_triangles_for_record)
    clear_step_overlay_state = inspect.getsource(Kraken3DInspector._clear_step_overlay_interaction_state)
    virtual_plane_overlays = inspect.getsource(Kraken3DInspector._add_optical_solid_virtual_plane_overlays)
    runtime_face_markers = inspect.getsource(Kraken3DInspector._face_role_markers_from_runtime_transform)
    editor_refresh_plot = inspect.getsource(KrakenLayoutEditor.refresh_plot)
    editor_build_scene_bundle = inspect.getsource(KrakenLayoutEditor._build_scene_bundle)
    editor_surface_meshes = inspect.getsource(KrakenLayoutEditor._iter_3d_optical_surface_meshes)
    refresh_3d_sync = inspect.getsource(KrakenLayoutEditor._refresh_3d_inspector_if_open)
    open3d_refresh_service = inspect.getsource(Open3DTraceRefreshService)
    open3d_step_state_service = inspect.getsource(Open3DStepStateService)
    widget_tooltip = inspect.getsource(WidgetTooltip)
    preview_sampling = inspect.getsource(KrakenLayoutEditor._preview_scene_sampling_mode)
    trace_preview_rays = inspect.getsource(KrakenLayoutEditor._trace_preview_rays)
    build_source_panel = inspect.getsource(KrakenLayoutEditor._build_source_panel)
    reset_runtime_state = inspect.getsource(KrakenLayoutEditor._reset_complete_layout_runtime_state)
    current_source_cone = inspect.getsource(KrakenLayoutEditor._current_source_cone_angle)
    saved_layout_figure = inspect.getsource(build_saved_layout_figure)
    scene_ray_records = inspect.getsource(KrakenLayoutEditor._iter_3d_scene_ray_records)
    ray_terminal_style = inspect.getsource(KrakenLayoutEditor._ray_terminal_3d_style)
    should_draw_endpoint = inspect.getsource(KrakenLayoutEditor._should_draw_3d_terminal_endpoint)
    bounded_ray_display = inspect.getsource(KrakenLayoutEditor._bounded_3d_ray_points_for_display)
    shared_bounded_ray_display = inspect.getsource(bounded_ray_points_for_scene_display)
    shared_scene_bounds = inspect.getsource(scene_display_center_radius)
    editor_detector_overlays = inspect.getsource(KrakenLayoutEditor._scene_detector_overlay_specs)
    legacy_open_3d = inspect.getsource(KrakenLayoutEditor._populate_legacy_3d_plotter_scene)
    legacy_replace_rays = inspect.getsource(KrakenLayoutEditor._legacy_3d_replace_rays)
    continuation_sync_ok, continuation_sync_diag = _scene_path_preserves_raykeeper_terminal_continuation()
    exit_axis_ok, exit_axis_diag = _traced_axis_records_mark_exit_segment()
    escaped_axis_ok, escaped_axis_diag = _traced_axis_records_bound_long_escaped_tail()
    checks = [
        (
            "Scene path event sync preserves raykeeper terminal continuation",
            continuation_sync_ok,
        ),
        (
            "Traced optical-axis records identify post-surface exit segments for cascade placement",
            exit_axis_ok,
        ),
        (
            "Traced optical-axis records anchor escaped tails near the last real surface",
            escaped_axis_ok,
        ),
        ("left drag binding exists", '"<B1-Motion>"' in bindings),
        ("plain left press no longer performs immediate pick", "_on_left_button_press(None, None)" not in bindings.split("def left_motion", 1)[0]),
        ("release without drag performs selection", "should_pick" in bindings and "_on_left_button_press(None, None)" in bindings),
        ("drag threshold prevents accidental rotation", "drag_threshold_px" in bindings),
        ("fixed drag method uses constant sensitivity", "degrees_per_pixel" in rotation),
        ("fixed drag preserves focal point", "camera.SetFocalPoint(*focal)" in rotation),
        ("fixed drag uses azimuth/elevation only", "camera.Azimuth" in rotation and "camera.Elevation" in rotation),
        (
            "middle drag pans camera in the view plane",
            '"<ButtonPress-2>"' in bindings
            and '"<B2-Motion>"' in bindings
            and '"<ButtonRelease-2>"' in bindings
            and "_pan_camera_fixed_drag(dx, dy)" in bindings
            and "camera.SetPosition(*(position[:3] + delta[:3]))" in camera_pan
            and "camera.SetFocalPoint(*(focal[:3] + delta[:3]))" in camera_pan
            and "camera.GetViewUp()" in camera_pan
            and "camera.GetParallelScale()" in camera_pan,
        ),
        ("VTK left-button trackball forwarding removed", "LeftButtonPressEvent(event" not in bindings),
        ("STEP click activates rotation handles", "show_step_rotation_handler(step_label)" in pick),
        (
            "STEP reselect rebuilds rotation handles after blank deselect",
            "_ensure_step_rotation_handles_for_label(label)" in handler
            and "_add_step_rotation_handles(label, mesh)" in ensure_step_handles
            and "_step_rotation_handle_count_for_label(label)" in ensure_step_handles,
        ),
        (
            "plain STEP face click keeps rotation handles usable",
            "start_step_normal_axis_pick(step_label)" not in plain_step_select_block
            and "Rotation handles remain active" in plain_step_select_block,
        ),
        ("STEP rotation handler is not a popup", "tk.Toplevel" not in handler and "_step_rotation_active_label" in handler),
        ("STEP rotation handles expose X/Y/Z axes", '("x",' in step_rotate_handles and '("y",' in step_rotate_handles and '("z",' in step_rotate_handles),
        ("STEP rotation handles expose signed user-selected arrows per axis", "sign=1.0" in step_rotate_handles and "_rotation_handle_step_deg()" in step_rotate_handles and "(-float(step), float(step))" in step_rotate_handles),
        ("STEP rotation handles are pickable scene actors", "pick_step_rotate" in step_rotate_handles and "_actor_step_rotate_map" in pick),
        ("STEP rotation handles hover-highlight before click", "_set_rotation_handle_hover(actor_key)" in mouse_move and "STEP rotation handle: click" in mouse_move and "SetColor(1.0, 0.78, 0.08)" in rotation_hover),
        ("STEP rotation handles can be hidden from the toolbar", "show_rotation_handles_var" in init and "_toggle_rotation_handles" in init_with_top_controls and "_show_rotation_handles()" in step_rotate_handles and "_remove_step_rotation_handle_actors" in rotation_toggle),
        ("Open 3D rotation handles expose selectable step size", "rotation_step_deg_var" in init and "15" in init_with_top_controls and "45" in init_with_top_controls and "180" in init_with_top_controls and "_on_rotation_step_changed" in init_with_top_controls),
        ("STEP rotation arcs show opposed start/end cone arrowheads", "pv.Cone" in rotation_arc_mesh and "point_array[0] - point_array[1]" in rotation_arc_mesh and "point_array[-1] - point_array[-2]" in rotation_arc_mesh),
        ("STEP rotation end arrows are scaled for CAD-style visibility", "float(radius) * 0.24" in rotation_arrowhead_mesh and "float(arrow_scale) * 0.15" in rotation_arrowhead_mesh),
        ("STEP rotation handle rotates selected component around the visible world axis", "rotate_step_world_axis(label, axis" in step_rotate_pick),
        (
            "Open 3D interaction trace captures clicks, face assignment, and refresh counts",
            "_open3d_debug_seq" in init
            and "Open3DTrace" in debug_trace
            and "left_click_pick" in pick
            and "right_click_context" in surface_menu
            and "face_assignment_start" in context_assign
            and "face_assignment_metadata_saved" in context_assign
            and "promote_step_face_assignment_start" in context_promote_assign
            and "refresh_scene_start" in refresh
            and "refresh_scene_done" in refresh
            and "show_rays_toggled" in show_rays_changed,
        ),
        ("Open 3D STEP import enters carry mode", "_step_carry_active_label = label" in step_import),
        (
            "Open 3D optical STEP import uses a distinct overlay slot",
            "import_optical_step(" in optical_step_import
            and 'label = "optical"' in optical_step_import
            and "import_lens_step(" not in optical_step_import
            and "_start_step_carry_follow(label)" in optical_step_import,
        ),
        (
            "Open 3D STEP carry has no cube lattice builder",
            "_step_carry_cube_grid_mesh" not in step_carry_grid
            and "_add_mesh_actor" not in step_carry_grid
            and "STEP carry:" in step_carry_grid,
        ),
        (
            "Open 3D STEP carry suppresses row placement grid lines",
            "step_carry_label = self._step_carry_label()" in refresh
            and "placement_grid_lines, placement_grid_summary = 0, \"\"" in refresh,
        ),
        ("Open 3D STEP carry removes snap-step selector", "Snap step" not in init and "STEP_CARRY_GRID_CHOICES" not in init),
        ("Open 3D STEP carry defaults to Free mode", STEP_CARRY_GRID_CHOICES == (STEP_CARRY_GRID_FREE,)),
        (
            "Open 3D STEP carry removes ray/grid snapping from drag path",
            "ray_snap_enabled\": False" in inspect.getsource(Kraken3DInspector._new_step_carry_motion_state)
            and "snap_enabled\": False" in inspect.getsource(Kraken3DInspector._new_step_carry_motion_state)
            and "_step_carry_ray_target(state" not in step_carry_plane_motion,
        ),
        (
            "Open 3D STEP normal snap defaults to surface-center anchoring",
            "Snap STEP Surface-Center Normal->Optical Axis" in init_with_top_controls
            and "Snap STEP Pick-Point Normal->Optical Axis" in init_with_top_controls
            and "Center Normal->Axis" in step_admin_source
            and "Pick Normal->Axis" in step_admin_source
            and "_remember_selected_step_feature" in pick
            and "start_step_normal_axis_pick(step_label)" in pick
            and "step_feature_selection(" in remember_step_feature
            and "selected_feature_action(" in step_feature_action_selection
            and "normal_world" in open3d_step_state_service
            and 'anchor_mode="surface_center"' in step_normal_snap
            and 'anchor_mode="pick_point"' in step_pick_normal_snap
            and "selection.surface_center_world" in step_normal_axis_apply
            and "selection.pick_point_world if anchor_mode == \"pick_point\" else selection.surface_center_world" in step_normal_axis_apply
            and "_step_normal_axis_anchor_mode = anchor_mode" in step_normal_axis_start
            and "_step_normal_axis_pick_mode = True" in step_normal_axis_start
            and "_actor_optical_axis_map" in pick
            and "_apply_step_normal_axis_pick(axis_info)" in pick
            and "_optical_axis_frame_from_pick" in step_normal_axis_apply
            and "axis_frame=axis_frame" in step_normal_axis_apply
            and "pick_optical_axis=record" in optical_axis_overlays
            and "_optical_axis_info_near_display_xy((x, y)" in pick
            and "_optical_axis_info_near_display_xy((x, y)" in mouse_move
            and "picked_world" in optical_axis_frame
            and "_world_to_display_2d" in optical_axis_screen_pick
            and "_closest_polyline_point_and_direction" in optical_axis_frame
            and "_nearest_traced_ray_frame_near_point" in editor_step_axis_frame
            and "_rotation_matrix_between_vectors" in editor_step_normal_snap
            and "_affine_from_point_sets" in editor_step_normal_snap,
        ),
        (
            "Open 3D STEP hover reports pick and surface-center coordinates",
            "_world_xyz_text" in mouse_move
            and "Pick=" in mouse_move
            and "Center=" in mouse_move
            and "_surface_center_from_face_ray_pick" in mouse_move
            and "centroid_world" in step_surface_center_pick,
        ),
        (
            "Open 3D can center a selected STEP surface on the optical axis separately from normal snap",
            "Center STEP Surface->Optical Axis" in top_controls_source
            and "Center Surface->Axis" in step_admin_source
            and "center_selected_step_surface_to_optical_axis" in step_admin_source
            and "_selected_step_feature: StepFeatureSelection | None" in init
            and "_selected_step_feature_surface_center_world" in init
            and "step_feature_selection(" in open3d_step_state_service
            and "selected_feature_action(" in open3d_step_state_service
            and "surface_center_world" in remember_step_feature
            and "start_step_surface_center_axis_pick(label)" in step_surface_center_action
            and "_step_surface_center_axis_pick_mode = True" in step_surface_center_axis_start
            and "_step_normal_axis_pick_mode = False" in step_surface_center_axis_start
            and "_apply_step_surface_center_axis_pick(axis_info)" in pick
            and "translate_step_overlay(label, delta[:3], refresh=False)" in step_surface_center_axis_apply
            and "Surface center=" in step_surface_center_axis_start
            and "_step_surface_center_axis_pick_mode = False" in operation_cancel,
        ),
        ("Open 3D STEP carry mode is free-only", "STEP carry uses free drag movement" in step_carry_mode),
        (
            "Open 3D STEP carry drag writes through placement state",
            "_apply_step_carry_plane_motion_state" in step_carry_drag
            and "_apply_step_carry_motion_state" in step_carry_drag
            and "translate_step_overlay" in step_carry_plane_motion
            and "translate_step_overlay" in step_carry_motion
            and "_step_placement_offset_xyz" in editor_step_translate,
        ),
        (
            "Open 3D STEP carry uses a center drag plane instead of screen deltas",
            "current_xy=current" in step_carry_drag_branch
            and "_cursor_plane_point" in step_carry_plane_motion
            and "drag_plane_origin" in step_carry_hold_activate
            and "drag_plane_normal" in step_carry_hold_activate
            and "drag_anchor_world" in step_carry_hold_activate
            and "start_center_world" in step_carry_hold_activate
            and "attach_to_cursor_on_next_motion" in step_carry_follow_state
            and "cursor_world[:3] - center_world[:3]" in step_carry_follow_motion
            and "DisplayToWorld" in step_carry_display_world
            and "continuous_plane_center" in step_carry_plane_motion
            and "np.trunc(raw_delta / spacing)" not in step_carry_plane_motion,
        ),
        (
            "Open 3D STEP carry drag rebases each motion event",
            "_apply_step_carry_drag_motion(dx, dy, current_xy=current)" in step_carry_drag_branch
            and "_left_drag_last_xy = current" in step_carry_drag_branch
            and step_carry_drag_branch.find("_left_drag_last_xy = current")
            < step_carry_drag_branch.find('return "break"'),
        ),
        ("Open 3D STEP carry avoids full scene rebuild per drag motion", "refresh=False" in step_carry_motion and "record_history=False" in step_carry_motion),
        ("Open 3D STEP carry moves existing actors in place", "AddPosition" in step_carry_actor_motion and "_step_follow_actor_map" in step_carry_actor_motion),
        ("Open 3D STEP carry Ctrl-drag rotates camera", "_event_control_pressed" in bindings and "_rotate_camera_fixed_drag(dx, dy)" in bindings),
        (
            "Open 3D STEP carry uses press-hold lift",
            "_step_carry_label_from_current_pick()" in bindings
            and "_arm_step_carry_hold(step_label" in bindings
            and "_step_carry_hold_candidate_label is not None" in bindings
            and "_activate_step_carry_hold()" in step_carry_drag_branch
            and "_vtk_widget.after" in step_carry_hold_arm
            and "_activate_step_carry_hold" in step_carry_hold_arm
            and "_step_carry_hold_after_id = None" in step_carry_hold_cancel,
        ),
        (
            "Open 3D STEP carry release drops held component",
            "step_carry_drag_state is not None" in bindings
            and "_finish_step_carry_drag(step_carry_drag_state)" in bindings
            and "_set_step_carry_cursor(False)" in inspect.getsource(Kraken3DInspector._finish_step_carry_drag),
        ),
        (
            "Open 3D STEP carry avoids pointer warping while gripping center",
            "_step_overlay_center_world(label)" in step_carry_hold_activate
            and "_show_step_carry_grip_marker(grip_world)" in step_carry_hold_activate
            and "center_world" in step_carry_hold_activate
            and "_sync_pointer_to_step_carry_center" not in step_carry_hold_activate
            and "_sync_pointer_to_step_carry_center" not in step_carry_drag
            and 'event_generate("<Motion>", warp=True' not in bindings
            and 'event_generate("<Motion>", warp=True' not in init
            and "_step_carry_pointer_syncing" not in init
            and "_transformed_imported_step_mesh_for_label" in step_carry_center
            and 'cursor="none"' in step_carry_cursor,
        ),
        (
            "Open 3D STEP carry shows an in-scene grip cursor",
            "_show_step_carry_grip_marker(grip_world)" in step_carry_hold_activate
            and "center_world" in step_carry_hold_activate
            and "_step_carry_grip_actor" in step_carry_grip_show
            and "actor.AddPosition" in step_carry_grip_translate
            and "_update_step_carry_grip_after_delta(state, delta)" in step_carry_motion
            and "_show_step_carry_grip_marker(grip[:3])" in step_carry_grip_update
            and "RemoveActor(actor)" in step_carry_grip_clear,
        ),
        (
            "Open 3D STEP carry only starts from STEP body picks",
            "_actor_step_map" in step_carry_pick_label
            and "_actor_step_rotate_map" in step_carry_pick_label
            and "_actor_placement_move_map" in step_carry_pick_label,
        ),
        (
            "Open 3D STEP carry removes old visible center snap actions",
            "Snap ray" not in init and "Snap target" not in init,
        ),
        (
            "Open 3D exposes STEP promotion to optical solid rows",
            "Promote STEP to Optical Solid Row" in init_with_top_controls and "promote_selected_step_to_optical_solid_row" in init_with_top_controls,
        ),
        (
            "Open 3D exposes explicit STEP placement acceptance",
            "Accept STEP Placement" in init_with_top_controls
            and "accept_selected_step_placement" in init_with_top_controls
            and "def accept_selected_step_placement" in inspect.getsource(Kraken3DInspector.accept_selected_step_placement),
        ),
        (
            "Open 3D exposes top-level Done 2D and Close actions",
            "Done 2D" in init_with_top_controls
            and "finish_stl_placement" in init_with_top_controls
            and "Close" in init_with_top_controls
            and "command=self._on_close" in init_with_top_controls,
        ),
        (
            "Open 3D visual diagnostics are opt-in toggles",
            "show_reference_surfaces_var = tk.BooleanVar(value=False)" in init
            and "show_detector_overlays_var = tk.BooleanVar(value=False)" in init
            and "show_terminal_diagnostics_var = tk.BooleanVar(value=False)" in init
            and "show_placement_handles_var = tk.BooleanVar(value=False)" in init
            and "scene_visibility_toggled" in scene_visibility_changed,
        ),
        (
            "Main Source controls panel lives outside layout_editor",
            "MainSourceControlsPanel(" in main_source_panel_factory
            and "source_model_default=SOURCE_MODEL_DEFAULT" in main_source_panel_factory
            and "self._main_source_controls_panel().build(parent)" in build_source_panel
            and "source_model_var" in main_source_panel
            and "source_cone_angle_var" in main_source_panel
            and "Scene Source Manager..." in main_source_panel
            and "_register_source_mode_controls(" in main_source_panel,
        ),
        (
            "Main Field controls panel lives outside layout_editor",
            "MainFieldControlsPanel(" in main_field_panel_factory
            and "field_type_values=FIELD_TYPE_CANONICAL_VALUES" in main_field_panel_factory
            and "camera_none_label=CAMERA_NONE_LABEL" in main_field_panel_factory
            and "self._main_field_controls_panel().build(parent)" in build_field_panel
            and "field_type_var" in main_field_panel
            and "field_count_var" in main_field_panel
            and "image_diameter_mode_var" in main_field_panel
            and "camera_model_var" in main_field_panel
            and "_sync_field_mode_ui()" in main_field_panel,
        ),
        (
            "Main Trace/Display controls panel lives outside layout_editor",
            "MainTraceDisplayControlsPanel(" in main_trace_display_panel_factory
            and "source_model_default=SOURCE_MODEL_DEFAULT" in main_trace_display_panel_factory
            and "coherent_sum_mode_values=COHERENT_SUM_MODE_VALUES" in main_trace_display_panel_factory
            and "self._main_trace_display_controls_panel().build(parent)" in build_controls_panel
            and "object_mode_var" in main_trace_display_panel
            and "trace_mode_var" in main_trace_display_panel
            and "nonseq_target_surface_var" in main_trace_display_panel
            and "analysis_branch_filter_var" in main_trace_display_panel
            and "_register_left_mode_control(" in main_trace_display_panel,
        ),
        (
            "Main analysis toolbar and information panel live outside layout_editor",
            "MainAnalysisToolbarPanel(self)" in main_analysis_toolbar_factory
            and "self._main_analysis_toolbar_panel().build(plot_toolbar_analysis)" in build_ui
            and "MainInformationPanel(self)" in main_information_factory
            and "self._main_information_panel().build(parent)" in build_results_panel
            and "analysis_mode_vars" in main_analysis_toolbar_panel
            and "toggle_analysis_mode" in main_analysis_toolbar_panel
            and "CohDet" in main_analysis_toolbar_panel
            and "TolCmp" in main_analysis_toolbar_panel
            and "results_table" in main_information_panel
            and "Property" in main_information_panel,
        ),
        (
            "Main optimization panel lives outside layout_editor",
            "MainOptimizationPanel(self, operand_specs=OPERAND_REGISTRY.values())" in main_optimization_factory
            and "self._main_optimization_panel().build(parent)" in build_optimization_panel
            and "Start Optimization" in main_optimization_panel
            and "Check Backend" in main_optimization_panel
            and "optimization_workers_var" in main_optimization_panel
            and "merit_mode_list" in main_optimization_panel
            and "operand_weight_vars" in main_optimization_panel
            and "MTF @ freq" in main_optimization_panel,
        ),
        (
            "Main paraxial/Gaussian dialogs live outside layout_editor",
            "MainParaxialAnalysisDialogs(self, short_error_message=_short_error_message)" in main_paraxial_analysis_factory
            and "self._main_paraxial_analysis_dialogs().open_gaussian_beam_report()" in open_gaussian_report
            and "self._main_paraxial_analysis_dialogs().open_paraxial_calculator()" in open_paraxial_calculator
            and "Paraxial Calculator" in main_paraxial_analysis_dialogs
            and "Gaussian Beam Report" in main_paraxial_analysis_dialogs
            and "Use Cavity Eigenmode" in main_paraxial_analysis_dialogs,
        ),
        (
            "Lens drawing dialogs live outside layout_editor",
            "MainLensDrawingDialogs(self, screenshot_dir=SCREENSHOT_DIR)" in main_lens_drawing_factory
            and "self._main_lens_drawing_dialogs()._open_lens_drawing_surface_properties_dialog(" in open_lens_drawing_properties
            and "self._main_lens_drawing_dialogs().export_lens_drawing()" in export_lens_drawing_wrapper
            and "Lens Drawing Surface Properties" in main_lens_drawing_dialogs
            and "Save JSON..." in main_lens_drawing_dialogs
            and "Export Lens Drawing" in main_lens_drawing_dialogs,
        ),
        (
            "Branch Gaussian Q dialog lives outside layout_editor",
            "MainBranchGaussianQDialog(self)" in main_branch_gaussian_q_factory
            and "self._main_branch_gaussian_q_dialog().open_branch_gaussian_q_report()" in open_branch_gaussian_q_report
            and "self._main_branch_gaussian_q_dialog()._refresh_branch_gaussian_q_report()" in refresh_branch_gaussian_q_report
            and "Branch Gaussian Q Report" in main_branch_gaussian_q_dialog
            and "Export Branch Gaussian Q CSV" in main_branch_gaussian_q_dialog
            and "branch_gaussian_q_table_values" in main_branch_gaussian_q_dialog,
        ),
        (
            "Detector Aperture Report dialog lives outside layout_editor",
            "MainDetectorApertureReportDialog(self)" in main_detector_aperture_factory
            and "self._main_detector_aperture_report_dialog().open_detector_aperture_report()" in open_detector_aperture_report
            and "self._main_detector_aperture_report_dialog()._refresh_detector_aperture_report()" in refresh_detector_aperture_report
            and "Detector Aperture Report" in main_detector_aperture_report_dialog
            and "Export Detector Aperture CSV" in main_detector_aperture_report_dialog
            and "detector_aperture_table_values" in main_detector_aperture_report_dialog,
        ),
        (
            "Source Illumination Report dialog lives outside layout_editor",
            "MainSourceIlluminationReportDialog(self)" in main_source_illumination_factory
            and "self._main_source_illumination_report_dialog().open_source_illumination_report()" in open_source_illumination_report
            and "self._main_source_illumination_report_dialog()._refresh_source_illumination_report()" in refresh_source_illumination_report
            and "Source Illumination Report" in main_source_illumination_report_dialog
            and "Export Source Illumination CSV" in main_source_illumination_report_dialog
            and "source_illumination_table_values" in main_source_illumination_report_dialog,
        ),
        (
            "Path Throughput Report dialog lives outside layout_editor",
            "MainBranchThroughputReportDialog(" in main_branch_throughput_factory
            and "analysis_path_filter_default=ANALYSIS_PATH_FILTER_DEFAULT" in main_branch_throughput_factory
            and "self._main_branch_throughput_report_dialog().open_branch_throughput_report()" in open_branch_throughput_report
            and "self._main_branch_throughput_report_dialog()._refresh_branch_throughput_report()" in refresh_branch_throughput_report
            and "Path Throughput Report" in main_branch_throughput_report_dialog
            and "Export Path Throughput CSV" in main_branch_throughput_report_dialog
            and "branch_throughput_table_values" in main_branch_throughput_report_dialog,
        ),
        (
            "Atmosphere controls and dialog live outside layout_editor",
            "MainAtmospherePanel(" in main_atmosphere_factory
            and "atmos_plot_mode_values=ATMOS_PLOT_MODE_VALUES" in main_atmosphere_factory
            and "self._main_atmosphere_panel().build_hidden_panel(parent)" in build_atmosphere_panel
            and "self._main_atmosphere_panel().open_settings_dialog()" in open_atmosphere_dialog
            and "self._main_atmosphere_panel().close_settings_dialog()" in close_atmosphere_dialog
            and "ATMOSPHERE_CONTROL_SPECS" in main_atmosphere_panel
            and "Apply + Atmos" in main_atmosphere_panel
            and "atmosphere_summary_var" in main_atmosphere_panel,
        ),
        (
            "Coating/material dialog lives outside layout_editor",
            "MainCoatingMaterialDialog(" in main_coating_dialog_factory
            and "coating_presets=COATING_PRESETS" in main_coating_dialog_factory
            and "metal_catalog_dir=METAL_CATALOG_DIR" in main_coating_dialog_factory
            and "validate_advanced_surface_inputs=_validate_advanced_surface_inputs" in main_coating_dialog_factory
            and "self._main_coating_material_dialog().open(row_index)" in open_coating_dialog
            and "Coating / Material" in main_coating_dialog
            and "Load CSV..." in main_coating_dialog
            and "CoatingMet" in main_coating_dialog
            and "Validation passed." in main_coating_dialog,
        ),
        (
            "Diffuse/BRDF dialog lives outside layout_editor",
            "MainDiffuseScatterDialog(" in main_diffuse_dialog_factory
            and "diffuse_object_surface=DIFFUSE_OBJECT_SURFACE" in main_diffuse_dialog_factory
            and "diffuse_scatter_default_settings=DIFFUSE_SCATTER_DEFAULT_SETTINGS" in main_diffuse_dialog_factory
            and "validate_diffuse_scatter_settings=_validate_diffuse_scatter_settings" in main_diffuse_dialog_factory
            and "self._main_diffuse_scatter_dialog().open(row_index)" in open_diffuse_dialog
            and "Diffuse / BRDF" in main_diffuse_dialog
            and "pySCATMECH BRDF" in main_diffuse_dialog
            and "Guided target surface" in main_diffuse_dialog
            and "Validation passed." in main_diffuse_dialog,
        ),
        (
            "Surface Shape Builder dialog lives outside layout_editor",
            "MainSurfaceShapeBuilderDialog(" in main_surface_shape_factory
            and "attachment_dir=ATTACHMENT_DIR" in main_surface_shape_factory
            and "optical_solid_filetypes=OPTICAL_SOLID_FILETYPES" in main_surface_shape_factory
            and "validate_advanced_surface_inputs=_validate_advanced_surface_inputs" in main_surface_shape_factory
            and "self._main_surface_shape_builder_dialog().open(row_index)" in open_surface_shape_builder
            and "Surface Shape Builder" in main_surface_shape_dialog
            and "Aperture / UDA / Mask" in main_surface_shape_dialog
            and "Optical CAD/STL" in main_surface_shape_dialog
            and "Refresh Preview" in main_surface_shape_dialog,
        ),
        (
            "Beam Splitter settings dialog lives outside layout_editor",
            "MainBeamSplitterDialog(" in main_beam_splitter_factory
            and "beam_splitter_surface=BEAM_SPLITTER_SURFACE" in main_beam_splitter_factory
            and "beam_splitter_split_modes=BEAM_SPLITTER_SPLIT_MODES" in main_beam_splitter_factory
            and "beam_splitter_coating_for_settings=_beam_splitter_coating_for_settings" in main_beam_splitter_factory
            and "self._main_beam_splitter_dialog().open(row_index)" in open_beam_splitter_dialog
            and "Beam Splitter can spawn deterministic" in main_beam_splitter_dialog
            and "Fresnel P/S mode" in main_beam_splitter_dialog
            and "Validation passed:" in main_beam_splitter_dialog,
        ),
        (
            "Error Map dialog lives outside layout_editor",
            "MainErrorMapDialog(" in main_error_map_factory
            and "attachment_dir=ATTACHMENT_DIR" in main_error_map_factory
            and "load_error_map_file=_load_error_map_file" in main_error_map_factory
            and "validate_error_map=_validate_error_map" in main_error_map_factory
            and "self._main_error_map_dialog().open(row_index)" in open_error_map_dialog
            and "Error_map = [X, Y, Z, SPACE]" in main_error_map_dialog
            and "Import..." in main_error_map_dialog
            and "Validation passed: no error map." in main_error_map_dialog,
        ),
        (
            "Advanced Surface dialog lives outside layout_editor",
            "MainAdvancedSurfaceDialog(" in main_advanced_surface_factory
            and "advanced_row_shape_fields=ADVANCED_ROW_SHAPE_FIELDS" in main_advanced_surface_factory
            and "advanced_surface_field_groups=ADVANCED_SURFACE_FIELD_GROUPS" in main_advanced_surface_factory
            and "validate_advanced_surface_inputs=_validate_advanced_surface_inputs" in main_advanced_surface_factory
            and "self._main_advanced_surface_dialog().open(row_index)" in open_advanced_surface_dialog
            and "Shape Params" in main_advanced_surface_dialog
            and "Optimize conic k" in main_advanced_surface_dialog
            and "Advanced Surface Validation" in main_advanced_surface_dialog,
        ),
        (
            "Specialized surface settings dialogs live outside layout_editor",
            "MainSurfaceSettingsDialogs(" in main_surface_settings_factory
            and "galvo_scan_overlay_key=GALVO_SCAN_OVERLAY_KEY" in main_surface_settings_factory
            and "parse_float_sequence_text=_parse_float_sequence_text" in main_surface_settings_factory
            and "self._main_surface_settings_dialogs().open_galvo_scan_overlay_settings(index)" in open_galvo_settings
            and "self._main_surface_settings_dialogs().open_surface_additional_settings(index)" in open_surface_additional_settings
            and "self._main_surface_settings_dialogs().open_grating_settings_editor(row_index)" in open_grating_settings
            and "Galvo Scan Overlay" in main_surface_settings_dialogs
            and "Grating Settings" in main_surface_settings_dialogs
            and "Pitch [um] must be non-zero." in main_surface_settings_dialogs,
        ),
        (
            "Main table context menu lives outside layout_editor",
            "MainContextMenu(" in main_context_menu_factory
            and "fields=FIELDS" in main_context_menu_factory
            and "coating_preset_names=COATING_PRESET_NAMES" in main_context_menu_factory
            and "element_arm_role_values=ELEMENT_ARM_ROLE_VALUES" in main_context_menu_factory
            and "self._main_context_menu().show_context_menu(event)" in show_context_menu
            and "Convert Type" in main_context_menu
            and "Shape / Aperture" in main_context_menu
            and "Coating / Polarization" in main_context_menu
            and "Path assignment" in main_context_menu,
        ),
        (
            "Scene and element settings dialogs live outside layout_editor",
            "MainSceneElementDialogs(" in main_scene_element_factory
            and "normalize_detector_settings=_normalize_detector_settings" in main_scene_element_factory
            and "scene_target_editor_kind_choices=SCENE_TARGET_EDITOR_KIND_CHOICES" in main_scene_element_factory
            and "element_branch_selector_values=ELEMENT_BRANCH_SELECTOR_VALUES" in main_scene_element_factory
            and "self._main_scene_element_dialogs().open_detector_settings(row_index)" in open_detector_dialog
            and "self._main_scene_element_dialogs().open_scene_target_editor(row_index)" in open_scene_target_dialog
            and "self._main_scene_element_dialogs().open_selected_path_local_pose_editor()" in open_path_pose_dialog
            and "self._main_scene_element_dialogs().open_element_settings()" in open_element_dialog
            and "Detector Settings" in main_scene_element_dialogs
            and "Scene Target" in main_scene_element_dialogs
            and "Path-Local Pose" in main_scene_element_dialogs
            and "Element Settings" in main_scene_element_dialogs,
        ),
        (
            "Scene Source Manager dialog lives outside layout_editor",
            "MainSceneSourceManagerDialog(" in main_scene_source_factory
            and "source_model_values=SOURCE_MODEL_VALUES" in main_scene_source_factory
            and "source_row_order_default=SOURCE_ROW_ORDER_DEFAULT" in main_scene_source_factory
            and "normalize_source_row_order=normalize_source_row_order" in main_scene_source_factory
            and "self._main_scene_source_manager_dialog().open_scene_source_manager(" in open_scene_source_manager
            and "Scene Source Manager" in main_scene_source_dialog
            and "Add From Source Panel" in main_scene_source_dialog
            and "Use Source Panel Only" in main_scene_source_dialog,
        ),
        (
            "Stock lens importer dialog lives outside layout_editor",
            "MainStockLensImporterDialog(" in main_stock_lens_factory
            and "available_stock_lens_catalogs=_available_stock_lens_catalogs" in main_stock_lens_factory
            and "load_stock_lens_catalog=_load_stock_lens_catalog" in main_stock_lens_factory
            and "stock_lens_summary=_stock_lens_summary" in main_stock_lens_factory
            and "self._main_stock_lens_importer_dialog().open_stock_lens_importer(" in open_stock_lens_importer
            and "Import Stock Lens" in main_stock_lens_dialog
            and "Add Stock Lens to Path" in main_stock_lens_dialog
            and "Import Selected" in main_stock_lens_dialog,
        ),
        (
            "Open 3D renders editable table Thickness dimensions",
            "_actor_thickness_dimension_map" in init
            and "_thickness_dimension_actor_map" in init
            and "pick_thickness_dimension" in add_mesh_actor
            and "_register_thickness_dimension_actor" in add_mesh_actor
            and "_add_thickness_dimension_overlays(system, scene_bundle)" in refresh
            and "thickness dimensions=" in refresh
            and "show_physical_distances_var" in thickness_dimensions
            and "_surface_reference_world_point(row_index" in thickness_dimensions
            and "_surface_reference_world_point(row_index + 1" in thickness_dimensions
            and "self.arrow_mesh(" in thickness_dimensions
            and "pv.Cone" in thickness_arrow
            and "billboard_text_actor_cls" in inspect.getsource(Open3DThicknessDimensionService.__init__)
            and "_register_thickness_dimension_actor" in thickness_label
            and "Thickness" in top_controls_source
            and "show_physical_distances_var" in top_controls_source,
        ),
        (
            "Reusable Tk tooltip lives outside layout_editor",
            WidgetTooltip.__module__.endswith(".widgets.tooltips")
            and "wm_attributes(\"-type\", \"tooltip\")" in widget_tooltip,
        ),
        (
            "Open 3D Thickness dimension clicks edit only the selected row thickness",
            "_actor_thickness_dimension_map.get(actor_key)" in pick
            and "GetViewProp" in pick
            and "_edit_open3d_thickness_dimension" in pick
            and "simpledialog.askfloat" in thickness_edit
            and "self.editor.rows[row_index].thickness = next_value" in thickness_edit
            and "_sync_table()" in thickness_edit
            and "_select_table_row(row_index)" in thickness_edit
            and "Other table thickness values are unchanged" in thickness_edit
            and "refresh_from_editor(force_retrace=True)" in thickness_edit,
        ),
        (
            "Open 3D STEP promotion refreshes and highlights the created row",
            "promote_imported_step_to_optical_solid_row" in step_promote_helper
            and "highlight_row(row_index)" in step_promote_helper
            and "Hold the promoted solid to move it" in step_promote,
        ),
        (
            "Open 3D STEP promotion and face assignment dirty the 2D refresh path",
            "_stl_placement_dirty = True" in step_promote_helper
            and "_stl_placement_dirty = True" in context_assign
            and "_stl_placement_dirty = True" in context_promote_assign,
        ),
        (
            "STEP promotion writes a file-backed optical solid row",
            "_transformed_imported_step_mesh_for_label" in editor_step_promote
            and "Solid_3d_stl" in editor_step_promote
            and "_optical_stl_solid_row" in editor_step_promote
            and "StepOverlayPromotion" in editor_step_promote,
        ),
        (
            "STEP promotion preserves scene placement metadata",
            "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_step_promote
            and "promotion_source" in editor_step_promote
            and "center_world" in editor_step_promote,
        ),
        ("Open 3D STEP carry has explicit drop state", "_step_carry_active_label = None" in step_carry_drop and "_step_carry_follow_state = None" in step_carry_drop and "STEP carry dropped" in step_carry_drop),
        (
            "Open 3D Esc cancels active carry and pick operations",
            '"<Escape>"' in init
            and "KeyPressEvent" in init
            and "cancel_active_3d_operation()" in key_press
            and "_cancel_step_carry_hold_timer()" in operation_cancel
            and "_step_carry_follow_state = None" in operation_cancel
            and "_placement_target_pick_mode = False" in operation_cancel
            and "_cad_axis_pick_any = False" in operation_cancel,
        ),
        (
            "Open 3D Delete/Backspace deletes selected STEP elements",
            '"<Delete>"' in init
            and '"<BackSpace>"' in init
            and "delete_selected_step()" in key_press
            and "KP_Delete" in key_press
            and "delete_selected_step()" in delete_step_event
            and "_open3d_step_state_service()" in delete_step
            and "resolve_delete_selection(" in delete_step
            and "_picked_row_index" in delete_step
            and "delete_optical_step_rows(selection.row_indices)" in delete_step
            and "promoted_step_row_indices" in open3d_step_state_service,
        ),
        (
            "Open 3D Esc and blank clicks clear selected components",
            "_clear_open3d_selection(render=True)" in operation_cancel
            and "_clear_open3d_selection(render=False)" in operation_cancel
            and "_clear_open3d_selection(render=False)" in pick
            and "_selected_step_label = None" in clear_selection
            and "_selected_step_feature_label" in clear_selection
            and "_set_step_highlight(None)" in clear_selection
            and "_remove_step_rotation_handle_actors()" in clear_selection
            and "RemoveActor(actor)" in remove_step_handles,
        ),
        (
            "Open 3D Esc reverts uncommitted free carry movement",
            "_restore_history_state(restore_state)" in operation_cancel
            and "_history_pending_state = None" in operation_cancel
            and "reverted free carry movement" in operation_cancel,
        ),
        ("STEP transform applies persistent 3D placement offset", "placement_offset_xyz" in editor_step_transform and "aligned[:, :3] += placement_offset" in editor_step_transform),
        ("STEP handler survives 3D refresh", "_update_step_rotation_handler_state" in refresh and "_add_step_rotation_handles" in refresh),
        ("duplicate STEP Rotate toolbar menu removed", "STEP Rotate" not in init),
        ("active mode badge covers STEP centering", "CENTER STEP AXIS" in badge_text),
        ("active mode badge covers Obj->LED", "OBJ -> LED" in badge_text),
        ("active mode badge covers Center Row->Optical Axis", "CENTER ROW -> OPTICAL AXIS" in badge_text),
        ("active mode badge covers Snap Row->Target", "SNAP ROW -> TARGET" in badge_text),
        ("active mode badge covers Orient Row->Target", "ORIENT ROW -> TARGET" in badge_text),
        ("active mode badge covers Orient Row->Ray", "ORIENT ROW -> RAY" in badge_text),
        ("active mode badge covers Source Target", "SOURCE TARGET" in badge_text),
        (
            "Open 3D passive ray selection is disabled by default",
            "ray_pick_enabled_var = tk.BooleanVar(value=False)" in init
            and 'text="Pick rays"' in init_with_top_controls
            and "_on_ray_pick_changed" in init_with_top_controls
            and "return bool(self.ray_pick_enabled_var.get())" in ray_pick_enabled
            and "Ray picking disabled" in ray_pick_changed,
        ),
        (
            "Open 3D ray clicks only open Ray Inspector when Pick rays is enabled",
            "if not self._ray_pick_enabled():" in pick
            and "Ray picking is disabled" in pick
            and "self.editor._select_ray_inspector_ray(int(ray_index))" in pick
            and pick.find("if not self._ray_pick_enabled():") < pick.find("self.editor._select_ray_inspector_ray(int(ray_index))"),
        ),
        (
            "Ray Inspector keeps wide ray fields inside a horizontally scrollable table",
            'window.geometry("1180x660")' in ray_inspector
            and "ray_x_scroll" in ray_inspector
            and "xscrollcommand=ray_x_scroll.set" in ray_inspector,
        ),
        (
            "STEP surface-to-axis picking hides regular rays before axis selection",
            "_hide_regular_rays_for_center_axis_pick()" in step_normal_axis_start
            and "_hide_regular_rays_for_center_axis_pick()" in step_surface_center_axis_start
            and "show_rays_var.set(False)" in center_row_axis_hide,
        ),
        ("active mode badge is a VTK overlay", "_add_renderer_view_prop(actor)" in badge_update and "vtkTextActor" in badge_update),
        ("active mode badge survives 3D refresh", "_update_mode_badge" in refresh),
        ("embedded STL placement toolbar removed", "stl_toolbar" not in init and "placement toolbar" not in init),
        (
            "CAD/STL selection does not open placement handler",
            "show_stl_placement_handler(int(row_index))" not in pick
            and "_update_stl_placement_handler_state()" in pick
            and "Right-click a face to assign physics" in pick,
        ),
        ("CAD/STL handler is embedded side panel", "CAD/STL placement side panel" in stl_handler and "tk.Toplevel" not in stl_handler),
        ("CAD/STL handler exposes axis fit", "Fit local axis to +Z" in stl_handler and "Fit Axis" in stl_handler),
        ("CAD/STL handler exposes repeated user-selected rotations", "-Rot" in stl_handler and "+Rot" in stl_handler and "_rotation_handle_step_deg()" in stl_handler),
        ("CAD/STL handler exposes placement finalization", "Done -> 2D" in stl_handler and "Front On Row" in stl_handler),
        ("CAD/STL handler stays current after pose changes", "_update_stl_placement_handler_state" in stl_refresh),
        ("Open 3D toolbar exposes Snapshot", "Snapshot" in init_with_top_controls and "save_snapshot" in init_with_top_controls),
        (
            "Open 3D face assignment has persistent non-pickable face tints",
            "_add_optical_solid_assigned_face_overlays" in refresh
            and "assigned face overlays" in refresh
            and "triangle_indices" in assigned_face_triangles
            and "flat_shading=True" in assigned_face_overlays
            and "backface_culling=False" in assigned_face_overlays
            and "extract_feature_edges" not in assigned_face_overlays,
        ),
        (
            "Open 3D imported optical solids default to Uncoated interaction faces",
            "OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT" in default_uncoated
            and "OPTICAL_SOLID_FACE_PORT_INTERACTION" in default_uncoated
            and "OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED" in default_uncoated
            and "_default_uncoated_optical_solid_face_metadata(path)" in inspect.getsource(KrakenLayoutEditor._optical_stl_solid_row),
        ),
        (
            "Open 3D hover badge reports face assignment physics",
            "vtkTextActor" in hover_status
            and "_hover_status_actor" in init
            and "_face_hover_status_text" in mouse_move
            and "_optical_solid_face_port_role" in face_hover_status,
        ),
        (
            "Open 3D direct face assignment suppresses normal-arrow marker actors",
            "face_role_markers = 0" in refresh
            and "_add_optical_solid_face_role_overlays(system)" not in refresh,
        ),
        (
            "Open 3D CAD/STL faces hover before right-click assignment",
            "right-click to assign surface physics" in mouse_move
            and "_hover_overlay_for_feature" in mouse_move
            and "_hover_overlay_for_row_face" in mouse_move
            and "_row_face_ray_pick_for_display_xy" in mouse_move
            and "optical_solid_face_record_for_mesh_cell" in mouse_move
            and "optical_solid_face_record_at_world_point" in mouse_move
            and '("row", actor_key, "ray", through_face_id)' in mouse_move,
        ),
        (
            "Open 3D transparent CAD solids support through-body internal face picking",
            "_display_to_world_3d(display_xy, 0.0)" in display_pick_ray
            and "_display_to_world_3d(display_xy, 1.0)" in display_pick_ray
            and "pick_face_from_ray(" in row_face_ray_pick
            and "pick_face_from_ray(" in step_face_ray_pick
            and "prefer_internal=True" in row_face_ray_pick
            and "prefer_internal=True" in step_face_ray_pick
            and "Toolkit pickers" in face_ray_pick_service
            and "internal" in face_ray_pick_service,
        ),
        (
            "Open 3D row face assignment uses the picked face id directly",
            "face_id: str" in assign_row_face_context
            and "optical_solid_face_record_for_mesh_cell" in right_click_menu
            and "_row_face_ray_pick_for_display_xy" in right_click_menu
            and "_traced_row_face_hit_near_display_xy" in right_click_menu
            and "_ray_event_mesh_face_id" in traced_face_context_pick
            and "distance_px" in traced_face_context_pick
            and "assign_optical_solid_face_function(" in assign_row_face_context
            and "assign_optical_solid_face_function_at_world_point(" in assign_row_face_context
            and "picked_face_id=face_id" in right_click_menu,
        ),
        (
            "Open 3D default source launch is collimated unless a cone is requested",
            'source_cone_angle_var = tk.StringVar(value="0.0")' in main_source_panel
            and '_set_optional_var("source_cone_angle_var", "0.0")' in reset_runtime_state
            and "else 0.0" in current_source_cone,
        ),
        (
            "Open 3D transient STEP face assignment carries picked face id through promotion",
            "optical_solid_step_overlay_face_record_at_world_point" in right_click_menu
            and "_step_face_ray_pick_for_display_xy" in right_click_menu
            and "picked_face_id=face_id" in right_click_menu
            and "face_id: str" in context_promote_assign
            and "assign_optical_solid_face_function(" in context_promote_assign,
        ),
        (
            "Open 3D normal-axis snap keeps picked axis highlighted",
            "_set_optical_axis_highlight(axis_id)" in step_normal_axis_apply,
        ),
        (
            "Open 3D optical-axis highlight is a solid overlay",
            "pv.lines_from_points" in optical_axis_highlight
            and "line_width=7.0" in optical_axis_highlight
            and "_optical_axis_highlight_actor" in optical_axis_highlight
            and "selected_axis_id = self._picked_optical_axis_id" in refresh
            and "_set_optical_axis_highlight(selected_axis_id)" in refresh,
        ),
        (
            "Open 3D refresh does not clear scene on empty surface rebuild",
            "rebuilt trace produced no surface meshes" in refresh
            and "previous_actor_count > 0" in refresh
            and "return" in refresh.split("rebuilt trace produced no surface meshes", 1)[1].split("RemoveAllViewProps", 1)[0],
        ),
        (
            "Open 3D refresh reuses previous meshes for suspicious trace refreshes",
            "_last_valid_surface_mesh_items" in refresh
            and "missing_file_backed_rows" in refresh
            and "suspicious_sparse_rebuild" in refresh
            and "3D refresh reused previous surface meshes" in refresh,
        ),
        (
            "Open 3D scene surface actors are double-sided",
            "pick_row_index=mesh_item.row_index" in refresh
            and "backface_culling=False" in refresh.split("for mesh_item in mesh_items:", 1)[1].split("assigned_face_overlays", 1)[0],
        ),
        (
            "Open 3D STEP promotion clears stale overlay interaction state",
            "_clear_step_overlay_interaction_state(label)" in step_promote_helper
            and "refresh_open_3d=False" in step_promote_helper
            and "_selected_step_label = None" in clear_step_overlay_state
            and "_close_step_rotation_handler()" in clear_step_overlay_state,
        ),
        (
            "Open 3D toolbar uses categorized rows",
            "toolbar_container" in init_with_top_controls and "view_toolbar" in init_with_top_controls and "scene_toolbar" in init_with_top_controls,
        ),
        (
            "Open 3D starts in the active 2D projection camera",
            "_camera_preset_for_display_orientation()" in init
            and '("YZ", "zy")' in init_with_top_controls
            and 'ttk.Label(view_toolbar, text="Camera")' in init_with_top_controls
            and "self.set_camera_preset(value)" in init_with_top_controls
            and '"zy"' in open3d_display_camera
            and '"xz"' in open3d_display_camera
            and '"xy"' in open3d_display_camera,
        ),
        (
            "legacy 3D fallback starts in the active 2D projection camera",
            "_legacy_3d_camera_preset_from_display_orientation" in legacy_configure
            and '"yz"' in legacy_display_camera
            and '"xz"' in legacy_display_camera
            and '"top"' in legacy_display_camera,
        ),
        (
            "Open 3D scene toolbar groups dense commands",
            '"CAD / target"' in init_with_top_controls
            and 'text="Place"' in init_with_top_controls
            and 'text="Orient"' in init_with_top_controls
            and "ttk.Menubutton" in init_with_top_controls,
        ),
        (
            "Open 3D has a right-docked STEP element browser",
            "_build_step_admin_right_panel" in init
            and '"STEP Elements"' in init
            and "columnconfigure(2, weight=0)" in init
            and "columnspan=3" in init_with_top_controls
            and "refresh_step_admin_panel" in refresh,
        ),
        (
            "STEP browser groups elements by CAD role",
            "ttk.Treeview" in step_admin_source
            and '"Optical Element"' in step_admin_source
            and '"Imaging Lens"' in step_admin_source
            and '"Camera / Detector"' in step_admin_source
            and '"overlay:"' in step_admin_source
            and '"row:"' in step_admin_source,
        ),
        (
            "STEP browser selection drives Open 3D highlight and table selection",
            "select_step_overlay_from_admin" in step_admin_source
            and "select_promoted_step_row_from_admin" in step_admin_source
            and "iid == self._selected_item_id" in step_admin_source
            and "iid == self._current_browser_selection_iid()" in step_admin_source
            and "_set_step_highlight(label)" in step_admin_overlay_select
            and "show_step_rotation_handler(label)" in step_admin_overlay_select
            and "_step_carry_active_label = label" not in step_admin_overlay_select
            and "_select_table_indices([row_index]" in step_admin_promoted_select
            and "_sync_surface_selection(row_index)" in step_admin_promoted_select
            and "highlight_row(row_index)" in step_admin_promoted_select,
        ),
        (
            "STEP browser exposes selected-element property actions",
            '"Properties"' in step_admin_source
            and '"Selected Element"' in step_admin_source
            and "start_selected_step_carry" in step_admin_source
            and "accept_selected_step_placement" in step_admin_source
            and "promote_selected_step_to_optical_solid_row" in step_admin_source
            and "delete_selected_step" in step_admin_source
            and "open_selected_optical_faces" in step_admin_source,
        ),
        ("Open 3D Snapshot uses Save As dialog", "filedialog.asksaveasfilename" in snapshot),
        ("Open 3D Snapshot defaults to attachment directory", "initialdir=str(ATTACHMENT_DIR)" in snapshot),
        ("Open 3D Snapshot has a short default filename", 'initialfile="3D.png"' in snapshot),
        ("Open 3D Snapshot uses VTK PNG capture", "vtkWindowToImageFilter" in snapshot and "vtkPNGWriter" in snapshot),
        ("Open 3D refresh reuses current SceneBundle when valid", "_current_preview_scene_trace" in open3d_refresh_service),
        (
            "Open 3D fallback traces the 3D sampling mode when it rebuilds locally",
            "_preview_3d_sampling_mode()" in open3d_refresh_service
            and "_preview_2d_sampling_mode()" not in open3d_refresh_service,
        ),
        (
            "Open 3D sync keeps supplied 2D SceneBundle instead of rebuilding",
            "if system is None or rays is None or scene_bundle is None" in open3d_refresh_service
            and "_build_preview_system_rays_bundle" in open3d_refresh_service,
        ),
        ("Open 3D ray-on leaves Object/Image reference disks translucent", 'row_surface in {"Object", "Image"}' in refresh and "mesh_opacity = min(mesh_opacity, 0.22)" in refresh),
        ("2D refresh uses shared 3D scene sampling", "_preview_scene_sampling_mode()" in editor_refresh_plot),
        ("2D refresh no longer traces display_slice as the main layout simulation", 'sampling_mode="display_slice"' not in editor_refresh_plot),
        (
            "saved 2D keeps an already-traced raykeeper instead of retracing a different sample",
            "has_traced_rays" in saved_layout_figure
            and "if not has_traced_rays" in saved_layout_figure
            and "_preview_2d_sampling_mode()" in saved_layout_figure,
        ),
        ("Open 3D sync receives the same SceneBundle as 2D", "scene_bundle=bundle" in editor_refresh_plot and "refresh_scene(" in open3d_refresh_service),
        ("shared scene sampling supports full-pupil, world-envelope, and explicit source-cone-world modes", "full_pupil" in preview_sampling and "world_envelope" in preview_sampling and "source_cone_world" in trace_preview_rays),
        (
            "Pupil/field source cone is not auto-promoted into a physical point cone",
            'return "world_envelope"' in preview_sampling
            and 'return "source_cone_world"' not in preview_sampling
            and "_build_default_finite_cone_world_bundles" in trace_preview_rays,
        ),
        (
            "Open 3D forced refresh uses 3D sampling instead of the 2D display slice",
            "_preview_3d_sampling_mode()" in open3d_refresh_service
            and "_preview_2d_sampling_mode()" not in open3d_refresh_service,
        ),
        (
            "promoted optical solid rows support direct hold-drag movement",
            "_row_carry_index_from_current_pick" in bindings
            and "_row_carry_drag_state" in bindings
            and "_file_backed_stl_row_at" in row_carry_pick
            and "translate_scene_row_pose_vector" in row_carry_apply
            and "record_history=False" in row_carry_apply
            and "_set_step_hover_outline(None, None, render=False)" in row_carry_activate
            and "_set_step_hover_outline(None, None, render=False)" in row_carry_apply
            and "_set_step_hover_outline(None, None, render=False)" in row_carry_finish
            and "track_row_index" in refresh
            and "_sync_table()" in row_carry_finish
            and "last_translate_mode" in editor_row_translate_vector,
        ),
        (
            "promoted optical solid display uses light body and strong edges",
            "row_index in file_backed_rows" in refresh
            and "mesh_opacity = min(max(mesh_opacity, 0.14), 0.28)" in refresh
            and "_solid_edge_color_from_body" in refresh
            and "_solid_silhouette_edge_color" in refresh
            and "if row_index in file_backed_rows:" in refresh
            and "continue" in refresh
            and "line_width=5.0" in refresh
            and "line_width=3.2" in refresh
            and "line_width=3.4" in legacy_open_3d,
        ),
        ("non-sequential scene bundles do not install YZ-only branch display overrides", 'not bool(trace_state.get("use_nonseq"))' in editor_build_scene_bundle and "_branch_output_display_path_overrides(rays)" in editor_build_scene_bundle),
        ("Open 3D ray records preserve terminal status", "ray_path_terminal_status_from_events(path)" in scene_ray_records),
        (
            "Open 3D viewport reports ray terminal status groups",
            "_trace_summary_actor" in init
            and "terminal_counts" in refresh
            and "bounded_ray_count" in refresh
            and "suppressed_endpoint_count" in refresh
            and "Ray terminals:" in trace_summary_text
            and "SetDisplayPosition(16, max(int(height) - 58, 16))" in trace_summary,
        ),
        (
            "Open 3D terminal summary reports final CAD face and physics action",
            "terminal_face_counts" in trace_summary_text
            and "last hit " in trace_summary_text
            and "terminal_sequence_counts" in trace_summary_text
            and "Path: " in trace_summary_text
            and "_ray_path_terminal_face_summary(ray_path)" in refresh
            and "_ray_path_surface_sequence_summary(ray_path)" in refresh
            and "mesh_face_id" in trace_terminal_face_summary
            and "event_type" in trace_terminal_face_summary,
        ),
        (
            "Open 3D optical-axis guides include only traced chief-ray exit segments",
            "physical_paths" in optical_axis_records
            and "_dotted_axis_records_from_ray_path(chief, bounds)" in optical_axis_records
            and "_dotted_axis_mesh_from_points(points[:, :3])" in optical_axis_overlays
        ),
        (
            "Generated traced axes can drive STEP face-normal cascade placement",
            "segment_midpoint" in editor_axis_record_frame
            and "segment_direction" in editor_axis_record_frame
            and "_step_overlay_face_metadata" in editor_step_overlay_axis_snap
            and "snap_step_feature_normal_to_optical_axis" in editor_step_overlay_axis_snap
            and '"axis_role"' in editor_step_overlay_axis_snap,
        ),
        ("Open 3D missed detector lines use status styling", "missed_detector" in ray_terminal_style and "line_opacity" in ray_terminal_style),
        ("Open 3D escaped rays preserve source/wavelength line color", '"escaped" else 0.74' in ray_terminal_style and '{"absorbed", "stopped"}' in ray_terminal_style),
        (
            "Open 3D refresh gates terminal endpoint disks behind terminal diagnostics",
            "_should_draw_3d_terminal_endpoint(" in refresh
            and "show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get())" in refresh
            and "ray_display_suppressed_diagnostic_endpoints" in refresh
            and 'status == "hit_detector"' in should_draw_endpoint
            and "return bool(show_terminal_diagnostics)" in should_draw_endpoint
            and 'status in {"absorbed", "stopped"}' in should_draw_endpoint,
        ),
        (
            "legacy 3D refresh gates stopped/absorbed endpoint disks behind terminal diagnostics",
            "_should_draw_3d_terminal_endpoint(" in legacy_replace_rays
            and "show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get())" in legacy_replace_rays
            and "suppressed_endpoint_count" in legacy_replace_rays,
        ),
        (
            "2D and Open 3D share escaped-tail and detector-miss display capping",
            "bounded_ray_points_for_scene_display(" in bounded_ray_display
            and "max_terminal_length" in shared_bounded_ray_display
            and '"escaped"' in shared_bounded_ray_display
            and '"missed_detector"' in shared_bounded_ray_display,
        ),
        (
            "2D and Open 3D share the same scene envelope for display capping",
            "scene_display_center_radius(scene_bundle)" in refresh
            and "surface_meshes" in shared_scene_bounds
            and "targets" in shared_scene_bounds,
        ),
        ("embedded 3D endpoint actors remain available for physical terminals", "pv.Sphere" in endpoint_actor),
        ("Open 3D renders scene detector active footprints", "_add_scene_detector_overlays(" in refresh and "scene_target_active_footprint_polylines" in editor_detector_overlays),
        ("Open 3D renders plane-preserving missed-detector projection crosshairs", "_detector_miss_crosshair_polylines_for_display" in editor_detector_overlays and "detector_miss_crosshair" in editor_detector_overlays),
        (
            "Open 3D keeps detector footprints and miss crosshairs separately opt-in",
            "include_footprints=bool(self.show_detector_overlays_var.get())" in refresh
            and "include_miss_crosshairs=bool(self.show_terminal_diagnostics_var.get())" in refresh
            and "if bool(include_footprints):" in editor_detector_overlays
            and "if bool(include_miss_crosshairs):" in editor_detector_overlays,
        ),
        ("embedded 3D detector overlays are line meshes", "pv.lines_from_points" in detector_overlays and "line_width" in detector_overlays),
        ("legacy 3D includes detector overlays", "_scene_detector_overlay_specs(" in legacy_open_3d and "cap_miss_crosshairs_to_scene=True" in legacy_open_3d),
        ("Open 3D renders row-backed placement handle state", "self._scene_placements_for_3d(scene_bundle)" in placement_grid and "grid_spacing_mm" in placement_grid),
        ("Open 3D suppresses visible placement grid planes", "_scene_placement_grid_mesh(" not in placement_grid and "Placement handles:" in placement_grid),
        ("Open 3D placement handles are contextual or explicitly enabled", "_show_scene_placement_handles()" in refresh and "_stl_placement_panel_visible()" in show_scene_placement_handles),
        ("Open 3D placement status is a VTK overlay", "vtkTextActor" in placement_grid_status and "Placement handles:" in placement_grid),
        ("Open 3D refresh reports placement grid count", "placement_grid_lines" in refresh and "_update_placement_grid_status" in refresh),
        ("Open 3D placement handles are pickable scene actors", "pick_placement_move" in placement_handles and "_actor_placement_move_map" in pick),
        ("Open 3D placement handles write through row pose service", "translate_scene_row_pose" in placement_handle_pick),
        ("placement translate service writes Desp and ScenePlacement metadata", "desp_x" in editor_translate and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_translate),
        ("Open 3D placement rotation handles are pickable scene actors", "pick_placement_rotate" in placement_rotate_handles and "_actor_placement_rotate_map" in pick),
        ("Open 3D placement rotation handles write through world-axis row pose service", "rotate_scene_row_pose_world_axis" in placement_rotate_pick),
        ("placement rotate service writes Tilt and ScenePlacement metadata", "tilt_x" in editor_rotate and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_rotate),
        ("Open 3D placement drag starts from picked handle actors", "_placement_drag_state_from_current_pick()" in bindings and "_placement_handle_info_for_actor_key" in placement_drag_start),
        ("Open 3D placement drag suppresses camera drag while active", "_apply_placement_drag_motion(dx, dy)" in bindings and "_rotate_camera_fixed_drag(dx, dy)" in bindings),
        ("Open 3D placement drag writes through row pose services", "translate_scene_row_pose" not in placement_drag and "_apply_scene_placement_translate_handle" in placement_drag and "_apply_scene_placement_rotate_handle" in placement_drag),
        (
            "Open 3D toolbar exposes Center Row->Optical Axis",
            "Center Row->Optical Axis" in init_with_top_controls
            and "start_center_row_to_ray" in init_with_top_controls
            and "_hide_regular_rays_for_center_axis_pick()" in center_row_axis_start
            and "show_rays_var.set(False)" in center_row_axis_hide
            and "_file_backed_stl_row_at(int(row_index)) is None" in center_row_axis_start
            and "self._set_row_highlight(int(self._center_row_to_ray_index))" in center_row_axis_start
            and "_center_axis_source_pick_ignoring_axis_overlays(x, y)" in pick
            and "_actor_optical_axis_map" in center_axis_source_pick
            and "_actor_ray_map" in center_axis_source_pick
            and "PickableOff()" in center_axis_source_pick
            and "PickableOn()" in center_axis_source_pick
            and "\"step_label\"" in center_axis_source_pick
            and "_picked_feature_info_cached(actor, self._picker" in pick
            and "start_step_normal_axis_pick(step_label)" in pick
            and "_picked_feature_info_cached(actor, self._picker" in mouse_move
            and "self._set_row_highlight(int(row_index))" in mouse_move
            and "return True" in center_row_axis_visibility
            and "dotted_global_guide" in optical_axis_records
            and "_dotted_axis_mesh_from_points(points[:, :3])" in optical_axis_overlays
            and "_should_draw_optical_axis_overlays()" in refresh
            and "_mouse_move_due()" in mouse_move
            and "time.monotonic()" in mouse_move_due
            and "_step_feature_cache" in step_feature_cache
            and "_kraken_row_select_style" in row_actor_highlight
            and "SetEdgeVisibility(1)" in row_actor_highlight
            and "_apply_center_row_to_optical_axis(axis_info)" in pick
            and "_optical_axis_info_near_display_xy((x, y)" in pick
            and "tolerance_px=28.0" in mouse_move
            and "center_surface_row_on_optical_axis" in center_row_axis_apply
            and "_ray_point_and_direction_on_surface_plane" in editor_center_row_axis,
        ),
        ("Open 3D toolbar exposes Snap Row->Target", "Snap Row->Target" in init_with_top_controls and "start_placement_target_pick" in init_with_top_controls),
        ("Snap Row->Target clears conflicting pick modes", "_source_target_pick_mode = False" in placement_target_start and "_center_row_to_ray_mode = False" in placement_target_start),
        ("Snap Row->Target suppresses placement-handle drag", "_placement_target_pick_mode" in placement_drag_start),
        ("Snap Row->Target writes through row pose service", "snap_scene_row_anchor_to_target" in placement_target_apply),
        ("target snap service writes Desp and ScenePlacement metadata", "desp_x" in editor_snap_target and "last_constraint_kind" in editor_snap_target and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_snap_target),
        ("Open 3D toolbar exposes Orient Row->Target", "Orient Row->Target" in init_with_top_controls and "start_placement_orient_pick" in init_with_top_controls),
        ("Orient Row->Target clears conflicting pick modes", "_source_target_pick_mode = False" in placement_orient_start and "_placement_target_pick_mode = False" in placement_orient_start),
        ("Orient Row->Target suppresses placement-handle drag", "_placement_orient_pick_mode" in placement_drag_start),
        ("Orient Row->Target writes through row pose service", "orient_scene_row_anchor_to_target" in placement_orient_apply),
        ("target orient service delegates to vector row pose service", "orient_scene_row_anchor_to_vector" in editor_orient_target and "target_normal" in editor_orient_target),
        ("Open 3D toolbar exposes Orient Row->Ray", "Orient Row->Ray" in init_with_top_controls and "start_placement_orient_ray_pick" in init_with_top_controls),
        ("Orient Row->Ray clears conflicting pick modes", "_source_target_pick_mode = False" in placement_orient_ray_start and "_placement_orient_pick_mode = False" in placement_orient_ray_start),
        ("Orient Row->Ray suppresses placement-handle drag", "_placement_orient_ray_mode" in placement_drag_start),
        ("Orient Row->Ray writes through vector row pose service", "orient_scene_row_anchor_to_vector" in placement_orient_ray_apply and "_ray_frame_near_point" in placement_orient_ray_apply),
        ("vector orient service writes Tilt and ScenePlacement metadata", "tilt_x" in editor_orient_vector and "target_vector" in editor_orient_vector and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_orient_vector),
        ("Open 3D toolbar exposes Orient Row->Source", "Orient Row->Source" in init_with_top_controls and "orient_selected_row_to_source_direction" in init_with_top_controls),
        ("Orient Row->Source writes through current source vector service", "orient_scene_row_anchor_to_current_source" in placement_orient_source and "_clear_immediate_orientation_modes" in placement_orient_source),
        ("source orient service writes source-vector metadata", "_current_source_direction" in editor_orient_source and "source_vector" in editor_orient_source and "last_constraint_source_origin" in editor_orient_source),
        ("Open 3D toolbar exposes Orient Row->Path", "Orient Row->Path" in init_with_top_controls and "orient_selected_row_to_path_frame" in init_with_top_controls),
        ("Orient Row->Path writes through current Path-view service", "orient_scene_row_anchor_to_current_path_frame" in placement_orient_path and "_clear_immediate_orientation_modes" in placement_orient_path),
        ("Path orient service writes Path-frame metadata", "_current_path_view_frame_near_point" in editor_orient_path and "path_frame" in editor_orient_path and "last_constraint_path_branch_path" in editor_orient_path),
        ("Open 3D toolbar exposes Orient Row->CAD Axis", "Orient Row->CAD Axis" in init_with_top_controls and "orient_selected_row_to_local_axis" in init_with_top_controls and "orient_axis_var" in init),
        ("Orient Row->CAD Axis writes through local-axis service", "orient_scene_row_anchor_to_local_axis" in placement_orient_axis and "_clear_immediate_orientation_modes" in placement_orient_axis),
        ("local-axis orient service writes CAD/local axis metadata", "_row_local_axis_world_vector" in editor_orient_axis and "local_axis" in editor_orient_axis and "last_constraint_axis_vector" in editor_orient_axis),
        ("Open 3D toolbar exposes Orient Row->Scene Source", "Orient Row->Scene Source" in init_with_top_controls and "orient_selected_row_to_scene_source" in init_with_top_controls),
        ("Orient Row->Scene Source writes through scene-source service", "orient_scene_row_anchor_to_scene_source" in placement_orient_scene_source and "_current_or_first_scene_source_id" in placement_orient_scene_source),
        ("scene-source orient service writes explicit source metadata", "_collect_scene_sources" in editor_orient_scene_source and "scene_source_vector" in editor_orient_scene_source and "last_constraint_source_id" in editor_orient_scene_source),
        ("Open 3D toolbar exposes named normal target preview/apply", "normal_target_var" in init and "Preview Normal" in init_with_top_controls and "Orient Row->Normal" in init_with_top_controls),
        ("named normal preview reads target without applying row pose", "preview_scene_row_anchor_to_named_normal_target" in placement_preview_named_normal and "orient_scene_row_anchor_to_named_normal_target" not in placement_preview_named_normal),
        ("named normal apply writes through row pose service", "orient_scene_row_anchor_to_named_normal_target" in placement_orient_named_normal and "_clear_immediate_orientation_modes" in placement_orient_named_normal),
        ("named normal preview resolves scene target diagnostics", "_scene_named_normal_target" in editor_preview_named_normal and "angle_error_deg" in editor_preview_named_normal),
        ("named normal orientation exports detector/object target metadata", "constraint_kind = f\"{normalized_kind}_normal\"" in editor_orient_named_normal and "last_constraint_target_role" in editor_orient_named_normal),
        ("ScenePlacement diagnostics expose applied normal target", "constraint=" in placement_features and "target_row=S" in placement_detail),
        ("CAD/STL assigned-face outlines use runtime TRANS_2A placement", "_runtime_transform_for_row(system, row_index)" in assigned_face_overlays),
        (
            "CAD/STL face-role marker helper remains runtime-transform aware",
            "_face_role_markers_from_runtime_transform" in face_overlays and "centroid_world" in runtime_face_markers,
        ),
        ("CAD/STL virtual-plane overlays use runtime TRANS_2A placement", "_runtime_transform_for_row(system, row_index)" in virtual_plane_overlays),
        ("3D refresh passes system into assigned-face overlays", "_add_optical_solid_assigned_face_overlays(system)" in refresh),
        (
            "Ray display envelope uses row geometry instead of overlay-inflated scene bounds",
            "center, radius = self._row_scene_bounds()" in refresh
            and "_row_actor_map" in row_scene_bounds
            and "ComputeVisiblePropBounds" not in row_scene_bounds,
        ),
        (
            "Ray-on refresh redraws retained CAD/STL edges after ray actors",
            "ray_surface_edge_overlays" in refresh
            and "for edges, edge_color, edge_width, edge_row_index in ray_surface_edge_overlays" in refresh
            and "track_row_index=edge_row_index" in refresh,
        ),
        (
            "Ray-on refresh redraws retained CAD/STL wireframes after ray actors",
            "ray_surface_wire_overlays" in refresh
            and "wireframe=True" in refresh
            and "pick_row_index=row_index" in refresh,
        ),
        (
            "file-backed optical STEP solids remain transparent during ray-on refresh",
            "file_backed_optical_solid" in editor_surface_meshes
            and "mesh_opacity = 0.30 if file_backed_optical_solid" in editor_surface_meshes
            and "mesh_opacity = min(max(mesh_opacity, 0.14), 0.28)" in refresh
            and "mesh_opacity = min(max(mesh_opacity, 0.14), 0.24)" in refresh
            and "elif row_index in file_backed_rows" in refresh,
        ),
        (
            "Open 3D shows the active Object launch aperture without enabling every reference plane",
            "_should_show_open3d_launch_reference_surface" in refresh
            and "include_reference_surfaces=show_reference_surfaces or show_launch_reference_surface" in refresh
            and 'row_surface == "Object"' in refresh,
        ),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Embedded 3D interaction contract failed:")
        for name in failed:
            print(f"- {name}")
        if not continuation_sync_ok:
            print(f"  continuation diagnostic: {continuation_sync_diag}")
        if not exit_axis_ok:
            print(f"  exit-axis diagnostic: {exit_axis_diag}")
        return 1
    print("Embedded 3D interaction contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
