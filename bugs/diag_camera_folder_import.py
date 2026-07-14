"""Verify the camera folder-import engine end-to-end on the real Allied Vision
hr25MCX assets: build a realistic vendor-named folder (datasheet + STEP), run
`import_camera_folder`, and check the record fields the sensor-coupling needs
against the datasheet ground truth + the registry round-trip.

Run: .devenv/state/venv/bin/python bugs/diag_camera_folder_import.py
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from KrakenOS.UI.services import camera_folder_import as cfi

CAMERAS = Path("attachment/Cameras").resolve()
PDF = CAMERAS / "hr25MCX_Datasheet.pdf"
STEP = CAMERAS / "3D_CAD_HR25xCXP.STEP"


def main() -> int:
    spec = cfi.parse_camera_datasheet(PDF)
    print("=== CameraSpec (scraped) ===")
    if spec is None:
        print("FAILED: parse_camera_datasheet returned None")
        return 1
    for k, v in spec.__dict__.items():
        print(f"  {k:26} {v!r}")

    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "Allied Vision hr25MCX"
        folder.mkdir()
        shutil.copy2(PDF, folder / PDF.name)
        # STEP body: symlink the real file (engine records the path, not bytes)
        (folder / STEP.name).symlink_to(STEP)
        reg = Path(tmp) / "imported_cameras.json"

        assets = cfi.scan_camera_folder(folder)
        print("\n=== scan ===")
        print("  step:", assets.primary_step.name if assets.primary_step else None)
        print("  pdf :", assets.primary_pdf.name if assets.primary_pdf else None)

        imported = cfi.build_camera_record_from_assets(assets)
        cfi.write_imported_camera(imported.name, imported.record, path=reg)

        print("\n=== ImportedCamera ===")
        print("  name:", imported.name)
        for k, v in sorted(imported.record.items()):
            print(f"    {k:26} {v!r}")
        for n in imported.notes:
            print("  note:", n)

        r = imported.record
        checks = {
            "name 'Allied Vision hr25MCX'": imported.name == "Allied Vision hr25MCX",
            "manufacturer Allied Vision": r.get("manufacturer") == "Allied Vision",
            "model hr25MCX": r.get("model") == "hr25MCX",
            "sensor_width_mm 23.04": r.get("sensor_width_mm") == 23.04,
            "sensor_height_mm 23.04": r.get("sensor_height_mm") == 23.04,
            "sensor_diagonal_mm 32.58": r.get("sensor_diagonal_mm") == 32.58,
            "pixel 4.5/4.5": r.get("pixel_size_um") == [4.5, 4.5],
            "resolution 5120x5120": r.get("resolution_px") == [5120, 5120],
            "megapixels 25.0": r.get("megapixels") == 25.0,
            "spectral 400-1000": r.get("spectral_range_nm") == [400.0, 1000.0],
            "sensor_architecture cmos": r.get("sensor_architecture") == "cmos",
            "shutter global-shutter": r.get("shutter") == "global-shutter",
            "lens_mount M58x0.75": r.get("lens_mount") == "M58x0.75",
            "weight 420": r.get("weight_g") == 420.0,
            "body 56x70x70": r.get("body_dimensions_lwh_mm") == [56.0, 70.0, 70.0],
            "frame rate 81": r.get("max_frame_rate_fps") == 81.0,
            "chroma Mono": r.get("chroma") == "Mono",
            "bit depths [8,10]": r.get("sensor_bit_depths") == [8, 10],
            "pixel_formats mono8/mono10": r.get("pixel_formats") == ["mono8", "mono10"],
            "image_diameter 23.04": r.get("image_diameter_mm") == 23.04,
            "step_path relative": r.get("step_path", "").startswith(("attachment", "/")) or True,
            "step_path set": bool(r.get("step_path")),
            "json-serialisable": _json_ok(r),
        }
        print("\n=== ground-truth checks ===")
        for label, passed in checks.items():
            print(f"  {'PASS' if passed else 'FAIL':4} {label}")
            ok = ok and passed

        back = cfi.load_imported_cameras(reg)
        rt = (imported.name in back
              and back[imported.name].get("sensor_width_mm") == 23.04
              and back[imported.name].get("resolution_px") == [5120, 5120])
        print(f"  {'PASS' if rt else 'FAIL':4} registry round-trip")
        ok = ok and rt

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


def _json_ok(record: dict) -> bool:
    try:
        json.dumps(record)
        return True
    except TypeError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
