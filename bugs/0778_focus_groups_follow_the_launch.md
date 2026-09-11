# 0778 -- focus groups follow the launch point, so the two arms agree

> "why not symmetry? Why your sweep also show A only kind of assymmetry?"
> "Or do you want to check all the geometry again and find where the assymmetry is?"
> "whatever you find, please make them symmetry."

One arm of the split field reported a ~400 um waist while the other reported sub-micron, on a
bench that is a mirror image about z = -25. Five hypotheses had already died on this
(edge-of-machine, stray rays, lens jammed against the prism, lens-move capped, field off the
sensor), each killed by measurement.

## The hardware is innocent

A six-lens measurement audit (57 agents, each required to measure rather than reason):

| what | result |
|---|---|
| bodies and row placements | symmetric; every pair's midpoint exactly **-25.000** |
| traced bundles | 1103 paths each, identical termination histograms, **max\|mirror(A about z=-25) - B\| = 0.0** |
| landings | exact mirrors |
| optics overall | **symmetric to 35 nm** |

Identical rays were producing two different answers. That can only be the readout.

## The readout

```
launch structure   arm A: 7 points, groups [361,361,361,5,5,5,5]
                   arm B: 7 points, groups [361,361,361,5,5,5,5]   <- identical
field_index        arm A: {0:361, 1:361, 2:361, 3:20}
                   arm B: {3:341, 4:361, 5:361, 6:40}              <- boundaries 20 out of step
```

`field_index` comes from `scene_builder._launch_field_group`, whose fallback is a uniform
`ray_index // ray_count_per_field` division. The launch is **ragged** -- it appends corner probes,
so some fields carry 5 rays and others 361 -- and its own docstring says the recorded mapping
exists precisely because of that. Arm B's boundaries land 20 rays out of step.

The consequence compounds: the mis-cut gave arm B a spurious **0.98 um** "sharp field", which then
disqualified that arm's genuine ~400 um fields through the bugs/0753 `waist <= 10 * sharpest`
test. So the scene reported one arm ruined and the other perfect.

Per-field waists tell the story:

```
by field_index    arm A 401.4 / 413.9 / 401.4 um     arm B    1.0 / 1574 / 1792 um
by launch point   arm A 401.4 / 413.9 / 401.4 um     arm B  401.4 /  413.9 / 401.4 um
```

## The fix

A field point is a PLACE ON THE OBJECT. The launch point IS that place, and it mirrors when the
bundle mirrors; `field_index` is bookkeeping stamped downstream. So the measurement groups on the
launch point whenever the launches are DISCRETE -- averaging at least 4 rays per distinct launch,
the same minimum a waist fit needs. `field_index` remains the fallback for a genuinely continuous
emitter, where launch-point grouping would fragment into one-ray groups and measure nothing.

| case | before (A \| B) | after (A \| B) |
|---|---|---|
| device 15, FOV 24 | 413.89 \| **0.33** | **413.89 \| 413.89** |
| device 15, FOV 26 | 197.88 \| **0.27** | **197.88 \| 197.88** |
| device 15, FOV 28 | 0.27 \| 0.23 | 0.27 \| 0.27 |
| device 21, default | 419.03 \| **0.42** | **419.03 \| 419.03** |
| device 23, default | 0.42 \| 0.42 | 0.42 \| 0.42 |

Every case agrees to 0.01 um or better.

## The correction this forces

**Arm B's sub-micron waists were fiction.** At device 21 BOTH arms are 419 um blurred -- there was
never an arm-A defect to explain, and the "A-only asymmetry" chased across several flags did not
exist. Size/FOV verdicts that leaned on arm B's number must be re-read: where both arms were
reported good (device 23+, FOV 28+) the verdict stands, because both were genuinely good; where
the report was "A bad, B fine", the truth is BOTH bad.

## Correction (bugs/0779)

The conclusion of the section above is wrong. The ~400 um waist both arms agreed on was not blur:
a few stray-route rays -- light that crossed the prism gap into the other arm and came back -- sat
inside the field groups, and one of them dragged a 105-ray field's waist from 2.06 um to 656 um.
With those routes excluded, device 21 measures 0.51 um on both arms and lands inside a pixel, and
device 15 at FOV 24 measures 0.40 um. The symmetry fix stands -- the two arms must be measured
alike -- but "at device 21 BOTH arms are 419 um blurred" does not, and neither does calling arm
B's sub-micron readings fiction: they came from a wrong grouping, yet the true value is sub-micron
too. The size/FOV verdicts that treated ~400 um as blur are wrong in the same way.

The pooled discreteness test was also a defect (an additive random emitter could flip the arms
back to `field_index`); it is now decided per source.

## Guard

`KrakenOS/UI/validate_open3d_0778_focus_groups_follow_the_launch.py`, penta phase **561**.

As first committed, its checks read the method's SOURCE TEXT, and the review of 244c2994 showed
that swapping the two grouping branches -- which restores the old wrong answer exactly -- passed all
of them. It now runs the real `_measure_focused_image_plane` (display-free stub) on a synthetic
mirror-image split field with the ragged launch and scene_builder's uniform `field_index`: the two
arms report the same waist and both report the blur (A); a continuous emitter stays one measurable
group (B); the >= 4 rays-per-launch threshold on the real `discrete_launch_sources` (C); the
legacy termination spelling (D).
