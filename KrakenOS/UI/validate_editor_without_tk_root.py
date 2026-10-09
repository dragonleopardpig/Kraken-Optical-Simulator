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
  * (bugs/0994) which inputs apply was worked out over the WIDGETS the Tk panels register: with
    no panel nothing was set aside and the sample count was not re-examined. The model goes over
    its own catalogue now -- the same 45 inputs -- and the Tk widgets follow
  * (bugs/0995) the optimizer's operand settings were variables the Tk optimization panel made
    with its cards -- five for every operand and five more for the MTF one, most of them never
    shown -- and the first operand was in use because a Tk list box selected it. The model
    makes every setting an operand holds and starts with the first operand
  * (bugs/0997) widening it to the optimizer found one more that is not about Tk: Stop pressed
    in the first seconds after Start did not stop the worker process -- it was only ever
    signalled as a process group, which it becomes seconds after it starts -- and it crashed on
    its own later
  * (bugs/0996) widening the session to a saved file found something that is not about Tk: the
    same scene saved by two processes gave two different files -- the operands were written in
    the order of a Python set, which is the process's. The two sessions here run under different
    hash seeds on purpose

  N  no Tk at all: the editor without a root, driven through the session, makes no Tk root, no
     Tk widget and no Tk variable (counted at tkinter's own constructors); its 79 model variables
     are its host's; a Tk call on it raises AttributeError -- it fails loudly instead of reaching
     a window nobody sees; whether it still exists it answers itself, true until it is destroyed
     (bugs/0999); it closes cleanly; without a UI host it is refused
  S  the same model: after every step every plain attribute of the editor -- the rows, the
     table's cells and selection, the 79 variables, the operands' settings, the undo and redo
     stacks, about 300 in all -- equals the Tk-rooted editor's: the list of known differences
     below is empty, and stays exact
  R  the model's own reactions, with no Tk: the summaries follow their inputs, a typed direction
     names its preset, an observatory preset fills the numbers, the field's label, count and
     hint follow the object mode, a settings round trip restores what it saved, what a trace
     prints is in the debug log; an input that stops applying is set aside, the sample count
     is "NA" again once nothing samples the field, and an input found saying "NA" gets the
     value set aside for it, or else the one it was created with; every operand holds its
     settings from the start, the first one is in use, and a choice of operands and a setting
     survive a settings round trip; the analyses chosen are the model's, and an input that
     belongs to an analysis applies exactly while that analysis is chosen; on a plain lens a
     cell becomes an optimization variable, a tolerance Monte Carlo runs over it, and an
     optimization starts and stops
  F  the file: the two editors, in two processes with different hash seeds, save the same
     scene as the same file byte for byte, at "Save As" and again at "Save" after an edit; the
     operands are in it in the operand list's order; and opening it brings back what was saved,
     not the edit made after
  T  the Tk window still lays itself out: both sidebars hide and come back with their restore
     strips, the status line and the same sashes; the left panel's canvas tracks its content;
     and its field inputs are still told what the model decided -- the sample count greyed
     while the field is zero and live once it is not, the field types offered in the object
     mode's order; and every registered input's widget is disabled and taken out of the panel
     exactly when the catalogue says the input does not apply, for two source models, with the
     source row's span and the field panel following the source model; and the settings the Tk
     optimization cards make, with their start values, are exactly the ones the model declares
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
#: a plain sequential lens, for what needs a merit that means something: tolerances, the optimizer
LENS = Path("KrakenOS/common_optical_layouts/double_gauss_lens.py")
#: not model state: the host, the root, the plot's toolkit objects
NOT_COMPARED = {"ui", "root", "_kraken_ttk_style", "figure", "ax", "canvas", "_model_variables_created_at_init"}
HISTORY = ("_undo_stack", "_redo_stack", "_last_saved_state")
BIG = 6000

#: What still differs between an editor without a Tk root and one with -- model state that
#: still lives in a Tk panel, by cause. EXACT: an attribute that stops differing must leave this
#: list, and a new one fails. It is EMPTY on this session since bugs/0995 (0993 began with 16:
#: the optimizer's operands, 14, and which inputs apply, 2); a wider session that finds more
#: lists them here until they are fixed.
KNOWN_DIFFERENCES: dict = {}
#: plain attributes only the editor WITHOUT a root has: where the model keeps what a Tk widget
#: holds when there is one -- the operands in use, which are a list box's selection under Tk
ROOTLESS_ONLY_PLAIN = {"_headless_selected_operand_labels"}
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
    from KrakenOS.UI.layout_editor import OPERAND_REGISTRY, KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    operands = [spec.label for spec in OPERAND_REGISTRY.values()]
    host = ScriptedUiHost(answers={})
    # ONE path for both sessions, which run one after the other: the path is in the file, in the
    # status line and in every undo state taken after the save
    saved_file = Path(out).with_name("saved_scene.py")
    saved_file.unlink(missing_ok=True)
    host._answers["asksaveasfilename"] = str(saved_file)
    host._answers["askopenfilename"] = str(saved_file)
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
        plain["<operands in use>"] = list(editor._selected_operand_labels())
        plain["<inputs that apply>"] = sorted(item.key for _group, items in system_controls.CONTROL_GROUPS
                                              for item in items if item.is_relevant(editor))
        plain["<thicknesses>"] = [repr(float(row.thickness)) for row in editor.rows]
        plain["<optimization variables>"] = [variable.normalized_name() for variable in editor._build_optimization_variables()]
        monte_carlo = editor.__dict__.get("_last_tolerance_monte_carlo_summary")
        plain["<tolerance run>"] = (None if not monte_carlo else [
            monte_carlo.get("sample_count"), monte_carlo.get("valid_count"), repr(monte_carlo.get("worst_total_merit"))])
        plain["<results>"] = {"<digest>": _digest(list(getattr(editor, "results_items", []) or []))}
        plain["<saved file>"] = ({"<digest>": hashlib.sha1(saved_file.read_bytes()).hexdigest()[:16],
                                  "bytes": saved_file.stat().st_size} if saved_file.exists() else None)
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

    def analyses(*wanted: str) -> None:
        """Choose exactly these analyses, by the toggle a shell's picker calls."""
        for chosen in list(editor.selected_analysis_modes):
            editor.toggle_analysis_mode(chosen)
        for chosen in wanted:
            editor.toggle_analysis_mode(chosen)

    def load_lens() -> None:
        editor.reset_layout()
        editor.layout_files[LENS.stem] = LENS
        editor.load_layout_by_name(LENS.stem, refresh=False)

    worker_after_stop: dict = {}

    def start_and_stop() -> None:
        """Start an optimization and stop it at once; note what became of its worker process."""
        editor.start_optimization()
        worker = editor._optimization_process
        shut_down = editor._shutdown_optimization_worker

        def watched(*args, **kwargs):
            result = shut_down(*args, **kwargs)
            try:        # looked at HERE, before the plot refresh Stop goes on to do gives it time to die by itself
                worker_after_stop["state"] = "ALIVE" if worker.is_alive() else f"dead, exit code {worker.exitcode}"
            except ValueError:          # the process object is closed: the editor found it dead and reaped it
                worker_after_stop["state"] = "stopped and reaped"
            return result

        editor._shutdown_optimization_worker = watched
        try:
            editor.stop_optimization()
        finally:
            del editor._shutdown_optimization_worker

    def settings_round_trip() -> None:
        settings = editor._collect_layout_settings()
        editor.atmos_zenith_deg_var.set("12.5")
        editor.field_value_var.set("9")
        editor.operand_target_vars[operands[2]].set("77")
        editor._set_selected_operand_labels([operands[3]])
        editor._apply_layout_settings(settings)

    source_models = system_controls.control_for("source_model_var").choices
    record("constructed", "ok")
    # on the blank scene the field inputs apply (the layout loaded next has a light source of its own)
    step("blank: a field", lambda: control("field_value_var", "3.0"))
    step("blank: field samples", lambda: control("field_count_var", "5"))
    step("blank: no field", lambda: control("field_value_var", "0"))
    step("blank: an input says NA, nothing set aside", lambda: (editor.wavelength_var.set("NA"),
                                                                editor._sync_left_mode_controls()))
    step("blank: an input says NA, a value set aside", lambda: (
        editor._left_mode_saved_values.__setitem__("wavelength_var", "0.633"), editor.wavelength_var.set("NA"),
        editor._sync_left_mode_controls()))
    step("blank: the wavelength back", lambda: control("wavelength_var", "0.55"))
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
    step("two operands", lambda: editor._set_selected_operand_labels([operands[0], operands[2]]))
    step("an operand's target", lambda: editor.operand_target_vars[operands[2]].set("120"))
    step("settings round trip", settings_round_trip)
    step("refresh the plot", editor.refresh_plot)
    step("add surface", editor.add_surface)
    step("trace mode non-sequential", lambda: control("trace_mode_var", system_controls.TRACE_MODES[1]))
    step("hit limit", lambda: control("nonseq_ns_limit_var", "150"))
    step("trace mode", lambda: control("trace_mode_var", "Sequential"))
    step("reset", editor.reset_layout)
    step("undo the reset", editor.undo)
    # analyses: which are chosen is the model's (bugs/0899); some inputs apply only with one of them
    step("analyses: none", lambda: analyses())
    step("analyses: tolerance compare", lambda: analyses("tolerance_compare"))
    step("the tolerance view", lambda: control("tolerance_compare_view_var", system_controls.control_for(
        "tolerance_compare_view_var").choices[-1]))
    step("analyses: detector map", lambda: analyses("detector_map"))
    step("detector bins", lambda: control("detector_bins_var", "64"))
    step("analyses: spot and wavefront", lambda: analyses("spot", "wavefront"))
    # a file: what is written, and what comes back
    step("save as", editor.save_layout_as)
    step("edit after saving", lambda: editor.commit_cell(3, "thickness", "6.5"))
    step("save", editor.save_layout)
    step("another edit", lambda: editor.commit_cell(3, "thickness", "9.75"))
    step("open the saved file", editor.open_layout)
    # tolerances and the optimizer, on a plain lens whose focal length a thickness changes
    step("a plain lens", load_lens)
    step("a variable", lambda: editor.toggle_optimization_cell(3, "thickness"))
    step("the lens's operand", lambda: editor._set_selected_operand_labels([operands[2]]))
    step("a tolerance Monte Carlo", lambda: editor.run_tolerance_monte_carlo(sample_count=3, seed=7))
    step("one worker", lambda: editor.optimization_workers_var.set("1"))
    # started and stopped at once: the whole run takes a minute and a half (it is compared once,
    # outside the gate: bugs/0997); stopped before its first generation it leaves the lens as it was
    step("an optimization started and stopped", start_and_stop)
    step("the variable unmarked", lambda: editor.toggle_optimization_cell(3, "thickness"))

    loud = {}
    for name in ("title", "geometry", "winfo_children", "bind_all", "tk"):
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
    exists_before = bool(editor.winfo_exists())         # its own answer when it has no root (bugs/0999)
    from KrakenOS.UI.layout_editor import _load_python_data

    in_the_file = list(_load_python_data(saved_file)["settings"]["operands"]) if saved_file.exists() else []
    try:
        editor.destroy()
        closed = "ok"
    except Exception as exc:
        closed = f"RAISED {type(exc).__name__}: {exc}"
    try:
        exists_after = bool(editor.winfo_exists())
    except Exception as exc:        # a destroyed Tk application cannot be asked
        exists_after = f"cannot be asked ({type(exc).__name__})"
    Path(out).write_text(json.dumps({"steps": steps, "observatory": observatory, "operands": operands}), encoding="utf-8")
    return {"made_at_start": made_at_start, "made": dict(made), "has_root": has_root, "host_made": host_made,
            "loud": loud, "refused": refused, "closed": closed, "steps": len(steps),
            "hash seed": os.environ.get("PYTHONHASHSEED", ""), "operands in the file": in_the_file,
            "worker after Stop": worker_after_stop.get("state", "no optimization was started"),
            "exists": [exists_before, exists_after]}


def _states(path: str) -> tuple[list, dict]:
    """[(label, result, every attribute at that step)] rebuilt from the recorded changes, and the rest."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    now: dict = {}
    out = []
    for label, result, changed, gone in record["steps"]:
        now = {key: value for key, value in now.items() if key not in gone}
        now.update(changed)
        out.append((label, result, dict(now)))
    return out, {key: value for key, value in record.items() if key != "steps"}


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
    without, facts = _states(none_path)
    differing: dict = {}
    results = []
    tk_only: set = set()
    rootless_only: set = set()
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
            if x == "<absent>":
                rootless_only.add(key)
                continue
            compared += 1
            if key in HISTORY:
                if x["apart from the operands"] != y["apart from the operands"] or x["entries"] != y["entries"]:
                    differing.setdefault(key, set()).add(label)
                elif x["all of it"] != y["all of it"]:
                    differing.setdefault(f"{key}: only the operands", set()).add(label)
            elif x != y:
                differing.setdefault(key, set()).add(label)
    return {"differing": {key: sorted(labels) for key, labels in differing.items()}, "results": results,
            "tk_only": sorted(tk_only), "rootless_only": sorted(rootless_only), "steps": [len(with_root), len(without)],
            "compared_per_step": compared // max(len(without), 1), "without": without, "with_root": with_root,
            "observatory": facts["observatory"], "operands": facts["operands"]}


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

    def operand_settings() -> dict:
        """What the Tk cards made, beside what the model declares an operand holds."""
        from KrakenOS.UI.layout_editor import OPERAND_REGISTRY
        from KrakenOS.UI.optimization_controls import FIELD_XY_CONTROLS, OPERAND_CONTROLS, default_for, variables_for

        tables = sorted({control.variables for control in OPERAND_CONTROLS + FIELD_XY_CONTROLS})
        made = {table: sorted(getattr(editor, table)) for table in tables}
        declared = {table: [] for table in tables}
        wrong = []
        for spec in OPERAND_REGISTRY.values():
            for control in variables_for(spec):
                declared[control.variables].append(spec.label)
                variable = getattr(editor, control.variables).get(spec.label)
                if variable is None or str(variable.get()) != default_for(control, spec, editor):
                    wrong.append((spec.label, control.name, None if variable is None else str(variable.get())))
        return {"made": made, "declared": {table: sorted(labels) for table, labels in declared.items()}, "wrong": wrong,
                "settings": sum(len(labels) for labels in made.values()),
                "in use": list(editor._selected_operand_labels()),
                "first": [spec.label for spec in OPERAND_REGISTRY.values()][:1]}

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

    record = {"start": panes(), "operands": operand_settings()}
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

    def panel() -> dict:
        """Each registered input: does the catalogue say it applies, and what does its widget show?"""
        wrong, apply = [], 0
        for registered in editor._left_mode_controls:
            name = str(registered["var_name"])
            if not name or name == "field_count_var":       # layout-only widgets; the sample count has its own claim
                continue
            applies = bool(system_controls.control_for(name).is_relevant(editor))
            widget = registered["widget"]
            shown = (str(widget.cget("state")) != "disabled", bool(widget.winfo_ismapped()))
            apply += applies
            if shown != (applies, applies):
                wrong.append((name, applies, shown))
        aside = sorted(editor._left_mode_saved_values)
        return {"inputs": sum(1 for registered in editor._left_mode_controls if registered["var_name"]), "apply": apply,
                "wrong": wrong, "set aside": aside, "source model": str(editor.source_model_var.get()),
                "source row spans": [str(editor.source_model_label.grid_info().get("columnspan")),
                                     str(editor.source_model_menu.grid_info().get("columnspan"))],
                "field panel shown": bool(editor.field_panel.winfo_ismapped())}

    record["field blank"] = field()
    record["panel default"] = panel()
    control("source_model_var", system_controls.control_for("source_model_var").choices[1])
    record["panel gaussian"] = panel()
    control("source_model_var", system_controls.control_for("source_model_var").choices[0])
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
    operands = list(result["operands"])

    def value(label: str, name: str) -> str:
        return str(without[label][name]["<var>"])

    def set_aside(label: str) -> dict:
        return dict(without[label]["_left_mode_saved_values"])

    def held(label: str, table: str) -> dict:
        return {name: str(item["<var>"]) for name, item in without[label][table].items()}

    def claim_n():
        loud = none_meta["loud"]
        return (none_meta["made"] == {} and none_meta["made_at_start"] == {} and none_meta["has_root"] is False
                and none_meta["host_made"] == 79 and set(loud.values()) == {"AttributeError"} and len(loud) == 5
                and none_meta["exists"] == [True, False] and tk_meta["exists"][0] is True
                and none_meta["refused"].startswith("ValueError") and none_meta["closed"] == "ok"
                and tk_meta["made_at_start"].get("roots") == 1 and tk_meta["made_at_start"].get("widgets", 0) > 300
                and tk_meta["host_made"] == 0 and tk_meta["closed"] == "ok" and none_meta["steps"] == tk_meta["steps"] >= 35,
                f"through {none_meta['steps']} steps the editor without a root made Tk objects {none_meta['made'] or 'none'} "
                f"(the one with a root: {tk_meta['made']}); its host made {none_meta['host_made']} model variables (the "
                f"Tk panels made all of theirs: {tk_meta['host_made']} by the host); Tk calls on it: {loud}; it says it "
                f"exists until it is destroyed ({none_meta['exists']}); it closes {none_meta['closed']}; without a UI host: "
                f"{none_meta['refused']}")

    def claim_s():
        found = set(result["differing"])
        known = set().union(*KNOWN_DIFFERENCES.values())
        new, fixed = sorted(found - known), sorted(known - found)
        return (not new and not fixed and not result["results"] and result["steps"][0] == result["steps"][1] >= 35
                and set(result["tk_only"]) == TK_ONLY_PLAIN and set(result["rootless_only"]) == ROOTLESS_ONLY_PLAIN
                and result["compared_per_step"] >= 250,
                f"{result['steps'][1]} steps, every one without an error in both ({result['results'] or 'none raised'}); "
                f"about {result['compared_per_step']} plain attributes compared at each; they differ in {len(found)}"
                + "".join(f"; {cause}: {len(names & found)} of {len(names)}" for cause, names in KNOWN_DIFFERENCES.items())
                + f" (new: {new or 'none'}; listed but no longer differing: {fixed or 'none'}); plain attributes only the Tk "
                f"window has: {result['tk_only']}; only the editor without a root: {result['rootless_only']}")

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
            "field samples follow the field": [value(label, "field_count_var") for label in (
                "constructed", "blank: a field", "blank: field samples", "blank: no field")] == ["NA", "1", "5", "NA"]
            and set_aside("blank: no field").get("field_count_var") == "5",
            "an input found saying NA gets its start value":
                value("blank: an input says NA, nothing set aside", "wavelength_var") == "0.55"
                and "wavelength_var" not in set_aside("blank: no field"),
            "or the value set aside for it": value("blank: an input says NA, a value set aside", "wavelength_var") == "0.633"
            and "wavelength_var" not in set_aside("blank: an input says NA, a value set aside"),
            "an input that stops applying is set aside": "field_type_var" not in set_aside("blank: no field")
            and set_aside("load a layout").get("field_type_var") == "Field Half-Angle"
            and set_aside("load a layout").get("object_mode_var") == "Infinity",
            "set aside from the start": set_aside("constructed").get("gaussian_m2_var") == "1.0"
            and set_aside("constructed").get("source_seed_var") == "1" == set_aside("load a layout").get("source_seed_var")
            and value("load a layout", "source_seed_var") != "1",
            "every operand holds its settings from the start": {
                table: len(held("constructed", table)) for table in (
                    "operand_weight_vars", "operand_target_vars", "operand_wavelength_vars", "operand_field_vars",
                    "operand_surface_vars", "operand_field_x_vars", "operand_field_y_vars", "operand_frequency_vars",
                    "operand_mtf_mode_vars", "operand_mtf_algorithm_vars")} == {
                "operand_weight_vars": len(operands), "operand_target_vars": len(operands),
                "operand_wavelength_vars": len(operands), "operand_field_vars": len(operands),
                "operand_surface_vars": len(operands), "operand_field_x_vars": 1, "operand_field_y_vars": 1,
                "operand_frequency_vars": 1, "operand_mtf_mode_vars": 1, "operand_mtf_algorithm_vars": 1}
            and len(operands) == 8 and set(held("constructed", "operand_wavelength_vars").values()) == {"0.55"},
            "the first operand is in use from the start": without["constructed"]["<operands in use>"] == operands[:1],
            "a choice of operands and a setting are kept": without["two operands"]["<operands in use>"]
            == [operands[0], operands[2]] and held("an operand's target", "operand_target_vars")[operands[2]] == "120"
            != held("two operands", "operand_target_vars")[operands[2]],
            "settings restore the operands": without["settings round trip"]["<operands in use>"] == [operands[0], operands[2]]
            and held("settings round trip", "operand_target_vars")[operands[2]] == "120",
            "the analyses chosen are the model's": [without[label]["selected_analysis_modes"] for label in (
                "analyses: none", "analyses: tolerance compare", "analyses: detector map", "analyses: spot and wavefront")]
            == [[], ["tolerance_compare"], ["detector_map"], ["spot", "wavefront"]],
            "an input applies while its analysis is chosen": [
                ("tolerance_compare_view_var" in without[label]["<inputs that apply>"],
                 "detector_bins_var" in without[label]["<inputs that apply>"]) for label in (
                    "analyses: none", "analyses: tolerance compare", "analyses: detector map", "analyses: spot and wavefront")]
            == [(False, False), (True, False), (False, True), (False, False)],
            "a cell is an optimization variable": [without[label]["<optimization variables>"] for label in (
                "a plain lens", "a variable", "the variable unmarked")] == [[], ["Front Flint Front Thickness"], []],
            "a tolerance Monte Carlo runs": without["the lens's operand"]["<tolerance run>"] is None
            and (without["a tolerance Monte Carlo"]["<tolerance run>"] or [0, 0, "0"])[:2] == [3, 4]
            and float((without["a tolerance Monte Carlo"]["<tolerance run>"] or [0, 0, "0"])[2]) > 1.0,
            "an optimization starts and stops": value("an optimization started and stopped", "status_var").startswith(
                "Optimization stopped") and without["an optimization started and stopped"]["optimization_running"] is False
            and without["an optimization started and stopped"]["<thicknesses>"] == without["one worker"]["<thicknesses>"]
            and value("one worker", "optimization_workers_var") == "1",
            "Stop right after Start leaves no worker process (bugs/0997)":
                (tk_meta["worker after Stop"], none_meta["worker after Stop"]) == ("stopped and reaped",) * 2,
            "the sample count is NA once nothing samples the field": value("source model default", "field_count_var") == "NA"
            and set_aside("source model default").get("field_count_var") == "3"
            and value("source direction typed", "field_count_var") == "3",
        }
        wrong = sorted(name for name, held in facts.items() if not held)
        return (not wrong, f"with no Tk, {len(facts) - len(wrong)} of {len(facts)} reactions of the model hold "
                           f"({', '.join(facts)}); not holding: {wrong or 'none'}")

    def claim_f():
        with_root = {label: state for label, _result, state in result["with_root"]}
        files = {label: (with_root[label]["<saved file>"], without[label]["<saved file>"])
                 for label in ("another edit", "save as", "save")}
        before = (with_root["analyses: spot and wavefront"]["<saved file>"], without["analyses: spot and wavefront"]["<saved file>"])
        thick = [without[label]["<thicknesses>"][3] for label in ("save as", "edit after saving", "another edit", "open the saved file")]
        seeds = (tk_meta["hash seed"], none_meta["hash seed"])
        same = all(a == b and a is not None for a, b in files.values())
        return (seeds == ("1", "2") and before == (None, None) and same and files["save as"][0] != files["save"][0]
                and files["save"][1]["bytes"] > 20000 and tk_meta["operands in the file"] == none_meta["operands in the file"]
                == operands and thick[1] == "6.5" != thick[0] and thick[2] == "9.75" and thick[3] == "6.5"
                and without["open the saved file"]["current_layout_file"] == "path:saved_scene.py",
                f"two processes with hash seeds {seeds}, one editor with a Tk root and one without: the scene saved by each is "
                f"the same file ({same}; {files['save'][1]['bytes']} bytes), at Save As and again at Save after an edit "
                f"(another file: {files['save as'][0] != files['save'][0]}); the operands in it are in the operand list's "
                f"order ({none_meta['operands in the file'] == operands}); row 3's thickness {thick[0]} was edited to {thick[1]} and "
                f"saved, edited to {thick[2]}, and opening the file gives {thick[3]}")

    return _claims((("N", claim_n), ("S", claim_s), ("R", claim_r), ("F", claim_f)))


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
        default, gaussian = record["panel default"], record["panel gaussian"]
        panel_ok = (default["inputs"] == gaussian["inputs"] == 45 and not default["wrong"] and not gaussian["wrong"]
                    and gaussian["source model"] == "Gaussian beam" and default["apply"] != gaussian["apply"]
                    and "gaussian_m2_var" in default["set aside"] and "field_type_var" in gaussian["set aside"]
                    and "field_type_var" not in default["set aside"]
                    and (default["source row spans"], default["field panel shown"]) == (["1", "1"], True)
                    and (gaussian["source row spans"], gaussian["field panel shown"]) == (["2", "2"], False))
        cards = record["operands"]
        cards_ok = (cards["made"] == cards["declared"] and not cards["wrong"] and cards["settings"] == 45
                    and cards["in use"] == cards["first"] and len(cards["first"]) == 1)
        return (not wrong and canvas_ok and field_ok and panel_ok and cards_ok,
                f"the Tk window: three panes with sashes at {start['sashes']} of {start['width']} px; each sidebar hides and "
                f"comes back with its restore strip, the status line and the same sashes (wrong: {wrong or 'none'}); the left "
                f"panel's canvas tracks its content: {canvas}; the field inputs, blank scene: "
                f"{[blank['samples'], blank['entry'], blank['types'][0]]}, finite object with a field: "
                f"{[finite['samples'], finite['entry'], finite['types'][0]]}; of {default['inputs']} registered inputs "
                f"{default['apply']} apply with the default source and {gaussian['apply']} with a Gaussian beam, and each "
                f"widget is live and in the panel exactly when its input applies (wrong: "
                f"{(default['wrong'] + gaussian['wrong']) or 'none'}); the source row spans and the field panel shows: "
                f"{[default['source row spans'], default['field panel shown']]} and "
                f"{[gaussian['source row spans'], gaussian['field panel shown']]}; the Tk cards make {cards['settings']} "
                f"operand settings, exactly the ones the model declares ({cards['made'] == cards['declared']}) with its start "
                f"values (wrong: {cards['wrong'] or 'none'}), and {cards['in use']} is in use")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str, needs_display: bool, config: str = "", hash_seed: str = "") -> dict | list:
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
    # ONE analysis worker, whatever memory is free. How many the model starts is capped by the
    # machine's free memory at that moment, and the parallel trace agrees with the single one only
    # to the last bits (0.4442048847402281 / ...22785): in a loaded gate on a 14 GB machine the two
    # sessions were given different counts and five trace results "differed" (the full gate of
    # 2026-10-10). The comparison is about Tk, not about the machine.
    env["KRAKEN_ANALYSIS_WORKER_MB"] = "1000000"
    if config:                  # a configuration folder of its own: no session finds what another left
        Path(config).mkdir(parents=True, exist_ok=True)
        env["KRAKEN_CONFIG_DIR"] = config
    if hash_seed:               # the order of a set is the process's: what is saved must not be
        env["PYTHONHASHSEED"] = hash_seed
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
        tk_meta = _run(f"session('tk', {tk_path!r})", "S", True, str(Path(folder) / "config_tk"), "1")
        none_meta = _run(f"session('none', {none_path!r})", "N", False, str(Path(folder) / "config_none"), "2")
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
