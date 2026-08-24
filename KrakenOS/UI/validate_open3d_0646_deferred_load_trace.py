"""Guard for bugs/0646 — loads are fast: rays and the 0625 re-measure are DEFERRED.

User: "the loading of a .py file take super long time, can't you just freeze the ray
first, or don't trace the ray upon startup? Let the user click Trace Now."

Measured (bugs/probe_0646_load_time_breakdown.py, ELS85/Apo75): 24.6 s total --
refresh_plot 18.0 s (the non-sequential preview trace + ray-derived analysis records;
cProfile: _trace_preview_rays_folded_aware 25.9 s of a 43.7 s instrumented refresh) and
the bugs/0625 load-time re-measure 6.5 s. Everything else ~0.2 s.

The fix keeps BOTH doctrines and moves only the timing:
  - loads call refresh_plot(defer_trace=True): geometry-only 2D, trace left DIRTY;
  - loads mark the 0625 re-measure PENDING (_defer_folded_m_relearn_on_load) and
    folded_m_correction() consumes it at the FIRST reader -- which by definition runs
    before any trace/readout could use the raw first order (the 0625 regression class);
  - an eager relearn (swap) clears the marker so a load+swap never re-measures twice;
  - a "Trace Now" button runs the deferred trace without the analysis panels.

Checks (display-free):
  A  every loader defers instead of re-measuring eagerly, and the .py loaders pass
     defer_trace=True to refresh_plot.
  B  folded_m_correction() consumes the pending marker, clearing it BEFORE the
     re-measure runs (re-entrancy: the re-measure's own trace reads this function).
  C  the eager relearn satisfies a pending marker (no double re-measure after a swap).
  D  refresh_plot's defer branch skips the preview trace and leaves the trace DIRTY.
  E  FUNCTIONAL (stub): while the FAST-LOAD state is set, reads return raw 1.0 and do
     NOT consume the pending marker (the load's own labels must not re-measure); once
     cleared, exactly ONE re-measure runs, nested reads do not recurse, marker cleared.
  F  the Trace Now affordance exists (_trace_now handler + toolbar button).
  G  the deferral helper sets the FAST-LOAD state, _traced_image_diameter_value refuses
     to build a temporary trace under it (that label was 25 s of the load profile), and
     both REAL trace entries (refresh_plot's trace branch, the 3D preview bundle) clear
     the state BEFORE tracing so the re-measure lands first.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0646_deferred_load_trace
"""

from __future__ import annotations

import inspect
import re


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_import_export as ie_module
    from KrakenOS.UI.services import layout_table_workbench as wb_module
    from KrakenOS.UI.services import layout_shell_controls as shell_module
    from KrakenOS.UI.services import plot_refresh as plot_module
    from KrakenOS.UI.services import quick_estimation as qe_module
    from KrakenOS.UI.panels import main_window as mw_module

    def _class_src(module, method):
        for name, cls in vars(module).items():
            if isinstance(cls, type) and method in vars(cls):
                return inspect.getsource(getattr(cls, method))
        return ""

    # ---------------------------------------------------------------- A: loaders defer
    load_src = _class_src(wb_module, "load_layout_by_name")
    open_src = _class_src(ie_module, "open_layout")
    problems = []
    for site, src in (("load_layout_by_name", load_src), ("open_layout", open_src)):
        if "_defer_folded_m_relearn_on_load(" not in src:
            problems.append(f"{site}: no deferral marker")
        if "_relearn_folded_m_correction_after_swap(" in src:
            problems.append(f"{site}: still re-measures eagerly (the 6.5 s load cost)")
        if "defer_trace=True" not in src:
            problems.append(f"{site}: refresh_plot without defer_trace (the 18 s load cost)")
    if problems:
        ok = False
        notes.append(f"FAIL: A (bugs/0646): {problems}")
    else:
        notes.append("PASS: A: both .py loaders defer the re-measure AND the preview trace")

    # ---------------------------------------------------------------- B: the consumer
    fmc_src = inspect.getsource(qe_module.folded_m_correction)
    consumes = "_folded_m_relearn_pending" in fmc_src
    clears_first = re.search(
        r"_folded_m_relearn_pending = False\s*\n(?:.*\n)*?\s*.*_relearn_folded_m_correction_after_swap\(",
        fmc_src,
    )
    if not consumes or clears_first is None:
        ok = False
        notes.append(
            "FAIL: B (bugs/0646): folded_m_correction does not consume the pending marker "
            "(or runs the re-measure before clearing it -- re-entrant recursion)"
        )
    else:
        notes.append("PASS: B: the first reader consumes the deferred re-measure, marker cleared first")

    # ---------------------------------------------------------------- C: eager satisfies
    relearn_src = _class_src(wb_module, "_relearn_folded_m_correction_after_swap")
    if "_folded_m_relearn_pending = False" not in relearn_src:
        ok = False
        notes.append(
            "FAIL: C (bugs/0646): an eager re-measure leaves the pending marker set -- "
            "load then swap re-measures twice (6.5 s each)"
        )
    else:
        notes.append("PASS: C: an eager re-measure satisfies a pending deferral")

    # ---------------------------------------------------------------- D: deferred 2D trace
    rp_src = _class_src(plot_module, "refresh_plot")
    defer_branch = re.search(
        r"if defer_trace:\s*\n(?:\s*#.*\n)*\s*rays = None", rp_src
    )
    stays_dirty = re.search(
        r"if defer_trace:\s*\n\s*self\._last_preview_trace_signature = None\s*\n"
        r"\s*self\._preview_scene_trace_dirty = True",
        rp_src,
    )
    if defer_branch is None or stays_dirty is None:
        ok = False
        notes.append(
            "FAIL: D (bugs/0646): refresh_plot's defer branch is gone or marks the skipped "
            "trace CLEAN -- a stale no-ray preview would satisfy the next consumer"
        )
    else:
        notes.append("PASS: D: defer_trace skips the preview trace and leaves it dirty")

    # ---------------------------------------------------------------- E: functional stub
    calls = []

    class _Stub:
        _folded_m_relearn_pending = True
        _folded_m_correction_state = None
        _preview_trace_deferred_until_requested = True

        def _relearn_folded_m_correction_after_swap(self):
            calls.append(1)
            # the re-measure's own trace reads the correction (re-entrancy):
            qe_module.folded_m_correction(self)
            self._folded_m_correction_state = 0.9
            return " measured"

        def append_debug(self, _msg):
            pass

    stub = _Stub()
    held = qe_module.folded_m_correction(stub)  # FAST-LOAD state: raw, no consume
    held_ok = not calls and stub._folded_m_relearn_pending and abs(held - 1.0) < 1e-9
    stub._preview_trace_deferred_until_requested = False  # a real trace request happened
    value = qe_module.folded_m_correction(stub)
    if not held_ok or len(calls) != 1 or stub._folded_m_relearn_pending or abs(value - 0.9) > 1e-9:
        ok = False
        notes.append(
            f"FAIL: E (bugs/0646): held read gave {held} with {len(calls)} early call(s) "
            f"(want 1.0 and none); after clearing, consume ran {len(calls)}x (want exactly 1), "
            f"pending={stub._folded_m_relearn_pending}, value={value} (want 0.9)"
        )
    else:
        notes.append(
            "PASS: E: fast-load reads stay raw without consuming; the first post-clear read "
            "re-measures exactly once, no recursion"
        )

    # ---------------------------------------------------------------- G: fast-load state
    from KrakenOS.UI.services import trace_preview_sampling as tps_module
    from KrakenOS.UI.services import three_d_scene_tools as tds_module

    defer_src = _class_src(wb_module, "_defer_folded_m_relearn_on_load")
    diam_src = _class_src(tps_module, "_traced_image_diameter_value")
    bundle_src = _class_src(tds_module, "_build_preview_system_rays_bundle")
    g_problems = []
    if "_preview_trace_deferred_until_requested = True" not in defer_src:
        g_problems.append("the deferral helper does not set the fast-load state")
    if "_preview_trace_deferred_until_requested" not in diam_src:
        g_problems.append(
            "_traced_image_diameter_value ignores the fast-load state (a results label "
            "rebuilds the 25 s temporary trace mid-load)"
        )
    if not re.search(
        r"_preview_trace_deferred_until_requested = False\s*\n(?:.*\n)*?"
        r"\s*rays, straight_equivalent_fold_transform",
        _class_src(plot_module, "refresh_plot"),
    ):
        g_problems.append("refresh_plot's real trace does not clear the fast-load state first")
    if not re.search(
        r"if trace_rays:\s*\n(?:\s*#.*\n)*\s*self\._preview_trace_deferred_until_requested = False",
        bundle_src,
    ):
        g_problems.append("the 3D preview bundle does not clear the fast-load state before tracing")
    if "_preview_trace_deferred_until_requested = False" not in inspect.getsource(
        qe_module.QuickEstimationService.fov_solve
    ):
        g_problems.append(
            "fov_solve does not clear the fast-load state -- a solve straight after a "
            "fast load books the RAW first order (the 0602/0621 regression class)"
        )
    if g_problems:
        ok = False
        notes.append(f"FAIL: G (bugs/0646): {g_problems}")
    else:
        notes.append("PASS: G: fast-load state set by loaders, honored by labels, cleared by real traces")

    # ---------------------------------------------------------------- F: Trace Now
    trace_now = _class_src(shell_module, "_trace_now")
    mw_src = inspect.getsource(mw_module)
    if "refresh_plot" not in trace_now or '"Trace Now"' not in mw_src or "_trace_now" not in mw_src:
        ok = False
        notes.append(
            "FAIL: F (bugs/0646): the Trace Now affordance is missing -- a fast load has "
            "no explicit way to trace ('Let the user click Trace Now')"
        )
    else:
        notes.append("PASS: F: Trace Now button wired to the deferred trace")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Deferred-load-trace validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
