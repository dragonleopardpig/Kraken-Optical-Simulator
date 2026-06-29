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
