"""Guard for bugs/0655 -- a camera folder imports from an Edmund stock-page PDF, and
EVERY bundled PDF is tried (the mechanical drawing sorting first must not veto the
spec sheet beside it).

The user's error.png (2026-08-27 13:48): "Could not import a camera from this folder:
.../Cameras/Basler_Ace ... Could not extract a sensor size". Two independent causes:

  1. `build_camera_record_from_assets` parsed ONLY `assets.primary_pdf` -- the
     alphabetically-first PDF, here the Basler MECHANICAL DRAWING (664 chars of title
     block). The Edmund spec sheet the user dropped beside it (`spec_35917.pdf`,
     sensor rows and all) was never opened. Now every PDF is tried in order and the
     first that yields a sensor size feeds the record; the record's `datasheet`
     pointer names the PDF that actually fed it.
  2. The Edmund camera stock-page rows use their own labels, all label-glued:
     "Sensing Area, H x V (mm):8.45 x 7.07" (the sensor size DIRECTLY),
     "Pixels (H x V):2,448 x 2,048", "Pixel Size, H x V (um):3.45 x 3.45",
     "Model Number:acA2440-20gm", "Mount:C-Mount". None matched. Also latent: the
     flange lookup keyed "C-MOUNT" against a table keyed "C" -- every "-Mount"
     suffixed spelling silently missed the standard FFD.

Checks:
  A  PARSER on embedded Edmund-format text: sensing area, pixels row, pixel-size
     row, model number, mount row -> C flange 17.526; and resolution x pitch
     cross-checks the stated sensing area.
  B  WIRING: the builder iterates `assets.pdf_files` (not primary-only) and re-points
     the record's datasheet at the feeding PDF; the flange lookup strips "-MOUNT".
  C  REAL FOLDER (skip-if-absent): Basler_Ace imports -- sensor 8.45 x 7.07,
     2448 x 2048 @ 3.45 um, front->sensor 17.526, datasheet = spec_35917.pdf.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0655_edmund_camera_stock_page
"""

from __future__ import annotations

import inspect
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOLDER = PROJECT_ROOT / "attachment/Cameras/Basler_Ace"

_EDMUND_TEXT = (
    "Basler ace acA2440-20gm Monochrome GigE Camera#35-917"
    "Model Number:acA2440-20gmManufacturer:BaslerCamera Series:ace"
    "Dimensions (mm):42 x 29 x 29 (excludes connectors and lens mount)Weight (g):90"
    "SensorSensor Format:2/3\"Resolution (Megapixels):5.00Frame Rate (fps):23.00"
    "Pixels (H x V):2,448 x 2,048Pixel Size, H x V (μm):3.45 x 3.45"
    "Sensing Area, H x V (mm):8.45 x 7.07Imaging Sensor:Sony IMX264"
    "Threading & MountingMount:C-MountMounting Threads:1/4-20 with Tripod Mount Adapter #88-517"
)


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import camera_folder_import as cfi

    # ---------------------------------------------------------------- A: parser
    a_problems = []
    import tempfile

    # Route the embedded text through the real parser by stubbing the extractor.
    original = cfi.extract_pdf_text
    try:
        cfi.extract_pdf_text = lambda path: _EDMUND_TEXT
        spec = cfi.parse_camera_datasheet("stub.pdf")
    finally:
        cfi.extract_pdf_text = original
    if spec is None:
        a_problems.append("the Edmund text yields no spec at all")
    else:
        if (spec.sensor_width_mm, spec.sensor_height_mm) != (8.45, 7.07):
            a_problems.append(f"sensing area misread: {spec.sensor_width_mm} x {spec.sensor_height_mm}")
        if spec.resolution_px != (2448, 2048):
            a_problems.append(f"pixels row misread: {spec.resolution_px}")
        if spec.pixel_size_um != (3.45, 3.45):
            a_problems.append(f"pixel-size row misread: {spec.pixel_size_um}")
        if spec.model != "acA2440-20gm":
            a_problems.append(f"model number misread: {spec.model!r}")
        if spec.camera_front_to_sensor_mm != 17.526:
            a_problems.append(
                f"'Mount:C-Mount' did not resolve the standard C flange "
                f"(got {spec.camera_front_to_sensor_mm})"
            )
        if spec.resolution_px and spec.pixel_size_um:
            w = spec.resolution_px[0] * spec.pixel_size_um[0] / 1000.0
            h = spec.resolution_px[1] * spec.pixel_size_um[1] / 1000.0
            if abs(w - 8.45) > 0.01 or abs(h - 7.07) > 0.01:
                a_problems.append(
                    f"resolution x pitch ({w:.2f} x {h:.2f}) does not corroborate the "
                    f"stated sensing area"
                )
    if a_problems:
        ok = False
        notes.append(f"FAIL: A (bugs/0655): {a_problems}")
    else:
        notes.append("PASS: A: the Edmund camera stock-page rows parse; pitch corroborates area")

    # ---------------------------------------------------------------- B: wiring
    b_problems = []
    build_src = inspect.getsource(cfi.build_camera_record_from_assets)
    if "for pdf in assets.pdf_files" not in build_src:
        b_problems.append(
            "the builder parses only the primary PDF again (a drawing sorting first "
            "vetoes the spec sheet beside it)"
        )
    if "_project_relative(spec_pdf)" not in build_src:
        b_problems.append("the record's datasheet pointer is not re-pointed at the feeding PDF")
    flange_src = inspect.getsource(cfi._scrape_flange)
    if '"-MOUNT"' not in flange_src:
        b_problems.append('the flange lookup no longer strips the "-MOUNT" suffix')
    if b_problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0655): {b_problems}")
    else:
        notes.append("PASS: B: every PDF tried in order; datasheet pointer + flange suffix wired")

    # ---------------------------------------------------------------- C: real folder
    if FOLDER.exists():
        c_problems = []
        try:
            cam = cfi.import_camera_folder(FOLDER, persist=False)
            r = cam.record
            if (r.get("sensor_width_mm"), r.get("sensor_height_mm")) != (8.45, 7.07):
                c_problems.append(f"sensor: {r.get('sensor_width_mm')} x {r.get('sensor_height_mm')}")
            if list(r.get("resolution_px") or []) != [2448, 2048]:
                c_problems.append(f"resolution: {r.get('resolution_px')}")
            if r.get("camera_front_to_sensor_mm") != 17.526:
                c_problems.append(f"front->sensor: {r.get('camera_front_to_sensor_mm')}")
            if "spec_35917" not in str(r.get("datasheet") or ""):
                c_problems.append(
                    f"datasheet points at {r.get('datasheet')} -- not the sheet that fed it"
                )
        except Exception as exc:
            c_problems = [f"import raised {type(exc).__name__}: {exc}"]
        if c_problems:
            ok = False
            notes.append(f"FAIL: C (bugs/0655): {c_problems}")
        else:
            notes.append("PASS: C: the real Basler_Ace folder imports (the error.png case)")
    else:
        notes.append("SKIP: C: the Basler_Ace folder is not in this checkout")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Edmund-camera-stock-page validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
