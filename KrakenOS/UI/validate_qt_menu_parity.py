"""Guard for menu parity between the Tk editor and the Qt shell (bugs/0942).

  S  every command on the Tk editor's menu bar has a Qt route -- an `ACTIONS` entry that runs the
     same editor method (`editor:<method>`), a Qt action whose window method calls it, or a Qt
     port named in `QT_PORTS` -- or is a documented `KNOWN_GAPS` entry. The gap list may only
     SHRINK: an entry that has gained a route fails until it is deleted. Every `editor:` target is
     a method the editor defines.
In a real Qt shell, with the 3D inspector hosted in its dock:
  H  a table edit, then Undo, puts the old value back in the model AND the Qt table; Redo puts the
     edit back. Undo / Redo enable and disable with the model's history.
  A  Save As asks for a name, writes the file and titles the window with it; after another edit,
     Save writes that same file WITHOUT asking, and the file reloads with the edit.
  C  Ctrl+C / Ctrl+V on the surface table copy a lens row and paste it right AFTER the selected
     row (the Qt table's selection -- the model used to read the hidden Tk table's, and pasted
     before the Image row); with focus outside the table, Ctrl+C copies no rows.
  I  File -> Open shows the new layout in the hosted 3D inspector (its scene bounds change); File ->
     Reload keeps that inspector -- alive, still the editor's, done adopting the reloaded layout.
     A Reload or Reset used to DESTROY it: the model closes the 3D window on a full layout load, and
     the Qt shell's inspector is that window.
  R  File -> Reset clears to Object + Image in the model and the Qt table, keeps the inspector and
     redraws it -- its scene shrinks to the blank layout -- and Undo brings the layout back.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "QTMENU_RESULT "
SKIP_MARK = "QTMENU_SKIP "
TK_MENU_SOURCE = Path("KrakenOS/UI/panels/main_window.py")
FIRST = Path("test_fixtures/machine_vision_Pyrite90_0.3X.py")    # 7 rows, three lens/stop rows
SECOND = Path("test_fixtures/Basler_Telecentric.py")

#: Tk menu-bar command -> the Qt action that ports it (a row form, a report, a Qt dialog)
QT_PORTS = {
    "request_quit": "quit",
    "open_stock_lens_importer": "stock_lens",          # also the Tk "Stock Lens Catalog..." entry
    "open_glass_catalog_browser": "glass_catalog",
    "open_ray_inspector": "ray_inspector",              # also "Inspect Ray / Surface Physics"
    "open_branch_tree_inspector": "trace_paths",
    "open_branch_throughput_report": "branch_throughput",
    "open_detector_aperture_report": "detector_aperture",
    "open_source_illumination_report": "source_illumination",
    "open_scene_source_manager": "scene_sources",
    "open_nonseq_scene_graph": "nonseq_scene_graph",
    "open_optical_stl_diagnostics": "optical_solid_diagnostics",
    "open_system_selection_calculator": "system_selection",
    "open_camera_lens_matcher": "catalog_matcher",
    "open_inspection_part_dialog": "inspection_part",
    "open_inspection_cell_dialog": "inspection_cell",
    "open_paraxial_matrix_report": "paraxial_matrix",
    "open_gaussian_beam_report": "gaussian_beam",
    "open_branch_gaussian_q_report": "branch_gaussian_q",
    "open_save_tolerance_solve_preset_dialog": "tolerance_preset",
    "open_apply_tolerance_solve_preset_dialog": "apply_tolerance_preset",
    "open_paraxial_calculator": "paraxial_calculator",
}

_TK_DIALOGS = "calls Tk messagebox / simpledialog directly -- needs host_of before it can be routed"
#: Tk menu-bar commands with no Qt route yet -> why (measured by running each in the Qt shell)
KNOWN_GAPS = {
    "_open_lens_drawing_surface_properties_dialog": _TK_DIALOGS,
    "export_lens_drawing": _TK_DIALOGS,
    "open_current_path_component_placement": "ends in a Tk row form (path component placement)",
    "open_current_path_stock_lens_placement": "ends in a Tk row form (stock lens placement)",
    "open_atmosphere_settings_dialog": "opens a Tk window -- needs a Qt port",
    "open_tolerance_monte_carlo_report": _TK_DIALOGS,
    "export_tolerance_monte_carlo_csv": _TK_DIALOGS,
    "open_tolerance_worst_sample_comparison_report": _TK_DIALOGS,
    "export_tolerance_comparison_csv": _TK_DIALOGS,
    "open_tolerance_stackup_dashboard_report": _TK_DIALOGS,
    "export_tolerance_stackup_csv": _TK_DIALOGS,
    "open_tolerance_compensator_sweep_report": _TK_DIALOGS,
    "export_tolerance_compensator_csv": _TK_DIALOGS,
    "open_tolerance_multi_compensator_report": _TK_DIALOGS,
    "export_tolerance_multi_compensator_csv": _TK_DIALOGS,
    "export_tolerance_overlay_csv": _TK_DIALOGS,
    "export_branch_psf_csv": _TK_DIALOGS,
    "export_branch_mtf_csv": _TK_DIALOGS,
    "export_detector_map_csv": _TK_DIALOGS,
    "export_coherent_detector_csv": _TK_DIALOGS,
    "export_branch_field_csv": _TK_DIALOGS,
}


def tk_menu_commands() -> list[tuple[str, str]]:
    """(label, editor method) of every command on the Tk editor's menu bar."""
    source = TK_MENU_SOURCE.read_text(encoding="utf-8")
    return re.findall(r'add_command\(\s*label="([^"]+)"[^)]*?command=self\.([a-zA-Z_0-9]+)', source)


def qt_routes() -> dict[str, str]:
    """Tk menu method -> the Qt action that reaches it."""
    import ast

    from KrakenOS.UI.qt.actions import ACTIONS, editor_command

    source = Path("KrakenOS/UI/qt/main_window.py").read_text(encoding="utf-8")
    bodies = {node.name: ast.get_source_segment(source, node) or ""
              for node in ast.walk(ast.parse(source)) if isinstance(node, ast.FunctionDef)}
    names = {action[0] for action in ACTIONS}
    routes: dict[str, str] = {}
    for _label, method in tk_menu_commands():
        for name, _menu, _text, _short, target, _tip in ACTIONS:
            command = editor_command(target)
            if command == method or (command is None and f"self.editor.{method}(" in bodies.get(target, "")):
                routes[method] = name
                break
        else:
            if QT_PORTS.get(method) in names:
                routes[method] = QT_PORTS[method]
    return routes


def static_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.qt.actions import ACTIONS, editor_command

    methods = sorted({method for _label, method in tk_menu_commands()})
    routes = qt_routes()
    unrouted = [m for m in methods if m not in routes and m not in KNOWN_GAPS]
    stale = sorted(m for m in KNOWN_GAPS if m in routes)
    gone = sorted(m for m in set(KNOWN_GAPS) | set(QT_PORTS) if m not in methods)
    targets = [editor_command(action[4]) for action in ACTIONS]
    undefined = sorted(t for t in targets if t is not None and not callable(getattr(KrakenLayoutEditor, t, None)))
    return [["S", len(methods) >= 70 and not unrouted and not stale and not gone and not undefined,
             f"{len(methods)} Tk menu-bar commands: {len(routes)} routed in Qt, {len(KNOWN_GAPS)} known gaps; "
             f"unrouted and undocumented {unrouted}; gaps that now HAVE a route (delete them) {stale}; "
             f"listed but no longer on the Tk menu {gone}; editor: targets the editor lacks {undefined}"]]


def qt_runtime_checks(folder: str) -> list:
    import time

    import numpy as np
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI.layout_library import load_python_data
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    folder = Path(folder)
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(FIRST)
    view = window.build_inspector_view()
    editor, model, actions = window.editor, window.rows_model, window.action_manager.actions
    inspector = view.inspector
    host = host_of(window)

    def settle(seconds: float = 0.6) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def shown(row: int, field: str) -> str:
        return str(model.data(model.index(row, fields.index(field))))

    def bounds() -> list:
        return [round(float(v), 3) for v in inspector._renderer.ComputeVisiblePropBounds()]

    settle(1.5)
    fields = [model.field(column) for column in range(model.columnCount())]
    rows = []

    # H -- undo / redo through the actions
    stop = 3
    before = editor.rows[stop].thickness
    typed = f"{before + 2.5:.4f}"
    model.setData(model.index(stop, fields.index("thickness")), typed)
    edited = editor.rows[stop].thickness
    enabled_after_edit = (actions["undo"].isEnabled(), actions["redo"].isEnabled())
    actions["undo"].trigger()
    app.processEvents()
    undone = (editor.rows[stop].thickness, shown(stop, "thickness"), actions["redo"].isEnabled())
    actions["redo"].trigger()
    app.processEvents()
    redone = (editor.rows[stop].thickness, shown(stop, "thickness"), actions["redo"].isEnabled())
    rows.append(["H", abs(edited - float(typed)) < 1e-9 and enabled_after_edit == (True, False)
                 and abs(undone[0] - before) < 1e-9 and abs(float(undone[1]) - before) < 1e-6
                 and undone[2] and abs(redone[0] - edited) < 1e-9 and abs(float(redone[1]) - edited) < 1e-6
                 and not redone[2],
                 f"edit {before} -> {edited} (undo/redo enabled {enabled_after_edit}); Undo -> model "
                 f"{undone[0]}, table {undone[1]!r}, redo enabled {undone[2]}; Redo -> model {redone[0]}, "
                 f"table {redone[1]!r}, redo enabled {redone[2]}"])

    # A -- Save As, then Save to the same file without asking
    asked: list = []
    target = folder / "saved_as.py"
    host.asksaveasfilename = lambda **kw: (asked.append(kw.get("title")), str(target))[1]
    actions["save_as"].trigger()
    app.processEvents()
    first_write = target.exists() and target.stat().st_mtime_ns
    title = window.windowTitle()
    model.setData(model.index(stop, fields.index("thickness")), f"{edited + 1.0:.4f}")
    actions["save"].trigger()
    app.processEvents()
    saved = [row["thickness"] for row in load_python_data(target)["surfaces"]] if target.exists() else []
    rows.append(["A", bool(first_write) and title.endswith("saved_as.py") and len(asked) == 1
                 and len(saved) == len(editor.rows) and abs(float(saved[stop]) - (edited + 1.0)) < 1e-6,
                 f"Save As asked {len(asked)}x and wrote {target.name}: {bool(first_write)}; title {title!r}; "
                 f"Save after an edit asked no more and the file reloads with thickness "
                 f"{saved[stop] if saved else None} (expected {edited + 1.0:g})"])

    # C -- Ctrl+C / Ctrl+V on the table; Ctrl+C elsewhere copies no rows
    window.raise_()
    window.activateWindow()
    active = QTest.qWaitForWindowActive(window, 3000)  # a shortcut fires only in the active window
    copies: list = []
    actions["copy_rows"].triggered.connect(lambda *_a: copies.append(1))
    lens = 2
    count = len(editor.rows)
    copied = (editor.rows[lens].surface, editor.rows[lens].rc, editor.rows[lens].thickness)
    window.select_rows([lens], lens)
    window.rows_view.setFocus()
    QTest.keyClick(window.rows_view, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    window.select_rows([lens], lens)
    QTest.keyClick(window.rows_view, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    settle(0.3)
    pasted = (editor.rows[lens + 1].surface, editor.rows[lens + 1].rc, editor.rows[lens + 1].thickness) \
        if len(editor.rows) > lens + 1 else None
    on_table = len(copies)
    outside = window.results_panel.table
    outside.setFocus()
    QTest.keyClick(outside, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
    app.processEvents()
    rows.append(["C", active and on_table == 1 and len(copies) == 1 and len(editor.rows) == count + 1
                 and model.rowCount() == count + 1 and pasted == copied,
                 f"window active {active}; Ctrl+C on the table copied {on_table}x; Ctrl+V: {count} -> "
                 f"{len(editor.rows)} rows (table {model.rowCount()}), row {lens + 1} is {pasted} -- the copied "
                 f"row {copied}; Ctrl+C in the Results view copied rows {len(copies) - on_table}x"])

    def kept() -> tuple:
        alive = bool(inspector.winfo_exists())
        return (alive, editor.__dict__.get("_three_d_inspector") is inspector,
                alive and not getattr(inspector, "_layout_replaced_pending", False))

    # I -- File -> Open shows the new layout; File -> Reload keeps the inspector
    first_bounds = bounds()
    host.askopenfilename = lambda **_kw: str(SECOND.resolve())
    actions["open"].trigger()
    settle(2.0)
    opened = kept()
    second_bounds = bounds() if opened[0] else []
    expected = len(load_python_data(SECOND)["surfaces"])
    opened_rows = len(editor.rows)
    actions["reload"].trigger()
    settle(2.0)
    reloaded = kept()
    rows.append(["I", opened == (True, True, True) and opened_rows == expected
                 and not np.allclose(first_bounds, second_bounds) and reloaded == (True, True, True)
                 and len(editor.rows) == expected,
                 f"Open of {SECOND.name}: {opened_rows} rows (file {expected}), scene bounds {first_bounds} -> "
                 f"{second_bounds}; inspector (alive, the editor's, adopted) after Open {opened}, after Reload "
                 f"{reloaded}"])

    # R -- Reset redraws the kept inspector; Undo brings the layout back
    loaded = len(editor.rows)
    before_reset = bounds()
    actions["reset"].trigger()
    settle(1.5)
    after_reset = kept()
    blank = bounds() if after_reset[0] else []
    surfaces = [row.surface for row in editor.rows]
    actions["undo"].trigger()
    settle(0.5)
    rows.append(["R", surfaces == ["Object", "Image"] and after_reset == (True, True, True)
                 and bool(blank) and not np.allclose(before_reset, blank)
                 and len(editor.rows) == loaded and model.rowCount() == loaded,
                 f"Reset -> rows {surfaces}; inspector (alive, the editor's, adopted) {after_reset}; scene bounds "
                 f"{before_reset} -> {blank}; Undo -> {len(editor.rows)} rows (table {model.rowCount()}, was {loaded})"])
    return rows


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_menu_parity import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Qt/Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    folder = tempfile.mkdtemp(prefix="qt_menu_parity_")
    rows = static_checks() + _run(f"qt_runtime_checks({folder!r})")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
