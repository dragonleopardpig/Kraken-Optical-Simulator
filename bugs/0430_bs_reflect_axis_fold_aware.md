# 0430 — Beam-splitter reflect axis is now fold-aware (draws on a mirror-folded scene)

**Flag `flag_20260723_155614`** (middle of a 3-flag before/after recording on `machine_vision_AZ85_RA_Mirror.py`,
build `a4be6128`):

> "After adding BS Plate, there is no optical axis generated from BS plate."

Recorded axis IDs, before **and** after adding the BS plate:
`['axis:global', 'axis:global:reflected:1', 'axis:global:reflected']` — the clean 2-RA-mirror fold, but
**no `axis:global:split`** (the BS's own reflect branch). Adding the BS also did **not** deviate the mirror
axis — confirming bugs/0429 holds (still 3 segments, not the pre-0429 four).

## Root cause

bugs/0428 Phase 1 drew the BS reflect axis by assuming the incoming beam is the global `+Z` at `x=y=0`, then
reflecting it off the coating. On a **mirror-folded** scene that assumption is wrong — the incoming to a BS
downstream of an RA mirror is the *folded* leg, not `+Z` — so an earlier follow-up gated the whole thing on
`not scene_is_folded`. That gate was **too broad**: it suppressed the BS reflect axis whenever *any* mirror
was present in the scene, even when the BS itself sits on the straight object leg (as in this flag, where the
BS plate is glued to the LED on the `+Z` object leg, upstream of both folds).

## Fix — derive each BS's incoming from the axis leg its coating sits on

Replace the scene-wide flag with a per-BS geometric lookup:

- **`nonseq_output_ports.beam_splitter_coating_world_frames(rows)`** (renamed from
  `beam_splitter_reflect_axis_frames`) — now returns each promoted BS's coating **(centroid, normal)** in
  world coords, and nothing else. The reflect math moved to the caller so it can use the *real* incoming.
- **`Kraken3DInspector._incoming_axis_leg_for_point(centroid, axis_records)`** (new, static) — scans the
  already-assembled axis guide records (`axis:global` + the mirror folds `reflected:*`) and returns the
  segment whose line passes **closest** to the coating centroid, as `(origin, unit_dir)` in propagation order.
  A BS before any fold → the object leg (`+Z`); a BS downstream of an RA mirror → the folded leg direction.
- **`_bs_reflect_axis_guide_records(bounds, axis_records)`** — for each coating, reflects that incoming leg off
  the coating (`d − 2(d·n)n`), finds the fold point where the incoming line crosses the coating plane, and
  draws `axis:global:split` out to the scene extent. Fold-aware, no `+Z` assumption.
- **`_optical_axis_records_for_3d`** — calls it **unconditionally** with the assembled `list(records)` (gate
  removed); with no promoted BS, `coatings` is empty and the walk is byte-identical.

Specular reflection is symmetric, so the same coating correctly sends `+Z → +X` (object-leg BS) *and* a folded
`+X → +Z` (folded-leg BS). Display-only — the follower placement still skips the BS (bugs/0396–0399); full
folded-scene BS *placement* is Phase 2 (predecessor chain).

## Verification

**`validate_open3d_bs_reflect_axis`** (penta phase 345, updated):

| check | asserts |
|---|---|
| REFLECT-MATH | `d − 2(d·n)n` off a 45° coating is symmetric (`+Z↔+X`) |
| FOLD-AWARE | `_incoming_axis_leg_for_point` picks the nearest segment (object leg → `+Z`, folded leg → `+X`) |
| NO-BS | `beam_splitter_coating_world_frames([]) == []` |
| MECHANISM | guide uses the coating helper + incoming-leg lookup + emits `axis:global:split`; assembler calls it with the records, **not** gated on `scene_is_folded` |
| PLACEMENT-UNCHANGED | the follower builder still skips the BS |

**`bugs/probe_0428_folded_bs_reflect_axis.py`** (end-to-end on the real folded AZ85 scene, under Xvfb):
loads `machine_vision_AZ85_RA_Mirror.py`, adds a BS plate to the LED, and asserts —
- BS reflect axis present: `['axis:global:split']` ✓ (was absent in the recording)
- mirror axis unchanged: `['reflected:1','reflected'] → ['reflected:1','reflected']` ✓ (0429 holds)

Neighbouring phases still pass: `validate_open3d_beam_splitter_transmit_and_second_axis`,
`validate_open3d_multifold_reflected_axis_segments`, `validate_open3d_bs_not_axis_fold`.

## Files

- `KrakenOS/UI/nonseq_output_ports.py` — `beam_splitter_reflect_axis_frames` → `beam_splitter_coating_world_frames` (returns coatings).
- `KrakenOS/UI/open3d_inspector.py` — `_incoming_axis_leg_for_point` (new); `_bs_reflect_axis_guide_records` fold-aware; gate removed in `_optical_axis_records_for_3d`.
- `KrakenOS/UI/validate_open3d_bs_reflect_axis.py` — updated guard (phase 345).
- `bugs/probe_0428_folded_bs_reflect_axis.py` — end-to-end folded-scene probe.

## In-app eyeball still owed

On `machine_vision_AZ85_RA_Mirror` with 2 RA mirrors: **add a BS plate** → a dotted `axis:global:split`
line must now appear from the BS coating along its reflect direction, while the 90° mirror fold is unchanged.
The visual *direction* of the split line on the folded scene is headless-untestable (VTK) — confirm it points
the physically correct way.
