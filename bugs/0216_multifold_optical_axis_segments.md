# 0216 — optical axes 2 (middle) and 3 (outgoing) vanish on the two-mirror fold

**Status: FIXED. On the two-mirror AZ85 (ELS-85 surrogate) folded scene only ONE reflected optical-axis
line was drawn — going straight DOWN from the first fold. The middle axis (mirror-1→mirror-2, +X) and the
outgoing axis (mirror-2→detector, −Z) were missing. The reflected axis is now reconstructed as a folded
POLYLINE through the mirror vertices, so all THREE optical axes are drawn (incoming +Z, middle +X,
outgoing −Z), with rays OFF. Fixes flag_20260703_153616_668 "the 2nd optical axis disappears after
promotion, Optical Axis 3 is completely not visible".**

## What the user flagged

Recording `flag_20260703_153616_668` enumerates three optical axes on the two-mirror scene:

1. *"the first optical axis should be OK"* — the incoming +Z guide (fixed in 0215). ✓
2. *"The 2nd one partially OK. When I doing the snapping of the RA mirror, the 2nd optical axis is there.
   But after promotion, it disappeared."* — the MIDDLE axis (mirror-1 → mirror-2).
3. *"Optical Axis 3 is completely not visible."* — the OUTGOING axis (mirror-2 → detector).

The recording state had `show_rays = False`, so only the *geometric* dotted guides draw (no traced ray
segments). The one reflected guide present was `axis:global:reflected = (0,0,71.9) → (0,0,−99.4)` — a
single line straight DOWN from the first fold, x pinned at 0.

## Root cause — the reflected guide was single-fold only, and under-counted the 2nd mirror

`axis:global` covers only object → mirror-1 (clamped at the first fold, bugs/0215). The OUTGOING leg was
drawn by `_folded_reflected_axis_guide_record` (`KrakenOS/UI/open3d_inspector.py`), which:

- gated on a `single_fold` count of rows whose *folded* surface is `"Mirror"`, and
- drew ONE segment from the fold point along the IMAGE-plane row's composed fold direction.

Two things broke on a chain of two folds:

1. **The fold count under-counts the free-placed 2nd mirror.** `_folded_sequential_trace_rows` only marks
   the SEQUENTIAL mirror (mirror-1) as `"Mirror"`; the free-placed 2nd mirror (bugs/0213) never gets a
   sequential record, so the `Mirror`-surface count is **1**. The scene was treated as single-fold.

2. **The single drawn direction is the twice-folded image direction.** With `single_fold` (wrongly) true,
   the method applied the IMAGE-plane row's fold transform to `+Z`. The image is on the twice-folded
   branch, so that direction is **−Z**. Anchored at the first fold `(0,0,71.9)` it drew
   `(0,0,71.9) → (0,0,−99.4)` — straight down, x never leaving 0.

So the middle (+X) axis was never emitted (axis 2 "disappeared") and the outgoing leg pointed the wrong
way from the wrong place (axis 3 "not visible").

## The fix — reconstruct the folded axis polyline through the mirror vertices

Two new pieces:

**1. `three_d_scene_tools.py` — `_promoted_mirror_fold_row_indices()` (editor).** Counts *every* promoted
full-mirror fold (sequential AND free-placed) with one predicate, `_is_promoted_mirror_fold` (a promoted
optical solid carrying a Mirror face). On the two-mirror scene this returns `[1, 8]` — where the old
`Mirror`-surface count returned 1. These rows are the fold VERTICES of the axis.

**2. `open3d_inspector.py` — `_folded_multifold_axis_guide_records(bounds, fold_point_z)`** (+ helpers
`_folded_axis_row_anchor_direction`, `_axis_branch_line_vertex`). For ≥2 folds it reconstructs the axis
polyline:

- Each NON-mirror row's world axis anchor `P = F @ (0,0,z)` and direction `D = R @ +Z` come from its fold
  transform `_optical_axis_fold_world_transform_for_row` (unfolded rows stay on the incoming +Z axis).
- Group the non-mirror rows into straight BRANCHES by direction (the mirror-body rows, which report their
  own off-branch pose, are excluded — they are the vertices, not the runs).
- The clean fold VERTICES are the closest-approach intersections of consecutive branch lines.
- Emit the MIDDLE segments bounded between two vertices and the OUTGOING segment extended to the scene
  bounds (the same reach the single-fold method uses for its one leg).

`_optical_axis_records_for_3d` routes to this builder when the scene is folded and returns `[]` for < 2
folds, so the single-fold path (`_folded_reflected_axis_guide_record`) is completely untouched and
byte-identical.

Two-mirror result (rays OFF, the recording state) — three dotted optical axes:

```
axis:global              (0,0,z0)          → (0,0,+76.9)     +Z  incoming  (axis 1, bugs/0215)
axis:global:reflected:1  (0,0,+71.9)       → (+181.4,0,+71.9) +X  middle    (axis 2)
axis:global:reflected    (+181.4,0,+71.9)  → (+181.4,0,−...)  −Z  outgoing  (axis 3, to the detector)
```

## Verification

Display-free guard `validate_open3d_multifold_reflected_axis_segments` (8/8, rays OFF):

1. the two-mirror scene draws THREE `dotted_global_guide` axes;
2. the MIDDLE axis (`axis:global:reflected:1`) starts at the first fold (x≈0, z≈+72) and runs +X to
   mirror-2 (end x > 100) — axis 2 restored;
3. the OUTGOING axis (`axis:global:reflected`) starts at the 2nd fold (x > 100, z≈+72) and goes −Z down
   toward the detector — axis 3 restored;
4. the incoming `axis:global` still runs +Z up to the first fold (bugs/0215 preserved);
5. **CAUSAL:** the old `_folded_reflected_axis_guide_record` on the SAME scene returns ONE −Z line with
   BOTH endpoints at x≈0 — never the +X middle nor a distinct outgoing leg (exactly the bug);
6. `_promoted_mirror_fold_row_indices()` counts BOTH folds (2), where the old `Mirror`-surface count was 1;
7. the single-mirror scene is byte-identical (one `axis:global:reflected`, no `:1`, multi-fold returns []);
8. the fix is wired.

Causal check confirmed by stashing the fix: the guard raises `AttributeError:
'_promoted_mirror_fold_row_indices'` against the old code (it is coupled to the fix), and check 5
independently documents the old wrong down-line against the current code.

Registered as penta **phase 192** (`phase_192_multifold_reflected_axis_segments`), baseline `pass`. The
full validator marathon still SIGSEGVs on llvmpipe, so phases 0–191 are carried forward.

Scratch probes (untracked): `bugs/probe_0216_multifold_axis.py` (per-row anchors/branches),
`bugs/probe_0216_records.py` (end-to-end records, rays on/off), `bugs/probe_0216_causal.py` (the old
down-line).

## In-app eyeball owed

The headless guard proves the three geometric axes are emitted with rays OFF (incoming +Z, middle +X,
outgoing −Z). Confirm the rendered dotted axes in-app on the user's two-mirror AZ85 scene — in particular
that the outgoing leg reaches the detector (its far end clamps to the scene bounds, which include the
detector plane when its actor is present).

## Relationship to the still-open two-mirror focus bug

This draws the axes from the folded GEOMETRY, independent of the traced rays, so it is not blocked on the
two-mirror "unfocused image" bug (flag_20260703_145514, next in the queue). When rays are ON the traced
`axis:ray:*` segments still terminate early (the dead-centre chief ray does not reach mirror-2 until the
image focuses through the two folds); the geometric guides here fill that in regardless.
