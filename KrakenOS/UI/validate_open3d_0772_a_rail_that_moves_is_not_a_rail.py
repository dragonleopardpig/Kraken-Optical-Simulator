"""Guard for bugs/0772 -- a hardware rail must not move when the lens moves.

Flag `20260910_162743`: "device size set to 23x23x1mm, image plane dislocate, only 2 rays,
worse than before." Measured on om05a_folded_80mm: the solve moved the lens -120.6 mm correctly
and then did NOT book the image side, leaving the image 77.2 mm off with a 1970 um spot, because

    the imaging group would have to travel to 192 mm, outside its 192.7 to 292.7 mm stage

-- a **0.66 mm** miss against limits that were guessed before the user said "the A5+C1 is where
the motors can travel". The authored geometry gives seat 269.120, A5 130.889 in front and C1
17.510 behind, i.e. a rail of [138.231, 286.630], which contains 192.0 comfortably. With it the
same case lands: armx 191.979, 644 rays (from 216), -0.081 mm, 2.10 um -- inside one pixel.

bugs/0766 added `_motor_rail_from_lens_block` to derive those limits instead of hand-typing them,
and it was wrong in a way the authored state hides: it read the LIVE gaps. `a5` and `c1` track the
LENS, not the arm, so mid-solve (lens at a5 = 10.265) it produced [258.9, 407.3] -- further from
the truth than the guess it replaced.

Checks (display-free, pure):
  A  the helper no longer reports travel limits it cannot anchor;
  B  it still reports what it CAN measure -- the rail length and the three row indices;
  C  the rail length is the invariant a5 + c1, so it is stable under the lens's thickness pair;
  D  `_camera_focus_stage` still honours the limits a scene states.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0772_a_rail_that_moves_is_not_a_rail
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Row:
    def __init__(self, name="", thickness=0.0, desp_x=0.0):
        self.name, self.thickness, self.desp_x = name, float(thickness), float(desp_x)
        self.desp_y = self.desp_z = 0.0


def _editor(a5, c1):
    """A minimal om05a-shaped chain: gap, lens block, gap, filter, gap, seat, ..., pad, image."""
    rows = [
        _Row("Object"), _Row("fold"), _Row("prism exit gap (air)", a5),
        _Row("Front Optical Vertex Datum"), _Row("Blackbox"), _Row("Aperture Stop"),
        _Row("Blackbox 2"), _Row("Rear Optical Vertex Datum", c1),
        _Row("Filter", 1.0), _Row("to camera", 31.11),
        _Row("RA mirror 2", 36.31, desp_x=269.120),
        _Row("placed", 0.0), _Row("sensor standoff", 9.67), _Row("Image"),
    ]
    return SimpleNamespace(
        rows=rows,
        _imaging_lens_block_indices=lambda: (3, 7),
        camera_focus_stage=None,
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    svc = QuickEstimationService(SimpleNamespace(editor=_editor(130.889, 17.510)))
    rail = svc._motor_rail_from_lens_block()
    ok(isinstance(rail, dict), f"A0: the helper still answers on an om05a-shaped chain ({rail!r})")
    if isinstance(rail, dict):
        leaked = sorted(k for k in rail if k.endswith("_min_mm") or k.endswith("_max_mm"))
        ok(
            not leaked,
            f"A1: it reports NO travel limits -- they cannot be anchored once a solve has moved "
            f"the lens, and a rail that moves when the lens moves is not a rail (leaked {leaked})",
        )
        ok(
            {"row", "arm_row", "arm_carry_row", "rail_mm"} <= set(rail),
            f"B1: it still reports what it CAN measure -- the rail length and the row indices "
            f"({sorted(rail)})",
        )
        ok(
            abs(float(rail.get("rail_mm", 0)) - 148.399) < 0.01,
            f"B2: the rail length is A5 + C1 = 148.400 (got {rail.get('rail_mm')})",
        )

    # ---- C: invariant under the lens's thickness pair ----------------------------------------
    moved = QuickEstimationService(
        SimpleNamespace(editor=_editor(10.265, 138.134))
    )._motor_rail_from_lens_block()
    if isinstance(rail, dict) and isinstance(moved, dict):
        ok(
            abs(float(rail["rail_mm"]) - float(moved["rail_mm"])) < 0.01,
            f"C1: the rail length is the SAME with the lens slid 120 mm along it "
            f"({rail['rail_mm']:.3f} vs {moved['rail_mm']:.3f}) -- that invariance is why it is "
            f"reportable and the anchored limits are not",
        )

    # ---- D: a scene's own limits still win ----------------------------------------------------
    ed = _editor(130.889, 17.510)
    ed.camera_focus_stage = {
        "enabled": True, "row": 12, "min_mm": -121.219, "max_mm": 27.18,
        "arm_row": 10, "arm_min_mm": 138.231, "arm_max_mm": 286.63, "arm_carry_row": 7,
    }
    stage = QuickEstimationService(SimpleNamespace(editor=ed))._camera_focus_stage()
    ok(
        isinstance(stage, dict) and isinstance(stage.get("arm"), dict),
        f"D1: a scene that states its stage still gets one ({stage!r})",
    )
    if isinstance(stage, dict) and isinstance(stage.get("arm"), dict):
        ok(
            abs(stage["arm"]["min_mm"] - 138.231) < 1e-6
            and abs(stage["arm"]["max_mm"] - 286.63) < 1e-6,
            f"D2: with the scene's OWN limits, untouched by the helper ({stage['arm']})",
        )
        ok(
            stage["arm"]["min_mm"] <= 192.0 <= stage["arm"]["max_mm"],
            "D3: and that rail admits the 192.0 mm the flagged 23x23 case needed -- the 0.66 mm "
            "miss that left the image 77.2 mm off",
        )

    src = inspect.getsource(QuickEstimationService._motor_rail_from_lens_block)
    ok(
        "arm_min_mm" not in src and "arm_max_mm" not in src,
        "A2: and the derivation itself no longer computes them at all",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0772 a-rail-that-moves-is-not-a-rail validation PASSED")
        return 0
    print("0772 a-rail-that-moves-is-not-a-rail validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
