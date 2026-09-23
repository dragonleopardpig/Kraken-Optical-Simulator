"""Display-free guard: report controls in the Qt shell (bugs/0863,
docs/design_qt_migration.md phase 3).

The Tk Path Throughput dialog has a path FILTER and the Source Illumination dialog a TARGET
selector; the first Qt ports showed each dialog's default and nothing else. A report may now
declare `ReportChoice` controls: the view collects their values, calls the builder again, and
shows what comes back -- so a control needs no Qt-side logic and the filtering stays in the model.

  D  the controls are the model's own choice lists, with the Tk defaults selected
  F  changing the path filter rebuilds through the builder, and the rows are exactly
     `filtered_branch_throughput_records` for that filter -- the module's own function
  T  changing the target surface re-aims the report: the summary is the model's for that target,
     and it differs from Auto's
  O  one change rebuilds ONCE: refreshing the combo's own choices inside the refresh must not
     re-enter the rebuild (the classic Qt signal loop)
  S  a filter value the choices do not contain is kept rather than silently dropped
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.branch_throughput_analysis import (
        BRANCH_THROUGHPUT_FILTER_DEFAULT,
        branch_throughput_filter_choices,
        branch_throughput_table_values,
        filtered_branch_throughput_records,
    )
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.source_illumination_analysis import source_illumination_summary_text

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

    # ---- D the controls come from the model ----------------------------------------------------
    throughput = window.action_manager["branch_throughput"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    illumination = window.action_manager["source_illumination"].trigger() or window._open_dialogs[-1]
    app.processEvents()

    all_records = list(editor._collect_branch_throughput_records(
        ray_records=editor._active_ray_analysis_records()))
    expected_filters = tuple(branch_throughput_filter_choices(all_records))
    expected_targets = tuple(editor._source_illumination_target_choices())
    filter_control = throughput.report.controls[0]
    target_control = illumination.report.controls[0]
    row("D", filter_control.choices == expected_filters
        and filter_control.value == BRANCH_THROUGHPUT_FILTER_DEFAULT
        and target_control.choices == expected_targets and target_control.value == "Auto"
        and set(throughput.controls) == {"filter_text"}
        and set(illumination.controls) == {"target"},
        f"the path filter offers the module's {len(expected_filters)} choices (default "
        f"{filter_control.value!r}) and the target selector the editor's {len(expected_targets)} "
        f"(default {target_control.value!r})")

    # ---- O one change, one rebuild ---------------------------------------------------------------
    calls = {"n": 0}
    real_rebuild = throughput.rebuild

    def counted(**values):
        calls["n"] += 1
        return real_rebuild(**values)

    throughput.rebuild = counted

    # ---- F the filter filters ---------------------------------------------------------------------
    discriminating = next((choice for choice in expected_filters
                           if choice != BRANCH_THROUGHPUT_FILTER_DEFAULT
                           and len(filtered_branch_throughput_records(all_records, choice))
                           != len(all_records)), None)
    chosen = discriminating or next(
        (c for c in expected_filters if c != BRANCH_THROUGHPUT_FILTER_DEFAULT), None)
    throughput.controls["filter_text"].setCurrentText(chosen)
    app.processEvents()
    expected_rows = list(filtered_branch_throughput_records(all_records, chosen))
    mismatches = []
    for index, record in enumerate(expected_rows):
        for column_index, value in enumerate(branch_throughput_table_values(record)):
            shown = throughput.report.cell(index, column_index)
            if shown != str(value):
                mismatches.append((index, column_index, shown, str(value)))
    row("F", throughput.model.rowCount() == len(expected_rows) and not mismatches
        and throughput.report.controls[0].value == chosen
        and f"filter={chosen}" in throughput.report.summary,
        f"picking {chosen!r} rebuilt the report to the {len(expected_rows)} rows "
        f"filtered_branch_throughput_records returns"
        + (" (this scene's filters all match every row, so the count is unchanged by design)"
           if discriminating is None else "")
        + (f" -- MISMATCH {mismatches[:2]}" if mismatches else ""))

    row("O", calls["n"] == 1,
        f"one combo change called the builder exactly {calls['n']} time -- refreshing the "
        f"control's own choices inside the refresh did not re-enter it")

    # ---- T the target re-aims ---------------------------------------------------------------------
    auto_summary = illumination.report.summary
    explicit = next((choice for choice in expected_targets if choice != "Auto"
                     and not choice.startswith("0:")), expected_targets[-1])
    illumination.controls["target"].setCurrentText(explicit)
    app.processEvents()
    index = int(explicit.split(":", 1)[0])
    label = f"S{index}: {editor.rows[index].name}"
    expected_records = list(editor._collect_source_illumination_records(
        index, ray_records=editor._active_ray_analysis_records()))
    row("T", illumination.report.summary == source_illumination_summary_text(
        expected_records, label) and illumination.report.summary != auto_summary
        and illumination.model.rowCount() == len(expected_records)
        and illumination.report.controls[0].value == explicit,
        f"picking {explicit!r} re-aimed the report: {illumination.report.summary[:64]!r}... "
        f"(Auto was {auto_summary[:44]!r}...)")

    # ---- S a stale value survives ------------------------------------------------------------------
    from KrakenOS.UI.reports import build_branch_throughput_report

    stale = build_branch_throughput_report(editor, "Output: no such path")
    row("S", stale.controls[0].value == "Output: no such path"
        and stale.controls[0].choices[0] == "Output: no such path"
        and len(stale.controls[0].choices) == len(expected_filters) + 1,
        f"a filter the choices do not contain is kept and offered "
        f"({stale.controls[0].choices[0]!r}), not silently replaced")

    throughput.close()
    illumination.close()
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
        "from KrakenOS.UI.validate_open3d_0863_report_controls import qt_runtime_checks\n"
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
            return "skip", [["Qt controls", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.reports import REPORT_BUILDERS
    from KrakenOS.UI.reports.base import ReportChoice

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    import inspect

    controlled = {"branch_throughput": "filter_text", "source_illumination": "target"}
    wrong = []
    for name, keyword in controlled.items():
        parameters = inspect.signature(REPORT_BUILDERS[name]).parameters
        if keyword not in parameters or parameters[keyword].default is inspect.Parameter.empty:
            wrong.append((name, keyword))
    ok(not wrong and ReportChoice("k", "l").choices == (),
       f"K: every controlled report's builder takes its control as a keyword with a default "
       f"({controlled}), so a view can call it with no controls at all"
       + (f" -- wrong: {wrong}" if wrong else ""))

    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP D/F/O/T/S: {rows[0][2]}")
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
