"""Validate folder-based vendor-camera import -> a CAMERA_DATABASE record.

The camera analogue of the machine-vision *lens* folder importer: a user points
at a single vendor *camera folder* (mechanical STEP + datasheet PDF, or a curated
``.json`` sidecar) and the sensor is scraped/registered so importing the vendor
STEP couples the surrogate to that sensor exactly like picking the camera from the
dropdown.

This guard is display-free and mostly deterministic (no Tk / VTK):

* a **synthetic sidecar folder** (STEP + ``.json`` with a sensor size) exercises
  the whole engine + DB merge end to end without any vendor asset: classify ->
  build record -> persist -> fold into a reloaded ``camera_database`` -> assert the
  camera appears in ``camera_names()`` with tuple / absolute-Path parity and
  reverse-resolves from its STEP via ``camera_model_for_step_path``;
* a built-in name in the registry must NOT be overridden (built-ins win);
* a source-less folder (STEP only, no spec) must raise a clear ``ValueError``;
* when the **real Allied Vision hr25MCX datasheet** is checked out, its PDF spec
  table is scraped and the headline sensor fields are asserted (skipped, not
  failed, when the asset is absent);
* the editor / inspector / menu wiring is asserted by reading the source files.

Exposes ``run_checks() -> (passed, failures)`` so it doubles as a comprehensive
penta-telescope phase, plus a standalone ``main()``.
"""

from __future__ import annotations

import importlib
import json
import tempfile
from pathlib import Path

from KrakenOS.UI.services.camera_folder_import import (
    build_camera_record_from_assets,
    parse_camera_datasheet,
    scan_camera_folder,
    write_imported_camera,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UI_DIR = PROJECT_ROOT / "KrakenOS" / "UI"
WORKBENCH_PATH = UI_DIR / "services" / "layout_table_workbench.py"
STEP_OVERLAY_PATH = UI_DIR / "services" / "step_overlay_import.py"
CAMERA_DB_PATH = UI_DIR / "camera_database.py"
INSPECTOR_PATH = UI_DIR / "open3d_inspector.py"
MENU_PATH = UI_DIR / "panels" / "main_context_menu.py"
TOP_CONTROLS_PATH = UI_DIR / "panels" / "open3d_top_controls.py"

# Real vendor asset (Filen-synced; may be absent on a bare checkout).
REAL_PDF = PROJECT_ROOT / "attachment" / "Cameras" / "hr25MCX_Datasheet.pdf"

_SIDECAR = {
    "name": "Contoso Vision cx-test",
    "manufacturer": "Contoso Vision",
    "model": "cx-test",
    "sensor_width_mm": 12.0,
    "sensor_height_mm": 8.0,
    "pixel_size_um": [3.0, 3.0],
    "resolution_px": [4000, 2667],
    "pixel_formats": ["mono8", "mono12"],
    "lens_mount": "C",
}


def run_checks() -> tuple[bool, list[str]]:
    """Return ``(passed, failures)`` without printing -- usable as a phase body."""
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as raw:
        work = Path(raw)

        # --- synthetic sidecar folder: engine + DB merge end to end ---------
        folder = work / "Contoso Vision cx-test"
        folder.mkdir(parents=True, exist_ok=True)
        step = folder / "3D_CAD_CXTEST.STEP"
        step.write_bytes(b"ISO-10303-21;\nENDSEC;\n")  # dummy; engine records path only
        (folder / "camera.json").write_text(json.dumps(_SIDECAR), encoding="utf-8")

        assets = scan_camera_folder(folder)
        if assets.primary_step is None:
            failures.append("sidecar folder: STEP not classified")
        if assets.primary_sidecar is None:
            failures.append("sidecar folder: .json sidecar not classified")

        try:
            imported = build_camera_record_from_assets(assets)
        except Exception as exc:
            failures.append(f"sidecar folder: build raised {exc!r}")
            imported = None

        if imported is not None:
            rec = imported.record
            if imported.name != _SIDECAR["name"]:
                failures.append(f"sidecar name {imported.name!r} != {_SIDECAR['name']!r}")
            if rec.get("sensor_width_mm") != 12.0 or rec.get("sensor_height_mm") != 8.0:
                failures.append("sidecar sensor size not carried into the record")
            # sensor_diagonal_mm + image_diameter_mm are derived from the size.
            if rec.get("sensor_diagonal_mm") != round((12.0**2 + 8.0**2) ** 0.5, 4):
                failures.append(f"derived sensor_diagonal_mm wrong: {rec.get('sensor_diagonal_mm')}")
            if rec.get("image_diameter_mm") != 12.0:
                failures.append(f"image_diameter_mm should be max side 12.0, got {rec.get('image_diameter_mm')}")

            # Persist to a temp registry and fold into a freshly-reloaded DB.
            reg = work / "imported_cameras.json"
            write_imported_camera(imported.name, imported.record, path=reg)

            import KrakenOS.UI.camera_database as db
            importlib.reload(db)
            db._merge_imported_cameras(reg)

            name = imported.name
            if name not in db.camera_names():
                failures.append("imported camera missing from camera_names() after merge")
            merged = db.camera_record(name) or {}
            if not isinstance(merged.get("resolution_px"), tuple):
                failures.append("resolution_px not converted to tuple on merge")
            if not isinstance(merged.get("pixel_formats"), tuple):
                failures.append("pixel_formats not converted to tuple on merge")
            step_path = merged.get("step_path")
            if not (isinstance(step_path, Path) and step_path.is_absolute()):
                failures.append(f"merged step_path not an absolute Path: {step_path!r}")
            elif step_path.resolve() != step.resolve():
                failures.append("merged step_path does not resolve to the folder STEP")
            if db.camera_model_for_step_path(step_path) != name:
                failures.append("camera_model_for_step_path(step_path) did not reverse-resolve")
            if db.camera_model_for_step_path("3D_CAD_CXTEST.STEP") != name:
                failures.append("camera_model_for_step_path(filename) did not reverse-resolve")
            if db.camera_image_coverage_mm(name) is None:
                failures.append("imported camera has no image coverage (sensor size lost)")

            # Built-ins win: a registry entry re-using a built-in name is ignored.
            reg2 = work / "reg2.json"
            reg2.write_text(json.dumps({
                "Allied Vision hr25MCX": {"sensor_width_mm": 999.0},
            }), encoding="utf-8")
            db._merge_imported_cameras(reg2)
            builtin = db.camera_record("Allied Vision hr25MCX") or {}
            if builtin.get("sensor_width_mm") != 23.04:
                failures.append("built-in camera was overridden by an imported record")

        # --- a source-less folder (STEP only, no PDF / sidecar) is rejected --
        bare = work / "Bare Camera Folder"
        bare.mkdir(parents=True, exist_ok=True)
        (bare / "body.step").write_text("ISO-10303-21;\n", encoding="utf-8")
        bare_assets = scan_camera_folder(bare)
        if bare_assets.has_spec_source:
            failures.append("source-less camera folder wrongly reports a spec source")
        try:
            build_camera_record_from_assets(bare_assets)
        except ValueError:
            pass
        else:
            failures.append("source-less camera folder did not raise on build")

    # --- real Allied Vision hr25MCX datasheet scrape (skip if absent) --------
    if REAL_PDF.exists():
        spec = parse_camera_datasheet(REAL_PDF)
        if spec is None:
            failures.append("real hr25MCX datasheet did not parse to a CameraSpec")
        else:
            if spec.sensor_width_mm != 23.04 or spec.sensor_height_mm != 23.04:
                failures.append(f"hr25 sensor size scraped wrong: {spec.sensor_width_mm}x{spec.sensor_height_mm}")
            if spec.resolution_px != (5120, 5120):
                failures.append(f"hr25 resolution scraped wrong: {spec.resolution_px}")
            if spec.pixel_size_um != (4.5, 4.5):
                failures.append(f"hr25 pixel size scraped wrong: {spec.pixel_size_um}")
            if spec.spectral_range_nm != (400.0, 1000.0):
                failures.append(f"hr25 spectral range scraped wrong: {spec.spectral_range_nm}")
            if not (spec.lens_mount or "").startswith("M58"):
                failures.append(f"hr25 lens mount scraped wrong: {spec.lens_mount!r}")

    # --- editor / inspector / menu wiring (source-text asserts) --------------
    def _src(path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    workbench_src = _src(WORKBENCH_PATH)
    step_overlay_src = _src(STEP_OVERLAY_PATH)
    camera_db_src = _src(CAMERA_DB_PATH)
    inspector_src = _src(INSPECTOR_PATH)
    menu_src = _src(MENU_PATH)
    top_controls_src = _src(TOP_CONTROLS_PATH)

    if "def import_vendor_camera_from_folder" not in workbench_src:
        failures.append("editor does not expose import_vendor_camera_from_folder")
    if "refresh_imported_cameras" not in workbench_src:
        failures.append("editor handler does not refresh the imported-camera registry")
    if "def refresh_imported_cameras" not in camera_db_src or "def _merge_imported_cameras" not in camera_db_src:
        failures.append("camera_database is missing the imported-camera merge hook")
    if "path: Path | str | None" not in step_overlay_src:
        failures.append("import_camera_step does not accept an explicit path= (folder-import reuse)")
    if "def import_vendor_camera_from_folder" not in inspector_src:
        failures.append("inspector does not expose import_vendor_camera_from_folder")
    if "import_vendor_camera_from_folder" not in menu_src:
        failures.append("2D context menu does not wire the camera folder importer")
    if "Import Vendor Camera from Folder" not in menu_src:
        failures.append("2D context menu has no 'Import Vendor Camera from Folder' label")
    if "import_vendor_camera_from_folder" not in top_controls_src:
        failures.append("3D top controls do not wire the camera folder importer")
    if "Import Camera from Folder" not in top_controls_src:
        failures.append("3D top controls have no 'Import Camera from Folder' label")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Camera folder-import validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Camera folder-import validation passed: a vendor camera folder (STEP + "
        "datasheet/sidecar) registers a CAMERA_DATABASE record, folds into the live "
        "database, and reverse-resolves from its STEP so the import couples the "
        "sensor -- and the editor / inspector / menus expose the importer."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
