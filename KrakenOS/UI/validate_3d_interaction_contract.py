"""Validate the embedded 3D mouse-interaction contract."""

from __future__ import annotations

import inspect

from KrakenOS.UI.layout_editor import Kraken3DInspector


def main() -> int:
    bindings = inspect.getsource(Kraken3DInspector._install_pick_only_left_click_bindings)
    rotation = inspect.getsource(Kraken3DInspector._rotate_camera_fixed_drag)
    pick = inspect.getsource(Kraken3DInspector._on_left_button_press)
    handler = inspect.getsource(Kraken3DInspector.show_step_rotation_handler)
    handler_rotate = inspect.getsource(Kraken3DInspector._rotate_step_from_handler)
    refresh = inspect.getsource(Kraken3DInspector.refresh_scene)
    init = inspect.getsource(Kraken3DInspector.__init__)
    badge_text = inspect.getsource(Kraken3DInspector._active_mode_badge_text)
    badge_update = inspect.getsource(Kraken3DInspector._update_mode_badge)
    stl_handler = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    stl_refresh = inspect.getsource(Kraken3DInspector._refresh_after_stl_pose_change)
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
