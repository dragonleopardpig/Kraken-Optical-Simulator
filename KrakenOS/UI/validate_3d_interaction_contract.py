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
    placement_handles = inspect.getsource(Kraken3DInspector._add_scene_placement_translate_handles)
    placement_rotate_handles = inspect.getsource(Kraken3DInspector._add_scene_placement_rotate_handles)
    placement_handle_pick = inspect.getsource(Kraken3DInspector._apply_scene_placement_translate_handle)
    placement_rotate_pick = inspect.getsource(Kraken3DInspector._apply_scene_placement_rotate_handle)
    placement_drag_start = inspect.getsource(Kraken3DInspector._placement_drag_state_from_current_pick)
    placement_drag = inspect.getsource(Kraken3DInspector._apply_placement_drag_motion)
    editor_translate = inspect.getsource(KrakenLayoutEditor.translate_scene_row_pose)
    editor_rotate = inspect.getsource(KrakenLayoutEditor.rotate_scene_row_pose)
    badge_text = inspect.getsource(Kraken3DInspector._active_mode_badge_text)
    badge_update = inspect.getsource(Kraken3DInspector._update_mode_badge)
    stl_handler = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    stl_refresh = inspect.getsource(Kraken3DInspector._refresh_after_stl_pose_change)
    snapshot = inspect.getsource(Kraken3DInspector.save_snapshot)
    refresh_from_editor = inspect.getsource(Kraken3DInspector.refresh_from_editor)
    face_overlays = inspect.getsource(Kraken3DInspector._add_optical_solid_face_role_overlays)
    virtual_plane_overlays = inspect.getsource(Kraken3DInspector._add_optical_solid_virtual_plane_overlays)
    runtime_face_markers = inspect.getsource(Kraken3DInspector._face_role_markers_from_runtime_transform)
    editor_refresh_plot = inspect.getsource(KrakenLayoutEditor.refresh_plot)
    refresh_3d_sync = inspect.getsource(KrakenLayoutEditor._refresh_3d_inspector_if_open)
    preview_sampling = inspect.getsource(KrakenLayoutEditor._preview_scene_sampling_mode)
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
