#!/usr/bin/env python3
"""Display-free guard: the Advanced Surface editor fits the screen + scrolls its tabs.

The "Advanced..." (Native KrakenOS attributes) dialog has a Notebook whose Diagnostics/Native
tab alone is ~30 rows -- taller than the screen. The window used to grow to that requested
content height (``_show_centered_dialog`` sized to ``winfo_reqheight()``), so it overflowed the
screen edges with no scrollbar and its title tucked under the top/AGS bar.

The fix: (1) each Notebook tab body lives in a ``tk.Canvas`` + auto-hiding ``Scrollbar`` (the
``make_scroll_tab`` helper) with recursive mouse + touchpad wheel binding; (2) the shared
``_show_centered_dialog`` caps the window to the usable screen and keeps the title below a top
bar. The footer (Apply/Cancel) stays on the window, not inside a scrolled tab, so it is always
reachable.

The dialog needs a real Tk root + full editor state to render, which the penta harness has no
display for, so this is a source-structure guard (mirrors validate_open3d_face_editor_scrollable):

  A. ``MainAdvancedSurfaceDialog.open`` wraps each tab in a Canvas + Scrollbar via
     ``create_window`` (``make_scroll_tab``);
  B. the wheel handler binds ``<MouseWheel>`` AND ``<Button-4>``/``<Button-5>`` recursively;
  C. all three content tabs (Shape Params, the field groups, Custom Surface) go through
     ``make_scroll_tab`` -- none is added to the notebook as a raw frame;
  D. the footer is gridded on the window (row 2), so the buttons are never inside the scroll;
  E. ``_show_centered_dialog`` caps the dialog to the screen (``min`` against a screen-based
     max) instead of growing to the requested content height.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_advanced_surface_dialog_scrollable

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import inspect


def _live_wheel_check() -> "str | None":
    """B, measured: a tall tab built the way the renderer builds one scrolls on a real X11 wheel
    event delivered to a FIELD (not the canvas). None = passed; a string = the failure; SKIP when
    there is no display."""
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.panels.row_form_view import bind_tab_wheel

    try:
        root = tk.Tk()
    except tk.TclError:
        return "SKIP"
    try:
        root.geometry("300x200")
        canvas = tk.Canvas(root, highlightthickness=0, height=200)
        canvas.pack(fill="both", expand=True)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        labels = [ttk.Label(inner, text=f"field {n}") for n in range(80)]
        for n, label in enumerate(labels):
            label.grid(row=n, column=0)
        root.update()
        canvas.configure(scrollregion=canvas.bbox("all"))
        bind_tab_wheel(canvas, inner)
        root.update()
        before = canvas.yview()[0]
        labels[3].event_generate("<Button-5>", x=5, y=5)
        root.update()
        after = canvas.yview()[0]
        if not after > before:
            return f"B: a wheel-down over a field did not scroll the tab (yview {before} -> {after})"
        return None
    finally:
        root.destroy()


def run_checks() -> "tuple[bool, list[str]]":
    """bugs/0911: since bugs/0873/0884 the dialog is a row form drawn by the SHARED renderer
    (`panels/row_form_view.render_row_form`), so the checks read the renderer and the form. The
    old checks read `MainAdvancedSurfaceDialog.open`, which no longer draws anything -- and the
    port had in fact dropped the wheel scrolling (B), which this now measures live."""
    import ast
    from pathlib import Path

    from KrakenOS.UI.panels import main_advanced_surface_dialog as dialog_module
    from KrakenOS.UI.panels import row_form_view
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    failures: list[str] = []
    render_src = inspect.getsource(row_form_view.render_row_form)
    wheel_src = inspect.getsource(row_form_view.bind_tab_wheel)
    place_src = inspect.getsource(LayoutTableWorkbenchMixin._show_centered_dialog)

    # bugs/0947: through `present_row_form`, the shell-aware entry that falls back to this renderer
    dialog_src = inspect.getsource(dialog_module)
    if not (("present_row_form(" in dialog_src or "render_row_form(" in dialog_src)
            and "render_row_form(owner, form" in inspect.getsource(row_form_view.present_row_form)):
        failures.append("the Advanced Surface dialog no longer renders through render_row_form")

    # A) every tab of a grouped form is a Canvas + Scrollbar scroll region
    if "for group in form.groups" not in render_src:
        failures.append("A: the renderer does not make one tab per group")
    if "tk.Canvas(" not in render_src or "create_window(" not in render_src or "Scrollbar(" not in render_src:
        failures.append("A: a tab body is not a Canvas+Scrollbar+create_window scroll region")

    # B) the wheel -- mouse and touchpad -- scrolls a tab from over any field
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        if seq not in wheel_src:
            failures.append(f"B: the tab wheel does not bind {seq} (mouse + touchpad)")
    if "bind_tab_wheel(canvas, inner)" not in render_src:
        failures.append("B: the renderer does not bind the wheel on each tab")
    live = _live_wheel_check()
    if live not in (None, "SKIP"):
        failures.append(live)

    # C) every Advanced Surface field sits in a tab -- a field with no group would be drawn
    #    nowhere a tab scrolls
    tree = ast.parse(Path(inspect.getsourcefile(
        __import__("KrakenOS.UI.row_forms.advanced_surface", fromlist=["x"]))).read_text())
    ungrouped = [node.lineno for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "FormField"
                 and not any(k.arg == "group" for k in node.keywords)]
    if ungrouped:
        failures.append(f"C: Advanced Surface fields with no tab (lines {ungrouped})")

    # D) the footer (Apply/Cancel) is on the dialog frame, never inside a scrolled tab
    if "footer = ttk.Frame(frame)" not in render_src:
        failures.append("D: the footer is not on the dialog frame (buttons could scroll out of reach)")

    # E) the shared placer caps the dialog to the screen instead of growing to content height.
    if "max_height" not in place_src or "min(" not in place_src or "screen_height" not in place_src:
        failures.append("E: _show_centered_dialog does not cap the dialog height to the screen")
    if "winfo_reqheight()" in place_src and "min(" not in place_src:
        failures.append("E: _show_centered_dialog still sizes to the raw requested height (no screen cap)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Advanced Surface dialog screen-fit + scrollable tabs")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Advanced Surface dialog fits the screen and scrolls its tabs (no overflow under the top bar)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
