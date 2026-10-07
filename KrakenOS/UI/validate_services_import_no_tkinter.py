"""Guard for bugs/0970: the toolkit-free layers import no tkinter -- a list that may only shrink.

Phase 7d of the Qt migration. `services/`, `reports/`, `row_forms/`, `uihost/` and `qt/` are meant to
hold no toolkit code but the Tk host itself. Measured 2026-10-06: 14 of 151 service modules imported
tkinter. Six did not need to -- five never used what they imported, one used it only to annotate a
dialog's parent (which is a Qt widget under the Qt shell) -- and a seventh made two `tk.BooleanVar`s
that no other host can make. The seven left each held a real Tk window or menu; they are listed
here with what they hold, and move out one at a time (bugs/0972 moved the first, bugs/0976 the
second, bugs/0977 the third, bugs/0978 the fourth, bugs/0979 the fifth, bugs/0980 the sixth and
bugs/0981 the last: no service imports tkinter now, only the Tk host).

  I  the other way in: a module reaches tkinter WITHOUT naming it when something it imports at
     module level does. Followed through every `KrakenOS.UI` import (bugs/0981), six modules of
     these layers did -- five since bugs/0982, then one fewer with each of bugs/0983 to 0986, and NONE since
     bugs/0987: the list is empty, and a module that reaches tkinter again fails here. (Until 0981 this
     claim counted imports of `panels/` and `widgets/` -- five -- which missed a service that
     imports the Tk inspector, and counted a `panels/` module that holds no Tk at all.)
  R  the same, asked of the interpreter rather than read from the source: each module of these
     layers is imported in a process of its own, and tkinter is loaded afterwards for exactly
     the modules claim I lists -- so the reading of the source is not what is trusted
  S  the scan: every module of those layers that imports tkinter at run time is in `TK_IMPORTERS`,
     and every entry there still does. A new importer fails here; a cleaned module must be deleted
     from the list -- so it can only shrink. (An import under `if TYPE_CHECKING:` is not a run-time
     import.)
  U  importing is not the only way to USE it: `layout_editor` copies its own globals -- `tk`
     among them -- into some service modules (`_sync_layout_globals`), and code there calls
     `tk.Menu(...)` with no import of its own. Measured with bugs/0981: one module did, sixteen
     times -- the Tk surface table's borders, grid, markers and choice menu. None does since
     bugs/0987, when that drawing code became a panel; the list is empty, so "no service imports
     tkinter" is not read as "no service uses it"
  C  nor is tkinter's own name the only Tk there is: a service that names a Tk view CLASS at run
     time -- a panel class of a module that imports tkinter, or the 3D inspector -- uses Tk as
     surely, however the name reached it (bugs/0982). Counted per module, exactly: the panel
     factories (`_main_*`) are most of it, the legacy viewer's calls on the inspector the rest.
     (53 uses of 48 classes then; 45 of 40 since bugs/0983, when eight panels that only show a
     form stopped loading tkinter; 38 of 32 since bugs/0984, when the report panels did; 37 of
     31 since bugs/0986, when the lens-drawing panel did)
  H  the two helpers the scene tools borrowed from the inspector class are functions of their own
     (bugs/0982): a surface's classic colour -- its own when it has one that is not black, else by
     its glass -- and a surface mesh as a deep copy of its own, None when it has no points; the
     inspector's two methods are still there and give the same. And every helper a service still
     calls on the inspector class through `_inspector_class()` is one the class has
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
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("KrakenOS/UI")
LAYERS = ("services", "reports", "row_forms", "uihost", "qt")
#: module -> the Tk code it still holds. EXACT: a port deletes its entry.
TK_IMPORTERS = {
    "uihost/tk_host.py": "the Tk host itself",
}
#: A module also reaches tkinter WITHOUT naming it, when something it imports at module level does
#: (bugs/0981: followed through every KrakenOS.UI import). module -> the first step of its road
#: there, and what that is for. EXACT: a module that no longer reaches it must be deleted here.
TK_REACHED_THROUGH: dict = {}      # empty since bugs/0987
#: module -> how many times it names tkinter at RUN TIME with no import of its own (the name is
#: put into its globals by `layout_editor`). EXACT: a count that falls must be lowered here.
TK_NAMES_WITHOUT_IMPORT: dict = {}     # empty since bugs/0987
#: module -> how many times it names a Tk view CLASS at run time (a class of a `panels/` module
#: that imports tkinter, or `Kraken3DInspector`), by import or through the editor's copied globals.
#: EXACT: a count that falls must be lowered here.
TK_CLASSES_NAMED = {
    "services/layout_import_export.py": 1,       # the Tk missing-assets dialog
    "services/layout_shell_controls.py": 7,      # seven panel factories
    "services/layout_table_workbench.py": 7,     # seven panel factories
    "services/legacy_3d_scene.py": 4,            # the legacy viewer's calls on the inspector class
    "services/optical_solid_workflow.py": 2,     # one panel factory, one inspector call
    "services/three_d_scene_tools.py": 16,       # opening the 3D view, and the legacy viewer's inspector helpers
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


def _ui_module_file(dotted: str):
    """The file of a `KrakenOS.UI...` module or package; None for anything else."""
    if not dotted.startswith("KrakenOS.UI"):
        return None
    relative = dotted[len("KrakenOS.UI"):].lstrip(".").replace(".", "/")
    for candidate in (ROOT / (relative + ".py"), ROOT / relative / "__init__.py"):
        if relative and candidate.is_file():
            return candidate
    return None


def _module_level_imports(path) -> tuple:
    """(does it import tkinter at module level, the dotted names it imports there). "Module level"
    takes in a top-level try / if / with; an import inside a function runs only when asked."""
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    names, direct, pending = set(), False, list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.Try, ast.If, ast.With)):
            pending.extend(node.body + getattr(node, "orelse", []) + getattr(node, "finalbody", [])
                           + [inner for handler in getattr(node, "handlers", []) for inner in handler.body])
        elif node.__class__ is ast.Import:
            direct = direct or any(alias.name.split(".")[0] == "tkinter" for alias in node.names)
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            direct = direct or (node.module or "").split(".")[0] == "tkinter"
            names.add(node.module or "")
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return direct, names


_ROADS: dict = {}


def road_to_tkinter(path, _seen=()) -> list:
    """The files, in order, by which importing ``path`` loads tkinter at module level: [] when it
    does not, [itself] when it imports tkinter itself."""
    if path in _ROADS:
        return _ROADS[path]
    if path in _seen:
        return []
    direct, names = _module_level_imports(path)
    found: list = [path.relative_to(ROOT).as_posix()] if direct else []
    if not direct:
        for name in sorted(names):
            target = _ui_module_file(name)
            if target is None or target == path:
                continue
            onward = road_to_tkinter(target, _seen + (path,))
            if onward:
                found = [path.relative_to(ROOT).as_posix()] + onward
                break
    _ROADS[path] = found
    return found


def tkinter_reached_through() -> dict:
    """module of the toolkit-free layers -> its road to tkinter (the files after itself), for every
    module that does not import tkinter itself but reaches it at module level."""
    reached: dict = {}
    for layer in LAYERS:
        if layer == "qt":
            continue
        for path in sorted((ROOT / layer).rglob("*.py")):
            steps = road_to_tkinter(path)
            if len(steps) > 1:
                reached[steps[0]] = steps[1:]
    return reached


_PROBE = ("import sys, importlib\n"
          "try:\n"
          "    importlib.import_module(sys.argv[1])\n"
          "    print('LOADED' if 'tkinter' in sys.modules else 'CLEAN')\n"
          "except Exception as exc:\n"
          "    print('ERROR ' + type(exc).__name__ + ': ' + str(exc)[:80])\n")


def tkinter_loaded_on_import() -> dict:
    """module -> "LOADED" / "CLEAN" / "ERROR ...": what importing it, alone in a fresh interpreter,
    does to `sys.modules`. One process per module -- an import cannot be undone in one process."""
    paths = [path for layer in LAYERS if layer != "qt" for path in sorted((ROOT / layer).rglob("*.py"))]

    def probe(path) -> tuple:
        dotted = "KrakenOS.UI." + path.relative_to(ROOT).with_suffix("").as_posix().replace("/", ".")
        dotted = dotted[: -len(".__init__")] if dotted.endswith(".__init__") else dotted
        try:
            done = subprocess.run([sys.executable, "-c", _PROBE, dotted], capture_output=True, text=True, timeout=300,
                                  cwd=str(Path.cwd()))
            answer = (done.stdout.strip().splitlines() or ["ERROR no answer: " + done.stderr.strip()[-80:]])[-1]
        except subprocess.TimeoutExpired:
            answer = "ERROR timed out"
        return path.relative_to(ROOT).as_posix(), answer

    with ThreadPoolExecutor(max_workers=max(1, min(4, (os.cpu_count() or 2) - 1))) as pool:
        return dict(pool.map(probe, paths))


def _annotation_nodes(tree) -> set:
    """ids of the nodes inside annotations (never evaluated under `from __future__ import annotations`)."""
    inside: set = set()
    for node in ast.walk(tree):
        notes = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            arguments = node.args
            notes += [a.annotation for a in arguments.args + arguments.kwonlyargs + arguments.posonlyargs if a.annotation]
            notes += [a.annotation for a in (arguments.vararg, arguments.kwarg) if a is not None and a.annotation]
            if node.returns:
                notes.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            notes.append(node.annotation)
        for note in notes:
            inside.update(id(inner) for inner in ast.walk(note))
    return inside


def tk_names_without_import(importers) -> dict:
    """module -> how many times it names tkinter at run time although it does not import it."""
    found: dict = {}
    for layer in LAYERS:
        if layer == "qt":
            continue
        for path in sorted((ROOT / layer).rglob("*.py")):
            name = path.relative_to(ROOT).as_posix()
            if name in importers:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
            skip = _annotation_nodes(tree) if "from __future__ import annotations" in text else set()
            count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES and id(node) not in skip)
            if count:
                found[name] = count
    return found


def tk_view_classes() -> set:
    """The names of the Tk view classes: every class of a `panels/` module whose import loads
    tkinter (itself, or through the Tk report / form views), and the 3D inspector -- a
    `tk.Toplevel` until phase 7e."""
    names = {"Kraken3DInspector"}
    for path in sorted((ROOT / "panels").glob("*.py")):
        if road_to_tkinter(path):
            names.update(node.name for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.ClassDef))
    return names


def tk_classes_named() -> dict:
    """module -> how many times it names one of those classes at run time (outside an annotation),
    a call of `_inspector_class()` -- the accessor bugs/0982 put in front of the inspector -- included."""
    classes = tk_view_classes()
    found: dict = {}
    for layer in LAYERS:
        if layer == "qt":
            continue
        for path in sorted((ROOT / layer).rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(text)
            skip = _annotation_nodes(tree) if "from __future__ import annotations" in text else set()
            count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in classes and id(node) not in skip)
            count += sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_inspector_class")
            if count:
                found[path.relative_to(ROOT).as_posix()] = count
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


def _helpers_claim() -> list:
    try:
        from types import SimpleNamespace

        import numpy as np
        import pyvista as pv

        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        from KrakenOS.UI.services import open3d_scene_look as look
        from KrakenOS.UI.services.open3d_mesh_basics import mesh_with_transform

        surfaces = {"own": SimpleNamespace(Color=[0.2, 0.4, 0.6], Glass="BK7"),
                    "black, glass": SimpleNamespace(Color=[0, 0, 0], Glass="BK7"),
                    "mirror": SimpleNamespace(Color=[0, 0, 0], Glass="mirror"),
                    "absorber": SimpleNamespace(Color=None, Glass="ABSORB"),
                    "nothing": SimpleNamespace()}
        colors = {name: tuple(look.surface_color(surface)) for name, surface in surfaces.items()}
        expected = {"own": (0.2, 0.4, 0.6), "black, glass": look.CLASSIC_GLASS_COLOR, "mirror": look.CLASSIC_MIRROR_COLOR,
                    "absorber": look.CLASSIC_ABSORB_COLOR, "nothing": look.CLASSIC_GLASS_COLOR}
        same_colors = all(tuple(Kraken3DInspector._surface_color(surface)) == colors[name] for name, surface in surfaces.items())
        sphere = pv.Sphere(radius=2.0)
        copy = mesh_with_transform(sphere, np.eye(4) * 5.0)
        untouched = bool(copy is not sphere and np.allclose(np.asarray(copy.points), np.asarray(sphere.points)))
        copy.points[0] = (99.0, 99.0, 99.0)
        deep = float(np.asarray(sphere.points)[0][0]) != 99.0
        refused = [mesh_with_transform(pv.PolyData(), None), mesh_with_transform(object(), None)]
        wrapper = Kraken3DInspector._mesh_with_transform(sphere, None)
        # the calls that stayed on the inspector class, now through an accessor: each names a real helper
        from KrakenOS.UI.services import three_d_scene_tools

        borrowed: set = set()
        for path in sorted((ROOT / "services").rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Call)
                        and getattr(node.value.func, "id", "") == "_inspector_class"):
                    borrowed.add(node.attr)
        missing = sorted(name for name in borrowed if not callable(getattr(Kraken3DInspector, name, None)))
        accessor = three_d_scene_tools._inspector_class() is Kraken3DInspector
        ok = (colors == expected and same_colors and untouched and deep and refused == [None, None]
              and wrapper is not None and int(wrapper.n_points) == int(sphere.n_points)
              and accessor and len(borrowed) >= 5 and not missing)
        return ["H", ok,
                f"classic colours {dict((name, tuple(round(c, 3) for c in color)) for name, color in colors.items())}; the "
                f"inspector's method gives the same: {same_colors}; a mesh comes back as its own deep copy with the points "
                f"unmoved ({untouched}, {deep}); an empty mesh and a non-mesh give {refused}; the inspector's method still "
                f"returns one of {int(wrapper.n_points) if wrapper is not None else None} points; the accessor returns the "
                f"inspector class ({accessor}) and the {len(borrowed)} helpers called on it {sorted(borrowed)} all exist "
                f"(missing: {missing or 'none'})"]
    except Exception as exc:        # a claim that raises is ITS failure
        return ["H", False, f"raised {type(exc).__name__}: {exc}"]


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
    reached = tkinter_reached_through()
    unlisted_roads = sorted(set(reached) - set(TK_REACHED_THROUGH))
    stale_roads = sorted(set(TK_REACHED_THROUGH) - set(reached))
    moved_roads = sorted(name for name in set(reached) & set(TK_REACHED_THROUGH) if reached[name][0] != TK_REACHED_THROUGH[name][0])
    rows.append(["I", not unlisted_roads and not stale_roads and not moved_roads,
                 f"{len(reached)} modules reach tkinter through what they import at module level: "
                 f"{ {name.split('/')[-1]: steps[0] for name, steps in reached.items()} }; not in the list: "
                 f"{unlisted_roads or 'none'}; listed but clean now (delete the entry): {stale_roads or 'none'}; reached by "
                 f"another road than listed: {moved_roads or 'none'}"])

    probed = tkinter_loaded_on_import()
    loaded = sorted(name for name, answer in probed.items() if answer == "LOADED")
    failed = {name: answer for name, answer in probed.items() if answer not in ("LOADED", "CLEAN")}
    rows.append(["R", loaded == sorted(TK_REACHED_THROUGH) and not failed and len(probed) >= 150,
                 f"{len(probed)} modules each imported in a process of its own: tkinter is loaded for "
                 f"{[name.split('/')[-1] for name in loaded]}; the list has {len(TK_REACHED_THROUGH)}; could not be imported: "
                 f"{failed or 'none'}"])

    injected = tk_names_without_import(set(found))
    rows.append(["U", injected == TK_NAMES_WITHOUT_IMPORT,
                 f"modules that name tkinter at run time with no import of their own: {injected or 'none'} (listed: "
                 f"{TK_NAMES_WITHOUT_IMPORT}; a new module or a higher count is a new use, a lower count must be lowered "
                 f"in the list)"])

    named = tk_classes_named()
    rows.append(["C", named == TK_CLASSES_NAMED,
                 f"modules that name a Tk view class at run time ({len(tk_view_classes())} such classes): {named} "
                 f"-- {sum(named.values())} uses; listed: {sum(TK_CLASSES_NAMED.values())} in {len(TK_CLASSES_NAMED)} modules"])

    rows.append(_helpers_claim())

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
