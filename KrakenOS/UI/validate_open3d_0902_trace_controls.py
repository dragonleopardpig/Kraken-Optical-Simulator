"""Display-free guard: the trace/display inputs in Qt, and whose rules they are (bugs/0902,
docs/design_qt_migration.md phase 6).

The last 15 inputs of the Tk trace/display panel -- pupil factor, analysis surface, spot view,
scene trace, NS target and hit limit, folded reach, NS probabilistic split, wavefront style,
tolerance compare, show clipped rays, analysis path, detector bins, coherent sum and BField z --
are the third `system_controls` group. Two things came with them that the catalogue could not
yet say, and both were MODEL logic living in the Tk layout:

* WHICH INPUTS APPLY. Twenty `_register_left_mode_control(key, widget, lambda: ...)` calls
  carried the rules -- object mode only for the pupil/field source, tolerance compare only with
  that plot ticked, detector bins only with a detector plot -- so the Qt System dock (0900)
  offered every input regardless. The rules are named model methods now; `SystemControl.relevant`
  names one, and BOTH shells ask it. The model tells a shell to re-read through a
  `show_control_state` seam at the end of every sync.
* LISTS THE MODEL FILLS. The analysis-surface and NS-target choices existed only as a Tk
  combobox's "values", and loading saved settings read them back OUT of that widget. They are
  `analysis_surface_options()` / `analysis_branch_options()` now; the Tk menus are one consumer.

  C  15 trace inputs (2 checkboxes), and every input of all three groups is either registered in
     the model registry or made by the editor's constructor -- so a shell without Tk panels has it
  K  the Tk panel takes every label and fixed list from the catalogue; the 8 constants that
     moved out of `layout_editor` are declared once and re-exported
  R  no enable rule is a lambda in a layout any more -- neither the trace panel's 20 nor the 25
     source/field ones in `_register_source_mode_controls`, which the 0900/0901 docks also
     lacked -- and for every state tried the Tk registration and the catalogue rule agree
  L  the surface list is model state, the Tk menu shows it, and neither settings loading nor the
     scene-bundle display reads a widget to find it
  Q  in Qt the Trace dock offers the model's live list; relevance follows the same rules in all
     three docks, including the System dock's object mode that 0900 left always on; the
     checkboxes bind both ways
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
#: analysis selections that switch the plot-dependent inputs on and off
SELECTIONS = ((), ("tolerance_compare",), ("detector_map",), ("coherent_detector",),
              ("branch_field",))
#: source states, as the variables to write -- enough to switch every source rule both ways:
#: the random-source inputs need a random source, the divergence inputs the other Gaussian
#: mode, and pupil r/theta the R-theta pattern
SOURCES = (
    {"source_model_var": "Pupil / field", "pupil_pattern_var": "Meridional fan"},
    {"source_model_var": "Pupil / field", "pupil_pattern_var": "R-theta"},
    {"source_model_var": "Gaussian beam", "gaussian_input_mode_var": "Waist + offset"},
    {"source_model_var": "Gaussian beam", "gaussian_input_mode_var": "Diameter + divergence"},
    {"source_model_var": "Random circle source"},
)
#: "Folded reach" applies when the scene CAN fold, and om05a_folded always can -- seeing it
#: switch off needs an unfoldable scene, which this guard does not load. Its agreement IS
#: checked in every state; only the "seen both ways" requirement is waived, by name.
ONE_WAY_ON_THIS_SCENE = {"folded_detector_policy_var"}


def constructor_made() -> set:
    """The variables `KrakenLayoutEditor.__init__` makes through the UI host."""
    tree = ast.parse(Path("KrakenOS/UI/layout_editor.py").read_text(encoding="utf-8"))
    made = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute)
                    and func.value.attr == "ui"):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        made.add(target.attr)
    return made


def rule_states(editor, select, set_source):
    """Yield (state label, {key: rule verdict}) over sources x selections.

    A GENERATOR on purpose: the caller must read the views while each state is still current.
    The first version built the whole list and returned it, so every state's rules were
    compared with the views as the LAST state left them -- four "disagreements" that were the
    guard's, not the product's.
    """
    from KrakenOS.UI.system_controls import CONTROL_GROUPS

    for source in SOURCES:
        set_source(source)
        for selection in SELECTIONS:
            select(selection)
            verdicts = {control.key: control.is_relevant(editor)
                        for _title, group in CONTROL_GROUPS for control in group}
            name = " / ".join(str(value) for value in source.values())
            yield f"{name} + {'/'.join(selection) or 'no plot'}", verdicts


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    panels = (window.system_panel, window.source_panel, window.trace_panel)
    rows: list[list] = []

    live = window.trace_panel.widgets["analysis_surface_var"]
    items = [live.itemText(i) for i in range(live.count())]
    rows.append(["Q1", items == editor.analysis_surface_options() and len(items) > 2
                 and "TraceDock" in window.dock_manager.docks,
                 f"the Trace dock offers the model's own {len(items)} surfaces"])

    def select(selection):
        editor.selected_analysis_modes = []
        for mode in selection:
            editor.toggle_analysis_mode(mode)
        if not selection:
            editor._sync_left_mode_controls()
        app.processEvents()

    def set_source(source):
        for key, value in source.items():
            getattr(editor, key).set(value)
        editor._on_source_model_changed()
        app.processEvents()

    disagreements = []
    for label, verdicts in rule_states(editor, select, set_source):
        shown = {}
        for panel in panels:
            shown.update(panel.enabled())
        for key, verdict in verdicts.items():
            if shown.get(key) != verdict:
                disagreements.append((label, key, verdict, shown.get(key)))
    object_mode_follows = not any(key == "object_mode_var" for _l, key, _v, _s in disagreements)
    rows.append(["Q2", not disagreements and object_mode_follows,
                 f"relevance followed the model's rules in all three docks over "
                 f"{len(SOURCES) * len(SELECTIONS)} states -- the System dock's object mode "
                 f"and the Source dock's Gaussian and random-source inputs included"
                 if not disagreements else f"disagreements: {disagreements[:4]}"])

    box = window.trace_panel.widgets["show_clipped_rays_var"]
    start = bool(editor.show_clipped_rays_var.get())
    box.setChecked(not start)
    app.processEvents()
    written = bool(editor.show_clipped_rays_var.get())
    editor.show_clipped_rays_var.set(start)
    app.processEvents()
    rows.append(["Q3", written == (not start) and box.isChecked() == start,
                 f"the checkbox wrote {written} into the model, and the model writing {start} "
                 f"back ticked it to match"])
    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list]:
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
        "from KrakenOS.UI.validate_open3d_0902_trace_controls import qt_runtime_checks\n"
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
    from KrakenOS.UI import layout_editor, system_controls
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.model_variables import MODEL_VARIABLES
    from KrakenOS.UI.panels import main_trace_display_controls
    from KrakenOS.UI.services import layout_scene_bundle_display, layout_settings
    from KrakenOS.UI.system_controls import CONTROL_GROUPS, TRACE_CONTROLS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- C every input exists for a shell without Tk panels --------------------------------
    made = constructor_made()
    everything = [control for _title, group in CONTROL_GROUPS for control in group]
    orphans = [c.key for c in everything if c.key not in MODEL_VARIABLES and c.key not in made]
    bools = [c.key for c in TRACE_CONTROLS if c.kind == "bool"]
    ok(len(TRACE_CONTROLS) == 15 and len(bools) == 2 and not orphans,
       f"C: {len(TRACE_CONTROLS)} trace inputs ({len(bools)} checkboxes); all {len(everything)} "
       f"inputs of the three groups are registered or constructor-made"
       + (f" -- orphans {orphans}" if orphans else ""))

    # ---- K the Tk panel reads the catalogue ------------------------------------------------
    panel_source = inspect.getsource(main_trace_display_controls)
    literal_labels = [c.label for c in TRACE_CONTROLS
                      if f'"{c.label}"' in panel_source]
    moved = ("FOLDED_DETECTOR_POLICY_VALUES", "FOLDED_DETECTOR_POLICY_DEFAULT",
             "WAVEFRONT_STYLE_VALUES", "WAVEFRONT_STYLE_DEFAULT", "WAVEFRONT_FUNCTION_STYLE",
             "WAVEFRONT_PHASE_STYLE", "FOLDED_DETECTOR_POLICY_TRACE",
             "FOLDED_DETECTOR_POLICY_DISPLAY")
    editor_source = Path("KrakenOS/UI/layout_editor.py").read_text(encoding="utf-8")
    redeclared = [name for name in moved if f"\n{name} = " in editor_source]
    same = all(getattr(layout_editor, name) is getattr(system_controls, name) for name in moved)
    ok(not literal_labels and '"Grid", "Absolute", "Centroid"' not in panel_source
       and not redeclared and same,
       f"K: the Tk panel takes every label and fixed list from the catalogue, and the "
       f"{len(moved)} moved constants are declared once and re-exported as the same objects"
       + (f" -- literal {literal_labels}, redeclared {redeclared}"
          if literal_labels or redeclared else ""))

    # ---- R one rule, two views -------------------------------------------------------------
    layout_lambdas = panel_source.count("lambda:") - panel_source.count(
        "return lambda: control.is_relevant(self)")
    registrations = panel_source.count("self._register_left_mode_control(")
    rewired = panel_source.count("self._relevance(\"")
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin

    source_registrations = inspect.getsource(
        LayoutShellControlsMixin._register_source_mode_controls)
    # the only lambdas left there are "always show" for two layout-only widgets
    source_rules = source_registrations.count("lambda:") - source_registrations.count(
        "lambda: True")
    ok(layout_lambdas == 0 and registrations == rewired == 20 and source_rules == 0
       and "relevance(key)" in source_registrations,
       f"R1: all {registrations} trace-panel registrations and every source/field registration "
       f"ask the catalogue's rule -- no enable rule is a lambda in a layout any more")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)

        def select(selection):
            editor.selected_analysis_modes = []
            for mode in selection:
                editor.toggle_analysis_mode(mode)
            editor._sync_left_mode_controls()

        def set_source(source):
            for key, value in source.items():
                getattr(editor, key).set(value)
            editor._on_source_model_changed()

        from KrakenOS.UI.system_controls import CONTROL_GROUPS as groups

        disagreements, seen = [], {}
        for label, verdicts in rule_states(editor, select, set_source):
            # "" marks the three layout-only widgets (note, summary, manager button) -- not inputs
            visible = {c["var_name"]: c.get("visible") for c in editor._left_mode_controls
                       if c["var_name"]}
            for key, shown in visible.items():
                if shown != verdicts.get(key):
                    disagreements.append((label, key, verdicts.get(key), shown))
                seen.setdefault(key, set()).add(bool(verdicts.get(key)))
        ruled = [c.key for _t, group in groups for c in group if c.relevant]
        one_way = [key for key in ruled
                   if seen.get(key) != {True, False} and key not in ONE_WAY_ON_THIS_SCENE]
        states = len(SOURCES) * len(SELECTIONS)
        ok(not disagreements and not one_way,
           f"R2: over {states} states the Tk panel and the catalogue rule agree on every "
           f"registered input, and {len(ruled) - len(ONE_WAY_ON_THIS_SCENE)} of the "
           f"{len(ruled)} ruled inputs were seen BOTH on and off (folded reach waived: this "
           f"scene can always fold)"
           if not disagreements and not one_way else
           f"R2: disagreements {disagreements[:4]}; only ever one way: {one_way}")

        # ---- L the surface list is model state -----------------------------------------
        options = editor.analysis_surface_options()
        menu = list(editor.analysis_surface_menu["values"])
        readers = (inspect.getsource(layout_settings), inspect.getsource(layout_scene_bundle_display))
        ok(options == menu and len(options) == len(editor.rows) + 1
           and all('analysis_surface_menu["values"]' not in source for source in readers),
           f"L: the {len(options)} surfaces are model state, the Tk menu shows exactly them, and "
           f"settings loading and the scene-bundle display read the model, not the widget")
    finally:
        editor.destroy()

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
