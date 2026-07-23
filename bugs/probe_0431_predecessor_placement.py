"""Probe (bugs/0431 / BS Phase 2): reproduce lens+camera misplacement when the FIRST RA mirror is
removed on the AZ85 scene.

Topology: Object(0) -> RA-mirror-1(1) -> lens group(3-7) -> RA-mirror-2(8) -> Image/Sensor(9).
The user replaces the temporary RA-mirror-1 with a BS plate; requirement 6 says the camera should
follow its IMMEDIATE predecessor (RA-mirror-2), so removing RA-mirror-1 must NOT move the lens/camera.

This probe builds the output-port overrides (display-free) with RA-mirror-1 present, then removes it and
rebuilds, and prints the follower centers so we can SEE whether the lens/camera collapse to the straight
axis. No assertion yet -- this is the diagnostic that drives the Phase 2 design.

Run:
    .devenv/state/venv/bin/python bugs/probe_0431_predecessor_placement.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _dump(label, rows):
    ov = build_optical_solid_output_port_pose_overrides(rows)
    print(f"\n=== {label}: {len(rows)} rows, {len(ov)} overrides ===")
    for idx in sorted(ov):
        o = ov[idx]
        c = np.asarray(o.get("center"), dtype=float).reshape(3)
        fwd = np.asarray(o.get("normal", (0, 0, 1)), dtype=float).reshape(3)
        name = getattr(rows[idx], "name", "?")[:34]
        print(f"  row {idx:2} [{name:34}] center=({c[0]:8.2f},{c[1]:8.2f},{c[2]:8.2f}) fwd=({fwd[0]:+.2f},{fwd[1]:+.2f},{fwd[2]:+.2f}) src={o.get('frame_source','')[:22]}")
    return ov


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        rows = list(app.rows)
        print("row roster:")
        for i, r in enumerate(rows):
            print(f"  {i:2} surf={getattr(r,'surface','?'):9} solid={getattr(r,'is_optical_solid',None)} name={getattr(r,'name','?')[:40]}")

        ov_before = _dump("WITH RA-mirror-1 (rows 1+2)", rows)

        # remove the WHOLE RA-mirror-1 solid (rows 1 AND 2 -- entry + "-> next" exit)
        rows_wo = [r for i, r in enumerate(rows) if i not in (1, 2)]
        ov_after = _dump("WITHOUT RA-mirror-1 (clean 2-surface removal)", rows_wo)

        # also: mirror-2 alone as a top-level source (does it re-fold the camera?)
        print("\n=== diagnose: is RA-mirror-2 recognised as a fold source when top-level? ===")
        from KrakenOS.UI.nonseq_output_ports import (
            _row_has_optical_solid, optical_solid_face_world_records, row_z_positions,
            _solid_has_full_mirror_interaction_face, _free_placed_solid_pinned_pose,
        )
        zp = row_z_positions(rows_wo)
        for i, r in enumerate(rows_wo):
            if not _row_has_optical_solid(r):
                continue
            wf = optical_solid_face_world_records(r, float(zp[i]) if i < len(zp) else 0.0, assigned_only=True)
            full_mir = _solid_has_full_mirror_interaction_face(wf)
            pinned = _free_placed_solid_pinned_pose(r, float(zp[i]) if i < len(zp) else 0.0)
            print(f"  row {i:2} [{getattr(r,'name','?')[:30]:30}] optical_solid full_mirror={full_mir} free_placed_pinned={pinned is not None}")

        # The camera (last Image row) -- did its placement move when mirror-1 was removed?
        img_before = next((i for i, r in enumerate(rows) if getattr(r, "surface", "") == "Image"), None)
        img_after = next((i for i, r in enumerate(rows_wo) if getattr(r, "surface", "") == "Image"), None)
        print("\n=== camera placement delta ===")
        cb = ov_before.get(img_before, {}).get("center") if img_before is not None else None
        ca = ov_after.get(img_after, {}).get("center") if img_after is not None else None
        print(f"  camera override BEFORE (row {img_before}):", None if cb is None else np.asarray(cb).round(2))
        print(f"  camera override AFTER  (row {img_after}):", None if ca is None else np.asarray(ca).round(2))
        if cb is None and ca is None:
            print("  NOTE: camera never had an override (may be placed via system Image station, not this map)")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
