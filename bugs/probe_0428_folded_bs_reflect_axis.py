"""Probe (bugs/0428 fold-aware follow-up): on the FOLDED AZ85 scene, adding a BS plate must now
emit its REFLECT-branch optical axis (``axis:global:split``) WITHOUT deviating the 2-RA-mirror axis.

Reproduces flag_20260723_155614 ("After adding BS Plate, there is no optical axis generated from BS
plate"): the recorded (gated) build showed only the 3 mirror segments and no split axis. After the
fold-aware fix the assembler derives the BS's incoming from the axis leg its coating sits on, so the
split axis appears even though the scene is mirror-folded -- and the 3 mirror segments stay unchanged
(0429). Short probe (single refresh), safe under xvfb-run -a.

Run:
    xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0428_folded_bs_reflect_axis.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _axis_ids(insp):
    recs = insp._optical_axis_records_for_3d(insp._current_scene_bundle)
    return [r.get("axis_id") for r in (recs or [])]


def main() -> int:
    app = KrakenLayoutEditor()
    rc = 1
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            raise RuntimeError("inspector unavailable")
        insp.refresh_from_editor()
        insp.update_idletasks()

        before = _axis_ids(insp)
        print("axis_ids BEFORE add BS:", before)

        print("\n--- add_beam_splitter_to_led('plate') ---")
        result = app.add_beam_splitter_to_led("plate")
        print("return value:", result)
        try:
            print("status:", app.status_var.get())
        except Exception:
            pass
        insp.refresh_from_editor()
        insp.update_idletasks()

        after = _axis_ids(insp)
        print("axis_ids AFTER add BS:", after)

        split = [a for a in after if isinstance(a, str) and a.startswith("axis:global:split")]
        mirror_before = [a for a in before if isinstance(a, str) and "reflected" in a]
        mirror_after = [a for a in after if isinstance(a, str) and "reflected" in a]

        print("\n== ASSERTIONS ==")
        ok_split = bool(split)
        ok_mirror = mirror_before == mirror_after
        print(f"  [{'PASS' if ok_split else 'FAIL'}] BS reflect axis present: {split}")
        print(f"  [{'PASS' if ok_mirror else 'FAIL'}] mirror axis unchanged (0429): {mirror_before} -> {mirror_after}")
        rc = 0 if (ok_split and ok_mirror) else 1
    except Exception:
        traceback.print_exc()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    sys.exit(main())
