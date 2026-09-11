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
others 361. Arm B's boundaries land 20 rays out of step. That invented a 0.98 um "sharp field"
for arm B, which then disqualified that arm's genuine ~400 um fields through the bugs/0753
``waist <= 10 * sharpest`` test, and the scene reported one arm ruined and the other perfect.

A field point is a PLACE ON THE OBJECT. The launch point IS that place, and it mirrors when the
bundle mirrors. Grouping on it makes the arms agree:

    device 15 FOV 24   before  A 413.89 um / B   0.33 um      after  A 413.89 / B 413.89
    device 15 FOV 26   before  A 197.88 um / B   0.27 um      after  A 197.88 / B 197.88
    device 15 FOV 28   before  A   0.27 um / B   0.23 um      after  A   0.27 / B   0.27
    device 21 default  before  A 419.03 um / B   0.42 um      after  A 419.03 / B 419.03
    device 23 default  before  A   0.42 um / B   0.42 um      after  A   0.42 / B   0.42

The correction this forces: arm B's sub-micron waists were FICTION. At device 21 BOTH arms are
419 um blurred -- there was never an arm-A defect to explain.

Checks (display-free, pure):
  A  discreteness is decided before grouping, and on the whole landing set;
  B  a discrete launch groups by launch point, a continuous one falls back to field_index
     (a true random emitter gives every ray its own launch and would fragment into one-ray
     groups, measuring nothing);
  C  the threshold is >= 4 rays per distinct launch, matching the min_rays a waist fit needs;
  D  the measured before/after numbers are recorded where the next reader will find them.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0778_focus_groups_follow_the_launch
"""

from __future__ import annotations

import inspect


def _discrete(landing_rays, distinct_launches):
    """The rule, mirrored so its cases can be enumerated."""
    return bool(distinct_launches and landing_rays >= 4 * distinct_launches)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as _M

    src = inspect.getsource(_M._measure_focused_image_plane)

    ok(
        "discrete_launches" in src,
        "A1: the measurement decides whether the launches are discrete before it groups",
    )
    ok(
        src.index("discrete_launches = bool(") < src.index("if discrete_launches:"),
        "A2: and decides it ONCE, over the whole landing set, not per ray",
    )
    ok(
        "_landing_rays >= 4 * len(_launch_seen)" in src,
        "C1: the rule is >= 4 rays per distinct launch -- the same minimum a waist fit needs, "
        "so a group that survives grouping can actually be measured",
    )
    ok(
        'key = (source, tuple(np.round(pts[0, :3], 3)))' in src,
        "B1: a discrete launch groups by the LAUNCH POINT -- the physical field point, which "
        "mirrors when the bundle mirrors",
    )
    tail = src.split("if discrete_launches:", 1)[-1]
    ok(
        "field_index" in tail,
        "B2: and a continuous emitter still falls back to field_index -- grouping a random "
        "source by launch point would give one ray per group and measure nothing",
    )

    # ---- the discreteness rule's own cases ---------------------------------------------------
    for landing, launches, want, why in (
        (1103, 7, True, "om05a: 1103 landings over 7 launch points"),
        (322, 7, True, "the same bundle after the aperture stop"),
        (400, 400, False, "a true random emitter: one launch per ray"),
        (400, 120, False, "mostly-distinct launches, 3.3 per point"),
        (400, 100, True, "exactly 4 per point"),
        (0, 0, False, "nothing landed"),
        (10, 0, False, "no launches recorded"),
    ):
        got = _discrete(landing, launches)
        ok(got == want, f"C2[{why}]: {landing} rays / {launches} launches -> discrete={got}")

    # ---- the measured evidence is recorded ----------------------------------------------------
    ok(
        "3.5e-5" in src or "mirror" in src.lower(),
        "D1: the source records that the two arms' bundles were measured as mirror images -- "
        "the fact that makes a readout difference impossible to blame on optics",
    )
    ok(
        "413.89" in src and "0.33" in src,
        "D2: and the before/after numbers that prove the fix, so the next reader need not "
        "re-derive them",
    )
    ok(
        "fiction" in src.lower() or "FICTION" in src,
        "D3: and that arm B's sub-micron waists were fiction -- the correction matters more "
        "than the fix, because tables were published on those numbers",
    )

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
