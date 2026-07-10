# 0286 — illumination overlay still shows nothing on the real MV-150 scene (Piece 2 / Approach A)

## Symptom (flag_20260710_085240_847, "Illumination overlay still show nothing")

On the real vendor scene `attachment/machine_vision_150mm_test.py` the user adds a scene-illumination
source (the LED of bugs/0283/0284, or marks the beam-splitter face per bugs/0264), switches on the
on-detector illumination heatmap, and the **sensor draws blank** — no coaxial dark edges. The
2-D "Relative illumination" report has the signal, but the sensor overlay is empty.

> "Illumination overlay still show nothing."

(Sibling of bugs/0285 "after adding Scene Source" — that flag was the phantom side-detector; this one is
the illumination→object→detector coupling, the deferred **Piece 2** of the scene-source-object feature.)

## Root cause — 0 illumination rays reach the sensor, so the DENSITY heatmap cannot build

The existing overlay (`_compute_detector_density_illumination_overlay_spec`, idea #3, bugs/0259–0282) bins
**source-illumination rays AT the detector** and reads their local hit density. That works for the coaxial
**teaching** layout, where ~60k LED rays flood the sensor directly. But on the **real vendor MV-150** the
imaging lens sits between the beam splitter and the sensor: the LED / marked face floods the **OBJECT at the
FOV**, and essentially **0 illumination rays reach the sensor** — even when the object is a mirror. So the
density path (needs ≥50 sensor hits) returns `None` and the sensor is left blank.

Characterized headlessly on the real scene (`bugs/diag_0286_density_probe.py`, `…_aim_probe.py`,
`…_aperture_probe.py`):

| source | object hits (r≤16.3 mm) | **sensor** hits | note |
|--------|------------------------:|----------------:|------|
| physical LED | ~1738 (central ±7 mm, clean coaxial rolloff) | **0** | floods FOV, images the object |
| LED + row0→**Mirror** | ~1738 | **0** | a mirror does **not** route the flood to the sensor either |
| marked 45° BS face `S001/F001` | **0 in-aperture** (sprays r∈[27.6, 43.9] mm ring) | ~5–14 | flood misses the imaged FOV entirely |

So a density-on-sensor heatmap is **impossible** on this scene (there is no on-sensor illumination sample),
and the marked-face case has **nothing to image** (it lands off the imaged aperture).

## Fix — image the object onto the sensor: bin illumination-on-object, PROJECT onto the sensor (Approach A)

The lens images the object plane onto the sensor, so the on-sensor illumination pattern **is** the
illumination-on-object pattern, rescaled to the sensor. `source_illumination_overlay_spec` becomes a
dispatcher — **direct density first**, then a coupled **projection** fallback:

* `source_object_coupling.object_illumination_projection_map` — bin the illumination landing **within the
  imaged object aperture** into a peak-normalised dark-edge map. It **clips to the aperture** (only that
  light is relayed) then **bins over the surviving data footprint** (the illumination shape), so the coaxial
  rolloff fills the map instead of shrinking to a speck ringed by un-illuminated aperture. Off-aperture
  floods (the 45° marker) keep **0** hits → `None` → sensor correctly blank (display follows physics).
* `source_object_coupling.project_object_map_onto_sensor` — keep the density grid, **rescale the edges to
  the sensor active half-extent** (`±half` per axis). This bakes the object→sensor conjugate as a uniform
  fill of the sensor square and avoids the bugs/0275 trap of drawing the quad at the FOV size.
* `three_d_scene_tools._compute_coupled_object_illumination_overlay_spec` orchestrates: object index →
  live-source records → aperture radius → project → sensor half-extent (target dims **or** the bugs/0276
  vendor override) → `build_source_illumination_overlay` at the sensor center/normal/tangent. Gated exactly
  like the density path (bugs/0280/0282: a **live non-marker** source must be present) so a pure imaging
  scene never fabricates a map from its sparse pupil/field fan.
* `main_path_detector_analysis._source_object_coupling_object_index` generalized: **Diffuse > Mirror /
  Object Target > plain sequential Object**. The real vendor row 0 is a plain "Object", so it now has a
  couplable surface; the 0274 Diffuse/Object-Target behaviour is unchanged.

### The user's "make the Object a mirror" request

> "making the Object a mirror surface rather than diffuse surface can visualize the dark edges more clearly."

Correct, and honoured: under the projection the map is **numerically independent** of what the object
reflects **into** (we bin the illumination landing **on** it), so a mirror, an Object Target, and a plain
Object all project the **same** dark-edge map — but a **mirror preserves the coaxial edges sharply** whereas a
diffuse/Lambertian object would blur them. Mirror is now recognised as a first-class couplable object and is
the sharpest semantic; it is not a special-case code path.

### Sub-bug found by the portable fixture — clip/centroid length mismatch

`object_illumination_projection_map` copied the samples dict and reindexed only `x`/`y`/`weights` to the
aperture clip, leaving the full-length `source_ids`/`source_names` lists — so
`source_illumination_map_data_from_samples`' centroid loop indexed a full-length list with the clipped mask
→ `IndexError` → `None`. The **LED case never tripped it** (its flood lands wholly inside the aperture, so
nothing was clipped); the **portable coaxial-scatter fixture** (footprint spilling past the aperture) exposed
it. Fixed by reindexing the id/name lists to the same clip. (A textbook case for the "validate on a general
fixture, not just the real scene" rule.)

## Validation

Display-free guard `KrakenOS/UI/validate_open3d_coupled_object_illumination_projection.py`
(`run_checks()`), penta **phase 252**:

* **Projection math** — aperture-clip + data-footprint binning (peak-normalised; far outliers dropped;
  too-few / all-off-aperture → `None`); edges rescaled to the sensor, pattern untouched (bugs/0275).
* **Object recognition** — Diffuse > Mirror/Object Target > plain Object; no object → `None`.
* **Dispatcher contract** — density before coupled; the coupled compute is render-only (no re-trace);
  the records path is source-gated (bugs/0280/0282).
* **Coupled fallback end-to-end** on the portable coaxial-scatter fixture — a 20×20 heatmap draws at the
  detector active size (39 mm), object idx 2 is **not** promoted to the detector plane idx 3 (bugs/0266).
* **Density non-regression** — the coaxial-LED teaching scene still returns the **direct** density overlay
  (fold 0.82 < perp 1.08).
* **Real vendor scene** (when `attachment/machine_vision_150mm_test.py` is present; it is gitignored, so
  SKIP + `bugs/diag_0286_production_wire.py` cover it for clones): +LED → **PRESENT** dark edges at the
  **23 mm** sensor (min_rel 0.05); marked BS face → `None`; no source → `None`.

Real-scene production dispatcher (`bugs/diag_0286_production_wire.py`):

| case | `source_illumination_overlay_spec` | drawn at |
|------|------------------------------------|----------|
| + physical LED | **PRESENT** fold 0.35 / perp 0.32 / min 0.05 | 23×23 mm sensor ✓ |
| + LED + row0→Mirror | **PRESENT** (≡ LED, mirror inert) | 23×23 mm sensor ✓ |
| + marked 45° BS face | **None** (sprays off the imaged FOV) | blank ✓ |
| no source (pure imaging) | **None** (0280/0282 gate) | blank ✓ |
| coaxial teaching (non-regression) | **PRESENT** density fold 0.73 / perp 0.96 | detector ✓ |
