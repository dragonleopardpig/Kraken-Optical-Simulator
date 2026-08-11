"""Guard for bugs/0609 — an interactive swap asks for the FOV the user wants.

A swapped lens does not reproduce the old operating point, so keeping the old FOV NUMBER
leaves the scene in a state the user never chose (measured: the preserved 15.30 field
filled 82% x 77% of the sensor; 19.79 was needed). The swap now opens the object-plane
FOV popup, prefilled with the field that fills the sensor at the MEASURED magnification.

Checks (display-free):
  A  PREFILL — object_fov_dimensions() applies the measured correction (bugs/0602's rule
     for display readers); with a synthetic correction it offers the sensor-filling field,
     not the raw-first-order one.
  B  GATING — the prompt fires only for interactive swaps, no-ops without a live
     inspector, and is SCHEDULED (the popup is modal: inline would block a headless swap).
  C  WIRING — the lens swap calls it with the bugs/0586 `interactive` flag and reports it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0609_swap_prompts_for_fov
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import layout_table_workbench as workbench_module
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    W = workbench_module.LayoutTableWorkbenchMixin

    # ---------------------------------------------------------------- A: prefill
    class _Stub(QuickEstimationService):
        def __init__(self, correction):
            self.editor = type("E", (), {"_folded_m_correction_state": correction})()

        def _finite_mag(self):
            return 1.5062  # the RAW folded first order after the flagged swap

        def sensor_active_dimensions(self):
            return (23.0, 23.0)

    raw = _Stub(None).object_fov_dimensions()
    corrected = _Stub(0.7714).object_fov_dimensions()
    if raw is None or corrected is None:
        ok = False
        notes.append("FAIL: A (bugs/0609): object_fov_dimensions returned None on the fixture")
    elif abs(raw[0] - 23.0 / 1.5062) > 1e-6:
        ok = False
        notes.append(f"FAIL: A (bugs/0609): uncorrected prefill {raw[0]} != sensor/raw")
    elif abs(corrected[0] - 23.0 / (1.5062 * 0.7714)) > 1e-6:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0609): the popup prefill {corrected[0]:.3f} ignores the measured "
            "correction -- it offers a field that does NOT fill the sensor"
        )
    else:
        notes.append(
            f"PASS: A: the prefill follows the delivered magnification "
            f"({raw[0]:.2f} raw -> {corrected[0]:.2f} measured)"
        )

    # ---------------------------------------------------------------- B: gating
    prompt = getattr(W, "_prompt_fov_solve_after_swap", None)
    if not callable(prompt):
        ok = False
        notes.append("FAIL: B (bugs/0609): _prompt_fov_solve_after_swap is gone")
        return ok, notes
    src = inspect.getsource(prompt)
    if "if not interactive" not in src:
        ok = False
        notes.append(
            "FAIL: B (bugs/0609): the prompt no longer gates on the bugs/0586 interactive "
            "flag -- a programmatic/headless swap would open a modal dialog and hang"
        )
    else:
        notes.append("PASS: B1: the prompt is interactive-only")
    if ".after(" not in src:
        ok = False
        notes.append(
            "FAIL: B2 (bugs/0609): the modal popup is opened inline instead of scheduled -- "
            "the swap would block inside its own call"
        )
    else:
        notes.append("PASS: B2: the modal popup is scheduled, never inline")
    if "_open_quick_estimation_fov_popup" not in src:
        ok = False
        notes.append("FAIL: B3 (bugs/0609): the prompt no longer opens the FOV popup")
    else:
        notes.append("PASS: B3: it opens the object-plane FOV popup")

    class _NoInspector:
        _three_d_inspector = None

        def append_debug(self, *_a, **_k):
            pass

    if prompt(_NoInspector(), True) != "":
        ok = False
        notes.append("FAIL: B4 (bugs/0609): the prompt does not no-op without a live inspector")
    elif prompt(_NoInspector(), False) != "":
        ok = False
        notes.append("FAIL: B4 (bugs/0609): a programmatic swap still prompted")
    else:
        notes.append("PASS: B4: no inspector / programmatic swap -> silent no-op")

    scheduled: list[int] = []

    class _Inspector:
        def winfo_exists(self):
            return True

        def after(self, delay, _cb):
            scheduled.append(int(delay))

    class _Editor:
        def __init__(self):
            self._three_d_inspector = _Inspector()

        def append_debug(self, *_a, **_k):
            pass

    note = prompt(_Editor(), True)
    if not scheduled:
        ok = False
        notes.append("FAIL: B5 (bugs/0609): an interactive swap did not schedule the popup")
    elif not note.strip():
        ok = False
        notes.append("FAIL: B5 (bugs/0609): the prompt is silent -- the user is not told to answer it")
    else:
        notes.append(f"PASS: B5: an interactive swap schedules the popup (+{scheduled[0]} ms) and says so")

    # ---------------------------------------------------------------- C: wiring
    swap_src = inspect.getsource(W.swap_imaging_lens_from_folder)
    if "_prompt_fov_solve_after_swap(interactive)" not in swap_src:
        ok = False
        notes.append(
            "FAIL: C (bugs/0609): the lens swap no longer prompts for the FOV -- it silently "
            "keeps a field that may not fill the sensor"
        )
    else:
        notes.append("PASS: C: the lens swap prompts with the bugs/0586 interactive flag")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Swap-prompts-for-FOV validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
