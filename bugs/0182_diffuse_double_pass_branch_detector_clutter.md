# 0182 — BUG: folded coaxial-LED 2D "YZ full 3D" view is a plaid of orange detector rectangles

## Flag

`attachment/recorded_bug_repros/flag_20260629_143602_903/` (description "3D") +
`attachment/2D.png` (titled "YZ full 3D"). After the 0181 fix the **3D** scene renders clean
(state.json: only `axis:global`, `optical_axis_actor_count: 1`, tight X/Y bounds), but the **2D**
`world_envelope` projection of the folded MV-150 coaxial-LED layout (0180) is still an unreadable
plaid of ~50 orange crisscrossing rotated rectangles spanning Z[-110,130] Y[-150,150].

## Root cause

Same disease as 0181 (diffuse scatter is non-deterministic), a **different render path**.

The folded scene is a non-sequential diffuse double-pass: LED → BS reflect → object →
**diffuse scatter** → BS transmit → lens → camera. `services/branch_detectors.derive_branch_detectors`
synthesizes one detector per **terminal leaf branch** of the traced ray tree — the 0090 "a beam
splitter must show a detector on BOTH arms" behaviour. But a diffuse scatter forks **one leaf per
scattered ray** (`S3/scatter01..N`), so the builder produced **69 branch-detector targets**.

Each branch detector emits, in the 2D projection:
- a `detector_active_footprint` **orange `#f97316` quad** (`scene_projector._project_detector_footprints`),
- two `detector_active_center` orange crosshairs, and
- an `image`-kind **plane outline quad** (`branch_detector_plane_curve`).

So 69 detectors → **67 orange footprint quads + 134 orange centers + 67 image plane quads**, each at
its own random scatter-direction pose → the crisscrossing plaid. The scattered detector planes also
blew the projection bounds out to ±150, shrinking the real geometry and hiding the rays underneath
(orange is drawn at zorder 72, on top).

`multi_leaf`-gives-every-leaf-a-detector is right for a 2-arm beam splitter; it is pathological for a
20-way scatter. A scattered branch has **no deterministic focus** — its post-scatter direction is
random — so a per-leaf detector plane is meaningless.

## Fix

`derive_branch_detectors` (`services/branch_detectors.py`): a new `_branch_path_has_scatter` predicate
drops any **leaf whose branch path contains a diffuse-scatter component** (`scatter`/`diffuse` token)
before detectors are derived. The rays themselves still render, and the real Image plane (an *existing*
target) still catches them — only the redundant per-scatter detector planes go away. This mirrors
0181's per-segment guard ("once a ray scatters, everything downstream is non-deterministic — drop it").

Surgical, not a blanket: a **scatter-free** split (a genuine beam splitter) has no scatter token in any
branch path, so every arm keeps its detector. The one **deterministic** survivor in the folded scene is
the LED straight-through leak (`S1/transmit`) — a real branch, correctly kept (1 rectangle, not 69).

## Verification

- Headless on the real folded layout: **69 branch-detector targets → 1** (the clean transmit leak);
  orange projection curves **~200 → 5**; `image` plane quads **67 → 1**. The 2D view renders the folded
  ray path cleanly with one detector box instead of the plaid.
- Clean folds preserved: `validate_open3d_beam_splitter_branch_detectors`,
  `validate_branch_detector_multi_arm`, `validate_open3d_detector_redundancy_drop` all stay green
  (the filter is a no-op without a scatter token).
- Guard `KrakenOS/UI/validate_open3d_branch_detector_scatter_clutter.py` (display-free, `run_checks()`):
  unit (3-way scatter fork → 0 scatter detectors, clean leak kept; clean 2-arm BS → both arms) and the
  real folded scene (1 branch detector, 0 on scatter branches). Wired as **penta phase 178**; baseline
  updated (standalone — the full marathon segfaults under Xvfb llvmpipe).

## Note

In-app eyeball still owed (headless can't drive the live VTK/matplotlib render), but the branch-detector
generation — the entire defect — is reproduced and asserted headlessly, and a faithful matplotlib
snapshot of the projection (`scene_renderer_2d.render_scene_2d`) confirms the plaid is gone.

## UPDATE — the first fix caused a 3D starburst regression (corrective fix)

**Flag** `attachment/recorded_bug_repros/flag_20260629_154209_345/` (description "3D"), re-recorded right
after the fix above shipped (commit `0a6dae00`). The 2D view is now clean — but the **3D** view became a
**starburst** of rays radiating in every direction, blowing `scene_visible_bounds` out to
**x[-235,592] y[-342,286]** (vs the known-good tight x[-46,46] y[-46,46] before).

**Root cause of the regression — branch detectors do DOUBLE DUTY.** Dropping the scatter leaves out of
`derive_branch_detectors` removed not just the *drawn* plane/footprint but the detector **target** itself.
Each branch detector is an `is_detector` `SceneTarget3D` that also feeds
`detector_planes_for_hard_stop` → `bounded_ray_points_for_scene_display`, i.e. it is a ray **hard-stop**
plane that **clips the otherwise-escaping scatter rays**. The diffuse scatter is non-deterministic —
133/173 rays "escape" (no Image hit) — so with the 67 per-scatter hard-stops gone, every escaping ray
extended to the **scene radius** → the 3D starburst. (The 2D looked fine because the YZ
`set_plot_limits(..., max_radius=50)` clamps Y to ±50 regardless; only VTK's `ComputeVisiblePropBounds`
exposed the blow-out.) Confirmed headlessly: with the scatter detectors present the bounded ray extent is
x[-5,61] y[-45,54] z[-47,78]; with them dropped only **1** hard-stop survives and the extent blows to
x[-181,234] y[-163,469].

**Corrective fix — keep the detector, gate only its DRAW.** `derive_branch_detectors` is reverted to its
original behaviour (it once again yields a detector per leaf, so all 67 hard-stops are back and the rays
stay bounded). The `_branch_path_has_scatter` predicate is now a **draw gate**, not a derivation filter:
- `scene_builder.py` — still appends the branch-detector *target* (the hard-stop) for every leaf, but only
  appends its `branch_detector_plane_curve` (the dark `image` plane) when the branch is **not** scatter.
- `scene_projector.py` — `_project_detector_footprints` / `_project_detector_miss_crosshairs` skip targets
  for which the new module helper `_target_is_scatter_branch_detector` (reads `metadata.target_source ==
  "branch_detector"` + `_branch_path_has_scatter(metadata.branch_path)`) is true → no orange footprint/
  crosshair drawn for a scatter detector.

So: scatter detectors are **invisible hard-stops** — they bound the rays in 3D (no starburst) but draw
nothing in 2D (no plaid). The single deterministic `S1/transmit` leak detector still both bounds and draws.

**Verification (headless).** Real folded layout: **67** branch-detector hard-stops kept (66 scatter,
draw-gated); bounded 3D ray extent **max|x,y| = 61** (was ~470 during the regression); 2D projection draws
**1** detector footprint + **1** branch plane (was ~67). The guard
`validate_open3d_branch_detector_scatter_clutter.py` was rewritten to assert all three of these (plus the
unit rule: a scatter fork keeps a detector per scatter leaf, each scatter-classified; a clean 2-arm beam
splitter keeps both arms, neither scatter-classified). Penta **phase 178** delegates to the same
`run_checks()`; its docstring was updated to the double-duty story. The three clean-BS validators and the
0181 sibling guard stay green. A fresh matplotlib snapshot confirms the 2D stays clean.
