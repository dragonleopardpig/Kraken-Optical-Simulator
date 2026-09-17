"""Probe: what pose-override does mirror 2 get? (bugs/0212 fix A)

Builds the AZ85 folded scene (mirror 1 promoted), inspects the rows + their
assigned-face counts, runs build_optical_solid_output_port_pose_overrides, then
synthesises a free-placed 2nd mirror (copy mirror 1's row, STRIP faces, re-pose
to world [210.7,0,71.9] like the flag) and re-runs the builder to see the
override that drags it off its placed pose.
"""
from __future__ import annotations

import copy
import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI import nonseq_output_ports as nop
from KrakenOS.UI.optical_solid_metadata import (
    normalize_optical_solid_face_metadata,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
)


def _assigned_face_count(row) -> int:
    adv = getattr(row, "advanced", None) or {}
    meta = normalize_optical_solid_face_metadata(adv.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    faces = list(meta.get("faces", []) or [])
    assigned = 0
    for f in faces:
        if not isinstance(f, dict):
            continue
        role = str(f.get("role") or "").strip().lower()
        func = str(f.get("function") or "").strip().lower()
        if (role and role not in ("", "none", "default")) or (func and func not in ("", "none", "default", "transmit")):
            assigned += 1
    return assigned


def main() -> int:
    editor = _build_editor(_AZ85)
    rows = editor.rows
    print(f"=== AZ85 rows: {len(rows)} ===")
    for i, r in enumerate(rows):
        is_solid = nop._row_has_optical_solid(nop._row_like(r))
        fc = _assigned_face_count(r)
        desp = (getattr(r, "desp_x", 0.0), getattr(r, "desp_y", 0.0), getattr(r, "desp_z", 0.0))
        print(f"  {i}: surf={getattr(r,'surface','?'):9s} solid={is_solid} assigned_faces={fc} desp={tuple(round(float(v),2) for v in desp)} name={getattr(r,'name','')[:40]}")

    print("\n=== overrides on the base AZ85 (1 mirror) ===")
    ov = nop.build_optical_solid_output_port_pose_overrides(rows)
    for idx in sorted(ov):
        c = np.asarray(ov[idx].get("center"), dtype=float)
        print(f"  row {idx}: center={tuple(round(float(v),2) for v in c)} src={ov[idx].get('source_index')} frame={ov[idx].get('frame_source')}")

    # --- synthesize a free-placed mirror 2 (no assigned faces) at world [210.7,0,71.9] ---
    mirror1 = rows[1]
    m2 = copy.deepcopy(mirror1)
    # strip assigned faces so it mimics a fresh promote (no ports)
    adv = dict(getattr(m2, "advanced", {}) or {})
    adv.pop(OPTICAL_SOLID_FACES_ADVANCED_ATTR, None)
    m2.advanced = adv
    # re-pose: desp_x/y = world center, desp_z encodes station later; just set world center
    img_idx = len(rows) - 1  # Image is last
    insert_at = img_idx
    # world center target
    m2.desp_x = 210.7
    m2.desp_y = 0.0
    # keep m2.desp_z from mirror1 for now; the builder recomputes via frame anyway
    rows2 = list(rows[:insert_at]) + [m2] + list(rows[insert_at:])
    print(f"\n=== synthetic 2-mirror rows: {len(rows2)} (mirror2 at index {insert_at}, assigned_faces={_assigned_face_count(m2)}) ===")
    ov2 = nop.build_optical_solid_output_port_pose_overrides(rows2)
    for idx in sorted(ov2):
        c = np.asarray(ov2[idx].get("center"), dtype=float)
        tag = "  <-- mirror2" if idx == insert_at else ""
        print(f"  row {idx}: center={tuple(round(float(v),2) for v in c)} src={ov2[idx].get('source_index')} frame={ov2[idx].get('frame_source')}{tag}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
