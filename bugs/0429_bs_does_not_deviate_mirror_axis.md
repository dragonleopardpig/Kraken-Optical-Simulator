# 0429 — Adding a beam splitter deviated the RA-mirror optical axis

**Flags `flag_20260723_153852` / `_153949` / `_154034`** (a 3-flag before/after recording on
`machine_vision_AZ85_RA_Mirror.py`):

- **before BS:** axis records `[axis:global, reflected:1, reflected]` — a clean **2-RA-mirror fold** (3 segments).
- **after BS:** `[axis:global, reflected:1, reflected:2, reflected]` — a spurious **`reflected:2`** appears (4 segments).
> "the RA mirror optical axis deviates from 90 deg right after BS plate was added ... doesn't restore even
> the BS is not interfering it."

(The separate "no optical axis created by BS" is expected on this still-folded scene — the bugs/0428
Phase 1 BS reflect axis is gated to the unfolded case; it appears once the RA mirror is removed.)

## Root cause

`_folded_multifold_axis_guide_records` reconstructs the folded axis by grouping every **non-mirror** row
into a straight branch by direction (mirror rows are the fold vertices, excluded). A beam splitter is not a
mirror fold, so it wasn't excluded — but it **is** skipped from the fold override
(`build_optical_solid_output_port_pose_overrides`, so it never re-aims the camera, bugs/0396–0399). With no
override the BS row reads as the straight `+Z` frame while the surrounding folded rows read the leg
direction (`+X`). That direction mismatch spawns a **spurious extra branch → an extra fold vertex → the
mirror axis shifts** — and persists because it's the BS's presence in the chain, not its position.

## Fix

Exclude BS rows from the branch grouping, exactly like mirror rows:

- **`_promoted_beam_splitter_row_indices()`** (editor) — every promoted BS row, via
  `_optical_solid_faces_have_beam_splitter` (a "Beam Splitter" face) plus the explicit
  `add_beam_splitter_to_led` mark (`StepOverlayPromotion["beam_splitter"]` / `OpticalSolidBeamSplitter`).
- **`_folded_multifold_axis_guide_records`** now skips `row_index in mirror_rows or row_index in bs_rows`,
  so a BS never spawns a fold vertex. Adding a BS leaves the mirror axis unchanged.

Additive: with no BS, `bs_rows` is empty and the walk is byte-identical (the existing multifold validator
still passes). Display-only — placement is untouched.

## Verification (`validate_open3d_bs_not_axis_fold`, penta phase 346)

| check | asserts |
|---|---|
| CLASSIFY | a BS face → beam splitter (not a mirror fold); a Mirror face → fold (not a BS) |
| HELPER | `_promoted_beam_splitter_row_indices` uses `_optical_solid_faces_have_beam_splitter` + the explicit mark |
| EXCLUDE | the multifold branch grouping skips `bs_rows` like `mirror_rows` |

3/3 pass; the existing `validate_open3d_multifold_reflected_axis_segments` still passes (no-BS unchanged).

## Files

- `KrakenOS/UI/services/three_d_scene_tools.py` — `_promoted_beam_splitter_row_indices`.
- `KrakenOS/UI/open3d_inspector.py` — exclude `bs_rows` in `_folded_multifold_axis_guide_records`.
- `KrakenOS/UI/validate_open3d_bs_not_axis_fold.py` — guard (phase 346).

## In-app eyeball still owed

On `machine_vision_AZ85_RA_Mirror` with 2 RA mirrors: **add a BS plate** → the RA mirror axis must stay at
its clean 90° fold (no extra segment, no deviation). Remove the RA mirror → the BS's own second axis
appears (bugs/0428 Phase 1). The full folded-scene BS axis + placement is Phase 2 (predecessor chain).
