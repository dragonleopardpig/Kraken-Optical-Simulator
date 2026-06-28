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


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.panels.main_advanced_surface_dialog import MainAdvancedSurfaceDialog
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    failures: list[str] = []
    open_src = inspect.getsource(MainAdvancedSurfaceDialog.open)
    place_src = inspect.getsource(LayoutTableWorkbenchMixin._show_centered_dialog)

    # A) tabs are scroll canvases with an inner frame placed via create_window.
    if "def make_scroll_tab" not in open_src:
        failures.append("A: no make_scroll_tab helper -- tabs are not scrollable")
    if "tk.Canvas(" not in open_src or "create_window(" not in open_src or "Scrollbar(" not in open_src:
        failures.append("A: a tab body is not a Canvas+Scrollbar+create_window scroll region")

    # B) wheel binds mouse + X11/touchpad, recursively over every field.
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        if seq not in open_src:
            failures.append(f"B: wheel handler does not bind {seq} (mouse + touchpad)")
    if "bind_recursive" not in open_src and "_bind" not in open_src:
        failures.append("B: wheel is not bound recursively on the tab's children")

    # C) every content tab goes through make_scroll_tab -- not a raw notebook.add(frame).
    for needed in ('make_scroll_tab("Shape Params")', "make_scroll_tab(group_name)", 'make_scroll_tab("Custom Surface")'):
        if needed not in open_src:
            failures.append(f"C: a content tab is not scrollable -- missing {needed}")
    if "notebook.add(shape_frame" in open_src or "notebook.add(custom_frame" in open_src:
        failures.append("C: a content tab is still added to the notebook as a raw (unscrolled) frame")

    # D) the footer (Apply/Cancel) is on the window, not inside a scrolled tab.
    if "footer.grid(row=2" not in open_src:
        failures.append("D: the footer is not gridded on the window row 2 (buttons could scroll out of reach)")

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
