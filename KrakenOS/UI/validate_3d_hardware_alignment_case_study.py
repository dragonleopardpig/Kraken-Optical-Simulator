"""Validate the 3D hardware-alignment case study docs and UI contracts."""

from __future__ import annotations

import inspect
from pathlib import Path

from KrakenOS.UI.layout_editor import Kraken3DInspector


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "3d_hardware_alignment.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
CAPTURE_SCRIPT = PROJECT_ROOT / "KrakenOS" / "UI" / "capture_3d_hardware_alignment_case_study_screenshots.py"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "3d_hardware_alignment"
EXPECTED_IMAGES = (
    "01_3d_inspector_axis_faces.png",
    "02_cad_stl_placement_handler.png",
    "03_center_step_axis_mode_badge.png",
    "04_step_rotation_handler.png",
    "05_source_target_mode_badge.png",
    "06_step_carry_grid.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def main() -> int:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    capture = _text(CAPTURE_SCRIPT)
    stl_handler = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    badge_text = inspect.getsource(Kraken3DInspector._active_mode_badge_text)
    step_handler = inspect.getsource(Kraken3DInspector.show_step_rotation_handler)
    step_handles = inspect.getsource(Kraken3DInspector._add_step_rotation_handles)

    checks = [
        ("case-study page exists", DOC_PATH.exists()),
        ("case-study in tutorials toctree", "3d_hardware_alignment" in index),
        ("capture script exists", CAPTURE_SCRIPT.exists() and "DEFAULT_OUTPUT_DIR" in capture),
        ("case-study documents CAD/STL handler", "CAD/STL placement handler" in doc),
        ("case-study documents STEP rotation handles", "STEP rotation handles" in doc),
        ("case-study documents STEP carry grid", "Carry Imported STEP On The Grid" in doc and "cube grid" in doc),
        ("case-study documents STEP Lift/Drop carry", "``Lift``" in doc and "``Drop``" in doc),
        ("case-study documents STEP Snap ray carry", "``Snap ray``" in doc),
        ("case-study documents STEP Snap target carry", "``Snap target``" in doc),
        ("case-study documents STEP promotion", "Promote STEP to Optical Solid Row" in doc),
        ("case-study documents active-mode badges", "active-mode badge" in doc),
        ("case-study documents Done -> 2D", "Done -> 2D" in doc),
        ("capture script captures STEP carry grid", "06_step_carry_grid.png" in capture and "start_selected_step_carry" in capture),
        ("CAD/STL handler has inline help", "What this does" in stl_handler and "Fit Axis chooses" in stl_handler),
        ("CAD/STL handler exposes placement actions", "Front On Row" in stl_handler and "Center X/Y" in stl_handler),
        ("STEP handler selects in-scene handles", "colored STEP rotation handles" in step_handler and "tk.Toplevel" not in step_handler),
        ("STEP handles expose repeated rotations", "pick_step_rotate" in step_handles and "-1.0" in step_handles and "90.0" in step_handles),
        ("mode badges cover source target", "SOURCE TARGET" in badge_text),
        ("mode badges cover center step axis", "CENTER STEP AXIS" in badge_text),
    ]
    for image_name in EXPECTED_IMAGES:
        path = STATIC_DIR / image_name
        checks.append((f"image exists: {image_name}", path.exists() and path.stat().st_size > 2048))

    failed = [name for name, ok in checks if not ok]
    if failed:
        print("3D hardware-alignment case study validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("3D hardware-alignment case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
