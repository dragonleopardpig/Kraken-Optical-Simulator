# 0230 — periscope (two adjacent RA mirrors) crashed the trace: `int has no ray_trace`

**Status: CRASH FIXED. Promoting a 2nd RA mirror adjacent to the 1st (a periscope) no longer
crashes the preview/plot trace. Rays now trace and fold through BOTH mirrors. AZ85 fully
preserved, all folded guards green. KNOWN FOLLOW-UP: the periscope's detector/overlay branch
(pose-override) and the folded ray branch disagree in sign — see "Remaining" below.**

## The report

flag_20260705_143355 (Pyrite 85, "after promoted the 2nd RA mirror, seems got error, no 3rd
axis created, detector not shifting, looks like the 2nd RA mirror is not there"). The full
recording carried the actual exception:

```
3D inspector refresh error: non-sequential surface 2: int has no ray_trace or extract_surface method.
...
KrakenOS.MeshRayTrace.MeshRayTraceError: non-sequential surface 2: int has no ray_trace ...
```

The user then saved the layout (`attachment/machine_vision_Pyrite85_RA_Mirror.py`): two promoted
RA-mirror solids at **adjacent rows 1 and 2**, centres (0,0,78) and (0,188,78) — a periscope
(fold up, run across, fold back down).

## Why it is NOT AZ85 (which works after 0185-0228)

AZ85's two mirrors sit at rows 1 and **8** with the whole lens group between them; its second
fold turns the axis 90° (a genuinely *rotating* fold). The Pyrite mirrors are **adjacent** and
compose to a **periscope**: +Z → +Y → +Z (or −Z), a **net-IDENTITY rotation with a lateral
offset**. Two independent fold subsystems were built for the *rotating* case and both miss the
periscope:

1. **The sequential-Mirror surrogate** (`fold_promoted_mirror_specs_to_sequential`,
   bugs/0187) rotation-folds the running frame. After mirror 1 its running beam points **−Y**,
   but the real mirror 2 sits at **+Y** — so its along-leg gap is negative and `_solve_mirror_tilt`
   finds no single-axis tilt (`best_cos = −2.0`). The mirror is LEFT as a promoted mesh solid.
2. **The flat-plate straight-equivalent path** (`_folded_optical_solid_straight_equivalent_rows`,
   bugs/0208 — the GENERAL path that flattens every mirror and reflects the display rays about
   each plane) was gated by `has_rotating_fold`, which only checks for a non-identity **rotation**.
   The periscope's per-row transforms are identity-rotation + translation, so the gate read the
   scene as unfolded and returned `None`.

With (2) bailing, the trace fell through to (1); the leftover mesh solid was fed into that
path's `build=0` (dummy) system, whose `EEE` is a list of int `0`s (no meshes). The
non-sequential tracer read `EEE[2]` (an int) for the on-beam mirror-2 solid →
`int has no ray_trace`. (Mirror 1 converted fine, so surface 1 never hit the dummy path — hence
the crash was specifically at surface **2**.)

## Root cause

`has_rotating_fold` recognised only a rotating fold, so a **periscope** (net-identity rotation,
lateral offset) was not routed to the general flat-plate path and fell through to the
single-fold sequential surrogate, which cannot compose the 2nd free-placed fold and left it as
an un-traceable dummy-built mesh solid.

## The fix

`_folded_optical_solid_straight_equivalent_rows` now treats a **DISPLACING** fold as a fold too:
the per-row transform triggers the flat-plate equivalent when its rotation is non-identity **OR**
its translation is non-zero (`bugs/0230`, `paraxial_tools.py`). The periscope now routes to the
general path, which flattens BOTH mirrors to zero-power plates and traces the unfolded straight
system with `build=0` — **no mesh solid, no crash** — then reflects the display rays about every
mirror plane. AZ85's rotating fold already tripped the rotation branch, so it is byte-unchanged;
an unfolded scene has no pose overrides, so it is untouched.

## Verification

`validate_open3d_periscope_fold_crash` (display-free):
- the translating-fold gate recognises a periscope transform (identity R + offset) that the
  old rotation-only gate rejected, and still rejects a true no-op (identity, zero offset);
- the two-mirror AZ85 rotating fold still yields flat-plate equivalent rows (no regression) and
  its preview still folds to the known detector (~266.9, 0, 71.9);
- source wiring for the `displacing` branch.
Regression: `validate_open3d_offbeam_promoted_mirror_inert` (0224/0226),
`validate_open3d_2d_layout_matches_3d_focus` (0227),
`validate_open3d_ra_mirror_retroreflected_ray_dive`,
`validate_open3d_second_mirror_same_part_mirror_carryover` all green.

## Remaining (separate follow-up — NOT the crash)

With the crash gone, the periscope traces 3249 rays that converge on the physically-correct
−Z branch (mirror 2's face normal (0,−0.707,−0.707) folds +Y→−Z, endpoints at z≈−92), but the
**pose-override walk** (`build_optical_solid_output_port_pose_overrides`, nonseq_output_ports)
seats the detector/lens/camera overlays on the **+Z** branch (z≈436) — the two disagree in the
fold *sign* for the second mirror (an output-port inference issue, cf. bug 0084's exit-face
priority). So the fold now appears and nothing crashes, but the drawn sensor and the ray waist
are on opposite branches until the pose-override's mirror-2 exit direction is reconciled with
the face-normal reflection. Tracked as the periscope focus/branch-alignment follow-up.
