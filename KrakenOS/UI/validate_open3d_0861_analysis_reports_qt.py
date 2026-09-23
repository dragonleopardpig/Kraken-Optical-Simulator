"""Display-free guard: three more analysis reports in the Qt shell (bugs/0861,
docs/design_qt_migration.md phase 3).

Detector Aperture, Path Throughput and Source Illumination -- all three of the same shape as
bugs/0860: their data layers were ALREADY shared (`detector_aperture_analysis.py`,
`branch_throughput_analysis.py`, `source_illumination_analysis.py` own the columns, the value
formatting, the summary and the report text; the collectors live on the editor). Each builder
calls exactly what the corresponding Tk dialog calls, and this guard checks that by recomputing
every cell, summary and text through those same module functions.

  A  each of the five report builders has an action of its own name and a title
  C  the columns come from the analysis modules' own layouts, including centred count columns
  R* per report (detector_aperture, branch_throughput, source_illumination):
     the table's cells equal the module's `*_table_values`, the summary equals its
     `*_summary_text`, the CSV fieldnames are its `*_CSV_COLUMNS`, and Copy carries its
     `*_report_text`
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


def _expected(editor, name):
    """Recompute a report's parts through the analysis modules the Tk dialogs use."""
    if name == "detector_aperture":
        from KrakenOS.UI.detector_aperture_analysis import (
            DETECTOR_APERTURE_CSV_COLUMNS, detector_aperture_report_text,
            detector_aperture_summary_text, detector_aperture_table_values)

        records = list(editor._collect_detector_aperture_records(
            ray_records=editor._active_ray_analysis_records()))
        return (records, detector_aperture_table_values, detector_aperture_summary_text(records),
                detector_aperture_report_text(records), tuple(DETECTOR_APERTURE_CSV_COLUMNS))

    if name == "branch_throughput":
        from KrakenOS.UI.branch_throughput_analysis import (
            BRANCH_THROUGHPUT_CSV_COLUMNS, BRANCH_THROUGHPUT_FILTER_DEFAULT,
            branch_throughput_report_text, branch_throughput_summary_text,
            branch_throughput_table_values, filtered_branch_throughput_records)

        all_records = list(editor._collect_branch_throughput_records(
            ray_records=editor._active_ray_analysis_records()))
        records = list(filtered_branch_throughput_records(
            all_records, BRANCH_THROUGHPUT_FILTER_DEFAULT))
        return (records, branch_throughput_table_values,
                branch_throughput_summary_text(records, all_records,
                                               BRANCH_THROUGHPUT_FILTER_DEFAULT),
                branch_throughput_report_text(records, all_records,
                                              BRANCH_THROUGHPUT_FILTER_DEFAULT),
                tuple(BRANCH_THROUGHPUT_CSV_COLUMNS))

    from KrakenOS.UI.source_illumination_analysis import (
        SOURCE_ILLUMINATION_CSV_COLUMNS, source_illumination_report_text,
        source_illumination_summary_text, source_illumination_table_values)

    target_index = editor._source_illumination_target_index()
    label = ("None" if target_index is None
             else f"S{int(target_index)}: {editor.rows[int(target_index)].name}")
    records = list(editor._collect_source_illumination_records(
        target_index, ray_records=editor._active_ray_analysis_records()))
    return (records, source_illumination_table_values,
            source_illumination_summary_text(records, label),
            source_illumination_report_text(records, label),
            tuple(SOURCE_ILLUMINATION_CSV_COLUMNS))


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

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
    editor = window.editor

    for name in ("detector_aperture", "branch_throughput", "source_illumination"):
        dialog = window.action_manager[name].trigger() or window._open_dialogs[-1]
        app.processEvents()
        report = dialog.report
        records, table_values, summary, text, csv_columns = _expected(editor, name)

        mismatches = []
        for index, record in enumerate(records):
            for column_index, value in enumerate(table_values(record)):
                shown = dialog.model.data(dialog.model.index(index, column_index),
                                          Qt.ItemDataRole.DisplayRole)
                if shown != str(value):
                    mismatches.append((index, column_index, shown, str(value)))
        cells_ok = (dialog.model.rowCount() == len(records) > 0 and not mismatches
                    and dialog.model.columnCount() == len(table_values(records[0])))

        target = Path(tempfile.gettempdir()) / f"kraken_{name}.csv"
        report.write_csv(target)
        with open(target, newline="", encoding="utf-8") as handle:
            written = list(csv.DictReader(handle))
        csv_ok = bool(written) and tuple(written[0].keys()) == csv_columns \
            and len(written) == len(records)

        copied = {}

        class _RecordingHost(QtUiHost):
            def clipboard_set(self, value: str) -> None:
                copied["text"] = value

        saved_host, dialog.host = dialog.host, _RecordingHost(window)
        try:
            dialog.copy_text()
        finally:
            dialog.host = saved_host

        row(f"R:{name}",
            cells_ok and report.summary == summary and csv_ok and copied.get("text") == text
            and window.statusBar().currentMessage().startswith(report.title.split()[0]) is not None,
            f"{dialog.model.rowCount()}x{dialog.model.columnCount()} cells equal the module's "
            f"own table values; summary {report.summary[:56]!r}...; CSV under its "
            f"{len(csv_columns)} fieldnames; Copy carries its {len(text)}-character report text"
            + (f" -- MISMATCH {mismatches[:2]}" if mismatches else ""))
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
        "from KrakenOS.UI.validate_open3d_0861_analysis_reports_qt import qt_runtime_checks\n"
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
            return "skip", [["Qt reports", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    import ast

    from KrakenOS.UI.qt.actions import ACTIONS
    from KrakenOS.UI.reports import REPORT_BUILDERS
    from KrakenOS.UI.reports.detector_aperture import COLUMNS as DETECTOR_COLUMNS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    source = Path("KrakenOS/UI/qt/main_window.py").read_text(encoding="utf-8")
    defined = {node.name for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.FunctionDef)}
    action_names = {name for name, _menu, *_rest in ACTIONS}
    methods = {name: method for name, _menu, _text, _short, method, _tip in ACTIONS}
    missing_action = sorted(set(REPORT_BUILDERS) - action_names)
    missing_method = [methods[name] for name in REPORT_BUILDERS
                      if name in methods and methods[name] not in defined]
    titles = {name: getattr(builder, "TITLE", None) for name, builder in REPORT_BUILDERS.items()}
    ok(len(REPORT_BUILDERS) >= 5 and not missing_action and not missing_method
       and all(titles.values()),
       f"A: all {len(REPORT_BUILDERS)} report builders have an action of their own name, a method "
       f"the window defines, and a title ({sorted(titles)})")

    from KrakenOS.UI.detector_aperture_analysis import DETECTOR_APERTURE_TABLE_LAYOUT

    centred = [column.key for column in DETECTOR_COLUMNS if column.alignment == "c"]
    layout_centred = [key for key, _width, anchor in DETECTOR_APERTURE_TABLE_LAYOUT
                      if anchor == "center"]
    ok(len(DETECTOR_COLUMNS) == len(DETECTOR_APERTURE_TABLE_LAYOUT) and centred == layout_centred
       and centred,
       f"C: the report columns are the analysis module's own layout, centred columns included "
       f"({centred})")

    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP R: {rows[0][2]}")
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
