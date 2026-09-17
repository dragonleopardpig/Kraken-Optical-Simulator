"""bugs/0810 -- a cache is a recipe.

"I sometimes see errors when you run validation but ignore them (previous known errors). Can you fix
them all?" The census of every penta phase found four that never finish (449-452) and a dozen that fail
with "file not found" or "0 folded rays" (169, 170, 181-194). One cause: 23 derived files under
``attachment/cad_cache`` -- promoted-body STLs and a generated beam-splitter template -- had been deleted
(Filen moved them to its trash), 132 references across 15 saved scenes, and:

* loading such a scene opened the MODAL missing-assets dialog, which no automated run can close;
* guards that build rows without the load path lost the body (neutralised at system build);
* and the one rebuild that existed (bugs/0021) re-meshed an overlay-promoted body in the STEP's native
  frame and repointed the row at it -- face S001/F001 at x -8.84 where the scene records +12.5.

The scene already records every recipe, and the face table proves a rebuild. Measured: all 21 rebuilt
caches reproduce their recorded faces, and the overlay bodies come back bit-identical to the originals
recovered from the trash (identical triangles, 0.0 vertex deviation).

A pure checks; B-D need Tk + OCC (SKIP otherwise); E the live load (standalone only).
"""

from __future__ import annotations

import contextlib
import copy
import io
import shutil
import tempfile
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ELS85 = PROJECT_ROOT / "attachment" / "machine_vision_ELS85.py"
GN150 = PROJECT_ROOT / "attachment" / "machine_vision_150mm_GN.py"


def _quiet():
    stack = contextlib.ExitStack()
    stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
    stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
    return stack


def _row_with(scene: Path, needle: str) -> "dict | None":
    import KrakenOS.UI.layout_editor as le

    with _quiet():
        info = le._load_python_data(scene)
    for item in info.get("surfaces") or []:
        advanced = item.get("advanced") or {}
        if needle in str(advanced.get("Solid_3d_stl", "")):
            return copy.deepcopy(advanced)
    return None


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    import pyvista as pv

    from KrakenOS.UI.services import beam_splitter_factory as bsf
    from KrakenOS.UI.services import cad_cache_recipes as recipes

    # ---- A: the proof is the recorded face table -----------------------------------------------------
    box = pv.Box(bounds=(-5.0, 5.0, -2.0, 2.0, -1.0, 1.0)).triangulate()
    tri = np.asarray(box.faces).reshape(-1, 4)[:, 1:]
    pts = np.asarray(box.points, dtype=float)
    faces = []
    for k in range(0, len(tri), 2):
        corners = pts[tri[[k, k + 1]]]
        cross = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        areas = 0.5 * np.linalg.norm(cross, axis=1)
        centroid = (corners.mean(axis=1) * areas[:, None]).sum(axis=0) / areas.sum()
        normal = cross.sum(axis=0) / np.linalg.norm(cross.sum(axis=0))
        faces.append({"face_id": f"F{k // 2}", "triangle_indices": [k, k + 1], "centroid": centroid.tolist(),
                      "area_mm2": float(areas.sum()), "normal": normal.tolist()})
    table = {"OpticalSolidFaces": {"faces": faces}}
    checked, problem = recipes.face_table_mismatch(box, table)
    ok(problem is None and checked == len(faces), f"A1: a mesh reproduces its own face table ({checked} faces)")
    moved = box.copy(deep=True)
    moved.points = pts + np.array([0.01, 0.0, 0.0])
    ok(recipes.face_table_mismatch(moved, table)[1] is not None, "A2: 10 um of displacement is caught")
    turned = box.copy(deep=True)
    turned.points = pts[:, [1, 0, 2]]
    ok(recipes.face_table_mismatch(turned, table)[1] is not None, "A3: the same body in another pose is caught")

    # ---- B: a template is rebuilt only from parameters that hash to its name -------------------------
    params = {"width_mm": 105.5, "height_mm": 77.0, "thickness_mm": 1.1, "tilt_deg": 45.0}
    name = bsf.beam_splitter_cache_path("plate", bsf._normalize_plate_params(105.5, 77.0, 1.1, 45.0)).name
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / name
        try:
            built, note = recipes.rebuild_beam_splitter_template(target, {"StepOverlayPromotion": {"beam_splitter_params": params}})
        except Exception as exc:
            built, note = False, f"raised {exc}"
        if "OCC" in note or "pythonocc" in note.lower():
            notes.append(f"SKIP: B: OCC unavailable ({note})")
        else:
            ok(built and target.exists() and target.stat().st_size > 0, f"B1: {note}")
            wrong = dict(params, thickness_mm=2.0)
            (Path(tmp) / name).unlink()
            built2, note2 = recipes.rebuild_beam_splitter_template(Path(tmp) / name, {"beam_splitter_params": wrong})
            ok(not built2 and "different template" in note2, f"B2: parameters that hash elsewhere are refused ({note2})")

    if app is not None or inspector is not None:
        notes.append("SKIP: C-E: they open their own editor -- run the guard standalone")
        return (not problems), notes
    if not ELS85.exists() or not GN150.exists():
        notes.append("SKIP: C-E: the ELS85 / 150 mm scenes are not in this checkout")
        return (not problems), notes

    editor = None
    try:
        import KrakenOS.UI.layout_editor as le

        with _quiet():
            editor = le.KrakenLayoutEditor(headless=True)

        # ---- C: an overlay-promoted body comes back from its recipe, identical ----------------------------
        for scene, needle, how in ((ELS85, "optical_48f0335eb2c76ec6", "as posed"),
                                   (GN150, "optical_aae83ad73a8d39d8", "resized")):
            advanced = _row_with(scene, needle)
            real = le._resolve_project_file_path(advanced["Solid_3d_stl"]) if advanced else None
            if advanced is None or real is None or not real.exists():
                notes.append(f"SKIP: C: {needle} is not on disk to compare with (run tools/rebuild_cad_caches.py)")
                continue
            with tempfile.TemporaryDirectory() as tmp:
                target = Path(tmp) / real.name
                with _quiet():
                    built, note = recipes.rebuild_overlay_promoted_body(editor, advanced, target)
                same = False
                if built:
                    a, b = pv.read(str(target)), pv.read(str(real))
                    same = (np.array_equal(np.asarray(a.faces), np.asarray(b.faces))
                            and np.allclose(np.asarray(a.points), np.asarray(b.points), atol=1e-6))
                ok(built and same and how in note, f"C1: {needle} rebuilds {how}, identical to the cache ({note})")
                tampered = copy.deepcopy(advanced)
                tampered["OpticalSolidFaces"]["faces"][0]["centroid"] = [99.0, 99.0, 99.0]
                with _quiet():
                    built_bad, note_bad = recipes.rebuild_overlay_promoted_body(editor, tampered, Path(tmp) / "bad.stl")
                ok(not built_bad and "refused" in note_bad and not (Path(tmp) / "bad.stl").exists(),
                   f"C2: a rebuild that cannot reproduce the recorded faces is refused and nothing is written")

        # ---- D: the load path rebuilds at the RECORDED path and never repoints an overlay body -------------
        advanced = _row_with(ELS85, "optical_48f0335eb2c76ec6")
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "optical_48f0335eb2c76ec6.stl"
            advanced["Solid_3d_stl"] = str(missing)
            from types import SimpleNamespace

            row = SimpleNamespace(advanced=advanced, name="fixture", surface="Standard")
            editor.rows = [row]
            with _quiet():
                editor._regenerate_missing_optical_solid_caches()
            ok(missing.exists() and row.advanced["Solid_3d_stl"] == str(missing),
               f"D1: the body is rebuilt where the scene points, the row is not repointed "
               f"({getattr(editor, '_cad_cache_rebuild_notes', None)})")
            editor.rows = []

        # ---- E: the missing-assets dialog does not hold the load -------------------------------------------
        import inspect

        from KrakenOS.UI.panels.missing_assets_dialog import MissingAssetsDialog
        from KrakenOS.UI.services.missing_assets_scan import MissingAsset

        source = inspect.getsource(type(editor)._prompt_for_missing_cad_assets)
        ok("modal=False" in source, "E1: the load opens the dialog non-modal")
        fake = MissingAsset(scope="row", row_index=0, key="OpticalSolidSourcePath",
                            expected_path=Path("/nonexistent/source.step"), label="fixture")
        started = time.monotonic()
        with _quiet():
            MissingAssetsDialog.run(editor, editor=editor, assets=[fake], modal=False)
        elapsed = time.monotonic() - started
        ok(elapsed < 5.0, f"E2: a non-modal dialog returns at once ({elapsed:.2f} s)")
        for child in list(editor.winfo_children()):
            if isinstance(child, MissingAssetsDialog):
                with contextlib.suppress(Exception):
                    child.destroy()

        # ---- F: the user's scene, a cache file moved aside, a real load ------------------------------------
        advanced = _row_with(ELS85, "optical_48f0335eb2c76ec6")
        real = le._resolve_project_file_path(advanced["Solid_3d_stl"])
        backup = real.with_name(real.stem + ".0810guard.stl")
        shutil.move(str(real), str(backup))
        try:
            editor.layout_files["els85"] = ELS85
            started = time.monotonic()
            with _quiet():
                editor.load_layout_by_name("els85")
            elapsed = time.monotonic() - started
            same = False
            if real.exists():
                a, b = pv.read(str(real)), pv.read(str(backup))
                same = np.array_equal(np.asarray(a.faces), np.asarray(b.faces)) and np.allclose(
                    np.asarray(a.points), np.asarray(b.points), atol=1e-6)
            ok(same, f"F1: loading the scene rebuilt the moved-aside body, identical ({elapsed:.1f} s, no dialog wait)")
        finally:
            if real.exists():
                backup.unlink(missing_ok=True)
            else:
                shutil.move(str(backup), str(real))
    except Exception as exc:
        ok(False, f"C-F raised {type(exc).__name__}: {exc}")
    finally:
        if editor is not None:
            with contextlib.suppress(Exception):
                editor.destroy()
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0810 cache-is-a-recipe validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
