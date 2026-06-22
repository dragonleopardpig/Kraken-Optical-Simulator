#!/usr/bin/env python3
"""Display-free guard for the Face Editor right-hand panel scrollability.

The "Assign CAD/STL Optical Faces" (Face Editor) dialog's right-hand assignment
form is taller than the dialog, so it must live in a vertical scroll canvas --
otherwise the lower controls overflow off the bottom with no scrollbar. The fix
wraps the ``editor`` pane in a ``tk.Canvas`` (+ auto-hiding ``Scrollbar``) and
binds wheel scrolling for BOTH the mouse and the touchpad, recursively on every
control so hovering any field scrolls.

The dialog needs a real Tk root + a promoted STL row to render, which the penta
harness has no display for, so this is a source-structure guard:
  A. the editor pane is wrapped in a Canvas with a vertical Scrollbar and the inner
     form is placed via ``create_window``;
  B. the wheel handler binds ``<MouseWheel>`` AND ``<Button-4>``/``<Button-5>``
     (mouse + X11/touchpad) and is applied recursively (``_bind_editor_wheel``);
  C. the Save/Close footer stays on the dialog window (not inside the scrolled
     pane) so it is always visible.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_face_editor_scrollable

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.panels.main_optical_solid_face_roles_dialog import (
        MainOpticalSolidFaceRolesDialog,
    )

    failures: list[str] = []
    src = inspect.getsource(MainOpticalSolidFaceRolesDialog._open_optical_solid_faces_for_row)

    # A) the editor pane is a scroll canvas with an inner frame.
    if "tk.Canvas(editor_host" not in src and "Canvas(editor_host" not in src:
        failures.append("FAIL: the editor pane must be wrapped in a Canvas (editor_host -> Canvas)")
    if "create_window(" not in src or "window=editor" not in src:
        failures.append("FAIL: the inner editor form must be placed in the canvas via create_window")
    if "Scrollbar(editor_host" not in src:
        failures.append("FAIL: the editor pane needs a vertical Scrollbar")
    if "scrollregion" not in src:
        failures.append("FAIL: the canvas scrollregion must be configured to the form size")

    # B) wheel scroll for mouse AND touchpad, bound recursively.
    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
        if seq not in src:
            failures.append(f"FAIL: the editor scroll must bind {seq} (mouse + X11/touchpad)")
    if "_bind_editor_wheel" not in src:
        failures.append(
            "FAIL: the wheel handler must be bound recursively on every control "
            "(_bind_editor_wheel) so hovering any field scrolls")

    # C) the Save/Close footer is on the dialog window, not inside the scrolled pane.
    if "footer = ttk.Frame(window" not in src:
        failures.append("FAIL: the action footer (Save Roles/Close) must stay on the window (always visible)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Face Editor right-hand panel is scrollable (mouse + touchpad)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Face Editor right-hand panel scrolls (canvas + auto scrollbar; mouse wheel + "
          "touchpad, recursive)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
