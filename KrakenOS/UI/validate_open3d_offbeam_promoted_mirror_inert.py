"""Display-free guard for bugs/0224 -- a promoted FULL-MIRROR parked CLEAR of the beam is
optically INERT: promoting it must not move any existing optical component, the detector,
the axis, or the imaging cone. A mirror only folds the beam if the beam actually hits it.

The flag (flag_20260705_101311, "random placement ... with promotion affect the existing
placement of optical component"): promoting an RA-mirror prism parked at ~(102, 97, 210) --
nowhere near the folded legs (y=0, z=71.9) -- reflected the pose-override walk's running
frame about the prism's distant infinite PLANE, flinging the Image row ~140 mm and the
detector ~300 mm onto a fold the beam never makes, and bent the reflected optical-axis
segments diagonally toward the parked prism.

The fix is a beam-hit gate in three layers, each pinned here:
  * ``_reflected_frame_from_interaction_face`` folds ONLY when the beam LINE crosses the
    face's transverse extent (sign-agnostic in the plane distance: the walk's frame origin
    is a station marker that legitimately sits PAST a genuine fold face -- the AZ85 second
    mirror reads distance = -93.9);
  * the pose-override follower walk skips a free-placed missed mirror entirely (pinned at
    its drop pose, contributing NO fold and NO frame re-sourcing from its inferred output);
  * ``offbeam_free_placed_mirror_row_indices`` (vertex-chain walk) drops the parked mirror
    from ``free_placed_mirror_world_planes`` (display bend + axis segments) and zeroes its
    flat-plate equivalent (AIR, thickness 0) in the straight-equivalent + paraxial
    reference so the traced stations/waist do not shift.

  (A) GENUINE FOLDS UNCHANGED: the two-mirror AZ85 baseline still folds to the known
      detector (~181.4, 0, -13.6) -- the gate must never kill a real fold (it briefly did
      during development, via a wrong forward-distance test).
  (B) INERT PROMOTE: after promoting the parked mirror, every existing row seat and the
      detector move < 0.01 mm, the parked row itself stays pinned at its drop pose, and
      the on-detector waist cluster is unchanged.
  (C) CLASSIFIED + EXCLUDED: the vertex-chain walk marks exactly the parked row off-beam
      (both on-path mirrors stay on-beam), and the display fold planes drop it.
  (D) WIRED: the three fix layers are present in source.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_offbeam_promoted_mirror_inert
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.services.folded_sequential_fold import (
    free_placed_mirror_world_planes,
    offbeam_free_placed_mirror_row_indices,
)
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import (
    _AZ85,
    _build_editor,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PORTS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "nonseq_output_ports.py"
_FOLD_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "folded_sequential_fold.py"
_PARAXIAL_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "paraxial_tools.py"

_PARKED_OFFSET = (100.0, 97.0, 200.0)  # mirrors the flagged random parked pose
_KNOWN_FOLDED_DETECTOR = np.asarray((181.374, 0.0, -13.552), dtype=float)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _snapshot(editor, bundle):
    seats = {}
    for index in range(len(editor.rows)):
        try:
            seats[index] = np.asarray(
                _quiet(editor._surface_reference_world_point, index), dtype=float
            ).reshape(3)
        except Exception:
            seats[index] = None
    detector = next(
        (
            np.asarray(t.center_world, dtype=float).reshape(3)
            for t in bundle.targets
            if getattr(t, "is_detector", False)
        ),
        None,
    )
    endpoints = np.asarray(
        [np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths]
    )
    return seats, detector, endpoints


def _waist_rms(endpoints: np.ndarray, detector: np.ndarray) -> float:
    near = endpoints[np.linalg.norm(endpoints - detector, axis=1) < 5.0]
    if len(near) < 10:
        return float("nan")
    centred = near[:, :2] - near[:, :2].mean(axis=0)
    return float(np.sqrt((centred**2).sum(axis=1).mean()))


def validate_offbeam_promoted_mirror_inert() -> list[Check]:
    checks: list[Check] = []

    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)
    _s, _r, bundle_before = _quiet(
        editor._build_preview_system_rays_bundle, update_state=True
    )
    seats_before, det_before, ends_before = _snapshot(editor, bundle_before)

    # ============ (A) genuine folds unchanged ==================================== #
    checks.append(Check(
        "GENUINE folds unchanged: the two-mirror baseline still folds to the known detector",
        det_before is not None and bool(np.allclose(det_before, _KNOWN_FOLDED_DETECTOR, atol=0.05)),
        f"detector={None if det_before is None else np.round(det_before, 3)} "
        f"(expect ~{np.round(_KNOWN_FOLDED_DETECTOR, 2)}; a wrong beam-hit gate kills the real fold)",
    ))

    # ============ (B) parked promote is inert ==================================== #
    original_offset = carryover._OFFSET
    carryover._OFFSET = _PARKED_OFFSET
    try:
        parked_index = int(_quiet(carryover._promote_mirror2, editor))
    finally:
        carryover._OFFSET = original_offset
    _s, _r, bundle_after = _quiet(
        editor._build_preview_system_rays_bundle, update_state=True
    )
    seats_after, det_after, ends_after = _snapshot(editor, bundle_after)
    worst_move = 0.0
    for index, seat_after in seats_after.items():
        if index == parked_index:
            continue
        before_index = index if index < parked_index else index - 1
        seat_before = seats_before.get(before_index)
        if seat_before is None or seat_after is None:
            continue
        worst_move = max(worst_move, float(np.linalg.norm(seat_before - seat_after)))
    detector_move = (
        float(np.linalg.norm(det_before - det_after))
        if det_before is not None and det_after is not None
        else float("inf")
    )
    parked_seat = seats_after.get(parked_index)
    parked_pinned = parked_seat is not None and bool(
        np.linalg.norm(parked_seat - np.asarray((93.75, 97.0, 206.25))) < 5.0
    )
    checks.append(Check(
        "INERT promote: no existing row seat and no detector movement; the parked mirror stays pinned",
        bool(worst_move < 0.01 and detector_move < 0.01 and parked_pinned),
        f"worst_row_move={worst_move:.4f}mm detector_move={detector_move:.4f}mm "
        f"parked_seat={None if parked_seat is None else np.round(parked_seat, 2)}",
    ))
    rms_before = _waist_rms(ends_before, det_before)
    rms_after = _waist_rms(ends_after, det_after)
    checks.append(Check(
        "INERT promote: the on-detector waist cluster is unchanged (imaging cone untouched)",
        bool(
            np.isfinite(rms_before)
            and np.isfinite(rms_after)
            and abs(rms_before - rms_after) < 0.01
        ),
        f"waist RMS before={rms_before:.5f}mm after={rms_after:.5f}mm",
    ))

    # ============ (C) classified off-beam + excluded from the display planes ===== #
    specs = _quiet(editor._serializable_specs_for_rows, list(editor.rows))
    offbeam = _quiet(offbeam_free_placed_mirror_row_indices, specs)
    plane_rows = {int(idx) for idx, _c, _n in _quiet(free_placed_mirror_world_planes, specs)}
    checks.append(Check(
        "CLASSIFIED: exactly the parked row is off-beam; the display fold planes drop it",
        bool(offbeam == {parked_index} and parked_index not in plane_rows),
        f"offbeam={sorted(offbeam)} (expect [{parked_index}]) plane_rows={sorted(plane_rows)}",
    ))

    # ============ (D) wiring ===================================================== #
    try:
        ports_src = _PORTS_SRC.read_text(encoding="utf-8")
        fold_src = _FOLD_SRC.read_text(encoding="utf-8")
        paraxial_src = _PARAXIAL_SRC.read_text(encoding="utf-8")
    except Exception:
        ports_src = fold_src = paraxial_src = ""
    wired = (
        "SIGN-AGNOSTIC" in ports_src  # the extent gate keeps station-marker semantics
        and "the beam line never crosses the face -- no fold" in ports_src
        and "bugs/0224" in ports_src  # follower inert-skip
        and "def offbeam_free_placed_mirror_row_indices" in fold_src
        and "offbeam_free_placed_mirror_row_indices(specs)" in fold_src  # planes exclusion
        and "_offbeam_promoted_mirror_rows" in paraxial_src  # zero-thickness equivalents
    )
    checks.append(Check(
        "the beam-hit gate, follower inert-skip, plane exclusion and zero-thickness equivalents are wired",
        wired,
        f"extent_gate={'SIGN-AGNOSTIC' in ports_src} inert_skip={'bugs/0224' in ports_src} "
        f"chain_walk={'def offbeam_free_placed_mirror_row_indices' in fold_src} "
        f"equivalents={'_offbeam_promoted_mirror_rows' in paraxial_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_offbeam_promoted_mirror_inert()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_offbeam_promoted_mirror_inert()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Off-beam-promoted-mirror-inert validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
