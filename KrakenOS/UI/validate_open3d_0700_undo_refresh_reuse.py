"""Guard for bugs/0700 -- "Ctrl-Z to undo the rotation is super slow".

A history restore runs a synchronous full refresh, and two redundancies made it
pay for the om05a non-sequential trace several times over:

  1. `current_or_rebuild_scene` discarded the EXPLICIT fresh products refresh_plot
     had just traced whenever the scene has promoted STEP optical-solid rows, and
     re-ran the identical trace (245 s -> two traces). That half is pinned in
     `validate_open3d_promoted_step_refresh` (trust-explicit / refuse-cached /
     mode-gate checks).
  2. `_active_ray_analysis_records` rebuilt a full scene bundle from the raykeeper
     on EVERY call (~23 s each), and one refresh consults it several times
     (branch choices + detector-aperture / throughput / illumination reports).

This validator pins the second half: the per-trace memo on
`_active_ray_analysis_records`.

Checks (display-free, unbound mixin method on a stub):
  A  identical (last_system, last_rays, keeper ray count) -> ONE build, the same
     records object returned.
  B  a NEW rays object (a fresh trace) invalidates.
  C  an in-place keeper append (an additive trace topping up the SAME keeper)
     invalidates via the stored-ray count.
  D  a NEW system object invalidates.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0700_undo_refresh_reuse
"""

from __future__ import annotations

from KrakenOS.UI.services.analysis_reports import AnalysisReportsMixin


class _Keeper:
    def __init__(self, count: int) -> None:
        self.CC = [object() for _ in range(count)]


class _Stub:
    """Editor stub: counts underlying record builds."""

    def __init__(self, system, rays) -> None:
        self.last_system = system
        self.last_rays = rays
        self.build_calls = 0

    def _ray_analysis_records_for_trace(self, *, system, rays):
        self.build_calls += 1
        return [{"build": self.build_calls}]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    system = object()
    rays = _Keeper(3)
    stub = _Stub(system, rays)
    first = AnalysisReportsMixin._active_ray_analysis_records(stub)
    second = AnalysisReportsMixin._active_ray_analysis_records(stub)
    ok(
        stub.build_calls == 1 and first is second,
        f"A: repeated calls on one trace build once and share the records "
        f"(builds={stub.build_calls})",
    )

    stub.last_rays = _Keeper(3)
    AnalysisReportsMixin._active_ray_analysis_records(stub)
    ok(stub.build_calls == 2, f"B: a new rays object invalidates (builds={stub.build_calls})")

    stub.last_rays.CC.append(object())
    AnalysisReportsMixin._active_ray_analysis_records(stub)
    ok(
        stub.build_calls == 3,
        f"C: an in-place keeper append invalidates (builds={stub.build_calls})",
    )

    stub.last_system = object()
    AnalysisReportsMixin._active_ray_analysis_records(stub)
    ok(stub.build_calls == 4, f"D: a new system object invalidates (builds={stub.build_calls})")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0700 undo-refresh reuse validation PASSED")
        return 0
    print("0700 undo-refresh reuse validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
