"""Guard for bugs/0663 -- the Inspection Cell: six station layouts composed around one
3D part in a single scene (phase 2 of the multi-station design).

User request (2026-08-27/30): six cameras inspecting a rectangular part's six faces,
"blow out 6 optical axis for user to place lens and cameras". A layout stays ONE
imaging chain; the cell loads each station HEADLESS, traces it on its own, and places
its bodies/rays under the rigid transform carrying its object plane onto its face --
the two-arm precedent (per-arm sequential traces composed by display transforms)
generalised to N arms.

Checks:
  A  TRANSFORM (pure): the station->face transform maps the object point onto the face
     centre, the object axis onto the outward normal, and the field-width direction
     onto the face width; it is rigid (orthonormal, det +1); the cell part box is
     centred at the origin with its six faces where cell_part_frames says.
  B  CELL FILE: the spec normalizes and round-trips through .cell.json.
  C  COMPOSITION (skip-if-absent, Tk/Xvfb, headless): two real station layouts on two
     faces compose off-screen -- each contributes actors, each station's object plane
     lands on its face centre (<1e-6 mm), the interference report runs, a screenshot
     renders.
  D  WIRING: Actions menu entry + editor method; the composite STEP path uses the
     native per-station export transformed into one compound.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0663_inspection_cell
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONT_SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"
TOP_SCENE = PROJECT_ROOT / "attachment/machine_vision_Pyrite90_0.3X.py"


def _check_transform(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_cell import (
        apply_transform,
        cell_part_corners,
        cell_part_frames,
        station_frame_transform,
    )
    from KrakenOS.UI.services.inspection_part import plane_basis

    part = {"width_mm": 60, "height_mm": 40, "depth_mm": 20}
    frames = cell_part_frames(part)
    corners = cell_part_corners(part)
    centre = corners.mean(axis=0)
    ok(np.allclose(centre, 0.0, atol=1e-9), f"A1: the cell part box is centred at the origin (centre {np.round(centre, 6)})")
    ok(
        np.allclose(frames["front"]["center"], [0, 0, 10]) and np.allclose(frames["top"]["normal"], [0, 1, 0])
        and np.allclose(frames["right"]["normal"], [1, 0, 0]),
        "A2: faces sit where the box says (front at +z = D/2, top normal +y, right normal +x)",
    )
    O = np.array([12.0, -3.0, 7.0])
    a = np.array([0.3, 0.2, 1.0]) / np.linalg.norm([0.3, 0.2, 1.0])
    u_s, _ = plane_basis(a)
    fr = frames["top"]
    T = station_frame_transform(O, a, fr["center"], fr["normal"], fr["u"])
    R = T[:3, :3]
    ok(
        np.allclose(apply_transform(T, O)[0], fr["center"]) and np.allclose(R @ a, fr["normal"])
        and np.allclose(R @ u_s, fr["u"]),
        "A3: object point -> face centre, object axis -> face normal, field width -> face width",
    )
    ok(
        np.allclose(R @ R.T, np.eye(3), atol=1e-9) and abs(float(np.linalg.det(R)) - 1.0) < 1e-9,
        "A4: the transform is rigid (orthonormal, det +1 -- no mirror)",
    )


def _check_cell_file(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_cell import CELL_SUFFIX, load_cell, normalize_cell_spec, save_cell

    spec = normalize_cell_spec({"part": {"width_mm": 30}, "stations": {"left": {"layout": "/tmp/x.py"}}})
    with tempfile.TemporaryDirectory() as tmp:
        path = save_cell(Path(tmp) / "demo", spec)
        back = load_cell(path)
    ok(
        path.name.endswith(CELL_SUFFIX) and back == spec and back["stations"]["left"]["enabled"]
        and not back["stations"]["front"]["enabled"] and back["part"]["enabled"],
        "B1: the cell spec normalizes (a slotted layout enables its face) and round-trips",
    )


def _check_composition(ok, notes) -> None:
    if not FRONT_SCENE.exists() or not TOP_SCENE.exists():
        notes.append("SKIP: C: the two station scenes are not in this checkout")
        return
    from KrakenOS.UI.services.inspection_cell import (
        cell_part_frames,
        compose_cell_plotter,
        normalize_cell_spec,
    )

    cell = normalize_cell_spec(
        {
            "part": {"width_mm": 60, "height_mm": 40, "depth_mm": 20},
            "stations": {
                "front": {"layout": str(FRONT_SCENE), "enabled": True},
                "top": {"layout": str(TOP_SCENE), "enabled": True},
            },
        }
    )
    plotter, report = compose_cell_plotter(cell, off_screen=True)
    try:
        ok(
            not report["errors"] and len(report["stations"]) == 2
            and all(st["actors"] > 0 for st in report["stations"]),
            f"C1: both stations compose ({[(s['face'], s['actors']) for s in report['stations']]}; "
            f"errors {report['errors']})",
        )
        frames = cell_part_frames(cell["part"])
        worst = max(
            (float(np.linalg.norm(np.asarray(st["object_point_cell"]) - frames[st["face"]]["center"]))
             for st in report["stations"]),
            default=float("inf"),
        )
        ok(worst < 1e-6, f"C2: every station's object plane lands on its face centre (worst {worst:.2e} mm)")
        ok(isinstance(report["interferences"], list), "C3: the interference report runs")
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "cell.png"
            plotter.camera_position = "iso"
            plotter.screenshot(str(png), window_size=(800, 600))
            ok(png.exists() and png.stat().st_size > 5000, "C4: the composite view renders to a screenshot")
    finally:
        try:
            plotter.close()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.panels import main_window as mw
    from KrakenOS.UI.services import inspection_cell as ic
    from KrakenOS.UI.services import layout_table_workbench as wb

    ok("Inspection Cell (6 stations)..." in inspect.getsource(mw), "D1: Actions menu offers the cell dialog")
    ok(
        any("open_inspection_cell_dialog" in vars(c) for c in vars(wb).values() if isinstance(c, type)),
        "D2: the editor has open_inspection_cell_dialog",
    )
    src = inspect.getsource(ic.export_cell_step)
    ok(
        "_write_step_with_cad_shapes_and_rays" in src and "_shape_with_affine" in src and "MakeCompound" in src,
        "D3: the cell STEP composes each station's NATIVE export, transformed, into one compound",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_transform), ("B", _check_cell_file), ("C", _check_composition), ("D", _check_wiring)):
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
        print("Inspection-cell validation passed.")
        return 0
    print("Inspection-cell validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
