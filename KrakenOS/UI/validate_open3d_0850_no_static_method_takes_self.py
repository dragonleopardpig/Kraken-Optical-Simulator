"""Display-free guard: no static method takes ``self`` -- the Optimize button and the Paraxial
Matrix Report menu item work again (bugs/0850).

Found while cutting the Qt seam (docs/design_qt_migration.md): the seam converter would not
touch a `self.after(...)` inside `start_optimization`, because that method was a STATIC method.
The mixin extraction of 2026-05-26 (fcb42075) left a stray decorator a blank line above two
methods:

    @staticmethod

    def start_optimization(self) -> None:          # Optimize button
    def open_paraxial_matrix_report(self) -> None: # Action -> Paraxial Matrix Report

A static method gets no instance, so `command=self.start_optimization` called it with NO
arguments and raised `TypeError: missing 1 required positional argument: 'self'` -- every click,
for four months (report_callback_exception showed it; the features never ran).

  S  across KrakenOS no static method's first parameter is self/cls (AST, the whole package) --
     with a CONTROL showing the scan finds the pattern when it is there
  B  both methods, called exactly as their button / menu entry calls them (a bound method, no
     arguments), now reach their bodies -- with a CONTROL: the static version raises TypeError
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace


def _static_self_methods(tree) -> list[str]:
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            static = any(isinstance(d, ast.Name) and d.id == "staticmethod" for d in node.decorator_list)
            args = [a.arg for a in node.args.posonlyargs + node.args.args]
            if static and args and args[0] in ("self", "cls"):
                found.append(f"{node.name}@{node.lineno}")
    return found


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- S: the invariant, package-wide -------------------------------------------------------------
    offenders = []
    for path in Path("KrakenOS").rglob("*.py"):
        if "archive" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(errors="replace"))
        except SyntaxError:
            continue
        offenders += [f"{path}:{hit}" for hit in _static_self_methods(tree)]
    ok(not offenders, f"S1: no static method in KrakenOS takes self/cls ({offenders or 'none'})")
    control = ast.parse("class C:\n    @staticmethod\n\n    def m(self) -> None:\n        pass\n")
    ok(_static_self_methods(control) == ["m@4"],
       "S2: CONTROL -- the scan finds the exact slip (decorator, blank line, def with self)")

    # ---- B: called the way the UI calls them -------------------------------------------------------
    class _Owner:
        start_optimization = AnalysisComputeWorkflowMixin.start_optimization
        open_paraxial_matrix_report = LayoutTableWorkbenchMixin.open_paraxial_matrix_report

        def __init__(self):
            self.optimization_running = True          # start_optimization returns at its guard
            self.opened = []
            self._main_paraxial_analysis_dialogs = lambda: SimpleNamespace(
                open_paraxial_matrix_report=lambda: self.opened.append("paraxial"))

    owner = _Owner()
    button = owner.start_optimization                 # what `command=self.start_optimization` holds
    menu = owner.open_paraxial_matrix_report
    try:
        button()
        menu()
        reached = owner.opened == ["paraxial"]
        error = ""
    except TypeError as exc:
        reached, error = False, str(exc)
    ok(reached, f"B1: the Optimize button and the Paraxial Matrix Report entry reach their bodies "
                f"when called with no arguments {error}")

    class _Static:
        start_optimization = staticmethod(AnalysisComputeWorkflowMixin.start_optimization)

    try:
        _Static().start_optimization()
        raised = ""
    except TypeError as exc:
        raised = str(exc)
    ok("self" in raised, f"B2: CONTROL -- the static version raises the error every click hit ({raised!r})")
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
