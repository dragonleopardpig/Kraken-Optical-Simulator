#!/usr/bin/env python3
"""Display-free regression for bugs/0091: the Quick-Estimation plane menu must not
hijack a right-click on a STEP overlay (incl. its transient live-trace row).

`_surface_row_under_cursor` returns the picked actor's SCENE row index. A
physics-preview-ready STEP overlay is drawn as a live-trace row INSERTED into the
traced rows, so its scene index (e.g. 4) does not index `editor.rows` (where row 4
is the Image). `_maybe_show_quick_estimation_role_menu` then read
`editor.rows[4].surface == "Image"` and popped the QE role menu -- returning before
the right-click handler logs, so a right-click on the beam-splitter cube showed a
menu with no Promote / face-assign (user: "right click no promotion option").

Fix: `_optical_surface_row_for_actor` returns None for a STEP-overlay actor or a
live-trace overlay row, so the QE plane menu only claims genuine Object/Image
surfaces and the cube's right-click falls through to the overlay menu.

Drives the real `Kraken3DInspector._optical_surface_row_for_actor` against a stub
self (no Xvfb / VTK). The full right-click VTK pick can't be driven headlessly;
confirm the menu in-app.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_qe_menu_skips_step_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types
from types import SimpleNamespace


def _stub():
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    stub = SimpleNamespace(
        _actor_step_map={"step_overlay_actor": "optical"},
        _actor_row_map={"step_overlay_actor": None, "live_trace_row_actor": 4, "image_actor": 5, "lens_actor": 2},
        _live_trace_step_overlay_label_by_row=lambda: {4: "optical"},
    )
    stub._optical_surface_row_for_actor = types.MethodType(
        Kraken3DInspector._optical_surface_row_for_actor, stub
    )
    return stub


def run_checks() -> tuple[bool, list[str]]:
    stub = _stub()
    failures: list[str] = []

    # STEP overlay actor -> not a surface row (QE menu must not claim it).
    if stub._optical_surface_row_for_actor("step_overlay_actor") is not None:
        failures.append("FAIL: STEP overlay actor treated as a surface row (QE menu would hijack the right-click)")

    # Transient live-trace overlay row -> not a surface row.
    if stub._optical_surface_row_for_actor("live_trace_row_actor") is not None:
        failures.append("FAIL: live-trace overlay row treated as a surface row (its scene index collides with editor Image)")

    # Genuine optical/Image surface actor -> its row index.
    if stub._optical_surface_row_for_actor("image_actor") != 5:
        failures.append("FAIL: genuine Image surface actor not resolved to its row")
    if stub._optical_surface_row_for_actor("lens_actor") != 2:
        failures.append("FAIL: genuine lens surface actor not resolved to its row")

    # Unknown / empty pick -> None.
    if stub._optical_surface_row_for_actor(None) is not None:
        failures.append("FAIL: None actor did not resolve to None")
    if stub._optical_surface_row_for_actor("nope") is not None:
        failures.append("FAIL: unknown actor did not resolve to None")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0091 QE plane menu hijacks STEP-overlay right-click")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Quick-Estimation plane menu skips STEP overlays; right-click reaches the overlay menu (bugs/0091)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
