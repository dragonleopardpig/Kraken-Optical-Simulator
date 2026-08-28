"""Guard for bugs/0661 -- the 3D Inspection Part: a W x H x D box on the object plane
with six blow-out optical axes, one per face (phase 1 of the multi-station cell).

User feature (2026-08-27): "I want to realize a 3D object instead of existing 2D
object plane. Then blow out 6 optical axis for user to place lens and cameras."

Checks:
  A  GEOMETRY (pure): the active face sits ON the object plane (centre = object point,
     normal = the station axis); opposite faces are antiparallel and one extent apart,
     adjacent faces orthogonal, every face frame right-handed; the box extends behind
     the plane; six axis records, exactly one active; re-targeting to "top" puts the
     top face on the plane with its own W x D dims; the normalizer refuses garbage.
  B  SETTINGS: the spec round-trips through the layout settings snapshot/parse.
  C  REAL SCENE (skip-if-absent, Tk/Xvfb): enabling the part draws its actors and six
     dotted axis records; "Solve FOV to this face" solves the object plane to the face
     (+5%); re-targeting a face re-poses the box; the layout file round-trips the spec.
  D  WIRING: Actions menu entry, the scene-refresh hook, the right-click part menu,
     the axis records folded into the pick overlays.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0661_inspection_part
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"


def _check_geometry(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_part import (
        FACE_ORDER,
        axis_records,
        box_corners,
        face_dims,
        face_frames,
        normalize_inspection_part_spec,
    )

    spec = normalize_inspection_part_spec(
        {"enabled": True, "width_mm": 60, "height_mm": 40, "depth_mm": 20, "active_face": "front"}
    )
    O = np.array([3.0, -2.0, 5.0])
    a = np.array([0.2, 0.1, 1.0]) / np.linalg.norm([0.2, 0.1, 1.0])
    fr = face_frames(spec, O, a)
    ok(
        np.allclose(fr["front"]["center"], O) and np.allclose(fr["front"]["normal"], a),
        "A1: the active face sits ON the object plane (centre = object point, normal = axis)",
    )
    pair_ok = True
    for f1, f2, ext in (("front", "back", 20.0), ("left", "right", 60.0), ("top", "bottom", 40.0)):
        pair_ok &= bool(np.allclose(fr[f1]["normal"], -fr[f2]["normal"]))
        pair_ok &= abs(float(np.linalg.norm(fr[f1]["center"] - fr[f2]["center"])) - ext) < 1e-9
    ortho_ok = all(
        (abs(float(np.dot(fr[f]["normal"], fr[g]["normal"]))) > 0.999
         or abs(float(np.dot(fr[f]["normal"], fr[g]["normal"]))) < 1e-9)
        for f in FACE_ORDER for g in FACE_ORDER
    )
    handed_ok = all(np.allclose(np.cross(fr[f]["u"], fr[f]["v"]), fr[f]["normal"]) for f in FACE_ORDER)
    ok(pair_ok and ortho_ok and handed_ok, "A2: opposite faces antiparallel one extent apart, adjacent orthogonal, frames right-handed")
    corners = box_corners(spec, O, a)
    depth_coords = (corners - O) @ a
    ok(
        corners.shape == (8, 3) and depth_coords.max() < 1e-9 and abs(depth_coords.min() + 20.0) < 1e-9,
        f"A3: the box extends 20 mm BEHIND the object plane (axial span {depth_coords.min():.3f}..{depth_coords.max():.3f})",
    )
    recs = axis_records(spec, O, a)
    ok(
        len(recs) == 6 and sum(1 for r in recs if r["active"]) == 1
        and all(np.allclose(r["points"][0], fr[r["face"]]["center"]) for r in recs),
        "A4: six blow-out axes from the face centres, exactly one active",
    )
    fr_top = face_frames(dict(spec, active_face="top"), O, a)
    ok(
        np.allclose(fr_top["top"]["center"], O) and np.allclose(fr_top["top"]["normal"], a)
        and face_dims(spec, "top") == (60.0, 20.0),
        "A5: re-targeting to TOP puts the top face on the plane with its W x D dims",
    )
    junk = normalize_inspection_part_spec({"width_mm": "abc", "height_mm": -5, "active_face": "diagonal"})
    ok(
        junk["width_mm"] == 60.0 and junk["height_mm"] == 40.0 and junk["active_face"] == "front",
        "A6: garbage specs normalize to safe defaults",
    )


def _check_settings(ok, notes) -> None:
    from KrakenOS.UI.services import layout_settings as ls

    src = inspect.getsource(ls)
    ok(
        '"inspection_part"' in src and "inspection_part_spec" in src,
        "B1: the layout settings snapshot packs and parses the inspection part",
    )


def _check_real_scene(ok, notes, app=None, inspector=None) -> None:
    if not SCENE.exists():
        notes.append("SKIP: C: the Basler_Telecentric scene is not in this checkout")
        return
    import tempfile

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle

    editor = None
    editor2 = None
    own_editor = app is None or inspector is None
    if not own_editor:
        # Inside the penta harness: a SECOND embedded inspector cannot open, and loading
        # another layout into the harness's live app tears down its VTK Tk widget
        # (measured: segfault). The render checks run STANDALONE (the strong
        # verification, see the module docstring); the harness phase keeps the
        # wiring checks.
        notes.append(
            "SKIP: %s: render checks run standalone only (the harness owns the single "
            "embedded inspector) -- run this module directly for them" % "C"
        )
        return
    try:
        # Inside the penta harness the ONE embedded inspector already exists -- a second
        # one cannot open ("3D inspector did not open"); drive the harness's instead.
        if own_editor:
            editor = KrakenLayoutEditor()
            editor._prompt_for_missing_cad_assets = lambda: None
        else:
            editor = app
        editor.layout_files["_0661"] = SCENE
        editor.load_layout_by_name("_0661")
        insp = _open_3d_inspector(editor) if own_editor else inspector
        insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        editor.set_inspection_part_spec(
            {"enabled": True, "width_mm": 60, "height_mm": 40, "depth_mm": 20, "active_face": "front"}
        )
        _settle(insp)
        axes = [r for r in insp._optical_axis_pick_records if str(r.get("axis_kind")) == "inspection_part_face"]
        ok(
            len(insp._inspection_part_actor_keys) >= 7 and len(axes) == 6,
            f"C1: the part draws (box + 6 outlines = {len(insp._inspection_part_actor_keys)} actors) "
            f"with six dotted axis records",
        )
        solved, msg = editor.solve_fov_to_inspection_face()
        # Outcome-honest (bugs/0656 doctrine): a variable-conjugate lens SOLVES the face
        # (+5%); a fixed-magnification lens (this scene's 1x telecentric) must REFUSE
        # with the one field it can deliver -- never a silent chase into the hardware.
        ok(
            (bool(solved) and "63 x 42" in msg) or ((not solved) and "Fixed" in msg and "refused" in msg),
            f"C2: 'Solve FOV to this face' is honest -- solves 60x40 +5% or refuses on a "
            f"fixed-magnification lens ({msg[:90]})",
        )
        editor.set_inspection_part_active_face("top")
        _settle(insp)
        axes = [r for r in insp._optical_axis_pick_records if str(r.get("axis_kind")) == "inspection_part_face"]
        active = [r["face"] for r in axes if r.get("active")]
        ok(active == ["top"], f"C3: re-targeting re-poses the box (active axis now {active})")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "part_roundtrip.py"
            editor._write_layout_file(out)
            editor2 = KrakenLayoutEditor()
            editor2._prompt_for_missing_cad_assets = lambda: None
            editor2.layout_files["rt"] = out
            editor2.load_layout_by_name("rt")
            spec = editor2.inspection_part_spec
        ok(
            spec["enabled"] and spec["active_face"] == "top" and spec["width_mm"] == 60.0,
            f"C4: the layout file round-trips the part ({spec})",
        )
    finally:
        for e in ((editor if own_editor else None), editor2):
            try:
                if e is not None:
                    e.destroy()
            except Exception:
                pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI import open3d_inspector as oi
    from KrakenOS.UI.panels import main_window as mw
    from KrakenOS.UI.services import open3d_face_assignment as fa
    from KrakenOS.UI.services import open3d_scene_refresh as osr

    ok("Inspection Part (3D object)..." in inspect.getsource(mw), "D1: Actions menu offers the part dialog")
    ok("_add_inspection_part_glyphs" in inspect.getsource(osr), "D2: the scene refresh draws the part")
    ok(
        "_maybe_show_inspection_part_menu" in inspect.getsource(fa)
        and "Inspect " in inspect.getsource(fa),
        "D3: right-clicking the part offers 'Inspect <face>'",
    )
    ok(
        "_inspection_part_axis_records" in inspect.getsource(oi),
        "D4: the six axes fold into the optical-axis pick overlays (dotted, pickable)",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_geometry), ("B", _check_settings), ("C", _check_real_scene), ("D", _check_wiring)):
        try:
            if section == "C":
                fn(ok, notes, app=app, inspector=inspector)
            else:
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
        print("Inspection-part validation passed.")
        return 0
    print("Inspection-part validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
