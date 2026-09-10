"""Guard for bugs/0774 -- a field that overflows the sensor must be SAID, not silently clipped.

The user, from a screenshot: *"I noticed the two image strips going outward from the center of
the sensor, reaching the boundary at 21mm device size. Do you take this into account?"* It was not
taken into account. A ray reaching the detector PLANE but landing beyond its active area counted
as landing, and the banner reported focus and spot size as usual.

Two laws govern where the strips sit on this bench, verified to +-0.005 mm across two device
sizes and five magnifications:

    LAW 1  strip POSITION  |u|outer = 9.278 * |m|        (the fixed arm offset, magnified)
    LAW 2  strip LENGTH    |v|half  = device * |m| / 2

Measured consequences: with the default +5% field the strips ALWAYS sit at 95.2% of the sensor
half, whatever the device size; and the field overflows the ends whenever the requested FOV is
smaller than the device -- a 30 mm device at FOV 24 images only 80% of the part.

Counting landings is not enough on its own: a ray heading well past the sensor never reaches it,
so the count sees only the sliver AT the boundary. That case registers 44 rays 0.005 mm out while
LAW 2 says 2.88 mm per side is lost. The check therefore predicts the extent too.

Checks (display-free, pure):
  A  a field wider than the sensor is reported, with the overflow, the two sizes and the
     captured fraction;
  B  a field inside the sensor says nothing (no false alarm on every ordinary scene);
  C  the captured fraction is LAW 2 -- verified against the three measured cases;
  D  the banner prefers the predicted overflow over the ray count, because the count
     under-reports; and the annotation never raises into the measurement.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0774_field_overflowing_the_sensor_is_said
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    #: the three measured cases, verbatim
    OVERFLOW = {
        "offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
        "sensor_overflow": {
            "outside": 44, "landed": 600, "overflow_mm": 0.004825, "fraction": 0.0683,
            "field_half_mm": 14.4, "sensor_half_mm": 11.52,
            "captured_fraction": 0.8, "predicted_overflow_mm": 2.88,
        },
    }
    CLEAN = {
        "offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
        "sensor_overflow": {
            "outside": 0, "landed": 640, "overflow_mm": 0.0, "fraction": 0.0,
            "field_half_mm": 10.1647, "sensor_half_mm": 11.52, "captured_fraction": 1.0,
        },
    }

    over_lines = format_focus_summary_lines(OVERFLOW, None, pixel_size_um=(4.5, 4.5))
    said = [l for l in over_lines if "OVERFLOW" in l.upper()]
    ok(bool(said), "A1: a field wider than the sensor is reported at all")
    if said:
        text = said[0]
        ok("2.88" in text, f"A2: with the per-side overflow (got {text!r})")
        ok("28.8" in text and "23.04" in text, "A3: and both sizes, field and sensor")
        ok("80.0%" in text, "A4: and the fraction of the device actually imaged")
        ok(
            "FOV at least as large as the device" in text,
            "A5: and what to do about it -- the length limit is FOV >= device (LAW 2)",
        )

    clean_lines = format_focus_summary_lines(CLEAN, None, pixel_size_um=(4.5, 4.5))
    ok(
        not [l for l in clean_lines if "OVERFLOW" in l.upper()],
        "B1: a field inside the sensor says nothing -- no alarm on every ordinary scene",
    )

    # ---- C: the captured fraction IS law 2, against the measured cases -----------------------
    S = 23.04
    for device, fov, want_half, want_frac in (
        (30.0, 24.0, 14.400, 0.800),
        (30.0, 34.0, 10.165, 1.000),
        (21.0, 22.05, 10.971, 1.000),
    ):
        m = S / fov
        half = 0.5 * device * m
        frac = min(1.0, (S / 2.0) / half)
        ok(
            abs(half - want_half) < 0.005 and abs(frac - want_frac) < 0.005,
            f"C1[dev {device:g} FOV {fov:g}]: LAW 2 gives field half {half:.3f} mm "
            f"(measured {want_half}) and captured {100*frac:.1f}% (measured {100*want_frac:.0f}%)",
        )

    # ---- D: prefer the prediction; never raise ------------------------------------------------
    # bugs/0775 review: assert the BEHAVIOUR, not the source text. The first cut matched
    # "elif outside > 0", which a later edit renamed to "if predicted is None and outside > 0" --
    # same behaviour, broken guard. A guard that breaks on a rename was testing the wrong thing.
    both = {
        "offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
        "sensor_overflow": {
            "outside": 44, "landed": 600, "overflow_mm": 0.004825, "fraction": 0.0683,
            "field_half_mm": 14.4, "sensor_half_mm": 11.52,
            "captured_fraction": 0.8, "predicted_overflow_mm": 2.88,
        },
    }
    def _field_lines(info):
        # only the FIELD lines -- "FOCUS:" and "Landed:" both contain the word "sensor"
        return [l for l in format_focus_summary_lines(info, None, pixel_size_um=(4.5, 4.5))
                if l.upper().startswith("FIELD ")]

    both_lines = _field_lines(both)
    ok(
        len(both_lines) == 1 and "2.88" in both_lines[0],
        f"D1: when BOTH a prediction and a ray count exist, the banner reports the PREDICTION "
        f"only -- counting landings sees just the sliver at the boundary (44 rays at 0.005 mm "
        f"for a 2.88 mm/side loss). Got {both_lines!r}",
    )
    only_count = {
        "offset_mm": -0.05, "rms_waist_mm": 0.0002, "rms_plane_mm": 0.0015,
        "sensor_overflow": {"outside": 7, "landed": 600, "overflow_mm": 0.02,
                            "fraction": 0.0115},
    }
    count_lines = _field_lines(only_count)
    ok(
        len(count_lines) == 1 and "7 ray" in count_lines[0],
        f"D1b: and with no prediction available the ray count still speaks, rather than the "
        f"scene going silent about light it is losing. Got {count_lines!r}",
    )
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M

    caller = inspect.getsource(_M._measure_focused_image_plane)
    ok(
        "_annotate_sensor_overflow" in caller and "except Exception" in caller,
        "D2: and the annotation is guarded -- a readout must never break the measurement "
        "it describes (bugs/0758)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0774 field-overflowing-the-sensor-is-said validation PASSED")
        return 0
    print("0774 field-overflowing-the-sensor-is-said validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
