"""Probe (bugs/0213): can a free-placed 2nd mirror be PINNED at its dropped pose
AND fold the detector onto the reflected leg by physics off its OWN orientation?

Phase 1 -- characterise: print mirror 1's assigned faces, compute the pinned
world pose a free-placed mirror 2 would take (its own desp+station), and for a
few candidate orientations print the resulting Mirror-face world normal + the
reflected direction of the incoming +X leg (r = d - 2(d.n)n). This tells us which
orientation folds +X -> -Z (the user's intent) with NO hard-coded axis.

Phase 2 -- current behaviour: run the (unfixed) override builder on the 2-mirror
scene to see mirror 2 swept off its placed pose / the detector left on the +X leg.
"""
from __future__ import annotations

import copy
import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI import nonseq_output_ports as nop
from KrakenOS.UI import optical_solid_metadata as osm
from KrakenOS.UI.optical_solid_metadata import (
    normalize_optical_solid_face_metadata,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
)

_PLACED = np.asarray([210.7, 0.0, 71.9], dtype=float)


def _fmt(v):
    return tuple(round(float(x), 3) for x in np.asarray(v, dtype=float).reshape(-1)[:3])


def _assigned_faces(row):
    adv = getattr(row, "advanced", None) or {}
    meta = normalize_optical_solid_face_metadata(adv.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
    out = []
    for f in list(meta.get("faces", []) or []):
        if not isinstance(f, dict):
            continue
        role = str(f.get("role") or "").strip()
        func = str(f.get("function") or "").strip()
        if role in ("", "Unassigned") and func in ("", "Unassigned"):
            continue
        out.append(f)
    return out


def main() -> int:
    editor = _build_editor(_AZ85)
    rows = list(editor.rows)
    img_idx = len(rows) - 1
    mirror1 = rows[1]

    print("=== mirror 1 assigned faces (local) ===")
    for f in _assigned_faces(mirror1):
        print(f"  {f.get('face_id')}: role={f.get('role')} func={f.get('function')} "
              f"side={f.get('side_2d')} normal={_fmt(f.get('normal'))} centroid={_fmt(f.get('centroid'))}")

    # z-station at the insert slot (before Image)
    insert_at = img_idx
    z_positions = nop.row_z_positions([nop._row_like(r) for r in rows[:insert_at]] + [nop._row_like(mirror1)] + [nop._row_like(r) for r in rows[insert_at:]])
    z_station = float(z_positions[insert_at]) if insert_at < len(z_positions) else 0.0
    print(f"\ninsert_at={insert_at}  z_station@insert={round(z_station,3)}")

    # desp that reconstructs world [210.7,0,71.9] as the mirror's OWN pose:
    #   offset = (desp_x, desp_y, z_station + desp_z)  ->  want offset == _PLACED
    desp = np.asarray([_PLACED[0], _PLACED[1], _PLACED[2] - z_station], dtype=float)
    print(f"pinned desp for own-pose == {_fmt(_PLACED)}:  desp={_fmt(desp)}")

    incoming = np.asarray([1.0, 0.0, 0.0], dtype=float)  # mirror 1's +X leg
    print("\n=== candidate orientations: Mirror-face world normal + reflected(+X) ===")
    for label, tilt in [
        ("tilt 0 (as mirror1)", (0.0, 0.0, 0.0)),
        ("tilt_y=-90", (0.0, -90.0, 0.0)),
        ("tilt_y=+90", (0.0, 90.0, 0.0)),
        ("tilt_y=180", (0.0, 180.0, 0.0)),
    ]:
        m2 = copy.deepcopy(mirror1)
        m2.desp_x, m2.desp_y, m2.desp_z = float(desp[0]), float(desp[1]), float(desp[2])
        m2.tilt_x, m2.tilt_y, m2.tilt_z = tilt
        rotation = osm.rotation_matrix_from_kraken_tilts(*tilt)
        center = np.asarray([m2.desp_x, m2.desp_y, z_station + m2.desp_z], dtype=float)
        faces = nop._optical_solid_faces_at_pose(m2, center, rotation, assigned_only=True)
        mface = nop.select_optical_solid_interaction_face(faces)
        if mface is None:
            print(f"  {label:22s}: no interaction face")
            continue
        n = np.asarray(mface.get("normal_world"), dtype=float)
        refl = incoming - 2.0 * float(np.dot(incoming, n)) * n
        print(f"  {label:22s}: pin_center={_fmt(center)} mirror_normal_world={_fmt(n)} "
              f"reflected(+X)={_fmt(refl)}")

    # Phase 2: current (unfixed) builder on the 2-mirror scene, faced mirror2 tilt_y=-90
    print("\n=== CURRENT builder on 2-mirror scene (faced free-placed mirror2, tilt_y=-90) ===")
    m2 = copy.deepcopy(mirror1)
    adv = dict(getattr(m2, "advanced", {}) or {})
    adv["StepOverlayPromotion"] = {"step_label": "optical", "center_world": [float(x) for x in _PLACED]}
    m2.advanced = adv
    m2.desp_x, m2.desp_y, m2.desp_z = float(desp[0]), float(desp[1]), float(desp[2])
    m2.tilt_x, m2.tilt_y, m2.tilt_z = 0.0, -90.0, 0.0
    rows2 = list(rows[:insert_at]) + [m2] + list(rows[insert_at:])
    ov = nop.build_optical_solid_output_port_pose_overrides(rows2)
    for idx in sorted(ov):
        tag = "  <-- mirror2" if idx == insert_at else ("  <-- Image" if idx == insert_at + 1 else "")
        print(f"  row {idx}: center={_fmt(ov[idx].get('center'))} src={ov[idx].get('source_index')} "
              f"frame={ov[idx].get('frame_source')}{tag}")
    print(f"  (mirror2 index={insert_at}, Image index={insert_at+1}); mirror2 in overrides = {insert_at in ov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
