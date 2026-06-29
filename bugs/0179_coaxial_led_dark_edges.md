# 0179 — FEATURE: MV-150 coaxial area-LED relative-illumination shows the 2 dark edges

## User setup (Q4 / Q5)

Real production machine-vision rig: an **MV-150 lens + 25 MP camera** imaging a **39×39 mm
FOV**, illuminated **coaxially** by a **55×78 mm area LED**. The LED light reflects off a
55×55×78 mm beam-splitter (BS) cube down to the FOV, returns through the BS, and reaches the
lens/camera. The 25 MP image shows **2 dark edges on one axis** and stays uniform on the other:
the **fold-axis** BS clear-aperture stop (~30 mm, i.e. half-width 15 mm) **under-fills** the
39 mm FOV, while the **perp-axis** 78 mm dimension **covers** it.

- **Q4** — model the 55×78 area LED at the reflected (virtual on-axis) position.
- **Q5** — reproduce the 2 side dark edges with the in-app **Relative illumination** analysis.

The layout `common_optical_layouts/machine_vision_150mm_coaxial_led.py` unfolds the coaxial path
on-axis: Object (78 mm, the area LED) → rectangular UDA stop at z=75 (`half_x=15` fold,
`half_y=39` perp) → Image (FOV) at z=130. Source = `Random rectangle source` (radius_x=27.5 <
radius_y=39). `trace_mode = "Non-Sequential Preview"` (the stop is a non-circular UDA → non-seq).

## Symptom

The deterministic coverage model proved the geometry *should* carve dark fold edges (fold
edge/centre ≈ 0.66, perp ≈ 1.00), but the **in-app relative-illumination map stayed flat** — no
dark edges. The map is built from the non-sequential scene-source trace
(`build_scene_bundle` → `_source_illumination_hit_samples`), and that pipeline let *every*
launched ray reach the FOV regardless of the stop.

## Two root causes

**#1 — the rectangular UDA stop did not vignette in the non-seq trace.** In non-sequential mode
a ray that lands outside a finite stop is simply not chosen by `__NonSequentialChooser` and
sails straight through. `__NsApertureStopVignette` (KrakenSys.py, from bugs/0093) terminated such
rays at the stop plane, but only tested the **circular** `Diameter`/`InDiameter` and only for
surfaces flagged `IsApertureStop`. A `UDA` (User-Defined Aperture) rectangle was neither flagged
nor polygon-tested, so the fold stop never blocked anything. (The *sequential* trace already
vignettes a UDA via `UDA_Obj.Hit` in `InterNormalCalc`.)

**#2 — vignetted rays were mislabeled as image hits.** Even once the trace correctly terminated
a blocked ray at the stop plane (z=75), the scene bundle still counted it as reaching the image.
The non-seq chooser picks the meshed image surface (the AIR stop is never *chosen*), so for a
blocked ray the loop breaks at the vignette **before** `__CollectData` runs → `len(self.GLASS)==0`
→ the post-loop `__EmptyCollect(... j)` tags the ray with `j` = the chosen **image** surface (2).
`build_scene_bundle` then reads `last_surface ∈ detector_surface_indices` → `reaches_image=True`,
so `_source_illumination_hit_samples` counted the vignetted ray as a FOV hit. Net effect: the
sampler's FOV-box count stayed constant as the stop shrank.

## Fix (root cause, both layers)

- **`KrakenOS/UI/layout_editor.py`** (`_build_system_from_specs`): flag a surface that carries an
  active `UDA` as `IsApertureStop = True`, so the non-seq vignette considers its polygon (a UDA
  is an *intentional* clear aperture; this never fires for arbitrary lens edges, preserving the
  random-element robustness rule).
- **`KrakenOS/KrakenSys.py` `__NsApertureStopVignette`**: after the circular clear-aperture test,
  also reject a crossing point that fails `UDA_Obj.Hit(Px, Py)` — the same test the sequential
  trace uses. Return `(world vignette point, blocking surface index)` instead of just the point.
- **`KrakenOS/KrakenSys.py` NsTrace + `__NsTraceBranching`**: at the vignette break, record the
  **blocking stop** as the ray's terminal surface (`self.val = 0; __EmptyCollect(vign_pt, …, vign_k)`)
  so the post-loop empty-collect can't tag it with the downstream image surface. The bundle then
  reads `last_surface = stop` → `reaches_image = False`, and vignetted rays drop out of the map.

## Verification

- Block test: as the fold stop shrinks (`half_x` 15→6→2) the sampler's FOV-box throughput now
  **collapses** (847→386→136) — previously constant. The stop genuinely vignettes.
- In-app trace at nominal geometry (`half_x=15`, 8000 rays, seeded): the relative-illumination
  sampler shows **fold(X) edge/centre ≈ 0.68 (dark)** while **perp(Y) ≈ 1.23 (uniform)** — the 2
  dark edges, on the fold axis only.

## Guard / phase

`KrakenOS/UI/validate_open3d_coaxial_led_dark_edges.py` (display-free) gains `_check_in_app_trace`:
it runs the **real** scene-source trace + relative-illumination sampler and asserts the fold FOV
edge is dark (≤0.85), the perp edge uniform (≥0.85), with a clear gap (≥0.12). This is the
decisive check — the prior analytic coverage model passed even while the real pipeline was broken,
because it never traced a ray. Wired as **penta phase 175**; baseline updated (0–175 all-pass).
