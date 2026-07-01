# 0197 — BUG: on the folded RA-mirror scene the on-axis cone waists at the surrogate lens and DIVERGES to the sensor ("can't focus after the fold")

**Status: RESOLVED. The single-fold path now traces the UNFOLDED flat-plate EQUIVALENT (which
images with the real ideal-lens power) and BENDS the display rays at the mirror with the editor's
own fold transform — so the folded cone lands CONVERGED, exactly on the drawn detector. bugs/0187's
sequential-`Mirror` surrogate reached the sensor STATION but DIVERGING; this is the focus fix on top
of it. A CHAIN of folds keeps the 0187 sequential-`Mirror` trace (which composes); only a SINGLE
fold takes the equivalent+bend path (matching the bugs/0192 single-fold correction scope).**

## Origin

Follow-up on the same folded AZURE ELS-85 layout as bugs/0185–0195
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`). bugs/0187 fix (3) got the rays
to REACH the +X sensor (they previously retroreflected at the first Thin Lens and reached 0 rays).
But the user then observed the cone does not **focus**:

> "the system [is] just exactly the same as unfolded, isn't it? All we need to do is just bend the
> ray at the mirror, split the Object distance into 2, adjust the QE formula accordingly. The same
> goes to [a] mirror between lens and detector."

## Symptom — measured headlessly through the REAL production path

`_build_preview_system_rays_bundle` on the AZ85 scene (detector snapped to the image plane), on-axis
cone transverse RMS vs world X along the folded +X arm (drawn detector at X = 295.577):

| X (mm) | OLD sequential-`Mirror` (0187) | NEW flat-equiv + bend (0197) |
|-------:|-------------------------------:|-----------------------------:|
|  82.0  | **0.392** (waist at surrogate) | 4.601 |
| 120.0  | 1.636 ↑ | 5.308 |
| 160.0  | 2.432 ↑ | 4.099 ↓ |
| 200.0  | 3.228 ↑ | 2.890 ↓ |
| 240.0  | 4.024 ↑ | 1.681 ↓ |
| 270.0  | 4.622 ↑ | 0.774 ↓ |
| 287.6  | 4.972 ↑ | 0.243 ↓ |
| 294.6  | 5.111 ↑ | **0.031** ↓ |

The OLD folded cone reaches its tightest waist (0.39 mm) **at the surrogate lens (X ≈ 82)** and then
**opens monotonically** to 5.11 mm at the detector — i.e. it focuses BEFORE the lens and diverges
after, exactly the user's report. The NEW cone converges monotonically to **0.03 mm at the detector**
(endpoints land at X = 295.577, delta +0.000 from the drawn detector; transverse RMS ≈ 0.8 µm at the
exact endpoint). Both edge fields (±13.7 mm object) also land on X = 295.577 and converge (≈ 8 µm).

## Root cause — the sequential-`Mirror` surrogate does not preserve the ideal-lens focus through the fold

bugs/0187 folds the frame by re-typing the promoted mirror cube as a sequential `Mirror`
(`AxisMove = 2`). A `Mirror` reflection is a det = −1 (improper) frame flip. The downstream elements
are **ideal `Thin Lens` blackboxes** (`Rc = 0`, `Glass = AIR`, `Thin_Lens = 159.49`), whose paraxial
deflection is synthesised by a fake surface normal. Composed through the reflected running frame, the
synthesised deflection no longer carries the cone to the paraxial image — the ray heights at the lens
are folded but the *convergence angle* is not preserved, so the cone waists at the lens and reopens.
Net: 0187 delivered the rays to the sensor STATION but not to a FOCUS.

The key physical fact the fix rests on: **first-order conjugates, magnification and best focus are
INVARIANT under a rigid fold.** The folded system is geometrically identical to its unfolded
flat-plate equivalent (only row 1 — the promoted BK7 mirror — bends the straight +Z axis onto +X; the
prescription is otherwise straight). So the *correct* focused cone is simply the unfolded system's
cone, rotated onto the folded branch.

## Fix — trace the flat equivalent, then BEND the display rays with the editor's own fold transform

In `services/three_d_scene_tools.py` `_build_preview_system_rays_bundle`, when the folded-sequential
path engages AND there is exactly ONE fold:

1. **Trace the UNFOLDED equivalent.** `_folded_optical_solid_straight_equivalent_rows()` flattens the
   promoted mirror cube back to its straight-axis flat-plate equivalent; a sequential system is built
   from it (`build=0`, no output-port meshing) and traced. This images to a real focus because the
   ideal Thin Lenses see a normal, un-reflected frame.
2. **Bend the display rays at the mirror.** `_fold_straight_equivalent_display_rays(scene_bundle, F)`
   carries every ray vertex at/after the mirror's straight-axis station (`z ≥ station_z`, along +Z)
   through `F = _optical_axis_fold_world_transform_for_row(image_row)` — the **same rigid rotation the
   editor already uses to seat the folded lens/detector overlays** (`F(v) = C + R·(v − S)`, proper
   rotation, det = +1). Because it is the editor's own transform, the bent cone lands **exactly** on
   the drawn detector; a hand-rolled reflection across the mirror centre instead lands 12.5 mm short
   (= the mirror's `desp_z`).
3. **Correct the meridional flip off-axis.** The existing bugs/0192
   `_apply_folded_mirror_reflection_correction` still runs (no-op on-axis; it re-seats the off-axis
   meridional sense onto the real hypotenuse).

The returned `rays` raykeeper now holds the UNFOLDED equivalent (the display bundle carries the folded
geometry). The 3D ray inspector reads `_last_scene_bundle` first, so it shows the folded cone; the
`last_rays` consumers that matter (2D layout `plot_refresh`, detector analysis) re-trace or rebuild
their own bundle, and the first-order optics (cardinal points) are fold-invariant, so the unfolded
`rays` do not regress them.

### Scope / fallback

- **Single fold only.** The equivalent+bend path is gated to exactly one synthesised `Mirror`
  (matching the bugs/0192 single-fold correction). A CHAIN of folds falls back to the bugs/0187
  sequential-`Mirror` trace, which composes an arbitrary number of folds natively.
- Beam splitters and refractive promoted solids never reach this path — the gate
  `scene_nonseq_trigger_is_only_promoted_full_mirrors` already excludes them (they trace through the
  real mesh).

## Verification (done)

- **`KrakenOS/UI/validate_open3d_ra_mirror_folded_cone_converges.py`** (new, standalone, display-free;
  run `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_cone_converges`):
  drives the REAL `_build_preview_system_rays_bundle` on the AZ85 scene (detector snapped to the image
  plane) and asserts (1) the folded-sequential path engaged; (2) the on-axis cone transverse RMS is
  strictly decreasing down the folded +X arm (120 → detector); (3) the on-axis endpoints land on the
  drawn detector (|ΔX| < 0.05 mm) and converge (endpoint RMS < 0.1 mm); (4) both ±13.7 mm edge fields
  also land on the drawn detector and converge.
- **`KrakenOS/UI/validate_open3d_ra_mirror_folded_sequential_trace.py`** (the bugs/0187 guard) updated:
  its end-to-end check now asserts the folded DISPLAY bundle CONVERGES on the +X sensor (endpoint
  transverse RMS < 1 mm) instead of the raw raykeeper reaching the sensor station — the raw rays now
  hold the unfolded equivalent. Its pure-synthesiser tests (single fold, double-fold chain composes,
  non-folded untouched) are unchanged.

Both guards are standalone (NOT penta phases) — no penta phase exercises a promoted mirror + ideal
Thin-Lens conjugate. In-app eyeball still owed (headless cannot drive the VTK inspector).

## Follow-ups (deferred)

- **Quick Estimation across the fold** ("split the object distance into 2, adjust the QE formula") —
  the QE overlay still assumes a single straight axis (bugs/0187 known-limitation; candidate-0196
  diagonal skew). Fold the QE onto the per-segment running frame next.
- **The ~1.19× vs 1× FOV** layout-conjugate question is separate and remains deferred.
