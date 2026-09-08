"""Guard for bugs/0753 -- a field that is ALREADY in focus is a focus measurement, and nine rays
are not evidence.

Found while measuring the om05a leg sweep: at the 54.09 mm station arm B's drawn focus plane read
-105.37 mm while arm A read -0.05 mm, with both arms landing 322 rays and identical |m| to seven
digits. Impossible optically -- the arms are mirror images. The per-field votes:

    arm B ('source:faceB', 3)  n=101  offset   -0.0111  waist  0.73um  plane  0.83um  VOTES=False
    arm B ('source:faceB', 4)  n=106  offset  -25.5391  waist 1996.74  plane 2257.49  VOTES=False
    arm B ('source:faceB', 5)  n=106  offset  -25.5430  waist 1996.89  plane 2257.35  VOTES=False
    arm B ('source:faceB', 6)  n=  9  offset -105.3673  waist 2846.79  plane 8855.00  VOTES=True

The vote was ``rms_waist < 0.5 * rms_plane`` -- purely RELATIVE. Two consequences, both wrong:
a field already AT focus cannot tighten by 2x and was rejected for being sharp, while a field
blurred everywhere passed because 2.8 mm is less than half of 8.9 mm. Arm B had no other voter,
so nine junk rays set the plane.

Checks (display-free, pure functions, deterministic fixture):
  A  the failure shape is reproduced: the junk group is the ONLY one the old relative test admits.
  B  the measurement now picks the well-sampled sharp field, and reports its offset.
  C  under-sampled groups are dropped even when they tighten; already-sharp groups vote.
  D  a genuinely defocused bundle is unchanged -- the field that really tightens still wins.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0753_a_sharp_field_is_a_focused_field
"""

from __future__ import annotations

import inspect

import numpy as np


def _group(centre, iu, iv, normal, n, ring_mm, offset_mm, jitter, seed):
    """A cone landing on a ring of radius ``ring_mm`` and converging near ``offset_mm``, with
    angular jitter that sets how tight the waist gets. Deterministic."""
    rs = np.random.RandomState(seed)
    waist_point = centre + offset_mm * normal
    ends, dirs = [], []
    for k in range(n):
        theta = 2.0 * np.pi * k / n
        end = centre + ring_mm * (np.cos(theta) * iu + np.sin(theta) * iv)
        d = waist_point - end
        d = d / np.linalg.norm(d)
        d = d + jitter * (rs.randn() * iu + rs.randn() * iv)
        dirs.append(d / np.linalg.norm(d))
        ends.append(end)
    return ends, dirs


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import detector_coverage_overlay as dco

    centre = np.zeros(3)
    normal = np.array([0.0, -1.0, 0.0])
    iu, iv = dco._basis(normal)

    # the arm-B shape: one well-sampled ALREADY-SHARP field, two well-sampled blurred ones, and a
    # nine-ray field that is blurred everywhere but halves between the sensor and its "waist".
    SHARP, BLUR_A, BLUR_B, JUNK = 0, 1, 2, 3
    specs = [
        (101, 0.0008, -0.011, 0.064, 11),
        (106, 2.257, -25.54, 0.075, 12),
        (106, 2.257, -25.54, 0.075, 13),
        (9, 8.855, -105.37, 0.027, 14),
    ]
    groups = [_group(centre, iu, iv, normal, *s) for s in specs]
    singles = [
        dco.focus_waist_from_rays(e, d, image_point=centre, image_axis=normal, min_rays=4)
        for e, d in groups
    ]
    ok(all(s is not None for s in singles), "A0: every fixture group yields a waist fit")
    if any(s is None for s in singles):
        return False, notes
    tightens = [float(s["rms_waist_mm"]) < 0.5 * float(s["rms_plane_mm"]) for s in singles]
    ok(
        tightens == [False, False, False, True],
        f"A1: the failure shape is reproduced -- the 9-ray junk field is the ONLY one the old "
        f"relative test admits ({tightens})",
    )
    ok(
        float(singles[SHARP]["rms_waist_mm"]) < float(singles[BLUR_A]["rms_waist_mm"]) / 100.0,
        f"A2: and the rejected field is by far the sharpest "
        f"({float(singles[SHARP]['rms_waist_mm']) * 1000:.2f} um vs "
        f"{float(singles[BLUR_A]['rms_waist_mm']) * 1000:.0f} um)",
    )

    # ---- B: the measurement picks the sharp, well-sampled field --------------------------------
    result = dco.focus_waist_from_grouped_rays(groups, image_point=centre, image_axis=normal)
    ok(isinstance(result, dict), "B0: the grouped measurement returns a result")
    if not isinstance(result, dict):
        return False, notes
    ok(
        int(result.get("group_index", -1)) == SHARP,
        f"B1: the WELL-SAMPLED SHARP field sets the plane, not the 9-ray outlier "
        f"(group_index {result.get('group_index')})",
    )
    ok(
        abs(float(result["offset_mm"])) < 1.0,
        f"B2: so the reported offset is the sharp field's ({float(result['offset_mm']):+.4f} mm), "
        f"not the outlier's ~-102 mm",
    )
    ok(
        int(result.get("ray_count", 0)) >= 100,
        f"B3: and it rests on real sampling ({result.get('ray_count')} rays, not 9)",
    )

    # ---- C: each filter does its own job -------------------------------------------------------
    ok(
        dco._MIN_SAMPLE_SHARE * 106.0 > 9.0,
        f"C1: the sampling share ({dco._MIN_SAMPLE_SHARE}) drops a 9-ray group beside a 106-ray "
        f"one before any vote is counted",
    )
    only_junk = dco.focus_waist_from_grouped_rays(
        [groups[BLUR_A], groups[JUNK]], image_point=centre, image_axis=normal
    )
    ok(
        isinstance(only_junk, dict) and int(only_junk.get("group_index", -1)) != 1,
        "C2: with only a blurred field and the junk field, the junk field still does not win",
    )
    sharp_only = dco.focus_waist_from_grouped_rays(
        [groups[SHARP]], image_point=centre, image_axis=normal
    )
    ok(
        isinstance(sharp_only, dict)
        and not bool(sharp_only.get("pooled"))
        and abs(float(sharp_only["offset_mm"])) < 1.0,
        "C3: an already-sharp field measures on its own -- being in focus is a focus "
        "measurement, not a failed vote (this is what the old test got backwards)",
    )

    # ---- D: a genuinely defocused bundle is unchanged -------------------------------------------
    defocused = [
        _group(centre, iu, iv, normal, 106, 1.6, -18.0, 0.004, 21),
        _group(centre, iu, iv, normal, 106, 1.6, -18.0, 0.004, 22),
    ]
    plain = dco.focus_waist_from_grouped_rays(defocused, image_point=centre, image_axis=normal)
    ok(
        isinstance(plain, dict) and abs(float(plain["offset_mm"]) + 18.0) < 2.0,
        f"D1: a real defocus still measures where it always did "
        f"({float(plain['offset_mm']) if isinstance(plain, dict) else None} mm, expected ~-18)",
    )
    ok(
        isinstance(plain, dict) and int(plain.get("field_count", 0)) == 2,
        "D2: and both fields still vote when both genuinely tighten (bugs/0728 unchanged)",
    )

    # ---- E: the filters are in the production path ----------------------------------------------
    src = inspect.getsource(dco.focus_waist_from_grouped_rays)
    ok(
        "_MIN_SAMPLE_SHARE" in src and "_SHARP_WAIST_FACTOR" in src,
        "E1: both filters live in the real measurement",
    )
    ok(
        src.find("_MIN_SAMPLE_SHARE") < src.find("already_sharp")
        and src.find("already_sharp") < src.find("offsets.append"),
        "E2: sampling is filtered first, then the vote, then the tally -- an under-sampled group "
        "never reaches the vote at all",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0753 sharp-field-is-a-focused-field validation PASSED")
        return 0
    print("0753 sharp-field-is-a-focused-field validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
