"""Display-free guard for bugs/0195: Quick Estimation must work on the folded AZ85
RA-mirror scene -- the object/image conjugate solve and the in-focus indicator, not just
the (already-correct) magnification readout.

The user re-flagged the folded AZ85 after bugs/0192 fixed the reflection, listing "wrong
magnification" and asking that Quick Estimation (right-click image plane / detector) also
work on the fold. Measured headlessly, the paraxial MAGNIFICATION was already correct
(|m|=1.1418, because `_current_finite_paraxial_magnification` substitutes the transmissive
reference rows) -- but the QE conjugate SOLVE threw:

    _compute_paraxial_solve_result("image") -> RuntimeError:
        "Paraxial solve supports centered refractive systems only"

because it calls `_exact_paraxial_solution_for_rows(self.rows)` on the RAW rows, whose row-1
promoted mesh mirror carries a placement decenter (desp_z=12.5) that trips the
centered-refractive guard. That throw also left QE's in-focus indicator unknown
(`current_state()["in_focus"]` swallows the exception -> None), so the detector's defocus
never surfaced.

Fix (shared with bugs/0194): folding is a rigid transform, so
`_compute_paraxial_solve_result` short-circuits through the unfolded straight flat-plate
equivalent (`_folded_optical_solid_straight_equivalent_rows`) when the layout has a
rotating mesh fold. The conjugate distances stay in the detector's cumulative-z frame.

This guard asserts, on the live AZ85 editor:
  1. BEFORE (the equivalent-rows helper shadowed to None): both solves raise and the
     inline in-focus check is unavailable -- the precondition, so the guard is not vacuous;
  2. AFTER (the real helper): solve("image") -> ~158.12 mm (= the current 150.368 mm gap +
     the 7.76 mm defocus, i.e. best focus), solve("object") -> ~65.31 mm, the magnification
     stays 1.1418, and the in-focus check reads False (correctly flagging the 7.76 mm
     defocus at the detector);
  3. scope: the sequential flat_mirror scene and a straight-through beam-splitter cube build
     NO flat equivalent -- the fix is inert off the folding-mesh-mirror path.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_quick_estimation

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _build_editor, _AZ85, _PLAIN

_BS_CUBE = "machine_vision_150mm_coaxial_led.py"
_EXPECTED_IMAGE = 158.1236   # = 150.3679 (current gap) + 7.7557 (defocus) -> best focus
_EXPECTED_OBJECT = 65.3137
_EXPECTED_MAG = 1.1418


def _solved(editor, target):
    try:
        return float(editor._compute_paraxial_solve_result(target).get("solved_distance"))
    except Exception as exc:  # noqa: BLE001
        return f"EXC {type(exc).__name__}"


def _in_focus(editor):
    try:
        solved = float(editor._compute_paraxial_solve_result("image").get("solved_distance"))
        img = float(editor._current_image_distance())
        return bool(abs(solved - img) <= max(0.05, 1e-3 * abs(img)))
    except Exception as exc:  # noqa: BLE001
        return None


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            editor = _build_editor(_AZ85)
            editor._build_preview_system_rays_bundle(update_state=True)

            # (1) BEFORE: shadow the equivalent-rows helper -> the folded solve has no surrogate.
            editor._folded_optical_solid_straight_equivalent_rows = lambda: None
            before_img = _solved(editor, "image")
            before_obj = _solved(editor, "object")
            before_focus = _in_focus(editor)

            # (2) AFTER: the real helper.
            del editor._folded_optical_solid_straight_equivalent_rows
            after_mag = editor._current_finite_paraxial_magnification()
            after_img = _solved(editor, "image")
            after_obj = _solved(editor, "object")
            after_focus = _in_focus(editor)

        # (1) precondition: BEFORE both solves raise (in-focus unavailable).
        if not (isinstance(before_img, str) and isinstance(before_obj, str)):
            failures.append(
                f"AZ85 precondition: BEFORE the folded QE solve did not throw "
                f"(image={before_img}, object={before_obj}) -- guard vacuous"
            )
        if before_focus is not None:
            failures.append(f"AZ85 precondition: BEFORE the in-focus check was computable ({before_focus}) -- guard vacuous")
        notes.append(f"BEFORE: solve(image)={before_img} solve(object)={before_obj} in_focus={before_focus}")

        # (2) AFTER: solves land, magnification holds, defocus is flagged.
        if not isinstance(after_img, float) or abs(after_img - _EXPECTED_IMAGE) > 0.5:
            failures.append(f"AZ85: AFTER solve('image')={after_img}, expected ~{_EXPECTED_IMAGE} mm (best focus)")
        if not isinstance(after_obj, float) or abs(after_obj - _EXPECTED_OBJECT) > 0.5:
            failures.append(f"AZ85: AFTER solve('object')={after_obj}, expected ~{_EXPECTED_OBJECT} mm")
        if after_mag is None or abs(float(after_mag) - _EXPECTED_MAG) > 1e-2:
            failures.append(f"AZ85: AFTER magnification={after_mag}, expected ~{_EXPECTED_MAG}")
        if after_focus is not False:
            failures.append(
                f"AZ85: AFTER in-focus={after_focus}, expected False "
                f"(the detector is ~7.76mm from best focus -- the flagged 'defocus at the image')"
            )
        notes.append(
            f"AFTER: solve(image)={after_img} solve(object)={after_obj} mag={after_mag} in_focus={after_focus}"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 integration raised {exc!r}")

    # (3) scope: no flat equivalent off the folding-mesh-mirror path.
    for layout, label in ((_PLAIN, "sequential flat mirror"), (_BS_CUBE, "straight-through BS cube")):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                other = _build_editor(layout)
                other._build_preview_system_rays_bundle(update_state=True)
                equiv = other._folded_optical_solid_straight_equivalent_rows()
            if equiv is not None:
                failures.append(
                    f"regression: {layout} ({label}) built a flat equivalent ({len(equiv)} rows) "
                    f"-- the fix must be inert off the folding-mesh-mirror path"
                )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{label} scope check raised {exc!r}")

    if failures:
        print("FAIL bugs/0195 folded RA-mirror Quick Estimation (conjugate solve + in-focus):")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0195 folded RA-mirror Quick Estimation (conjugate solve + in-focus):")
    print("  - BEFORE the folded QE solve throws and the in-focus check is unavailable")
    print(f"  - AFTER solve('image')~{_EXPECTED_IMAGE:.2f}mm, solve('object')~{_EXPECTED_OBJECT:.2f}mm, "
          f"mag~{_EXPECTED_MAG}, in-focus=False (defocus flagged)")
    print(f"  - scope: {_PLAIN} and {_BS_CUBE} build no flat equivalent (inert off the folding path)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
