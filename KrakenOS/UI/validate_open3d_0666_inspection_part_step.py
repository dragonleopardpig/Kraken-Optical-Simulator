"""Guard for bugs/0666 -- a STEP of the REAL part: its native bounding box sizes the
six-face model (x -> W, y -> H, z -> D, +z = Front) and its mesh replaces the box in the
station scene, the cell view, and the cell STEP.

Checks:
  A  GEOMETRY (pure): `part_frame` reproduces `face_frames` (same R / centre; the box
     corners are unchanged); a synthetic mesh's bounds size the spec; the portable path
     round-trips (project-relative inside the project, absolute outside);
     `part_mesh_world` moves the mesh's AABB centre onto the part centre and its +z
     face onto the active face's plane.
  B  CELL (skip-if-absent, Tk/Xvfb): a real STEP (the Basler body as a stand-in part)
     + one station compose with the part mesh drawn (`report["part_mesh"]`), and the
     cell STEP export embeds the part shape centred at the origin.
  C  WIRING: the station glyph loads the STEP; both dialogs carry the STEP entry; the
     spec normalizer keeps `step_path`.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0666_inspection_part_step
"""

from __future__ import annotations

import inspect
import tempfile
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PART_STEP = PROJECT_ROOT / "attachment/Cameras/Basler_Ace/Basler ace GigE C-Mount v01.STP"
FRONT_SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"


def _check_geometry(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_part import (
        apply_step_bounds,
        box_corners,
        face_frames,
        normalize_inspection_part_spec,
        part_frame,
        part_mesh_world,
        portable_part_step_text,
    )

    spec = normalize_inspection_part_spec({"enabled": True, "width_mm": 30, "height_mm": 20, "depth_mm": 10, "active_face": "left"})
    O = np.array([4.0, 1.0, -2.0])
    a = np.array([0.1, 0.9, 0.3]) / np.linalg.norm([0.1, 0.9, 0.3])
    R, centre = part_frame(spec, O, a)
    fr = face_frames(spec, O, a)
    ok(
        np.allclose(R @ np.array([0, 0, 1.0]), fr["front"]["normal"]) and np.allclose(R @ np.array([1.0, 0, 0]), fr["right"]["normal"])
        and np.allclose(centre, 0.5 * (fr["front"]["center"] + fr["back"]["center"])),
        "A1: part_frame agrees with face_frames (R maps local z/x onto front/right normals; centre = box centre)",
    )
    ok(np.allclose(box_corners(spec, O, a).mean(axis=0), centre), "A2: the box corners are unchanged by the refactor")

    class _Mesh:
        def __init__(self, pts):
            self.points = np.asarray(pts, dtype=float)

        def copy(self, deep=True):
            return _Mesh(self.points.copy())

    synthetic = _Mesh([[1, 2, 3], [11, 6, 8], [5, 4, 5]])
    sized = apply_step_bounds({"active_face": "top"}, synthetic)
    ok(
        (sized["width_mm"], sized["height_mm"], sized["depth_mm"]) == (10.0, 4.0, 5.0) and sized["active_face"] == "top",
        f"A3: STEP bounds size the spec (x->W, y->H, z->D): {sized['width_mm']} x {sized['height_mm']} x {sized['depth_mm']}",
    )
    inside = portable_part_step_text(str(PROJECT_ROOT / "attachment" / "part.step"))
    outside = portable_part_step_text("/nonexistent/elsewhere/part.step")
    ok(
        inside == "attachment/part.step" and outside == "/nonexistent/elsewhere/part.step",
        f"A4: the STEP path stores project-relative inside the project ({inside}) and absolute outside",
    )
    placed = part_mesh_world(synthetic, sized, O, a)
    pts = np.asarray(placed.points)
    c = 0.5 * (pts.min(axis=0) + pts.max(axis=0))
    R2, centre2 = part_frame(sized, O, a)
    ok(np.allclose(c, centre2, atol=1e-9), "A5: part_mesh_world moves the mesh AABB centre onto the part centre")
    # the mesh's +z extreme lands on the FRONT face plane: front centre + normal * 0 (z max -> front)
    frames2 = face_frames(sized, O, a)
    zmax_pt = pts[np.argmax((pts - c) @ frames2["front"]["normal"])]
    depth_from_front = float((zmax_pt - frames2["front"]["center"]) @ frames2["front"]["normal"])
    ok(abs(depth_from_front) < 1e-9, f"A6: the STEP's +z face lands on the part's Front face plane (offset {depth_from_front:.2e})")


def _check_cell(ok, notes) -> None:
    if not PART_STEP.exists() or not FRONT_SCENE.exists():
        notes.append("SKIP: B: the stand-in part STEP / station scene are not in this checkout")
        return
    from KrakenOS.UI.services.inspection_cell import compose_cell_plotter, export_cell_step, normalize_cell_spec

    cell = normalize_cell_spec(
        {
            "part": {"width_mm": 42, "height_mm": 29, "depth_mm": 29, "step_path": str(PART_STEP)},
            "stations": {"front": {"layout": str(FRONT_SCENE), "enabled": True}},
        }
    )
    ok(cell["part"]["step_path"].startswith("attachment/"), f"B0: the cell stores the part STEP portably ({cell['part']['step_path']})")
    plotter, report = compose_cell_plotter(cell, off_screen=True)
    try:
        ok(report.get("part_mesh") is True and not report["errors"], f"B1: the cell view draws the real part mesh (errors {report['errors']})")
        ok("cell_part_step" in plotter.renderer.actors, "B2: the part mesh actor is in the composed scene")
    finally:
        try:
            plotter.close()
        except Exception:
            pass
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "cell.step"
        rep = export_cell_step(cell, out)
        ok(rep.get("part_mesh") is True and out.exists() and out.stat().st_size > 10000, f"B3: the cell STEP embeds the part shape ({out.stat().st_size} bytes)")


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI import open3d_inspector as oi
    from KrakenOS.UI.services import inspection_cell as ic
    from KrakenOS.UI.services import inspection_part as ip

    src = inspect.getsource(oi)
    ok("part_mesh_world" in src and "resolve_part_step_path" in src, "C1: the station glyph loads and places the part STEP")
    ok("Part STEP (optional)" in inspect.getsource(ip.open_inspection_part_dialog), "C2: the part dialog offers the STEP")
    ok("Part STEP (optional)" in inspect.getsource(ic.open_inspection_cell_dialog), "C3: the cell dialog offers the STEP")
    ok(ip.normalize_inspection_part_spec({"step_path": "x.step"})["step_path"] == "x.step", "C4: the spec keeps step_path")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_geometry), ("B", _check_cell), ("C", _check_wiring)):
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
        print("Inspection-part-STEP validation passed.")
        return 0
    print("Inspection-part-STEP validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
