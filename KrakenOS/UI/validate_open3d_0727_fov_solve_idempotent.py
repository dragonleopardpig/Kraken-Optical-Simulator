"""Guard for bugs/0727 -- re-solving a field the scene already delivers is a NO-OP.

User: "make the solve idempotent." Measured on om05a before the fix: solving FOV 20x20 moved
the lens -138.6 mm and succeeded; solving the SAME 20x20 again refused with "No real-image
conjugate for that size (near the focal point?)" while the object-side term was exactly
0.0000 mm and the delivered field was 20.002 x 20.002 mm. The solve derives from the CURRENT
geometry, so the second pass re-asked for a move that was already made and the image-side term
swung to -98 mm ("the sensor would sit inside the optics").

That message also misled: the user read it as a working-distance limit. It is not -- the object
side was reachable; the IMAGE side was not, because the camera is fixed.

Checks (display-free):
  A  _fov_already_delivered: matches inside the tolerance and reports the delivered field;
     returns None outside it, and on unusable input (zero/None magnification).
  B  wiring: the gate runs BEFORE the conjugate move; the no-op keeps the focus residual and a
     FORCED banner (which still describes the geometry) but not a stale plain refusal; it still
     re-books the target FOV and the split-field band widths.
  C  the forced repeat says there is nothing to force.
  D  the folded conjugate solver stashes a MEASURED reason at each bail (which side failed, by
     how much) and clears it on entry; the FOV solve prefers that reason over the generic text.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0727_fov_solve_idempotent
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    def service(magnification, sensor_wh=(23.04, 23.04)):
        editor = SimpleNamespace(
            _current_finite_paraxial_magnification=lambda: magnification,
            _current_camera_sensor_active_mm=lambda: sensor_wh,
        )
        return QuickEstimationService(SimpleNamespace(editor=editor))

    # om05a: sensor semi-diagonal 16.29, FOV 20x20 -> object semi-diagonal 14.14, |m| 1.1519
    sensor_semi, object_semi = 16.2917, 14.1436
    target_m = sensor_semi / object_semi

    # ---- A: the pure gate --------------------------------------------------------------------
    exact = service(target_m)._fov_already_delivered(sensor_semi, object_semi)
    ok(
        exact is not None and abs(exact[0] - target_m) < 1e-9 and len(exact[1]) == 2,
        f"A1: the delivered field matches the request -> no-op with the delivered size ({exact})",
    )
    near = service(target_m * 1.002)._fov_already_delivered(sensor_semi, object_semi)
    far = service(target_m * 1.05)._fov_already_delivered(sensor_semi, object_semi)
    ok(
        near is not None and far is None,
        f"A2: within 0.5% counts as delivered, 5% off does not (near={near is not None}, far={far is not None})",
    )
    ok(
        service(None)._fov_already_delivered(sensor_semi, object_semi) is None
        and service(0.0)._fov_already_delivered(sensor_semi, object_semi) is None
        and service(target_m)._fov_already_delivered(sensor_semi, 0.0) is None,
        "A3: unusable magnification or a zero object semi -> no claim (the solve runs normally)",
    )
    delivered_wh = exact[1] if exact else (0.0, 0.0)
    ok(
        abs(delivered_wh[0] - 23.04 / target_m) < 1e-6,
        f"A4: the reported field is the sensor divided by the delivered |m| ({delivered_wh[0]:.4f} mm)",
    )

    # ---- B / C: wiring ------------------------------------------------------------------------
    source = inspect.getsource(QuickEstimationService.fov_solve)
    gate_at = source.find("_fov_already_delivered(")
    move_at = source.find("_apply_conjugate_pair(semi")
    ok(
        gate_at > 0 and move_at > 0 and gate_at < move_at,
        "B1: the idempotence gate runs BEFORE the conjugate move",
    )
    ok(
        "self.editor._fov_solve_focus_residual_info = prior_focus_residual" in source
        and "prior_forced_info" in source
        and "solve_banner_outcome" in source,
        "B2: a no-op restores the focus residual and keeps a FORCED banner (a stale refusal is not kept)",
    )
    ok(
        "self.set_target_fov(semi)" in source[gate_at:move_at]
        and "_update_split_field_band_widths(obj_w)" in source[gate_at:move_at],
        "B3: the no-op still books the target FOV and the split-field band widths",
    )
    ok(
        "nothing to force" in source,
        "C1: a forced repeat of a delivered field says there is nothing to force",
    )

    # ---- D: the measured refusal reason -------------------------------------------------------
    from KrakenOS.UI.services import paraxial_tools

    folded = inspect.getsource(paraxial_tools.ParaxialToolsMixin._folded_conjugate_gaps_for_magnification)
    ok(
        folded.count("_folded_conjugate_refusal") >= 2 and 'self._folded_conjugate_refusal = ""' in folded,
        f"D1: the folded solver clears its reason on entry and stashes one at each REFUSING bail "
        f"({folded.count('_folded_conjugate_refusal')} references)",
    )
    # bugs/0731 (user: "Only apply to real collision will do") retired the image-side REFUSAL:
    # that path now flags the result and the solve reports a focus residual instead. What must
    # still name its reason is the OBJECT-side bail -- the one that really cannot proceed.
    ok(
        "no lens-leg slide to book it on" in folded
        and "OBJECT side is reachable" not in folded
        and "image_side_unreachable = True" in folded,
        "D2: the OBJECT-side bail still names its reason; the image side no longer refuses "
        "(superseded by bugs/0731, guarded by penta 530)",
    )
    ok(
        "No real-image conjugate for that size: {folded_reason}" in source
        or 'f"No real-image conjugate for that size: {folded_reason}"' in inspect.getsource(QuickEstimationService),
        "D3: the FOV solve prefers the measured reason over the generic 'near the focal point?' text",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0727 FOV-solve idempotence validation PASSED")
        return 0
    print("0727 FOV-solve idempotence validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
