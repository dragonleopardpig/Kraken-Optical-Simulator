"""bugs/0454 -- the amber Object->LED thickness overlay must hide on right-click.

flag_20260727_160952 ("right click: unable hide the manual thickness overlay (gold
color)"): the amber "Object -> LED" dimension keys the hidden set under
LED_OBJECT_EDGE_DIM_ROW (-7), and the right-click menu toggles it there -- but
`_emit_led_object_edge_dimension` was called unconditionally, so unlike the blue
per-row arrows (gated by `_thickness_dimension_is_hidden`) it re-emitted every frame
and "Hide" did nothing. The builder now honours the hidden set.

Display-free: the gate sits before any render call, so with a shim inspector the
HIDDEN path returns 0 without touching the renderer, while the visible path proceeds
past the gate. The hidden-set toggle round-trip and the menu-header naming are checked
too. (The live draw + right-click pick are the in-app eyeball.)

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0454_hide_object_led_dimension.py
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


class _ShimSelf:
    """Stand-in ``self`` for the unbound builder: the hidden gate reads only
    ``self.editor`` and ``self.LED_OBJECT_EDGE_DIM_ROW`` before any render call.
    Past the gate the builder reaches render-only helpers this shim lacks -- which is
    exactly how the VISIBLE case proves it ran past the gate."""

    def __init__(self, editor, led_row):
        self.editor = editor
        self.LED_OBJECT_EDGE_DIM_ROW = led_row


def _load_led_scene(app):
    for name in ("machine_vision_150mm_test", "machine_vision_150mm_GN", "machine_vision_AZ85_RA_Mirror"):
        p = Path(f"attachment/{name}.py")
        if p.exists():
            app.layout_files[name] = p
            app.load_layout_by_name(name)
            if getattr(app, "imported_led_step_path", None) is not None:
                return name
    return None


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    LED_ROW = Open3DThicknessDimensionService.LED_OBJECT_EDGE_DIM_ROW
    check("LED dimension keys a distinct synthetic row (not a real S# row)", LED_ROW < 0, str(LED_ROW))

    # SOURCE: the gate exists and precedes the render emit.
    src = _inspect.getsource(Open3DThicknessDimensionService._emit_led_object_edge_dimension)
    gate = "_thickness_dimension_is_hidden(self.LED_OBJECT_EDGE_DIM_ROW)"
    check("builder gates on the hidden set", gate in src)
    if gate in src and "_emit_span_dimension" in src:
        check("the hidden gate runs BEFORE the render emit", src.index(gate) < src.index("_emit_span_dimension"))

    # MENU: the header names the LED row instead of "S-7".
    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        menu_src = _inspect.getsource(Kraken3DInspector._show_thickness_dimension_menu)
        check("menu header names the Object -> LED dimension", "Object → LED dimension" in menu_src)
    except Exception as exc:
        check("menu header source available", False, repr(exc)[:60])

    app = KrakenLayoutEditor()
    try:
        name = _load_led_scene(app)
        if name is None:
            print("SKIP: no LED-bearing scene present (gitignored attachment) -- source checks stand")
            return 1 if FAILURES else 0

        # Toggle round-trip (display-free: the hidden set is plain editor state).
        app.show_all_thickness_dimensions()
        check("clean start: LED dimension not hidden", not app._thickness_dimension_is_hidden(LED_ROW))
        app.toggle_thickness_dimension_hidden(LED_ROW)
        check("right-click Hide marks it hidden", app._thickness_dimension_is_hidden(LED_ROW))
        check("hiding the LED row does NOT hide a real S0 row", not app._thickness_dimension_is_hidden(0))

        emit = Open3DThicknessDimensionService._emit_led_object_edge_dimension
        shim = _ShimSelf(app, LED_ROW)
        kw = dict(
            base_offset=10.0, scene_span=500.0,
            view_normal=(0.0, 1.0, 0.0), screen_up=(0.0, 1.0, 0.0), screen_right=(1.0, 0.0, 0.0),
        )
        # HIDDEN: the gate returns 0 before any render call (the shim self survives).
        hidden_result = emit(shim, None, **kw)
        check("HIDE takes effect: builder emits nothing (returns 0) when hidden", hidden_result == 0,
              f"result={hidden_result}")

        # VISIBLE: the builder proceeds PAST the gate (the shim then raises in the render
        # emit -- proving the gate did not suppress a visible dimension).
        app.toggle_thickness_dimension_hidden(LED_ROW)
        if not (float(getattr(app, "led_object_edge_distance_mm", 0.0) or 0.0) > 1e-6):
            app.led_object_edge_distance_mm = 200.0
        passed_gate = False
        try:
            emit(shim, None, **kw)
        except Exception:
            passed_gate = True  # reached a render-only helper -> the gate let it through
        check("VISIBLE: builder runs past the gate when not hidden", passed_gate)
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- the amber Object->LED dimension honours right-click Hide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
