"""Validate the embedded 3D mouse-interaction contract."""

from __future__ import annotations

import inspect

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


def main() -> int:
    bindings = inspect.getsource(Kraken3DInspector._install_pick_only_left_click_bindings)
    rotation = inspect.getsource(Kraken3DInspector._rotate_camera_fixed_drag)
    pick = inspect.getsource(Kraken3DInspector._on_left_button_press)
    handler = inspect.getsource(Kraken3DInspector.show_step_rotation_handler)
    handler_rotate = inspect.getsource(Kraken3DInspector._rotate_step_from_handler)
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
        ("VTK left-button trackball forwarding removed", "LeftButtonPressEvent(event" not in bindings),
        ("STEP click opens rotation handler", "show_step_rotation_handler(step_label)" in pick),
        ("STEP handler exposes X/Y/Z axes", '("x", "y", "z")' in handler and "axis.upper()" in handler),
        ("STEP handler exposes repeated +/-90 rotations", "-90.0" in handler and "90.0" in handler),
        ("STEP handler rotates selected component", "rotate_selected_step_axis" in handler_rotate),
        ("STEP handler survives 3D refresh", "_update_step_rotation_handler_state" in refresh),
        ("duplicate STEP Rotate toolbar menu removed", "STEP Rotate" not in init),
        ("active mode badge covers STEP centering", "CENTER STEP AXIS" in badge_text),
        ("active mode badge covers Obj->LED", "OBJ -> LED" in badge_text),
        ("active mode badge covers Center Row->Ray", "CENTER ROW -> RAY" in badge_text),
        ("active mode badge covers Snap Row->Target", "SNAP ROW -> TARGET" in badge_text),
        ("active mode badge covers Orient Row->Target", "ORIENT ROW -> TARGET" in badge_text),
        ("active mode badge covers Orient Row->Ray", "ORIENT ROW -> RAY" in badge_text),
        ("active mode badge covers Source Target", "SOURCE TARGET" in badge_text),
        ("active mode badge is a VTK overlay", "AddActor2D" in badge_update and "vtkTextActor" in badge_update),
        ("active mode badge survives 3D refresh", "_update_mode_badge" in refresh),
        ("embedded STL placement toolbar removed", "stl_toolbar" not in init and "placement toolbar" not in init),
        ("CAD/STL selection opens placement handler", "show_stl_placement_handler(int(row_index))" in pick),
        ("CAD/STL handler is embedded side panel", "CAD/STL placement side panel" in stl_handler and "tk.Toplevel" not in stl_handler),
        ("CAD/STL handler exposes axis fit", "Fit local axis to +Z" in stl_handler and "Fit Axis" in stl_handler),
        ("CAD/STL handler exposes repeated +/-90 rotations", "-90.0" in stl_handler and "90.0" in stl_handler),
        ("CAD/STL handler exposes placement finalization", "Done -> 2D" in stl_handler and "Front On Row" in stl_handler),
        ("CAD/STL handler stays current after pose changes", "_update_stl_placement_handler_state" in stl_refresh),
        ("Open 3D toolbar exposes Snapshot", "Snapshot" in init and "save_snapshot" in init),
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
