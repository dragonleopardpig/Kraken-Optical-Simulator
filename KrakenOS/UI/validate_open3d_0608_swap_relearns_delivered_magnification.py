"""Guard for bugs/0608 — a swap must RE-MEASURE the delivered magnification, not just clear it.

flag_20260811_133818 ("swapped a lens, please verify rays"): after swapping PYRITE 4.5/85
into the folded Apo75 scene the rays were sound (205 arrivals, all inside the 23x23 active
rect, 9 clean field spots) but the readout promised |m| 1.506 while the real rays delivered
1.160 -- the "FOV 15.3 x 15.3" label implied a full sensor while the traced field covered
~82% of its width.

bugs/0591 clears `_folded_m_correction_state` on a swap (correct: the old glass's factor is
meaningless on new glass) but nothing re-measured it, so every readout between the swap and
the user's next solve ran on the RAW folded first order.

Checks (display-free):
  A  CONTRACT — QuickEstimationService.relearn_folded_m_correction exists, measures with the
     real-ray probe, and divides out any standing factor (absolute, never compounded).
  B  WIRING — both swap paths (lens + camera) call the workbench helper, and the helper
     reports through the swap message.
  C  BEHAVIOUR (stubbed) — with a promised-vs-delivered mismatch the factor is recorded as
     measured/promised; a scene the probe cannot measure keeps correction 1.0 and returns None.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0608_swap_relearns_delivered_magnification
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import quick_estimation as qe_module
    from KrakenOS.UI.services import layout_table_workbench as workbench_module

    Service = qe_module.QuickEstimationService
    relearn = getattr(Service, "relearn_folded_m_correction", None)

    # ---------------------------------------------------------------- A: contract
    if not callable(relearn):
        ok = False
        notes.append(
            "FAIL: A (bugs/0608): relearn_folded_m_correction is gone -- a swap leaves the "
            "readout on the raw folded first order until the user's next solve"
        )
        return ok, notes
    src = inspect.getsource(relearn)
    if "_measured_delivered_image_semi" not in src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0608): the re-learn no longer measures with real rays -- it cannot "
            "know what the new glass delivers"
        )
    elif "_folded_m_correction()" not in src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0608): the re-learn no longer divides out the standing factor -- "
            "repeated swaps compound the correction"
        )
    else:
        notes.append("PASS: A: the re-learn measures with real rays against the RAW first order")

    # ---------------------------------------------------------------- B: wiring
    helper = getattr(workbench_module.LayoutTableWorkbenchMixin, "_relearn_folded_m_correction_after_swap", None)
    if not callable(helper):
        ok = False
        notes.append("FAIL: B (bugs/0608): the workbench swap helper is gone")
    else:
        notes.append("PASS: B1: the workbench exposes the after-swap re-learn helper")
    lens_src = inspect.getsource(workbench_module.LayoutTableWorkbenchMixin.swap_imaging_lens_from_folder)
    module_src = inspect.getsource(workbench_module)
    if "_relearn_folded_m_correction_after_swap" not in lens_src:
        ok = False
        notes.append(
            "FAIL: B2 (bugs/0608): the LENS swap no longer re-measures -- the flagged 23% "
            "readout overstatement returns"
        )
    else:
        notes.append("PASS: B2: the lens swap re-measures the delivered magnification")
    if module_src.count("_relearn_folded_m_correction_after_swap(") < 3:
        ok = False
        notes.append(
            "FAIL: B3 (bugs/0608): the CAMERA swap path lost the re-measure (a new sensor is a "
            "new conjugate target, bugs/0591)"
        )
    else:
        notes.append("PASS: B3: the camera swap re-measures too")
    if "_swap_correction_note" not in module_src:
        ok = False
        notes.append("FAIL: B4 (bugs/0608): the re-measure is never reported to the user")
    else:
        notes.append("PASS: B4: the swap message reports the re-measured factor")

    # ---------------------------------------------------------------- C: behaviour
    class _Stub(Service):
        def __init__(self, promised, measured_semi, object_semi):
            self.editor = type("E", (), {"_folded_m_correction_state": None})()
            self._promised = promised
            self._measured_semi = measured_semi
            self._object_semi = object_semi

        def current_state(self):
            return {"magnification": self._promised, "fov_semi": self._object_semi}

        def _measured_delivered_image_semi(self, object_semi):
            return self._measured_semi

    # promised 1.506 with 7.65 object semi; rays deliver 8.87 => |m| 1.160 => factor 0.770
    stub = _Stub(1.5062, 8.872, 7.648)
    factor = stub.relearn_folded_m_correction()
    expected = (8.872 / 7.648) / 1.5062
    if factor is None or abs(factor - expected) > 1e-6:
        ok = False
        notes.append(f"FAIL: C1 (bugs/0608): factor {factor} != measured/promised {expected:.6f}")
    elif abs(float(stub.editor._folded_m_correction_state) - expected) > 1e-6:
        ok = False
        notes.append("FAIL: C1 (bugs/0608): the factor was computed but never recorded")
    else:
        notes.append(f"PASS: C1: the flagged case records {factor:.4f} (readout would follow the rays)")

    unmeasurable = _Stub(1.5062, None, 7.648)
    if unmeasurable.relearn_folded_m_correction() is not None:
        ok = False
        notes.append("FAIL: C2 (bugs/0608): an unmeasurable scene invented a factor")
    elif unmeasurable.editor._folded_m_correction_state is not None:
        ok = False
        notes.append("FAIL: C2 (bugs/0608): an unmeasurable scene still wrote a correction")
    else:
        notes.append("PASS: C2: an unmeasurable scene keeps correction 1.0")

    absurd = _Stub(1.5062, 8.872 * 50.0, 7.648)  # a wild probe must not be trusted
    if absurd.relearn_folded_m_correction() is not None:
        ok = False
        notes.append("FAIL: C3 (bugs/0608): an out-of-range factor was accepted (guard band 0.1-10)")
    else:
        notes.append("PASS: C3: an out-of-range measurement is rejected")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Swap-relearns-delivered-magnification validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
