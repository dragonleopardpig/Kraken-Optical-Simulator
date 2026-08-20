"""Guard for bugs/0634 — the camera + lens catalog matcher (pure logic).

Tests every registered camera against every catalog lens for a FOV / resolution / WD
requirement (bugs/0631 relations). This guards the pure matching core on synthetic
catalogs; the real enumeration + dialog are exercised separately.

Checks (display-free):
  A  PASS — a compatible camera+lens passes all four hard fits (resolution, magnification,
     WD, image circle) with the numbers right (m, WD).
  B  each FAILURE mode isolates — pixel count, magnification range, working distance,
     image circle — and reports a reason.
  C  f/# is ADVISORY — a too-slow lens is flagged (fnumber_ok False) but still `passes`
     when the four hard fits are met; unknown f/# leaves fnumber_ok None.
  D  match_catalog orders passing first, then fewest failed criteria, then WD margin.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0634_catalog_matcher
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_matcher import (
        CameraSpec,
        LensSpec,
        MatchRequirement,
        match_catalog,
        match_combination,
    )

    req = MatchRequirement(fov_w_mm=55, fov_h_mm=55, resolution_um_per_px=12, wd_min_mm=150, wavelength_um=0.55)
    cam = CameraSpec("hr25MCX", 23.04, 23.04, 5120, 5120)

    # ---------------------------------------------------------------- A: a passing combo
    good = LensSpec("Apo75", focal_length_mm=75, image_circle_mm=32.6, fnumber=4.0)
    r = match_combination(req, cam, good)
    if not r.passes:
        ok = False
        notes.append(f"FAIL: A (bugs/0634): compatible combo did not pass ({r.reasons})")
    elif abs(r.magnification - 23.04 / 55) > 1e-6 or r.working_distance_mm is None or abs(r.working_distance_mm - 75 * (1 + 55 / 23.04)) > 1e-3:
        ok = False
        notes.append(f"FAIL: A (bugs/0634): m/WD wrong (m={r.magnification}, WD={r.working_distance_mm})")
    else:
        notes.append(f"PASS: A: compatible combo passes (m={r.magnification:.3g}, WD={r.working_distance_mm:.1f})")

    # ---------------------------------------------------------------- B: failure modes
    under_pixels = match_combination(req, CameraSpec("small", 12.8, 12.8, 2000, 2000), good)
    fixed_mag = match_combination(req, cam, LensSpec("PYRITE", focal_length_mm=85, image_circle_mm=62.5, mag_min=0.5, mag_max=2.0))
    short_wd = match_combination(MatchRequirement(55, 55, 12, wd_min_mm=1000), cam, good)
    small_circle = match_combination(req, cam, LensSpec("Tiny", focal_length_mm=50, image_circle_mm=16.0))
    checks = [
        (not under_pixels.resolution_ok, "resolution"),
        (not fixed_mag.magnification_ok, "magnification range"),
        (not short_wd.working_distance_ok, "working distance"),
        (not small_circle.image_circle_ok, "image circle"),
    ]
    bad = [label for good_flag, label in checks if not good_flag]
    if bad:
        ok = False
        notes.append(f"FAIL: B (bugs/0634): failure mode(s) not caught: {bad}")
    elif not (under_pixels.reasons and fixed_mag.reasons and short_wd.reasons and small_circle.reasons):
        ok = False
        notes.append("FAIL: B (bugs/0634): a failure produced no reason string")
    else:
        notes.append("PASS: B: resolution / mag-range / WD / image-circle each isolate + report")

    # ---------------------------------------------------------------- C: f/# advisory
    slow = match_combination(req, cam, LensSpec("Slow", focal_length_mm=75, image_circle_mm=32.6, fnumber=11.0))
    unknown = match_combination(req, cam, LensSpec("NoFno", focal_length_mm=75, image_circle_mm=32.6))
    if slow.fnumber_ok is not False:
        ok = False
        notes.append("FAIL: C (bugs/0634): a slow lens was not flagged over the diffraction budget")
    elif not slow.passes:
        ok = False
        notes.append("FAIL: C (bugs/0634): the f/# advisory GATED passes (should be advisory only)")
    elif unknown.fnumber_ok is not None:
        ok = False
        notes.append("FAIL: C (bugs/0634): unknown f/# did not report None")
    else:
        notes.append("PASS: C: f/# is advisory (flags but does not fail); unknown → None")

    # ---------------------------------------------------------------- D: ordering
    lenses = [
        LensSpec("Tiny", focal_length_mm=50, image_circle_mm=16.0),       # fails image circle
        LensSpec("Apo75", focal_length_mm=75, image_circle_mm=32.6, fnumber=4.0),   # passes, WD 254
        LensSpec("LongApo", focal_length_mm=100, image_circle_mm=40.0, fnumber=4.0),  # passes, WD 338 (more margin)
    ]
    ordered = match_catalog(req, [cam], lenses)
    if not (ordered[0].passes and ordered[1].passes):
        ok = False
        notes.append(f"FAIL: D (bugs/0634): passing combos not sorted first ({[o.lens for o in ordered]})")
    elif ordered[0].lens != "LongApo":
        ok = False
        notes.append(f"FAIL: D (bugs/0634): larger WD-margin combo not ranked first ({ordered[0].lens})")
    elif ordered[-1].passes:
        ok = False
        notes.append("FAIL: D (bugs/0634): a failing combo was not last")
    else:
        notes.append("PASS: D: passing first, ranked by WD margin, failing last")

    # ---------------------------------------------------------------- E: magnification parse
    from KrakenOS.UI.services.system_matcher import (
        enumerate_cameras,
        parse_magnification_range,
    )

    parse_cases = {
        "PYRITE_45_85_05x-20x_V38_1072517": (0.5, 2.0),  # compact range (not 85_05!)
        "PYRITE_56_120_10x_V38": (1.0, 1.0),             # single, trailing "_V38"
        "PYRITE_56_100_V38_1097303": None,               # no mag token
        "ELS-85-4.5V16K": None,                          # "4.5V" is not a token
        "0.5x-2.0x": (0.5, 2.0),                         # literal decimals
    }
    parse_bad = [t for t, exp in parse_cases.items() if parse_magnification_range(t) != exp]
    if parse_bad:
        ok = False
        notes.append(
            f"FAIL: E (bugs/0634): magnification parse wrong for {parse_bad} "
            "(the '85_05'/'10x_V38' traps)"
        )
    else:
        notes.append("PASS: E: magnification range parses PYRITE compact + literal, rejects non-tokens")

    # ---------------------------------------------------------------- F: enumeration + wiring
    # enumerate_cameras is fast (no PDF); the slow lens scrape is left to the diag probe.
    from KrakenOS.UI.panels import main_window as mw
    from KrakenOS.UI.services import layout_table_workbench as wb
    from KrakenOS.UI.services import system_matcher as sm

    try:
        cams = enumerate_cameras()
    except Exception as exc:  # noqa: BLE001
        cams = []
        notes.append(f"(enumerate_cameras raised {exc!r})")
    editor_has = any(
        isinstance(cls, type) and "open_camera_lens_matcher" in vars(cls) for cls in vars(wb).values()
    )
    if not cams:
        ok = False
        notes.append("FAIL: F (bugs/0634): enumerate_cameras returned no registered cameras")
    elif not any(c.pixels_w > 0 and c.sensor_w_mm > 0 for c in cams):
        ok = False
        notes.append("FAIL: F (bugs/0634): enumerated cameras have no sensor/pixel data")
    elif not hasattr(sm, "open_catalog_matcher_dialog") or not editor_has:
        ok = False
        notes.append("FAIL: F (bugs/0634): matcher dialog / editor method missing")
    elif "open_camera_lens_matcher" not in inspect.getsource(mw):
        ok = False
        notes.append("FAIL: F (bugs/0634): the Actions menu does not open the matcher")
    else:
        notes.append(f"PASS: F: {len(cams)} cameras enumerated; dialog + editor + menu wired")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Catalog-matcher validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
