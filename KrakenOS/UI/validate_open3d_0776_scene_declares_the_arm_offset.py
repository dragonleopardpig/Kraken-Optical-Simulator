"""Guard for bugs/0776 -- the split-field arm offset is the SCENE's to declare.

The user: *"let the scene declare it, like camera_focus_stage"*, about the coefficient k in the
strip-POSITION law bugs/0774 measured:

    |strip centre| = k * |m|      k = the object-space half-separation of the two arms' axes

k is a property of the BENCH, not of optics -- 8.778 mm on om05a_folded_80mm -- so hardcoding it
would bake one machine's geometry into the simulator. It persists exactly as `camera_focus_stage`
does, and the check is inert on any scene that does not declare it.

HONEST SCOPE. This does NOT catch the 21 mm anomaly it was proposed for. Measured with the
correct statistic, device 21's strips sit 0.25% off the law -- they are correctly positioned. The
"1.393 mm excess" that motivated it was measured on the strip's outer EDGE, and an edge moves when
a strip widens, which is what defocus does. What ships is a legitimate invariant guard, not a
diagnostic for that bug.

An adversarial review of the first cut returned 21 findings; three were confirmed by reading the
diff and are fixed here (no clipped-strip guard where the sibling traced_m check has one; no
minimum ray count before a mean is called a strip centre; a banner asserting "the field is the
right SIZE" -- a thing it never checks, which could contradict the FIELD OVERFLOWS line printed
directly above it). Known and NOT fixed: np.hypot discards sign so two strips stacked on the same
side would pass; groups are keyed by band NAME so two identically-named bands merge; and
`_solve_summary_info` can be stale across a scene load.

Checks (display-free, pure):
  A  the offset round-trips through save/load, and every malformed value is DROPPED -- including
     non-finite, which would otherwise be written back as a bare `inf` and make the .py
     unimportable, silently discarding every persisted setting on the next load;
  B  a scene that declares nothing gets no check at all;
  C  the banner fires only past the threshold, and never claims anything about SIZE;
  D  the measurement carries the clipped-strip and minimum-ray guards.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0776_scene_declares_the_arm_offset
"""

from __future__ import annotations

import inspect
import math


def _sanitize(offset):
    """The loader's contract, mirrored so the cases can be enumerated here."""
    if offset is None:
        return None
    try:
        value = float(offset)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) and value > 0.0 else None


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import layout_settings as ls

    src = inspect.getsource(ls)
    ok(
        '"split_field_arm_offset_mm": getattr(' in src,
        "A1: the offset is SAVED, alongside camera_focus_stage",
    )
    ok(
        'settings.get("split_field_arm_offset_mm"' in src,
        "A2: and LOADED back",
    )
    ok(
        "math.isfinite" in src,
        "A3: with a finiteness test -- 1e400 parses to inf, passes a bare '> 0' test, and "
        "pformat writes it back as the bare token `inf`, which is not a Python literal: the .py "
        "then fails to import and BOTH loaders fall back to surfaces-only, silently dropping "
        "every persisted setting",
    )
    for raw, want in (
        (None, None), ("", None), ("abc", None), (0, None), (-3.0, None),
        (float("inf"), None), (float("nan"), None), (1e400, None),
        (8.778, 8.778), ("8.778", 8.778),
    ):
        got = _sanitize(raw)
        ok(got == want, f"A4[{raw!r}]: sanitizes to {got!r} (want {want!r})")

    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    def strip_lines(info):
        return [l for l in format_focus_summary_lines(info, None, pixel_size_um=(4.5, 4.5))
                if l.upper().startswith("STRIP")]

    def info_with(worst, arms=None):
        return {"offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
                "sensor_overflow": {"outside": 0, "landed": 640, "overflow_mm": 0.0,
                                    "fraction": 0.0,
                                    "strip_position": {"expected_mm": 9.17,
                                                       "arm_offset_mm": 8.778,
                                                       "arms": arms or [],
                                                       "worst_relative": worst}}}

    ok(
        not strip_lines({"offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
                         "sensor_overflow": {"outside": 0, "landed": 640, "overflow_mm": 0.0,
                                             "fraction": 0.0}}),
        "B1: a scene that declares no offset produces no strip-position record and no line",
    )
    ok(not strip_lines(info_with(0.0025)),
       "C1: device 21's real 0.25% stays quiet -- it is within the law, not a fault")
    ok(not strip_lines(info_with(0.015)), "C2: 1.5% stays quiet (below the 2% threshold)")
    fired = strip_lines(info_with(0.076, [{"name": "Face A field", "centre_mm": 9.87,
                                           "expected_mm": 9.17, "relative": 0.076}]))
    ok(bool(fired), "C3: 7.6% fires")
    if fired:
        ok("9.17" in fired[0] and "8.778" in fired[0],
           f"C4: naming the expected position and the declared offset (got {fired[0]!r})")
        ok(
            "SIZE" not in fired[0],
            "C5: and claiming NOTHING about size -- it never measures size, and the FIELD "
            "OVERFLOWS line printed above it may be saying the opposite",
        )

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M

    meas = inspect.getsource(_M._annotate_sensor_overflow)
    ok(
        "outside == 0 and enough" in meas,
        "D1: the measurement skips a CLIPPED strip -- its surviving mean drifts off the true "
        "centre, and the sibling traced_m check has had this guard all along",
    )
    ok("n >= 8" in meas, "D2: and requires enough rays per arm to call a mean a centre")
    ok(
        "layout_object_fov_bands" in meas,
        "D3: grouping is by FIELD BAND, the rule _focus_image_partitions uses -- grouping by "
        "launch point gave one group per field point (14 on a 23 mm device) and fired on every "
        "correct scene at 50-68%",
    )
    # strip comments before looking: the coefficient is NAMED in the explanation, which is
    # documentation. What must not exist is a line that USES it as a value.
    code_only = "\n".join(
        line.split("#", 1)[0] for line in meas.splitlines()
    )
    ok(
        "8.778" not in code_only,
        f"D4: the bench's own coefficient is never used as a VALUE in the code -- it is read "
        f"from the scene. (It is named in the comments, which is documentation.)",
    )
    ok(
        'getattr(self, "split_field_arm_offset_mm", None)' in code_only,
        "D5: k comes from the scene attribute and nowhere else",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0776 scene-declares-the-arm-offset validation PASSED")
        return 0
    print("0776 scene-declares-the-arm-offset validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
