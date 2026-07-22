# 0412 — Lens STEP overlay detached from its surrogate (AZ85 RA-mirror scene)

**User:** "can we fix the surrogate and lens STEP detached issue? I notice it in
`machine_vision_AZ85_RA_Mirror.py`. I think this is after your fix about flipping the lens."

The imaging-lens STEP overlay floats ~3.8 mm off its analytic surrogate on the AZ85 folded scene — the
glass block no longer sits inside the surrogate's front/rear datums.

## Root cause — a stale pre-0374 nudge double-counts the 0374 pin

The user's instinct was right: this surfaced after the lens-STEP re-registration work.

- **bugs/0374** changed how the lens STEP is pinned for display. It now pins the **optical glass-block
  centre** on the surrogate's **datum-span centre** (`_lens_step_display_front_z`), so the mechanical
  body no longer needs a hand-tuned glass-alignment nudge.
- Layouts authored **before** 0374 carried that nudge in `lens_step_placement_offset_xyz` — z set to
  `mechanical_front − front_glass_vertex` (the old body-face-pin correction,
  `STEP_GLASS_ALIGNMENT_Z_OFFSET_MM`). AZ85 (ELS-85) had **z = −3.8489…**, which is exactly
  `body_hi − glass_hi = 28.325 − 24.476 = 3.849 mm`.
- The aligner (`_cad_mesh_aligned_to_optical_axis`) adds `placement_offset` **on top of**
  `target_front_z` (`aligned[:, 2] += target_front_z` **then** `aligned[:, :3] += placement_offset`).
  So the pre-0374 nudge now stacks on the 0374 glass-centre pin → the STEP shifts by its full magnitude
  → **detached by 3.849 mm**.

Why the pin already lands it with **offset 0**: the ELS-85 **glass span equals the surrogate datum
span** (both **55.0 mm** — the surrogate was built from the STEP's glass vertices). With glass span =
datum span, pinning the glass-block centre on the datum centre puts the **front glass vertex exactly on
the front datum**. The old nudge is redundant, and now actively harmful.

## Fix — drop the stale offset

`lens_step_placement_offset_xyz` z **−3.8489… → 0.0** in both AZ85 copies:

- `KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py` (committed layout)
- `attachment/machine_vision_AZ85_RA_Mirror.py` (the user's working copy the app opens)

No engine change — the 0374 pin already does the right thing; we only remove the double-count. Verified
no validator or export asserts the lens-STEP offset/position (they only set/clear `lens_step_path`; the
export guard excludes the lens body).

## Verification (`validate_open3d_lens_step_datum_attached`, penta phase 336)

Display-free (no VTK / no app):

| check | asserts |
|---|---|
| LAYOUT-CLEAN | the committed AZ85 layout's `lens_step_placement_offset_xyz` z is ~0 |
| PIN-GEOMETRY | with the real ELS-85 glass metrics + datum span = glass span, offset 0 lands the front glass vertex ON the front datum (gap ~0); the old `body_hi−glass_hi` offset detaches it by 3.849 mm |
| MECHANISM | the aligner adds `placement_offset` AFTER `target_front_z` (so a stale offset detaches); `_lens_step_display_front_z` pins the glass-block centre on the datum-span centre |

3/3 pass. Baseline records phase 336 = pass.

## Scope / not touched

- **AZ85 (ELS-85)** is the clean, provable case: glass span = datum span = 55.0, offset = `body_hi−glass_hi`
  exactly → the fix is arithmetic, not tuning.
- **Pyrite85** (`machine_vision_Pyrite85_RA_Mirror.py`, attachment) is a *related but different* case —
  narrow barrel (glass-centre pin also active), but its offset (−3.5472) does **not** equal
  `body_hi−glass_hi` (3.27) and I have not confirmed its datum span equals its glass span, so I left it
  rather than risk clobbering a possibly-intentional value. Flagged for the user to confirm.
- **Datasheet layouts** using `STEP_GLASS_ALIGNMENT_Z_OFFSET_MM` on **wide** barrels (body-face pin,
  not glass-centre pin) legitimately keep their offset — those are not affected by 0374 and were not
  touched.

## Files

- `KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py` — offset z → 0.
- `attachment/machine_vision_AZ85_RA_Mirror.py` — offset z → 0 (working copy).
- `KrakenOS/UI/validate_open3d_lens_step_datum_attached.py` — guard (phase 336).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — register phase 336.
- `tools/penta_validator_baseline.json` — phase 336 = pass.

## In-app eyeball still owed

Open the AZ85 RA-mirror scene in the Open 3D inspector → the imaging-lens STEP glass block sits **inside**
its analytic surrogate (front glass vertex on the front datum), not floating ~3.8 mm off it.
