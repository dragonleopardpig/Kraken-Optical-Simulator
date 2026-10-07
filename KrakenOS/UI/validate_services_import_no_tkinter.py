"""Guard for bugs/0970: the toolkit-free layers import no tkinter -- a list that may only shrink.

Phase 7d of the Qt migration. `services/`, `reports/`, `row_forms/`, `uihost/` and `qt/` are meant to
hold no toolkit code but the Tk host itself. Measured 2026-10-06: 14 of 151 service modules imported
tkinter. Six did not need to -- five never used what they imported, one used it only to annotate a
dialog's parent (which is a Qt widget under the Qt shell) -- and a seventh made two `tk.BooleanVar`s
that no other host can make. The seven left each held a real Tk window or menu; they are listed
here with what they hold, and move out one at a time (bugs/0972 moved the first, bugs/0976 the
second, bugs/0977 the third, bugs/0978 the fourth: three left).

  I  the other way in: a service that imports a Tk VIEW module (`panels/`, `widgets/`) at module
     level reaches tkinter without naming it. Those are counted too, against their own exact list
     (bugs/0972) -- five services, each building a Tk delegation panel or binding a Tk widget
  S  the scan: every module of those layers that imports tkinter at run time is in `TK_IMPORTERS`,
     and every entry there still does. A new importer fails here; a cleaned module must be deleted
     from the list -- so it can only shrink. (An import under `if TYPE_CHECKING:` is not a run-time
     import.)
  G  no GUARD reaches for a tkinter name THROUGH one of those modules (`fa_mod.tk.Menu = Fake`).
     That works only while the module still has its own `import tkinter as tk`, and raises
     AttributeError the day it is cleaned: bugs/0970 broke two guards that way (phases 293 and
     296), and nothing short of the full Tk gate saw it
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
    "services/layout_bug_recorder.py": "the Tk editor's own flag popup, and its scan of open Tk windows",
    "services/paraxial_tools.py": "Tk popup-menu and dialog-centring helpers",
    "services/system_selection.py": "the Tk System Selection window",
    "uihost/tk_host.py": "the Tk host itself",
}
#: A service can also reach Tk WITHOUT naming it: by importing a Tk view module (`panels/`,
#: `widgets/`) at module level. Counted separately, and as exactly (bugs/0972).
TK_VIEW_PACKAGES = ("KrakenOS.UI.panels", "KrakenOS.UI.widgets")
TK_VIEW_IMPORTERS = {
    "services/analysis_reports.py": "builds the seven Tk report / inspector delegation panels",
    "services/layout_import_export.py": "builds the Tk glass-catalogue, lens-drawing and stock-lens panels",
    "services/layout_shell_controls.py": "binds Tk entries' commit keys (`bind_entry_commit`)",
    "services/layout_table_workbench.py": "places the Tk table's in-cell entry (`place_commit_cell_entry`)",
    "services/tolerance_modeling.py": "builds the Tk tolerance-report panel",
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


def tk_view_importers() -> dict:
    """module -> the line numbers where it imports a Tk view package at MODULE level (an import
    inside a function is how a service asks a view to do something, and runs only when asked)."""
    found: dict = {}
    for layer in LAYERS:
        if layer == "qt":
            continue
        for path in sorted((ROOT / layer).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            lines = []
            for node in tree.body:
                names = []
                if node.__class__ is ast.Import:
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module or ""] + [f"{node.module}.{alias.name}" for alias in node.names]
                if any(name == package or name.startswith(package + ".") for name in names for package in TK_VIEW_PACKAGES):
                    lines.append(node.lineno)
            if lines:
                found[path.relative_to(ROOT).as_posix()] = lines
    return found


def _layer_module_file(dotted: str) -> str:
    """"services/x.py" for "KrakenOS.UI.services.x" when that is a module of the toolkit-free layers."""
    prefix = "KrakenOS.UI."
    if not dotted.startswith(prefix):
        return ""
    relative = dotted[len(prefix):].replace(".", "/") + ".py"
    return relative if relative.split("/")[0] in LAYERS and (ROOT / relative).is_file() else ""


def guards_reaching_for_tkinter(importers) -> dict:
    """guard file -> where it reaches for a tkinter name through a module of the toolkit-free
    layers that does NOT import tkinter (``importers`` are the ones that do)."""
    found: dict = {}
    for path in sorted(ROOT.glob("validate_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        aliases: dict = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                for alias in node.names:          # from KrakenOS.UI.services import x as fa_mod
                    module_file = _layer_module_file(f"{node.module}.{alias.name}")
                    if module_file:
                        aliases[alias.asname or alias.name] = module_file
            elif node.__class__ is ast.Import:
                for alias in node.names:          # import KrakenOS.UI.services.x as fa_mod
                    module_file = _layer_module_file(alias.name)
                    if module_file and alias.asname:
                        aliases[alias.asname] = module_file
        hits = sorted({f"{node.value.id}.{node.attr} (line {node.lineno}, {aliases[node.value.id]})"
                       for node in ast.walk(tree)
                       if isinstance(node, ast.Attribute) and node.attr in TK_NAMES and isinstance(node.value, ast.Name)
                       and node.value.id in aliases and aliases[node.value.id] not in importers})
        if hits:
            found[path.name] = hits
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
    rows.append(["S", not unlisted and not stale and len(services) == len([n for n in TK_IMPORTERS if n.startswith("services/")]),
                 f"{len(found)} modules of {'/'.join(LAYERS)} import tkinter at run time, {len(services)} of them services "
                 f"(14 before bugs/0970); not in the list: {unlisted or 'none'}; listed but clean now (delete the entry): "
                 f"{stale or 'none'}"])
    indirect = tk_view_importers()
    unlisted_views = sorted(set(indirect) - set(TK_VIEW_IMPORTERS))
    stale_views = sorted(set(TK_VIEW_IMPORTERS) - set(indirect))
    rows.append(["I", not unlisted_views and not stale_views,
                 f"{len(indirect)} modules import a Tk view package (panels, widgets) at module level: "
                 f"{sorted(name.split('/')[-1] for name in indirect)}; not in the list: {unlisted_views or 'none'}; listed "
                 f"but clean now (delete the entry): {stale_views or 'none'}"])

    reaching = guards_reaching_for_tkinter(set(found))
    guards_scanned = len(list(ROOT.glob("validate_*.py")))
    rows.append(["G", not reaching and guards_scanned > 500,
                 f"{guards_scanned} guards scanned; reaching for a tkinter name through a module that does not import "
                 f"it: {reaching or 'none'}"])

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
