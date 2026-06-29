# 0183 — BUG: folded coaxial-LED 2D "YZ full 3D" still has two big tilted orange parallelograms

## Flag

`attachment/recorded_bug_repros/flag_20260629_161038_580/` (description "3D") +
`attachment/2D.png` (titled "YZ full 3D"), re-recorded right after the 0182 corrective fix
(commit `6ff1dc4b`) shipped. The 3D starburst is gone (state.json `scene_visible_bounds` back to a
tight `x[-46,46] y[-46,46]`) and the ~67-quad scatter plaid is gone — but the **2D** view still shows
**two large tilted orange parallelograms** in the upper half (Y[8,75], Z[-44,42]) plus two orange
dotted crosshairs (the big one centred at Z≈0 Y≈42). The real geometry (object plane, BS, lens,
camera) is squeezed below them.

## Root cause — a DIFFERENT branch-detector explosion than 0182 (beam-splitter internal bounce)

0182 was about diffuse **scatter** leaves (`S3/scatter01..N`), gated by a `scatter`/`diffuse` token.
These two parallelograms carry **no scatter token**, so the 0182 gate never touches them.

The glued MV-150 beam-splitter **cube** is a non-sequential solid: the tracer forks **transmit/reflect
at every face interaction**, so a ray can re-bounce on the **SAME surface** (the cube, `S1`) over and
over:

```
S1:S1/transmit -> S1:S1/reflect -> S1:S1/reflect -> S1:S1/reflect -> ... (depth 8)
```

`services/branch_detectors.derive_branch_detectors` synthesises one detector per **terminal leaf**
(the 0090 "a beam splitter shows a detector on BOTH arms" behaviour). The internal bounce is
combinatorial — 2^(depth-1) leaves — so a dense LED bundle produced **128 deterministic-but-faint
ghost detectors**, all clustered at the cube. Each draws a `detector_active_footprint` orange quad +
crosshairs (`scene_projector._project_detector_footprints`); 128 of them overlap into the two
parallelograms (their final post-bounce directions differ slightly, so the projected quads are tilted
and don't perfectly coincide → you see ~2 outlines, not 1).

**Why the 0182 headless guard missed it (ray-count sensitivity).** The explosion only blooms at the
live LED ray count (`LED_RAY_COUNT = 60`). The 0182 guard builds the folded bundle with `ray_count=15`,
where the deep internal-bounce chains don't form: **15 rays → 67 branch detectors, 1 drawn** (the clean
`S1/transmit` leak); **60 rays → 199 branch detectors, 128 drawn** (the depth-8 ghosts). At 60 rays the
non-scatter targets split cleanly: 71 are scatter (depths 1-4, already draw-gated by 0182) and **128 are
depth-8 internal-bounce ghosts** (max same-surface hit count = 8, no scatter token → drawn → the plaid).

An internal-bounce ghost, like a scatter leaf, has **no meaningful focus** — a per-leaf detector plane
for it is noise.

## Fix — extend the DRAW gate to internal-bounce ghosts (still double-duty)

Same shape as the 0182 corrective fix: **keep the detector target** (it is an `is_detector` ray
hard-stop via `detector_planes_for_hard_stop`, so the rays stay bounded in 3-D — exactly the regression
0182 fought) and **gate only its 2-D DRAW**.

`services/branch_detectors.py`:
- `_branch_component_surface("S1:S1/transmit") -> "S1"` (the surface a component hits).
- `_branch_path_has_internal_bounce` — True when one surface is hit `_MAX_SAME_SURFACE_HITS = 3` times
  in a branch path. A legitimate double-pass (Michelson recombine, autocollimator return) hits a surface
  at most **twice**, so 3 is the first count that can only be an internal bounce. A multi-element fold
  uses **distinct** surfaces, so it is never tripped.
- `_branch_path_draw_suppressed = _branch_path_has_scatter OR _branch_path_has_internal_bounce` — the
  single predicate the draw gates now consult.

`scene_builder.py` — appends the `branch_detector_plane_curve` only when `not _branch_path_draw_suppressed`.
`scene_projector.py` — new `_target_branch_detector_draw_suppressed(target)` (target_source ==
"branch_detector" + `_branch_path_draw_suppressed`); `_project_detector_footprints` /
`_project_detector_miss_crosshairs` skip it. The scatter-only `_target_is_scatter_branch_detector` /
`_branch_path_has_scatter` are kept (the 0182 guard still asserts the scatter-specific classification).

## Verification

- **Live 2-D projection path** (`project_scene_bundle` + the editor arm/ray-display filters +
  `_projected_scene_for_layout_render`, exactly as `saved_layout_plot.py`) on the real folded layout at
  the native LED ray count (60): orange **detector** curves **128+ → 0** — the only orange that remains
  is the legitimate LED **source** line (`Coaxial 55x78 area LED`, Z45 Y[-39,39]). A rendered PNG
  snapshot confirms the two parallelograms + crosshairs are gone.
- **3-D stays bounded** — the change touches only the DRAW gates, never `derive_branch_detectors`, so all
  199 hard-stop targets survive; the 0182 guard re-confirms the bounded ray extent max|x,y| = 61.
- **Clean folds preserved** — at 15 rays the clean `S1/transmit` leak still draws (max-same-surface 1);
  `validate_open3d_beam_splitter_branch_detectors`, `validate_branch_detector_multi_arm`,
  `validate_open3d_detector_redundancy_drop` (clean 2-arm BS arms, max-same-surface 1, all kept) and the
  0181/0182 siblings stay green (the new predicate is a no-op without ≥3 hits on one surface).
- Guard `KrakenOS/UI/validate_open3d_branch_detector_internal_bounce_clutter.py` (display-free,
  `run_checks()`): unit (an 8-deep same-surface fork → 0 drawn, all kept as hard-stops; a clean 2-arm BS
  → both arms drawn; a 3-surface fold → both fold detectors drawn) and the real folded scene at the live
  ray count (0 drawn detector footprints, hard-stops still numerous, bounded extent tight). Wired as
  **penta phase 179**; baseline updated (standalone — the full marathon segfaults under Xvfb llvmpipe).

## Note

In-app eyeball still owed (headless can't drive the live VTK/matplotlib render), but the entire defect
— the branch-detector generation at the live ray count and its 2-D draw — is reproduced and asserted
headlessly, and a faithful matplotlib snapshot of the live projection confirms the plaid is gone.
