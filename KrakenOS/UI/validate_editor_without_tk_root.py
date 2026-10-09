"""Guard for bugs/0993: the editor can be built with NO Tk root (docs/design_qt_migration.md phase 7f).

The Qt shell runs a hidden Tk application: one root, 399 widgets at start-up, 148 Tk variables.
It could not do otherwise -- `KrakenLayoutEditor(...)` always made a root and built every Tk
panel, and parts of the MODEL only worked because those panels existed. `tk_root=False` builds the
editor with no root and no panel; this guard measures what such an editor is, against the one
with a root, on one scripted session.

What had to stop depending on a Tk panel for the two to agree (each was found by that
comparison, not by reading):

  * the main window's pane layout was in the toolkit-free shell-controls service, and the model
    asks for a re-layout after every plot refresh -- it is the window builder's now
  * the source summary, the direction preset and the atmosphere summary followed their inputs
    through traces the Tk panels wired while building widgets -- they are the model's reactions
  * the field's label, sample count and status hint were only kept when a Tk menu / entry
    existed, and what a temporary trace printed reached the debug log only when a Tk text box did
  * the field value was declared with its value AFTER start-up, so start-up ran from a
    different beginning and the blank scene's image was 4 mm wide, not 17.5
  * the atmosphere's ten numbers were not declared at all (made and read by name)

  N  no Tk at all: the editor without a root, driven through the session, makes no Tk root, no
     Tk widget and no Tk variable (counted at tkinter's own constructors); its 79 model variables
     are its host's; a Tk call on it raises AttributeError -- it fails loudly instead of reaching
     a window nobody sees; it closes cleanly; without a UI host it is refused
  S  the same model: after every step every plain attribute of the editor -- the rows, the
     table's cells and selection, the 79 variables, the undo and redo stacks, about 290 in all
     -- equals the Tk-rooted editor's, except EXACTLY the known differences listed below
  R  the model's own reactions, with no Tk: the summaries follow their inputs, a typed direction
     names its preset, an observatory preset fills the numbers, the field's label, count and
     hint follow the object mode, a settings round trip restores what it saved, and what a
     trace prints is in the debug log
  T  the Tk window still lays itself out: both sidebars hide and come back with their restore
     strips, the status line and the same sashes; the left panel's canvas tracks its content;
     and its field inputs are still told what the model decided -- the sample count greyed
     while the field is zero and live once it is not, the field types offered in the object
     mode's order
  L  the layering: the eight pane methods are the window builder's and not the service's; the
     two Tk panels wire no variable trace of their own; the model's code names a panel-made Tk
     widget exactly as often as listed below
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter
from pathlib import Path

RESULT_MARK = "ROOTLESS_RESULT "
SKIP_MARK = "ROOTLESS_SKIP "
ROOT = Path("KrakenOS/UI")
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: not model state: the host, the root, the plot's toolkit objects
NOT_COMPARED = {"ui", "root", "_kraken_ttk_style", "figure", "ax", "canvas", "_model_variables_created_at_init"}
HISTORY = ("_undo_stack", "_redo_stack", "_last_saved_state")
BIG = 6000

#: What still differs between an editor without a Tk root and one with -- model state that
#: still lives in a Tk panel. EXACT: a family that stops differing must leave this list, and a
#: new one fails. Two causes are left, each the subject of a next step of phase 7f:
#:   * the optimizer's operand settings are variables the Tk optimization panel creates, and the
#:     selected operands are a Tk list box's selection
#:   * which inputs apply (and the value an inapplicable one is set aside with) is worked out
#:     over the widgets the Tk panels REGISTER, so with no panel nothing is set aside
KNOWN_DIFFERENCES = {
    "the optimizer's operands": {
        "operand_field_vars", "operand_field_x_vars", "operand_field_y_vars", "operand_frequency_vars",
        "operand_mtf_algorithm_vars", "operand_mtf_mode_vars", "operand_surface_vars", "operand_target_vars",
        "operand_wavelength_vars", "operand_weight_vars",
        "_undo_stack: only the operands", "_redo_stack: only the operands", "_last_saved_state: only the operands",
        "_headless_selected_operand_labels: only without a root",
    },
    "which inputs apply": {
        "_left_mode_saved_values", "field_count_var",
    },
}
#: plain attributes only the Tk-rooted editor has: its window's own state, none of it model state
TK_ONLY_PLAIN = {"_selection_anchor_row", "_selection_border_overlays", "analysis_mode_menu", "analysis_mode_vars",
                 "control_stack_window", "projection_display_mode_buttons"}
PANE_METHODS = ("_on_control_stack_configure", "_on_control_canvas_configure", "_on_left_panel_mousewheel", "_pane_present",
                "toggle_left_sidebar", "toggle_right_sidebar", "_set_initial_pane_layout", "_maybe_refresh_initial_pane_layout")
#: editor attribute holding a panel-made Tk widget -> how often the toolkit-free layers name it.
#: EXACT, and it may only shrink (it was 30 attributes, 103 uses, before bugs/0993).
WIDGET_USES = {
    "table": 27, "merit_mode_list": 9, "results_table": 6, "progress_bar": 4, "source_model_label": 1,
    "source_model_menu": 1, "pupil_pattern_menu": 1, "optimization_start_stop_button": 1, "operand_surface_menus": 1,
    "operand_setup_frames": 1, "nonseq_target_surface_menu": 1, "machine_vision_menu": 1, "layout_menu": 1,
    "field_panel": 1, "example_menu": 1, "arm_view_menu": 1, "analysis_surface_menu": 1,
    "analysis_branch_filter_menu": 1, "_insert_component_menu": 1,
}


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


# ---- the session, recorded in a process of its own -------------------------------------------------------
def _canon(value, depth: int = 0):
    """A comparable form of plain data; "<object>" for anything that is the toolkit's or the app's."""
    import numpy as np

    if depth > 7:
        return "<deep>"
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (np.floating, np.integer, np.bool_)):
        return repr(value.item())
    if isinstance(value, Path):
        return "path:" + value.name
    if isinstance(value, np.ndarray):
        return "array:" + hashlib.sha1(np.ascontiguousarray(value).tobytes()).hexdigest()[:12] + str(value.shape)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {"<dataclass>": type(value).__name__,
                **{f.name: _canon(getattr(value, f.name), depth + 1) for f in dataclasses.fields(value)}}
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            plain = _canon(item, depth + 1)
            if plain == "<object>":
                return "<object>"
            out[str(_canon(key, depth + 1))] = plain
        return dict(sorted(out.items()))
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [_canon(item, depth + 1) for item in value]
        if "<object>" in items:
            return "<object>"
        return sorted(items, key=repr) if isinstance(value, (set, frozenset)) else items
    if hasattr(value, "get") and hasattr(value, "set") and hasattr(value, "trace_add"):     # a variable: its value
        try:
            return {"<var>": str(value.get())}
        except Exception as exc:
            return {"<var>": f"RAISED {type(exc).__name__}"}
    return "<object>"


def _digest(plain) -> str:
    return hashlib.sha1(json.dumps(plain, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _without_operands(plain):
    """The history entry with the optimizer's operand settings taken out -- the one known difference."""
    if isinstance(plain, dict):
        return {key: _without_operands(item) for key, item in plain.items() if key not in ("operands", "selected_operands")}
    if isinstance(plain, list):
        return [_without_operands(item) for item in plain]
    return plain


def session(mode: str, out: str) -> dict:
    """Drive one editor -- with a hidden Tk root ("tk") or with none ("none") -- and record it."""
    import tkinter as tk

    made = Counter()
    widget_init, variable_init, root_init = tk.BaseWidget.__init__, tk.Variable.__init__, tk.Tk.__init__

    def counted(kind, real):
        def init(self, *args, **options):
            made[kind] += 1
            return real(self, *args, **options)
        return init

    tk.BaseWidget.__init__ = counted("widgets", widget_init)
    tk.Variable.__init__ = counted("variables", variable_init)
    tk.Tk.__init__ = counted("roots", root_init)

    from KrakenOS.UI import system_controls
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    host = ScriptedUiHost(answers={})
    if mode == "tk":
        editor = KrakenLayoutEditor(headless=True, ui=host)
    else:
        editor = KrakenLayoutEditor(headless=True, ui=host, tk_root=False)
    made_at_start = dict(made)
    steps: list = []
    last: dict = {}

    def state() -> dict:
        plain = {}
        for key, value in list(editor.__dict__.items()):
            if key in NOT_COMPARED or key.endswith("_instance"):
                continue
            item = _canon(value)
            if item == "<object>":
                plain[key] = "<object>"
            elif key in HISTORY:
                plain[key] = {"entries": len(item) if isinstance(item, list) else 1, "all of it": _digest(item),
                              "apart from the operands": _digest(_without_operands(item))}
            elif len(json.dumps(item, default=str)) > BIG:
                plain[key] = {"<digest>": _digest(item)}
            else:
                plain[key] = item
        cells = editor._table_cells()
        plain["<cells>"] = {"<digest>": _digest([[i, list(cells.values(i)), list(cells.tags(i))] for i in cells.items()])}
        plain["<selection>"] = [list(editor._table_selection()), editor._table_focus_item()]
        plain["<plot axes>"] = len(editor.figure.axes)
        return plain

    def record(label: str, result: str) -> None:
        now = state()
        steps.append([label, result, {key: value for key, value in now.items() if last.get(key, "<absent>") != value},
                      sorted(key for key in last if key not in now)])
        last.clear()
        last.update(now)

    def step(label: str, call) -> None:
        try:
            call()
            result = "ok"
        except Exception as exc:
            where = " < ".join(frame.name for frame in traceback.extract_tb(exc.__traceback__)[-1:-5:-1])
            result = f"RAISED {type(exc).__name__}: {str(exc)[:140]} @ {where}"
        host.run_due(200)
        record(label, result)

    def control(name: str, value: str) -> None:
        """Set an input as a shell does: the variable, then the commit the catalogue names."""
        getattr(editor, name).set(value)
        spec = system_controls.control_for(name) or next((c for c in system_controls.ATMOSPHERE_CONTROLS if c.key == name), None)
        commit = getattr(spec, "commit", None) if spec is not None else None
        if commit:
            getattr(editor, commit)()

    def load() -> None:
        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)

    def settings_round_trip() -> None:
        settings = editor._collect_layout_settings()
        editor.atmos_zenith_deg_var.set("12.5")
        editor.field_value_var.set("9")
        editor._apply_layout_settings(settings)

    source_models = system_controls.control_for("source_model_var").choices
    record("constructed", "ok")
    step("load a layout", load)
    step("commit a cell", lambda: editor.commit_cell(3, "thickness", "7.25"))
    step("commit a material", lambda: editor.commit_cell(4, "glass", "F2"))
    step("select rows", lambda: editor._select_table_indices([2, 3], focus_index=2))
    step("duplicate", editor.duplicate_selected)
    step("undo", editor.undo)
    step("redo", editor.redo)
    step("group", editor.group_selected_as_element)
    step("move down", editor.move_down)
    step("delete", editor.delete_selected)
    step("undo the delete", editor.undo)
    views = list(editor.arm_view_options())
    step("path view", lambda: (editor.arm_view_var.set(views[1]), editor.set_arm_view()))
    step("all paths", lambda: (editor.arm_view_var.set(views[0]), editor.set_arm_view()))
    step("object mode finite", lambda: control("object_mode_var", "Finite"))
    step("field value", lambda: control("field_value_var", "2.0"))
    step("field samples", lambda: control("field_count_var", "3"))
    step("object mode infinity", lambda: control("object_mode_var", "Infinity"))
    step("field value zero", lambda: control("field_value_var", "0"))
    step("field type", lambda: control("field_type_var", system_controls.FIELD_TYPE_LABELS[1]))
    step("aperture", lambda: control("aperture_value_var", "6.0"))
    step("source model", lambda: control("source_model_var", source_models[1]))
    step("gaussian waist", lambda: editor.gaussian_waist_radius_var.set("0.8"))
    step("source direction typed", lambda: (editor.source_l_var.set("1"), editor.source_m_var.set("0"),
                                            editor.source_n_var.set("0")))
    step("source model default", lambda: control("source_model_var", source_models[0]))
    observatory = editor._atmos_observatory_names()[1]
    step("observatory", lambda: control("atmos_observatory_var", observatory))
    step("atmosphere zenith", lambda: editor.atmos_zenith_deg_var.set("30"))
    step("atmosphere plot", lambda: control("atmos_plot_mode_var", system_controls.ATMOS_PLOT_MODE_VALUES[-1]))
    step("apply atmosphere", lambda: editor.apply_atmosphere_settings())
    step("settings round trip", settings_round_trip)
    step("refresh the plot", editor.refresh_plot)
    step("add surface", editor.add_surface)
    step("trace mode", lambda: control("trace_mode_var", "Sequential"))
    step("reset", editor.reset_layout)
    step("undo the reset", editor.undo)

    loud = {}
    for name in ("title", "geometry", "winfo_exists", "bind_all", "tk"):
        try:
            getattr(editor, name)
            loud[name] = "answered"
        except AttributeError:
            loud[name] = "AttributeError"
    try:
        KrakenLayoutEditor(headless=True, tk_root=False)
        refused = "built"
    except (TypeError, ValueError) as exc:
        refused = f"{type(exc).__name__}: {exc}"
    host_made = len(editor._model_variables_created_at_init)
    has_root = editor.root is not None
    try:
        editor.destroy()
        closed = "ok"
    except Exception as exc:
        closed = f"RAISED {type(exc).__name__}: {exc}"
    Path(out).write_text(json.dumps({"steps": steps, "observatory": observatory}), encoding="utf-8")
    return {"made_at_start": made_at_start, "made": dict(made), "has_root": has_root, "host_made": host_made,
            "loud": loud, "refused": refused, "closed": closed, "steps": len(steps)}


def _states(path: str) -> tuple[list, str]:
    """[(label, result, every attribute at that step)] rebuilt from the recorded changes."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    now: dict = {}
    out = []
    for label, result, changed, gone in record["steps"]:
        now = {key: value for key, value in now.items() if key not in gone}
        now.update(changed)
        out.append((label, result, dict(now)))
    return out, record["observatory"]


def _leaves(a, b, path: str = ""):
    if type(a) is not type(b):
        yield path
    elif isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                yield f"{path}.{key}"
            else:
                yield from _leaves(a[key], b[key], f"{path}.{key}")
    elif isinstance(a, list):
        if len(a) != len(b):
            yield f"{path}[len]"
        for index, (x, y) in enumerate(zip(a, b)):
            yield from _leaves(x, y, f"{path}[{index}]")
    elif a != b:
        yield path


def compare(tk_path: str, none_path: str) -> dict:
    """Which attributes differ between the two recorded sessions, by family, and where."""
    with_root, _ = _states(tk_path)
    without, observatory = _states(none_path)
    differing: dict = {}
    results = []
    tk_only: set = set()
    compared = 0
    for (label, tk_result, a), (label_b, none_result, b) in zip(with_root, without):
        if label != label_b or tk_result != "ok" or none_result != "ok":
            results.append((label, tk_result, label_b, none_result))
        for key in sorted(set(a) | set(b)):
            x, y = a.get(key, "<absent>"), b.get(key, "<absent>")
            if "<object>" in (x, y):        # a toolkit or app object in at least one: nothing plain to compare
                continue
            if y == "<absent>":
                tk_only.add(key)
                continue
            compared += 1
            if x == "<absent>":
                differing.setdefault(f"{key}: only without a root", set()).add(label)
            elif key in HISTORY:
                if x["apart from the operands"] != y["apart from the operands"] or x["entries"] != y["entries"]:
                    differing.setdefault(key, set()).add(label)
                elif x["all of it"] != y["all of it"]:
                    differing.setdefault(f"{key}: only the operands", set()).add(label)
            elif x != y:
                differing.setdefault(key, set()).add(label)
    return {"differing": {key: sorted(labels) for key, labels in differing.items()}, "results": results,
            "tk_only": sorted(tk_only), "steps": [len(with_root), len(without)],
            "compared_per_step": compared // max(len(without), 1), "without": without, "observatory": observatory}


# ---- the Tk window's own layout ------------------------------------------------------------------------
def tk_window() -> dict:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")

    def settle(seconds: float = 1.0) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle(2.5)

    def panes() -> dict:
        main = editor.main_pane
        count = len(main.panes())
        return {"panes": count, "sashes": [int(main.sashpos(i)) for i in range(max(count - 1, 0))],
                "left": bool(editor._pane_present(editor.left_sidebar_host)),
                "right": bool(editor._pane_present(editor.right_sidebar_host)),
                "left strip": bool(editor.left_restore_frame.winfo_ismapped()),
                "right strip": bool(editor.right_restore_frame.winfo_ismapped()),
                "collapsed": [bool(editor._left_sidebar_collapsed), bool(editor._right_sidebar_collapsed)],
                "status": str(editor.status_var.get()), "width": int(main.winfo_width()),
                "center sash": int(editor.center_panel.sashpos(0))}

    record = {"start": panes()}
    for label, toggle in (("left hidden", editor.toggle_left_sidebar), ("left back", editor.toggle_left_sidebar),
                          ("right hidden", editor.toggle_right_sidebar), ("both hidden", editor.toggle_left_sidebar),
                          ("left again", editor.toggle_left_sidebar), ("both back", editor.toggle_right_sidebar)):
        toggle()
        settle(0.8)
        record[label] = panes()
    canvas = editor.control_canvas
    canvas.itemconfigure(editor.control_stack_window, width=11)
    canvas.configure(scrollregion=(0, 0, 1, 1))
    editor._on_control_canvas_configure()
    editor._on_control_stack_configure()
    record["canvas"] = {"stack width": str(canvas.itemcget(editor.control_stack_window, "width")),
                        "canvas width": str(canvas.winfo_width()),
                        "scrollregion": [int(float(v)) for v in str(canvas.cget("scrollregion")).split()],
                        "content": [int(v) for v in canvas.bbox("all")],
                        "wheel with no event": editor._on_left_panel_mousewheel(None)}

    def holds_widget(value) -> bool:
        if isinstance(value, tk.Misc):
            return True
        if isinstance(value, dict):
            return any(isinstance(item, tk.Misc) for item in value.values())
        if isinstance(value, (list, tuple)):
            return any(isinstance(item, tk.Misc) for item in value)
        return False

    record["widget attributes"] = sorted(name for name, value in editor.__dict__.items() if holds_widget(value))

    from KrakenOS.UI import system_controls

    def field() -> dict:
        return {"samples": str(editor.field_count_var.get()), "entry": str(editor.field_count_entry.cget("state")),
                "label": str(editor.field_count_label.cget("state")), "types": list(editor.field_type_menu["values"])}

    def control(name: str, value: str) -> None:
        getattr(editor, name).set(value)
        getattr(editor, system_controls.control_for(name).commit)()
        settle(0.3)

    record["field blank"] = field()
    control("object_mode_var", "Finite")
    control("field_value_var", "2.0")
    record["field finite"] = field()
    return record


def widget_uses(names) -> dict:
    """How often the toolkit-free layers name each editor attribute that holds a panel-made Tk widget."""
    lines = []
    for layer in ("services", "row_forms", "uihost"):
        for path in sorted((ROOT / layer).rglob("*.py")):
            lines += [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
                      if not line.strip().startswith("#")]
    counts = {}
    for name in names:
        direct = re.compile(rf"\b(?:self|editor|self\.editor|owner)\.{re.escape(name)}\b")
        named = re.compile(rf"""(?:getattr|hasattr)\(\s*(?:self|editor|self\.editor|owner)\s*,\s*["']{re.escape(name)}["']"""
                           rf"""|__dict__\.get\(\s*["']{re.escape(name)}["']"""
                           rf"""|["']{re.escape(name)}["']\s+(?:not\s+)?in\s+(?:self|editor)\.__dict__""")
        count = sum(len(direct.findall(line)) + len(named.findall(line)) for line in lines)
        if count:
            counts[name] = count
    return counts


# ---- the claims ------------------------------------------------------------------------------------------
def _methods(path: Path, cls: str) -> set:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    return {fn.name for fn in node.body if isinstance(fn, ast.FunctionDef)}


def _trace_calls(path: Path) -> int:
    return sum(1 for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
               if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "trace_add")


def layering_checks(widget_names) -> list:
    def claim_l():
        service = _methods(ROOT / "services/layout_shell_controls.py", "LayoutShellControlsMixin")
        builder = _methods(ROOT / "panels/main_window.py", "MainWindowBuilder")
        in_service = sorted(set(PANE_METHODS) & service)
        missing = sorted(set(PANE_METHODS) - builder)
        traces = {name: _trace_calls(ROOT / "panels" / name) for name in ("main_source_controls.py", "main_atmosphere_panel.py")}
        installs = {name: text.count(f"self.{call}()") for name, call, text in (
            ("main_source_controls.py", "_install_source_summary_reactions",
             (ROOT / "panels/main_source_controls.py").read_text(encoding="utf-8")),
            ("main_atmosphere_panel.py", "_install_atmosphere_summary_reactions",
             (ROOT / "panels/main_atmosphere_panel.py").read_text(encoding="utf-8")))}
        uses = widget_uses(widget_names)
        return (not in_service and not missing and traces == {"main_source_controls.py": 0, "main_atmosphere_panel.py": 0}
                and installs == {"main_source_controls.py": 1, "main_atmosphere_panel.py": 1} and uses == WIDGET_USES
                and len(widget_names) >= 40,
                f"the pane layout is the window builder's (still in the service: {in_service or 'none'}; missing from the "
                f"builder: {missing or 'none'}); variable traces the two panels wire themselves: {traces}, each asks the "
                f"model once: {installs}; of {len(widget_names)} editor attributes holding a Tk widget the toolkit-free layers "
                f"name {len(uses)}, {sum(uses.values())} times"
                + ("" if uses == WIDGET_USES else f" -- NOT the listed ones: now {uses}"))

    return _claims((("L", claim_l),))


def session_checks(tk_meta: dict, none_meta: dict, result: dict) -> list:
    without = {label: state for label, _result, state in result["without"]}

    def value(label: str, name: str) -> str:
        return str(without[label][name]["<var>"])

    def claim_n():
        loud = none_meta["loud"]
        return (none_meta["made"] == {} and none_meta["made_at_start"] == {} and none_meta["has_root"] is False
                and none_meta["host_made"] == 79 and set(loud.values()) == {"AttributeError"} and len(loud) == 5
                and none_meta["refused"].startswith("ValueError") and none_meta["closed"] == "ok"
                and tk_meta["made_at_start"].get("roots") == 1 and tk_meta["made_at_start"].get("widgets", 0) > 300
                and tk_meta["host_made"] == 0 and tk_meta["closed"] == "ok" and none_meta["steps"] == tk_meta["steps"] >= 35,
                f"through {none_meta['steps']} steps the editor without a root made Tk objects {none_meta['made'] or 'none'} "
                f"(the one with a root: {tk_meta['made']}); its host made {none_meta['host_made']} model variables (the "
                f"Tk panels made all of theirs: {tk_meta['host_made']} by the host); Tk calls on it: {loud}; it closes "
                f"{none_meta['closed']}; without a UI host: {none_meta['refused']}")

    def claim_s():
        found = set(result["differing"])
        known = set().union(*KNOWN_DIFFERENCES.values())
        new, fixed = sorted(found - known), sorted(known - found)
        return (not new and not fixed and not result["results"] and result["steps"][0] == result["steps"][1] >= 35
                and set(result["tk_only"]) == TK_ONLY_PLAIN and result["compared_per_step"] >= 250,
                f"{result['steps'][1]} steps, every one without an error in both ({result['results'] or 'none raised'}); "
                f"about {result['compared_per_step']} plain attributes compared at each; they differ in {len(found)} -- "
                + "; ".join(f"{cause}: {len(names & found)} of {len(names)}" for cause, names in KNOWN_DIFFERENCES.items())
                + f" -- and in nothing else (new: {new or 'none'}; listed but no longer differing: {fixed or 'none'}); plain "
                f"attributes only the Tk window has: {result['tk_only']}")

    def claim_r():
        observatory = result["observatory"]
        facts = {
            "the blank scene's source": value("constructed", "source_summary_var").startswith("Pupil / field source"),
            "field samples while the field is zero": value("constructed", "field_count_var") == "NA",
            "the loaded scene's source": value("load a layout", "source_summary_var").startswith("Collimated disk source"),
            "field samples once a scene has a field": value("load a layout", "field_count_var") == "1",
            "a trace's print reached the debug log": without["load a layout"]["debug_lines"] not in ([], "<absent>"),
            "the note follows the object mode": value("object mode finite", "field_mode_note_var").startswith(
                "Preferred: Object semi-height") and value("object mode infinity", "field_mode_note_var").startswith(
                "Preferred: Field half-angle"),
            "the hint follows the object mode": value("object mode finite", "status_hint_var").startswith(
                "Preferred: Object semi-height"),
            "field samples typed": value("field samples", "field_count_var") == "3",
            "the field's label follows its type": value("field type", "field_value_label_var") == "Object Semi-Height [mm]",
            "the summary follows the source model": value("source model", "source_summary_var").startswith("Gaussian beam"),
            "the summary follows a source value": "w0 0.8 mm" in value("gaussian waist", "source_summary_var")
            and "w0 0.8 mm" not in value("source model", "source_summary_var"),
            "a typed direction names its preset": value("source direction typed", "source_direction_preset_var")
            == "+X out of YZ plane" != value("gaussian waist", "source_direction_preset_var"),
            "the observatory fills the numbers": value("observatory", "atmos_altitude_m_var") != "2800"
            == value("source model default", "atmos_altitude_m_var")
            and value("observatory", "atmosphere_summary_var").startswith(observatory + ":"),
            "the atmosphere summary follows a number": "Z=30 deg" in value("atmosphere zenith", "atmosphere_summary_var")
            and "Z=45 deg" in value("observatory", "atmosphere_summary_var"),
            "the atmosphere summary follows the plot": value("atmosphere plot", "atmosphere_summary_var")
            != value("atmosphere zenith", "atmosphere_summary_var"),
            "settings restore what they saved": value("settings round trip", "atmos_zenith_deg_var") == "30"
            and value("settings round trip", "field_value_var") == value("apply atmosphere", "field_value_var"),
        }
        wrong = sorted(name for name, held in facts.items() if not held)
        return (not wrong, f"with no Tk, {len(facts) - len(wrong)} of {len(facts)} reactions of the model hold "
                           f"({', '.join(facts)}); not holding: {wrong or 'none'}")

    return _claims((("N", claim_n), ("S", claim_s), ("R", claim_r)))


def window_checks(record: dict) -> list:
    def claim_t():
        start = record["start"]
        s0, s1 = start["sashes"]
        both = {"left": True, "right": True, "left strip": False, "right strip": False}

        def is_(label: str, panes: int, **facts) -> bool:
            return record[label]["panes"] == panes and all(record[label][key] == want for key, want in facts.items())

        steps = {
            "start": start["panes"] == 3 and 0 < s0 < s1 < start["width"] and start["center sash"] > 0
            and all(start[key] == want for key, want in both.items()),
            "left hidden": is_("left hidden", 2, left=False, right=True, status="Left controls hidden.", collapsed=[True, False],
                               **{"left strip": True, "right strip": False}),
            "left back": is_("left back", 3, status="Left controls shown.", sashes=start["sashes"], **both),
            "right hidden": is_("right hidden", 2, left=True, right=False, status="Right panels hidden.",
                                **{"left strip": False, "right strip": True}),
            "both hidden": is_("both hidden", 1, left=False, right=False, collapsed=[True, True],
                               **{"left strip": True, "right strip": True}),
            "both back": is_("both back", 3, status="Right panels shown.", sashes=start["sashes"], collapsed=[False, False],
                             **both),
        }
        canvas = record["canvas"]
        canvas_ok = (canvas["stack width"] == canvas["canvas width"] != "11" and canvas["scrollregion"] == canvas["content"]
                     and canvas["content"][3] > 100 and canvas["wheel with no event"] is None)
        wrong = sorted(name for name, held in steps.items() if not held)
        blank, finite = record["field blank"], record["field finite"]
        field_ok = ((blank["samples"], blank["entry"], blank["label"]) == ("NA", "disabled", "disabled")
                    and (finite["samples"], finite["entry"], finite["label"]) == ("1", "normal", "normal")
                    and blank["types"][0] == "Field Half-Angle" and finite["types"][0] == "Object Semi-Height"
                    and sorted(blank["types"]) == sorted(finite["types"]) and len(blank["types"]) == 4)
        return (not wrong and canvas_ok and field_ok,
                f"the Tk window: three panes with sashes at {start['sashes']} of {start['width']} px; each sidebar hides and "
                f"comes back with its restore strip, the status line and the same sashes (wrong: {wrong or 'none'}); the left "
                f"panel's canvas tracks its content: {canvas}; the field inputs, blank scene: "
                f"{[blank['samples'], blank['entry'], blank['types'][0]]}, finite object with a field: "
                f"{[finite['samples'], finite['entry'], finite['types'][0]]}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str, needs_display: bool) -> dict | list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs_display else "")
        + "from KrakenOS.UI.validate_editor_without_tk_root import session, tk_window\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows: list = []
    with tempfile.TemporaryDirectory() as folder:
        tk_path, none_path = str(Path(folder) / "tk.json"), str(Path(folder) / "none.json")
        tk_meta = _run(f"session('tk', {tk_path!r})", "S", True)
        none_meta = _run(f"session('none', {none_path!r})", "N", False)
        if isinstance(tk_meta, list) or isinstance(none_meta, list):
            rows += (tk_meta if isinstance(tk_meta, list) else []) + (none_meta if isinstance(none_meta, list) else [])
        else:
            try:
                rows += session_checks(tk_meta, none_meta, compare(tk_path, none_path))
            except Exception as exc:
                rows.append(["S", False, f"comparing the two sessions raised {type(exc).__name__}: {exc}"])
    window = _run("tk_window()", "T", True)
    if isinstance(window, list):
        rows += window
    else:
        rows += window_checks(window) + layering_checks(window["widget attributes"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
