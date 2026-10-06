"""Guard for bugs/0970: the toolkit-free layers import no tkinter -- a list that may only shrink.

Phase 7d of the Qt migration. `services/`, `reports/`, `row_forms/`, `uihost/` and `qt/` are meant to
hold no toolkit code but the Tk host itself. Measured 2026-10-06: 14 of 151 service modules imported
tkinter. Six did not need to -- five never used what they imported, one used it only to annotate a
dialog's parent (which is a Qt widget under the Qt shell) -- and a seventh made two `tk.BooleanVar`s
that no other host can make. The seven left each hold a real Tk window or menu; they are listed
here with what they hold, and move out one at a time.

  S  the scan: every module of those layers that imports tkinter at run time is in `TK_IMPORTERS`,
     and every entry there still does. A new importer fails here; a cleaned module must be deleted
     from the list -- so it can only shrink. (An import under `if TYPE_CHECKING:` is not a run-time
     import.)
  M  the modules cleaned by bugs/0970 import, and none still refers to a tkinter name
  V  a station loaded with no inspector gets its two inspector switches from the editor's UI HOST:
     on a toolkit-free owner both are made, as booleans holding False, and an existing one is left
     alone (they were `tk.BooleanVar`s: on such an owner the old code made none)
"""
from __future__ import annotations

import ast
import importlib
from pathlib import Path

ROOT = Path("KrakenOS/UI")
LAYERS = ("services", "reports", "row_forms", "uihost", "qt")
#: module -> the Tk code it still holds. EXACT: a port deletes its entry.
TK_IMPORTERS = {
    "services/analysis_compute_workflow.py": "the Tk text widgets' copy shortcuts and context menu",
    "services/layout_bug_recorder.py": "the Tk editor's own flag popup, and its scan of open Tk windows",
    "services/layout_shell_controls.py": "fills the Tk menu bar's layout / example / Zemax submenus",
    "services/open3d_thickness_dimensions.py": "the Tk inline thickness editor (the shell is asked first, bugs/0950)",
    "services/paraxial_tools.py": "Tk popup-menu and dialog-centring helpers",
    "services/scene_placement_commands.py": "the Tk LED edge-distance prompt (the shell is asked first, bugs/0950)",
    "services/system_selection.py": "the Tk System Selection window",
    "uihost/tk_host.py": "the Tk host itself",
}
#: the modules bugs/0970 cleaned
CLEANED = ("services/tolerance_modeling.py", "services/open3d_face_assignment.py", "services/layout_import_export.py",
           "services/three_d_scene_tools.py", "services/layout_analysis_display.py", "services/step_overlay_import.py",
           "services/inspection_cell.py")
TK_NAMES = {"tk", "ttk", "_tk", "tkfont", "messagebox", "filedialog", "simpledialog", "colorchooser"}


def _type_checking_lines(tree) -> set:
    """Line numbers inside an ``if TYPE_CHECKING:`` block -- not run-time code."""
    lines: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test = node.test
            name = test.id if isinstance(test, ast.Name) else test.attr if isinstance(test, ast.Attribute) else ""
            if name == "TYPE_CHECKING":
                for inner in node.body:
                    lines.update(range(inner.lineno, (inner.end_lineno or inner.lineno) + 1))
    return lines


def tkinter_importers() -> dict:
    """module -> the line numbers of its run-time tkinter imports."""
    found: dict = {}
    for layer in LAYERS:
        for path in sorted((ROOT / layer).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            skip = _type_checking_lines(tree)
            lines = []
            for node in ast.walk(tree):
                if node.__class__ is ast.Import and any(alias.name.split(".")[0] == "tkinter" for alias in node.names):
                    lines.append(node.lineno)
                elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter":
                    lines.append(node.lineno)
            lines = [line for line in lines if line not in skip]
            if lines:
                found[path.relative_to(ROOT).as_posix()] = sorted(lines)
    return found


def run_checks() -> tuple[bool, list[str]]:
    from types import SimpleNamespace

    from KrakenOS.UI.services import inspection_cell
    from KrakenOS.UI.uihost import ObservableValue, ScriptedUiHost

    rows = []
    found = tkinter_importers()
    unlisted = sorted(set(found) - set(TK_IMPORTERS))
    stale = sorted(set(TK_IMPORTERS) - set(found))
    services = sorted(name for name in found if name.startswith("services/"))
    rows.append(["S", not unlisted and not stale and len(services) == 7,
                 f"{len(found)} modules of {'/'.join(LAYERS)} import tkinter at run time, {len(services)} of them services "
                 f"(14 before bugs/0970); not in the list: {unlisted or 'none'}; listed but clean now (delete the entry): "
                 f"{stale or 'none'}"])

    problems = []
    for name in CLEANED:
        module = "KrakenOS.UI." + name[:-3].replace("/", ".")
        try:
            importlib.import_module(module)
        except Exception as exc:
            problems.append(f"{name}: import raised {type(exc).__name__}: {exc}")
            continue
        tree = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        loose = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        if loose:
            problems.append(f"{name}: still refers to {loose}")
        if name in found:
            problems.append(f"{name}: imports tkinter again (line {found[name]})")
    rows.append(["M", not problems, f"the {len(CLEANED)} cleaned modules import and refer to no tkinter name: {problems or 'all clean'}"])

    bare = SimpleNamespace(ui=ScriptedUiHost())
    made = inspection_cell.seed_inspector_variables(bare)
    values = {name: getattr(bare, name, None) for name, _default in inspection_cell.STATION_INSPECTOR_VARIABLES}
    kinds = {name: (type(value).__name__, getattr(value, "kind", None), value.get() if value is not None else None)
             for name, value in values.items()}
    keep = ObservableValue("boolean", True)
    held = SimpleNamespace(ui=ScriptedUiHost(), show_terminal_diagnostics_var=keep)
    made_again = inspection_cell.seed_inspector_variables(held)
    expected = [name for name, _default in inspection_cell.STATION_INSPECTOR_VARIABLES]
    rows.append(["V", made == expected and len(expected) == 2
                 and all(kind == ("ObservableValue", "boolean", False) for kind in kinds.values())
                 and held.show_terminal_diagnostics_var is keep and keep.get() is True
                 and made_again == ["show_reference_surfaces_var"],
                 f"on a toolkit-free owner the station gets {made} as {sorted(set(kinds.values()))}; an owner that already has "
                 f"one keeps it ({held.show_terminal_diagnostics_var is keep}) and gets only {made_again}"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
