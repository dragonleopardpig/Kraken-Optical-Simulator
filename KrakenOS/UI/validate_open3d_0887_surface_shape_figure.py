"""Display-free guard: the Surface Shape Builder and `FormFigure` (bugs/0887,
docs/design_qt_migration.md phase 3, with the phase-6 matplotlib seam).

`FormPreview` (0886) draws polygons and text with no dependencies. This dialog's explanation is a
real PLOT -- an imshow of the sag/departure map with a colorbar beside the aperture/UDA/mask
footprint -- so `FormFigure` carries it instead: the MODEL draws into a figure the VIEW supplies,
because matplotlib already has a canvas for both toolkits, and `draw` returns the status line,
which is where a validation warning about the drawn candidate belongs.

  B  the builder: the coefficient and preset fields, the Browse verb, a figure
  D  draw fills a real figure and reports the model's own validation of the candidate
  F  the plot FOLLOWS the values -- a mask preset adds its patches without an Apply
  V  the model's own messages
  A  apply writes advanced/extra_data/uda together
  T  the REAL Tk dialog embeds a matplotlib canvas
  Q  the Qt dialog embeds one too, on the same builder
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    row = next(index for index, item in enumerate(window.editor.rows)
               if item.surface not in ("Object", "Image"))
    window.rows_view.selectRow(row)
    app.processEvents()
    dialog = window.action_manager["surface_shape"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    embedded = dialog.figure_canvas is not None
    axes = len(dialog.figure_object.axes)
    first = dialog.summary.text()
    dialog.widgets["mask_preset"].setCurrentText("Ronchi mask")
    dialog.redraw_visuals()
    app.processEvents()
    patches = sum(len(axis.patches) for axis in dialog.figure_object.axes)
    dialog.close()
    app.processEvents()

    window.close()
    return [embedded, axes, first[:40], patches]


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
        "from KrakenOS.UI.validate_open3d_0887_surface_shape_figure import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", "the Qt subprocess timed out after 900 s"
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_surface_shape_form

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
        row_index = next(index for index, row in enumerate(editor.rows)
                         if row.surface not in ("Object", "Image"))

        form = build_surface_shape_form(editor, row_index)
        keys = [field.key for field in form.fields]
        refused = ""
        image_row = next((index for index, row in enumerate(editor.rows)
                          if row.surface == "Image"), None)
        try:
            build_surface_shape_form(editor, image_row)
        except FormRefused as exc:
            refused = str(exc)
        ok(len(keys) == 11 and "aspher" in keys and "mask_preset" in keys
           and form.figure is not None
           and [action.label for action in form.actions] == ["Browse CAD/STL..."]
           and refused.startswith("Shape builders apply to physical surfaces"),
           f"B: {len(keys)} shape fields, one Browse verb and a figure; an Image row refuses "
           f"({refused[:46]!r}...)")

        figure = Figure(figsize=(7.2, 5.4), dpi=100)
        message = form.figure.draw(form, dict(form.values), figure)
        ok(len(figure.axes) >= 2 and message
           and (message.startswith("Preview OK.") or message.startswith("Validation")),
           f"D: draw filled {len(figure.axes)} axes and reported the model's own verdict on "
           f"the candidate ({message[:48]!r})")

        figure.clear()
        form.figure.draw(form, dict(form.values, mask_preset="Ronchi mask"), figure)
        masked = sum(len(axis.patches) for axis in figure.axes)
        figure.clear()
        form.figure.draw(form, dict(form.values, mask_preset="None"), figure)
        plain = sum(len(axis.patches) for axis in figure.axes)
        ok(masked > plain,
           f"F: the plot FOLLOWS the values -- a Ronchi preset drew {masked} mask patches "
           f"where None drew {plain}, before any Apply")

        # `inf` is not a Python literal, so "[1.0, inf]" fails to PARSE rather than failing the
        # finiteness check; 1e400 parses and overflows, which is what reaches that guard.
        messages = [form.validate(dict(form.values, aspher="not a list")),
                    form.validate(dict(form.values, znk="[1.0, 1e400]")),
                    form.validate(dict(form.values))]
        ok(messages[0] and "numeric list" in messages[0][0]
           and messages[1] and "non-finite" in messages[1][0]
           and messages[2] == [],
           f"V: {messages[0][0][:44]!r}, {messages[1][0][:44]!r}")

        status = form.apply(dict(form.values, mask_preset="Ronchi mask", uda_preset="Hexagon"))
        stored = dict(editor.rows[row_index].advanced or {})
        uda = editor.rows[row_index].uda
        ok(str(stored.get("Mask_Shape", {}).get("preset")) == "ronchi"
           and int(stored.get("Mask_Type", 0)) == 2
           and isinstance(uda, dict) and int(uda.get("sides", 0)) == 6
           and "Updated shape/custom/mask settings" in status,
           f"A: apply wrote the mask, its Mask_Type and the {uda.get('sides')}-sided UDA "
           f"together")

        before = {str(child) for child in editor.root.winfo_children()}
        editor.open_surface_shape_builder(row_index)
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before and child.winfo_class() == "Toplevel"]
        # FigureCanvasTkAgg's widget is a plain tk.Canvas -- the FIGURE hangs off the canvas
        # OBJECT, not the widget -- so identify it by being the only canvas, and a big one
        import tkinter as tk

        widths = []
        if windows:
            def walk(widget):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Canvas):
                        widths.append(int(child.winfo_reqwidth()))
                    walk(child)

            walk(windows[-1])
            windows[-1].destroy()
        ok(windows and widths and max(widths) >= 600 and not boxes,
           f"T: the REAL Tk dialog embedded a matplotlib canvas "
           f"({max(widths) if widths else 0} px wide)")
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

    embedded, axes, first, patches = payload
    ok(embedded and int(axes) >= 2 and str(first) and int(patches) > 0,
       f"Q: the Qt dialog embedded a canvas with {axes} axes, and a Ronchi preset drew "
       f"{patches} mask patches on it")

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
