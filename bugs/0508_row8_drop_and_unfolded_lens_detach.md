# 0508 — three 13:2x flags: live-only row-8 drop; unfolded lens detach; BS-drag semantics

All on build `36ddd3cd` (current). Evidence gathered 2026-08-02 13:30-13:45; fixes NOT started.

## A — `flag_20260802_131958` "dragged the LED left, the rays go pass the camera sensor"

The E2 signature again: Image row exactly one mirror->image thickness (44.11) below the sensor
(row 8 cz -26.38 vs sensor blend +17.73). The recording pins the trigger ORDER: two PERPENDICULAR
LED drags first (row 8 correctly rode the fold: -5.1 -> 2.7 -> 17.7), then a STATION x-drag
dropped it to -26.4; a second x-drag left it stable. **Headless replay of the exact z,z,x
sequence with a system rebuild per step does NOT reproduce** (row 8 holds 17.72) — the drop needs
a live-only ingredient (inspector refresh order / async worker replay / a probe failing only in
the live system state). Also observed in the flag state: the row-0 ACTOR at x=-30.24 while the
axis/object anchor is at -64.7 — a 34.5 mismatch (suspiciously the 11:0x session's mirror-slide
amount; check whether `_surface_reference_world_point(0)`'s transforms[0] is non-identity there,
which would make the bugs/0505 lateral add double-count). Next: replay the RECORDING's real Tk
events (the 0503 method) against the live inspector, and dump `frame_source` from the follower
builder at the failing rebuild — if it reports the fallback, log WHY the probe trace died.

## B — `flag_20260802_132302` "glued BS cube to LED, moved BS, the LED not moving"

BY DESIGN per bugs/0437, from the user's OWN earlier flag (flag_20260726_110337: the symmetric
carry "effectively cancelled the BS plate move"): the BS is the child seated in the housing —
dragging it repositions it RELATIVE to the LED; dragging the LED moves the assembly. If the
expectation has genuinely changed, that is a product decision to revisit 0437 (e.g. modifier-gated
assembly drag from the BS side), not a regression.

## C — `flag_20260802_132419` "glued lens to surrogate, drag lens STEP, surrogate not moving —
is the fix general or specific to certain file only?"

Fresh UNFOLDED nominal-axis scene (imports + Add-BS-cube this morning): lens body slid to
z[436.3, 492.6] while the surrogate rows stayed (rows ~397-454) — detached. The honest answer to
the user's question: the 0499/0503 row-carry only fires on a FOLDED leg (`_lens_leg_slide_plan`
gate `plan[2]`); an unfolded scene relies on the OLDER thickness redirect, which is gated on
`overlay_on_axis`, `abs(delta[2])>1e-9`, AND a row-NAME search ("front"+"datum|edge") — and may
not be reached at all if this drag committed through the CARRY path (carry_finish_transition)
rather than the translate gizmo (never verified in 0503). So: general on folded machine-vision
scenes, NOT yet general on this import path. Next: reproduce on this scene shape (import lens ->
glue -> drag via BOTH carry and gizmo), then unify: make the leg slide use the SAME row-carry
mechanism for the unfolded root leg (rows_along_leg on axis:root between the datums) instead of
the name-matched thickness redirect, and route the carry commit through translate_step_overlay.

## Update — C FIXED; A exhaustively chased, not reproducible on current code

**C fixed.** Reproduced on the user's own `machine_vision_150mm_test.py`: the whole-body carry
commits through `translate_step_overlay` PER FRAME, and the axial redirect's on-axis gate was
machine-precision (1e-3) — the first frame's 0.2 mm lateral jitter poisoned the placement offset
and every later axial increment slid the body off its optics (detached 23.4 mm over 40 frames).
The gate now uses a physical 3 mm tolerance; the flag_20260621_142758 parked-off-the-beam
protection is asserted intact. Guard: `validate_open3d_0508_unfolded_carry_keeps_lens_glued`,
penta phase 409. So the answer to "is the fix general?": the folded row-carry was always
projection-based and jitter-proof; the unfolded thickness redirect was the fragile one, and it is
now jitter-proof too.

**A not reproducible.** The recorded x,z,z,x LED sequence was replayed four ways — single-commit
headless, per-frame carry-style commits, per-frame with live STEP overlay trace rows, and through
the REAL inspector with `refresh_from_editor` + idle pumping between gestures — row 8 holds its
correct station (17.72) in every one, on the exact build (36ddd3cd) that produced the flag.
Remaining hypothesis: a mid-gesture ASYNC trace capture applied stale after the drag (the worker
snapshot re-seating followers from a half-moved state) — inherently timing-dependent, invisible
to synchronous replays. Needs a live re-test WITH recording active on current code; if it
recurs, instrument `apply_async_trace_result` with a model-generation check and log the follower
builder's `frame_source` at apply time.

**B** remains by-design (bugs/0437) pending a product decision.

## Update 2 — flag A cracked open: reproducible in ONE line, writer narrowed

The 14:05 recurrence (`flag_20260802_140514`, build 9a7e5593) forced a re-examination, and the
breakthrough: **my earlier "not reproducible" replays were green-washed — they asserted the MODEL
rows, but the drawn row-8 actor and the traced rays follow the BUILT SYSTEM.** Measuring the
system's image transform reproduces the flag exactly:

    x,z,z,x LED sequence:  MODEL row8 z = 17.72 (correct)   SYSTEM image z = -26.4  (= 17.72 - 44.12)

Bisected to a **one-line repro**: fresh load + `rows[3].desp_x -= 23.4` (the BS row alone, raw)
flips the built image from -5.08 to **-49.2** — exactly one mirror→image thickness (44.12) low.
The 0505 station write triggers it live because it legitimately moves the BS desp.

Ruled OUT with probes: model rows (clean), `_serializable_specs_for_rows` (only row-3 desp_x
differs), `_saved_promoted_step_native_trace_rows` (identical), trace mode (Non-Sequential
Preview both configs, no folded synthesis, 0 fold records), the follower override applier
(`_apply_optical_solid_output_port_system_overrides_built` spied during the real build — receives
EMPTY maps in both configs). The exit-frame probe trace only *reports* the already-moved image.

**Remaining suspect**: the image surface's post-trace finalization inside
`_build_preview_system_rays_bundle` — the 0433/0495 hard-stop / branch-detector placement (fit
from ray landings or an axial reference ray), which would key on the BS lateral pose vs the
NOMINAL axis — the same nominal-anchoring family as every 0505-era find. Next: trace
`_system_transform_list`'s source attribute and find who writes the image slot between build and
bundle return, with the one-line repro as the harness.

## Update 3 — writer hunt narrowed to its last corner

Additional exclusions, each by probe on the one-line repro (`rows[3].desp_x -= 23.4`):

* per-surface TRANS_2A diff: ONLY slot 3 (the moved BS, expected) and slot 8 (the image) differ;
  surfaces 4-7 identical -- no chain propagation, the image slot alone is rewritten;
* `Prerequisites3SMath` (the core cumulative math) cannot produce it (AxisMove=0 everywhere);
* `_apply_optical_solid_output_port_system_overrides_built` receives EMPTY override maps during
  the real build (spied);
* `_reconcile_folded_image_to_ray_convergence` STUBBED -- divergence unchanged;
* threshold sweep: desp_x -12 fine, -23.4 broken -- the flip sits between 12 and 23.4 mm,
  consistent with a REFERENCE RAY clearing vs missing the lens half-aperture (~14.1 mm);
* the arithmetic signature: healthy image = mirror_z - designed_gap (53.8 - 58.88 = -5.08);
  broken = mirror_z - (r7.thickness + designed_gap) (53.8 - 102.99 = -49.2) -- a DOUBLE-gap
  advance, r7.thickness applied once more.

Remaining candidates for the writer (next session, with the one-line repro as harness): whatever
in `_build_preview_system_rays_bundle` between engine build and bundle return rewrites TRANS_2A
slot -1 -- instrument by wrapping TRANS_2A in a write-logging list proxy, or bisect the builder's
stages by stubbing (`_folded_sequential_trace_rows` variants, hard-stop/branch-detector spec
surgery, `_apply_frozen...` solves). The gate is ray-reachability of a nominal-anchored reference
(the same 0505 family) and the wrong branch advances the mirror-image gap twice.

## Generality probe (2026-08-02, `bugs/probe_0508a_generality.py`)

Is A specific to `machine_vision_AZ85_RA_Mirror_BS.py`? One fresh process per
config (fresh load + one raw desp edit + build), MODEL `row_world_pose` vs
BUILT `TRANS_2A[-1]`:

| scene | config | model image | built image |
|---|---|---|---|
| AZ85_BS | baseline | (229.93, 0, -5.08) | same |
| AZ85_BS | `rows[3].desp_x -12` | held | same -- clean |
| AZ85_BS | `rows[3].desp_x -23.4` | held | z = **-49.20** (the -44.12 double-advance) |
| AZ85 periscope | baseline | (0, 0, 347.22) nominal | (275.32, 0, 71.90) folded |
| AZ85 periscope | `rows[1].desp_x -23.4` | held | (0, 0, 347.22) -- fold COLLAPSED to the straight chain (beam misses the slid prism; defensible non-seq physics) |
| AZ85 periscope | `rows[1].desp_y -23.4` | held | unchanged -- clean |
| AZ85 periscope | `rows[1].desp_x -40` | held | (0, 0, 307.22) = straight - 40 -- the off-beam neutralizer zeroed the prism's 40 mm row (bugs/0074 axial inertness) |
| 150mm GN straight | all 3 | -- | headless LOAD alone exceeded the 420 s cap; no data (and the signature is structurally precluded on a straight chain -- no fold walk, no mirror-thickness advance) |

**Verdict: the SYMPTOM is specific, the MECHANISM is general.** The
double-advance needs the AZ85-BS structural shape -- a BS-carried fold whose
follower placement probe dies while the fold itself survives, so the
face+thickness fallback walks the mirror row twice. The gate that decides
which branch runs -- ray-reachability of a nominal-anchored reference -- is
shared code: the periscope trips the SAME gate at the SAME kind of threshold
but resolves into fold-collapse or off-beam neutralization instead, both
defensible. So the fix must target the shared fallback (double-count) / anchor
the probe on `axis_root_origin`, NOT an AZ85-specific patch; the periscope
shove configs make good contrast fixtures for the guard.

## Update 4 -- A ROOT-CAUSED and FIXED: the off-beam reached-walk zeroed the frozen mirror

The TRANS_2A "writer" was never a post-build rewriter. Stage bisection
(`bugs/probe_0508a_writer_bisect.py`; spy prints land in the redirect capture ->
read them back from `kraken_debug_latest.log`) showed the image already at
-49.197 the moment `build_system` returned, with the override machinery
producing ZERO overrides even with the system in hand. The double-advance is
born in the SPECS: `neutralize_offbeam_inert_solids`, called at the top of
`_build_system_from_specs`.

Mechanism, measured (neutralizer sweep on the real scene):

* healthy (BS desp 0 / -12): `folded_beam_reached_mirror_fold_indices` = {3, 7}
  -> the RA mirror keeps its 44.119 mm row thickness;
* broken (-23.4 / -40): the walk -- launched from the NOMINAL (0,0,0)->+Z --
  folds at the SLID diagonal (axis hit at z = 53.8 - delta), so its reflect leg
  runs |delta| high and misses the mirror-face centroid by |delta|*sqrt(2)
  (33.1 mm at -23.4) > the sqrt(area)+2 = 27 mm hit radius -> mirror NOT
  reached -> `axially_inert_offbeam_solid_spec` zeroes its thickness. On the
  0448-inverted frozen leg (world = const - thickness) removing 44.12 mm of
  station pushes the built image one mirror->image gap PAST the sensor:
  -5.08 -> -49.20. Flip threshold |delta| > 27/sqrt(2) = 19.1 -- exactly the
  measured 12-vs-23.4 bracket (the earlier "lens half-aperture ~14.1" guess
  was wrong);
* the live flags (131958 / 140514) hit the same gate via the 0505 STATION
  drag: object+BS move together, the real beam still hits the mirror, but the
  nominal-anchored walk loses it.

Fix (`offbeam_optical_solid.py`), both halves in the shared gate:

1. **reached-by-authorship** -- a fold solid on a 0433-frozen/breadcrumbed row
   (`ScenePlacement.stay_put_freeze` / `last_axis_to_axis_move`, the same
   predicate the 0448 build path uses) seeds the reached set. A frozen chain's
   stations were AUTHORED with that thickness; zeroing it corrupts every
   downstream baked row by exactly one thickness. The geometric walk stays the
   arbiter for free-placed solids only.
2. **station-anchored launch** -- `_walk_launch_origin` starts the walk at the
   OBJECT row's lateral station (`axis_root_origin` semantics), so a station
   drag keeps the walk's verdicts geometrically too. Centred scenes are
   byte-identical.

Verified: the one-line repro heals (built image -5.077 at desp -23.4 and -40;
baseline and -12 byte-identical); the generality probe's periscope contrast
configs (no breadcrumbs) are byte-identical pre/post fix -- the fold-collapse
at -23.4 and the off-beam zeroing at -40 are both preserved. Guard
`validate_open3d_0508_frozen_fold_thickness_stable` (penta phase 410):
synthetic free-vs-breadcrumbed parked-fold contrast pair, real-scene
thickness-stability under the one-line repro AND the station gesture, and a
breadcrumb-STRIPPED walk check pinning the geometric re-anchor.

**B** remains by-design (bugs/0437) pending a product decision.
