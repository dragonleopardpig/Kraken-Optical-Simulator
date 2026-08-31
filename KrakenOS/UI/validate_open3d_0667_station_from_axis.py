"""Guard for bugs/0667 -- "add components on each axis independently": one click on a
blow-out axis creates -- or opens -- that face's STATION layout, pre-linked into the
cell; and an enabled inspection part survives a lens import.

The user's intent (2026-08-31): the 3D part with six axes should let components be
added per axis. Each axis's components live in that face's station layout (one chain
per scene, the engine's invariant); this makes the axis itself the handle: right-click
a blow-out axis -> "Create/Open station for this face". A CREATED station is seeded
from the current scene with the part re-targeted onto the face; the cell file is
written beside it so the Cell View finds every station. Opening twice never
re-creates. And because a lens import REPLACES the whole layout, an enabled part is
carried across it -- without that, the first thing a user does on a fresh station
(import the lens) silently deleted the part.

Checks:
  A  STATION CREATE/OPEN (skip-if-absent, Tk/Xvfb): from a part-enabled scene,
     `open_station_for_face("top")` writes station_top.py + the cell json, loads it
     with the part active on TOP, and links BOTH stations (the seed scene keeps its
     face); a second editor holding the cell spec OPENS the same file (no re-create,
     mtime unchanged).
  B  PART SURVIVES THE LENS IMPORT (skip-if-absent): enable the part, import a lens
     folder -- the part is still enabled afterwards (it used to vanish with the
     replaced layout).
  C  WIRING: the blow-out axis routes to its own menu (create/open, re-target,
     solve); the part right-click carries the create/open item too.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0667_station_from_axis
"""

from __future__ import annotations

import inspect
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"
LENS_FOLDER = PROJECT_ROOT / "attachment/Lens/67304_0.75X_Telecentric"


def _check_station_create_open(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A: the Basler_Telecentric scene is not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    cell_dir = PROJECT_ROOT / "attachment" / "cells" / "_guard_0667"
    editor = None
    editor2 = None
    try:
        # a private copy so the guard never writes into the user's cells
        if cell_dir.exists():
            shutil.rmtree(cell_dir)
        scene_copy_dir = cell_dir / "seed"
        scene_copy_dir.mkdir(parents=True)
        seed = scene_copy_dir / "_guard_0667.py"
        shutil.copyfile(SCENE, seed)
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["_0667"] = seed
        editor.load_layout_by_name("_0667")
        editor.set_inspection_part_spec(
            {"enabled": True, "width_mm": 10, "height_mm": 8, "depth_mm": 6, "active_face": "front"}
        )
        created = editor.open_station_for_face("top")
        station = PROJECT_ROOT / "attachment" / "cells" / "_guard_0667" / "station_top.py"
        cell_json = PROJECT_ROOT / "attachment" / "cells" / "_guard_0667" / "_guard_0667.cell.json"
        ok(
            created and station.exists() and cell_json.exists(),
            f"A1: the top station + cell file are created ({station.name}, {cell_json.name})",
        )
        spec = editor.inspection_part_spec
        ok(
            spec["enabled"] and spec["active_face"] == "top"
            and Path(str(editor.current_layout_file)).resolve() == station.resolve(),
            f"A2: the created station is LOADED with the part on TOP ({editor.current_layout_file})",
        )
        cell = json.loads(cell_json.read_text())
        ok(
            Path(cell["stations"]["top"]["layout"]).resolve() == station.resolve()
            and Path(cell["stations"]["front"]["layout"]).resolve() == seed.resolve(),
            "A3: BOTH stations are linked -- the new top one and the seed scene for its own front face",
        )
        mtime = station.stat().st_mtime
        editor2 = KrakenLayoutEditor()
        editor2._prompt_for_missing_cad_assets = lambda: None
        editor2.inspection_cell_spec = cell
        opened = editor2.open_station_for_face("top")
        ok(
            opened and Path(str(editor2.current_layout_file)).resolve() == station.resolve()
            and station.stat().st_mtime == mtime,
            "A4: a second open OPENS the same file (no re-create; mtime unchanged)",
        )
    finally:
        for e in (editor, editor2):
            try:
                if e is not None:
                    e.destroy()
            except Exception:
                pass
        try:
            shutil.rmtree(cell_dir)
        except Exception:
            pass


def _check_part_survives_lens_import(ok, notes) -> None:
    if not LENS_FOLDER.exists():
        notes.append("SKIP: B: the 67304 folder is not in this checkout")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.set_inspection_part_spec(
            {"enabled": True, "width_mm": 10, "height_mm": 8, "depth_mm": 6, "active_face": "left"}
        )
        editor.import_machine_vision_lens_from_folder(str(LENS_FOLDER))
        spec = editor.inspection_part_spec
        ok(
            spec["enabled"] and spec["active_face"] == "left" and spec["width_mm"] == 10.0,
            f"B1: the part survives the layout-replacing lens import ({spec['active_face']}, "
            f"{spec['width_mm']:g} x {spec['height_mm']:g} x {spec['depth_mm']:g})",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.services import open3d_face_assignment as fa
    from KrakenOS.UI.services import layout_table_workbench as wb

    axis_src = ""
    for cls in vars(fa).values():
        if isinstance(cls, type) and "_show_inspection_part_axis_menu" in vars(cls):
            axis_src = inspect.getsource(getattr(cls, "_show_inspection_part_axis_menu"))
            break
    ok(
        "Create/Open station for this face" in axis_src and "open_station_for_face" in axis_src
        and "set_inspection_part_active_face" in axis_src,
        "C1: the blow-out axis menu offers create/open + re-target + solve",
    )
    route_src = inspect.getsource(fa.Open3DFaceAssignmentService._maybe_show_optical_axis_menu) if hasattr(
        fa, "Open3DFaceAssignmentService"
    ) else ""
    if not route_src:
        for cls in vars(fa).values():
            if isinstance(cls, type) and "_maybe_show_optical_axis_menu" in vars(cls):
                route_src = inspect.getsource(getattr(cls, "_maybe_show_optical_axis_menu"))
                break
    ok(
        "inspection_part_face" in route_src,
        "C2: the generic axis menu routes part-face axes to their own menu",
    )
    part_menu_src = ""
    for cls in vars(fa).values():
        if isinstance(cls, type) and "_maybe_show_inspection_part_menu" in vars(cls):
            part_menu_src = inspect.getsource(getattr(cls, "_maybe_show_inspection_part_menu"))
            break
    ok(
        "Create/Open station for the inspected face" in part_menu_src,
        "C3: the part right-click carries the create/open item",
    )
    import_src = ""
    for cls in vars(wb).values():
        if isinstance(cls, type) and "import_machine_vision_lens_from_folder" in vars(cls):
            import_src = inspect.getsource(getattr(cls, "import_machine_vision_lens_from_folder"))
            break
    ok("_carried_part" in import_src, "C4: the lens import snapshots + restores the part")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_station_create_open), ("B", _check_part_survives_lens_import), ("C", _check_wiring)):
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
        print("Station-from-axis validation passed.")
        return 0
    print("Station-from-axis validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
