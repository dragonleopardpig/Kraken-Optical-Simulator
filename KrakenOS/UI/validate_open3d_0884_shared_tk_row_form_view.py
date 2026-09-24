"""Display-free guard: the five row dialogs that still had their own Tk layout now share the
renderer (bugs/0884, docs/design_qt_migration.md phase 3).

0869-0873 moved these dialogs' MODELS into `row_forms/` but left each panel a hand-written Tk
page -- 898 lines of layout that `panels/row_form_view.py` already knew how to draw. Finishing
the job needed two things the shared renderer lacked: `kind="textarea"` (a `tk.Text`, which has
no `textvariable`, so it is read and written by hand) and `form.groups` as a `ttk.Notebook` with
a canvas+scrollbar per tab, which is what the hand-written Advanced Surface page did for its 53
fields.

  R  the renderer draws every kind the six builders use, including a 6-tab notebook
  L  the five panels are down to the prologue and one call
  D  each REAL Tk dialog opens on the builder's fields, or refuses with the builder's message
"""
from __future__ import annotations

import inspect
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")
SPLITTER_SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
PANELS = (
    ("main_coating_material_dialog", "open_coating_material_editor"),
    ("main_error_map_dialog", "open_error_map_editor"),
    ("main_beam_splitter_dialog", "open_beam_splitter_settings"),
    ("main_diffuse_scatter_dialog", "open_diffuse_scatter_settings"),
    ("main_advanced_surface_dialog", "open_advanced_surface_editor"),
)


def _widget_census(window):
    import tkinter as tk
    from tkinter import ttk

    counts = {"Notebook": 0, "Entry": 0, "Combobox": 0, "Checkbutton": 0, "Text": 0,
              "Button": 0, "Treeview": 0}

    def walk(widget):
        for child in widget.winfo_children():
            if isinstance(child, ttk.Notebook):
                counts["Notebook"] += 1
            elif isinstance(child, ttk.Combobox):
                counts["Combobox"] += 1
            elif isinstance(child, ttk.Treeview):
                counts["Treeview"] += 1
            elif isinstance(child, ttk.Entry):
                counts["Entry"] += 1
            elif isinstance(child, ttk.Checkbutton):
                counts["Checkbutton"] += 1
            elif isinstance(child, tk.Text):
                counts["Text"] += 1
            elif isinstance(child, ttk.Button):
                counts["Button"] += 1
            walk(child)

    walk(window)
    return counts


def _open(editor, method, row_index):
    before = {str(child) for child in editor.root.winfo_children()}
    getattr(editor, method)(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    try:
        return _widget_census(window)
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import row_form_view

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    view = inspect.getsource(row_form_view)
    ok('field.kind == "textarea"' in view and "tk.Text(" in view
       and 'text.get("1.0", "end-1c")' in view
       and "ttk.Notebook(" in view and "form.fields_in(group)" in view
       and "tk.Canvas(" in view,
       "R: the shared renderer draws textareas (a tk.Text read by hand, since it has no "
       "textvariable) and tabs (a Notebook with a canvas+scrollbar per group)")

    sizes = {}
    for panel, _method in PANELS:
        path = Path("KrakenOS/UI/panels") / f"{panel}.py"
        source = path.read_text(encoding="utf-8")
        sizes[panel] = len(source.splitlines())
        if "render_row_form(" not in source:
            ok(False, f"L: {panel} does not use the shared renderer")
            break
        if "ttk.Entry(" in source or "ttk.Combobox(" in source or "ttk.Notebook(" in source:
            ok(False, f"L: {panel} still builds its own widgets")
            break
    else:
        ok(max(sizes.values()) < 100,
           f"L: the five panels are the prologue and one call now -- "
           f"{', '.join(f'{name.replace(chr(95), ' ')[5:]} {size}' for name, size in sizes.items())} lines")

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        coating = _open(editor, "open_coating_material_editor", 1)
        error_map = _open(editor, "open_error_map_editor", 1)
        advanced = _open(editor, "open_advanced_surface_editor", 1)
        refused_before = len(boxes)
        diffuse = _open(editor, "open_diffuse_scatter_settings", 1)
        diffuse_refused = len(boxes) > refused_before

        editor.layout_files[SPLITTER_SCENE.stem] = SPLITTER_SCENE
        editor.load_layout_by_name(SPLITTER_SCENE.stem)
        splitter_row = next(index for index, row in enumerate(editor.rows)
                            if row.surface == "Beam Splitter")
        splitter = _open(editor, "open_beam_splitter_settings", splitter_row)

        ok(coating is not None and coating["Text"] == 1 and coating["Combobox"] >= 2
           and coating["Button"] >= 4,
           f"D1: Coating / Material drew its literal table as a textarea "
           f"({coating['Text']} Text, {coating['Combobox']} combos, "
           f"{coating['Button']} buttons)" if coating else "D1: Coating / Material did not open")
        ok(error_map is not None and error_map["Button"] >= 4,
           f"D2: Error Map drew its static summary and {error_map['Button']} verbs"
           if error_map else "D2: Error Map did not open")
        ok(advanced is not None and advanced["Notebook"] == 1 and advanced["Entry"] > 40
           and advanced["Checkbutton"] >= 1,
           f"D3: Advanced Surface drew a notebook with {advanced['Entry']} entries and "
           f"{advanced['Checkbutton']} switch(es)" if advanced else
           "D3: Advanced Surface did not open")
        ok(splitter is not None and splitter["Entry"] >= 2 and splitter["Combobox"] >= 1,
           f"D4: Beam Splitter opened on a real splitter row (S{splitter_row}) with "
           f"{splitter['Entry']} entries" if splitter else
           f"D4: Beam Splitter did not open on S{splitter_row}")
        ok(diffuse is None and diffuse_refused,
           "D5: Diffuse / BRDF refuses a non-Diffuse row through the builder's message, "
           "exactly as it did before")
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

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
