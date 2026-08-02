"""Pin the chained pose-override bug: for the 2-mirror scene, print the override center/
rotation/frame_source for EVERY follower row -- especially mirror2 (its own pose) and the
Image (its follower). Shows whether mirror2's OWN pose is folded onto leg 2 or left on the
straight axis, and whether its followers use a compounded frame."""
from __future__ import annotations

import contextlib
import io
from dataclasses import asdict

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides


def _dup(row):
    return SurfaceRow(**asdict(row))


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        rows = list(editor.rows)
        mirror2 = _dup(rows[1])
        mirror2.name = "mirror2"
        rows[7].thickness = 90.0
        mirror2.thickness = 60.0
        new_rows = rows[:8] + [mirror2] + [rows[8]]
        editor.rows = new_rows
        editor._normalize_special_rows()

    for use_system in (False,):
        ov = build_optical_solid_output_port_pose_overrides(editor.rows, system=None)
        print(f"\n=== overrides (system=None) : follower rows {sorted(ov.keys())} ===")
        for i in sorted(ov.keys()):
            d = ov[i]
            c = np.asarray(d.get("center"), float).reshape(3)
            rot = np.asarray(d.get("rotation"), float).reshape(3, 3)
            fwd = rot[:, 2]
            print(f"  row {i:2d}: center=({c[0]:8.2f},{c[1]:7.2f},{c[2]:8.2f}) fwd=({fwd[0]:5.2f},{fwd[1]:5.2f},{fwd[2]:5.2f}) "
                  f"src={d.get('frame_source')!r} source_index={d.get('source_index')}")
    # which rows are mirrors?
    print("\nmirror rows: 1 and 8 (mirror2). Image is row 9.")


if __name__ == "__main__":
    main()
