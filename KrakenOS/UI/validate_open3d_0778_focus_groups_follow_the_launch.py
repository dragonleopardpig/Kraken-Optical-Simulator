"""Guard for bugs/0778 -- focus groups follow the LAUNCH POINT, so the two arms agree.

The user, across several flags: *"why not symmetry?"* -- one arm of the split field reported a
~400 um waist while the other reported sub-micron, on a bench that is a mirror image about
z = -25.

A six-lens measurement audit settled that the hardware is innocent:

    bodies / rows      symmetric to 35 nm; placements pair to a midpoint of exactly -25.000
    traced bundles     1103 paths each, identical termination histograms,
                       max|mirror(A about z=-25) - B| = 0.0
    landings           exact mirrors

So identical rays were producing two different answers, which can only be the readout. It was:

    launch structure   arm A: 7 points, groups [361,361,361,5,5,5,5]
                       arm B: 7 points, groups [361,361,361,5,5,5,5]   <- identical
    field_index        arm A: {0:361, 1:361, 2:361, 3:20}
                       arm B: {3:341, 4:361, 5:361, 6:40}              <- boundaries 20 out

``field_index`` is a uniform ray-index division (scene_builder._launch_field_group's fallback)
sliding over a RAGGED launch -- the launch appends corner probes, so some fields carry 5 rays and
others 361. Arm B's boundaries land 20 rays out of step, which invented a 0.98 um "sharp field"
for arm B and disqualified that arm's other fields through the bugs/0753 vote.

A field point is a PLACE ON THE OBJECT. The launch point IS that place, and it mirrors when the
bundle mirrors. Grouping on it makes the arms measure alike.

bugs/0779 CORRECTION: the ~400 um both arms then agreed on was NOT blur. A few stray-route rays sat
inside the field groups; without them device 21 measures 0.51 um on both arms. The symmetry fix
stands; the "both arms blurred" conclusion drawn from it did not.

bugs/0779 review: the first version of this guard asserted on SOURCE TEXT, and swapping the two
grouping branches -- which restores the old wrong answer exactly -- still passed every check. These
checks run the REAL _measure_focused_image_plane (display-free, via a stub) on synthetic rays:

  A  a mirror-image two-arm split field with the RAGGED launch and scene_builder's uniform
     field_index, blurred on both arms by the same aberration: the two arms read the same, and
     both read blurred (field_index grouping read one blurred and the other ~0);
  B  a continuous emitter (one launch per ray) is not fragmented into one-ray groups;
  C  the discreteness threshold (>= 4 rays per distinct launch) on the real function;
  D  the older 'target_termination' spelling measures the same.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0778_focus_groups_follow_the_launch
"""

from __future__ import annotations

import types

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import discrete_launch_sources
    from KrakenOS.UI.validate_open3d_0779_stray_routes_are_not_the_image import (
        DELTA,
        FIELD_COUNT,
        RAYS_PER_FIELD,
        _polyline,
        measure,
        per_arm,
        split_field_paths,
    )

    # ---- A: the two arms of a ragged, mirrored split field measure alike --------------------------
    blurred = split_field_paths(tail=20)
    counts: "dict[str, dict[int, int]]" = {}
    for index, path in enumerate(blurred):
        arm = "A" if index < len(blurred) // 2 else "B"
        counts.setdefault(arm, {}).setdefault(int(path.field_index), 0)
        counts[arm][int(path.field_index)] += 1
    ok(counts.get("A") == {0: 361, 1: 361, 2: 361, 3: 20} and counts.get("B") == {3: 341, 4: 361, 5: 361, 6: 40},
       f"A0: the synthetic field_index reproduces the om05a mis-cut ({counts})")
    _, info = measure(blurred)
    arms = per_arm(info)
    a, b = arms.get("Face A field"), arms.get("Face B field")
    if a and b:
        wa, wb = float(a["rms_waist_mm"]), float(b["rms_waist_mm"])
        ok(abs(wa - wb) < 1.0e-9,
           f"A1: the two arms report the same waist ({1000 * wa:.4f} um | {1000 * wb:.4f} um)")
        ok(wa > 0.1 and wb > 0.1,
           "A2: and both report the blur -- field_index grouping read arm B as ~0 um and arm A as ~400 um")
        ok(abs(float(a["offset_mm"]) - float(b["offset_mm"])) < 1.0e-9,
           "A3: and the same image-plane offset")
    else:
        ok(False, f"A1: both arms must be measured (got {list(arms)})")

    # ---- B: a continuous emitter is not fragmented ---------------------------------------------------
    rng = np.random.default_rng(778)
    continuous = []
    for _ in range(400):
        launch = np.array([0.0, rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0)])
        pupil = np.array([50.0, rng.uniform(-4.5, 4.5), rng.uniform(-4.5, 4.5)])
        continuous.append(types.SimpleNamespace(
            points_world=_polyline(launch, pupil, np.array([100.0 + DELTA, 0.0, 0.0])),
            termination_reason="image", source_id="source:random", field_index=0,
            surface_ids=np.asarray((1.0, 25.0)),
        ))
    _, cont = measure(continuous, bands=None)
    ok(isinstance(cont, dict) and cont.get("pooled") is False and int(cont.get("field_count") or 0) == 1,
       f"B1: 400 one-launch-per-ray rays stay ONE measurable group, not 400 unmeasurable ones "
       f"(pooled={None if not isinstance(cont, dict) else cont.get('pooled')}, "
       f"fields={None if not isinstance(cont, dict) else cont.get('field_count')})")

    # ---- C: the threshold, on the real function -------------------------------------------------------
    def items(n_rays, n_points):
        points = [np.array([float(k), 0.0, 0.0]) for k in range(max(n_points, 1))]
        return [("s", points[i % max(n_points, 1)]) for i in range(n_rays)] if n_points else []

    for n_rays, n_points, want, why in (
        (1103, 7, True, "om05a: 1103 landings over 7 launch points"),
        (322, 7, True, "the same bundle after the aperture stop"),
        (400, 400, False, "a true random emitter: one launch per ray"),
        (400, 120, False, "mostly-distinct launches, 3.3 per point"),
        (400, 100, True, "exactly 4 per point"),
        (399, 100, False, "just under 4 per point"),
    ):
        got = discrete_launch_sources(items(n_rays, n_points), source_of=lambda it: it[0],
                                      launch_of=lambda it: it[1]).get("s", False)
        ok(got == want, f"C1[{why}]: {n_rays} rays / {n_points} launches -> discrete={got}")

    # ---- D: the older termination spelling -------------------------------------------------------------
    _, legacy = measure(split_field_paths(tail=20, term="target_termination"))
    la = per_arm(legacy)
    ok(bool(a and b) and len(la) == 2
       and abs(float(la["Face A field"]["rms_waist_mm"]) - float(a["rms_waist_mm"])) < 1.0e-9
       and abs(float(la["Face B field"]["rms_waist_mm"]) - float(b["rms_waist_mm"])) < 1.0e-9,
       "D1: 'target_termination' landings measure exactly like 'image' ones")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0778 focus-groups-follow-the-launch validation PASSED")
        return 0
    print("0778 focus-groups-follow-the-launch validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
