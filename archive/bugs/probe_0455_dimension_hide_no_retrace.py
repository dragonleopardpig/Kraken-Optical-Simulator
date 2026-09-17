"""bugs/0455 -- hiding/showing a thickness dimension re-renders, never re-traces.

Follow-up to 0454 (the user: "after clicking hide, the ray disappear and re-trace, is
it correct behaviour?"). Hiding a dimension is a pure display-layer change, but
`set_thickness_dimension_hidden` refreshed via `_refresh_open_3d_views()`, whose
embedded-inspector branch calls `refresh_from_editor` -- which, with Show Rays ON,
kicks a full async re-trace (the ray blink). It now refreshes with `display_only=True`,
routing through the inspector's `_on_scene_visibility_changed` (the bugs/0166 cached
re-render), so nothing re-traces.

Display-free: a spy inspector records which refresh the hide/show invoked.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0455_dimension_hide_no_retrace.py
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


class _SpyInspector:
    """Records which 3D refresh a hide/show triggered. `_on_scene_visibility_changed`
    is the cached re-render (0166); `refresh_from_editor` is the retracing path."""

    def __init__(self):
        self.visibility_calls = 0
        self.refresh_from_editor_calls = 0

    def winfo_exists(self):
        return True

    def _on_scene_visibility_changed(self):
        self.visibility_calls += 1

    def refresh_from_editor(self, **kwargs):
        self.refresh_from_editor_calls += 1


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    # SOURCE: the refresh helper has a display_only branch to the cached re-render, and
    # the dimension hide/show use it.
    from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    refresh_src = _inspect.getsource(LayoutOpticalSolidWorkflowMixin._refresh_open_3d_views)
    check("_refresh_open_3d_views has a display_only branch to _on_scene_visibility_changed",
          "display_only" in refresh_src and "_on_scene_visibility_changed" in refresh_src)
    set_hidden_src = _inspect.getsource(ScenePlacementMixin.set_thickness_dimension_hidden)
    check("set_thickness_dimension_hidden refreshes display_only", "display_only=True" in set_hidden_src)
    show_all_src = _inspect.getsource(ScenePlacementMixin.show_all_thickness_dimensions)
    check("show_all_thickness_dimensions refreshes display_only", "display_only=True" in show_all_src)

    # BEHAVIORAL: drive the real editor method with a spy inspector.
    app = KrakenLayoutEditor()
    try:
        # A minimal layout so a real row exists to (un)hide; the scene need not render.
        scene = None
        for name in ("machine_vision_150mm_test", "machine_vision_AZ85_RA_Mirror"):
            if Path(f"attachment/{name}.py").exists():
                scene = name
                break
        if scene is not None:
            app.layout_files[scene] = Path(f"attachment/{scene}.py")
            app.load_layout_by_name(scene)

        spy = _SpyInspector()
        app._three_d_inspector = spy
        app._legacy_3d_plotter = None

        app.set_thickness_dimension_hidden(0, True)
        check("hide routed to the cached re-render (visibility handler), once",
              spy.visibility_calls == 1, f"visibility={spy.visibility_calls}")
        check("hide did NOT call the retracing refresh_from_editor",
              spy.refresh_from_editor_calls == 0, f"retrace_calls={spy.refresh_from_editor_calls}")

        app.set_thickness_dimension_hidden(0, False)
        check("show also re-renders (no retrace)",
              spy.visibility_calls == 2 and spy.refresh_from_editor_calls == 0,
              f"visibility={spy.visibility_calls} retrace={spy.refresh_from_editor_calls}")

        app.set_thickness_dimension_hidden(0, True)  # re-hide so show-all has work
        app.show_all_thickness_dimensions()
        check("show-all re-renders (no retrace)",
              spy.refresh_from_editor_calls == 0, f"retrace_calls={spy.refresh_from_editor_calls}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- dimension hide/show re-renders the cached scene, no ray re-trace")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
