"""Display-free guard for bugs/0297 -- the folded FOV solve must target the SAME first order the
magnification readout (and the ray trace) use.

The user typed 54x54 into the object-plane FOV popup on the two-fold AZ85 periscope, pinned
object->mirror = 50 mm and mirror->sensor = 30 mm, hit Solve for Thickness -- and got a FOV of
58.8x58.8 with the system left out of focus (recording 20260713_200738, flags 3+4).

Root cause: ``_folded_conjugate_gaps_for_magnification`` solved against a hand-carved LENS-ONLY
first order (the rows between the first and last lens surface, the fold mirrors EXCLUDED). The RA
folds are BK7 right-angle PRISMS -- ~25 mm of glass each, a reduced path of t(1-1/n) ~ 8.5 mm on
EVERY leg -- so dropping them put the solved conjugate ~8.5 mm out on each side: the scene stayed
defocused (~20 mm) and the achieved |m| missed the target by ~9%. The magnification readout, which
reads the straight-equivalent reference (prisms kept as glass plates, bugs/0219), was CORRECT and
matched the ray trace to 5 digits -- so it honestly reported the FOV the wrong solve had produced.

Fix: one ``_shared_first_order_reference`` (cardinals + their absolute z in the reference frame)
that the readout AND the solve both read, with the Gaussian conjugate inverted on it directly:
object->H = f(1 + 1/m), H'->image = f(1 + m). Plus: the gap sums no longer clamp at zero, because
seating the detector at best focus on a folded scene legitimately drives the trailing mirror's gap
NEGATIVE -- clamping made a pinned image leg land ~8.5 mm short of the value the user typed.

  (A) SOLVE HITS THE TARGET: after fov_solve(object, thickness, W, W) the magnification READOUT
      equals the requested sensor/object ratio (it was ~9% off).
  (B) SOLVE LANDS IN FOCUS: the shared reference reports ~zero residual defocus AND the real
      folded ray trace lands a tight spot on the sensor (it was a ~1 mm RMS blur).
  (C) PINNED LEG SURVIVES A NEGATIVE GAP: with the trailing image gap seated negative (what the
      best-focus snap writes), pinning mirror->sensor = X yields EXACTLY X.
  (D) SHARED: the readout and the folded solve both source their first order from
      ``_shared_first_order_reference`` -- a refactor that re-forks them trips this guard.
  (E) NON-FOLDED UNTOUCHED: the folded helper still returns None on an unfolded scene, so the
      plain conjugate path is unchanged.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_conjugate_first_order
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin
from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin
from KrakenOS.UI.validate_open3d_folded_fov_solve import _load_unfolded, _qe
from KrakenOS.UI.validate_open3d_two_fold_image_arm_follow import _two_fold_editor

_FOV = 54.0          # the width the user typed
_IMAGE_LEG = 30.0    # the "last distance" the user pinned


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _residual_defocus(editor) -> float:
    """How far the prescription image plane sits from the conjugate, per the shared reference.
    Defensive so a build WITHOUT the shared reference still reports each check (a FAIL), rather
    than dying on the missing attribute before the physics checks are printed."""
    reference = getattr(editor, "_shared_first_order_reference", None)
    if reference is None:
        return float("nan")
    first_order = _quiet(reference)
    mag = _quiet(editor._current_finite_paraxial_magnification)
    if first_order is None or mag is None:
        return float("nan")
    f = float(first_order["f"])
    focus_z = float(first_order["h2_z"]) + f * (1.0 + abs(float(mag)))
    return focus_z - float(first_order["image_z"])


def _axial_spot_rms(editor) -> float:
    """RMS radius of the on-axis bundle where it lands on the sensor, from the REAL folded trace."""
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    detector = next((t for t in bundle.targets if getattr(t, "is_detector", False)), None)
    if detector is None:
        return float("nan")
    centre = np.asarray(detector.center_world, dtype=float).reshape(3)
    normal = np.asarray(getattr(detector, "normal_world", (0, 0, 1)), dtype=float).reshape(3)
    normal = normal / (np.linalg.norm(normal) or 1.0)
    ends = []
    for path in bundle.ray_paths:
        points = np.asarray(path.points_world, dtype=float)[:, :3]
        if len(points) < 2 or np.linalg.norm(points[0][:2]) > 1e-6:
            continue  # on-axis field only
        if abs(float((points[-1] - centre) @ normal)) > 0.05:
            continue  # never reached the sensor
        ends.append(points[-1])
    if len(ends) < 8:
        return float("nan")
    ends = np.asarray(ends)
    return float(np.sqrt(np.mean(np.sum((ends - ends.mean(axis=0)) ** 2, axis=1))))


def validate_folded_conjugate_first_order() -> list[Check]:
    checks: list[Check] = []

    editor = _two_fold_editor()
    qe = _qe(editor)
    sensor_semi = float(_quiet(qe._sensor_semi))
    object_semi = ((_FOV ** 2 + _FOV ** 2) ** 0.5) / 2.0
    target = sensor_semi / object_semi

    ok, msg = _quiet(qe.fov_solve, "object", "thickness", _FOV, _FOV, None)
    readout = _quiet(editor._current_finite_paraxial_magnification)

    # ---- (A) the solve reaches the magnification the user asked for -------------------------- #
    hit = ok and readout is not None and abs(abs(float(readout)) - target) <= 1e-6 * target
    checks.append(Check(
        "SOLVE HITS THE TARGET: the readout |m| after the solve equals the requested sensor/object ratio",
        bool(hit),
        f"target |m|={target:.6f} readout={None if readout is None else round(abs(float(readout)), 6)} "
        f"(FOV {'n/a' if readout is None else round(2 * sensor_semi / abs(float(readout)) / (2 ** 0.5), 3)} mm "
        f"vs the {_FOV} mm typed) ok={ok}",
    ))

    # ---- (B) ... and leaves the system in focus, per the REAL folded trace ------------------- #
    residual = _residual_defocus(editor)
    spot = _axial_spot_rms(editor)
    focused = abs(residual) <= 1e-3 and np.isfinite(spot) and spot <= 0.02
    checks.append(Check(
        "SOLVE LANDS IN FOCUS: zero residual defocus and a tight traced spot on the sensor",
        bool(focused),
        f"residual defocus={residual:+.5f} mm, traced on-axis spot RMS={spot:.5f} mm",
    ))

    # ---- (C) a pinned image leg survives the negative gap the best-focus snap writes --------- #
    seated = _two_fold_editor()
    mirror_row = int(_quiet(seated._folded_image_conjugate_split)["mirror_row"])
    # Seat the detector at best focus -- exactly what the snap does, and what drives the trailing
    # mirror's gap NEGATIVE (its row carries a 40 mm axial reserve that is not optical path).
    seated.rows[mirror_row].thickness = (
        float(seated.rows[mirror_row].thickness) + _residual_defocus(seated)
    )
    negative_gap = float(seated.rows[mirror_row].thickness)
    ok_split, msg_split = _quiet(seated._apply_folded_image_split, "far", _IMAGE_LEG)
    after = _quiet(seated._folded_image_conjugate_split)
    pinned = float(after["far"]) if after else float("nan")
    honoured = bool(ok_split) and abs(pinned - _IMAGE_LEG) <= 1e-6
    checks.append(Check(
        "PINNED LEG SURVIVES A NEGATIVE GAP: pinning mirror->sensor yields exactly the typed value",
        honoured,
        f"seated gap={negative_gap:+.4f} mm (negative={negative_gap < 0}) -> pinned far leg="
        f"{pinned:.6f} mm (asked {_IMAGE_LEG}) ok={ok_split}",
    ))

    # ---- (D) the readout and the solve read the SAME first order ----------------------------- #
    mag_src = inspect.getsource(LayoutSceneBundleDisplayMixin._current_finite_paraxial_magnification)
    solve_src = inspect.getsource(ParaxialToolsMixin._folded_conjugate_gaps_for_magnification)
    shared = (
        "_shared_first_order_reference" in mag_src
        and "_shared_first_order_reference" in solve_src
        and hasattr(ParaxialToolsMixin, "_shared_first_order_reference")
    )
    checks.append(Check(
        "SHARED: the magnification readout and the folded FOV solve both read _shared_first_order_reference",
        shared,
        f"readout={'_shared_first_order_reference' in mag_src} "
        f"solve={'_shared_first_order_reference' in solve_src}",
    ))

    # ---- (E) an unfolded scene still takes the plain conjugate path -------------------------- #
    try:
        unfolded = _load_unfolded()
        still_none = _quiet(unfolded._folded_conjugate_gaps_for_magnification, 0.5) is None
        detail_e = f"unfolded helper returns None: {still_none}"
    except Exception as exc:  # noqa: BLE001
        still_none = False
        detail_e = f"unfolded load failed: {exc!r}"
    checks.append(Check(
        "NON-FOLDED UNTOUCHED: the folded helper returns None on an unfolded scene (plain path used)",
        still_none,
        detail_e,
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_conjugate_first_order()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_conjugate_first_order()
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if any(not c.ok for c in checks):
        raise SystemExit(1)
    print("Folded-conjugate-first-order validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
