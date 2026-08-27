# 0647 — "standoff 53.47+67.32 vs bench ~130": the WORLD is right; the readouts mix three reference planes (ANALYSIS)

**Flag:** `flag_20260825_113300_911` — "can double check FOV 20x20, standoff=53.47+67.32?
Actual testing is around 130mm." Scene `attachment/machine_vision_ELS85.py` (re-saved by the
user at 11:23, obj row t=108.38), build 4f5703cf.

## Verdict: the model MATCHES the bench — the numbers on screen measure different planes

Datasheet (`attachment/Lens/ELS-85-4.5V16K/ELS-85 4.5V16K_specification.pdf`): EFL 85,
suitable distance **225 / 142 / 99 mm at 0.5× / 1.0× / 2.0×**. Fitting WD(m) = f(1+1/m) − off
to the vendor's own three points gives off ≈ 28.8 ± 1 → the vendor's WD reference plane sits
**28.8 mm ahead of the front principal = 4.8 mm behind the scene's Front Optical Vertex
Datum** (and ~8.7 mm behind the STEP housing front face at x=67.60; datum x=71.45).

Measured on the flagged state (world bounds from the flag + headless probes):

| quantity | value |
|---|---|
| world object→datum (fold 54.28 + datum 71.45) | **125.73 mm** |
| datasheet law at the datum, m=1.152 | 125.3 mm (Δ 0.4) |
| world object→vendor-reference (datum+4.8) | **130.5 mm ≈ the bench's ~130** ✓ |
| user's markers 53.47+67.32 = object→STEP housing face | 120.8 (their reference, 8.7 mm outside the vendor plane) |
| full-grid measured delivered m at this state | **1.1508** = first-order at the WORLD distance (1.148, Δ0.25%) |

So the physical standoff the scene ACTUALLY models agrees with the vendor law and the bench
within ~0.5 mm. The user's on-screen markers measured to the STEP front housing face — a
legitimate but different plane than the vendor's WD convention.

## The real defect found underneath (open)

The PRESCRIPTION object row says t=108.38 while the WORLD object→datum is 125.73 — a
**17.35 mm frame split on the object leg** of this frozen display-folded scene. Consequences:

- the solve message quotes "object->lens 108.4 mm" — prescription-frame, 17 mm short of
  the world truth a user can measure;
- the delivered-m "correction" (0.772 here) is NOT optics: it exactly equals
  m_raw(world)/m_raw(prescription) = 1.148/1.49 — the 0602/0621 machinery silently absorbs
  the frame split as a magnification fudge, so it drifts whenever the split changes
  (0.9233 on yesterday's geometry) and degrades the further the two frames diverge.
- repeated solves are idempotent (probed 3×: obj 108.38↔108.41, corr 0.7721–0.7726,
  delivered VERIFIED each time) — no drift bug; the state is self-consistent.

Candidate fixes (not yet built): quote the WORLD object distance (and a vendor-convention
"WD" readout) in solve messages/HUD; root-cause the object-leg t↔world split so the
correction goes back to measuring OPTICS only.

Probes: scratchpad check_els85_wd/wd2/drift/mapping (session 2026-08-25); the mapping probe
fits launch→landing spans from the full traced grid — no chief ruler, no learned state.

## CORRECTION + SHIPPED FIX (same day, after the user pushed back)

The user: "We can only measure the object plane to the outer housing rim during actual
setup … do you mean whatever I measure on the screen is wrong?" — right on both counts.
The vendor WD convention IS the housing rim (the only bench-accessible plane), so my
"reference-plane ambiguity" reconciliation above was wrong: **the scene really was ~9.4 mm
optimistic**. Root cause: a datasheet-only surrogate's principal split is NOMINAL
(bugs/0565 symmetric fallback) — nothing anchored the glass to the housing. On the ELS-85
the front principal sat 37.45 mm behind the STEP front face; the vendor's own Optimum
Working Distance row (142 mm @ 1.0×, EFL 85) demands 85·(1+1/1) − 142 = **28.0 mm**.

Shipped (general, per the standing rule):

- `parse_optimum_working_distance` (datasheet_prescription_import): recovers the Optimum
  WD + pairing |m| from the delaminated text soup via a physics window
  f/m* < WD < f(1+1/m*) — on the ELS soup that admits exactly 142; decoys (back focus
  glued as "10-4141.85mm", TTL, 26/68/85) fall out; ambiguity refuses. PYRITE sheets
  (no such label) refuse cleanly.
- `calibrate_lens_housing_to_datasheet_wd` (scene_placement_commands): slides the BODY
  (never the optics) along the lens axis until principal-behind-rim matches the vendor
  law. **Scar:** the first cut routed through `translate_step_overlay`, which drags the
  OPTICS rows with the body (the user-drag glue follow, 0574) — principal−rim stayed put
  and the conjugates broke; the fix writes the placement offset directly. EFL
  cross-check (5%) refuses a PDF that does not match the glass.
- Wired into the folder importer AND the lens swap (both after glue, before the 0608
  delivered-field re-measure — the housing openings are 0379 ray stops).
- ELS85 scene repaired + saved (backup: `machine_vision_ELS85_pre0647_backup.py`):
  rim +9.46 mm, datum/optics byte-identical, principal−rim 27.99, object→rim
  **121.89 → 131.34 ≈ the bench's ~130**, delivered semi(10 mm) unchanged to the last
  digit. Render: `recorded_bug_repros/render_0647_after_housing_calibration.png`.
- Guard: `validate_open3d_0647_housing_wd_calibration` = penta **phase 485**.

## RETIREMENT of the body shift (flag_20260825_132731 "lens surrogate detached from lens body")

The +9.46 mm body shift made the on-screen standoff bench-true — and floated the
surrogate's fictitious thin-group discs ~5.6 mm OUTSIDE the housing front. The user
flagged it within the hour. Scene REVERTED to the user's own 11:23 save (backup kept);
`calibrate_lens_housing_to_datasheet_wd` is now ADVISORY ONLY: it returns the honest
bench note ("on-screen standoffs read 9.4 mm SHORTER than the bench -- add 9.4 mm"),
appended by the folder importer and the lens swap. Guard C now asserts the function
moves NOTHING.

**The real fix — SHIPPED for the import path:** `refit_lens_principal_to_datasheet_wd`
re-solves the two-group internals (`solve_two_thin_groups` with ppa reduced by the
measured mismatch, ppp/span/datums/body/image-gap all preserved, object leg grown by the
mismatch so object→principal is invariant) — discs stay INSIDE the barrel, no visual
detachment. Auto-applied at folder IMPORT and persisted into the emitted library .py.
Verified end-to-end on a fresh ELS-85 import: mismatch −0.0000 after refit, conjugate
held exactly (object→principal 175.91 before and after), and the solved standoff followed
the vendor law to the last digit (object→rim 147.91 = f(1+1/0.935) − 28.0 − 0).

Three scars found on the way, all guarded:
- the refit must `_sync_table()` — `_write_layout_file` starts with
  `_read_rows_from_table()`, so a stale table silently REVERTS un-synced row writes on
  the next save;
- the refit must clear the learned magnification/centre + set the 0646 deferral (the
  0591/0608 "new machine" doctrine) — a stale centre let a solve "verify" 20×20 while
  the independent grid mapping read m=0.83;
- **frozen scenes need the desp RE-BAKE** — the "mis-verifying ruler" was never a pupil
  bug: on a frozen scene world_z = station + baked desp_z, so the refit's thickness
  edits (and the row-0 conjugate write) lifted the internal discs — and everything
  downstream — 9–17 mm OFF the leg in z while x stayed baked; every instrument then
  honestly measured a displaced hybrid. The frozen-aware refit (same function) skips the
  row-0 write (object world-pinned; the write would shift ALL downstream stations) and
  re-bakes the three internal rows' desp onto the leg at their new stations.
  **Verified on the user's saved ELS85**: rows 1–5 all at z=54.283 on the leg, trace vs
  first-order 1.294 vs 1.310 (1.2%), the 20×20 solve honest (focus −3.8e-05 mm, ruler
  −0.06% AND the independent grid mapping at m=1.1502 — reconciled), and
  **object→rim = 131.39 mm on screen** = the vendor law at the operating point (bench
  132 ± spec scatter). Scene saved; render
  `recorded_bug_repros/render_0647_frozen_refit.png`.

The SWAP path stays advisory for now — not because of the frozen hazard (solved above)
but because bugs/0648 (the 0645 recruit's interaction with consecutive opposing-room
solves, caught by guard 0573: 55×55-after-35×35 under-delivers 10.5% on Apo75+PYRITE)
must be resolved before adding another machinery interaction to that path.

**Authority decision (user, 2026-08-25): the datasheet PDF is the calibration source.**
The WD-aware build uses the vendor's Optimum-WD row (28.0 mm principal-behind-rim for the
ELS-85), NOT any single lab point — "there might be manufacturing error + lab measurement
error."

*Lab corroboration note (not used for calibration):* object plane → lens front outer rim
measured **132 mm** at the 20×20 operating point. Inverted: principal-behind-rim = 26.9 mm
— within 1.1 mm of the vendor row; the model's object→principal (159.3) matches the
bench-derived 160.0 within 0.7 mm. The vendor law, the model optics, and the lab agree to
~1 mm; the on-screen shortfall is purely the drawn housing registration. Practical rule on
the current scene: **on-screen standoff + ~9.4 mm ≈ bench** (datasheet law; the lab point
suggests ~10, inside the combined tolerance).

**0572 catch (fixed here):** the 0645 recruit could slide the fold mirror BEFORE the
snap's first apply refused, and the iteration-0 bail returned WITHOUT restoring the row
snapshot (pre-0645 nothing had moved by then) — an 11.2 mm mirror drift survived a
REFUSED 35×35 solve on the 0572 guard scene. Both refusal exits (and the
unmeasurable-pass break) now restore the best snapshot first: a refused snap leaves the
scene exactly as found.

STILL OPEN (the original frame-split finding stands): solve messages quote the
prescription-frame object distance (17.35 mm short of world on this scene) and the
delivered-m correction absorbs that split — the object-side world-truth reader
(the 0447/0478 image-side doctrine mirrored) remains to be built.

## Follow-up (2026-08-27) — the SWAP path refits too

The swap path had been left ADVISORY-only, with the hazard spelled out in its comment:
refitting a frozen scene's block moved the aperture stop inside desp-baked rows and the
stale learned state mis-verified the next solve (object->rim driven to 169 while the
ruler claimed 20x20). That hazard was fixed INSIDE the refit the same day (frozen desp
re-bake with row 0 untouched, learned m-correction + field centre cleared, re-measure
marked pending) -- the pin on the swap path was a leftover workaround, not a live
safety property.

Change: `swap_imaging_lens_from_folder` now calls `refit_lens_principal_to_datasheet_wd()`
(advisory remains as the refit's own internal fallback), placed BEFORE
`_swap_auto_refocus_to_best_focus()` so best focus and the m re-learn run on the
corrected optics. Guard 0647 check D inverted: it now REQUIRES the refit in the swap and
enforces the ordering (refit before refocus -- the one surviving hazard).

Verified (headless, real scenes):
- Pyrite90 (unfrozen) -> swap to ELS-85: message carries the refit note; post-swap
  registration mismatch -0.00 (principal 28.0 mm behind rim = vendor law, was 37.4);
  20x20 solve honest (diag 28.284 = want). Swap to a no-WD PYRITE folder stays silent.
- machine_vision_ELS85 (FROZEN -- the hazard scenario): post-swap mismatch +0.00;
  internal rows ON the leg (worst transverse 0.0000 mm; the broken refit lifted them
  9-17 mm); 20x20 solve honest (28.280 vs 28.284); object->rim 106.5 mm, not the 169
  hazard signature.
- Guards 0647 (A-E) and 0594 (incl. E's four real swaps, now through the refit) pass.
