#!/usr/bin/env python3
"""Display-free guard for bugs/0104: the OBJECT PLANE must stay visible after a
beam-splitter cube is promoted in a finite-conjugate (machine-vision) scene.

Why it exists (flag_20260622_071429_544 "Missing object plane after promotion",
flag_20260622_080859_497 "promoted, object plane missing"):
  The user's scene is MV 150mm 1X with a 50mm beam-splitter cube BEFORE the single
  lens. The TRANSMIT arm images through the 150 lens; the REFLECT arm is a BARE
  pickoff (no lens / no aperture). That is ONE imaging arm, so it is NOT a two-arm
  display fold -- the detectors are ray-tree branch detectors with no
  `two_arm_magnification` metadata. The detector-coverage object-FOV rectangle (the
  visible "object plane" when the Det overlay is on, since the row-0 clear-aperture
  disk is suppressed to opacity 0) is only drawn when the paraxial magnification is a
  finite, non-zero number.

  `_current_finite_paraxial_magnification()` only STRAIGHTENED the layout for a folding
  Mirror, not for a beam splitter, so the conjugate solve threw on the splitter and the
  method returned None -> object_fov_half_width == 0 -> the object plane vanished. The
  fix straightens whenever `_layout_needs_paraxial_reference()` is True (mirror OR beam
  splitter OR promoted mesh solid), reusing the transmissive flat-plate reference every
  other first-order consumer already uses.

What it checks:
  A. A beam-splitter single-imaging-arm finite scene now yields a FINITE, non-zero
     `_current_finite_paraxial_magnification()` (was None -- the bug).
  B. That magnification makes the detector-coverage object-FOV half-width > 0 (the
     object plane WOULD be drawn).
  C. A plain refractive finite scene is unchanged (still ~its magnification), and the
     change is gated on `_layout_needs_paraxial_reference` (source check) so it cannot
     silently regress to mirror-only.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_object_plane_after_promote

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io

import numpy as np

_BS_SETTINGS = {
    "split_mode": "Deterministic paths", "reflectance": 0.5, "absorption": 0.0,
    "transmit_phase_deg": 0.0, "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3, "max_branch_depth": 8,
}


def _editor(specs):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
    from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SETTINGS

    rows = [KrakenLayoutEditor._row_from_layout_item(dict(s)) for s in specs]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    settings = dict(SETTINGS)
    settings["trace_mode"] = "Non-Sequential Preview"
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return _snapshot_editor(rows, settings)


def _plain_specs():
    from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SURFACES
    return [dict(s) for s in SURFACES]


def _splitter_specs():
    """MV 150 1X + a 50mm beam-splitter cube before the single lens (reflect arm BARE)."""
    s = _plain_specs()
    object_to_bs = 176.43
    s[0] = dict(s[0], thickness=object_to_bs)
    splitter = {
        "element": "Splitter", "surface": "Beam Splitter", "name": "50 mm cube splitter",
        "rc": 0.0, "k": 0.0, "thickness": 275.0 - object_to_bs, "diameter": 50.0,
        "tilt_x": 45.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0, "glass": "AIR",
        "advanced": {"BeamSplitter": _BS_SETTINGS,
                     "Element": {"element_name": "50 mm cube splitter", "branch_selector": ""}},
    }
    return [s[0], splitter] + s[1:]


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # A) The beam-splitter single-imaging-arm scene now has a finite, non-zero magnification.
    bs_editor = _editor(_splitter_specs())
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        bs_mag = bs_editor._current_finite_paraxial_magnification()
        needs_ref = bool(bs_editor._layout_needs_paraxial_reference(bs_editor.rows))
    if not needs_ref:
        failures.append("FAIL: the beam-splitter scene should report _layout_needs_paraxial_reference()=True")
    if bs_mag is None or not np.isfinite(bs_mag) or abs(bs_mag) < 1e-9:
        failures.append(
            f"FAIL: beam-splitter scene magnification must be finite & non-zero (object plane), got {bs_mag!r}")

    # B) That magnification makes the object-FOV half-width > 0 (the object plane is drawn).
    from KrakenOS.UI.services.detector_coverage_overlay import detector_coverage_metrics
    metrics = detector_coverage_metrics(23.0, 23.0, 16.5, bs_mag)
    if not (metrics.object_fov_half_width > 1e-9 and metrics.object_fov_half_height > 1e-9):
        failures.append(
            f"FAIL: object-FOV half-width must be > 0 so the object plane draws "
            f"(got {metrics.object_fov_half_width!r} from mag {bs_mag!r})")

    # C) Regression: a plain refractive finite scene is unchanged (~1X), and the
    #    straightening is gated on _layout_needs_paraxial_reference (not mirror-only).
    plain_editor = _editor(_plain_specs())
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        plain_mag = plain_editor._current_finite_paraxial_magnification()
    if plain_mag is None or not np.isfinite(plain_mag) or abs(abs(plain_mag) - 1.0) > 0.05:
        failures.append(f"FAIL: plain MV 150 1X magnification regressed (expected ~1X, got {plain_mag!r})")

    # bugs/0440: the straighten gate moved INTO the shared first-order reference
    # (bugs/0297 -- ONE first order for every conjugate consumer), so inspect the
    # DELEGATION CHAIN, not just the magnification method: the stale single-method
    # source check false-failed this guard from the 0297 refactor onward (it sat
    # mis-binned in the 0434 environmental baseline until flag_20260726_111415).
    src = inspect.getsource(type(bs_editor)._current_finite_paraxial_magnification)
    chain_src = src
    if "_shared_first_order_reference" in src:
        chain_src += inspect.getsource(type(bs_editor)._shared_first_order_reference)
    if "_layout_needs_paraxial_reference" not in chain_src:
        failures.append(
            "FAIL: the magnification's first-order chain must straighten on "
            "_layout_needs_paraxial_reference (beam splitter / solid), not just a Mirror")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0104 object plane must stay visible after a beam-splitter cube promotion")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] beam-splitter (single imaging arm) scene keeps a finite magnification -> "
          "object plane / object-FOV stays drawn (bugs/0104)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
