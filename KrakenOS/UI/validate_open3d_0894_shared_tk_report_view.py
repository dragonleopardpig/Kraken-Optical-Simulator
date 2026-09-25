"""Display-free guard: the four report dialogs share one Tk renderer over their builders
(bugs/0894, docs/design_qt_migration.md phase 4).

Phase 3 gave each report a toolkit-free builder in `reports/` and the Qt shell a view over it,
but the four Tk windows kept hand-building their own `ttk.Treeview`: 806 lines that decided a
second time what the columns, the widths, the summary and the CSV were. The two toolkits could
therefore disagree, and only the Tk half had the Source Illumination detail pane at all.
`panels/report_view.py` is the Tk counterpart of `qt/dialogs/report_dialog.py`, and
`DetailText` carries that prose pane in the report, so Qt shows it too.

  R  the four panels are their prologue and a `ReportWindow`; none builds a table any more
  D  each REAL Tk window draws exactly the builder's grid -- summary, headings and every cell
  C  changing the Path Throughput filter rebuilds through the builder: the rows are
     `filtered_branch_throughput_records` for the chosen filter, and are not the default's
  T  selecting a Source Illumination row shows that record's own detail prose, from the model
  U  Update refreshes an open report and forgets one the user has closed
  Q  the Qt shell shows that same prose pane, from the same `DetailText`
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"

SCENE = Path("attachment/om05a_folded.py")
PANELS = (
    ("main_branch_throughput_report_dialog", "open_branch_throughput_report",
     "_refresh_branch_throughput_report_if_open"),
    ("main_detector_aperture_report_dialog", "open_detector_aperture_report",
     "_refresh_detector_aperture_report_if_open"),
    ("main_source_illumination_report_dialog", "open_source_illumination_report",
     "_refresh_source_illumination_report_if_open"),
    ("main_branch_gaussian_q_dialog", "open_branch_gaussian_q_report",
     "_refresh_branch_gaussian_q_report_if_open"),
)


def _grid(window):
    """Everything the window is showing: the summary, the headings and every cell."""
    from tkinter import ttk

    tables = []

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, ttk.Treeview):
                tables.append(child)
            walk(child)

    walk(window)
    if not tables:
        return None
    table = tables[0]
    columns = list(table["columns"])
    headings = [str(table.heading(column, "text")) for column in columns]
    rows = [[str(value) for value in table.item(iid, "values")]
            for iid in table.get_children("")]
    return headings, rows


def _builder_grid(report):
    headings = list(report.headings)
    rows = [[report.cell(index, column) for column in range(len(report.columns))]
            for index in range(len(report.rows))]
    return headings, rows


def qt_runtime_checks() -> list[list]:
    """The Qt half: the prose detail pane the port gave Qt, driven through the real dialog."""
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.source_illumination_analysis import source_illumination_record_detail_text

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = (window.action_manager["source_illumination"].trigger()
              or window._open_dialogs[-1])
    app.processEvents()
    records = list(dialog.report.rows)
    if not records:
        return [["Q", False, "the Qt source illumination report has no record to select"]]
    index = len(records) - 1
    dialog.select_master_row(index)
    app.processEvents()
    shown = dialog.detail_text.toPlainText() if dialog.detail_text is not None else None
    expected = source_illumination_record_detail_text(records[index])
    rows = [["Q", shown == expected,
             f"the Qt dialog showed source {index}'s own detail prose ({len(expected)} chars), "
             f"the pane only Tk used to have"
             if shown == expected else
             f"the Qt detail pane showed {str(shown)[:60]!r}, model says {expected[:60]!r}"]]
    dialog.close()
    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0894_shared_tk_report_view import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.branch_throughput_analysis import filtered_branch_throughput_records
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import report_view
    from KrakenOS.UI.source_illumination_analysis import source_illumination_record_detail_text

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- R the panels are shims -------------------------------------------------------------
    sizes = {}
    for panel, _open_method, _refresh in PANELS:
        source = (Path("KrakenOS/UI/panels") / f"{panel}.py").read_text(encoding="utf-8")
        sizes[panel] = len(source.splitlines())
        if "ReportWindow(" not in source or "build_" not in source:
            ok(False, f"R: {panel} does not render its builder through ReportWindow")
            break
        if "ttk.Treeview(" in source or "tk.Toplevel(" in source:
            ok(False, f"R: {panel} still builds its own window or table")
            break
    else:
        ok(max(sizes.values()) < 100,
           "R: the four report panels are a builder and a ReportWindow now -- "
           + ", ".join(f"{name[5:].replace('_', ' ')} {size}" for name, size in sizes.items())
           + " lines")

    view = inspect.getsource(report_view)
    ok("report.cell(index, column)" in view and "report.write_csv(path)" in view
       and "report.detail_text" in view,
       "R2: the renderer asks the report for every cell, the CSV and the detail prose")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor.refresh_plot()

        # ---- D every window draws its builder's grid ----------------------------------------
        for panel, open_method, _refresh in PANELS:
            dialog = getattr(editor, f"_{panel}")()
            getattr(dialog, open_method)()
            handle = dialog._report_window
            drawn = _grid(handle.window)
            expected = _builder_grid(handle.report)
            summary_shown = handle.summary_var.get()
            ok(drawn == expected and summary_shown == handle.report.summary,
               f"D: {handle.report.title} drew the builder's grid "
               f"({len(expected[1])} rows x {len(expected[0])} columns) and its summary"
               if drawn == expected and summary_shown == handle.report.summary else
               f"D: {panel} drew {drawn} for a builder grid of {expected}")

        # ---- C the filter rebuilds through the builder ---------------------------------------
        throughput = editor._main_branch_throughput_report_dialog()._report_window
        default_rows = list(throughput.report.rows)
        all_records = list(editor._collect_branch_throughput_records(
            ray_records=editor._active_ray_analysis_records()))
        # the choice the MODEL says narrows the list most: a filter that changes nothing would
        # make this check pass whether or not the view rebuilt at all
        offered = list(throughput.control_widgets["filter_text"]["values"])
        narrowing = min(offered, key=lambda value: len(
            filtered_branch_throughput_records(all_records, value)), default=None)
        expected = (list(filtered_branch_throughput_records(all_records, narrowing))
                    if narrowing is not None else [])
        if narrowing is None or len(expected) >= len(default_rows):
            ok(False, f"C: no offered path filter narrows {len(default_rows)} rows ({offered})")
        else:
            throughput.controls["filter_text"].set(narrowing)
            throughput.refresh()
            drawn = _grid(throughput.window)[1]
            ok(throughput.report.rows == expected and len(drawn) == len(expected),
               f"C: picking {narrowing!r} rebuilt through the builder -- {len(expected)} of "
               f"{len(all_records)} paths drawn, where the default showed {len(default_rows)}"
               if throughput.report.rows == expected else
               f"C: filter {narrowing!r} gave {len(throughput.report.rows)} rows and drew "
               f"{len(drawn)}, model says {len(expected)}")

        # ---- T the prose detail pane ---------------------------------------------------------
        illumination = editor._main_source_illumination_report_dialog()._report_window
        records = list(illumination.report.rows)
        if not records:
            ok(False, "T: the source illumination report has no record to select")
        else:
            index = len(records) - 1
            illumination.select_row(index)
            shown = illumination.detail_widget.get("1.0", "end-1c")
            expected = source_illumination_record_detail_text(records[index])
            ok(shown == expected and illumination.selected_key() == index,
               f"T: selecting source {index} showed the model's own detail prose "
               f"({len(expected)} chars)" if shown == expected else
               f"T: detail pane showed {shown[:60]!r}, model says {expected[:60]!r}")

        # ---- U Update refreshes what is open, and forgets what is not -------------------------
        before = illumination.report
        editor._refresh_source_illumination_report_if_open()
        refreshed = illumination.report is not before and illumination.is_open()
        detector = editor._main_detector_aperture_report_dialog()._report_window
        detector.window.destroy()
        editor._refresh_detector_aperture_report_if_open()
        ok(refreshed and detector.window is None and not detector.is_open(),
           "U: Update rebuilt the open report and dropped the one the user had closed"
           if refreshed else
           f"U: refresh_if_open rebuilt={refreshed}, closed window forgotten="
           f"{detector.window is None}")
    finally:
        editor.destroy()

    # ---- Q the same pane in the Qt shell -------------------------------------------------
    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
    else:
        for name, passed, detail in qt_rows:
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
