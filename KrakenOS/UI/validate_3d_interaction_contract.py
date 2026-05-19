"""Validate the embedded 3D mouse-interaction contract."""

from __future__ import annotations

import inspect

from KrakenOS.UI.layout_editor import (
    STEP_CARRY_GRID_CHOICES,
    STEP_CARRY_GRID_FREE,
    Kraken3DInspector,
    KrakenLayoutEditor,
)


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
    step_rotate_handles = inspect.getsource(Kraken3DInspector._add_step_rotation_handles)
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
    step_carry_start = inspect.getsource(Kraken3DInspector.start_selected_step_carry)
    step_carry_snap_start = inspect.getsource(Kraken3DInspector.start_step_carry_snap_ray)
    step_carry_snap_apply = inspect.getsource(Kraken3DInspector._apply_step_carry_snap_ray)
    step_carry_snap_target_start = inspect.getsource(Kraken3DInspector.start_step_carry_snap_target)
    step_carry_snap_target_apply = inspect.getsource(Kraken3DInspector._apply_step_carry_snap_target)
    step_normal_snap = inspect.getsource(Kraken3DInspector.snap_selected_step_normal_to_optical_axis)
    step_normal_axis_start = inspect.getsource(Kraken3DInspector.start_step_normal_axis_pick)
    step_normal_axis_apply = inspect.getsource(Kraken3DInspector._apply_step_normal_axis_pick)
    optical_axis_records = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    optical_axis_overlays = inspect.getsource(Kraken3DInspector._add_optical_axis_pick_overlays)
    optical_axis_frame = inspect.getsource(Kraken3DInspector._optical_axis_frame_from_pick)
    optical_axis_screen_pick = inspect.getsource(Kraken3DInspector._optical_axis_info_near_display_xy)
    picked_step_feature = inspect.getsource(Kraken3DInspector._picked_feature_info)
    remember_step_feature = inspect.getsource(Kraken3DInspector._remember_selected_step_feature)
    step_carry_drop = inspect.getsource(Kraken3DInspector.stop_step_carry)
    operation_cancel = inspect.getsource(Kraken3DInspector.cancel_active_3d_operation)
    clear_selection = inspect.getsource(Kraken3DInspector._clear_open3d_selection)
    remove_step_handles = inspect.getsource(Kraken3DInspector._remove_step_rotation_handle_actors)
    key_press = inspect.getsource(Kraken3DInspector._on_key_press)
    refresh = inspect.getsource(Kraken3DInspector.refresh_scene)
    init = inspect.getsource(Kraken3DInspector.__init__)
    placement_grid = inspect.getsource(Kraken3DInspector._add_scene_placement_grid_overlays)
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
    editor_rotate = inspect.getsource(KrakenLayoutEditor.rotate_scene_row_pose)
    editor_step_translate = inspect.getsource(KrakenLayoutEditor.translate_step_overlay)
    editor_step_promote = inspect.getsource(KrakenLayoutEditor.promote_imported_step_to_optical_solid_row)
    editor_step_snap = inspect.getsource(KrakenLayoutEditor.snap_step_overlay_center_to_world_point)
    editor_step_snap_target = inspect.getsource(KrakenLayoutEditor.snap_step_overlay_center_to_scene_target)
    editor_step_normal_snap = inspect.getsource(KrakenLayoutEditor.snap_step_feature_normal_to_optical_axis)
    editor_step_axis_frame = inspect.getsource(KrakenLayoutEditor._step_optical_axis_frame_near_point)
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
    stl_handler = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    stl_refresh = inspect.getsource(Kraken3DInspector._refresh_after_stl_pose_change)
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
    refresh_3d_sync = inspect.getsource(KrakenLayoutEditor._refresh_3d_inspector_if_open)
    preview_sampling = inspect.getsource(KrakenLayoutEditor._preview_scene_sampling_mode)
    scene_ray_records = inspect.getsource(KrakenLayoutEditor._iter_3d_scene_ray_records)
    ray_terminal_style = inspect.getsource(KrakenLayoutEditor._ray_terminal_3d_style)
    editor_detector_overlays = inspect.getsource(KrakenLayoutEditor._scene_detector_overlay_specs)
    legacy_open_3d = inspect.getsource(KrakenLayoutEditor._populate_legacy_3d_plotter_scene)
    legacy_replace_rays = inspect.getsource(KrakenLayoutEditor._legacy_3d_replace_rays)
    checks = [
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
        ("STEP rotation handler is not a popup", "tk.Toplevel" not in handler and "_step_rotation_active_label" in handler),
        ("STEP rotation handles expose X/Y/Z axes", '("x",' in step_rotate_handles and '("y",' in step_rotate_handles and '("z",' in step_rotate_handles),
        ("STEP rotation handles expose repeated +/-90 rotations", "-1.0" in step_rotate_handles and "90.0" in step_rotate_handles),
        ("STEP rotation handles are pickable scene actors", "pick_step_rotate" in step_rotate_handles and "_actor_step_rotate_map" in pick),
        ("STEP rotation handle rotates selected component", "rotate_step_axis(label, axis" in step_rotate_pick),
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
            "Open 3D STEP normal snap is face-normal based",
            "Snap STEP Normal->Optical Axis" in init
            and "_remember_selected_step_feature" in pick
            and "start_step_normal_axis_pick(step_label)" in pick
            and "feature[2]" in remember_step_feature
            and "start_step_normal_axis_pick(label)" in step_normal_snap
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
            "Promote STEP to Optical Solid Row" in init and "promote_selected_step_to_optical_solid_row" in init,
        ),
        (
            "Open 3D STEP promotion refreshes and highlights the created row",
            "promote_imported_step_to_optical_solid_row" in step_promote
            and "highlight_row(row_index)" in step_promote
            and "Assign optical faces/material" in step_promote,
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
        ("active mode badge is a VTK overlay", "AddActor2D" in badge_update and "vtkTextActor" in badge_update),
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
        ("CAD/STL handler exposes repeated +/-90 rotations", "-90.0" in stl_handler and "90.0" in stl_handler),
        ("CAD/STL handler exposes placement finalization", "Done -> 2D" in stl_handler and "Front On Row" in stl_handler),
        ("CAD/STL handler stays current after pose changes", "_update_stl_placement_handler_state" in stl_refresh),
        ("Open 3D toolbar exposes Snapshot", "Snapshot" in init and "save_snapshot" in init),
        (
            "Open 3D face assignment has persistent face overlays",
            "_add_optical_solid_assigned_face_overlays" in refresh
            and "assigned face overlays" in refresh
            and "triangle_indices" in assigned_face_triangles
            and "backface_culling=False" in assigned_face_overlays
            and "feature_edges=False" in assigned_face_overlays,
        ),
        (
            "Open 3D CAD/STL faces hover before right-click assignment",
            "right-click to assign surface physics" in mouse_move
            and "_hover_overlay_for_feature" in mouse_move
            and "optical_solid_face_record_at_world_point" in mouse_move
            and '("row", actor_key, cell_id)' in mouse_move,
        ),
        (
            "Open 3D normal-axis snap keeps picked axis highlighted",
            "_set_optical_axis_highlight(axis_id)" in step_normal_axis_apply,
        ),
        (
            "Open 3D refresh does not clear scene on empty surface rebuild",
            "rebuilt trace produced no surface meshes" in refresh
            and "previous_actor_count > 0" in refresh
            and "return" in refresh.split("rebuilt trace produced no surface meshes", 1)[1].split("RemoveAllViewProps", 1)[0],
        ),
        (
            "Open 3D STEP promotion clears stale overlay interaction state",
            "_clear_step_overlay_interaction_state(label)" in step_promote
            and "refresh_open_3d=False" in step_promote
            and "_selected_step_label = None" in clear_step_overlay_state
            and "_close_step_rotation_handler()" in clear_step_overlay_state,
        ),
        (
            "Open 3D toolbar uses categorized rows",
            "toolbar_container" in init and "view_toolbar" in init and "scene_toolbar" in init,
        ),
        (
            "Open 3D scene toolbar groups dense commands",
            '"CAD / target"' in init and 'text="Place"' in init and 'text="Orient"' in init and "ttk.Menubutton" in init,
        ),
        ("Open 3D Snapshot uses Save As dialog", "filedialog.asksaveasfilename" in snapshot),
        ("Open 3D Snapshot defaults to attachment directory", "initialdir=str(ATTACHMENT_DIR)" in snapshot),
        ("Open 3D Snapshot has a short default filename", 'initialfile="3D.png"' in snapshot),
        ("Open 3D Snapshot uses VTK PNG capture", "vtkWindowToImageFilter" in snapshot and "vtkPNGWriter" in snapshot),
        ("Open 3D refresh reuses current SceneBundle when valid", "_current_preview_scene_trace" in refresh_from_editor),
        ("2D refresh uses shared 3D scene sampling", "_preview_scene_sampling_mode()" in editor_refresh_plot),
        ("2D refresh no longer traces display_slice as the main layout simulation", 'sampling_mode="display_slice"' not in editor_refresh_plot),
        ("Open 3D sync receives the same SceneBundle as 2D", "scene_bundle=bundle" in editor_refresh_plot and "refresh_scene(" in refresh_3d_sync),
        ("shared scene sampling supports full-pupil and world-envelope modes", "full_pupil" in preview_sampling and "world_envelope" in preview_sampling),
        ("Open 3D ray records preserve terminal status", "ray_path_terminal_status_from_events(path)" in scene_ray_records),
        ("Open 3D missed detector endpoints use status styling", "missed_detector" in ray_terminal_style and "endpoint_color" in ray_terminal_style),
        ("Open 3D refresh draws status-aware ray endpoints", "terminal_status=terminal_status" in refresh and "endpoint_scale" in refresh),
        ("legacy 3D refresh keeps status-aware ray endpoints", "terminal_status in self._iter_3d_scene_ray_records" in legacy_replace_rays and "endpoint_scale" in legacy_replace_rays),
        ("embedded 3D missed detector endpoint resolution is higher", "terminal_status == \"missed_detector\"" in endpoint_actor),
        ("Open 3D renders scene detector active footprints", "_add_scene_detector_overlays(scene_bundle)" in refresh and "scene_target_active_footprint_polylines" in editor_detector_overlays),
        ("Open 3D renders missed-detector projection crosshairs", "scene_target_detector_miss_crosshair_polylines" in editor_detector_overlays and "detector_miss_crosshair" in editor_detector_overlays),
        ("embedded 3D detector overlays are line meshes", "pv.lines_from_points" in detector_overlays and "line_width" in detector_overlays),
        ("legacy 3D includes detector overlays", "_scene_detector_overlay_specs(scene_bundle)" in legacy_open_3d),
        ("Open 3D renders row-backed placement grid state", "self._scene_placements_for_3d(scene_bundle)" in placement_grid and "grid_spacing_mm" in placement_grid),
        ("Open 3D placement grid is polyline data, not a UI-only table", "pv.PolyData" in placement_grid_mesh and "lines=" in placement_grid_mesh),
        ("Open 3D placement grid status is a VTK overlay", "vtkTextActor" in placement_grid_status and "Placement grid:" in placement_grid),
        ("Open 3D refresh reports placement grid count", "placement_grid_lines" in refresh and "_update_placement_grid_status" in refresh),
        ("Open 3D placement handles are pickable scene actors", "pick_placement_move" in placement_handles and "_actor_placement_move_map" in pick),
        ("Open 3D placement handles write through row pose service", "translate_scene_row_pose" in placement_handle_pick),
        ("placement translate service writes Desp and ScenePlacement metadata", "desp_x" in editor_translate and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_translate),
        ("Open 3D placement rotation handles are pickable scene actors", "pick_placement_rotate" in placement_rotate_handles and "_actor_placement_rotate_map" in pick),
        ("Open 3D placement rotation handles write through row pose service", "rotate_scene_row_pose" in placement_rotate_pick),
        ("placement rotate service writes Tilt and ScenePlacement metadata", "tilt_x" in editor_rotate and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_rotate),
        ("Open 3D placement drag starts from picked handle actors", "_placement_drag_state_from_current_pick()" in bindings and "_placement_handle_info_for_actor_key" in placement_drag_start),
        ("Open 3D placement drag suppresses camera drag while active", "_apply_placement_drag_motion(dx, dy)" in bindings and "_rotate_camera_fixed_drag(dx, dy)" in bindings),
        ("Open 3D placement drag writes through row pose services", "translate_scene_row_pose" not in placement_drag and "_apply_scene_placement_translate_handle" in placement_drag and "_apply_scene_placement_rotate_handle" in placement_drag),
        (
            "Open 3D toolbar exposes Center Row->Optical Axis",
            "Center Row->Optical Axis" in init
            and "start_center_row_to_ray" in init
            and "_hide_regular_rays_for_center_axis_pick()" in center_row_axis_start
            and "show_rays_var.set(False)" in center_row_axis_hide
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
            and "_dotted_optical_axis_mesh" in optical_axis_overlays
            and "_should_draw_optical_axis_overlays()" in refresh
            and "_mouse_move_due()" in mouse_move
            and "time.monotonic()" in mouse_move_due
            and "_step_feature_cache" in step_feature_cache
            and "_kraken_row_select_style" in row_actor_highlight
            and "SetEdgeVisibility(1)" in row_actor_highlight
            and "_apply_center_row_to_optical_axis(axis_info)" in pick
            and "_optical_axis_info_near_display_xy((x, y)" in pick
            and "center_surface_row_on_optical_axis" in center_row_axis_apply
            and "_ray_point_and_direction_on_surface_plane" in editor_center_row_axis,
        ),
        ("Open 3D toolbar exposes Snap Row->Target", "Snap Row->Target" in init and "start_placement_target_pick" in init),
        ("Snap Row->Target clears conflicting pick modes", "_source_target_pick_mode = False" in placement_target_start and "_center_row_to_ray_mode = False" in placement_target_start),
        ("Snap Row->Target suppresses placement-handle drag", "_placement_target_pick_mode" in placement_drag_start),
        ("Snap Row->Target writes through row pose service", "snap_scene_row_anchor_to_target" in placement_target_apply),
        ("target snap service writes Desp and ScenePlacement metadata", "desp_x" in editor_snap_target and "last_constraint_kind" in editor_snap_target and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_snap_target),
        ("Open 3D toolbar exposes Orient Row->Target", "Orient Row->Target" in init and "start_placement_orient_pick" in init),
        ("Orient Row->Target clears conflicting pick modes", "_source_target_pick_mode = False" in placement_orient_start and "_placement_target_pick_mode = False" in placement_orient_start),
        ("Orient Row->Target suppresses placement-handle drag", "_placement_orient_pick_mode" in placement_drag_start),
        ("Orient Row->Target writes through row pose service", "orient_scene_row_anchor_to_target" in placement_orient_apply),
        ("target orient service delegates to vector row pose service", "orient_scene_row_anchor_to_vector" in editor_orient_target and "target_normal" in editor_orient_target),
        ("Open 3D toolbar exposes Orient Row->Ray", "Orient Row->Ray" in init and "start_placement_orient_ray_pick" in init),
        ("Orient Row->Ray clears conflicting pick modes", "_source_target_pick_mode = False" in placement_orient_ray_start and "_placement_orient_pick_mode = False" in placement_orient_ray_start),
        ("Orient Row->Ray suppresses placement-handle drag", "_placement_orient_ray_mode" in placement_drag_start),
        ("Orient Row->Ray writes through vector row pose service", "orient_scene_row_anchor_to_vector" in placement_orient_ray_apply and "_ray_frame_near_point" in placement_orient_ray_apply),
        ("vector orient service writes Tilt and ScenePlacement metadata", "tilt_x" in editor_orient_vector and "target_vector" in editor_orient_vector and "SCENE_PLACEMENT_ADVANCED_ATTR" in editor_orient_vector),
        ("Open 3D toolbar exposes Orient Row->Source", "Orient Row->Source" in init and "orient_selected_row_to_source_direction" in init),
        ("Orient Row->Source writes through current source vector service", "orient_scene_row_anchor_to_current_source" in placement_orient_source and "_clear_immediate_orientation_modes" in placement_orient_source),
        ("source orient service writes source-vector metadata", "_current_source_direction" in editor_orient_source and "source_vector" in editor_orient_source and "last_constraint_source_origin" in editor_orient_source),
        ("Open 3D toolbar exposes Orient Row->Path", "Orient Row->Path" in init and "orient_selected_row_to_path_frame" in init),
        ("Orient Row->Path writes through current Path-view service", "orient_scene_row_anchor_to_current_path_frame" in placement_orient_path and "_clear_immediate_orientation_modes" in placement_orient_path),
        ("Path orient service writes Path-frame metadata", "_current_path_view_frame_near_point" in editor_orient_path and "path_frame" in editor_orient_path and "last_constraint_path_branch_path" in editor_orient_path),
        ("Open 3D toolbar exposes Orient Row->CAD Axis", "Orient Row->CAD Axis" in init and "orient_selected_row_to_local_axis" in init and "orient_axis_var" in init),
        ("Orient Row->CAD Axis writes through local-axis service", "orient_scene_row_anchor_to_local_axis" in placement_orient_axis and "_clear_immediate_orientation_modes" in placement_orient_axis),
        ("local-axis orient service writes CAD/local axis metadata", "_row_local_axis_world_vector" in editor_orient_axis and "local_axis" in editor_orient_axis and "last_constraint_axis_vector" in editor_orient_axis),
        ("Open 3D toolbar exposes Orient Row->Scene Source", "Orient Row->Scene Source" in init and "orient_selected_row_to_scene_source" in init),
        ("Orient Row->Scene Source writes through scene-source service", "orient_scene_row_anchor_to_scene_source" in placement_orient_scene_source and "_current_or_first_scene_source_id" in placement_orient_scene_source),
        ("scene-source orient service writes explicit source metadata", "_collect_scene_sources" in editor_orient_scene_source and "scene_source_vector" in editor_orient_scene_source and "last_constraint_source_id" in editor_orient_scene_source),
        ("Open 3D toolbar exposes named normal target preview/apply", "normal_target_var" in init and "Preview Normal" in init and "Orient Row->Normal" in init),
        ("named normal preview reads target without applying row pose", "preview_scene_row_anchor_to_named_normal_target" in placement_preview_named_normal and "orient_scene_row_anchor_to_named_normal_target" not in placement_preview_named_normal),
        ("named normal apply writes through row pose service", "orient_scene_row_anchor_to_named_normal_target" in placement_orient_named_normal and "_clear_immediate_orientation_modes" in placement_orient_named_normal),
        ("named normal preview resolves scene target diagnostics", "_scene_named_normal_target" in editor_preview_named_normal and "angle_error_deg" in editor_preview_named_normal),
        ("named normal orientation exports detector/object target metadata", "constraint_kind = f\"{normalized_kind}_normal\"" in editor_orient_named_normal and "last_constraint_target_role" in editor_orient_named_normal),
        ("ScenePlacement diagnostics expose applied normal target", "constraint=" in placement_features and "target_row=S" in placement_detail),
        ("CAD/STL face overlays use runtime TRANS_2A placement", "_runtime_transform_for_row(system, row_index)" in face_overlays),
        (
            "CAD/STL face overlays avoid raw-pose duplicate arrows",
            "_face_role_markers_from_runtime_transform" in face_overlays and "centroid_world" in runtime_face_markers,
        ),
        ("CAD/STL virtual-plane overlays use runtime TRANS_2A placement", "_runtime_transform_for_row(system, row_index)" in virtual_plane_overlays),
        ("3D refresh passes system into CAD/STL overlays", "_add_optical_solid_face_role_overlays(system)" in refresh),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Embedded 3D interaction contract failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Embedded 3D interaction contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
