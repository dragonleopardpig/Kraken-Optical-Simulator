"""Guard for bugs/0669 -- the cell lives IN the existing 3D canvas: the OTHER
stations appear as translucent, non-pickable GHOSTS around the live part, and the
part itself is reachable from a 3D right-click -- no separate window required.

User (2026-08-31): "I see you put the 6-sided object in 2D menu and launch a separate
3D window. Can't we do everything to existing 3D canvas?" The separate cell window
(0664) composes six chains; this brings that composition into the live canvas as
ghost context (the 0664 transplant pattern re-targeted at the live renderer). The
live station stays fully editable; 0667's axis right-click switches which face is
live; ghosts re-seat from the LIVE part pose.

Checks:
  A  FRAME CONSISTENCY (pure): ghost_world_transform is rigid (det +1); for the
     active face it is the identity; a ghost's object point lands EXACTLY on the
     live-world centre of its part face -- the 0663 cell frames and the 0661
     live-world face frames agree through T_live^-1.
  B  CELL DISCOVERY (skip-if-absent): find_cell_for_layout locates the cell json
     beside a station layout by reference, not by name.
  C  WIRING: the scene refresh re-seats ghosts every rebuild; the part and axis
     menus carry the ghost toggle; the generic optical-axis menu offers the
     Inspection Part dialog (enable the part without the 2D menu).
  D  LIVE CANVAS (standalone only, Tk/Xvfb, ~3 min): on a real solved cell station,
     toggling ghosts composes every other station into the live renderer
     (non-pickable), re-targeting the active face re-keys the ghost set, and
     toggling off removes and clears everything.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0669_cell_ghosts_in_canvas
"""

from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATION = PROJECT_ROOT / "attachment/cells/solved/solved_front.py"


def _check_frames(ok, notes) -> None:
    from KrakenOS.UI.services.inspection_cell import cell_part_frames, station_frame_transform
    from KrakenOS.UI.services.inspection_cell_ghosts import ghost_world_transform
    from KrakenOS.UI.services.inspection_part import face_frames, normalize_inspection_part_spec

    spec = normalize_inspection_part_spec(
        {"enabled": True, "width_mm": 60, "height_mm": 40, "depth_mm": 20, "active_face": "front"}
    )
    O = np.array([7.0, -2.0, 31.0])
    a = np.array([0.2, -0.1, 1.0]) / np.linalg.norm([0.2, -0.1, 1.0])
    frames_cell = cell_part_frames(spec)
    fr = frames_cell["front"]
    T_live = station_frame_transform(O, a, fr["center"], fr["normal"], fr["u"])
    T_self = ghost_world_transform(O, a, "front", spec, T_live)
    ok(np.allclose(T_self, np.eye(4), atol=1e-9), "A1: the active face's own transform is the identity")

    # a ghost on TOP whose station object plane happens to be the same (O, a):
    fr_top = frames_cell["top"]
    T_top = station_frame_transform(O, a, fr_top["center"], fr_top["normal"], fr_top["u"])
    T = ghost_world_transform(O, a, "front", spec, T_top)
    R = T[:3, :3]
    ok(
        np.allclose(R @ R.T, np.eye(3), atol=1e-9) and abs(float(np.linalg.det(R)) - 1.0) < 1e-9,
        "A2: the ghost placement is rigid (orthonormal, det +1 -- no mirror)",
    )
    landed = (T[:3, :3] @ O) + T[:3, 3]
    live_top = face_frames(spec, O, a)["top"]["center"]
    err = float(np.linalg.norm(landed - np.asarray(live_top)))
    ok(
        err < 1e-9,
        f"A3: the ghost's object point lands on the LIVE-world top-face centre "
        f"(0663 cell frames == 0661 world frames through T_live^-1; err {err:.2e} mm)",
    )


def _check_cell_discovery(ok, notes) -> None:
    if not STATION.exists():
        notes.append("SKIP: B: the solved cell station is not in this checkout")
        return
    from KrakenOS.UI.services.inspection_cell_ghosts import find_cell_for_layout

    cell = find_cell_for_layout(STATION)
    ok(
        cell is not None and any(
            (e or {}).get("layout") and Path(str(e["layout"])).resolve() == STATION.resolve()
            for e in (cell.get("stations") or {}).values()
        ),
        "B1: find_cell_for_layout locates the cell json beside the station by reference",
    )


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI import open3d_inspector as oi
    from KrakenOS.UI.services import open3d_face_assignment as fa
    from KrakenOS.UI.services import open3d_scene_refresh as sr

    src = inspect.getsource(oi)
    ok(
        "def toggle_cell_ghosts" in src and "def _add_cell_ghost_glyphs" in src
        and "PickableOff" in src,
        "C1: the inspector owns the ghost toggle and the non-pickable ghost composer",
    )
    ok(
        "_add_cell_ghost_glyphs" in inspect.getsource(sr),
        "C2: the scene refresh re-seats ghosts on every rebuild",
    )
    fa_src = inspect.getsource(fa)
    ok(
        fa_src.count("Show the other stations here (ghosts)") >= 2,
        "C3: BOTH part right-click menus (box + blow-out axis) carry the ghost toggle",
    )
    ok(
        "Inspection Part (3D object)" in fa_src,
        "C4: the generic optical-axis menu opens the Inspection Part dialog (3D-canvas enable)",
    )


def _check_live_canvas(ok, notes, app=None, inspector=None) -> None:
    if app is not None or inspector is not None:
        notes.append(
            "SKIP: D: live-canvas checks run standalone only (the harness owns the "
            "single embedded inspector) -- run this module directly for them"
        )
        return
    if not STATION.exists():
        notes.append("SKIP: D: the solved cell station is not in this checkout")
        return
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["st"] = STATION
        editor.load_layout_by_name("st")
        insp = _open_3d_inspector(editor)
        insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        insp.toggle_cell_ghosts()
        _settle(insp)
        cache = insp._cell_ghost_cache
        faces = sorted(cache.keys())
        total = sum(len(rec.get("actors") or []) for rec in cache.values())
        seated = sum(
            1 for rec in cache.values() for a in (rec.get("actors") or []) if insp._renderer.HasViewProp(a)
        )
        pickable = sum(
            1 for rec in cache.values() for a in (rec.get("actors") or []) if a.GetPickable()
        )
        ok(
            faces == ["back", "bottom", "left", "right", "top"] and total > 0
            and seated == total and pickable == 0,
            f"D1: every OTHER station ghosts into the live renderer, none pickable "
            f"({faces}, {seated}/{total} seated, {pickable} pickable)",
        )
        editor.set_inspection_part_active_face("top")
        _settle(insp)
        faces = sorted(insp._cell_ghost_cache.keys())
        ok(
            faces == ["back", "bottom", "front", "left", "right"],
            f"D2: re-targeting the live face re-keys the ghosts (now {faces})",
        )
        insp.toggle_cell_ghosts()
        _settle(insp)
        ok(
            not insp._cell_ghost_cache,
            "D3: toggling off removes the ghosts and clears the cache",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_frames), ("B", _check_cell_discovery), ("C", _check_wiring)):
        try:
            fn(ok, notes)
        except Exception as exc:  # pragma: no cover - environment
            notes.append(f"FAIL: section {section} raised ({type(exc).__name__}: {exc})")
    try:
        _check_live_canvas(ok, notes, app=app, inspector=inspector)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: section D raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Cell-ghosts-in-canvas validation passed.")
        return 0
    print("Cell-ghosts-in-canvas validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
