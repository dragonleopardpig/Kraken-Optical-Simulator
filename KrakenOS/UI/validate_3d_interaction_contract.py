"""Validate the embedded 3D mouse-interaction contract."""

from __future__ import annotations

import inspect

from KrakenOS.UI.layout_editor import Kraken3DInspector


def main() -> int:
    bindings = inspect.getsource(Kraken3DInspector._install_pick_only_left_click_bindings)
    rotation = inspect.getsource(Kraken3DInspector._rotate_camera_fixed_drag)
    checks = [
        ("left drag binding exists", '"<B1-Motion>"' in bindings),
        ("plain left press no longer performs immediate pick", "_on_left_button_press(None, None)" not in bindings.split("def left_motion", 1)[0]),
        ("release without drag performs selection", "should_pick" in bindings and "_on_left_button_press(None, None)" in bindings),
        ("drag threshold prevents accidental rotation", "drag_threshold_px" in bindings),
        ("fixed drag method uses constant sensitivity", "degrees_per_pixel" in rotation),
        ("fixed drag preserves focal point", "camera.SetFocalPoint(*focal)" in rotation),
        ("fixed drag uses azimuth/elevation only", "camera.Azimuth" in rotation and "camera.Elevation" in rotation),
        ("VTK left-button trackball forwarding removed", "LeftButtonPressEvent(event" not in bindings),
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
