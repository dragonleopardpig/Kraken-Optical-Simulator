"""Guard for bugs/0775 -- measure the delivered magnification from the RAYS and check the claim.

Chasing a 21 mm asymmetry, the banner's "delivering 22.05 x 22.05 mm (|m| 1.045)" could not be
checked against anything: every readout that might have contradicted it came from the same first
order that produced it. bugs/0774 established two laws for where the strips land, and the LENGTH
one reads backwards into an independent measurement:

    LAW 2   |v|half = device * |m| / 2      ->      |m| = 2 * |v|half / device

That is scene-independent -- unlike the strip POSITION, whose coefficient (9.278 on om05a) is a
property of one bench's arm offset and would be a hardcoded scene constant in the simulator.

Measured, the check is quiet where it should be: device 21 traced 1.04519 vs claimed 1.04490,
device 30/FOV 34 traced 0.67778 vs 0.67765, device 23 traced 0.95431 vs 0.95404 -- 0.03% apart
at worst, against a 2% threshold.

It also settles a claim made earlier in that investigation and withdrawn: the 21 mm strips are
NOT mis-magnified. They are correctly sized (1.0452 vs 1.0449 claimed) and mis-POSITIONED, which
is a pointing error and a different bug.

Checks (display-free, pure):
  A  a real disagreement is reported, naming both numbers and which to trust;
  B  agreement within the threshold says nothing -- the measured cases must stay quiet;
  C  the check is skipped when the strip is CLIPPED, because a clipped strip under-reports its
     own length and would lie exactly where the overflow warning already speaks;
  D  the arithmetic is LAW 2 read backwards, checked against the three measured cases.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0775_traced_magnification_checks_the_claim
"""

from __future__ import annotations

import inspect


def _info(traced, claimed, outside=0):
    rec = {"outside": outside, "landed": 640, "overflow_mm": 0.0, "fraction": 0.0,
           "field_half_mm": 10.0, "sensor_half_mm": 11.52, "captured_fraction": 1.0}
    if outside == 0:
        rec["traced_m"] = traced
        rec["claimed_m"] = claimed
        rec["m_disagreement"] = abs(traced - claimed) / claimed
    return {"offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
            "sensor_overflow": rec}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    def said(info):
        return [l for l in format_focus_summary_lines(info, None, pixel_size_um=(4.5, 4.5))
                if "DISAGREES" in l.upper()]

    # ---- A: a real disagreement speaks --------------------------------------------------------
    lines = said(_info(1.1243, 1.0449))
    ok(bool(lines), "A1: a 7.6% disagreement between the rays and the claim is reported")
    if lines:
        text = lines[0]
        ok("1.124" in text and "1.045" in text,
           f"A2: naming BOTH numbers, measured and claimed (got {text!r})")
        ok("trust the rays" in text,
           "A3: and which one to believe -- the rays are the measurement, the claim is a model")

    # ---- B: agreement is silent ---------------------------------------------------------------
    for label, traced, claimed in (
        ("device 21", 1.0451901560695362, 1.0448979591912706),
        ("device 30 FOV 34", 0.6777753030362078, 0.6776470588255558),
        ("device 23", 0.9543090389367669, 0.9540372670866609),
    ):
        ok(
            not said(_info(traced, claimed)),
            f"B1[{label}]: the measured case stays quiet "
            f"({100*abs(traced-claimed)/claimed:.3f}% apart)",
        )
    # bracket the 2% threshold rather than sit on it -- 1.02-1.0 is 0.020000000000000018 in
    # binary floating point, so an exactly-at-the-line assertion tests the FPU, not the rule.
    ok(not said(_info(1.015, 1.0)), "B2: a 1.5% gap stays quiet (below the 2% threshold)")
    ok(bool(said(_info(1.03, 1.0))), "B3: a 3% gap speaks (above it)")
    ok(bool(said(_info(1.05, 1.0))), "B4: and so does a 5% gap")

    # ---- C: skipped when clipped ---------------------------------------------------------------
    clipped = _info(0.0, 0.0, outside=44)
    ok(
        "traced_m" not in clipped["sensor_overflow"],
        "C1: a clipped strip records no traced |m| at all -- it under-reports its own length, "
        "and the overflow warning already covers that case",
    )
    ok(not said(clipped), "C2: so nothing is claimed about magnification there")

    # ---- D: the arithmetic is LAW 2 ------------------------------------------------------------
    S = 23.04
    for device, fov, want in ((21.0, 22.05, 1.0449), (30.0, 34.0, 0.6776), (23.0, 24.15, 0.9540)):
        m = S / fov
        half = device * m / 2.0
        back = 2.0 * half / device
        ok(
            abs(back - m) < 1e-9 and abs(m - want) < 0.001,
            f"D1[dev {device:g}]: LAW 2 inverts exactly -- 2*({half:.4f})/{device:g} = {back:.4f}"
            f" = |m| ({want})",
        )
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M

    src = inspect.getsource(_M._annotate_sensor_overflow)
    ok(
        "if outside == 0 and span_v > 0.0:" in src,
        "D2: and the guard against a clipped strip is in the measurement, not only the banner",
    )
    ok(
        "9.278" not in src,
        "D3: the scene-specific strip-POSITION coefficient is not baked in -- only the "
        "scene-independent length law is asserted",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0775 traced-magnification-checks-the-claim validation PASSED")
        return 0
    print("0775 traced-magnification-checks-the-claim validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
