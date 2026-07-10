# 0288 — Illumination footprint projection (soft-penumbra dark edges)

STATUS: **DESIGN COMPLETE, NOT YET IMPLEMENTED.** Investigation done this session; no
production code written yet. This doc is the RESUME-HERE for the build. Task #453.

## The two flags (both on the real vendor MV-150 scene + an added LED)

- `attachment/recorded_bug_repros/flag_20260710_170554_093/` — "still a small patch
  launching from object plane."
- `attachment/recorded_bug_repros/flag_20260710_170627_720/` — "heat map."

Both show a **small central radial heatmap blob** on the sensor instead of a full-FOV
illumination pattern that would reveal dark edges *if they exist*.

Flag `170627_720` state.json: `step_actor_counts {lens:1, led:1, camera:1}`, the LED
`step_overlay_poses.led.placement_offset_xyz = [22.8856, -0.0208, 0.0]`, LED
`step_actor_bounds ≈ [-32.2, 78.0, -45.0, 45.0, 186.9, 263.3]` → the LED sits AT the BS
(z 187–263, BS centre z≈229.6), offset +22.9 mm in x. So the flagged LED is coaxial
(beside/at the BS), NOT at the object plane — the "launching from object plane" wording
describes the heatmap being *computed* at the object plane and showing a small patch.

## What the user asked for (verbatim intent — do not drift)

- "tell KrakenOS to launch rays within the 'limited projected area' so that it shows dark
  edges if exist."
- **"no hardcoded value please, it is meant to be general, going to implement it on other
  setup as well."** ← vetoes any tuned/analytic teaching-scene formula. Derive EVERYTHING
  from scene geometry.
- Soft roll-off (penumbra weight), not a hard mask ("1. soft roll off").
- User confirmed "yes, please" to build mechanism **B** (below).

## Root cause of the flags

`add_illumination_led_source` (source_modeling.py 982–1043) seats the LED at
`_current_source_origin()` with `half = max(radius, 5)`, `cone = 30°`, 2000 rays. Two
regimes, both broken for the user's goal:

1. **LED at the object plane (default add, z≈0):** a small ~10 mm emitter floods only a
   ±7 mm central patch of the 16.3 mm-radius object → the projection is *faithful* but the
   illumination is **starved** → small radial blob. (Reproduced headlessly: centre 0.447,
   all edges 0.000; on-sensor fold 0.351 / perp 0.324; drawn 23×23.)
2. **LED coaxial beside the BS (flagged pose, z≈225):** the flood reflects off the BS fold
   face toward the object *geometrically*, BUT the imaging trace never relays it — the
   **trace-order wall** (below). So 0 illumination lands on the object → the traced coupled
   map returns None → the only thing left to bin is the sparse imaging fan → small blob.

The projection pipeline (0286) is **correct**; the illumination that reaches the imaged
object aperture is what's missing.

## The trace-order wall (confirmed headlessly — `diag_0286_flood_path_probe.py`)

KrakenOS traces in **surface-index order**. On the real scene object = surface 0 (z=0),
BS = surface 1 (z≈202). A flood reflecting off the BS back toward the object runs *backward*
in index order and is never retested against surface 0. Probe (with the +x absorber face
flipped to transmit so nothing blocks the flood): **min z reached = 202.2 mm, 0 rays below
z=100.** The flood physically cannot land on the object through the trace. Confirmed again
as the 0287 finding: a coaxial-via-BS flood cannot reach an object BEHIND the BS.

⇒ B **cannot** use traced object hits. It must GEOMETRICALLY complete the illumination
trace: reflect the terminal illumination rays off the fold face and intersect the object
plane ourselves.

## The anamorphic 45° fold (`proto_bs_limiter_footprint.py` — analytic PROOF, teaching layout)

A 45° fold compresses ONLY the fold-plane axis by cos45° = 1/√2; the perpendicular axis
passes unchanged. The proto proves the **BS clear aperture is the limiting stop** that
carves the dark edges: project the BS aperture onto the LED/object plane through each FOV
point, overlap with the source → fold-edge coverage ≈ 0.66, perp ≈ 1.00 → 2 fold-axis dark
edges. NOTE: the proto hardcodes `L.*` teaching constants — it is a PROOF of the physics,
NOT the production path (which must be scene-derived).

## Real-scene reality — SURFACE THIS TO THE USER

On the real vendor MV-150 the BS-projected footprint (~39 fold × 78 perp) **EXCEEDS** the
object aperture (Ø32.6 / r16.29). So a *faithful* footprint projection reads **~UNIFORM (no
dark edges)** on the user's real scene. Dark edges are a compressed/teaching-geometry
phenomenon. This is consistent with the user's own "shows dark edges IF exist" framing — on
the real scene they don't; the FOV is fully illuminated. B must honestly show uniform there
and carve edges only where a setup genuinely under-fills. Tell the user this so the uniform
result isn't a surprise.

## Mechanism B — geometric illumination-footprint projection (THE PLAN)

Bypass the trace-order wall by geometrically completing the illumination trace:

1. Take the ISOLATED illumination source records (launched flood) via
   `_coupled_object_illumination_records(system, wavelength)` (three_d_scene_tools.py 3684 —
   union of launched 0284 + isolated marker 0267/0270 records).
2. For each record get the launch origin + direction (LED→BS is direct, so use
   `source_l/m/n`), OR the terminal hit on the BS + incoming direction.
3. Reflect off the BS **fold-face normal**, read GENERICALLY from the beam-splitter face
   metadata (`row.advanced["OpticalSolidFaces"]["faces"][*]` — the beam-splitter/transmit
   face normal; on the vendor scene it is [-0.707, 0, 0.707]). NO hardcode.
   `r = d - 2(d·n)n`. On the vendor scene d=[-1,0,0] → r=[0,0,-1] (straight to the object).
4. Geometrically intersect the object plane (z = object-surface z from the object row).
5. Bin the resulting (x,y) footprint into a SOFT penumbra weight map (peak-normalized),
   reusing `object_illumination_projection_map`'s conventions (adaptive bins over the
   FOOTPRINT extent not the whole aperture; source_object_coupling.py 146).
6. Weight each imaging ray by sampling the footprint at its object origin
   (`imaging_ray_object_origin` + `sample_irradiance`, source_object_coupling.py 98 / 76).
7. **GATE:** dark edges appear IFF the footprint UNDER-FILLS the imaged FOV (object
   aperture). Footprint covers the aperture → uniform. (This is the "if exist" gate.)

### No-hardcode checklist (the user's hard constraint)
- object-surface z + radius ← object row
- fold-face normal ← beam-splitter face metadata (generic read)
- sensor half-extent ← `_detector_target_half_extent`
- bins ← adaptive from hit count
- NO teaching-layout `L.*` constants, NO tuned sensor/ray-count/sigma.

## Where to wire it

- **New function** in `KrakenOS/UI/services/source_object_coupling.py`, e.g.
  `geometric_illumination_footprint_map(editor, system, object_surface_index, fold_face_normal,
  object_z, object_radius, *, ray_records, sensor_half, bins=None)` — reflect→object-plane→bin,
  returns a `build_source_illumination_overlay`-ready map (same shape as
  `project_object_map_onto_sensor` output).
- **Dispatcher** `KrakenOS/UI/services/three_d_scene_tools.py`
  `_compute_source_illumination_overlay_spec` (3589): add the geometric footprint as a
  fallback AFTER density-on-sensor (`_compute_detector_density_illumination_overlay_spec`
  3600) and the traced coupled map (`_compute_coupled_object_illumination_overlay_spec`
  3742) — i.e. fire it when the trace lands 0 illumination on the object (the real-scene
  case). MUST NOT redefine imaging conjugates (0266); render-only + cached like the siblings.
- The per-ray weighting path already exists
  (`_illumination_weighted_detector_spot_samples`, main_path_detector_analysis.py 190–290)
  but is only called by the guard, NOT wired to live display
  (`_plot_branch_detector_spot_analysis` 292–397 uses the PLAIN unweighted samples at 301).
  B may wire the weighting to the live spot plot too, or keep to the overlay for now.

## Why the existing 0286 coupled map returns None on the real scene
`object_illumination_projection_map` → `editor._source_illumination_hit_samples(system,
object_surface_index, …)` reads hits AT the object surface. Real scene = 0 (trace-order
wall) → None → blank. Hence B's geometric completion is required, not optional.

## Remaining workflow steps (per CLAUDE.md / feedback memories)
1. Build the geometric footprint function + dispatcher wiring (no hardcode).
2. Reproduce BOTH flags headlessly (never off the screenshot): reconstruct the flagged LED
   pose (coaxial, z≈225, offset +22.9 x) and confirm B produces a full-FOV footprint —
   uniform on the real scene, edges only where genuinely under-filled.
3. Display-free guard exposing `run_checks() -> (bool, list[str])`.
4. Penta-validator phase.
5. Surgically regen `tools/penta_validator_baseline.json`.
6. ONE commit `Open 3D: … (0288)`, trailer
   `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
7. Push to `nonseq-display-refactor`.
8. Memory update + end with a Flag/Report/Status markdown table.

## Key files & line numbers
- `source_object_coupling.py`: `object_illumination_projection_map` (146),
  `project_object_map_onto_sensor` (225), `sample_irradiance` (76),
  `imaging_ray_object_origin` (98), `couple_imaging_records` (117),
  `DEFAULT_COUPLING_BINS=16` (28).
- `three_d_scene_tools.py`: `source_illumination_overlay_spec` (3559),
  `_compute_source_illumination_overlay_spec` (3589),
  `_compute_detector_density_illumination_overlay_spec` (3600),
  `_coupled_object_illumination_records` (3684),
  `_compute_coupled_object_illumination_overlay_spec` (3742).
- `main_path_detector_analysis.py`: `_illumination_weighted_detector_spot_samples` (190–290),
  `_plot_branch_detector_spot_analysis` (292–397).
- `source_modeling.py`: `add_illumination_led_source` (982–1043) — the small-patch source.
- `validate_open3d_source_object_coupling.py` — the 0286 guard (phase 241); note the fixture
  hardcode `led["radius_y"]=39.0` (177–178), low-priority to generalize (test fixture, not
  the mechanism).
- `attachment/machine_vision_150mm_test.py` — the real vendor scene (object r16.29, gap 202
  to BS; BS = promoted STEP BK7 55×55×78 cube, beam-splitter face normal [-0.707,0,0.707],
  absorber face on +x; sensor 23×23).

## Probes (this session — committed alongside this doc)
- `diag_0286_flood_path_probe.py` — proves the trace-order wall (min z 202.2, 0 below z=100).
- `diag_0286_led_placement_probe.py`, `diag_0286_coaxial_placement_probe.py` — LED placement.
- `diag_0287_diffuse_fold_probe.py`, `diag_0287_object_plane_extend_probe.py` — 0287 finding.
- `proto_bs_limiter_footprint.py` — analytic proof the BS aperture is the limiting stop
  (teaching layout, hardcoded — PROOF only, not the production path).
