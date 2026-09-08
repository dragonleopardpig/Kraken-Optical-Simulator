"""Guard for bugs/0754 -- when the solve leaves a focus residual, NAME the field that lands.

Flag 20260908_133248_992: "Device size 30mm. Two seperate image planes shown, they are
deteched from the sensor. Why the image is not landed on the sensor? I need a configuration to
land the image on the sensor."

The solve did exactly what it was asked: delivering 31.5 x 31.5 mm (|m| 0.7314) by moving the
lens -90.84 mm, and it reported the consequence -- "the image forms 65.75 mm in front of the
sensor". What it never said is that a FIXED TRACK focuses exactly two magnifications, and that
this one focuses |m| 0.4262 (a 54.05 mm field). The user was told their request failed, with no
way out in the scene.

Checks (display-free, pure):
  A  the inverse solve recovers the analytic conjugate roots of the SAME model the solve uses,
     so the two readouts cannot disagree;
  B  it converts them to object fields with the real sensor dimensions, largest first, and
     degrades to [] rather than guessing when the model or the sensor is unavailable;
  C  the residual stash carries them and the HUD renders a line naming the field that lands;
  D  a scene with no residual still renders nothing.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0754_name_the_field_that_lands
"""

from __future__ import annotations

import inspect
import math
from types import SimpleNamespace


def _model_editor(f: float, K: float, sensor=(23.04, 23.04), broken: bool = False):
    """An editor stub whose first-order model is the textbook conjugate law:
    image_delta(m) = f*(2 + m + 1/m) - K, zero exactly at the reciprocal root pair."""

    class Stub:
        def _folded_conjugate_gaps_for_magnification(self, magnitude):
            if broken:
                raise RuntimeError("model unavailable")
            m = float(magnitude)
            if m <= 0.0:
                return None
            return {"image_delta": f * (2.0 + m + 1.0 / m) - K, "magnitude": m}

        def _current_camera_sensor_active_mm(self):
            if sensor is None:
                raise RuntimeError("no camera")
            return sensor

    return Stub()


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services import system_info_hud as hud

    # om05a_folded_80mm's fitted first order
    f, K = 82.407, 392.60
    service = QuickEstimationService(SimpleNamespace(editor=_model_editor(f, K)))
    fields = service._in_focus_fields_at_current_track()

    # analytic roots of f*m^2 + (2f - K)*m + f = 0
    b = 2.0 * f - K
    disc = b * b - 4.0 * f * f
    lo = (-b - math.sqrt(disc)) / (2.0 * f)
    hi = (-b + math.sqrt(disc)) / (2.0 * f)
    ok(len(fields) == 2, f"A1: a fixed track focuses TWO magnifications, and both are found "
                         f"({len(fields)})")
    if len(fields) == 2:
        found = sorted(entry["m"] for entry in fields)
        ok(
            abs(found[0] - lo) < 1.0e-6 and abs(found[1] - hi) < 1.0e-6,
            f"A2: they are the analytic reciprocal pair ({found[0]:.7f}, {found[1]:.7f} vs "
            f"{lo:.7f}, {hi:.7f})",
        )
        ok(
            abs(found[0] * found[1] - 1.0) < 1.0e-6,
            f"A3: and they are reciprocal, as the conjugate law requires "
            f"(product {found[0] * found[1]:.7f})",
        )
        ok(
            abs(fields[0]["field_w_mm"] - 23.04 / lo) < 1.0e-6,
            f"B1: converted to an object field with the real sensor width "
            f"({fields[0]['field_w_mm']:.4f} mm)",
        )
        ok(
            fields[0]["field_w_mm"] > fields[1]["field_w_mm"],
            "B2: largest field first -- the one a user asking for a big part wants",
        )
    ok(
        QuickEstimationService(
            SimpleNamespace(editor=_model_editor(f, K, broken=True))
        )._in_focus_fields_at_current_track() == [],
        "B3: an unavailable first-order model yields [] -- never a guessed field",
    )
    ok(
        QuickEstimationService(
            SimpleNamespace(editor=_model_editor(f, K, sensor=None))
        )._in_focus_fields_at_current_track() == [],
        "B4: an unavailable sensor yields [] too",
    )
    ok(
        QuickEstimationService(
            SimpleNamespace(editor=_model_editor(f, 4.0 * f - 1.0))
        )._in_focus_fields_at_current_track() == [],
        "B5: a track SHORTER than 4f focuses nothing, and nothing is claimed",
    )

    # ---- C: the stash and the HUD ----------------------------------------------------------
    # the residual is stashed by _apply_conjugate_pair, which every fov_solve path routes through
    solve_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        '"in_focus_fields": self._in_focus_fields_at_current_track(),' in solve_src
        and '"image_delta_mm": residual,' in solve_src,
        "C1: the field list is stashed in the SAME dict as the residual, by the conjugate "
        "solve every fov_solve path routes through",
    )
    ok(
        "_apply_conjugate_pair(" in inspect.getsource(QuickEstimationService.fov_solve),
        "C1b: and fov_solve does route through it",
    )
    lines = hud.format_focus_residual_lines(
        {
            "image_delta_mm": -65.75,
            "lens_move_mm": -90.84,
            "in_focus_fields": [{"m": 0.4262, "field_w_mm": 54.05, "field_h_mm": 54.05}],
        }
    )
    ok(
        any("DOES focus" in line and "54.05" in line for line in lines),
        f"C2: the HUD names the field that lands ({[l[:44] for l in lines]})",
    )
    ok(
        any("65.75" in line for line in lines),
        "C3: alongside the residual it always reported (bugs/0719 unchanged)",
    )
    ok(
        any("ask for that" in line for line in lines),
        "C4: and says what to do with it -- a way out, not just a diagnosis",
    )

    # ---- D: nothing invented when there is nothing to say -------------------------------------
    ok(hud.format_focus_residual_lines(None) == [], "D1: no residual -> no lines")
    ok(
        not any(
            "DOES focus" in line
            for line in hud.format_focus_residual_lines({"image_delta_mm": -1.0})
        ),
        "D2: a residual without the field list renders no claim about what would land",
    )
    ok(
        not any(
            "DOES focus" in line
            for line in hud.format_focus_residual_lines(
                {"image_delta_mm": -1.0, "in_focus_fields": [{"m": "bad"}]}
            )
        ),
        "D3: a malformed entry is skipped, not rendered half-formed",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0754 name-the-field-that-lands validation PASSED")
        return 0
    print("0754 name-the-field-that-lands validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
