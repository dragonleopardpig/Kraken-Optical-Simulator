"""Display-free guard for bugs/0161: object/point-source rays are a real CONE.

A plain SEQUENTIAL point source (object illumination) must revolve into a true
rotationally-symmetric 3D cone -- NOT collapse to a flat meridional fan. The fan
collapse is kept ONLY for the bug-0126 carve-out (a scene forced non-sequential
by an in-line refractive mesh solid, whose revolved mesh traces are too slow:
Ray Count 20 -> 201 traces -> ~70 s).

The cone's X=0 meridional slice must still read as the even Ray-Count fan -- and
for an ODD Ray Count that slice is EXACTLY ``linspace(-R, R, N)`` (the meridional
spokes land on ``R * j / n_rings`` with ``n_rings = N // 2``). Hence the Ray
Count control is discretised to odd steps (``RAY_FAN_COUNT_VALUES``).

The guard binds the real ``TracePreviewSamplingMixin`` methods onto a light fake
editor (no display) and checks the cone geometry, the slice, the carve-out, the
odd discrete steps, and that the cone totals stay under the draw budget.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_sequential_cone_is_cone

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.three_d_scene_tools import _RAY_DRAW_BUDGET_CONE
from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin
from KrakenOS.UI.source_trace_helpers import RAY_FAN_COUNT_DEFAULT, RAY_FAN_COUNT_VALUES

_EPS = 1e-9


class _ConeEditor:
    """Fake editor binding the REAL cone sampler + gate (exercises production code)."""

    rows: list = []
    _sample_ray_count_cone_points = TracePreviewSamplingMixin._sample_ray_count_cone_points
    _launch_cone_prefers_flat_fan = TracePreviewSamplingMixin._launch_cone_prefers_flat_fan
    _cone_azimuth_count = TracePreviewSamplingMixin._cone_azimuth_count

    def __init__(self, count: int, *, prefers_fan: bool, use_nonseq: bool) -> None:
        self._count = int(count)
        self._prefers_fan = bool(prefers_fan)
        self._use_nonseq = bool(use_nonseq)

    def _current_ray_count(self) -> int:
        return self._count

    def _launch_pupil_prefers_meridional_fan(self) -> bool:
        return self._prefers_fan

    def _resolved_trace_mode(self, *, system=None) -> dict:
        return {"use_nonseq": self._use_nonseq}

    def _current_display_slice_axis(self) -> str:
        return "y"


def _meridional_slice_heights(points: np.ndarray) -> np.ndarray:
    """Sorted unique Y heights of the X=0 (90/270 deg) meridional spokes + centre."""
    on_axis = points[np.abs(points[:, 0]) < 1e-6]
    return np.unique(np.round(on_axis[:, 1], 6))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    radius = 25.0

    # 1) A plain SEQUENTIAL scene revolves into a real cone (the 0161 fix): more
    #    than N rays, and genuine off-meridian spokes (not a flat planar fan).
    for n in (5, 13, 21, 31):
        editor = _ConeEditor(n, prefers_fan=True, use_nonseq=False)
        pts = np.asarray(editor._sample_ray_count_cone_points(radius), dtype=float)
        n_rings = max(1, n // 2)
        n_az = editor._cone_azimuth_count()
        expected_total = 1 + n_rings * n_az
        if pts.shape[0] != expected_total:
            failures.append(
                f"FAIL: sequential cone N={n} drew {pts.shape[0]} samples, expected {expected_total}"
            )
        off_meridian = np.any((np.abs(pts[:, 0]) > _EPS) & (np.abs(pts[:, 1]) > _EPS))
        if not off_meridian:
            failures.append(f"FAIL: sequential cone N={n} is still a flat fan (no off-meridian spokes)")

        # 2) Its X=0 slice is EXACTLY the odd N-ray linspace fan. Equality to
        #    linspace(-R, R, N) IS the even-gap guarantee (linspace is uniform).
        heights = _meridional_slice_heights(pts)
        expected = np.linspace(-radius, radius, n)
        if heights.size != n or not np.allclose(heights, expected, atol=1e-6):
            failures.append(
                f"FAIL: sequential cone N={n} slice is not the even N-ray fan "
                f"(got {heights.size} heights: {heights.tolist()})"
            )

    # 3) The bug-0126 carve-out (non-seq inline solid) still keeps the FLAT fan.
    for n in (5, 13, 21):
        editor = _ConeEditor(n, prefers_fan=True, use_nonseq=True)
        pts = np.asarray(editor._sample_ray_count_cone_points(radius), dtype=float)
        if pts.shape[0] != n:
            failures.append(f"FAIL: 0126 carve-out N={n} drew {pts.shape[0]} rays, expected flat {n}")
        elif float(np.max(np.abs(pts[:, 0]))) > _EPS:
            failures.append(f"FAIL: 0126 carve-out N={n} is not a flat meridional fan (X != 0)")

    # 4) The discrete Ray-Count steps are all ODD (so every slice is exactly N).
    for value in RAY_FAN_COUNT_VALUES:
        if int(value) % 2 == 0:
            failures.append(f"FAIL: Ray-Count step {value!r} is even (breaks the N-ray slice)")
    if RAY_FAN_COUNT_DEFAULT not in RAY_FAN_COUNT_VALUES:
        failures.append(f"FAIL: default Ray Count {RAY_FAN_COUNT_DEFAULT!r} is not one of the discrete steps")

    # 5) Every cone step stays under the cone draw budget (no perf cliff).
    for value in RAY_FAN_COUNT_VALUES:
        n = int(value)
        editor = _ConeEditor(n, prefers_fan=True, use_nonseq=False)
        total = 1 + max(1, n // 2) * editor._cone_azimuth_count()
        if total > _RAY_DRAW_BUDGET_CONE:
            failures.append(
                f"FAIL: Ray-Count step {n} revolves into {total} samples (> budget {_RAY_DRAW_BUDGET_CONE})"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0161 sequential point source is a cone")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] object/point-source rays revolve into a real cone; odd-N slice is the even fan (bugs/0161)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
