"""Guard for bugs/0610 — the shared field converter must use the DELIVERED magnification.

An image-height field (the camera coupling stores "Real Image Height" = the sensor
half-diagonal) becomes an OBJECT height by dividing by the magnification. Dividing by the
folded first order's PROMISE instead of what the machine DELIVERS launched the wrong field:
measured after a PYRITE swap, raw |m| 1.506 put the launched field at 15.30 mm while the
sensor needed 19.79, so the trace under-filled the glass by ~18% -- and no FOV solve could
re-frame it, because the launcher never saw the corrected number (bugs/0609).

`_field_metrics_for_value` is the SHARED converter: the ray launcher, the field samplers,
the auto image diameter and the panel readout all flow through it, so the fix is general
rather than per-scene. On a sequential scene the correction is 1.0 and nothing moves.

Checks (display-free):
  A  CONTRACT — the converter applies folded_m_correction.
  B  BEHAVIOUR — with a synthetic correction, an image-height field converts by the
     DELIVERED magnification (object height = height / (raw * correction)), and the
     reported paraxial image height follows the same conjugate.
  C  NEUTRALITY — correction 1.0 (sequential/unmeasured) reproduces the old numbers
     exactly, and an Object Height / Angle field is never scaled by it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0610_field_converter_uses_delivered_magnification
"""

from __future__ import annotations

import inspect


def _stub(correction, mag=1.5062, object_distance=118.97, effl=85.13):
    from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin

    class _Editor(LayoutSceneBundleDisplayMixin):
        _folded_m_correction_state = correction

        def _current_object_distance(self):
            return object_distance

        def _current_effl_estimate(self):
            return effl

        def _current_image_distance(self):
            return 190.0

        def _current_finite_paraxial_magnification(self):
            return mag

    return _Editor()


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.layout_scene_bundle_display import LayoutSceneBundleDisplayMixin

    src = inspect.getsource(LayoutSceneBundleDisplayMixin._field_metrics_for_value)
    if "folded_m_correction" not in src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0610): the shared field converter no longer applies the measured "
            "correction -- an image-height field launches the first order's promised field, "
            "so the trace under-fills the sensor and no FOV solve can re-frame it"
        )
    else:
        notes.append("PASS: A: the shared field converter applies the delivered correction")

    sensor_semi_diagonal = 16.263  # the flagged 23 x 23 sensor
    raw = 1.5062
    corrected_factor = 0.7714

    plain = _stub(None)._field_metrics_for_value("Real Image Height", sensor_semi_diagonal)
    fixed = _stub(corrected_factor)._field_metrics_for_value("Real Image Height", sensor_semi_diagonal)

    want_plain = sensor_semi_diagonal / raw
    want_fixed = sensor_semi_diagonal / (raw * corrected_factor)
    if abs(plain["object_height"] - want_plain) > 1e-6:
        ok = False
        notes.append(f"FAIL: C1 (bugs/0610): unmeasured scene changed ({plain['object_height']} != {want_plain})")
    else:
        notes.append(f"PASS: C1: correction 1.0 reproduces the old conversion ({plain['object_height']:.3f} mm)")
    if abs(fixed["object_height"] - want_fixed) > 1e-6:
        ok = False
        notes.append(
            f"FAIL: B1 (bugs/0610): image-height field converts by the RAW magnification "
            f"({fixed['object_height']:.3f} != {want_fixed:.3f}) -- the launcher under-fills"
        )
    else:
        notes.append(
            f"PASS: B1: an image-height field launches the DELIVERED field "
            f"({plain['object_height']:.2f} -> {fixed['object_height']:.2f} mm semi)"
        )
    # the reported image height must follow the same conjugate (no half-corrected state)
    if abs(fixed["paraxial_image_height"] - sensor_semi_diagonal) > 1e-6:
        ok = False
        notes.append(
            "FAIL: B2 (bugs/0610): the reported image height no longer round-trips the "
            f"field ({fixed['paraxial_image_height']} != {sensor_semi_diagonal})"
        )
    else:
        notes.append("PASS: B2: the reported image height round-trips the requested field")

    # C2: an OBJECT-space field is never scaled by the correction.
    obj_plain = _stub(None)._field_metrics_for_value("Object Height", 7.648)
    obj_fixed = _stub(corrected_factor)._field_metrics_for_value("Object Height", 7.648)
    if abs(obj_plain["object_height"] - 7.648) > 1e-9 or abs(obj_fixed["object_height"] - 7.648) > 1e-9:
        ok = False
        notes.append("FAIL: C2 (bugs/0610): an Object Height field was scaled by the correction")
    else:
        notes.append("PASS: C2: an Object Height field is taken as given, corrected or not")
    ang_plain = _stub(None)._field_metrics_for_value("Angle", 5.0)
    ang_fixed = _stub(corrected_factor)._field_metrics_for_value("Angle", 5.0)
    if abs(ang_plain["object_height"] - ang_fixed["object_height"]) > 1e-9:
        ok = False
        notes.append("FAIL: C3 (bugs/0610): an Angle field's object height moved with the correction")
    else:
        notes.append("PASS: C3: an Angle field is unaffected by the correction")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Field-converter-uses-delivered-magnification validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
