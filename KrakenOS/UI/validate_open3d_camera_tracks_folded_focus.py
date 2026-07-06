"""Display-free guard for bugs/0220 -- the camera STEP must stay ATTACHED to the drawn
detector on a folded promoted-mirror scene.

bugs/0243 rework: the bugs/0217 reconcile (which used to park the detector at the ray
waist, forcing the camera to chase the FOCUS) is retired. The folded scene traces on the
REAL system, the detector sits at the PRESCRIPTION seat, and a stale-gap fixture is shown
honestly defocused until solved/snapped -- so the camera tracks the PRESCRIPTION plane
again and is coincident with the detector at all times. After ``snap_detector_to_image_
plane`` the prescription IS the focus, so camera+detector+focus coincide (the original
bugs/0220 outcome, now achieved by moving the prescription instead of detaching planes).

  (A) TWO-MIRROR: the camera track equals the prescription plane (the detector seat).
  (B) SINGLE-MIRROR: same.
  (C) SNAP: after snap_detector_to_image_plane the camera track equals the (new)
      prescription = the paraxial focus -- camera, detector and focus coincide.
  (D) WIRED: the camera placement sites call ``_camera_track_image_plane_z``.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_tracks_folded_focus
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_second_mirror_incoming_axis_placement import (
    _build_single_mirror,
    _build_two_mirror,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVICES = PROJECT_ROOT / "KrakenOS" / "UI" / "services"
_TOL = 0.5


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _editor(builder):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor, _ = builder()
    return editor


def _zs(editor):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        presc = float(editor._current_image_plane_z())
        track = float(editor._camera_track_image_plane_z())
        focus = editor._paraxial_image_plane_z()
    return presc, track, (None if focus is None else float(focus))


def validate_camera_tracks_folded_focus() -> list[Check]:
    checks: list[Check] = []

    presc2, track2, focus2 = _zs(_editor(_build_two_mirror))
    presc1, track1, focus1 = _zs(_editor(_build_single_mirror))

    # ============ (A)/(B): camera track == prescription plane (the detector seat) ===== #
    checks.append(Check(
        "two-mirror: camera tracks the prescription plane (the detector seat; bugs/0243)",
        abs(track2 - presc2) < _TOL,
        f"prescription={presc2:.2f} camera_track={track2:.2f} (expect equal; paraxial focus={None if focus2 is None else round(focus2,2)})",
    ))
    checks.append(Check(
        "single-mirror: camera tracks the prescription plane (the detector seat; bugs/0243)",
        abs(track1 - presc1) < _TOL,
        f"prescription={presc1:.2f} camera_track={track1:.2f} (expect equal)",
    ))

    # ============ (C) SNAP: prescription -> focus, camera follows both ================= #
    snap_ok = False
    snap_detail = "unavailable"
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor_snap, _ = _build_two_mirror()
            editor_snap._build_preview_system_rays_bundle(update_state=True)
            editor_snap.snap_detector_to_image_plane()
            presc_s = float(editor_snap._current_image_plane_z())
            track_s = float(editor_snap._camera_track_image_plane_z())
            focus_s = editor_snap._paraxial_image_plane_z()
        snap_ok = (
            focus_s is not None
            and abs(presc_s - float(focus_s)) < 0.5
            and abs(track_s - presc_s) < _TOL
        )
        snap_detail = (
            f"after snap: prescription={presc_s:.2f} focus={None if focus_s is None else round(float(focus_s),2)} "
            f"camera_track={track_s:.2f} (expect all equal -- camera+detector+focus coincide)"
        )
    except Exception as exc:  # noqa: BLE001
        snap_detail = f"raised {exc!r}"
    checks.append(Check(
        "SNAP: after snap_detector_to_image_plane the camera sits at the focus with the detector",
        snap_ok, snap_detail,
    ))

    # ===================== (D) WIRED ================================================= #
    wired_files = {
        "layout_polyline_display.py": False,
        "optical_solid_workflow.py": False,
        "scene_placement_commands.py": False,
    }
    for name in wired_files:
        try:
            src = (_SERVICES / name).read_text(encoding="utf-8")
        except Exception:
            src = ""
        wired_files[name] = "_camera_track_image_plane_z()" in src
    all_wired = all(wired_files.values())
    checks.append(Check(
        "the camera placement sites call _camera_track_image_plane_z (bugs/0220), not the raw prescription plane",
        all_wired,
        ", ".join(f"{k}={v}" for k, v in wired_files.items()),
    ))

    return checks


def run_checks() -> tuple[bool, list[str]]:
    checks = validate_camera_tracks_folded_focus()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_camera_tracks_folded_focus()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Camera-tracks-folded-focus validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
