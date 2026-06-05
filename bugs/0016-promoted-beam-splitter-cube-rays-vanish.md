# 0016 — A promoted beam-splitter cube makes every traced ray invisible

**Status:** Fixed (2026-06-05).
**Component:** Open 3D inspector — STEP-promotion face auto-classifier
(`_auto_assign_lens_face_functions`, `services/step_overlay_promotion.py`) and
the 3D ray-display filter (`_iter_3d_scene_ray_records`,
`services/three_d_scene_tools.py`) via a new predicate in
`KrakenOS/UI/scene_geometry.py`.
**Reported via:** in-app recorder, follow-up to bug 0015. **Repro bundles are
gitignored**, so the evidence below is transcribed here. Saved repro
prescription: `attachment/machine_vision_150mm_measured_test.py` (8 surfaces; S6
is a promoted LED STEP beam-splitter cube with 7 OpticalSolidFaces).

## Symptoms (user's words)

> the ray is still missing.

and, mid-investigation, after I proposed defaulting faces to Uncoated:

> heads up, I just tried assigning all surfaces to Uncoated, same, no rays at
> all.

A promoted STEP **beam-splitter cube** sitting on the optical path made *every*
physically-traced ray disappear in the 3D inspector — `ray_actor_count = 0` with
*Show Rays* on, *Trace Now* clicked. The rays trace fine numerically (279 ray
paths); nothing is drawn.

The user's two durable invariants (saved to memory):

1. *All promoted optical-solid faces should default to **Uncoated**
   (Transmit/Port). The user only authors the special faces (Mirror, Beam
   Splitter, Absorber, detector) — fewer manual assignments, faster.*
2. *A physically-traced ray **always traces** and stays visible up to its
   terminal surface. Even an absorptive face just stops the ray **at** that
   surface; in the real world a ray can never go missing **before** hitting a
   surface.*

## Root cause (confirmed 2026-06-05, headless)

Two compounding defects, both required to produce the blank scene:

### 1. The promotion auto-classifier hard-blocked the real optical faces

`_auto_assign_lens_face_functions` picks the body's optical axis from the
**largest anti-parallel pair** of faces, marks that pair `Transmit/Port`, and
condemned **everything else** to `Absorber/Mechanical`. A beam-splitter *cube*
has six equal-area faces, so the pair search picked ±X as the "lens" pair and
hard-blocked the real ±Z entry/exit faces — the on-axis beam was **absorbed on
the entry face**. (This is the same class of failure as a prism or any body
whose true optical faces aren't its largest anti-parallel pair.)

### 2. The default ray-display filter dropped every non-detector ray

With *Show Clipped Rays* **off**, `_iter_3d_scene_ray_records` kept only paths
whose terminal status was `hit_detector` (`ray_path_reaches_image_from_events`).
So:

* as-saved (Absorber on the entry face) every ray terminates `absorbed` → all
  dropped;
* even once the cube *transmits*, the 45° beam-splitter face read as a plain
  BK7↔air interface **total-internal-reflects** the on-axis beam (BK7 critical
  angle ≈ 41.8° < 45°), folding it 90° off-axis so it **misses** the sensor →
  terminal status `missed_detector` → also dropped.

Either way the default view showed **zero** rays — a direct violation of
invariant 2 (a traced ray must never silently vanish before reaching a surface).

**Fix #2 is the load-bearing one.** Defaulting the faces to Uncoated (Fix #1)
alone still left the scene blank, because the *transmitted* rays then TIR off the
45° face and miss the sensor — still `missed_detector`, still dropped by the old
filter. The user confirmed this directly ("assigning all surfaces to Uncoated,
same, no rays at all").

Headless reproduction (`machine_vision_150mm_measured_test.py`, 279 ray paths):

| scenario | terminal statuses | displayed (clipped off) |
|---|---|---|
| as-saved (Absorber entry) | 279 `absorbed` | **0** |
| all faces Uncoated | 279 `missed_detector` (45° TIR) | **0** |
| after Fix #2 | (unchanged) | **279** |

## Fix

### Fix #1 — promotion defaults faces to Uncoated, never Absorber

`_auto_assign_lens_face_functions` (`services/step_overlay_promotion.py`): the
two anti-parallel optical-axis faces are still flagged `Transmit/Port` and
labeled Input/Output, but **every other face now also defaults to
`Transmit/Port` (Uncoated)** instead of `Absorber/Mechanical`. Snell/Fresnel
then decides at each boundary and the user authors only the special faces.
Marking the faces Transmit (not leaving them `Unassigned`) still avoids the
older per-triangle-refraction fallback that produced erratic bending rays.
`_default_uncoated_optical_solid_face_metadata`
(`services/optical_solid_workflow.py`) likewise heals a stale non-manual
`Absorber/Mechanical` to Uncoated on STL import.

### Fix #2 — a traced ray stays visible up to its terminal surface

New predicate `ray_path_visible_without_clipping_from_events`
(`KrakenOS/UI/scene_geometry.py`): with *Show Clipped Rays* off, keep **every**
ray whose terminal status is `hit_detector`, `absorbed`, `stopped`, or
`missed_detector` (it traversed the optics but missed the sensor); hide **only**
an `escaped` ray (no next intersection — it left the system without reaching a
surface). `_iter_3d_scene_ray_records` now filters on this predicate instead of
`hit_detector`-only. A beam splitter's reflect branch that leaves the system
still shows only with *Show Clipped Rays* on; nothing is ever silently dropped
(clipped-on displayed == traced paths).

### Follow-up regression — analytic promotion over-counted surfaces

Fix #1 broadened `Transmit/Port` to *all* non-special faces. The
"Convert to Analytic Surfaces" promotion selected refractive surfaces by
`function == "Transmit/Port"`, so it then fitted one Standard surface **per
uncoated face** — a cylinder side wall became a spurious surface and the fit
demanded an extra glass per region. That broke promotion of the penta-telescope
cascade lenses (`need 3 glass name(s) for the 4 fitted surface(s); got 1`),
cascading through Phases 3/5/6/7/9/10/13. Fixed by tagging the genuine
optical-axis pair with `optical_axis_surface=True` in the auto-assign and
selecting **flagged** faces for the analytic fit (falling back to
`function == "Transmit/Port"` for manually authored bodies, where the user marks
only the real ports). The analytic fit again sees exactly the front/back pair;
the mesh trace still treats the side walls as uncoated.

## Tests

* **Display-free unit (Fix #2)** —
  `KrakenOS/UI/validate_open3d_traced_rays_always_visible.py`
  (`python -m KrakenOS.UI.validate_open3d_traced_rays_always_visible`). Asserts:
  predicate semantics (`hit_detector` / `absorbed` / `stopped` /
  `missed_detector` visible by default, only `escaped` hidden); a clean lens
  drops nothing; a mid-path fold (Mirror) makes every ray `missed_detector` yet
  all stay visible by default (pre-fix the default view showed 0); a beam
  splitter's escaped branch is hidden by default, shown with clipped on, and
  never dropped (`0 < off < on == paths`); a seeded random-element sweep
  confirms no silent drop; and (when the CAD cache is present) the user's real
  beam-splitter-cube scene shows 279 rays by default again.
* **Display-free unit (Fix #1)** —
  `KrakenOS/UI/validate_open3d_promotion_auto_lens_faces.py`: the two
  anti-parallel end faces get `Transmit/Port` (Input/Output) **and**
  `optical_axis_surface=True`; every other face defaults to Uncoated
  (`Transmit/Port`) with `optical_axis_surface=False`; the auto pass **never**
  assigns `Absorber/Mechanical`; and the analytic fit selects exactly the 2
  optical-axis faces (guarding the over-count regression). Prisms and
  pre-assigned bodies are left alone.
* **Display-free unit (analytic regression)** —
  `KrakenOS/UI/validate_open3d_promotion_analytic_fit.py` now selects refractive
  surfaces by the `optical_axis_surface` flag (matching production) and still
  recovers the Zemax Rc to < 0.01 mm for the Ball Lens / DCV / Achromat
  fixtures.
* **Regression / end-to-end** — `Phase 25`
  (`phase_25_traced_rays_always_visible`) in
  `validate_open3d_penta_telescope_comprehensive.py` wraps the Fix #2
  `run_checks()`. The analytic over-count is already guarded by the existing
  promotion phases (3/5/6/7/9/10/13). Gate baseline regenerated
  (`tools/penta_validator_baseline.json`).
* **Visual** — the real cube scene rendered off-screen with *Show Clipped Rays*
  off draws **279** multicolored ray polylines through the promoted cube up to
  the terminal image plane (was a blank scene). Confirmed by eye.
