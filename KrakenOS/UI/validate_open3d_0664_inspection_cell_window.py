"""Guard for bugs/0664 -- the EMBEDDED Inspection Cell view (phase 3): a Tk/VTK window
that transplants the off-screen composition, opens a station's layout on double-click,
and re-composes when a station layout is saved.

Checks:
  A  WINDOW (skip-if-absent / standalone-only, Tk/Xvfb): with a two-station cell the
     window reports available, its renderer holds the composed actors, every station
     face resolves from at least one actor (the double-click map), a prop pick at the
     projected object point of a station resolves to that face, `open_station` loads
     the station layout into the editor, and touching a station file makes
     `check_station_files` re-compose (compose count increments).
  B  WIRING: the cell dialog's "Open Cell View" goes through the embedded window with
     the pyvista fallback; the composition records per-station actor keys; the window
     hands a double-click to its session, which watches the station files (bugs/0967:
     the window is a view over `services/inspection_cell_session.py`).

Inside the penta harness the window section is SKIPPED (the harness owns the single
embedded inspector; a second VTK/Tk widget is not opened there) -- run this module
directly for the window checks.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0664_inspection_cell_window
"""

from __future__ import annotations

import inspect
import os
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONT_SCENE = PROJECT_ROOT / "attachment/Basler_Telecentric.py"
TOP_SCENE = PROJECT_ROOT / "attachment/machine_vision_Pyrite90_0.3X.py"


def _check_window(ok, notes, app=None, inspector=None) -> None:
    if app is not None and inspector is not None:
        notes.append("SKIP: A: window checks run standalone only (the harness owns the single embedded inspector)")
        return
    if not FRONT_SCENE.exists() or not TOP_SCENE.exists():
        notes.append("SKIP: A: the two station scenes are not in this checkout")
        return
    import shutil
    import tempfile

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.inspection_cell_window import InspectionCellWindow
    from KrakenOS.UI.services.inspection_cell import normalize_cell_spec

    editor = None
    window = None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            # a private copy of one station so the mtime touch never edits the user's file
            top_copy = Path(tmp) / "station_top.py"
            shutil.copyfile(TOP_SCENE, top_copy)
            cell = normalize_cell_spec(
                {
                    "part": {"width_mm": 60, "height_mm": 40, "depth_mm": 20},
                    "stations": {
                        "front": {"layout": str(FRONT_SCENE), "enabled": True},
                        "top": {"layout": str(top_copy), "enabled": True},
                    },
                }
            )
            editor = KrakenLayoutEditor()
            editor._prompt_for_missing_cad_assets = lambda: None
            window = InspectionCellWindow(editor, cell)
            if not window.available:
                notes.append(f"SKIP: A: embedded view unavailable here ({window.unavailable_reason})")
                return
            window.update()
            n_actors = window._renderer.GetViewProps().GetNumberOfItems()
            ok(n_actors > 10, f"A1: the window's renderer holds the composed actors ({n_actors})")
            faces = set(window._actor_face.values())
            ok(faces == {"front", "top"}, f"A2: every station face is reachable from the double-click map ({sorted(faces)})")
            # pick at the projected centre of the TOP station's BODY box (a face centre
            # sits on the part box itself, which is correctly not a station)
            top = next(st for st in window._report["stations"] if st["face"] == "top")
            b = top["bounds"]
            centre = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
            window.fit_view()
            window.update()
            renderer = window._renderer
            renderer.SetWorldPoint(float(centre[0]), float(centre[1]), float(centre[2]), 1.0)
            renderer.WorldToDisplay()
            dx, dy, _ = renderer.GetDisplayPoint()
            picked = window.face_at(int(dx), int(dy))
            hit = getattr(window, "_last_pick_hit", None)
            ok(
                picked == "top",
                f"A3: a geometric pick at the projected top-station body centre resolves to that "
                f"station ({picked}; hit actor: {hit is not None}; display ({dx:.0f}, {dy:.0f}))",
            )
            opened = window.open_station("front")
            ok(
                opened and Path(str(editor.current_layout_file or "")).resolve() == FRONT_SCENE.resolve(),
                f"A4: open_station loads the station layout into the editor ({editor.current_layout_file})",
            )
            before = window._compose_count
            time.sleep(1.1)
            os.utime(top_copy, None)
            changed = window.check_station_files()
            ok(
                changed and window._compose_count == before + 1,
                f"A5: a saved station layout re-composes the cell (compose count {before} -> {window._compose_count})",
            )
    finally:
        try:
            if window is not None:
                window.destroy()
        except Exception:
            pass
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def _check_wiring(ok, notes) -> None:
    from KrakenOS.UI.panels import inspection_cell_window as icw
    from KrakenOS.UI.services import inspection_cell as ic

    # bugs/0913: since bugs/0883 the cell dialog is a row form (row_forms/inspection_cell.py) the
    # Tk shim renders, so "the dialog opens the embedded view" is MEASURED by running the form's
    # own Open Cell View action with the embedded opener recorded
    from types import SimpleNamespace

    from KrakenOS.UI.row_forms import inspection_cell as cell_form

    owner = SimpleNamespace(inspection_cell_spec=None, inspection_part_spec=None)
    form = cell_form.build_inspection_cell_form(owner)
    view = next((action for action in form.actions if action.key == "view"), None)
    opened: list = []
    real_open = icw.open_inspection_cell_window
    icw.open_inspection_cell_window = lambda _owner, cell: opened.append(cell)
    try:
        message = view.run(form, None) if view is not None else ""
    finally:
        icw.open_inspection_cell_window = real_open
    ok(
        view is not None and len(opened) == 1 and "pyvista" in str(message)
        and "build_inspection_cell_form" in inspect.getsource(ic.open_inspection_cell_dialog),
        "B1: the cell dialog opens the EMBEDDED view (pyvista only as fallback) -- its Open Cell "
        f"View action called the embedded opener {len(opened)}x and, with no window back, said "
        f"{message!r}",
    )
    compose_src = inspect.getsource(ic.compose_cell_plotter)
    ok("station_actor_keys" in compose_src, "B2: the composition records per-station actor keys for picking")
    # bugs/0967: the window is a VIEW now -- what it watches and what a double-click means live in
    # the session, so the watch is MEASURED on a scripted clock instead of read from the source
    from KrakenOS.UI.services.inspection_cell_session import InspectionCellSession
    from KrakenOS.UI.uihost import ScriptedUiHost

    clock = ScriptedUiHost()
    watcher = InspectionCellSession(SimpleNamespace(), {}, host=clock)
    watcher.start_watching()
    armed = clock.pending()
    ran = clock.run_due(InspectionCellSession.POLL_MS)
    win_src = inspect.getsource(icw.InspectionCellWindow)
    ok(
        "GetRepeatCount" in win_src and "session.double_click" in win_src and "SetInteractorStyle" in win_src
        and armed == 1 and ran == 1 and clock.pending() == 1,
        "B3: double-click opens a station (the window hands the point to its session); station files are "
        f"watched (one timer armed, it ran {ran}x at {InspectionCellSession.POLL_MS} ms and re-armed: "
        f"{clock.pending()}); trackball camera",
    )
    ok("plotter.show" in inspect.getsource(icw.open_inspection_cell_window), "B4: the pyvista fallback survives")


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    for section, fn in (("A", _check_window), ("B", _check_wiring)):
        try:
            if section == "A":
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
        print("Inspection-cell-window validation passed.")
        return 0
    print("Inspection-cell-window validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
