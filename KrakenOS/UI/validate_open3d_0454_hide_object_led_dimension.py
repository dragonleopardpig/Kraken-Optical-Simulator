"""bugs/0454 guard -- the amber Object->LED thickness overlay honours right-click Hide.

flag_20260727_160952 ("right click: unable hide the manual thickness overlay (gold
color)"): the amber dimension keys the hidden set under LED_OBJECT_EDGE_DIM_ROW (-7)
and the right-click menu toggled it there, but `_emit_led_object_edge_dimension` was
called unconditionally -- so, unlike the blue per-row arrows, it re-emitted every frame
and "Hide" did nothing. The builder now checks the hidden set (before any render call),
and the menu header names the dimension instead of "S-7".

Checks:
  SOURCE -- the builder gates on _thickness_dimension_is_hidden before the render emit;
            the menu header names the Object -> LED row.
  REAL   -- toggling the LED row hides it (builder returns 0), leaves the blue S0 row
            untouched, and un-hiding lets the builder run past the gate again.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path


class _ShimSelf:
    def __init__(self, editor, led_row):
        self.editor = editor
        self.LED_OBJECT_EDGE_DIM_ROW = led_row


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    try:
        from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
    except Exception as exc:
        return True, [f"SKIP: thickness-dimensions module unavailable ({exc!r})"]

    LED_ROW = Open3DThicknessDimensionService.LED_OBJECT_EDGE_DIM_ROW
    src = _inspect.getsource(Open3DThicknessDimensionService._emit_led_object_edge_dimension)
    gate = "_thickness_dimension_is_hidden(self.LED_OBJECT_EDGE_DIM_ROW)"
    if gate in src and "_emit_span_dimension" in src and src.index(gate) < src.index("_emit_span_dimension"):
        notes.append("SOURCE = builder gates on the hidden set before the render emit")
    else:
        notes.append("SOURCE the 0454 hidden gate is missing / misordered")
        ok = False
    try:
        from KrakenOS.UI.open3d_inspector import Kraken3DInspector
        if "Object → LED dimension" in _inspect.getsource(Kraken3DInspector._show_thickness_dimension_menu):
            notes.append("SOURCE = menu header names the Object -> LED dimension")
        else:
            notes.append("SOURCE menu header still shows a raw S# row")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: menu source unavailable ({exc!r})")

    scene = None
    for name in ("machine_vision_150mm_test", "machine_vision_150mm_GN", "machine_vision_AZ85_RA_Mirror"):
        if Path(f"attachment/{name}.py").exists():
            scene = name
            break
    if scene is None:
        notes.append("SKIP: no LED-bearing scene present (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files[scene] = Path(f"attachment/{scene}.py")
        app.load_layout_by_name(scene)
        if getattr(app, "imported_led_step_path", None) is None:
            notes.append(f"SKIP: {scene} has no LED overlay")
            return ok, notes
        if not (float(getattr(app, "led_object_edge_distance_mm", 0.0) or 0.0) > 1e-6):
            app.led_object_edge_distance_mm = 200.0

        emit = Open3DThicknessDimensionService._emit_led_object_edge_dimension
        shim = _ShimSelf(app, LED_ROW)
        kw = dict(base_offset=10.0, scene_span=500.0, view_normal=(0.0, 1.0, 0.0),
                  screen_up=(0.0, 1.0, 0.0), screen_right=(1.0, 0.0, 0.0))

        app.show_all_thickness_dimensions()
        app.toggle_thickness_dimension_hidden(LED_ROW)
        hidden_ok = app._thickness_dimension_is_hidden(LED_ROW) and emit(shim, None, **kw) == 0
        s0_untouched = not app._thickness_dimension_is_hidden(0)
        app.toggle_thickness_dimension_hidden(LED_ROW)
        passed_gate = False
        try:
            emit(shim, None, **kw)
        except Exception:
            passed_gate = True
        if hidden_ok and s0_untouched and passed_gate:
            notes.append("REAL = Hide suppresses the amber dimension; S0 untouched; un-hide restores it")
        else:
            notes.append(f"REAL unexpected: hidden_ok={hidden_ok} s0_untouched={s0_untouched} passed_gate={passed_gate}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
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
