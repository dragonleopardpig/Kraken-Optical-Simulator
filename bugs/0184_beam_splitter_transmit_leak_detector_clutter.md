# 0184 — BUG: folded coaxial-LED 2D "YZ full 3D" still shows ONE tilted orange parallelogram at the preview ray count

## Flag

`attachment/recorded_bug_repros/flag_20260629_165748_297/` (description "3D") +
`attachment/2D.png` (titled "YZ full 3D"), re-recorded right after the 0183 fix
(commit `d24b1f06`) shipped. The two big parallelograms of 0183 are gone, but the **2D**
view still shows **one tilted orange parallelogram** plus small orange dotted crosshairs.
The real geometry (LED source line, object plane, lens, camera) is otherwise clean.

The decisive datum is in the flag's `state.json`: `sampling_diagnostics.ray_count` is
**15** (the `world_envelope` preview count), not the live LED count of 60. The 0183 fix
was verified at 60 rays; this case lives at 15.

## Root cause — a clean single-pass beam-splitter LEAK that survives BOTH per-path gates

0182 gated diffuse **scatter** leaves; 0183 gated **internal-bounce** ghosts (one surface
hit ≥3×). The surviving detector at 15 rays is neither:

```
branch_path = 'S1:S1/transmit'   (scatter=False, internal_bounce=False)
```

It is the LED light transmitting **straight through** the glued beam-splitter cube (`S1`)
exactly once and escaping — the coaxial illuminator's wasted forward leak. It hits no
downstream imaging optic and forms no image, so its synthesised detector plane is fitted
to a non-converging bundle at a fallback distance: a huge tilted ~78×78 mm quad near the
cube (the parallelogram) plus its crosshairs.

**Why it is ray-count-dependent (the real tell).** The SAME physical ray exists at both
counts. At **60 rays** the deep internal bounces form, so `S1:S1/transmit` is extended into
longer paths (`S1:S1/transmit -> S1:S1/reflect -> ...`) and is no longer a TERMINAL leaf →
`derive_branch_detectors` gives it no detector → nothing drawn. At **15 rays** those bounces
don't form, so `S1:S1/transmit` IS a terminal leaf → it earns a detector → it draws. A
detector that blinks in and out with the preview ray count is not physical; it is noise.

The 0183 fix even *intentionally* kept this clean leak drawing ("Clean folds preserved — at
15 rays the clean `S1/transmit` leak still draws"). That is correct **for a clean beam
splitter** (bugs/0090: a BS shows a detector on both arms), but wrong **in this diffuse
double-pass**, where the only real detector is the camera/image plane.

## Fix — promote the draw gate to a SCENE-LEVEL diffuse-scatter gate

In a diffuse double-pass scene EVERY synthesised branch detector is noise — scatter leaves,
internal-bounce ghosts, AND the clean BS leak alike. So the discriminator is the **scene**,
not the per-path token:

`scene_geometry.py`:
- `ray_paths_have_diffuse_scatter(ray_paths)` — True when any ray path underwent a diffuse
  scatter (reuses the existing `ray_path_has_diffuse_scatter`, the same predicate the 0181
  optical-axis scene gate uses).

`scene_projector.py`:
- `_target_branch_detector_draw_suppressed(target, scene_has_diffuse_scatter=False)` — returns
  True for ANY branch detector when `scene_has_diffuse_scatter`; otherwise falls back to the
  per-path `_branch_path_draw_suppressed` (0182 scatter token / 0183 internal bounce).
- `_project_detector_footprints` / `_project_detector_miss_crosshairs` compute the scene flag
  once (`ray_paths_have_diffuse_scatter(bundle.ray_paths)`) and pass it in.

`scene_builder.py`:
- appends `branch_detector_plane_curve` only when `not (scene_has_diffuse_scatter or
  _branch_path_draw_suppressed(...))`.

Same double-duty discipline as 0182/0183: the detector **target is kept** (still an
`is_detector` hard-stop via `detector_planes_for_hard_stop`, so rays stay bounded in 3-D —
no starburst); only its **2-D DRAW** is gated. The per-path predicates
`_branch_path_has_scatter` / `_branch_path_draw_suppressed` are unchanged, so the 0182/0183
guards' per-path unit assertions stay valid.

**Why this cannot break the clean beam splitter (bugs/0090).** A clean BS scene has NO
diffuse-scatter path, so `ray_paths_have_diffuse_scatter` is False, the scene gate is inert,
and both arm detectors draw exactly as before.

## Verification

- **Live 2-D projection path** (`project_scene_bundle(bundle, "Vertical")`, the same call
  `saved_layout_plot.py` makes) on the real folded layout: at the recording's **15** rays the
  orange **detector** curves go **3 → 0** (1 footprint + 2 crosshair-centers eliminated; the
  `branch_detector_plane_curve` is no longer appended, surface_curves 3 → 2); at **60** rays it
  stays 0. The only orange that remains at either count is the legitimate LED **source** line
  (`Coaxial 55x78 area LED`, Z45 Y[-39,39]). A rendered PNG snapshot at 15 rays confirms the
  parallelogram + crosshairs are gone.
- **3-D stays bounded** — the change touches only the DRAW gates, never
  `derive_branch_detectors`, so all 67 (15-ray) / 199 (60-ray) hard-stop targets survive; the
  0182/0183 guards re-confirm the bounded ray extent (max|x,y| = 61 / 60).
- **Clean beam splitter preserved** — a scatter-free 2-arm BS keeps both arm detectors drawn
  (the scene gate is inert without a scatter path); `validate_open3d_branch_detector_scatter_clutter`
  (0182), `validate_open3d_branch_detector_internal_bounce_clutter` (0183) and
  `validate_open3d_optical_axis_scatter_clutter` (0181) all stay green.
- Guard `KrakenOS/UI/validate_open3d_branch_detector_leak_clutter.py` (display-free,
  `run_checks()`): unit (a scatter scene suppresses ALL branch-detector draws incl. a clean
  `S1:S1/transmit` leak, while every target is kept as a hard-stop; a clean 2-arm BS still
  draws both arms) + the real folded scene at BOTH 15 and 60 rays (0 drawn detector footprints,
  hard-stops still numerous, bounded extent tight). Wired as **penta phase 180**; baseline
  updated (standalone — the full marathon segfaults under Xvfb llvmpipe).

## Note

In-app eyeball still owed (headless can't drive the live VTK/matplotlib render), but the entire
defect — the `S1:S1/transmit` leak detector at the live preview ray count and its 2-D draw — is
reproduced and asserted headlessly, and a faithful matplotlib snapshot of the live projection at
15 rays confirms the parallelogram is gone.
