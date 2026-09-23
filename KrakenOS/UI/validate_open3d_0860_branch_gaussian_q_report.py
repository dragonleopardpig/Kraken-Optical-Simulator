"""Display-free guard: the Branch Gaussian Q report in the Qt shell (bugs/0860,
docs/design_qt_migration.md phase 3).

The second report ported, and a different starting point from the first: this dialog's data layer
was ALREADY shared -- `services/analysis_reports._collect_branch_gaussian_q_records` collects and
`KrakenOS/UI/branch_gaussian_q_report.py` formats. The Qt builder therefore calls exactly what the
Tk dialog calls; it re-implements nothing, and this guard checks that by comparing the Qt table
against those same functions.

It also pins what made the report work at all: the Qt shell's redraw traces with `update_state`
LEFT AT ITS DEFAULT, so `last_system` / `last_rays` are the live trace every analysis reads. The
viewport first passed `update_state=False` -- copied from a validator, not from the app -- and
every analysis in the shell had nothing to report on.

  E  with no trace, the report is the Tk dialog's empty state, not a crash
  A  each report action names a real window method, and the builders carry their title
  S  after a redraw the shell's live trace state is set, so analyses have data
  B1 every cell of the Qt table equals `branch_gaussian_q_table_values` -- the row tuple the Tk
     Treeview inserts
  B2 the summary equals `branch_gaussian_q_summary_text` over the same collector's summary
  B3 the CSV uses BRANCH_GAUSSIAN_Q_CSV_COLUMNS (which are NOT the table's columns) and writes
     the raw records
  B4 Copy puts `branch_gaussian_q_report_text` on the clipboard, through the UI host
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


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.branch_gaussian_q_report import (
        BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
        branch_gaussian_q_report_text,
        branch_gaussian_q_summary_text,
        branch_gaussian_q_table_values,
    )
    from KrakenOS.UI.qt.app import build
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

    # ---- S the redraw is the app tracing -------------------------------------------------------
    editor = window.editor
    live_system = getattr(editor, "last_system", None)
    live_rays = getattr(editor, "last_rays", None)
    records = editor._active_ray_analysis_records()
    row("S", live_system is not None and live_rays is not None and len(records) > 0,
        f"after the shell's redraw the live trace state is set (system={live_system is not None}, "
        f"rays={live_rays is not None}) and the analyses see {len(records)} ray records")

    # ---- the dialog ----------------------------------------------------------------------------
    dialog = window.action_manager["branch_gaussian_q"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    report = dialog.report

    expected_rows, expected_summary = editor._collect_branch_gaussian_q_records(
        records=editor._active_ray_analysis_records())

    # ---- B1 the cells are the shared formatter's ----------------------------------------------
    from PySide6.QtCore import Qt

    model = dialog.model
    mismatches = []
    for index, record in enumerate(expected_rows):
        values = branch_gaussian_q_table_values(record)
        for column_index, value in enumerate(values):
            shown = model.data(model.index(index, column_index), Qt.ItemDataRole.DisplayRole)
            if shown != str(value):
                mismatches.append((index, column_index, shown, str(value)))
                if len(mismatches) > 3:
                    break
        if len(mismatches) > 3:
            break
    row("B1", model.rowCount() == len(expected_rows) > 0
        and model.columnCount() == len(branch_gaussian_q_table_values(expected_rows[0]))
        and not mismatches,
        f"{model.rowCount()}x{model.columnCount()} cells equal branch_gaussian_q_table_values -- "
        f"the tuple the Tk Treeview inserts"
        + (f" -- MISMATCH {mismatches[:2]}" if mismatches else ""))

    # ---- B2 the summary -------------------------------------------------------------------------
    row("B2", report.summary == branch_gaussian_q_summary_text(expected_summary)
        and "traces=" in report.summary,
        f"the summary is the collector's own: {report.summary[:72]!r}...")

    # ---- B3 the CSV ------------------------------------------------------------------------------
    target = Path(tempfile.gettempdir()) / "kraken_branch_q_export.csv"
    report.write_csv(target)
    with open(target, newline="", encoding="utf-8") as handle:
        written = list(csv.DictReader(handle))
    fieldnames = list(written[0].keys()) if written else []
    sample_ok = bool(written) and str(written[0]["ray_index"]) == str(
        expected_rows[0]["ray_index"])
    row("B3", fieldnames == list(BRANCH_GAUSSIAN_Q_CSV_COLUMNS)
        and fieldnames != list(report.keys) and len(written) == len(expected_rows) and sample_ok,
        f"the CSV's {len(fieldnames)} fieldnames are BRANCH_GAUSSIAN_Q_CSV_COLUMNS, not the "
        f"table's {len(report.keys)} columns, and it holds the {len(written)} raw records")

    # ---- B4 Copy ---------------------------------------------------------------------------------
    copied = {}

    class _RecordingHost(QtUiHost):
        def clipboard_set(self, text: str) -> None:
            copied["text"] = text

    saved_host, dialog.host = dialog.host, _RecordingHost(window)
    try:
        dialog.copy_text()
    finally:
        dialog.host = saved_host
    expected_text = branch_gaussian_q_report_text(list(expected_rows), expected_summary)
    row("B4", dialog.copy_button is not None and copied.get("text") == expected_text
        and "KrakenOS Branch Gaussian Q Report" in expected_text,
        f"Copy put the model's own {len(expected_text)}-character report text on the clipboard "
        f"through the host")

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
        "from KrakenOS.UI.validate_open3d_0860_branch_gaussian_q_report import qt_runtime_checks\n"
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
            return "skip", [["Qt report", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    import ast

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.qt.actions import ACTIONS
    from KrakenOS.UI.reports import REPORT_BUILDERS, build_branch_gaussian_q_report
    from KrakenOS.UI.reports.branch_gaussian_q import EMPTY

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- E the empty state, without any trace ---------------------------------------------------
    editor = KrakenLayoutEditor(headless=True)
    try:
        empty = build_branch_gaussian_q_report(editor)
        ok(empty.rows == [] and empty.summary == EMPTY and empty.status == EMPTY
           and empty.columns,
           f"E: with no trace the report is the Tk dialog's empty state ({empty.summary!r}) and "
           f"still carries its {len(empty.columns)} columns")
    finally:
        editor.destroy()

    # ---- A the actions ---------------------------------------------------------------------------
    source = Path("KrakenOS/UI/qt/main_window.py").read_text(encoding="utf-8")
    defined = {node.name for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.FunctionDef)}
    report_actions = [name for name, _menu, *_rest in ACTIONS if name in REPORT_BUILDERS]
    missing = [(name, method) for name, _menu, _text, _short, method, _tip in ACTIONS
               if method not in defined]
    titled = [getattr(builder, "TITLE", None) for builder in REPORT_BUILDERS.values()]
    ok(sorted(report_actions) == sorted(REPORT_BUILDERS) and not missing and all(titled),
       f"A: every report builder {sorted(REPORT_BUILDERS)} has an action of the same name, each "
       f"action names a method the window defines, and every builder carries its title {titled}")

    # ---- the Qt sections -------------------------------------------------------------------------
    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP S/B1-B4: {rows[0][2]}")
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
