"""Validate the Galvo F-theta scanner case-study docs and assets."""

from __future__ import annotations

import inspect
from pathlib import Path

from KrakenOS.common_optical_layouts import f_theta_lens_50mm_figure8 as ftheta
from KrakenOS.common_optical_layouts import galvo_f_theta_laser_scanner as scanner
from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "galvo_f_theta_laser_scanner.rst"
INDEX_PATH = PROJECT_ROOT / "docs" / "source" / "tutorials" / "index.rst"
STATIC_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "galvo_f_theta_laser_scanner"

EXPECTED_ASSETS = (
    "galvo_f_theta_workflow.svg",
    "galvo_scan_overlay.svg",
    "01_folded_layout_yz.png",
    "02_detector_map.png",
    "03_branch_field.png",
    "04_standalone_f_theta_lens.png",
)


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _asset_ok(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    if path.suffix.lower() == ".png":
        return path.stat().st_size > 10_000
    return path.stat().st_size > 500


def _galvo_mirror_row() -> dict:
    for row in scanner.SURFACES:
        if str(row.get("surface", "")).strip() == "Mirror" and "galvo" in str(row.get("name", "")).lower():
            return row
    raise AssertionError("Galvo mirror row not found")


def _validate_common_layout_contract() -> None:
    _require(scanner.TITLE == "Galvo F-Theta Laser Scanner", "unexpected scanner layout title")
    _require(scanner.SETTINGS.get("source_model") == "Gaussian beam", "scanner preset should use Gaussian beam source")
    _require(scanner.SETTINGS.get("trace_mode") == "Folded Preview", "scanner preset should use Folded Preview")
    _require(
        scanner.SETTINGS.get("folded_detector_policy") == "Display compatibility",
        "scanner preset should explicitly opt into folded display detector reach",
    )
    _require(scanner.SETTINGS.get("ray_count") == "9", "scanner tutorial assumes 9 representative rays")

    mirror = _galvo_mirror_row()
    overlay = (
        mirror.get("advanced", {})
        .get("Display2D", {})
        .get("tilt_x_overlay_deg", [])
    )
    _require(float(mirror.get("tilt_x", 0.0)) == 45.0, "galvo mirror nominal TiltX should be 45 deg")
    _require([float(value) for value in overlay] == [40.0, 45.0, 50.0], "galvo overlay should be 40,45,50")

    ftheta_rows = [row for row in scanner.SURFACES if row.get("element") == "F-theta Figure 8 lens"]
    _require(len(ftheta_rows) == 8, "scanner should embed eight F-theta refractive rows")
    _require(scanner.SURFACES[-1].get("surface") == "Image", "scanner should terminate at an Image scan plane")

    _require(ftheta.SETTINGS.get("object_mode") == "Infinity", "standalone F-theta lens should use Infinity object mode")
    _require(ftheta.SETTINGS.get("field_type") == "Angle", "standalone F-theta lens should use angle fields")
    _require(ftheta.SETTINGS.get("field_value") == "20.0", "standalone F-theta lens should cover 20 deg half field")


def _validate_docs_and_assets() -> None:
    doc = _text(DOC_PATH)
    index = _text(INDEX_PATH)
    _require("galvo_f_theta_laser_scanner" in index, "tutorial index does not include galvo page")
    _require("Case Study 17: Galvo F-Theta Laser Scanner" in doc, "tutorial title missing")
    _require("TiltX = 40,45,50" in doc, "tutorial should document current conservative overlay")
    _require("TiltX = 35,45,55" in doc, "tutorial should document current full-field overlay")
    _require("F-Theta Lens 50mm Figure 8" in doc, "tutorial should link the standalone lens validation workflow")
    for asset in EXPECTED_ASSETS:
        _require(asset in doc, f"tutorial does not reference {asset}")
        _require(_asset_ok(STATIC_DIR / asset), f"missing or tiny tutorial asset: {asset}")


def _validate_open3d_scan_animation_contract() -> None:
    plan_source = inspect.getsource(KrakenLayoutEditor._folded_scan_overlay_plans)
    draw_source = inspect.getsource(KrakenLayoutEditor._draw_folded_scan_overlay)
    animation_source = inspect.getsource(Kraken3DInspector.start_galvo_scan_animation)
    frame_source = inspect.getsource(Kraken3DInspector._add_galvo_scan_frame_actors)
    _require(
        "folded_scan_overlay_plan" in plan_source and "field_theta" in plan_source,
        "folded scan overlay plan builder should remain the shared 2D/Open 3D source",
    )
    _require(
        "_folded_scan_overlay_plans" in draw_source,
        "2D galvo overlay should draw from the shared folded scan plan builder",
    )
    _require(
        "_folded_scan_overlay_plans" in animation_source,
        "Open 3D galvo animation should animate the shared folded scan plans",
    )
    _require(
        "_folded_scan_display_points_to_3d" in frame_source and "_ray_segment_mesh_for_3d_display" in frame_source,
        "Open 3D galvo animation should render scan plans as physical 3D line segments",
    )


def main() -> None:
    _validate_common_layout_contract()
    _validate_docs_and_assets()
    _validate_open3d_scan_animation_contract()
    print("Galvo F-theta case-study validation passed.")


if __name__ == "__main__":
    main()
