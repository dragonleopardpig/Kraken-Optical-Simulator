#!/usr/bin/env python3
"""Display-free regression for bugs/0095 + 0096: "Ray Fan count = N" is LITERAL.

KrakenOS's ``PupilCalc.Samp`` is a per-axis sampling *density*, not a ray count
(a meridional fan emits ``2*Samp+1`` rays, hexapolar ``1+3*Samp*(Samp+1)``), and
the default pattern label "Meridional fan" was missing from ``PUPIL_PATTERN_TO_KRAKEN``
so ``_current_kraken_pupil_pattern()`` returned ``None`` and the launch silently fell
back to **Hexapolar**. So a user setting "Ray Fan count = 5" got 91 rays (~50 after
aperture clipping) in the 3-D view, and the 2-D YZ projection collapsed that dense
grid to ~3 visible lines -- neither equal to 5.

The fix maps "Meridional fan" -> ``fany`` and inverts ``Samp`` per pattern
(``kraken_pattern_samp_for_count``) so the finite/angular display bundles draw N
rays per field in the selected pattern, identical in 2-D and 3-D.

Asserts:
  - "Meridional fan" maps to ``fany`` (no Hexapolar fallback);
  - a meridional fan of N is EXACTLY N rays, all in the tangential plane (Cordx == 0);
  - filled patterns (hexapolar / square) honor the count (>= N, not ~5x over);
  - the Samp inversion is monotone non-decreasing in N.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ray_fan_count

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io

import numpy as np


def _pupil_for_system():
    import KrakenOS as Kos
    from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SURFACES
    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs([dict(s) for s in SURFACES])
        system.energy_probability = 0
        # surface 3 is the Aperture Stop in the datasheet layout
        return Kos.PupilCalc(system, 3, 0.546, "EPD", 26.8)


def _pattern_ray_count(pattern: str, n: int) -> tuple[int, float]:
    from KrakenOS.UI.source_trace_helpers import kraken_pattern_samp_for_count

    pupil = _pupil_for_system()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        pupil.Ptype = pattern
        pupil.Samp = kraken_pattern_samp_for_count(pattern, n)
        pupil.Pattern()
    cordx = np.asarray(pupil.Cordx, dtype=float).ravel()
    return cordx.size, (float(np.max(np.abs(cordx))) if cordx.size else 0.0)


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.source_trace_helpers import (
        PUPIL_PATTERN_DEFAULT,
        PUPIL_PATTERN_TO_KRAKEN,
        kraken_pattern_samp_for_count,
    )

    failures: list[str] = []

    # 1) the default pattern label is mapped (no silent Hexapolar fallback)
    if PUPIL_PATTERN_TO_KRAKEN.get(PUPIL_PATTERN_DEFAULT) != "fany":
        failures.append(
            f"FAIL: default pattern {PUPIL_PATTERN_DEFAULT!r} maps to "
            f"{PUPIL_PATTERN_TO_KRAKEN.get(PUPIL_PATTERN_DEFAULT)!r}, expected 'fany'"
        )

    # 2) a meridional fan of N is EXACTLY N rays, all in the tangential plane
    for n in (3, 5, 7, 11, 21):
        count, max_x = _pattern_ray_count("fany", n)
        if count != n:
            failures.append(f"FAIL: Meridional fan N={n} produced {count} rays, expected {n}")
        if max_x > 1e-9:
            failures.append(f"FAIL: Meridional fan N={n} is not meridional (max|Cordx|={max_x:.4f})")

    # 3) filled patterns honor the count: >= N and not a ~5x blow-up
    for pattern in ("hexapolar", "square"):
        count, _ = _pattern_ray_count(pattern, 21)
        if count < 21:
            failures.append(f"FAIL: {pattern} N=21 produced only {count} rays (< 21)")
        if count > 21 * 3:
            failures.append(f"FAIL: {pattern} N=21 blew up to {count} rays (> 3x)")

    # 4) inversion is monotone non-decreasing in N (more rays never asks for less Samp)
    for pattern in ("fany", "fan", "hexapolar", "square"):
        samps = [kraken_pattern_samp_for_count(pattern, n) for n in range(1, 40)]
        if any(b < a for a, b in zip(samps, samps[1:])):
            failures.append(f"FAIL: Samp inversion for {pattern} is not monotone in N")

    # 5) bugs/0096: the WORLD_CONE sampler (the path "Pupil / field" scenes use,
    #    not the grid bundles above) must honor a meridional fan as a FLAT N-ray
    #    fan -- it previously revolved it into 1 + (N//2)*azimuth rays (N=5 -> 33)
    #    in 3D and a ring-slice in 2D. A flat fan sits entirely at X=0, so the 3D
    #    bundle and the 2D X=0 slice both show exactly N. Non-seq/folded scenes
    #    (prefers_meridional_fan False) still revolve into a filled cone.
    from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin

    class _ConeStub:
        rows: list = []

        def __init__(self, prefers: bool, count: int) -> None:
            self._prefers, self._count = prefers, count

        def _current_ray_count(self) -> int:
            return self._count

        def _launch_pupil_prefers_meridional_fan(self) -> bool:
            return self._prefers

        def _current_display_slice_axis(self) -> str:
            return "y"

        def _cone_azimuth_count(self) -> int:
            return 16

    cone = TracePreviewSamplingMixin._sample_ray_count_cone_points
    for n in (3, 5, 7, 11):
        pts = np.asarray(cone(_ConeStub(True, n), 25.0), dtype=float)
        if pts.shape[0] != n:
            failures.append(f"FAIL: world_cone meridional fan N={n} drew {pts.shape[0]} rays, expected {n}")
        elif float(np.max(np.abs(pts[:, 0]))) > 1e-9:
            failures.append(f"FAIL: world_cone meridional fan N={n} is not meridional (X != 0)")
        elif len(set(np.round(pts[:, 1], 6))) != n:
            failures.append(f"FAIL: world_cone meridional fan N={n} has duplicate heights")
    revolved = np.asarray(cone(_ConeStub(False, 5), 25.0), dtype=float)
    if revolved.shape[0] <= 5:
        failures.append(f"FAIL: non-seq world_cone should revolve into a filled cone, got {revolved.shape[0]} rays")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0095 literal Ray Fan count")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] 'Ray Fan count = N' is a literal per-field ray count, honoring the pattern (bugs/0095)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
