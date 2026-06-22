#!/usr/bin/env python3
"""Display-free guard for bugs/0102: the Scene Components tree right-click offers
the SAME element-level CAD actions as the 3D-canvas right-click, via one shared
helper so the two menus never drift.

Why it exists (user's two reasons):
  1. the 3D-canvas right-click is slow -- after the click it resolves the exact
     face under the cursor (runtime mesh rebuild + brute-force ray-triangle pick +
     traced-ray scan), 12 s on the first click / ~1 s warm. The tree menu is keyed
     by the already-known element, so it skips that pipeline entirely (instant).
  2. when bodies overlap, the canvas pick returns the front-most actor, so you
     can't reach the body underneath without hiding the front one first. The tree
     lists every element by name -> pick the one underneath directly.

What it checks:
  A. ``append_element_context_actions`` adds the right element-level commands for a
     STEP overlay -- Promote/Glue/Resize for the generic "optical" overlay, and
     NO "Promote" for a decoration (led/camera, bugs/0101), while still offering
     Glue/Resize; an unknown label adds nothing and returns False.
  B. the helper handles file-backed / promoted rows (Open Face Editor, Unpromote,
     Row Actions) -- source check (a real cascade needs a tk master).
  C. BOTH the 3D-canvas menu (``_show_surface_function_context_menu``) and the tree
     menu (``Open3DStepAdminPanel._show_element_context_menu``) call the shared
     helper, so they stay in sync.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_tree_element_context_menu

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace


class _FakeMenu:
    """Records the labels a menu builder adds (tk-free)."""

    def __init__(self) -> None:
        self.labels: list[str] = []

    def add_command(self, label=None, **_kw) -> None:
        self.labels.append(str(label))

    def add_separator(self) -> None:
        self.labels.append("---")

    def add_cascade(self, label=None, **_kw) -> None:
        self.labels.append(str(label))


def _build_service():
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    editor = SimpleNamespace(
        _step_overlay_display_label=lambda lbl: str(lbl),
        _step_path_for_label=lambda lbl: None,  # -> BS<->LED glue unavailable
        optical_led_glued=lambda: False,
        rows=[],
        _file_backed_stl_row_at=lambda i: None,
        _is_any_promoted_optical_solid_row=lambda r: False,
        open_optical_solid_face_role_editor=lambda *a, **k: None,
    )
    inspector = SimpleNamespace(
        editor=editor,
        status_var=SimpleNamespace(set=lambda *a, **k: None),
        append_debug=lambda *a, **k: None,
    )
    return Open3DFaceAssignmentService(inspector)


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    # A) Behavioral: the generic "optical" overlay gets the full element menu.
    svc = _build_service()
    m = _FakeMenu()
    added = svc.append_element_context_actions(m, step_label="optical")
    if not added:
        failures.append("FAIL: optical overlay added no element actions")
    for need in ("Promote to Optical Element", "Glue STEP to Surrogate"):
        if need not in m.labels:
            failures.append(f"FAIL: optical overlay menu missing {need!r} (labels={m.labels})")
    if not any("Resize" in lbl for lbl in m.labels):
        failures.append(f"FAIL: optical overlay menu missing Resize (labels={m.labels})")

    # A) Decoration (led): Glue/Resize yes, Promote NO (bugs/0101 holds here too).
    m2 = _FakeMenu()
    svc.append_element_context_actions(m2, step_label="led")
    if "Promote to Optical Element" in m2.labels:
        failures.append(f"FAIL: led decoration must NOT offer Promote (labels={m2.labels})")
    if "Glue STEP to Surrogate" not in m2.labels:
        failures.append(f"FAIL: led decoration should still offer Glue to Surrogate (labels={m2.labels})")

    # A) Unknown label adds nothing.
    m3 = _FakeMenu()
    res = svc.append_element_context_actions(m3, step_label="not-a-label")
    if res or m3.labels:
        failures.append(f"FAIL: unknown overlay label should add nothing (res={res}, labels={m3.labels})")

    # B) The helper covers the row element actions (source check; a live cascade
    #    needs a tk master so we don't build it headless).
    helper_src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    for token in ("Open Face Editor", "Unpromote to STEP overlay", "_build_row_actions_cascade"):
        if token not in helper_src:
            failures.append(f"FAIL: shared helper lost the row action {token!r}")

    # C) Both menus call the SAME helper (no drift).
    canvas_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "append_element_context_actions" not in canvas_src:
        failures.append("FAIL: the 3D-canvas menu no longer delegates to append_element_context_actions")

    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel

    tree_src = inspect.getsource(Open3DStepAdminPanel._show_element_context_menu)
    if "append_element_context_actions" not in tree_src:
        failures.append(
            "FAIL: the Scene Components tree menu does not call append_element_context_actions "
            "(tree right-click would not match the 3D canvas)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0102 tree right-click must mirror the 3D-canvas element actions")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] tree right-click mirrors the 3D-canvas element-level actions via one shared helper (bugs/0102)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
