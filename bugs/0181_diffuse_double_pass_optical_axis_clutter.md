# 0181 — BUG: folded coaxial-LED 3D view is a mess of giant stray "Optical Axis" lines

## Flag

`attachment/recorded_bug_repros/flag_20260629_140228_972/` (description "3D") + `attachment/2D.png`
(titled "YZ full 3D"). Both the 3D scene and the 2D YZ projection of the folded MV-150
coaxial-LED layout (0180) render as an unreadable tangle of huge crisscrossing lines.

The recorder's `state.json` is the tell: `optical_axis_records` holds the legit
`dotted_global_guide` (record 0) **plus 6 `traced_chief_ray_segment` records** ("Optical Axis
2–7") whose endpoints reach **±1000–1150 mm scattered in all three axes**
(`axis:ray:580:segment:2`, `axis:ray:579:segment:2/6`, `axis:ray:247:segment:4`,
`axis:ray:246:segment:4/7`). They blow `scene_visible_bounds` out to x[-1035,1122] y[-410,347]
z[-1076,1082] for a rig whose real parts span ~±90 mm — so the camera fits to the stray lines
and everything useful shrinks to a dot.

## Root cause

The traced-optical-axis builder promotes "genuine fold" ray segments to scene-spanning dotted
guides (a beam-splitter's reflected branch, a fold mirror, a penta deviation). A **diffuse
scatter is non-deterministic**: the Diffuse Object sends every ray off in its own random
direction, so a diffuse double-pass has **no single chief-ray optical axis**. The builder was
blind to scatter in two places:

1. **Per-segment** (`services/ray_display_geometry.py`, `_dotted_axis_records_from_ray_path`):
   the existing scatter exclusion (`_is_external_between_surface_axis`) only rejects a segment
   whose **immediately adjacent** event is a scatter. A segment one hop further on — *scatter at
   the object → beam-splitter → lens* — has refraction/split events on both sides, so it slipped
   through carrying the **random post-scatter direction**. (Headless repro: all 6 stray records
   were **segment 4**, `from_event_type` `split_reflect`/`split_transmit` — i.e. the BS
   interaction on the return pass, downstream of the scatter.)

2. **Whole scene**: even the **down arm** (LED → BS reflect → object, *before* the scatter)
   produces clutter, because the LED is an **extended 30° area source** — its reflected cone
   fans ±25° off −Z, so the fold has many distinct directions that never merge into one axis.
   After fixing (1), the 6 slots simply refilled with these segment-2 down-arm cone directions.

So the real defect is conceptual: an optical axis only means something for a **collimated**
fold. The zemax LED beam-splitter template is in the same boat (a Zemax-rayfile LED, also
extended + diffuse double-pass) — neither scene has a chief axis to draw.

## Fix (two layered guards)

- **Per-segment** (`_dotted_axis_records_from_ray_path`): scan the path's surface events for the
  first scatter; **drop every segment that starts at or after it**. A genuine fold with *no*
  upstream scatter still earns its axis. (Principled core; defends any caller.)
- **Scene-level** (`open3d_inspector._optical_axis_records_for_3d`): a new
  `scene_geometry.ray_path_has_diffuse_scatter` predicate gates `allow_traced_axis_guides` —
  **any** diffuse-scatter path in the bundle suppresses **all** traced axes, leaving only the
  global dotted guide. The rays themselves still render the folded path; only the redundant
  guide lines go away.

The gate is precise: a scatter-free beam-splitter scene still draws its single +X folded axis
(confirmed — `validate_open3d_beam_splitter_transmit_and_second_axis` and the penta cascade
prism-by-prism guard both stay green), so penta/beam-splitter fold axes are untouched.

## Verification

- Headless repro on the real folded layout: **6 traced axes spanning x[-817,931] z[-853,902]
  → 0 traced** after the fix (global guide only).
- Clean folds preserved: beam-splitter guard = 1 folded axis; penta cascade = chief exit
  well-defined through every fold.
- Guard `KrakenOS/UI/validate_open3d_optical_axis_scatter_clutter.py` (display-free,
  `run_checks()`): per-segment (post-scatter tail dropped, scatter-free fold kept), scene-level
  (scatter scene → global only, clean fold → axis kept), and the **real folded layout → global
  guide only, 0 traced**. Wired as **penta phase 177**; baseline updated (added standalone — the
  full marathon segfaults under Xvfb llvmpipe).

## Note

In-app eyeball still owed (headless can't drive the live VTK render), but the axis-record
generation — the entire defect — is reproduced and asserted headlessly.
