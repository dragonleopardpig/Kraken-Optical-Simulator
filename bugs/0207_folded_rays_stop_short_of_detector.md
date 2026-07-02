# 0207 — BUG: on the folded RA-mirror the reflected rays stop ~desp_z short of the image plane / detector

**Status: RESOLVED. `_reflected_frame_from_interaction_face` (`KrakenOS/UI/nonseq_output_ports.py`)
added the FULL sequential mirror thickness BEYOND the reflection hit, but the hit sits `desp_z`
(12.5 mm on AZ85) past the mirror row's front station — so that pre-hit run was double-counted and
the whole folded lens/camera/detector chain was drawn `desp_z` too far along the folded axis, while
the bugs/0205 reflected display rays (folded about the mirror-face centre) landed at the physically
correct spot. The rays therefore terminated ~12.5 mm SHORT of the drawn image plane. Fix: add only
the REMAINING thickness after the hit (`thickness − pre_hit_run`). `F` stays a rotation, nothing is
mirrored, and the drawn detector now coincides with the reflected rays. Guard
`validate_open3d_ra_mirror_rays_reach_detector.py`, wired as penta phase 185.**

## Flag

`attachment/recorded_bug_repros/flag_20260702_183320_903` on the folded AZ85 ELS-85 layout
(`machine_vision_AZ85_RA_Mirror.py`):

> *"the ray not reaching the image plane or detector."*

The 3D scene shows the beam fold 90° at the RA-mirror and converge along +X, but the drawn ray
bundle terminates with a clear gap before the "Image circle / Sensor" plane on the far right.

## Symptom — measured headlessly

On the as-loaded AZ85 scene the on-axis reflected rays end at **X = 275.321 mm**, while the drawn
image-plane row (row 8) is at **X = 287.821 mm** — a **+12.500 mm = +`desp_z`** longitudinal gap.
It is not just the detector: EVERY folded downstream row is drawn `desp_z` beyond where the rays
cross it (row 2 drawn 40.0 vs ray 27.5; row 7 drawn 137.5 vs ray 125.0; row 8 drawn 287.8 vs ray
275.3). The straight-equivalent image plane is the SAME for both (straight Z = 347.218); only the
FOLD differs, so this is purely a fold-frame inconsistency, not an optics error.

## Root cause — the fold exit frame double-counts the pre-hit run

bugs/0205 folds the display rays by REFLECTING the straight-equivalent bundle about the mirror-face
CENTRE plane (Z = 71.897, the real `/` hypotenuse). That is the physically correct fold: the ray
travels to the hypotenuse, reflects, and continues the REMAINING optical distance — so row 2 lands
27.5 mm past the hypotenuse (= 40 mm element thickness − 12.5 mm from the row station to the
hypotenuse).

But the drawn lens/camera/detector CAD is folded by `F = _optical_axis_fold_world_transform_for_row`,
which seats the downstream chain on the exit frame returned by
`_reflected_frame_from_interaction_face`. That helper computed:

```python
hit    = origin + incoming * distance      # reflection point on the '/' face (the hypotenuse)
center = hit + reflected * thickness        # <-- BUG: full thickness added BEYOND the hit
```

`origin` is the mirror row's front **station** (Z = 59.397); `distance` is the run from the station
forward to the hit (12.5 mm = `desp_z`, since the cube's hypotenuse is at its centre); `thickness`
is the element's **station-to-station** sequential thickness (40 mm). Adding the full 40 mm *beyond*
the hit double-counts the 12.5 mm already spent reaching the hit from the station — total 52.5 mm
from the station instead of 40. So the exit frame (and the whole chain that hangs off it) overshot
by `desp_z`, drawing the detector at 287.821 while the rays land at 275.321.

The gap is `desp_z` (12.5 mm), constant across the whole downstream chain and independent of focus
(snapping the detector moves both by the same amount: 283.077 vs 295.577, still +12.5). It is a
LONGITUDINAL gap along the folded axis — the rays visibly end in mid-air before the detector — which
is why it read as "rays not reaching the detector," not as a blur.

(This is the consequence I mis-called "nearly invisible, deferred" in the bugs/0205 phase-181
retarget. It was neither invisible nor in need of a large overlay-fold change — see the correction
appended to `bugs/0205`.)

## Fix

Add only the thickness that lies BEYOND the reflection hit:

```python
center = hit + reflected * (float(thickness or 0.0) - pre_hit_run)   # pre_hit_run = distance
```

`pre_hit_run` is the station→hit distance (`desp_z` for a centred cube; 0 for a flat mirror whose
face is at the row station, so the fix is a no-op there). This lands the folded exit frame — and the
whole lens/camera/detector chain — exactly on the reflected rays. `F` is unchanged (still a
rotation, so no CAD is mirrored), and the on-axis outgoing arm stays on the folded optical axis
(Z = 71.897), preserving the bugs/0205 on-axis registration (no transverse offset reintroduced).

Measured after the fix: as-loaded the drawn detector X 287.821 → **275.321** (gap +12.500 →
**+0.000**); after snap 295.577 → **283.077** (gap **+0.000**); on-axis Z stays 71.897; every folded
row now coincides with its ray crossing (worst 0.000 mm).

## Blast radius

`_reflected_frame_from_interaction_face` is only reached on the FULL-mirror reflection fallback
(bugs/0185: a promoted right-angle mirror cube with no explicit output port). A display-free sweep
of every mirror layout confirms only `machine_vision_AZ85_RA_Mirror.py` uses
`interaction_reflection_fallback`; the penta-prism cascade and beam-splitter cubes are authored with
explicit output ports (a different code path) and the loaded penta cascade produces no fold
overrides at all — all unaffected. Flat mirrors have `pre_hit_run ≈ 0`, so the fix is inert on them.
The two guards that directly exercise the fallback re-pass:
`validate_open3d_ra_mirror_fold_follows_reflection` and `validate_optical_solid_uncoated_interaction_fold`
(its synthetic case had baked in the overshoot — expected center corrected from `(0,12,0)` to the
physically correct `(0,2,0)`: station −10, thickness 12, fold at 0 → 10 up to the hit, then only 2
across). The three AZ85 folded guards (phases 181/183/192) re-pass and improve: phase 181 now reads
the drawn detector "+0.000 beyond" (was +12.5).

## Verification (display-free)

New guard `KrakenOS/UI/validate_open3d_ra_mirror_rays_reach_detector.py` — as-loaded AND after
snap-to-image-plane, on the live AZ85 editor:

1. the drawn detector X coincides with the on-axis reflected ray endpoint X (gap < 0.05 mm);
2. the sorted drawn outgoing-row X's match the on-axis ray's outgoing vertex X's 1:1 (whole chain
   aligned, not just the detector — worst |gap| < 0.05 mm);
3. the on-axis arm stays on the folded axis Z = 71.897 (bugs/0205 registration preserved).

Proven non-vacuous: the guard FAILs on the pre-fix code (gap +12.500 mm, whole chain off by 12.5),
passes on the fix (+0.000). Wired as `phase_185_folded_rays_reach_detector`; baseline `"185": "pass"`.

Visual proof (eyeballed): `bugs/render_0207_rays_reach_detector.py` renders the X-vs-Z view the user
sees — the ray tips now land on the drawn detector (blue), with the old detector position (red
dashed) 12.5 mm beyond where the rays used to fall short — to
`attachment/bugs_0207_rays_reach_detector.png`.

In-app eyeball still owed (the headless render is a matplotlib projection of the traced bundle, not
the live VTK scene).
