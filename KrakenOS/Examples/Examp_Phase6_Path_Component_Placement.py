"""Phase 6 path-workbench component placement example.

This script demonstrates the same calculation used by the UI command:

    Right-click Beam Splitter -> Add component to transmitted/reflected path...

It loads the common 50/50 beam-splitter layout headlessly, computes the
transmitted/reflected path frames from the selected splitter, and creates native
KrakenOS table rows for a detector, aperture, thin lens, refractive surface,
and mirror without manually calculating global Tilt/Decenter values.
"""

from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import (
    BEAM_SPLITTER_SURFACE,
    ELEMENT_ADVANCED_ATTR,
    LAYOUTS_DIR,
    PATH_COMPONENT_APERTURE,
    PATH_COMPONENT_DETECTOR,
    PATH_COMPONENT_MIRROR,
    PATH_COMPONENT_REFRACTIVE_SURFACE,
    PATH_COMPONENT_THIN_LENS,
    _load_python_data,
)
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


def build_demo_rows():
    path = LAYOUTS_DIR / "beam_splitter_50_50_example.py"
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(_rows_from_layout_info(info), settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    splitter_index = next(index for index, row in enumerate(editor.rows) if row.surface == BEAM_SPLITTER_SURFACE)
    placed_rows = [
        editor._path_component_row_for_arm(
            splitter_index,
            "Transmit",
            PATH_COMPONENT_THIN_LENS,
            35.0,
            20.0,
            parameter_mm=100.0,
        ),
        editor._path_component_row_for_arm(
            splitter_index,
            "Transmit",
            PATH_COMPONENT_DETECTOR,
            70.0,
            25.0,
        ),
        editor._path_component_row_for_arm(
            splitter_index,
            "Reflect",
            PATH_COMPONENT_APERTURE,
            35.0,
            15.0,
        ),
        editor._path_component_row_for_arm(
            splitter_index,
            "Reflect",
            PATH_COMPONENT_REFRACTIVE_SURFACE,
            50.0,
            20.0,
            parameter_mm=80.0,
            glass="BK7",
        ),
        editor._path_component_row_for_arm(
            splitter_index,
            "Reflect",
            PATH_COMPONENT_MIRROR,
            70.0,
            25.0,
            parameter_mm=0.0,
        ),
    ]
    return placed_rows


def main() -> int:
    rows = build_demo_rows()
    print("component | surface | role | selector | distance mm | tilt xyz deg | decenter xyz mm")
    print("--- | --- | --- | --- | --- | --- | ---")
    for row in rows:
        metadata = row.advanced.get(ELEMENT_ADVANCED_ATTR, {}) if isinstance(row.advanced, dict) else {}
        tilt = f"{row.tilt_x:.6g}, {row.tilt_y:.6g}, {row.tilt_z:.6g}"
        decenter = f"{row.desp_x:.6g}, {row.desp_y:.6g}, {row.desp_z:.6g}"
        print(
            f"{row.name} | {row.surface} | {metadata.get('arm_role')} | "
            f"{metadata.get('branch_selector')} | {float(metadata.get('arm_distance', 0.0)):.6g} | "
            f"{tilt} | {decenter}"
        )
    print(f"\nRun the UI validation with: python -m KrakenOS.UI.validate_phase6_path_workbench")
    print(f"Source layout: {Path(LAYOUTS_DIR / 'beam_splitter_50_50_example.py')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
