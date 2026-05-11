"""Validate imported STEP axis centering from a picked KrakenOS surface."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import DEFAULT_LED_STEP_PATH, KrakenLayoutEditor, SurfaceRow


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    try:
        app.rows = [
            SurfaceRow(surface="Object", name="Object", thickness=20.0, diameter=20.0, glass="AIR"),
            SurfaceRow(
                surface="Standard",
                name="Decentered target surface",
                rc=0.0,
                thickness=10.0,
                diameter=12.0,
                glass="AIR",
                desp_x=2.5,
                desp_y=-1.25,
            ),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=20.0, glass="AIR"),
        ]
        app._normalize_special_rows()
        app.imported_led_step_path = Path(DEFAULT_LED_STEP_PATH)
        app.led_step_axis_offset_xy = (9.0, -8.0)
        app._cad_axis_pick_label = "led"
        result = app.center_step_axis_on_surface("led", 1)
        if result is None:
            raise AssertionError("Expected surface-axis centering result.")
        target = np.asarray(result["target"], dtype=float)
        offset = np.asarray(result["offset"], dtype=float)
        if not np.allclose(offset, -target[:2], atol=1e-9):
            raise AssertionError(f"Expected offset {-target[:2]}, got {offset}.")
        if app._cad_axis_pick_label is not None:
            raise AssertionError("Surface-axis pick did not clear axis-pick mode.")
        if app._selected_step_label != "led":
            raise AssertionError(f"Expected selected STEP label 'led', got {app._selected_step_label!r}.")

        app.led_step_axis_offset_xy = (3.0, 4.0)
        direct = app.center_step_axis_on_world_point("led", (0.0, 0.0, 30.0))
        if direct is None:
            raise AssertionError("Expected direct world-point centering result.")
        if tuple(app.led_step_axis_offset_xy) != (-0.0, -0.0):
            raise AssertionError(f"Expected LED axis offset reset to optical axis, got {app.led_step_axis_offset_xy}.")
    finally:
        app.destroy()
    print("STEP axis surface-pick validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
