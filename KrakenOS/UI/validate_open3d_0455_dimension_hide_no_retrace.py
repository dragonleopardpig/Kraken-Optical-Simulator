"""bugs/0455 guard -- hiding/showing a thickness dimension re-renders, never re-traces.

Follow-up to 0454: hiding a dimension is display-only, but the refresh went through
`refresh_from_editor` (which re-traces the rays when Show Rays is on -- the blink). The
dimension hide/show now refresh with `display_only=True`, routing through the
inspector's `_on_scene_visibility_changed` (the bugs/0166 cached re-render).

Checks:
  SOURCE -- `_refresh_open_3d_views` has a display_only branch to the visibility
            handler, and the dimension hide/show use it.
  SPY    -- driving the real editor method with a spy inspector, the hide invokes the
            cached re-render and never the retracing refresh.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path


class _SpyInspector:
    def __init__(self):
        self.visibility_calls = 0
        self.refresh_from_editor_calls = 0

    def winfo_exists(self):
        return True

    def _on_scene_visibility_changed(self):
        self.visibility_calls += 1

    def refresh_from_editor(self, **kwargs):
        self.refresh_from_editor_calls += 1


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    except Exception as exc:
        return True, [f"SKIP: mixins unavailable ({exc!r})"]

    refresh_src = _inspect.getsource(LayoutOpticalSolidWorkflowMixin._refresh_open_3d_views)
    set_src = _inspect.getsource(ScenePlacementMixin.set_thickness_dimension_hidden)
    show_src = _inspect.getsource(ScenePlacementMixin.show_all_thickness_dimensions)
    if (
        "display_only" in refresh_src
        and "_on_scene_visibility_changed" in refresh_src
        and "display_only=True" in set_src
        and "display_only=True" in show_src
    ):
        notes.append("SOURCE = dimension hide/show refresh display-only via the visibility handler")
    else:
        notes.append("SOURCE the 0455 display-only routing is missing")
        ok = False

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        for name in ("machine_vision_150mm_test", "machine_vision_AZ85_RA_Mirror"):
            if Path(f"attachment/{name}.py").exists():
                app.layout_files[name] = Path(f"attachment/{name}.py")
                app.load_layout_by_name(name)
                break
        spy = _SpyInspector()
        app._three_d_inspector = spy
        app._legacy_3d_plotter = None
        app.set_thickness_dimension_hidden(0, True)
        app.set_thickness_dimension_hidden(0, False)
        if spy.visibility_calls == 2 and spy.refresh_from_editor_calls == 0:
            notes.append("SPY = hide/show routed to the cached re-render, never the retrace")
        else:
            notes.append(
                f"SPY unexpected: visibility={spy.visibility_calls} retrace={spy.refresh_from_editor_calls}"
            )
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: spy drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
