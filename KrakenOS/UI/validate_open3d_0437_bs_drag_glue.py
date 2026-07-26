"""bugs/0437 guard -- the BS<->LED glue is ASYMMETRIC (parent/child).

flag_20260726_110337: dragging the BS plate down carried the glued LED along,
"effectively cancelling the BS plate move" (the old symmetric two-body glue
resurfacing past the 0432 Alt-only suspend). Encodes BOTH directions:

  * a BS move (vector row drag, per-axis row drag) leaves the LED fixed;
  * an LED move (overlay drag, translation-change carry) still carries the BS.

Run: python -m KrakenOS.UI.validate_open3d_0437_bs_drag_glue (needs a DISPLAY).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

_SCENE = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    if not _SCENE.exists():
        return True, [f"SKIP: scene fixture absent ({_SCENE.name})"]
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    except Exception as exc:  # pragma: no cover - environment
        return True, [f"SKIP: editor import failed ({exc!r})"]
    try:
        app = KrakenLayoutEditor()
    except Exception as exc:  # pragma: no cover - environment
        return True, [f"SKIP: editor could not start ({exc!r})"]

    passed = True

    def note(label: str, ok: bool, detail: str = "") -> None:
        nonlocal passed
        notes.append(("= " if ok else "") + label + (f" [{detail}]" if detail else ""))
        if not ok:
            passed = False

    def led_offset() -> np.ndarray:
        return np.asarray(app._step_placement_offset_xyz("led"), dtype=float).reshape(3)

    def bs_center(row_index: int) -> np.ndarray:
        z = app._row_z_positions()
        row = app.rows[row_index]
        return np.asarray(
            (float(row.desp_x), float(row.desp_y), float(z[row_index]) + float(row.desp_z)),
            dtype=float,
        )

    try:
        app.layout_files["az85_0437"] = _SCENE
        app.load_layout_by_name("az85_0437")
        app.add_beam_splitter_to_led("plate")
        if not bool(getattr(app, "_optical_led_glued", False)):
            return True, ["SKIP: one-click BS add did not glue (fixture drift)"]
        bs_row = app._promoted_optical_solid_row_index("optical")
        if bs_row is None:
            return True, ["SKIP: BS promoted row did not resolve (fixture drift)"]

        led0, bs0 = led_offset(), bs_center(bs_row)
        app.translate_scene_row_pose_vector(bs_row, (0.0, 0.0, -9.0), record_history=False, sync_table=False)
        led1, bs1 = led_offset(), bs_center(bs_row)
        note("BS-ALONE: vector BS drag moves the BS", abs(float(bs1[2] - bs0[2]) + 9.0) < 1e-9)
        note("BS-ALONE: vector BS drag leaves the LED fixed", bool(np.allclose(led1, led0, atol=1e-9)),
             f"led_delta={np.round(led1 - led0, 6)}")

        app.translate_scene_row_pose(bs_row, "z", 2.5)
        led2, bs2 = led_offset(), bs_center(bs_row)
        note("BS-ALONE: per-axis BS drag leaves the LED fixed", bool(np.allclose(led2, led1, atol=1e-9)),
             f"led_delta={np.round(led2 - led1, 6)}")
        note("BS-ALONE: per-axis BS drag moves the BS", abs(float(bs2[2] - bs1[2]) - 2.5) < 1e-9)

        app.translate_step_overlay("led", (0.0, 0.0, 6.0), refresh=False, record_history=False)
        led3, bs3 = led_offset(), bs_center(bs_row)
        note("CARRY: LED drag moves the LED", abs(float(led3[2] - led2[2]) - 6.0) < 1e-9)
        note("CARRY: LED drag carries the glued BS", abs(float(bs3[2] - bs2[2]) - 6.0) < 1e-6,
             f"bs_dz={float(bs3[2] - bs2[2]):.6f}")

        before_translation = app._led_step_z_translation()
        app._carry_led_glue_over_translation_change(before_translation - 2.0)
        bs4 = bs_center(bs_row)
        note("CARRY: LED translation-change carry reaches the BS", abs(float(bs4[2] - bs3[2]) - 2.0) < 1e-6)
        note("glue flag intact after all drags", bool(getattr(app, "_optical_led_glued", False)))
    except Exception as exc:  # pragma: no cover - defensive
        notes.append(f"raised {exc!r}")
        passed = False
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for line in notes:
        print(line)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
