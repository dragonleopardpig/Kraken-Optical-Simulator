"""Display-free guard: one report, two toolkits (bugs/0859, docs/design_qt_migration.md phase 3).

Phase 3 is 62 dialog functions, ~9 000 lines of Tk. The recipe this guard pins, on the first one
ported: a dialog's DATA becomes a toolkit-free `Report` builder under `KrakenOS/UI/reports/`, and
each toolkit keeps only its layout. The Tk dialog and the Qt dialog then render the SAME object,
so a number cannot differ between them -- and the numbers become checkable without a display.

  P1 the extracted builder returns what the model computes -- checked against an independent
     `system.ParaxMatrices` call, value by value
  P2 the REAL Tk dialog shows exactly the report: its headings and every cell of its Treeview
  P3 the CSV carries the RAW values under the column keys, not the display text
  P4 a model that cannot build the report raises ReportFailed carrying the message to show
  Q1 the Qt dialog's table is the same report: title, summary, and every cell equal to Tk's
  Q2 numeric columns are right-aligned and text columns left-aligned
  Q3 Export CSV asks through the UI host and writes the same file the report writes
  Q4 a failed build reports through the host and opens no dialog
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def _tk_report_dialog_cells(editor):
    """Open the REAL Tk dialog and read back its headings and every cell."""
    import tkinter.ttk as ttk

    before = set(editor.root.winfo_children())
    editor.open_paraxial_matrix_report()
    window = next((child for child in editor.root.winfo_children()
                   if child not in before and str(child.title()) == "Paraxial Matrix Report"), None)
    if window is None:
        return None, None
    try:
        trees = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    trees.append(child)
                walk(child)

        walk(window)
        if not trees:
            return None, None
        tree = trees[0]
        columns = list(tree["columns"])
        headings = [tree.heading(column)["text"] for column in columns]
        cells = [[str(value) for value in tree.item(item, "values")]
                 for item in tree.get_children("")]
        return headings, cells
    finally:
        window.destroy()


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports import build_paraxial_matrix_report
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    expected = build_paraxial_matrix_report(window.editor)
    dialog = window.paraxial_matrix_report_action()
    app.processEvents()

    # ---- Q1 the same report -------------------------------------------------------------------
    model = dialog.model
    mismatches = []
    for r in range(model.rowCount()):
        for c in range(model.columnCount()):
            shown = model.data(model.index(r, c), Qt.ItemDataRole.DisplayRole)
            if shown != expected.cell(r, c):
                mismatches.append((r, c, shown, expected.cell(r, c)))
    headings = [model.headerData(c, Qt.Orientation.Horizontal)
                for c in range(model.columnCount())]
    row("Q1", dialog.windowTitle() == expected.title
        and dialog.summary_label.text() == expected.summary
        and model.rowCount() == len(expected.rows) > 0
        and headings == list(expected.headings) and not mismatches,
        f"{model.rowCount()}x{model.columnCount()} cells equal the report's, headings "
        f"{headings[:4]}..., summary {dialog.summary_label.text()[:44]!r}"
        + (f" -- MISMATCH {mismatches[:2]}" if mismatches else ""))

    # ---- Q2 alignment follows the column kind ---------------------------------------------------
    wrong_alignment = []
    for c, column in enumerate(expected.columns):
        flag = model.data(model.index(0, c), Qt.ItemDataRole.TextAlignmentRole)
        right = bool(int(flag) & int(Qt.AlignmentFlag.AlignRight))
        if right != bool(column.numeric):
            wrong_alignment.append((column.key, right, column.numeric))
    row("Q2", not wrong_alignment,
        f"numeric columns are right-aligned and text columns left-aligned across all "
        f"{len(expected.columns)} columns" + (f" -- wrong {wrong_alignment}" if wrong_alignment else ""))

    # ---- Q3 export through the UI host ----------------------------------------------------------
    target = Path(tempfile.gettempdir()) / "kraken_qt_paraxial_export.csv"
    reference = Path(tempfile.gettempdir()) / "kraken_qt_paraxial_reference.csv"
    expected.write_csv(reference)
    asked = {}

    def fake_save(**options):
        asked.update(options)
        return str(target)

    saved_ask = dialog.host.asksaveasfilename
    dialog.host.asksaveasfilename = fake_save
    try:
        written = dialog.export_csv()
    finally:
        dialog.host.asksaveasfilename = saved_ask
    same = (target.exists()
            and target.read_text(encoding="utf-8") == reference.read_text(encoding="utf-8"))
    row("Q3", written == str(target) and same
        and asked.get("title") == f"Export {expected.title} CSV"
        and asked.get("defaultextension") == ".csv",
        f"Export CSV asked the host ({asked.get('title')!r}) and wrote a file identical to the "
        f"report's own ({same})")

    # ---- Q4 the failure path ---------------------------------------------------------------------
    shown = {}

    # A REAL UiHost subclass: host_of() checks isinstance, so a duck-typed fake would be skipped
    # and the action would reach the live host -- a modal QMessageBox that never returns.
    class _RecordingHost(QtUiHost):
        def showerror(self, title=None, message=None, **options):
            shown.update(title=title, message=message)
            return "ok"

    def _raise(*_args, **_kwargs):
        raise RuntimeError("no paraxial solution")

    editor = window.editor
    editor.build_system = _raise
    saved_ui, window.ui = window.ui, _RecordingHost(window)
    open_before = len(window._open_dialogs)
    try:
        failed = window.paraxial_matrix_report_action()
    finally:
        window.ui = saved_ui
        del editor.build_system
    row("Q4", failed is None and len(window._open_dialogs) == open_before
        and "no paraxial solution" in str(shown.get("message"))
        and "failed" in window.statusBar().currentMessage(),
        f"a model that cannot build the report showed {shown.get('title')!r} and opened no "
        f"dialog; the status line reads {window.statusBar().currentMessage()!r}")

    dialog.close()
    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0859_paraxial_report_shared import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Qt report dialog", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.reports import ReportFailed, build_paraxial_matrix_report
    from KrakenOS.UI.reports.paraxial_matrix import matrix_cell

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        report = build_paraxial_matrix_report(editor)

        # ---- P1 against an independent computation ------------------------------------------
        system = editor.build_system(force_rebuild=True)
        trace = system.ParaxMatrices(editor._current_wavelength())
        drift = []
        for index, surface in enumerate(trace.surfaces):
            record = report.rows[index]
            for key, value in (("surface", int(surface.surface_index)),
                               ("n_before", float(surface.n_before)),
                               ("radius", float(surface.radius)),
                               ("thickness", float(surface.thickness)),
                               ("A", matrix_cell(surface.abcd_matrix, 0, 0)),
                               ("K11", matrix_cell(surface.kraken_matrix, 1, 1))):
                if record[key] != value:
                    drift.append((index, key, record[key], value))
        ok(len(report.rows) == len(trace.surfaces) > 0 and not drift
           and f"{float(trace.effl):.6g}" in report.summary,
           f"P1: the builder's {len(report.rows)} rows equal an independent ParaxMatrices call, "
           f"and the summary carries EFFL {float(trace.effl):.6g} mm"
           + (f" -- DRIFT {drift[:2]}" if drift else ""))

        # ---- P2 the REAL Tk dialog shows the report ------------------------------------------
        headings, cells = _tk_report_dialog_cells(editor)
        expected_cells = [[report.cell(r, c) for c in range(len(report.columns))]
                          for r in range(len(report.rows))]
        ok(headings == list(report.headings) and cells == expected_cells and cells,
           f"P2: the Tk dialog's Treeview shows the report exactly -- {len(cells or [])} rows x "
           f"{len(headings or [])} headings, every cell equal")

        # ---- P3 the CSV carries raw values ---------------------------------------------------
        with tempfile.TemporaryDirectory() as folder:
            path = report.write_csv(Path(folder) / "paraxial.csv")
            with open(path, newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
            keys_ok = bool(written) and list(written[0].keys()) == list(report.keys)
            # Round-trip every numeric cell, and find one the DISPLAY rounds (.8g) so the file is
            # shown to carry the value rather than the text -- 5.35 prints the same either way.
            round_trips = True
            rounded_example = None
            for index, record in enumerate(report.rows):
                for column_index, column in enumerate(report.columns):
                    raw = written[index][column.key]
                    if not column.numeric:
                        continue
                    if float(raw) != float(record[column.key]):
                        round_trips = False
                    if rounded_example is None and raw != report.cell(index, column_index):
                        rounded_example = (column.key, raw, report.cell(index, column_index))
        ok(keys_ok and round_trips and rounded_example is not None,
           f"P3: the CSV's {len(report.keys)} columns are the keys and every numeric value "
           f"round-trips exactly; where the display rounds, the file keeps the value "
           f"({rounded_example[0]}: {rounded_example[1]!r} written, {rounded_example[2]!r} shown)"
           if rounded_example else "P3: no rounded cell found to compare")

        # ---- P4 the failure carries its message ----------------------------------------------
        def _raise(**_kwargs):
            raise RuntimeError("system will not build")

        broken = SimpleNamespace(build_system=_raise, _current_wavelength=lambda: 0.55)
        message = ""
        try:
            build_paraxial_matrix_report(broken)
        except ReportFailed as exc:
            message = str(exc)
        ok("system will not build" in message,
           f"P4: a model that cannot build raises ReportFailed carrying the message to show "
           f"({message!r})")
    finally:
        editor.destroy()

    # ---- Q the Qt dialog, in its own process --------------------------------------------------
    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q1-Q4: {rows[0][2]}")
    else:
        for name, passed, detail in rows:
            ok(passed, f"{name}: {detail}")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
