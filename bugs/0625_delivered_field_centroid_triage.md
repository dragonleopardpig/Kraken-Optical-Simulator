# 0625 — the delivered field is DECENTRED; 2 field spots landed off-glass (FIXED)

User reports (2026-08-15/16/17): "image side still missing 2 sampled rays, only shows 7"
+ "the object side is missing 2 launched rays" + flag_20260817_080138 "object side still
mising 2 launch rays". After 0624 (blackbox extended apertures) the pencils all launch
and refract — but 7 of 9 spots arrive.

## Measured (solved Apo75, 55×55, c = 0.906, build 995134a7)

Per-launch-column census (grid columns x = −27.6 / 0 / +27.6, 186 rays each):

- **x = −27.6: ALL 38 missed_image; only 21 arrivals** — the missing spots are BOTH
  on the minus-fold-axis side.
- x = 0: 61 arrivals, 0 missed. x = +27.6: 52 arrivals, 0 missed.

Consistent with the long-standing landing asymmetry (arrival clusters at
u ∈ {−10.6, −0.2, +6.5} instead of ±10.4): the real folded machine images the field
OFF-CENTRE along the fold axis. The bugs/0591 correction c fixes the delivered
SCALE; nothing fixed the delivered CENTRE, so a launch grid centred on the axis
mapped to a footprint shifted off the 23×23 glass on one side.

## Fix — learn the delivered field CENTRE (the 0591 pattern, sign-safe)

`_learn_folded_field_center(object_semi)` in quick_estimation.py, called from BOTH
refinement exits of `_refine_folded_field_fill` (i.e. whenever the scale correction is
verified-learned). Rather than converting one centroid through the magnification —
whose SIGN convention on a frozen fold is exactly what bugs/0612 says not to trust —
it measures the full field→landing map with real rays:

1. Three probes through the world-order instrument (on-axis + two axis offsets of
   `delta = max(0.1·|object_semi|, 1 mm)`) give the centroid Jacobian `J`.
2. `shift = −J⁻¹ · C0`; rejected if non-finite or larger than the object semi-field.
3. A FOURTH probe at the shift must at least HALVE the centroid norm before anything
   is stored (bugs/0613 verified trust — an unverified one-shot never steers).
4. Stored as `editor._folded_field_center_state = (sx, sy)` — world X/Y offsets at
   the object plane, the world-order launcher's own field coordinates. A machine
   already centred (<0.05 mm) stores the explicit (0, 0).

Machine state lifecycle exactly like `_folded_m_correction_state`: cleared on
`load_layout_by_name`, `open_layout`, the zemax loader (both previously cleared
NEITHER correction — the bugs/0563 two-loader gap, fixed here), lens swap, camera
import, and both unmeasurable refinement exits.

### Loads must re-measure, not just clear (flag_20260817_124307)

The user's actual workflow never solves: they LOAD the saved scene and look. The load
cleared the learned state and nothing re-measured it, so the readout showed the raw
first order (FOV 28.2×28.2 instead of the solved 55) and the grid stayed decentred.
Extended the bugs/0608 doctrine (a swap RE-MEASURES) to every full-scene loader:
`load_layout_by_name` and `open_layout` call `_relearn_folded_m_correction_after_swap`
after the scene is complete (post cache-regen), which now also learns the centre.
Sequential scenes no-op on the world-placed-chain early-out. Measured load cost on the
Apo75: 68 s total (solids included).

### The SIGN trap: pair convention vs world convention

The learned centre is a WORLD offset at the object plane (the world-order instrument:
`o_x = origin + field_x`). But the grid pairs feed PupilCalc-style launchers whose
`height` convention launches from MINUS the field value (PupilTool: `shiftX = -FieldX`;
the world launcher: `origin = anchor - field`; the geometric fallback likewise). A
mirrored SYMMETRIC grid is indistinguishable from the original — the latent mirror was
invisible until the learned shift broke the symmetry. Measured (probe v1): the
un-negated shift moved the pencils AWAY from the delivered field; the mirrored edge
column and two corner probes died (4 dead pencils). The world shift therefore enters
the PAIR values NEGATED.

Consumers (the delivered-readers side of the 0602 doctrine):
- `_sample_imaging_field_grid_pairs`: the linspace grids offset by −shift (pair
  convention); a single-field launch launches AT the centre; unlearned scenes are
  byte-identical symmetric.
- The bugs/0522 FOV-corner probes: corners of the SAME shifted rectangle (unshifted
  corners double-launched beside the shifted grid — the four extra 10-ray pencils in
  the flag_124307 census, 598 = 9×62 + 4×10).
- The drawn object-FOV square (detector-coverage overlay): `obj_pt` shifts by the
  learned state in WORLD frame (+shift), agreeing with where the pencils now land.

## Verified (diag_0625_field_center_verify.py — the user's exact workflow: load, NO solve)

- Load learns correction 0.8165 + centre (0.43, 0.0) in 64 s (debug: "axial centroid
  [-0.35, 0] -> [-0.0, 0]").
- Instrument: all 9 grid pairs land 66/66 rays on the glass; centroids EXACTLY at the
  sensor corners/edges (±11.51 on the 11.52 half-side), fully symmetric.
- Display bundle: 558 paths (the 4 duplicate corner-probe pencils deduped away),
  **zero missed_image** (flag: 41), **166 arrivals** (flag: 133), all 9 pencils
  arrive — no missing field spot. Visual: bugs/_0625_object_side_after_load.png.

Guard: phase 469 (`validate_open3d_0625_delivered_field_center`) — learner contract
(both exits learn, both unmeasurable exits clear), Jacobian recovery on a synthetic
linear machine, bugs/0613 refusal on an unverifiable shift, grid recentre/neutrality,
overlay contract, loader invalidation (incl. open_layout + zemax).
