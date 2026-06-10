#!/usr/bin/env python3
"""Display-free guard for bugs/0052: the imported LED overlay body must wear the
shared grey-blue glass palette, not the old saturated amber.

The LED was `(0.95, 0.62, 0.16)` amber -- it read as "why is only the LED
orange, different from the rest?" and the gold face-hover edge was invisible on
it. The color is duplicated across two draw paths (an earlier single-path fix
was not enough), so this checks BOTH at the source level:

  1. `Open3DStepOverlayRefreshService._step_overlay_display_spec` -- the
     per-label partial refresh; and
  2. `Open3DSceneRefreshService.refresh_scene` -- the inline per-label spec list
     used by the full `refresh_from_editor` rebuild (the live render path).

A grey-blue LED keeps the gold hover (1.0, 0.78, 0.08) high-contrast.

Run: `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_overlay_palette`
Exit: 0 = pass, 1 = the amber regressed (or the LED line drifted).
"""
from __future__ import annotations

import inspect
import re

from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.open3d_step_overlay_refresh import (
    Open3DStepOverlayRefreshService,
)

AMBER = "(0.95, 0.62, 0.16)"
GREY_BLUE = "(0.30, 0.36, 0.46)"  # shared with the lens overlay


def _led_spec_line(source: str) -> str | None:
    """Return the source line that defines the ``led`` overlay color."""
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('"led"') or stripped.startswith('("led"'):
            return stripped
    return None


def main() -> int:
    failures: list[str] = []
    paths = {
        "partial refresh (_step_overlay_display_spec)": inspect.getsource(
            Open3DStepOverlayRefreshService._step_overlay_display_spec
        ),
        "full refresh (refresh_scene)": inspect.getsource(
            Open3DSceneRefreshService.refresh_scene
        ),
    }
    for name, source in paths.items():
        # The amber may legitimately appear in an explanatory comment, but never
        # on the actual `led` spec line.
        led_line = _led_spec_line(source)
        if led_line is None:
            failures.append(f"{name}: no `led` overlay spec line found")
            continue
        if AMBER.replace(" ", "") in led_line.replace(" ", ""):
            failures.append(f"{name}: LED is still amber -> {led_line}")
        if GREY_BLUE.replace(" ", "") not in led_line.replace(" ", ""):
            failures.append(
                f"{name}: LED is not the shared grey-blue {GREY_BLUE} -> {led_line}"
            )

    if failures:
        for message in failures:
            print(f"[FAIL] {message}")
        return 1
    print("LED overlay palette validation passed (grey-blue in both draw paths).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
