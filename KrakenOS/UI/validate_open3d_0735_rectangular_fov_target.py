"""Guard for bugs/0735 -- a rectangular field fills a rectangular sensor on ONE axis.

Flag 20260907_104239_564: "is this something correct?" -- the scene showed the lens driven
13.03 mm into RA mirror 1 by an auto-applied force (bugs/0732), for a request of
"21 x 1.05 mm (needs |m| 1.549)".

It was not correct, and the crash was avoidable. The solve sized its target by the DIAGONAL
(sensor semi-diagonal / object semi-diagonal). That is right for a round image circle and wrong
for a long thin field: the user's 20 x 1 mm device asks for 21 x 1.05 mm, whose diagonal (21.03)
is essentially its long side, so the diagonal rule demanded |m| 1.549 where 23.04 / 21 = 1.097
already fills the sensor. The extra 41% of magnification needed 172 mm of lens travel against
158.9 mm of room -- hence the collision.

With the rectangular rule the same request solves cleanly: |m| 1.097, lens -135 mm, no penetration.

Checks (display-free):
  A  the rule is min(Sw/W, Sh/H) -- the axis that runs out first -- and it is orientation-aware.
  B  a bare lens (no sensor rectangle) keeps the diagonal rule, where the image circle IS the
     constraint; unusable inputs return None rather than a wrong target.
  C  wiring: the solve encodes the target in the image semi it hands _apply_conjugate_pair, the
     idempotence gate and the refusal stash use the SAME target, and it is computed before both.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0735_rectangular_fov_target
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def _service(sensor_wh):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = SimpleNamespace(_current_camera_sensor_active_mm=lambda: sensor_wh)
    return QuickEstimationService(SimpleNamespace(editor=editor))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    square = _service((23.04, 23.04))

    # ---- A: the rule ---------------------------------------------------------------------------
    thin = square._rectangular_target_magnification(21.0, 1.05)
    ok(
        thin is not None and abs(thin - 23.04 / 21.0) < 1e-9,
        f"A1: the om05a case -- a 21 x 1.05 field on a 23.04 mm sensor needs |m| {23.04 / 21.0:.4f}, "
        f"not the diagonal's 1.549 (got {thin:.4f})",
    )
    fat = square._rectangular_target_magnification(1.05, 21.0)
    ok(
        fat is not None and abs(fat - 23.04 / 21.0) < 1e-9,
        "A2: it is orientation-aware -- a tall thin field is limited by its own long axis too",
    )
    even = square._rectangular_target_magnification(20.0, 20.0)
    ok(
        even is not None and abs(even - 23.04 / 20.0) < 1e-9,
        f"A3: a square field is unchanged by the rule ({even:.4f})",
    )
    landscape = _service((23.04, 17.28))._rectangular_target_magnification(20.0, 20.0)
    ok(
        landscape is not None and abs(landscape - 17.28 / 20.0) < 1e-9,
        f"A4: on a NON-square sensor the short axis is the one that runs out ({landscape:.4f})",
    )

    # ---- B: when NOT to apply it -------------------------------------------------------------------
    def _raises():
        raise RuntimeError("no camera")

    bare = QuickEstimationService(SimpleNamespace(editor=SimpleNamespace(_current_camera_sensor_active_mm=_raises)))
    ok(
        bare._rectangular_target_magnification(21.0, 1.05) is None,
        "B1: no sensor rectangle (a bare lens) -> None, so the diagonal rule stands",
    )
    ok(
        square._rectangular_target_magnification(0.0, 1.05) is None
        and square._rectangular_target_magnification(21.0, 0.0) is None
        and _service((0.0, 23.04))._rectangular_target_magnification(21.0, 1.05) is None,
        "B2: a zero field or sensor dimension -> None rather than an infinite target",
    )

    # ---- C: wiring ------------------------------------------------------------------------------------
    solve = inspect.getsource(QuickEstimationService.fov_solve)
    target_at = solve.find("target_m = self._rectangular_target_magnification(obj_w, obj_h)")
    gate_at = solve.find("_fov_already_delivered(image_semi")
    apply_at = solve.find("_apply_conjugate_pair(semi, image_semi / correction")
    ok(
        target_at > 0 and apply_at > target_at,
        "C1: the solve hands _apply_conjugate_pair an image semi carrying the rectangular target",
    )
    ok(
        gate_at > target_at,
        "C2: the idempotence gate uses the SAME target (computed before it), so a re-solve of a "
        "rectangular field is still a no-op",
    )
    ok(
        'info.setdefault("target_m", float(image_semi) / float(semi))' in solve,
        "C3: the refusal banner quotes the rectangular target, not the diagonal one",
    )
    ok(
        "float(semi) * float(target_m) if target_m is not None else float(sensor)" in solve,
        "C4: with no rectangular target the diagonal sensor semi is used unchanged",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0735 rectangular-FOV-target validation PASSED")
        return 0
    print("0735 rectangular-FOV-target validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
