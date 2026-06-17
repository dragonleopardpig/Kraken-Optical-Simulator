#!/usr/bin/env python3
"""Display-free regression for bugs/0089: right-clicking a snapped STEP overlay
must still offer Promote / face-assign even when the click lands on its transient
live-trace ROW actor.

After an axis-snap marks an imported STEP overlay physics-preview-ready, it is
folded into the trace and ALSO drawn as a transient live-trace row (rays on). A
right-click that hits that row actor resolves no `step_label` and the row is not
file-backed, so `_show_surface_function_context_menu` fell through to "requires a
file-backed CAD/STL row" -- the Promote to Optical Element + "Promote and set
<face>" options disappeared (user: "after snapping to optical axis, right click
don't have option to direct assign the face, also missing the promotion option").

Fix: `_right_click_pick_context` calls `_resolve_picked_step_overlay`, which maps
a picked live-trace overlay row back to its STEP-overlay label (and drops the row
index) so the overlay menu still appears.

Drives the real `Kraken3DInspector._resolve_picked_step_overlay` against a stub
self (no Xvfb / VTK). The full right-click VTK pick can't be driven headlessly;
confirm the menu in-app.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_right_click_live_trace_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import types
from types import SimpleNamespace


def _stub(live_by_row):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    stub = SimpleNamespace(_live_trace_step_overlay_label_by_row=lambda: dict(live_by_row))
    stub._resolve_picked_step_overlay = types.MethodType(
        Kraken3DInspector._resolve_picked_step_overlay, stub
    )
    return stub


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # 1) live-trace overlay row picked (no step_label) -> mapped to the overlay label, row dropped.
    stub = _stub({4: "optical"})
    sl, ri = stub._resolve_picked_step_overlay(None, 4)
    if sl != "optical" or ri is not None:
        failures.append(f"FAIL: live-trace row not mapped to overlay (got step_label={sl!r}, row={ri!r})")

    # 2) a row that is NOT a live-trace overlay -> unchanged (real CAD/STL row keeps its row menu).
    sl, ri = stub._resolve_picked_step_overlay(None, 7)
    if sl is not None or ri != 7:
        failures.append(f"FAIL: non-overlay row was altered (got step_label={sl!r}, row={ri!r})")

    # 3) already a step overlay actor -> unchanged.
    sl, ri = stub._resolve_picked_step_overlay("optical", 4)
    if sl != "optical" or ri != 4:
        failures.append(f"FAIL: explicit step_label changed (got step_label={sl!r}, row={ri!r})")

    # 4) no row picked -> unchanged.
    sl, ri = stub._resolve_picked_step_overlay(None, None)
    if sl is not None or ri is not None:
        failures.append(f"FAIL: empty pick altered (got step_label={sl!r}, row={ri!r})")

    # 5) no live-trace rows at all -> unchanged.
    empty = _stub({})
    sl, ri = empty._resolve_picked_step_overlay(None, 4)
    if sl is not None or ri != 4:
        failures.append(f"FAIL: row altered with no live-trace overlays (got step_label={sl!r}, row={ri!r})")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0089 right-click live-trace overlay -> overlay menu")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] right-click on a live-trace STEP overlay row resolves to the overlay menu (bugs/0089)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
