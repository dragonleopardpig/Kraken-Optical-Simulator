#!/usr/bin/env python3
"""Regression guard: the main surface-table right-click context menu builds
``OpticalVariable`` instances for its tolerance-compensator / coupling /
manufacturing solve items. The class was used but never imported, so opening the
context menu on an optimization-capable row raised
``NameError: name 'OpticalVariable' is not defined`` (a Tkinter callback crash).

Importing the module does NOT catch this -- the name is referenced inside
``show_context_menu`` at call time, not at import -- so this test asserts the
symbol is resolvable in the module namespace and constructs with the exact
call-site signature used by the menu.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_context_menu_optical_variable
"""
from __future__ import annotations

import KrakenOS.UI.panels.main_context_menu as mcm


def main() -> int:
    failures: list[str] = []

    if not hasattr(mcm, "OpticalVariable"):
        failures.append(
            "main_context_menu must import OpticalVariable -- the solve submenu builds it for "
            "tolerance compensator/coupling/manufacturing items (else show_context_menu raises NameError)"
        )
    else:
        try:
            # The exact call-site signature from show_context_menu.
            var = mcm.OpticalVariable(1, "thickness", 0.0, 1.0, name="S1 Thickness")
            if var.surface_index != 1 or var.parameter != "thickness" or var.name != "S1 Thickness":
                failures.append(f"OpticalVariable fields unexpected: {var!r}")
        except Exception as exc:  # pragma: no cover - signature drift
            failures.append(f"OpticalVariable construction with the menu's signature failed: {exc!r}")

    if failures:
        print("FAIL: context-menu OpticalVariable guard")
        for f in failures:
            print(f"  ! {f}")
        return 1
    print("PASS: main_context_menu resolves and builds OpticalVariable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
