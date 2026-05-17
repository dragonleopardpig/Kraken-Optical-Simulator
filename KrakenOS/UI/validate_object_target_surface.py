"""Validate the semantic Object Target surface type.

Run from the repository root:

    python -m KrakenOS.UI.validate_object_target_surface
"""

from __future__ import annotations

from KrakenOS.common_optical_layouts.right_angle_beam_splitter_illumination import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info
from KrakenOS.UI.scene_builder import build_scene_targets


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
    targets = build_scene_targets(rows)
    target_record = next((target for target in targets if target.row_index == object_target_index), None)
    assert target_record is not None, "Object Target row should become a SceneTarget3D record"
    assert target_record.role == "object_target"
    assert not target_record.is_detector
    print("Object Target semantic surface validation passed.")


if __name__ == "__main__":
    main()
