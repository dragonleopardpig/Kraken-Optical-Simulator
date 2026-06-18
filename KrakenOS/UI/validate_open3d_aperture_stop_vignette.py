#!/usr/bin/env python3
"""Display-free regression for bugs/0093: the non-sequential trace VIGNETTES a ray
that lands outside an APERTURE STOP's clear aperture, instead of skipping the finite
stop and shooting it straight through.

Root (recording flag_20260618_231705, the 150mm machine-vision 1X datasheet scene):
promoting a cube before the lens forces non-seq mode, and there a ray outside the
aperture stop was not chosen by `__NonSequentialChooser` and sailed straight on,
unrefracted and unblocked -> the diverging rays. A real stop blocks rays outside its
clear aperture. The build flags the stop (`IsApertureStop`); the trace terminates
such a ray AT the stop plane.

Asserts:
  - the 1X datasheet builds with its Aperture Stop flagged;
  - a ray mapping INSIDE the stop reaches the image; one OUTSIDE terminates at the
    stop plane (vignetted), NOT at the image;
  - a scene with NO aperture stop sets no flag and is not spuriously vignetted.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_aperture_stop_vignette

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io

import numpy as np


def _build(specs):
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs([dict(s) for s in specs])
        system.energy_probability = 0
    return system


def _end_z(system, y, obj_to_front=275.0, wl=0.546):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system.NsTrace([0.0, 0.0, 0.0], [0.0, y / obj_to_front, 1.0], wl)
    return float(np.asarray(system.RAY[-1], dtype=float).reshape(-1)[2])


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SURFACES

    failures: list[str] = []
    system = _build(SURFACES)

    # the stop is surface [3] (Aperture Stop, clear radius 9.68 mm); image at z=595.81.
    stop = next((s for s in system.SDT if bool(getattr(s, "IsApertureStop", False))), None)
    if stop is None:
        failures.append("FAIL: the Aperture Stop was not flagged IsApertureStop at build time")
        return (not failures), failures
    if abs(float(stop.Diameter) - 19.356) > 0.5:
        failures.append(f"FAIL: flagged stop has unexpected diameter {float(stop.Diameter)} (expected ~19.356)")

    STOP_Z, IMAGE_Z = 300.86, 595.81
    # ray mapping INSIDE the stop -> reaches the image.
    inside = _end_z(system, 2.0)
    if abs(inside - IMAGE_Z) > 3.0:
        failures.append(f"FAIL: an on-axis-ish ray (inside the stop) should reach the image z~595.8, got {inside:.1f}")
    # ray mapping OUTSIDE the stop -> vignetted AT the stop plane (not the image, not beyond).
    outside = _end_z(system, 13.4)
    if abs(outside - STOP_Z) > 3.0:
        failures.append(
            f"FAIL: a marginal ray outside the stop should be VIGNETTED at the stop z~300.9, "
            f"got {outside:.1f} (reaches image / shoots through = the diverging-rays bug)"
        )

    # a scene with NO aperture stop: no flag set, no spurious vignette (random-element
    # robustness -- only an explicit stop blocks rays).
    singlet = [
        {"surface": "Object", "name": "O", "rc": 0.0, "thickness": 100.0, "diameter": 50.0, "glass": "AIR"},
        {"surface": "Standard", "name": "L1", "rc": 60.0, "thickness": 8.0, "diameter": 40.0, "glass": "BK7"},
        {"surface": "Standard", "name": "L2", "rc": -60.0, "thickness": 120.0, "diameter": 40.0, "glass": "AIR"},
        {"surface": "Image", "name": "I", "rc": 0.0, "thickness": 0.0, "diameter": 50.0, "glass": "AIR"},
    ]
    s2 = _build(singlet)
    if any(bool(getattr(x, "IsApertureStop", False)) for x in s2.SDT):
        failures.append("FAIL: a scene with no Aperture surface should set no IsApertureStop flag")
    # an on-axis ray must still trace past the lens (not vignetted by anything).
    if _end_z(s2, 1.0, obj_to_front=100.0, wl=0.55) <= 120.0:
        failures.append("FAIL: a no-stop singlet on-axis ray was spuriously blocked before the image")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0093 aperture-stop vignette (non-seq)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] non-seq trace vignettes rays outside the aperture stop (bugs/0093)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
