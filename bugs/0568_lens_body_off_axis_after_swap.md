# 0568 — a swapped lens STEP body sits OFF the optical axis

**Flag** `attachment/recorded_bug_repros/flag_20260805_203837_379` (build 1d1f21a7,
`machine_vision_AZ85_RA_Mirror_BS`):

> swap a lens, Lens STEP is not centered to optical axis, I think because of the screw.

**Follow-up from the user, same session** (the feature half of this bug):

> I found right click center the STEP require clicking edge then optical axis, this is good for
> other step, not good to adjust the center of Lens body vs surrogate as picking optical axis
> will shift the lens body along optical axis, separating the already positioned surrogate.
> Perhaps add an option "Center lens body to surrogate", user click an edge and the lens
> centered without shifting along the optical axis.

## Measured

The flag records the lens overlay's actor bounds; the surrogate's own rows are on the
BS-reflect leg (`axis:global:split`, +x at y = 0, z = 55.359):

| | world x | world y | world z |
|---|---|---|---|
| lens STEP bounds | 76.574 … 124.374 | −24.248 … 24.250 | 23.855 … 75.471 |
| barrel (CAD cylinder) axis | — | 0.000 | **48.104** |
| surrogate datum rows | 78.085 … 117.604 | 0.000 | **55.359** |

**The barrel's optical axis is 7.255 mm off the leg.** (The *bbox* centre is 5.696 mm off — the
extra 1.559 mm is exactly half the 3.117 mm screw boss the user suspected, so the eye and the
CAD axis disagree by that much.) `bugs/diag_0568_lens_step_axis_centre.py` shows the PYRITE
barrel's OCC extraction is *clean*: 472 concentric cylinders, perp spread 0.000 mm, anchor
exactly on the barrel — the bugs/0077 centring is not what failed.

## Root cause — the preserved placement NUMBERS are not a preserved SEAT

bugs/0381 deliberately preserves the overlay's rotation / axis offset / placement offset across
a swap ("a swap changes the lens, not where the user put it"). But those numbers only mean what
they meant **for the body they were set for**. On this 0433-frozen scene the lens is turned onto
the leg with `lens_step_rotation_y_deg = 270`, and then:

* `_cad_mesh_aligned_to_optical_axis` pivots its x/y rotations about **the mesh's own bounding
  box** (`pivot_x`, `pivot_z`) — deliberately, so a flip turns the body in place. After a 270°
  rotation the body's transverse seat is therefore
  `pivot_z − pivot_x` = (axial half-extent) − (transverse bbox midpoint), **both properties of
  the body**. ELS-85 → PYRITE moves that constant by **5.111 mm** (2.55 mm of axial length,
  2.56 mm of bbox midpoint — the mount/screw asymmetry).
* `target_front_z` (the axial datum pin) is added to the aligned **+Z** *after* those rotations,
  so a 270° rotation redirects the axial pin **sideways**. The swapped block's front-datum
  station moved the body a further **3.220 mm**.
* a small `placement_z` change (+1.076 mm) came from the leg itself moving.

−5.111 − 3.220 + 1.076 = **−7.255 mm**, exactly the measured miss. `bugs/diag_0568_swap_overlay_seat.py`
replays the shipped alignment with the flag's own numbers and reproduces the flag's recorded
lens bounds to **0.0004 mm**, so this decomposition is measured, not modelled.

The same arithmetic also explains why the ELS-85 was already 2.144 mm off before this swap:
the drift accumulates one swap at a time.

## Fix — preserve the SEAT, not the numbers

`center_lens_body_on_surrogate_axis` (`services/scene_placement_commands.py`):

1. `_lens_step_overlay_axis_world_line` (`services/layout_polyline_display.py`) **measures**
   where the body's optical axis actually is: two points that lie ON the CAD cylinder axis are
   pushed through the *very same alignment the display uses* (they sit at 25 % / 75 % of the
   axial span, strictly inside every bbox/extreme/centroid the alignment reads, so they cannot
   perturb the drawn body). A probe that re-derived the transform by hand would drift from what
   is on screen the first time either changed — so the alignment inputs now live in ONE place,
   `_lens_step_alignment_params`, shared by the builder and the probe.
2. `_lens_surrogate_optical_axis_line` reads the surrogate's own axis — the line through the
   Front/Rear Optical Vertex Datums — through the ONE row-pose resolver (bugs/0557), so it is
   the real leg on a frozen scene and the straight-equivalent on a sequential one.
3. The placement offset is corrected by the **transverse component only** — the component along
   the surrogate axis is dropped, so the axial registration (the datum pin, or wherever the user
   put the body) is untouched. That is literally the user's "without shifting along the optical
   axis", and it is what makes this safe to run automatically.
4. The glue REFERENCE + its datum anchor are re-recorded at the corrected placement, or one
   "Glue STEP to Surrogate" click would restore the off-axis placement (bugs/0497 / bugs/0503).
5. The result is **re-measured** with the same probe, not assumed from the algebra, and logged.

Wired in two places:

* **the swap** — after the rows settle (`_swap_reseat_preserved_rows`), inside the same history
  capture; the status line says how far it had to move the body, so a swap that shifts the
  overlay is visible rather than silent.
* **the right-click menu the user asked for** — "Center Lens Body -> Surrogate Axis (no axial
  shift)" on a lens STEP face, next to the existing "Center Picked Face -> Optical Axis" (which
  moves all three axes and so slides the barrel off its surrogate). It needs **no second pick**:
  the CAD barrel axis says where the optics are. A picked face centre is the fallback for a body
  whose cylinder axis cannot be extracted.

**Refuses rather than guesses**: with no CAD cylinder axis (or with a resize that has taken the
mesh out of the STEP-native frame the axis point lives in) nothing is moved.

**Cannot disturb a straight scene**: on an unrotated overlay both bodies are already anchored on
their cylinder axis by bugs/0077, so the correction is exactly zero (guard A6).

Diagnostic: the flag now records `step_overlay_poses.lens.optical_axis_offset_mm` (and the
body-vs-axis tilt), so "the lens STEP is not centered" is a number in the next flag instead of an
eyeball judgement.

## Guard — phase 443 `validate_open3d_0568_lens_body_centred_on_axis`

* **A (synthetic, always runs)**: two barrels of different length, each with a one-sided screw
  boss. Fail-before (> 1 mm off), fix (→ 0), **no axial shift**, the boss cannot pull it off, the
  glue reference follows, an undecidable body moves nothing, the picked-feature fallback works,
  and the whole thing is a NO-OP on an unrotated scene.
* **C (real swap)**: drives the shipped `swap_imaging_lens_from_folder` (only file I/O stubbed)
  and checks the body comes out on the axis — a command nobody calls fixes nothing.
* **B (real fixtures, skip-if-absent)**: the flag's own numbers, ELS-85 → PYRITE. Reproduces the
  flag's recorded bounds to 0.0004 mm, then 7.254 mm → 0 with the along-axis position unchanged.

## Drive-by: two lens-STEP guards that had gone red on a clean tree

Both were **pre-existing** (confirmed with the work stashed out), and neither was a code bug:

* **phase 315 `validate_open3d_lens_step_glass_recenter`** asserted the builder's SOURCE
  (`"target_front_z=self._lens_step_display_front_z()" in getsource(...)`), so the refactor in
  step 1 above read as a regression. Rewritten to assert the VALUES the builder feeds the
  alignment, plus a non-vacuity check that the flip shift is non-zero for a flipped asymmetric
  barrel (the bugs/0531 lesson: assert behaviour, not implementation).
* **phase 402 `validate_open3d_0497_glue_restores_the_recorded_placement` — STILL RED, not
  touched here.** Same family (it drives the same live scene) but not a one-liner, so it is left
  for its own turn rather than half-fixed. Diagnosis for whoever picks it up: at HEAD it fails
  B2 with residual **13.567 mm**, which is just the live file's stored glue reference being the
  placement from *before* the user's last lens move (the scene is simply not in a glued state).
  Recording the reference at load — the normalisation that fixed 407 — changes the residual to
  **exactly 25.000 mm = the x component of the test's own `drag1 = (25, 0, 18)`**, i.e. with a
  correct reference the glue restores the body to where it was *before* the drag while the test
  expects `base + leg·(drag·leg)`. So the open question is whether the bugs/0499 axial leg-slide
  carry still fires on this scene (it has since become 0433-FROZEN) or whether the expectation
  is stale — a real behavioural question about 0499/0503, not a fixture tweak.
* **phase 407 `validate_open3d_0500_flip_attaches_optics`** drives the user's LIVE scene file
  and had hardcoded its datum rows (1 and 6 — the datums are now 1 and 5) and assumed the barrel
  is saved unflipped and glued. It now reads the datum rows through `_lens_datum_row_index`,
  normalises the orientation, and starts from a glued state. Its central assertion also became
  stronger: instead of "the overhangs swap" (true only when the glass centre happens to sit on
  the datum midpoint — 0.203 mm out on the live scene, which read as a 0.406 mm flip error that
  is not one) it now asserts the flip is a **pure mirroring about one point** and that the point
  **is the glass-span centre**, which is the actual bugs/0500 contract and holds for any
  placement.
