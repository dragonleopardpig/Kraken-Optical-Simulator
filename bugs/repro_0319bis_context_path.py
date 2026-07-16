"""Repro 0319-bis: the REAL right-click "Add Beam Splitter to LED -> Cube" path.

The 07:31 recording (flag_20260716_073108_117) is a fresh post-restart app on HEAD
e33ac3ab, yet "nothing happened" -- no BS row was added (promoted rows still [1, 8]).
My earlier direct-call repro succeeded, so the difference must be live-app STATE or the
context wrapper. This drives the EXACT context object the menu lambda calls
(insp._face_assignment_service()._add_beam_splitter_to_led_from_context("cube")) with the
full lens+led+camera overlay state built, and captures every status line, append_debug
line, exception, and row delta so we can see WHY it stops.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def main() -> int:
    app = KrakenLayoutEditor()
    dbg: list[str] = []
    status: list[str] = []
    try:
        app.append_debug = lambda m, *a, **k: dbg.append(str(m))
        orig_status = app.status_var.set
        app.status_var.set = lambda s: (status.append(str(s)), orig_status(s))[1]
    except Exception:
        traceback.print_exc()

    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        insp = app._three_d_inspector
        insp.refresh_from_editor(
            sampling_mode=app._preview_3d_sampling_mode(),
            force_retrace=True,
        )
        insp.update_idletasks()
        insp.update()

        print("=== step actor counts (live-state check) ===")
        for label in ("led", "lens", "camera", "optical"):
            try:
                mesh = app._transformed_imported_step_mesh_for_label(label)
                print(f"  {label}: mesh={'yes' if mesh is not None else 'NONE'} "
                      f"path={app._step_path_for_label(label)}")
            except Exception as exc:
                print(f"  {label}: <err {exc}>")

        print("=== rows BEFORE ===")
        for i, r in enumerate(app.rows):
            print(f"  S{i}: {getattr(r, 'name', '?')}")

        print("=== opening plan ===")
        try:
            plan = app._led_beam_splitter_opening_plan()
            print("  plan:", plan)
        except Exception:
            print("  !!! plan raised:")
            traceback.print_exc()

        print("=== EXACT context path: _add_beam_splitter_to_led_from_context('cube') ===")
        svc = insp._face_assignment_service()
        svc._add_beam_splitter_to_led_from_context("cube")

        print("=== rows AFTER ===")
        for i, r in enumerate(app.rows):
            print(f"  S{i}: {getattr(r, 'name', '?')}")

        print("=== also try the direct editor call (for comparison) ===")
        try:
            result = app.add_beam_splitter_to_led("cube")
            print("  direct result:", result)
        except Exception:
            print("  !!! direct call raised:")
            traceback.print_exc()

        print("=== rows AFTER direct call ===")
        for i, r in enumerate(app.rows):
            print(f"  S{i}: {getattr(r, 'name', '?')}")
    except Exception:
        print("!!! TOP-LEVEL EXCEPTION !!!")
        traceback.print_exc()
    finally:
        print("=== status lines ===")
        for s in status:
            print("  [status]", s)
        print("=== append_debug lines ===")
        for m in dbg:
            print("  [debug]", m)
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
