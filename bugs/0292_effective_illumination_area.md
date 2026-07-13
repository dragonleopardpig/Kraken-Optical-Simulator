# 0292 — "Effective Illumination area" bounds the imaging FOV

Follows the 0287–0291 MV-150 coaxial-LED illumination work. The user's exact ask:

> *All I want is this "Effective Illumination" area passed to KrakenOS imaging ray launching engine for it
> to launch imaging rays from 38.9×39 mm FOV instead of the Imaging Lens FOV of 39×39.*

## The physics the user is describing
The MV-150 side LED is a **55×74 mm** collimated area beam on the **55×78 mm** face of a **55×55×78 mm**
beam-splitter cube folded at **45°**. Folding foreshortens the fold axis (`55·cos45 = 38.9 mm`) while the
perpendicular axis stays 74 mm. That folded footprint is the **effective illumination area**. Intersected
with the 39×39 mm imaging-lens FOV it is **38.9 × 39 mm** — it under-fills the FOV on the fold axis only, so
the two fold-axis sensor edges go dark while the perpendicular axis stays uniform.

(The bare 0.05 mm shortfall of 38.9 vs 39 is invisible with a hard edge; the *visible* dark band comes from
the diffuser/LED-array **soft penumbra** straddling the FOV edge — modelled below.)

## Why we can't just trace it (the engine wall, restated)
A folded flood is a **split branch ray**, and the non-sequential engine traces branch rays in surface-index
order — a branch never re-consults the later limiting aperture (documented 0287/0289). So a traced folded
flood always over-fills → uniform, and cannot foreshorten itself. The effective area therefore has to be
built **geometrically**, then imaged onto the sensor — bypassing the un-traceable flood without any
display-only nudge.

## Approach (b) — the one the user greenlit ("OK, go for (b)")
Rather than read the fold geometry off the promoted BS by heavy scene analysis (approach a), attach a small
**coaxial-illuminator descriptor** (aperture + fold angle + fold axis) to the LED spec at *Add Illumination
Source* time. The overlay dispatcher then:

1. builds the effective-area footprint **geometrically** from the descriptor
   (`effective_fold = aperture_fold · cos(fold_angle)`, perp unchanged), with a raised-cosine soft edge; then
2. images that footprint onto the sensor with the **existing bugs/0288 kernel**
   `project_footprint_onto_sensor(map, |m|, sensor_half_w, sensor_half_h)`, which samples the object footprint
   at `o = s/|m|` per sensor cell and darkens where the footprint under-fills.

No hardcoded FOV, sensor size, ray count or sigma: the fold angle + aperture come from the descriptor, `|m|`
and the sensor half-extents come from the real scene. Display follows physics — the sensor darkens exactly
where the effective area fails to cover the FOV.

## Implementation (SHIPPED — general, display-free geometry + the 0288 projector)
- **Geometry kernel** — `KrakenOS/UI/services/source_object_coupling.py`:
  - `_aperture_soft_edge(coord, half, penumbra)` — raised-cosine roll from 1→0 across the penumbra at ±half.
  - `coaxial_illuminator_footprint_map(aperture_fold_mm, aperture_perp_mm, fold_angle_deg, *, fold_axis,
    penumbra_mm, grid, margin_mm)` — foreshortens the fold half by `cos(fold_angle)`, leaves perp alone, lays
    the soft-edged separable density on a local grid; default penumbra `max(6%·fold, 0.5 mm)`; non-finite /
    non-positive inputs → `None`.
- **Descriptor reader** — `KrakenOS/UI/scene_source_analysis.py`:
  `coaxial_illuminator_descriptor(spec)` — reads `coaxial_illuminator` + `coaxial_aperture_fold_mm` /
  `_perp_mm` / `coaxial_fold_angle_deg` / `coaxial_fold_axis` (+ optional `coaxial_penumbra_mm`) off a spec
  dict *or* a `SceneSource3D.settings`; non-coaxial specs → `None`. Spec normalization preserves arbitrary
  keys, so the descriptor round-trips.
- **Dispatcher wiring** — `KrakenOS/UI/services/three_d_scene_tools.py`:
  - `_compute_coupled_object_illumination_overlay_spec` now consults the coaxial branch **first**: if a live
    descriptor resolves and yields a spec, return it; otherwise fall through to today's traced-flood path
    unchanged.
  - `_live_coaxial_illuminator_descriptor()` — first enabled physical scene source whose spec yields a
    descriptor, else `None`.
  - `_coaxial_illuminator_overlay_spec(system, target, descriptor)` — guards `|m|` and the sensor
    half-extents, builds the footprint map, projects with the 0288 kernel, colours from the camera record,
    returns a **render-only** `build_source_illumination_overlay(...)`.
- **Descriptor seed at Add-Illumination** — `KrakenOS/UI/services/source_modeling.py`:
  `_coaxial_illuminator_descriptor_from_module(...)` reads the transformed LED-module bounds — a decentred
  (side-mounted) module → `fold_axis` from the larger decentre, `aperture_fold = along-axis (z) face dim`,
  `aperture_perp = cross-fold face dim`, `fold_angle = 45°`; an on-axis module → `fold_angle 0` (keep the
  fallback aperture). `add_illumination_led_source` attaches the result to the LED spec.

## Verified end-to-end (real vendor scene, no display)
| path | fold edge | perp edge | verdict |
|---|---|---|---|
| isolated kernel → sensor (`bugs/diag_effective_illum.py`, geometry only) | 0.723 | 1.000 | 2-sided fold-dark |
| **production dispatcher, explicit 55×74/45° descriptor** | **0.823** | **1.000** | **2-SIDED fold-dark ✓** |
| on-axis module (fold_angle 0) | ~1.0 | ~1.0 | uniform (graceful, no false edges) |

`|m| = 0.5908`, sensor half 11.52×11.52 mm, imaged-FOV half 19.50 mm. The production overlay draws the two
fold-axis dark edges the user expects while the perpendicular axis stays uniform.

## Non-regression
A scene **without** a descriptor makes `_live_coaxial_illuminator_descriptor()` return `None` → the coaxial
branch is skipped → the traced-flood fallback runs byte-for-byte unchanged (confirmed directly:
descriptor-less `SIDE_LED` → live descriptor `None`). So 0287–0291 behaviour is untouched.

## Guard + gate
`KrakenOS/UI/validate_open3d_effective_illumination_area.py` (`run_checks()`) — display-free: soft edge +
geometric footprint (fold foreshortened, perp unchanged) + descriptor reader (round-trip, non-coaxial→None) +
module-bounds seed (side LED → fold axis from decentre; on-axis → angle 0) + **wiring contract**
(`inspect.getsource`: dispatcher consults the branch first, overlay uses the kernel and is render-only,
`add_illumination_led_source` attaches the descriptor) + **real vendor scene when present** (Add LED attaches
a descriptor; an explicit 55×74/45° descriptor drives the production overlay to fold edge < 0.85 dark, perp
edge ≥ 0.85 uniform). Penta **phase 256**, baseline updated.

## Note / remaining
This models the effective area from the **as-authored aperture + fold angle**. The *hard*-edged limiting
window of the true side-in → BS-reflect path (the ~30 mm illuminator stop) still isn't traced — that remains
0289's documented future engine work (split-branch rays don't consult later aperture rows). The descriptor
apertures are user-tunable on the spec (`coaxial_aperture_fold_mm` / `_perp_mm` / `coaxial_fold_angle_deg` /
`coaxial_penumbra_mm`) for scenes whose window differs from the module face.
