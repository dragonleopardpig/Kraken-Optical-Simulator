"""Guard for bugs/0645 — an out-of-reach traced focus recruits the fold's near leg,
and the solve never claims focus it did not measure.

flag_20260824_201012/201312 (ELS85, "solved for FOV 20x20, image side ray defocus"): a
MAGNIFYING solve (|m|=1.152, the untested regime) put the traced focus 23.5 mm BEHIND the
image-side fold mirror (scanned: axial blur monotone toward the mirror, zero extrapolates
to a -23.5 mm exit leg) -- no sensor position on the exit leg could reach it. The snap's
0570 pre-flip guessed "sign error" and moved the sensor +82.65 mm the WRONG way, the 0577
guard reverted (net movement 0.0000 mm), the 0515-B2 adaptive flip was dead code (0577
broke the loop before it could run) -- and the solve still reported "snapped to the traced
focus" while _snap_detector_refusal held the recorded refusal.

The general fix (all imaging-lens scenes, both regimes):
  1. the 0577 guard grants ONE measured retry in the opposite direction (the 0515-B2
     intent, now alive);
  2. a still-negative target leg recruits the NEAR leg -- _recruit_image_fold_near_leg
     slides the fold mirror toward the lens via _apply_folded_image_split("near", ...)
     (near shrinks, far grows, focus unchanged) so a positive exit leg exists;
  3. the loop's revert snapshot also restores STEP overlay placement offsets (the settle
     walks the camera BODY with the sensor -- the bugs/0626 snapshot mechanism);
  4. _finish_solve_on_traced_focus claims "snapped to the traced focus" only when the
     re-measured residual IS small, and surfaces _snap_detector_unreachable_mm.

Checks (display-free):
  A  the snap loop has the one-shot direction retry (restore best, flip, continue).
  B  the loop recruits via _recruit_image_fold_near_leg, which routes through
     _apply_folded_image_split("near", ...); numeric stub: amount clamps to the near
     room and the applier is asked for near - give.
  C  the revert snapshot covers STEP overlay placement offsets, not just rows.
  D  the solve finisher's "snapped to the traced focus" claim is gated by the measured
     residual, and the out-of-reach warning path exists.
  E  snap_detector_to_image_plane resets and honestly publishes
     _snap_detector_unreachable_mm.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0645_focus_reach_recruitment
"""

from __future__ import annotations

import inspect
import re


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    snap_src = inspect.getsource(ScenePlacementMixin.snap_detector_to_image_plane)

    # ---------------------------------------------------------------- A: the live retry
    has_retry = (
        "flip_retry_used" in snap_src
        and re.search(
            r"if not flip_retry_used:\s*\n(?:.*\n)*?\s*flip_retry_used = True\s*\n"
            r"(?:.*\n)*?\s*direction = -direction\s*\n(?:.*\n)*?\s*continue",
            snap_src,
        )
        is not None
    )
    if not has_retry:
        ok = False
        notes.append(
            "FAIL: A (bugs/0645): the snap loop has no measured direction retry -- a wrong 0570 "
            "pre-flip guess burns the only pass and the sensor never moves"
        )
    else:
        notes.append("PASS: A: one measured opposite-direction retry before declaring divergence")

    # ---------------------------------------------------------------- B: recruitment
    recruit = getattr(ScenePlacementMixin, "_recruit_image_fold_near_leg", None)
    if recruit is None or "_recruit_image_fold_near_leg(" not in snap_src:
        ok = False
        notes.append(
            "FAIL: B (bugs/0645): the snap loop does not recruit the near leg -- a focus behind "
            "the fold mirror stays unreachable and the scene stays defocused"
        )
    else:
        recruit_src = inspect.getsource(recruit)
        if '_apply_folded_image_split("near"' not in recruit_src:
            ok = False
            notes.append(
                "FAIL: B (bugs/0645): recruitment no longer routes through the focus-preserving "
                "near-leg repackaging (_apply_folded_image_split)"
            )
        else:
            calls = []

            class _Stub:
                def _folded_image_conjugate_split(self):
                    return {"near": 100.0, "near_min": 20.0}

                def _apply_folded_image_split(self, which, value):
                    calls.append((which, float(value)))
                    return True, ""

            got = ScenePlacementMixin._recruit_image_fold_near_leg(_Stub(), 200.0)
            if abs(got - 80.0) > 1e-9 or calls != [("near", 20.0)]:
                ok = False
                notes.append(
                    f"FAIL: B (bugs/0645): recruit(200) on near=100/near_min=20 gave {got} with "
                    f"calls {calls} -- expected 80.0 recruited via ('near', 20.0)"
                )
            else:
                notes.append(
                    "PASS: B: near-leg recruitment slides the mirror through the focus-preserving "
                    "repackaging, clamped to the collision floor"
                )

    # ---------------------------------------------------------------- C: snapshot coverage
    if "_step_overlay_label_set" not in snap_src or "_set_step_placement_offset_xyz" not in snap_src:
        ok = False
        notes.append(
            "FAIL: C (bugs/0645): the loop's revert snapshot no longer covers STEP overlay "
            "placement offsets -- a reverted pass strands the camera body at the failed pose"
        )
    else:
        notes.append("PASS: C: the revert snapshot restores rows AND STEP overlay offsets")

    # ---------------------------------------------------------------- D: measured claims
    fin_src = inspect.getsource(QuickEstimationService._finish_solve_on_traced_focus)
    gated = re.search(
        r"if abs\(after\) <= 0\.5:\s*\n(?:.*\n)*?.*snapped to the traced focus", fin_src
    )
    warns = "beyond the fold's reach" in fin_src and "_snap_detector_unreachable_mm" in fin_src
    if gated is None or not warns:
        ok = False
        notes.append(
            "FAIL: D (bugs/0645): the solve finisher claims 'snapped to the traced focus' without "
            "measuring the residual, or drops the out-of-reach warning -- the ELS85 dishonesty"
        )
    else:
        notes.append("PASS: D: the focus claim is gated by the measured residual; out-of-reach warns")

    # ---------------------------------------------------------------- E: the published remainder
    resets = re.search(r"self\._snap_detector_unreachable_mm = 0\.0", snap_src)
    publishes = re.search(
        r"self\._snap_detector_unreachable_mm = \(\s*\n\s*float\(unreachable_mm\) if best_magnitude > 0\.5 else 0\.0",
        snap_src,
    )
    if resets is None or publishes is None:
        ok = False
        notes.append(
            "FAIL: E (bugs/0645): _snap_detector_unreachable_mm is not reset on entry and "
            "published honestly at loop exit -- callers cannot report the true remainder"
        )
    else:
        notes.append("PASS: E: the unreachable remainder is reset on entry and published at exit")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Focus-reach-recruitment validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
