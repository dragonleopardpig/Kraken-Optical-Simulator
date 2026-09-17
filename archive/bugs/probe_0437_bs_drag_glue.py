#!/usr/bin/env python3
"""bugs/0437 -- the BS<->LED glue is ASYMMETRIC (flag_20260726_110337).

The user dragged the BS plate down to seat it inside the LED housing and the LED
followed, "effectively cancelling the BS plate move" (the 0432 Alt-drag suspend
existed, but a PLAIN drag still carried the LED -- the old two-body symmetric
glue resurfacing). Required semantics:

  * dragging the LED (parent housing) carries the glued BS  -> assembly moves as one;
  * dragging the BS (child, seated inside the housing) moves the BS ALONE.

Drives all three BS-move primitives the drag paths use (vector row drag, per-axis
row drag, overlay drag) plus the LED-side carries, on the real AZ85 + one-click
plate BS. Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0437_bs_drag_glue.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from KrakenOS.UI.layout_editor import KrakenLayoutEditor  # noqa: E402

SCENE = Path(__file__).resolve().parents[1] / "attachment" / "machine_vision_AZ85_RA_Mirror.py"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok  " if ok else "FAIL") + f" {label}" + (f"  [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


def led_offset(app) -> np.ndarray:
    return np.asarray(app._step_placement_offset_xyz("led"), dtype=float).reshape(3)


def bs_center(app, row_index: int) -> np.ndarray:
    z = app._row_z_positions()
    row = app.rows[row_index]
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), float(z[row_index]) + float(row.desp_z)), dtype=float
    )


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.add_beam_splitter_to_led("plate")
        check("glue active after one-click add", bool(getattr(app, "_optical_led_glued", False)))
        bs_row = app._promoted_optical_solid_row_index("optical")
        check("BS promoted row resolves", bs_row is not None)
        if bs_row is None:
            return 1

        # --- BS drag (vector primitive) -> BS alone, LED fixed --------------------
        led0, bs0 = led_offset(app), bs_center(app, bs_row)
        delta = np.asarray((0.0, 0.0, -21.0))
        app.translate_scene_row_pose_vector(bs_row, delta, record_history=False, sync_table=False)
        led1, bs1 = led_offset(app), bs_center(app, bs_row)
        check("vector BS drag moves the BS", np.allclose(bs1 - bs0, delta, atol=1e-9),
              f"delta={np.round(bs1 - bs0, 6)}")
        check("vector BS drag leaves the LED fixed", np.allclose(led1, led0, atol=1e-9),
              f"led_delta={np.round(led1 - led0, 6)}")

        # --- BS drag (per-axis placement-handle primitive) -> BS alone ------------
        app.translate_scene_row_pose(bs_row, "z", 4.0)
        led2, bs2 = led_offset(app), bs_center(app, bs_row)
        check("per-axis BS drag moves the BS", abs(float(bs2[2] - bs1[2]) - 4.0) < 1e-9)
        check("per-axis BS drag leaves the LED fixed", np.allclose(led2, led1, atol=1e-9),
              f"led_delta={np.round(led2 - led1, 6)}")

        # --- LED drag -> glued BS follows (assembly direction KEPT) ---------------
        led_delta = np.asarray((0.0, 0.0, 7.5))
        app.translate_step_overlay("led", (0.0, 0.0, 7.5), refresh=False, record_history=False)
        led3, bs3 = led_offset(app), bs_center(app, bs_row)
        check("LED drag moves the LED", np.allclose(led3 - led2, led_delta, atol=1e-9),
              f"led_delta={np.round(led3 - led2, 6)}")
        check("LED drag carries the glued BS", np.allclose(bs3 - bs2, led_delta, atol=1e-6),
              f"bs_delta={np.round(bs3 - bs2, 6)}")

        # --- LED distance-path carry (0133) still reaches the BS ------------------
        before_translation = app._led_step_z_translation()
        app._carry_led_glue_over_translation_change(before_translation - 3.0)
        bs4 = bs_center(app, bs_row)
        check("LED translation-change carry still moves the BS", abs(float(bs4[2] - bs3[2]) - 3.0) < 1e-6,
              f"bs_dz={float(bs4[2] - bs3[2]):.6f}")

        # --- glue intact + Alt path harmless --------------------------------------
        check("glue flag intact after all drags", bool(getattr(app, "_optical_led_glued", False)))
        app._suppress_optical_led_carry = True
        try:
            app.translate_scene_row_pose_vector(bs_row, (0.0, 0.0, 1.0), record_history=False, sync_table=False)
        finally:
            app._suppress_optical_led_carry = False
        led5 = led_offset(app)
        check("Alt-suspend path still BS-alone (compatible)", np.allclose(led5, led3, atol=1e-9))
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if failures:
        print(f"RESULT: FAIL ({len(failures)} failure(s))")
        return 1
    print("RESULT: PASS -- BS drags move the BS alone; LED drags carry the glued BS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
