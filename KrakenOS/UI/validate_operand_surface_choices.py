"""Guard for bugs/0969: an operand's surface choices are model data, handed to each shell's pickers.

`_refresh_operand_surface_choices` runs on every table sync. It computed the list an operand's "Surf"
picker offers and then found the Tk pickers by walking EVERY widget of the window -- 409 of them on
a two-arm layout -- comparing each combobox's variable name. Measured: about 2 ms of each 5 ms
table sync, to fill eight pickers that are not laid out (no operand declares a surface setting
today). It also tied model code to a Tk widget tree, which phase 7f removes.

  P  the model, no display:
       P1 the list is Auto and then every row that is neither the object nor the image, as
          "index: name"; a refresh puts an operand aimed at a surface that is gone back to Auto,
          leaves a valid one alone (and an empty one, which already reads as Auto), hands the list
          to every REGISTERED picker and to the shell's
          `show_operand_surface_choices`, and asks the window for its widgets NOT ONCE
       P2 the catalogue: the surface setting names the model's method, `choices_for` returns the
          model's list for it and a fixed setting's own choices; with no such method, the fixed ones
  T  a real Tk editor: the panel registered one picker per operand and each offers the model's list;
     after a row is renamed and the table synced they offer the new list; a refresh makes no
     `winfo_children` call on the editor
  Q  a real Qt shell, with one operand given a surface setting: the seam is the panel's; its "Surf"
     picker offers the model's list; choosing an entry writes that operand's variable; when ANOTHER
     row is renamed the OPEN picker shows the new list and still that entry; when that surface's own
     row is removed the model puts the variable back to Auto and the open picker shows Auto
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "OPERANDSURF_RESULT "
SKIP_MARK = "OPERANDSURF_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def pure_checks() -> list:
    from types import SimpleNamespace

    from KrakenOS.UI import optimization_controls as catalogue
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as Model

    rows = [SimpleNamespace(surface="Object", name="object"), SimpleNamespace(surface="Standard", name="front"),
            SimpleNamespace(surface="Standard", name="back"), SimpleNamespace(surface="Image", name="image")]
    walked: list = []
    handed: list = []
    menus = {"A": {}, "B": {}}
    owner = SimpleNamespace(
        rows=rows,
        operand_surface_vars={"A": _Var("2: back"), "B": _Var("7: gone"), "C": _Var("")},
        operand_surface_menus=menus,
        show_operand_surface_choices=lambda values: handed.append(list(values)),
        winfo_children=lambda: (walked.append(1), [])[1],
    )
    owner.operand_surface_options = lambda: Model.operand_surface_options(owner)
    options = Model.operand_surface_options(owner)
    Model._refresh_operand_surface_choices(owner)
    after = {label: var.get() for label, var in owner.operand_surface_vars.items()}
    # an owner with nothing registered and no shell (a stripped snapshot editor): nothing raises
    bare = SimpleNamespace(rows=rows, operand_surface_vars={"A": _Var("9: gone")})
    bare.operand_surface_options = lambda: Model.operand_surface_options(bare)
    try:
        Model._refresh_operand_surface_choices(bare)
        bare_raised = ""
    except Exception as exc:
        bare_raised = f"{type(exc).__name__}: {exc}"
    out = [["P1", options == ["Auto", "1: front", "2: back"] and after == {"A": "2: back", "B": "Auto", "C": ""}
            and all(menu.get("values") == options for menu in menus.values()) and handed == [options] and walked == []
            and not bare_raised and bare.operand_surface_vars["A"].get() == "Auto",
            f"the list {options}; after a refresh the operands' surfaces are {after}; each of {len(menus)} registered "
            f"pickers got the list {all(menu.get('values') == options for menu in menus.values())}; the shell was handed it "
            f"{len(handed)}x; the window was asked for its widgets {len(walked)}x; an owner with no picker and no shell: "
            f"{bare.operand_surface_vars['A'].get()!r}{' -- RAISED ' + bare_raised if bare_raised else ''}"]]

    surface = next(control for control in catalogue.OPERAND_CONTROLS if control.name == "surface")
    fixed = next(control for control in catalogue.OPERAND_CONTROLS if control.name == "mtf_mode")
    with_model = catalogue.choices_for(surface, owner)
    without = catalogue.choices_for(surface, SimpleNamespace())
    out.append(["P2", surface.options == "operand_surface_options" and with_model == options and without == ["Auto"]
                and catalogue.choices_for(fixed, owner) == list(catalogue.MTF_MODES) and fixed.options == "",
                f"the surface setting names {surface.options!r}: choices_for gives {with_model} with the model and "
                f"{without} without; a fixed setting gives {catalogue.choices_for(fixed, owner)}"])
    return out


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import OPERAND_REGISTRY, KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    for _ in range(4):
        editor.update()
    options = editor.operand_surface_options()
    menus = dict(editor.operand_surface_menus)
    offered = {label: list(menu.cget("values")) for label, menu in menus.items()}
    registered_all = sorted(menus) == sorted(spec.label for spec in OPERAND_REGISTRY.values())
    old_name = editor.rows[1].name
    editor.rows[1].name = "renamed for the guard"
    walked: list = []
    real = editor.root.winfo_children
    editor.winfo_children = lambda: (walked.append(1), real())[1]      # the editor's own call would land here
    try:
        editor._sync_table()
        for _ in range(2):
            editor.update()
    finally:
        del editor.winfo_children
    new_options = editor.operand_surface_options()
    offered_after = {label: list(menu.cget("values")) for label, menu in menus.items()}
    editor.rows[1].name = old_name
    return [["T", registered_all and len(menus) >= 4 and len(options) >= 4 and all(v == options for v in offered.values())
             and "1: renamed for the guard" in new_options and all(v == new_options for v in offered_after.values())
             and walked == [],
             f"the Tk panel registered {len(menus)} pickers, one per operand: {registered_all}; each offers the model's "
             f"{len(options)} choices {all(v == options for v in offered.values())}; after a rename and a table sync they offer "
             f"{new_options[:2]}... {all(v == new_options for v in offered_after.values())}; the sync asked the window for its "
             f"widgets {len(walked)}x"]]


def qt_checks() -> list:
    import dataclasses
    import time

    from PySide6.QtWidgets import QComboBox

    from KrakenOS.UI.optimization_controls import controls_for
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    window.build_scene()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    editor, panel = window.editor, window.optimization_panel
    seam = editor.__dict__.get("show_operand_surface_choices")
    seam_is_panel = getattr(seam, "__self__", None) is panel
    declared_today = [spec.label for spec in panel.specs if any(c.name == "surface" for c in controls_for(spec))]
    # no operand declares a surface setting today: give the first one, for this window only
    first = panel.specs[0]
    panel.specs = (dataclasses.replace(first, controls=tuple(first.controls) + ("surface",)),) + tuple(panel.specs[1:])
    panel._select_labels([first.label])
    settle()
    field = panel.fields.get((first.label, "surface"))
    if not isinstance(field, QComboBox):
        return [["Q", False, f"the Qt panel built no Surf picker for {first.label!r}: {type(field).__name__}"]]
    options = editor.operand_surface_options()
    offered = [field.itemText(i) for i in range(field.count())]
    variable = editor.operand_surface_vars[first.label]
    target = options[2]
    field.setCurrentIndex(2)                      # the picker's own signal carries the choice
    settle()
    chosen = (str(variable.get()), field.currentText())
    row_index = int(target.split(":", 1)[0])
    # another row is renamed: the list changes, this operand's surface is still in it
    other = int(options[-1].split(":", 1)[0])
    other_name = editor.rows[other].name
    editor.rows[other].name = "renamed for the guard"
    try:
        editor._sync_table()
        settle()
        renamed_options = editor.operand_surface_options()
        kept = (str(variable.get()), field.currentText(), [field.itemText(i) for i in range(field.count())] == renamed_options)
    finally:
        editor.rows[other].name = other_name
        editor._sync_table()
        settle()
    removed = editor.rows.pop(row_index)
    try:
        editor._sync_table()
        settle()
        new_options = editor.operand_surface_options()
        offered_after = [field.itemText(i) for i in range(field.count())]
        after = (str(variable.get()), field.currentText())
    finally:
        editor.rows.insert(row_index, removed)
        editor._sync_table()
    return [["Q", seam_is_panel and len(options) >= 4 and offered == options and chosen == (target, target)
             and other != row_index and renamed_options != options and kept == (target, target, True)
             and target not in new_options and offered_after == new_options and after == ("Auto", "Auto"),
             f"the seam is the Qt panel's: {seam_is_panel}; operands declaring a surface setting today: {declared_today}; "
             f"given one, {first.label!r} offers the model's {len(options)} choices: {offered == options}; choosing "
             f"{target!r} -> (variable, picker) {chosen}; with ANOTHER row renamed the list changes and the open picker "
             f"still shows it: (variable, picker, new list shown) {kept}; with that row removed the model's list has {len(new_options)}, "
             f"the open picker shows it: {offered_after == new_options}, and (variable, picker) are {after}"]]


def _run(call: str, needs: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_operand_surface_choices import qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = pure_checks() + _run("tk_checks()", "") + _run("qt_checks()", "import PySide6\n")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
