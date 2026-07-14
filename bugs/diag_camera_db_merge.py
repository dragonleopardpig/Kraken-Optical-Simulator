"""Verify camera_database folds the imported-camera registry JSON into
CAMERA_DATABASE: an imported camera must appear in camera_names(), keep tuple /
absolute-Path parity with built-ins, and reverse-resolve from its STEP path via
camera_model_for_step_path -- so importing the vendor STEP couples the sensor
exactly like a built-in.  A built-in name in the registry must NOT be overridden.

Run: .devenv/state/venv/bin/python bugs/diag_camera_db_merge.py
"""
from __future__ import annotations

import importlib
import json
import tempfile
from pathlib import Path

from KrakenOS.UI.services import camera_folder_import as cfi

CAMERAS = Path("attachment/Cameras").resolve()
PDF = CAMERAS / "hr25MCX_Datasheet.pdf"
STEP = CAMERAS / "3D_CAD_HR25xCXP.STEP"


def main() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp) / "Contoso Vision cx99MCX"
        folder.mkdir()
        # Reuse the real hr25 datasheet body (so the scrape yields a full record)
        # but give the STEP a UNIQUE name/file so the reverse-lookup can't collide
        # with the built-in "Allied Vision hr25MCX" that owns 3D_CAD_HR25xCXP.STEP.
        (folder / PDF.name).symlink_to(PDF)
        step = folder / "3D_CAD_CX99.STEP"
        step.write_bytes(b"ISO-10303-21;\nENDSEC;\n")  # dummy body; engine records path only
        reg = Path(tmp) / "imported_cameras.json"

        imported = cfi.import_camera_folder(folder, persist=False)
        cfi.write_imported_camera(imported.name, imported.record, path=reg)
        name = imported.name
        print("imported name:", name)

        # Point the DB merge hook at our temp registry, then re-run it.
        import KrakenOS.UI.camera_database as db
        importlib.reload(db)
        db._merge_imported_cameras(reg)

        checks = {
            "appears in camera_names()": name in db.camera_names(),
            "record present": db.camera_record(name) is not None,
        }
        rec = db.camera_record(name) or {}
        checks["resolution_px is tuple"] = isinstance(rec.get("resolution_px"), tuple)
        checks["pixel_size_um is tuple"] = isinstance(rec.get("pixel_size_um"), tuple)
        checks["pixel_formats is tuple"] = isinstance(rec.get("pixel_formats"), tuple)
        step_path = rec.get("step_path")
        checks["step_path is absolute Path"] = (
            isinstance(step_path, Path) and step_path.is_absolute()
        )
        checks["step_path resolves to file"] = (
            isinstance(step_path, Path) and step_path.resolve() == step.resolve()
        )
        # The whole point: importing the vendor STEP reverse-resolves to this model.
        checks["camera_model_for_step_path(STEP path)"] = (
            db.camera_model_for_step_path(step_path) == name
        )
        checks["camera_model_for_step_path(bare filename)"] = (
            db.camera_model_for_step_path("3D_CAD_CX99.STEP") == name
        )
        checks["sensor coverage present"] = (
            db.camera_image_coverage_mm(name) is not None
        )
        checks["short summary non-empty"] = bool(db.camera_short_summary(name))

        # Built-ins must win: seed the registry with a built-in name + junk record
        # and confirm the merge refuses to clobber it.
        reg2 = Path(tmp) / "reg2.json"
        reg2.write_text(json.dumps({
            "Allied Vision hr25MCX": {"sensor_width_mm": 999.0},
        }), encoding="utf-8")
        db._merge_imported_cameras(reg2)
        builtin = db.camera_record("Allied Vision hr25MCX") or {}
        checks["built-in NOT overridden"] = builtin.get("sensor_width_mm") == 23.04

        print("\n=== merge checks ===")
        for label, passed in checks.items():
            print(f"  {'PASS' if passed else 'FAIL':4} {label}")
            ok = ok and passed

    print("\nRESULT:", "ALL PASS" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
