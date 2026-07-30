# 0486 — the fold point left the axis feeding it, because a station is not that axis

**Flag `flag_20260730_160140`** (recording `recording_20260730_160336`, build `8f3a9b42`):

> changed to FOV 30x30, RA mirror shifted, not centered to optical axis, the fold axis also slanted.

First fix in this family pinned by a **structural** invariant rather than a scene-specific number:
bugs/0485's CONTINUITY rule — *a child segment's origin lies on its parent, because a beam cannot
leave an axis it never met.*

## Cause

bugs/0468 keeps the sensor off the fold mirror by **sliding the mirror** rather than refusing, and it
applied that slide with `rows[near_gap_row].thickness += -deficit`.

On a **frozen** fold a station thickness is not a distance along the mirror's incoming leg. Here the
leg runs **+x** while a thickness moves the row in **z**, so the slide displaced the mirror
*perpendicular to its own beam* by exactly the deficit.

Stepping the solve on `attachment/machine_vision_AZ85_RA_Mirror_BS.py` at 30 × 30:

    start                                   off-parent 0.0000   mirror (229.930, 0, 53.803)
    ENTRY apply_image_distance_frozen_aware off-parent 6.1200   mirror (229.930, 0, 84.576)
                                                                BS coating (0, 0, 90.696)

The object-gap write shifted every station by +36.892, taking the BS coating (the parent leg) to
z = 90.696 — but the mirror reached only 84.576, because the resolver had already shortened row 6 by
the 6.12 mm deficit. `90.696 − 84.576 = 6.120`: the fold point hung that far below the beam feeding
it, and the emitted leg then drew slanted (**3.39°** measured). `c_m` equalled row 7's
`station + desp` at every step, confirming the mirror is station-derived and the station is what
moved it sideways.

Pre-existing, and not caused by bugs/0482/0484: measured −6.12 mm before them and −5.33 mm after.
(My first attribution blamed those fixes and was wrong — it normalised against the as-loaded axis z
while the object-side hold moves where that axis is.)

## Fix

Route the resolver's slide through `_apply_folded_image_split`, which slides along `in_dir` and
re-seats the sensor and camera on the exit leg (bugs/0447). That writer is exactly why the **manual**
leg constraint was always clean — driven by hand it moves the mirror `[−20, 0, 0]`, **0.0° off
axis**, z untouched. The raw thickness write is kept for straight/unfrozen scenes, where a station
*is* along the beam.

Also, on the user's call, `IMAGE_LEG_ASSEMBLY_MARGIN_MM` goes **1.0 → 5.0 mm**. At 1 mm a 40 × 40
field left the camera body's bounding box only 3.04 mm from the mirror's — genuinely clear, and
`camera_body_collisions()` agreed, but too tight to read as safe (*"+3.04 … should crash already"*).
It is the single knob for how much daylight a large field keeps.

## Verification

Real scene, camera re-seated after each solve:

| field | off-parent | sec 1 | sec 2 | sec 3 | sec 4 | cam→mirror | collisions |
|---|---|---|---|---|---|---|---|
| 23×23 | **0.0000** | 53.803 | 82.727 | 96.884 | 45.114 | +21.13 | none |
| 30×30 | **0.0000** | 53.803 | 108.552 | 86.950 | 35.180 | +11.20 | none |
| 35×35 | **0.0000** | 53.803 | 126.998 | 82.287 | 30.517 | +6.54 | none |
| 40×40 | **0.0000** | 53.803 | 145.444 | 76.830 | 28.980 | **+5.00** | none |

The mirror now moves only in **x** across the whole sweep, never in z, and `out_dir` is exactly
(0, 0, −1) — perpendicular to the incoming +x leg, so the slant is gone. The 40 × 40 row is where the
floor binds, and it tracks the 5 mm margin exactly.

`KrakenOS/UI/validate_open3d_0486_fold_point_stays_on_its_axis.py`, penta **phase 392**,
display-free, 9 checks: the invariant itself (A1 a fold point on its parent is clean, A2 the reported
state IS a 5.33 mm CONTINUITY violation), the routing (B1 a frozen scene slides through the writer at
`pre_near + delta`, B2 the station thickness is NOT written, B3 an unfrozen scene keeps it), and the
wiring plus the margin (C1–C4).

Guard family re-run: 0468, 0470, 0471, 0478, 0482, 0484, 0448, folded image-mesh reseat, folded
duplicate image plane — all PASS. Gate `--phases 251,380,381,382,386,387,388,389,390,391,392` = 10
pass, 1 known-failing (251, in baseline). 54/54 pytest.

## One guard fixture re-scaled, deliberately

The margin change moved bugs/0482's clamp fixture into the *impossible* region: its "tight" pair
(total 60 → 40) put `near_min + far_floor = 41.48` above the 40 mm total, so the "cannot clear"
branch fired first and the clamp under test never ran. The totals are re-scaled (80 → 60); the
assertion is unchanged and still reads `total − floor` computed, not a literal.
