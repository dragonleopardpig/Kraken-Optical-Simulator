"""Guard for bugs/0718 -- "the program seems freezing" after a forced FOV solve.

A preview trace on the deliberately-crashed / off-conjugate geometry could block the
UI thread forever: (1) the force short-circuit ran a best-focus SNAP trace, and (2)
the auto image-diameter side channel fired a temporary trace whose parallel
``future.result()`` had NO timeout. The fix defers the trace on force AND bounds every
parallel preview trace so a wedged worker cannot hang the UI.

Checks (all source-shape, display-free):
  A  the executor result loop is bounded: a budget constant, a timed result, the
     futures TimeoutError handled, and the worker teardown in the finally.
  B  the force path DEFERS instead of tracing: quick_estimation drops the best-focus
     snap and sets the fast-load gate; the workbench redraw is bodies-only on force.
  C  the fast-load gate still short-circuits the temporary diameter trace.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0718_force_solve_freeze
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: bounded parallel preview trace -------------------------------------
    from KrakenOS.UI.services import trace_preview as tp

    budget = getattr(tp, "_PREVIEW_TRACE_RESULT_BUDGET_SECONDS", None)
    ok(
        isinstance(budget, (int, float)) and 10.0 <= float(budget) <= 600.0,
        f"A1: a preview-trace result budget constant exists and is sane ({budget!r})",
    )
    bundles_src = inspect.getsource(tp.TracePreviewService._trace_preview_bundles)
    ok(
        "future.result(timeout=" in bundles_src
        and "_PREVIEW_TRACE_RESULT_BUDGET_SECONDS" in bundles_src,
        "A2: the parallel result wait is bounded by the budget (no unbounded .result())",
    )
    ok(
        "_futures.TimeoutError" in bundles_src and "timed_out" in bundles_src,
        "A3: a chunk timeout is caught and abandons the remaining chunks",
    )
    ok(
        "self._shutdown_analysis_executor()" in bundles_src,
        "A4: the finally tears the executor down (force-terminates wedged workers)",
    )
    # the unbounded form must be gone -- a bare future.result() with no timeout would
    # re-open the freeze.
    import re

    ok(
        re.search(r"\.result\(\s*\)", bundles_src) is None,
        "A5: no bare future.result() remains in the parallel path",
    )

    # ---- B: the force path defers the trace ------------------------------------
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    apply_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "_preview_trace_deferred_until_requested = True" in apply_src
        and "snap_detector_to_image_plane" not in apply_src,
        "B1: force short-circuit sets the fast-load gate and drops the best-focus snap",
    )

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    solve_src = inspect.getsource(LayoutTableWorkbenchMixin.solve_fov_to_inspection_face)
    ok(
        "refresh_plot(defer_trace=bool(force and ok))" in solve_src,
        "B2: a forced solve redraws BODIES only (defer_trace) -- no trace on the crash",
    )

    # B3 is the fix that actually stopped the freeze: the 3D-inspector rebuild
    # (reached from refresh_plot UNCONDITIONALLY) must honour the fast-load gate too,
    # else it runs the in-process NsTraceLoop on the crashed geometry and wedges.
    from KrakenOS.UI.services import open3d_trace_refresh as otr

    rebuild_src = inspect.getsource(otr.Open3DTraceRefreshService.current_or_rebuild_scene)
    ok(
        "_preview_trace_deferred_until_requested" in rebuild_src
        and "trace_rays=not deferred" in rebuild_src,
        "B3: the 3D rebuild (refresh_plot path) honours the fast-load gate (bodies-only "
        "while deferred), so the force path never runs the in-process NS trace on the crash",
    )
    # Every 3D refresh entry must honour the gate, not just the refresh_plot path:
    # refresh_from_editor routes through build_inspector_refresh, and a bodies-only
    # rebuild leaves the scene trace-dirty, so a later refresh would force_retrace and
    # wedge. The gate must beat both physics-requested and force_retrace.
    binsp_src = inspect.getsource(otr.Open3DTraceRefreshService.build_inspector_refresh)
    ok(
        "_preview_trace_deferred_until_requested" in binsp_src
        and "trace_rays = False" in binsp_src,
        "B4: build_inspector_refresh (the refresh_from_editor path) also stays bodies-only "
        "while the gate is set",
    )

    # ---- C: the fast-load gate still guards the temporary diameter trace -------
    from KrakenOS.UI.services import trace_preview_sampling as tps

    diam_src = inspect.getsource(tps.TracePreviewSamplingMixin._traced_image_diameter_value)
    ok(
        "_preview_trace_deferred_until_requested" in diam_src and "return None" in diam_src,
        "C1: the auto-diameter trace is skipped while the fast-load gate is set (bugs/0646)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0718 force-solve freeze validation PASSED")
        return 0
    print("0718 force-solve freeze validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
