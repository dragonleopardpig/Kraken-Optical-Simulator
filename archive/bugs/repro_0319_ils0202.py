"""Throwaway repro: one-click Add Beam Splitter in the USER's EXACT folded scene.

Loads attachment/machine_vision_AZ85_RA_Mirror.py -- the user's saved layout
(ILS0202 LED + two promoted RA mirrors + ELS-85 blackbox lens + aperture + datums,
the same 10 rows as the 17:02 prelude) -- then runs add_beam_splitter_to_led("cube")
to see whether the FOLDED scene exposes a failure the bare-LED repro did not.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _open_inspector(app):
    app.open_3d_view()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        raise RuntimeError("Embedded 3D inspector unavailable")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.update_idletasks()
    inspector.update()
    return inspector


def main() -> int:
    app = KrakenLayoutEditor()
    msgs = []
    try:
        orig = app.status_var.set
        app.status_var.set = lambda s: (msgs.append(str(s)), orig(s))[1]
    except Exception:
        pass
    try:
        # Load the user's exact saved scene via the production load path.
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        print("=== rows AFTER scene load ===")
        for i, r in enumerate(app.rows):
            print(f"  S{i}: {getattr(r,'name','?')}")
        print("  imported_led_step_path:", getattr(app, "imported_led_step_path", None))
        print("  imported_optical_step_path:", getattr(app, "imported_optical_step_path", None))

        inspector = _open_inspector(app)
        inspector.refresh_from_editor()
        inspector.update_idletasks()

        print("=== auto_detect_step_clear_aperture_candidates('led') ===")
        cands = app.auto_detect_step_clear_aperture_candidates("led")
        print(f"  verified candidates: {len(cands)}")
        for c in cands[:6]:
            print(f"    face_index={c.face_index} score={c.score:.3f} "
                  f"centroid={tuple(round(x,1) for x in c.centroid)} area={c.area_mm2:.1f}")

        print("=== _led_beam_splitter_opening_plan() ===")
        plan = app._led_beam_splitter_opening_plan()
        print(f"  plan: {plan!r}")

        print("=== add_beam_splitter_to_led('cube') ===")
        result = app.add_beam_splitter_to_led("cube")
        print(f"  RESULT: {result!r}")

        print("=== rows AFTER add_beam_splitter_to_led ===")
        for i, r in enumerate(app.rows):
            print(f"  S{i}: {getattr(r,'name','?')}")
    except Exception:
        print("!!! EXCEPTION !!!")
        traceback.print_exc()
    finally:
        print("=== status_var messages ===")
        for m in msgs:
            print(f"  [status] {m}")
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
