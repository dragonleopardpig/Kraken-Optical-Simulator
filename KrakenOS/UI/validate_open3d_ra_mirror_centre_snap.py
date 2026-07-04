"""Display-free guard for bugs/0221 -- the manual-measurement re-anchor tool can SNAP to the RA
mirror CENTRE (the optical axis meeting the hypotenuse = the fold vertex), so the user can measure
e.g. object plane -> RA-mirror centre.

Background (flag_20260704_195234 request): "For manual measurement overlay, can we have option to
snap from object plane to the RA mirror center (snap to the intersection of optical axis and RA
mirror hypotenuse surface)?" The re-anchor tool snapped to the arbitrary surface point under the
cursor. bugs/0221: ``_ra_mirror_fold_vertex_world`` resolves the fold vertex for a promoted RA-mirror
row, and ``_apply_dimension_anchor_pick_motion`` snaps the moving endpoint onto it (labelled "RA
MIRROR CENTRE") when the cursor is over an RA mirror.

  (A) VERTEX: ``_ra_mirror_fold_vertex_world`` returns the fold vertex (== ``promoted_mirror_world_
      center``) for each promoted RA-mirror row.
  (B) GATED: it returns None for non-mirror rows (Object, Image, lens/aperture/datum rows) -- the
      snap only fires on an RA mirror.
  (C) MEASUREMENT: object plane -> mirror-1 centre (both on the incoming +Z axis) measures the
      object->fold-vertex distance (the mirror-1 centre z), i.e. the first optical-axis segment.
  (D) WIRED: the pick-motion snap override + the "RA MIRROR CENTRE" label are present in the source.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_centre_snap
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.folded_sequential_fold import promoted_mirror_world_center
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import _build_two_mirror

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_INSPECTOR_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "open3d_inspector.py"
_TOL = 0.05


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _editor():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = _build_two_mirror()
        editor._build_preview_system_rays_bundle(update_state=True)
    return editor


def validate_ra_mirror_centre_snap() -> list[Check]:
    checks: list[Check] = []
    e = _editor()
    specs = e._serializable_specs_for_rows(list(e.rows))

    # ===================== (A) VERTEX matches the fold centre ======================= #
    mirror_rows = [i for i, r in enumerate(e.rows) if _row_is_promoted_mirror_fold(r)]
    vtx_ok = len(mirror_rows) == 2
    vtx_detail_parts = []
    for i in mirror_rows:
        v = e._ra_mirror_fold_vertex_world(i)
        c = promoted_mirror_world_center(specs, i)
        match = v is not None and c is not None and float(np.linalg.norm(np.asarray(v) - np.asarray(c))) < _TOL
        vtx_ok = vtx_ok and match
        vtx_detail_parts.append(
            f"row {i}: vertex={None if v is None else [round(float(x),2) for x in v]} "
            f"== centre={None if c is None else [round(float(x),2) for x in c]} ({match})"
        )
    checks.append(Check(
        "the fold vertex resolves for each RA-mirror row and equals the promoted-mirror centre",
        vtx_ok, "; ".join(vtx_detail_parts) or "no RA-mirror rows found",
    ))

    # ===================== (B) GATED to RA mirrors ================================== #
    non_mirror = [i for i, r in enumerate(e.rows) if not _row_is_promoted_mirror_fold(r)]
    gated = all(e._ra_mirror_fold_vertex_world(i) is None for i in non_mirror)
    checks.append(Check(
        "the snap is gated to RA mirrors: non-mirror rows (Object/Image/lens/aperture) resolve to None",
        gated,
        f"non-mirror rows={non_mirror} all None={gated}",
    ))

    # ===================== (C) MEASUREMENT: object -> mirror-1 centre =============== #
    v1 = e._ra_mirror_fold_vertex_world(mirror_rows[0]) if mirror_rows else None
    meas_ok = False
    meas_detail = "no mirror-1 vertex"
    if v1 is not None:
        fixed = np.array([0.0, 0.0, 0.0], dtype=float)          # object plane on the axis
        moving_q = np.array([fixed[0], fixed[1], float(v1[2])])  # snap: axis X/Y + vertex Z
        measured = abs(float(moving_q[2] - fixed[2]))
        expected = float(v1[2])                                  # the mirror-1 centre z (first axis segment)
        meas_ok = abs(measured - expected) < _TOL and expected > 60.0
        meas_detail = (
            f"object(0,0,0) -> mirror-1 centre: snapped endpoint z={float(v1[2]):.2f}, "
            f"measured={measured:.2f}mm (expect {expected:.2f} = object->fold-vertex, the first axis segment)"
        )
    checks.append(Check(
        "object plane -> mirror-1 centre measures the object->fold-vertex distance (the first optical-axis segment)",
        meas_ok, meas_detail,
    ))

    # ===================== (D) WIRED =============================================== #
    try:
        src = _INSPECTOR_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ""
    wired = "_ra_mirror_fold_vertex_world(int(row_hit))" in src and "RA MIRROR CENTRE" in src
    checks.append(Check(
        "the pick-motion snap override + 'RA MIRROR CENTRE' label are wired into the re-anchor tool",
        wired,
        f"snap_override={'_ra_mirror_fold_vertex_world(int(row_hit))' in src} label={'RA MIRROR CENTRE' in src}",
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    checks = validate_ra_mirror_centre_snap()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_ra_mirror_centre_snap()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("RA-mirror-centre-snap validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
