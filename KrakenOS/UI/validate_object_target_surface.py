"""Validate the semantic Object Target surface type.

Run from the repository root:

    python -m KrakenOS.UI.validate_object_target_surface
"""

from __future__ import annotations

from KrakenOS.common_optical_layouts.zemax_led_beam_splitter_imaging import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info


def main() -> None:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    object_target_rows = [row for row in rows if row.surface == "Object Target"]
    assert object_target_rows, "expected the LED beam-splitter layout to expose an Object Target row"
    row = object_target_rows[0]
    assert str(row.glass).upper() == "MIRROR", "Object Target must use MIRROR internally for current proxy tracing"
    assert row.advanced.get("Display2D", {}).get("label") == "Object target"

    system = _build_system_from_specs(SURFACES)
    object_target_index = next(index for index, spec in enumerate(SURFACES) if spec.get("surface") == "Object Target")
    runtime_surface = system.SDT[object_target_index]
    assert str(getattr(runtime_surface, "Glass", "")).upper() == "MIRROR"
    assert abs(float(getattr(runtime_surface, "AxisMove", 0.0))) > 0.0
    print("Object Target semantic surface validation passed.")


if __name__ == "__main__":
    main()
