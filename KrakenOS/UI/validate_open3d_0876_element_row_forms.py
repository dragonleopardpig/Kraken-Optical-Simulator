"""Display-free guard: the Path-Local Pose and Element Settings row forms (bugs/0876,
docs/design_qt_migration.md phase 3).

These two edit an element BLOCK -- the run of consecutive rows sharing one element key -- which
every previous row form's one-row assumption could not express. `RowForm.row_index` is the
block's FIRST row (the row a view selects) and the block itself rides in `form.state`.

  B  a row grows into its block; two blocks selected at once refuse
  R  the pose editor refuses an element with no path-placement metadata
  V  the model's own messages: a non-number, a non-finite tilt, an empty name, a bad role
  P  the pose apply writes through _apply_path_local_pose_to_indices
  E  Element Settings writes the name and metadata to EVERY row of the block
  T  the REAL Tk dialogs open on the builders' values, with an EDITABLE parent-splitter combo
  Q  the Qt forms do the same
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
POSE_KEYS = ("arm_distance", "local_decenter_x", "local_decenter_y",
             "local_tilt_x", "local_tilt_y", "local_tilt_z")


def block_starting_with(editor, element_key: str) -> int:
    """The first row of the named element block."""
    return next(index for index, row in enumerate(editor.rows)
                if editor._element_key(row) == element_key)


def prepare(editor) -> tuple:
    """Give the transmit arm a path-placement record, the way a stock-lens insert would.

    No shipped scene carries one -- `_metadata_has_path_pose` wants `path_component_type` or
    `path_frame_source`, which only the path-component commands write -- so the guard writes one
    onto the block's FIRST row (where the block reads its metadata) and both halves agree.
    """
    pose_row = block_starting_with(editor, "Transmit doublet")
    plain_row = block_starting_with(editor, "Reflect doublet")
    parent = next(choice for choice in editor._beam_splitter_element_choices() if choice)
    data = dict(editor._element_metadata(editor.rows[pose_row]))
    data.update({"path_component_type": "stock_lens", "parent_splitter": parent,
                 "branch_selector": "transmit", "arm_role": "Transmit", "arm_distance": 12.0,
                 "element_name": "Transmit doublet"})
    editor._set_element_metadata(editor.rows[pose_row], data)
    return pose_row, plain_row, parent


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    pose_row, plain_row, _parent = prepare(editor)
    window.refresh_from_model()
    app.processEvents()

    window.rows_view.selectRow(pose_row)
    app.processEvents()
    pose = window.action_manager["path_local_pose"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    pose.widgets["arm_distance"].setText("21.25")
    pose_errors = list(pose.validate())
    pose_applied = pose.apply_to_row()
    app.processEvents()
    pose_state = float(editor._element_metadata(editor.rows[pose_row]).get("arm_distance", 0.0))

    window.rows_view.selectRow(plain_row)
    app.processEvents()
    settings = window.action_manager["element_settings"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    editable = settings.widgets["parent_splitter"].isEditable()
    settings.widgets["element_name"].setText("QtReflect")
    settings.widgets["arm_role"].setCurrentText("Reflect")
    settings_errors = list(settings.validate())
    settings_applied = settings.apply_to_row()
    app.processEvents()
    block = [index for index, row in enumerate(editor.rows)
             if editor._element_key(row) == "QtReflect"]
    roles = [str(editor._element_metadata(editor.rows[index]).get("arm_role"))
             for index in block]

    window.close()
    return [pose.form.row_index, sorted(pose.form.state["indices"]), pose_errors,
            bool(pose_applied), pose_state, bool(editable), settings_errors,
            bool(settings_applied), block, roles]


def _run_qt_subprocess() -> tuple[str, object]:
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
        "from KrakenOS.UI.validate_open3d_0876_element_row_forms import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", ("the Qt subprocess timed out after 900 s -- a modal dialog with no one "
                         "to close it is the usual cause")
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_dialog_state(editor, opener):
    """Open a REAL Tk dialog and read back what it shows and how its combos behave."""
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    opener()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    shown: list[str] = []
    readonly: list[str] = []
    try:
        def walk(widget):
            for child in widget.winfo_children():
                name = ""
                for option in ("textvariable", "variable"):
                    try:
                        name = str(child.cget(option))
                    except Exception:
                        name = ""
                    if name:
                        break
                if name:
                    try:
                        shown.append(str(window.getvar(name)))
                    except Exception:
                        pass
                if isinstance(child, ttk.Combobox):
                    readonly.append("readonly" if child.instate(["readonly"]) else "editable")
                walk(child)

        walk(window)
        return shown, readonly
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import (FormRefused, build_element_settings_form,
                                       build_path_local_pose_form)

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        pose_row, plain_row, parent = prepare(editor)

        settings_form = build_element_settings_form(editor, plain_row + 1)
        editor._select_table_indices([pose_row, plain_row], focus_index=pose_row)
        two_blocks = ""
        try:
            build_element_settings_form(editor)
        except FormRefused as exc:
            two_blocks = str(exc)
        ok(settings_form.row_index == plain_row
           and settings_form.state["indices"] == [plain_row, plain_row + 1, plain_row + 2]
           and two_blocks == "Open Element Settings for one element at a time.",
           f"B: row {plain_row + 1} grew into its block {settings_form.state['indices']} with "
           f"row_index={settings_form.row_index}; two selected blocks refuse ({two_blocks!r})")

        no_pose = ""
        try:
            build_path_local_pose_form(editor, plain_row)
        except FormRefused as exc:
            no_pose = str(exc)
        ok(no_pose.startswith("The selected element has no path-placement metadata."),
           f"R: the pose editor refuses an element with no path metadata ({no_pose[:46]!r}...)")

        pose_form = build_path_local_pose_form(editor, pose_row)
        pose_messages = [pose_form.validate(dict(pose_form.values, arm_distance="x")),
                         pose_form.validate(dict(pose_form.values, local_tilt_x="inf")),
                         pose_form.validate(pose_form.values)]
        settings_messages = [settings_form.validate(dict(settings_form.values,
                                                         element_name="   ")),
                             settings_form.validate(dict(settings_form.values,
                                                         arm_role="Nope")),
                             settings_form.validate(settings_form.values)]
        ok(pose_messages[0] == ["arm distance expects a number."]
           and pose_messages[1] == ["local tilt x must be finite."]
           and pose_messages[2] == []
           and settings_messages[0] == ["Element name cannot be empty."]
           and settings_messages[1] == ["Choose a valid path role."]
           and settings_messages[2] == [],
           f"V: {pose_messages[0][0]!r}, {pose_messages[1][0]!r}, "
           f"{settings_messages[0][0]!r}, {settings_messages[1][0]!r}")

        pose_status = pose_form.apply(dict(pose_form.values, arm_distance="18.5"))
        written = float(editor._element_metadata(editor.rows[pose_row]).get("arm_distance", 0.0))
        ok(abs(written - 18.5) < 1e-9 and "Updated path-local pose" in pose_status
           and editor.status_var.get() == pose_status,
           f"P: the pose apply wrote arm_distance={written} through "
           f"_apply_path_local_pose_to_indices")

        settings_form = build_element_settings_form(editor, plain_row)
        settings_status = settings_form.apply(dict(settings_form.values,
                                                   element_name="GuardReflect",
                                                   arm_role="Reflect",
                                                   branch_selector="Auto",
                                                   local_decenter_x="1.5"))
        block = [index for index, row in enumerate(editor.rows)
                 if editor._element_key(row) == "GuardReflect"]
        records = [editor._element_metadata(editor.rows[index]) for index in block]
        ok(block == [plain_row, plain_row + 1, plain_row + 2]
           and all(str(record.get("arm_role")) == "Reflect" for record in records)
           and all(str(record.get("branch_selector")) == "reflect" for record in records)
           and all(abs(float(record.get("local_decenter_x", 0.0)) - 1.5) < 1e-9
                   for record in records)
           and "Updated element settings for GuardReflect" in settings_status,
           f"E: Element Settings wrote the name, the role and an Auto selector resolved to "
           f"'reflect' to all {len(block)} rows of the block")

        shown, combos = _tk_dialog_state(
            editor, lambda: editor.open_element_settings())
        rebuilt = build_element_settings_form(editor, plain_row)
        missing = [value for key, value in rebuilt.values.items()
                   if value and value not in (shown or [])]
        # the pose dialog reads the TABLE selection, so put it on the placed block first
        editor._select_table_indices(pose_form.state["indices"], focus_index=pose_row)
        pose_shown, _pose_combos = _tk_dialog_state(
            editor, lambda: editor.open_selected_path_local_pose_editor())
        pose_rebuilt = build_path_local_pose_form(editor, pose_row)
        pose_missing = [pose_rebuilt.values[key] for key in POSE_KEYS
                        if pose_rebuilt.values[key] not in (pose_shown or [])]
        ok(shown is not None and not missing and combos == ["readonly", "editable", "editable"]
           and pose_shown is not None and not pose_missing and not boxes,
           f"T: the REAL Element Settings dialog shows the builder's values with combos "
           f"{combos} (the parent splitter is EDITABLE), and the REAL Path-Local Pose dialog "
           f"shows its {len(POSE_KEYS)} pose values"
           + (f" -- missing {missing + pose_missing}" if missing or pose_missing else "")
           + (f" -- boxes {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    (row_index, indices, pose_errors, pose_applied, pose_state, editable, settings_errors,
     settings_applied, qt_block, roles) = payload
    ok(pose_applied and pose_errors == [] and row_index == indices[0]
       and abs(float(pose_state) - 21.25) < 1e-9,
       f"Q1: the Qt pose form opened on block {indices} (row_index={row_index}) and applied "
       f"arm_distance={pose_state}")
    ok(settings_applied and settings_errors == [] and editable
       and len(qt_block) == 3 and set(roles) == {"Reflect"},
       f"Q2: the Qt Element Settings form has an EDITABLE parent combo and wrote "
       f"{len(qt_block)} rows, roles {sorted(set(roles))}")

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
