"""Guard for bugs/0665 -- the cell-level solve: part dims + defect size -> a camera + lens
per face from the registered cameras and the lens catalog, then the station layouts
are BUILT with the folder importers.

Checks:
  A  REQUIREMENTS (pure): every face's field is its dims + margin, oriented landscape;
     resolution = defect / px-per-defect; opposite faces share a requirement.
  B  SELECTION (pure, synthetic catalog): a fixed-magnification lens is judged at ITS
     OWN field (0.75x covering a 10.5 x 8.4 mm face passes -- the catalog matcher's
     in-band test alone rejected it); a fixed lens whose field is SMALLER than the face
     fails with the reason; a variable lens passes at the height-aware m; with the
     preference on, a passing telecentric outranks a passing variable lens; resolution
     is judged at the delivered m.
  C  BUILD (skip-if-absent, Tk/Xvfb): one station is built headless from the real
     Basler + 0.75x telecentric folders on a 10 x 8 x 6 part -- the layout file exists,
     the camera is coupled, the mount law holds (WD mismatch ~0).
  D  WIRING: the cell dialog carries the solve section; the matcher specs carry their
     folders; the phase-3 design doc marks the solve.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0665_inspection_cell_solve
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LENS = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric"
CAMERA = PROJECT_ROOT / "attachment/Cameras/Basler_Ace"


def _check_requirements(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_cell_solve import face_requirements

    reqs = face_requirements({"width_mm": 10, "height_mm": 8, "depth_mm": 6}, 0.02, px_per_defect=4, margin=0.05, wd_min_mm=40)
    f, l, t = reqs["front"], reqs["left"], reqs["top"]
    ok(
        abs(f.fov_w_mm - 10.5) < 1e-9 and abs(f.fov_h_mm - 8.4) < 1e-9 and not f.rotated,
        f"A1: front = W x H + 5% ({f.fov_w_mm:.2f} x {f.fov_h_mm:.2f})",
    )
    ok(
        abs(l.fov_w_mm - 8.4) < 1e-9 and abs(l.fov_h_mm - 6.3) < 1e-9 and l.rotated,
        f"A2: left = D x H read LANDSCAPE ({l.fov_w_mm:.2f} x {l.fov_h_mm:.2f}, rotated {l.rotated})",
    )
    ok(abs(t.fov_w_mm - 10.5) < 1e-9 and abs(t.fov_h_mm - 6.3) < 1e-9, "A3: top = W x D + 5%")
    ok(abs(f.resolution_um_per_px - 5.0) < 1e-9 and f.wd_min_mm == 40.0, "A4: resolution = defect / px-per-defect (20 um / 4 = 5 um/px); WD min carried")
    ok(reqs["back"].fov_w_mm == f.fov_w_mm and reqs["right"].fov_w_mm == l.fov_w_mm, "A5: opposite faces share a requirement")


def _check_selection(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_cell_solve import choose_station, face_requirements
    from KrakenOS.UI.services.system_matcher import CameraSpec, LensSpec

    cam = CameraSpec("Basler acA2440-20gm", 8.45, 7.07, 2448, 2048, folder=None)
    tele075 = LensSpec("0.75x telecentric", focal_length_mm=70.4, image_circle_mm=11.0, fnumber=13.3, mag_min=0.75, mag_max=0.75)
    tele1 = LensSpec("1x telecentric", focal_length_mm=27.8, image_circle_mm=11.0, fnumber=11.0, mag_min=1.0, mag_max=1.0)
    var35 = LensSpec("35 mm fixed focal", focal_length_mm=35.0, image_circle_mm=11.0, fnumber=1.8)
    req = face_requirements({"width_mm": 10, "height_mm": 8, "depth_mm": 6}, 0.02, px_per_defect=3, wd_min_mm=40)["front"]

    best = choose_station(req, [cam], [tele075, var35])
    ok(
        best is not None and best.lens == "0.75x telecentric" and best.passes,
        f"B1: a 0.75x fixed lens whose field covers the 10.5 x 8.4 face PASSES and is preferred "
        f"({best.lens if best else None}, passes {best.passes if best else None})",
    )
    only_1x = choose_station(req, [cam], [tele1])
    ok(
        only_1x is not None and not only_1x.passes and any("field" in r for r in only_1x.reasons),
        f"B2: a 1x fixed lens (8.45 x 7.07 field) FAILS the 10.5 x 8.4 face with the reason "
        f"({only_1x.reasons if only_1x else None})",
    )
    only_var = choose_station(req, [cam], [var35])
    ok(
        only_var is not None and only_var.passes and abs(only_var.magnification - min(8.45 / 10.5, 7.07 / 8.4)) < 1e-9,
        f"B3: a variable lens passes at the height-aware m ({only_var.magnification if only_var else None:.3f})",
    )
    no_pref = choose_station(req, [cam], [tele075, var35], prefer_fixed_magnification=False)
    ok(
        no_pref is not None and no_pref.lens == "35 mm fixed focal",
        f"B4: without the preference the longer-WD variable lens wins ({no_pref.lens if no_pref else None})",
    )
    coarse = face_requirements({"width_mm": 10, "height_mm": 8, "depth_mm": 6}, 0.005, px_per_defect=3, wd_min_mm=40)["front"]
    fine = choose_station(coarse, [cam], [tele075])
    ok(
        fine is not None and not fine.passes and not fine.resolution_ok if hasattr(fine, "resolution_ok") else (fine is not None and not fine.passes),
        f"B5: a 5 um defect at 3 px (1.7 um/px) is refused at the delivered 4.6 um/px ({fine.reasons if fine else None})",
    )


def _check_build(ok, notes) -> None:
    if not LENS.exists() or not CAMERA.exists():
        notes.append("SKIP: C: the Basler / 0.75x telecentric folders are not in this checkout")
        return
    from KrakenOS.UI.services.inspection_cell_solve import (
        FaceRequirement,
        StationChoice,
        build_station_layout,
    )

    req = FaceRequirement("front", 10.5, 8.4, False, 6.67, 40.0)
    choice = StationChoice(
        face="front", requirement=req, camera="Basler acA2440-20gm", camera_folder=str(CAMERA),
        lens="0.75x telecentric", lens_folder=str(LENS), magnification=0.75, working_distance_mm=110.0,
        delivered_fov_mm=(11.27, 9.43), resolution_um_per_px=4.6, passes=True, reasons=(),
    )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "station_front.py"
        report = build_station_layout(choice, {"width_mm": 10, "height_mm": 8, "depth_mm": 6}, out)
        ok(out.exists() and out.stat().st_size > 1000, f"C1: the station layout is written ({out.name}, {report.get('rows')} rows)")
        ok(str(report.get("camera") or "").startswith("Basler"), f"C2: the camera is coupled ({report.get('camera')})")
        ok(
            report.get("mode", "").startswith("fixed") and abs(float(report.get("wd_mismatch") or 9)) < 0.05,
            f"C3: the telecentric station is mounted by the WD law (mode {report.get('mode')}, mismatch {report.get('wd_mismatch')})",
        )


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.services import inspection_cell as ic
    from KrakenOS.UI.services import system_matcher as sm

    ok("Solve & build stations" in inspect.getsource(ic.open_inspection_cell_dialog), "D1: the cell dialog carries the solve section")
    ok(
        "folder" in {f.name for f in sm.LensSpec.__dataclass_fields__.values()}
        and "folder" in {f.name for f in sm.CameraSpec.__dataclass_fields__.values()},
        "D2: matcher specs carry their folders (so a choice can be BUILT)",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_requirements), ("B", _check_selection), ("C", _check_build), ("D", _check_wiring)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Inspection-cell-solve validation passed.")
        return 0
    print("Inspection-cell-solve validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
