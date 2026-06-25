"""Confirm bug 0151: editing the Object->LED distance after a carry-drag doesn't
put the LED where the user typed, because the dialog operates on the RAW
led_object_edge_distance_mm knob while the live dimension (and the LED's live
object-edge) include the additive placement_offset_xyz.z from the drag.

  live_distance = led_object_edge_distance_mm + placement_offset_z   (thickness_dims:1022)

So after a drag of offset_z, typing V sets the knob to V but the live distance
becomes V + offset_z != V.

No display needed -- pure editor state. Drives the REAL set_led_edge_distance with
the Tk dialog stubbed.

Run:  .devenv/state/venv/bin/python bugs/repro_0151_object_led_dialog.py
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

_REPO = Path(__file__).resolve().parents[1]
_LED = _REPO / "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"


def _live_distance(app) -> float:
    knob = float(getattr(app, "led_object_edge_distance_mm", 0.0) or 0.0)
    try:
        off_z = float(app._step_placement_offset_xyz("led")[2])
    except Exception:
        off_z = 0.0
    return knob + off_z


def main() -> int:
    if not _LED.exists():
        print(f"SKIP: LED STEP missing at {_LED}")
        return 0
    app = KrakenLayoutEditor()
    try:
        app.imported_led_step_path = _LED
        # An object-edge reference + a typed distance: LED edge pinned at object+200.
        app.led_step_object_edge_local_z = 0.0
        app.led_object_edge_distance_mm = 200.0
        # Now the user carry-drags the LED -71.34 in Z (the recorded drag, bug 0137).
        app.led_step_placement_offset_xyz = (22.8856, -0.0208, -71.3406)

        live_before = _live_distance(app)
        print(f"knob (led_object_edge_distance_mm) = {app.led_object_edge_distance_mm:.4g}")
        print(f"placement_offset_z                = {app._step_placement_offset_xyz('led')[2]:.4g}")
        print(f"LIVE 'Object -> LED' shown         = {live_before:.4g} mm   (this is what the dimension label reads)")

        # The user opens the dialog wanting Object->LED = 100. Stub the Tk prompt.
        typed = 100.0
        app._ask_led_edge_distance = lambda *a, **k: typed  # type: ignore[assignment]
        # set_led_edge_distance refreshes the 3D view; harmless/no-op without one.
        try:
            app.set_led_edge_distance()
        except Exception as exc:
            print("set_led_edge_distance raised (non-fatal for the assert):", repr(exc))

        live_after = _live_distance(app)
        print(f"\nUser typed Object -> LED = {typed:.4g} mm")
        print(f"knob after   = {app.led_object_edge_distance_mm:.4g}")
        print(f"offset_z after = {app._step_placement_offset_xyz('led')[2]:.4g}")
        print(f"LIVE 'Object -> LED' AFTER edit = {live_after:.4g} mm")

        ok = abs(live_after - typed) <= 1e-6
        print(f"\n{'PASS' if ok else 'BUG CONFIRMED'}: live distance "
              f"{'==' if ok else '!='} typed value "
              f"({live_after:.4g} vs {typed:.4g}); "
              f"error = {live_after - typed:+.4g} mm (== the drag offset_z)")
        return 0 if ok else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
