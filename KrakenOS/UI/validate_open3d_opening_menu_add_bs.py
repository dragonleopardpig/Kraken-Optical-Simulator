#!/usr/bin/env python3
"""Display-free guard: the pinned-opening menu offers "Add Beam Splitter to LED" (bugs/0339).

User directive (imported LED, latest flag):
  "after snapping the CA to optical axis, right click add BS Cube or Plate not working."
  ... "The snapping is not from the right click menu."

Root cause:
  The one-click "Add Beam Splitter to LED (Cube/Plate)" commands live only in the
  whole-body STEP overlay menu. But once a clear-aperture OPENING is PINNED
  (bugs/0334), every right-click is diverted to ``_show_selected_opening_context_menu``
  (the ``_has_selected_step_opening()`` guard in ``_show_surface_function_context_menu``).
  A snap performed from a NON-right-click path leaves the opening pinned, so the user
  right-clicks to add a beam splitter and only ever sees the opening menu -- which had
  no "Add BS" item. "Not working."

Fix:
  When the pinned opening belongs to the LED, the opening menu now also offers
  "Add Beam Splitter to LED (Cube)" and "(Plate)" -- routing to the same
  ``_add_beam_splitter_to_led_from_context`` pipeline. The pinned opening IS the LED
  clear aperture the BS centres on, so it is reachable regardless of pin state.

What it checks
--------------
  1. Behavioural: build the opening menu for a pinned LED opening (fake Tk) -> both
     "Add Beam Splitter to LED (Cube)" and "(Plate)" labels are present.
  2. Behavioural: build it for a NON-LED overlay opening -> NO "Add BS" labels.
  3. Source contract: the method gates the BS items on ``step_label == "led"`` and
     routes them to ``_add_beam_splitter_to_led_from_context``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_opening_menu_add_bs

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


class _FakeMenu:
    def __init__(self, *a, **k):
        self.items: list[tuple[str, object]] = []

    def add_command(self, label=None, **k):
        self.items.append(("command", label))

    def add_separator(self, **k):
        self.items.append(("separator", None))

    def add_cascade(self, label=None, **k):
        self.items.append(("cascade", label))

    def labels(self) -> list[str]:
        return [str(lbl) for kind, lbl in self.items if kind == "command" and lbl is not None]


def _build_opening_menu(label: str) -> list[str]:
    """Return the command labels the opening menu builds for a pinned ``label`` opening."""
    import KrakenOS.UI.services.open3d_face_assignment as fa_mod
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    captured: dict[str, object] = {}
    svc = types.SimpleNamespace(
        _selected_opening_label=label,
        _selected_opening_center=np.asarray([1.0, 2.0, 3.0]),
        _selected_opening_normal=np.asarray([0.0, 0.0, 1.0]),
        _selected_opening_face_id="F266",
        editor=types.SimpleNamespace(
            _step_overlay_display_label=lambda s: str(s).upper(),
            step_clear_aperture=lambda s: None,
        ),
    )
    svc._show_selected_opening_context_menu = types.MethodType(FA._show_selected_opening_context_menu, svc)
    svc._popup_context_menu = types.MethodType(
        lambda self, menu, event: captured.__setitem__("menu", menu), svc
    )

    orig_menu = fa_mod.tk.Menu
    fa_mod.tk.Menu = lambda *a, **k: _FakeMenu()
    try:
        ok = svc._show_selected_opening_context_menu(event=types.SimpleNamespace(x=0, y=0, x_root=0, y_root=0))
    finally:
        fa_mod.tk.Menu = orig_menu
    if not ok or "menu" not in captured:
        return []
    return captured["menu"].labels()


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # 1. LED opening -> both Add BS items present.
    led_labels = _build_opening_menu("led")
    if not led_labels:
        failures.append("FAIL(1): the opening menu failed to build for a pinned LED opening")
    if "Add Beam Splitter to LED (Cube)" not in led_labels:
        failures.append(f"FAIL(1): LED opening menu must offer 'Add Beam Splitter to LED (Cube)', got {led_labels}")
    if "Add Beam Splitter to LED (Plate)" not in led_labels:
        failures.append(f"FAIL(1): LED opening menu must offer 'Add Beam Splitter to LED (Plate)', got {led_labels}")

    # 2. Non-LED overlay opening -> no Add BS items (the pipeline is LED-only).
    other_labels = _build_opening_menu("optical")
    if any("Add Beam Splitter" in lbl for lbl in other_labels):
        failures.append(f"FAIL(2): a non-LED opening menu must NOT offer Add Beam Splitter, got {other_labels}")

    # 3. Source contract: LED gate + routing to the BS pipeline.
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as FA

    src = inspect.getsource(FA._show_selected_opening_context_menu)
    if 'step_label == "led"' not in src:
        failures.append("FAIL(3): the opening menu must gate the Add-BS items on step_label == 'led'")
    if '_add_beam_splitter_to_led_from_context("cube")' not in src:
        failures.append("FAIL(3): the opening menu must route the Cube item to _add_beam_splitter_to_led_from_context")
    if '_add_beam_splitter_to_led_from_context("plate")' not in src:
        failures.append("FAIL(3): the opening menu must route the Plate item to _add_beam_splitter_to_led_from_context")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] pinned-opening menu is missing 'Add Beam Splitter to LED'")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] a pinned LED clear-aperture opening menu offers 'Add Beam Splitter to LED "
          "(Cube/Plate)', so Add BS is reachable while an opening is pinned (post-snap)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
