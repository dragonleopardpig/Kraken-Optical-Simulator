"""Display-free guard for bugs/0126.

A scene forced non-sequential ONLY by an in-line refractive mesh solid (a
promoted STEP) keeps a single rotationally-symmetric converging cone about the
global axis -- it never branches or folds. The launch pupil used to hand every
``use_nonseq``/``use_folded`` scene the area-filling disk, which revolved
Ray Count 20 into ``1 + (20//2)*20 = 201`` pupil samples; each is a slow
non-seq mesh trace, so "Show rays" ignored the ray count and "Trace Now" ran for
~70 s (flags flag_20260624_084750_167 + flag_20260624_085043_656).

``_launch_pupil_prefers_meridional_fan`` now collapses such a scene back to the
uniform Ray-Count fan (exactly ``count`` rays) while still handing the disk to
anything that genuinely branches (beam splitter / probabilistic split / diffuse
scatter), folds (mirror), or runs through a tilted / transversely-decentred
element -- failing toward the disk so rays never silently vanish from a split
path. An axial-only ``desp_z`` (an element slid along the axis) must NOT force
the disk.

The guard binds the real ``TracePreviewSamplingMixin`` methods onto a light
fake editor (no display) and checks both the predicate and the resulting pupil
sample count.
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin


class _Row:
    def __init__(
        self,
        surface: str = "Standard",
        *,
        tilt_x: float = 0.0,
        tilt_y: float = 0.0,
        tilt_z: float = 0.0,
        desp_x: float = 0.0,
        desp_y: float = 0.0,
        desp_z: float = 0.0,
        diameter: float = 78.0,
    ) -> None:
        self.surface = surface
        self.tilt_x = tilt_x
        self.tilt_y = tilt_y
        self.tilt_z = tilt_z
        self.desp_x = desp_x
        self.desp_y = desp_y
        self.desp_z = desp_z
        self.diameter = diameter


class _FakeEditor:
    # Bind the REAL methods under test so the guard exercises production code.
    _launch_pupil_prefers_meridional_fan = (
        TracePreviewSamplingMixin._launch_pupil_prefers_meridional_fan
    )
    _scene_breaks_rotational_symmetry = (
        TracePreviewSamplingMixin._scene_breaks_rotational_symmetry
    )
    _sample_ray_count_cone_points = TracePreviewSamplingMixin._sample_ray_count_cone_points
    _sample_ray_count_pupil_points = TracePreviewSamplingMixin._sample_ray_count_pupil_points
    _cone_azimuth_count = TracePreviewSamplingMixin._cone_azimuth_count
    # bugs/0161: the cone sampler now gates on _launch_cone_prefers_flat_fan
    # (flat only for the 0126 non-seq inline solid; sequential scenes revolve).
    _launch_cone_prefers_flat_fan = TracePreviewSamplingMixin._launch_cone_prefers_flat_fan

    def __init__(self, trace_state: dict, rows: list, ray_count: int = 20) -> None:
        self._trace_state = dict(trace_state)
        self.rows = list(rows)
        self._ray_count = int(ray_count)

    def _resolved_trace_mode(self, *, system=None) -> dict:
        return dict(self._trace_state)

    def _current_ray_count(self) -> int:
        return self._ray_count

    def _current_display_slice_axis(self) -> str:
        return "y"


def _expected_disk_count(ray_count: int) -> int:
    n_rings = max(1, ray_count // 2)
    clamped = max(16, min(24, ray_count))
    n_az = int(4 * round(clamped / 4.0))
    return 1 + n_rings * n_az


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True
    radius = 39.0
    ray_count = 20

    on_axis_lens = _Row("Standard", diameter=78.0)
    # The recorded flag: a promoted in-line solid slid +27.5 mm along the axis.
    axial_solid = _Row("Standard", desp_z=27.5, diameter=78.0)

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal passed
        if not cond:
            passed = False
            notes.append(f"FAIL: {label}{(' -- ' + detail) if detail else ''}")
        elif verbose:
            notes.append(f"ok: {label}")

    # A -- sequential, non-folded -> uniform fan (unchanged baseline).
    ed = _FakeEditor({}, [on_axis_lens], ray_count)
    check("A sequential scene prefers the meridional fan", ed._launch_pupil_prefers_meridional_fan())

    # B -- non-seq ONLY because of an axial in-line refractive solid -> fan, and
    # the cone pupil stays at exactly Ray Count rays (THE 0126 FIX).
    ed = _FakeEditor(
        {"use_nonseq": True, "has_optical_stl_solid": True},
        [on_axis_lens, axial_solid],
        ray_count,
    )
    fan = ed._launch_pupil_prefers_meridional_fan()
    check("B axial non-branching solid prefers the fan", fan)
    cone_pts = np.asarray(ed._sample_ray_count_cone_points(radius), dtype=float)
    check(
        "B cone pupil respects Ray Count (no 20 -> 201 explosion)",
        cone_pts.shape[0] == ray_count,
        f"got {cone_pts.shape[0]} pupil samples, expected {ray_count}",
    )

    # C -- a genuine beam splitter still keeps the area-filling disk.
    ed = _FakeEditor({"use_nonseq": True, "has_beam_splitter": True}, [on_axis_lens], ray_count)
    check("C beam-splitter scene keeps the disk", not ed._launch_pupil_prefers_meridional_fan())
    disk_pts = np.asarray(ed._sample_ray_count_cone_points(radius), dtype=float)
    check(
        "C beam-splitter pupil is the full revolved disk",
        disk_pts.shape[0] == _expected_disk_count(ray_count),
        f"got {disk_pts.shape[0]}, expected {_expected_disk_count(ray_count)}",
    )

    # D -- a tilted element breaks rotational symmetry -> disk (rays must not
    # collapse to a flat fan that misses the off-axis deflection).
    ed = _FakeEditor(
        {"use_nonseq": True, "has_optical_stl_solid": True},
        [on_axis_lens, _Row("Standard", tilt_y=5.0)],
        ray_count,
    )
    check("D tilted element keeps the disk", not ed._launch_pupil_prefers_meridional_fan())

    # E -- a transverse decentre (desp_x) breaks symmetry -> disk.
    ed = _FakeEditor(
        {"use_nonseq": True, "has_optical_stl_solid": True},
        [on_axis_lens, _Row("Standard", desp_x=10.0)],
        ray_count,
    )
    check("E transverse decentre keeps the disk", not ed._launch_pupil_prefers_meridional_fan())

    # F -- a folded (mirror) preview keeps the disk.
    ed = _FakeEditor({"use_folded": True}, [on_axis_lens], ray_count)
    check("F folded preview keeps the disk", not ed._launch_pupil_prefers_meridional_fan())

    # G -- a Mirror surface keeps the disk even with only an axial pose.
    ed = _FakeEditor({"use_nonseq": True}, [on_axis_lens, _Row("Mirror", desp_z=12.0)], ray_count)
    check("G mirror surface keeps the disk", not ed._launch_pupil_prefers_meridional_fan())

    # H -- axial desp_z alone must NEVER trip the symmetry breaker.
    ed = _FakeEditor({"use_nonseq": True}, [axial_solid], ray_count)
    check("H axial desp_z does not break rotational symmetry", not ed._scene_breaks_rotational_symmetry())

    # Source contract: the predicate must reason about branching, not bare
    # use_nonseq, and must consult the symmetry helper.
    src = inspect.getsource(TracePreviewSamplingMixin._launch_pupil_prefers_meridional_fan)
    check("source consults has_beam_splitter", "has_beam_splitter" in src)
    check("source consults _scene_breaks_rotational_symmetry", "_scene_breaks_rotational_symmetry" in src)
    check("source consults has_probabilistic_nonseq", "has_probabilistic_nonseq" in src)
    check(
        "source early-returns the fan for non-branched scenes (not a bare use_nonseq->disk)",
        "if not (" in src,
    )

    return passed, notes


if __name__ == "__main__":
    import sys

    ok, all_notes = run_checks(verbose=True)
    for line in all_notes:
        print(line)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)
