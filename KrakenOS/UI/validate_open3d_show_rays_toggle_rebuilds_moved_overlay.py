#!/usr/bin/env python3
"""Display-free regression for bugs/0087: a Show-Rays toggle must NOT reuse a
scene whose preview trace has been dirtied by moving an imported STEP overlay.

The bug (flag_20260617_213656 + the 211828/211917/211953 family): an imported
beam-splitter overlay marked physics-preview-ready is a live-trace element, so
the cached scene bundle holds its on-axis live-trace row. A live carry-drag moves
the body actors via AddPosition WITHOUT rebuilding that bundle, then toggling Show
Rays off takes the fast `can_reuse_current_scene_for_show_rays` path and reuses
the stale bundle -- redrawing the body at its pre-drag, on-axis pose while the
placement offset stays where the user dragged it. Captured proof
(flag_20260617_213656_719): `placement_offset_xyz` y=42.9 but the drawn body sits
on-axis (y in [-25, 25]) with no axis anchor -- the placement survived, the
display reverted ("snap back to optical axis when ray off" + the floating gizmo).

The fix: `can_reuse_current_scene_for_show_rays` returns False when the editor's
`_preview_scene_trace_dirty` flag is set (a placement/trace change), so the toggle
falls through to a full rebuild that redraws the overlay at its live placement.

This drives the real service method against a lightweight stub editor/inspector,
so it runs with no Xvfb and no VTK. The end-to-end body-follows-drag proof (boots
the inspector) lives in the repro referenced by bugs/0087.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_show_rays_toggle_rebuilds_moved_overlay

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value


def _service(*, dirty: bool, showing_rays: bool):
    from KrakenOS.UI.services.open3d_trace_refresh import Open3DTraceRefreshService

    editor = SimpleNamespace(
        _preview_scene_trace_dirty=bool(dirty),
        # No optical STEP path -> has_traceable_step_overlays() is False, so the
        # showing-rays branch is inert; we exercise the dirty gate, which runs first.
        _step_path_for_label=lambda label: None,
    )
    inspector = SimpleNamespace(
        _current_system=object(),
        _current_rays=object(),
        _current_scene_bundle=object(),
        _current_row_names=["0", "1"],
        show_rays_var=_Var(bool(showing_rays)),
    )
    return Open3DTraceRefreshService(editor), inspector


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # 1) Clean scene, rays-off toggle -> reuse is allowed (fast path preserved).
    svc, insp = _service(dirty=False, showing_rays=False)
    if not svc.can_reuse_current_scene_for_show_rays(insp):
        failures.append("FAIL: a clean scene was NOT reusable -- fast Show-Rays toggle broken")

    # 2) Dirtied scene (overlay moved), rays-off toggle -> MUST rebuild, not reuse.
    svc, insp = _service(dirty=True, showing_rays=False)
    if svc.can_reuse_current_scene_for_show_rays(insp):
        failures.append("FAIL: a dirtied scene was reused on Show-Rays off -- moved overlay would snap back (bugs/0087)")

    # 3) Dirtied scene, rays-on toggle -> also must not reuse.
    svc, insp = _service(dirty=True, showing_rays=True)
    if svc.can_reuse_current_scene_for_show_rays(insp):
        failures.append("FAIL: a dirtied scene was reused on Show-Rays on (bugs/0087)")

    # 4) Missing cached bundle -> never reusable (pre-existing guard intact).
    svc, insp = _service(dirty=False, showing_rays=False)
    insp._current_scene_bundle = None
    if svc.can_reuse_current_scene_for_show_rays(insp):
        failures.append("FAIL: reused with no cached scene bundle")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0087 Show-Rays toggle reuse gate")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Show-Rays toggle rebuilds after a moved overlay; clean scenes still fast-reuse (bugs/0087)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
