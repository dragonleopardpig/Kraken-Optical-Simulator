"""Display-free guard for bugs/0220 -- the camera STEP must track the TRUE optical focus (not the
prescription Image-row plane) on a folded promoted-mirror scene whose trailing mirror overshoots
the conjugate, so it stays ATTACHED to the detector the bugs/0217 reconcile parks at that focus.

Background (flag_20260704_195234 "detector and camera STEP detached"): the camera front is placed at
``_current_image_plane_z() - front_to_sensor``. On the two-mirror AZ85 the prescription Image row
sits a mirror-plate (~32 mm) PAST the true focus, so the camera followed the row to 387 while the
0217 reconcile put the detector at the focus (355) -> detached by the plate. bugs/0220:
``_camera_track_image_plane_z`` tracks ``_paraxial_image_plane_z`` (the focus) when it is
meaningfully BEFORE the prescription row (the overshoot -- exactly when 0217 fires), else keeps the
prescription plane (unfolded, or a single fold whose rays stop at the row 8 mm short of the focus,
where 0217 is a no-op and moving the camera would detach it the OTHER way).

  (A) TWO-MIRROR: the camera tracks the paraxial FOCUS (< the prescription row) -> attaches to the
      0217 detector.
  (B) SINGLE-MIRROR: the focus is PAST the prescription row (rays stop short), so the camera keeps
      the prescription plane -- UNCHANGED (no detach the other way).
  (C) CAUSAL: the two-mirror camera-track z is the focus, NOT the prescription row it used to follow
      (a plate behind the detector).
  (D) WIRED: the camera placement sites call ``_camera_track_image_plane_z`` (not the raw
      ``_current_image_plane_z``).

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

    # ===================== (A) TWO-MIRROR: track the focus =========================== #
    two_ok = (
        focus2 is not None
        and focus2 < presc2 - _TOL          # the trailing-mirror overshoot
        and abs(track2 - focus2) < _TOL      # camera tracks the focus, attaches to the detector
    )
    checks.append(Check(
        "two-mirror: camera tracks the paraxial FOCUS (before the prescription row) -> attaches to the detector",
        two_ok,
        f"prescription={presc2:.2f} focus={None if focus2 is None else round(focus2,2)} camera_track={track2:.2f} "
        f"(expect track==focus, focus<prescription)",
    ))

    # ===================== (B) SINGLE-MIRROR: keep the prescription =================== #
    one_ok = (
        focus1 is not None
        and focus1 < presc1 - _TOL           # bugs/0222: the external-air fold also overshoots
        and abs(track1 - focus1) < _TOL       # ... so the camera tracks the focus too, onto the detector
    )
    checks.append(Check(
        "single-mirror: the external-air focus is BEFORE the prescription row, so the camera tracks the focus (0222)",
        one_ok,
        f"prescription={presc1:.2f} focus={None if focus1 is None else round(focus1,2)} camera_track={track1:.2f} "
        f"(expect track==focus)",
    ))

    # ===================== (C) CAUSAL ================================================ #
    causal = (
        focus2 is not None
        and abs(track2 - presc2) > _TOL       # the camera did NOT follow the overshot prescription row
        and abs(presc2 - focus2) > 10.0        # ... which is a real plate (~32 mm) behind the focus
    )
    checks.append(Check(
        "CAUSAL: the two-mirror camera-track z is the focus, NOT the prescription row (a plate behind the detector)",
        causal,
        f"track={track2:.2f} vs prescription={presc2:.2f} (delta {track2-presc2:+.2f}); "
        f"prescription is {presc2-(focus2 or presc2):+.2f} mm past the focus",
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
