"""Guard for bugs/0984: a report window's handle has no toolkit in it; the Tk view is imported when Tk draws.

`ReportWindow` is what a report panel keeps: it opens, refreshes and closes the report, answers for
the selection, copies, exports and runs the report's verbs. Under a shell that draws its own
dialogs it hands all of that to the shell's dialog. It was ALSO the Tk view -- one class of 510
lines in `panels/report_view.py` -- so every panel that wanted a handle loaded tkinter with it, and
through the panels `services/analysis_reports.py` did.

It is two modules now: the handle, `reports/window.py`, and the Tk view, `panels/report_view.py`,
which is functions over the handle and is imported only when Tk actually draws.

That the Tk windows draw their builders' grids, rebuild on a filter, keep the selection, copy and
export is what phases 682-685 hold (0894-0897), and the Qt dialogs phases 638-645. This guard holds
what the split added:

  S  the handle module names no tkinter; the Tk view defines no class of its own and the name
     `ReportWindow` there is the same class; every method the class had is still a method of it;
     no module takes the handle from the Tk view any more
  L  asked of the interpreter, each in a process of its own: importing the handle loads neither
     tkinter nor Qt, and the six report-only panels load no tkinter
  N  a handle that was never opened, used in every way, in a fresh process: it is not open, has no
     selection and no control values, refresh / close / select are no-ops -- and no tkinter is loaded
  Q  a handle under a shell, in a fresh process, with a stand-in dialog: open hands the builder to
     the shell and takes the report from its dialog; open again refreshes and raises it; refresh
     rebuilds with the dialog's control values and gives the dialog the new report; the selection
     is asked of and set on the dialog; the report's verb runs with the controls and the
     selection; export asks the host for a path and writes the CSV; close closes the dialog --
     and neither tkinter nor the Tk view was ever imported
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("KrakenOS/UI")
REPORT_ONLY_PANELS = ("main_branch_gaussian_q_dialog", "main_branch_throughput_report_dialog", "main_detector_aperture_report_dialog",
                      "main_nonseq_scene_graph_dialog", "main_ray_trace_inspectors", "main_source_illumination_report_dialog")
METHODS = ("__init__", "editor", "_shell_report", "_shell_view", "is_open", "open", "close", "refresh_if_open", "refresh",
           "control_values", "_build", "_set_status", "_make_window", "_make_table", "_make_detail_table", "_render",
           "_insert_tree", "_refresh_controls", "selected_key", "select_key", "select_row", "refresh_detail", "_show_detail",
           "copy_text", "run_action", "export_csv")
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog"}
LOADED = "sorted(n for n in ('tkinter', 'PySide6', 'KrakenOS.UI.panels.report_view') if n in sys.modules)"

NEVER_OPENED = f'''
import json, sys
from types import SimpleNamespace
from KrakenOS.UI.reports.window import ReportWindow

status = []
owner = SimpleNamespace(status_var=SimpleNamespace(set=status.append))
handle = ReportWindow(owner, lambda **controls: None)
answers = [handle.is_open(), handle.control_values(), handle.selected_key(), handle.window, handle.table]
handle.refresh_if_open(); handle.refresh(); handle.select_key(3); handle.select_row(1); handle.refresh_detail(); handle.close()
print(json.dumps({{"answers": answers, "open_after": handle.is_open(), "status": status, "loaded": {LOADED}}}))
'''

UNDER_A_SHELL = f'''
import csv, json, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
from KrakenOS.UI.reports.base import Report, ReportAction, ReportColumn
from KrakenOS.UI.reports.window import ReportWindow
from KrakenOS.UI.uihost import ScriptedUiHost

built, ran = [], []

def build(**controls):
    built.append(dict(controls))
    scale = int(controls.get("scale", "1"))
    return Report(title="Guard report", summary=f"scale {{scale}}",
                  columns=(ReportColumn("n", "N"), ReportColumn("v", "Value")),
                  rows=tuple({{"n": index, "v": index * scale}} for index in range(3)),
                  actions=(ReportAction("Mark", lambda controls, key: (ran.append((dict(controls), key)), "marked")[1],
                                        needs_controls=True, needs_selection=True),))

class Dialog:                                   # stands in for the shell's own report dialog
    def __init__(self, builder):
        self.visible, self.selected, self.calls = True, 0, []
        self.values = {{"scale": "2"}}
        self.report = builder(**self.values)
    def isVisible(self): return self.visible
    def raise_(self): self.calls.append("raise_")
    def activateWindow(self): self.calls.append("activateWindow")
    def set_report(self, report): self.calls.append("set_report"); self.report = report
    def control_values(self): return dict(self.values)
    def selected_key(self): return self.selected
    def select_key(self, key): self.calls.append(("select_key", key)); self.selected = key
    def select_master_row(self, index): self.calls.append(("select_master_row", index)); self.selected = index
    def close(self): self.calls.append("close"); self.visible = False

work = Path(tempfile.mkdtemp(prefix="g0984_"))
host = ScriptedUiHost(answers={{"asksaveasfilename": str(work / "out.csv")}})
status = []
editor = SimpleNamespace(ui=host, status_var=SimpleNamespace(set=status.append))
shown = []
editor.show_report = lambda builder: (shown.append(builder), Dialog(builder))[1]
panel = SimpleNamespace(editor=editor, status_var=editor.status_var)

handle = ReportWindow(panel, build, csv_title="Guard")
view = handle.open()
first = {{"shell_got_builder": shown == [build], "report": handle.report.summary, "open": handle.is_open(), "is_dialog": view is handle.shell_view}}
again = handle.open()
second = {{"same_dialog": again is view, "calls": [c for c in view.calls if isinstance(c, str)], "built_with": built[-1]}}
view.values["scale"] = "5"
handle.refresh()
third = {{"built_with": built[-1], "dialog_report": view.report.summary, "handle_report": handle.report.summary}}
handle.select_key(2)
key_after_select_key = handle.selected_key()
handle.select_row(1)
selection = {{"select_key": key_after_select_key, "select_row": handle.selected_key(), "dialog_calls": [c for c in view.calls if isinstance(c, tuple)]}}
verb = handle.run_action(handle.report.actions[0])
exported = handle.export_csv()
rows = list(csv.reader(open(work / "out.csv", newline="", encoding="utf-8"))) if (work / "out.csv").exists() else []
handle.close()
print(json.dumps({{"first": first, "second": second, "third": third, "selection": selection,
                  "verb": [verb, ran], "export": [Path(exported).name if exported else "", len(rows), status[-1] if status else ""],
                  "closed": [view.calls[-1], handle.is_open(), handle.shell_view is None], "loaded": {LOADED}}}))
'''


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _fresh(code: str) -> str:
    """The last line a fresh interpreter prints for ``code``."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=str(Path.cwd()))
    return (done.stdout.strip().splitlines() or ["ERROR " + done.stderr.strip()[-300:]])[-1]


def run_checks() -> tuple[bool, list[str]]:
    def s():
        from KrakenOS.UI.panels import report_view
        from KrakenOS.UI.reports import window

        handle_tree = ast.parse((ROOT / "reports/window.py").read_text(encoding="utf-8"))
        named = sorted({node.id for node in ast.walk(handle_tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        view_tree = ast.parse((ROOT / "panels/report_view.py").read_text(encoding="utf-8"))
        view_classes = [node.name for node in view_tree.body if isinstance(node, ast.ClassDef)]
        view_functions = [node.name for node in view_tree.body if isinstance(node, ast.FunctionDef)]
        missing = [name for name in METHODS if name not in vars(window.ReportWindow)]
        from_view = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.py")
                           if "archive" not in path.parts and not path.name.startswith("validate_")
                           and "panels.report_view import ReportWindow" in path.read_text(encoding="utf-8", errors="replace"))
        return (named == [] and view_classes == [] and len(view_functions) >= 12 and missing == [] and len(METHODS) == 26
                and report_view.ReportWindow is window.ReportWindow and from_view == [],
                f"the handle names tkinter {named or 'nowhere'}; the Tk view has {len(view_classes)} classes and "
                f"{len(view_functions)} functions; of the class's {len(METHODS)} methods {missing or 'none'} are missing; the old "
                f"name is the same class: {report_view.ReportWindow is window.ReportWindow}; modules still taking the handle "
                f"from the Tk view: {from_view or 'none'}")

    def l():
        handle = _fresh(f"import sys\nimport KrakenOS.UI.reports.window\nprint({LOADED})\n")
        panels = {name: _fresh(f"import sys\nimport KrakenOS.UI.panels.{name}\nprint('tkinter' in sys.modules)\n")
                  for name in REPORT_ONLY_PANELS}
        return (handle == "[]" and all(answer == "False" for answer in panels.values()) and len(panels) == 6,
                f"importing the handle loads {handle}; the {len(panels)} report-only panels that load tkinter when imported: "
                f"{sorted(name for name, answer in panels.items() if answer != 'False') or 'none'}")

    def n():
        answer = _fresh(NEVER_OPENED)
        data = json.loads(answer)
        return (data == {"answers": [False, {}, None, None, None], "open_after": False, "status": [], "loaded": []},
                f"a handle never opened: open {data['answers'][0]}, control values {data['answers'][1]}, selection "
                f"{data['answers'][2]}; after refresh, select and close it is open {data['open_after']} and said "
                f"{data['status']}; loaded {data['loaded']}")

    def q():
        answer = _fresh(UNDER_A_SHELL)
        data = json.loads(answer)
        expected = {
            "first": {"shell_got_builder": True, "report": "scale 2", "open": True, "is_dialog": True},
            "second": {"same_dialog": True, "calls": ["set_report", "raise_", "activateWindow"], "built_with": {"scale": "2"}},
            "third": {"built_with": {"scale": "5"}, "dialog_report": "scale 5", "handle_report": "scale 5"},
            "selection": {"select_key": 2, "select_row": 1, "dialog_calls": [["select_key", 2], ["select_master_row", 1]]},
            "verb": ["marked", [[{"scale": "5"}, 1]]],
            "export": ["out.csv", 4, "Guard CSV exported: out.csv"],
            "closed": ["close", False, True],
            "loaded": [],
        }
        wrong = sorted(key for key in expected if data.get(key) != expected[key])
        return (wrong == [],
                f"under a shell: opened {data['first']}; opened again {data['second']}; refreshed {data['third']}; selection "
                f"{data['selection']}; the verb {data['verb']}; export {data['export']}; closed {data['closed']}; loaded "
                f"{data['loaded']}" + (f" -- NOT as expected: {wrong}" if wrong else ""))

    rows = _claims((("S", s), ("L", l), ("N", n), ("Q", q)))
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
