# 0274 — Source → Object → Detector coupling (Stage 3, Option B: irradiance-weighted imaging)

Stage 3 of the **Source + Object separation** feature (`bugs/DESIGN_source_object_separation.md`). A marked
face is an illumination **source**; the object is a **scatterer**. Stages 1–2 shipped the authoring +
emission + absorb (bugs/0267–0273). This stage makes the source's non-uniformity — e.g. the MV-150 coaxial
**dark edges** (bugs/0179) — ride the **actual detector image**, not just the standalone "Relative
illumination" overlay.

Follows the user flag `flag_20260709_083737_055` confirming 0273 ("Illumination source surface no longer
shows phantom Image Plane or Detector"), and the directive: *"Please proceed with Stage 3."*

## Option B — factorized coupling (the design's recommended model)

Rather than a full unified non-seq scatter trace (Option A, exact but expensive), we **factorize**:

1. Trace the illumination source onto the object **once** and bin its irradiance into a smooth,
   peak-normalized density map — reusing the 0259–0262 relative-illumination machinery
   (`source_illumination_map_data_from_samples`).
2. **Weight** each object → lens imaging ray by the local source irradiance sampled at its **object
   origin** (the first hit where the ray left the object surface, in the same surface-local frame the map
   is binned in).

The coupled detector weight is `base_weight × irradiance@origin`. The source rolloff then imprints on the
image the imaging trace already produces.

**Coarse binning matters.** An imaging ray's object origin is (by construction) exactly where a source ray
landed, so a *fine* grid over a modest ray budget leaves each origin alone in its bin → a 0/half/peak
staircase (probe: a 73×73 grid gave ~2 distinct weights). A **coarse 16×16 grid** (`DEFAULT_COUPLING_BINS`)
recovers the smooth falloff the coupling must transfer.

## The fix — additive, read-only over imaging (protects bugs/0266)

* **`services/source_object_coupling.py`** (new, pure/display-free) — `object_irradiance_map` (bins the
  source → object landing), `sample_irradiance` (nearest-bin, 0.0 off-grid/non-finite/`None`-map),
  `imaging_ray_object_origin` (first object-surface hit → surface-local x/y), `couple_imaging_records`
  (per record: `{record, object_x, object_y, irradiance}`).
* **`panels/main_path_detector_analysis.py`** — `_source_object_coupling_object_index` (auto-detect: first
  "Diffuse Object" / `DiffuseScatter` face, else first "Object Target") and
  `_illumination_weighted_detector_spot_samples` (computes the base via the **untouched**
  `_branch_detector_spot_samples`, builds the map, and multiplies each detector-record base weight by the
  sampled irradiance). Returns the coupled `weights` **plus** the un-coupled `base_weights` control and the
  per-ray `irradiance`. Returns the base unchanged (`coupling_applied=False`) when there is no object
  surface or the object gets no source light.
* **`services/analysis_reports.py`** — thin delegators to the panel methods.

The coupling **never** redefines the image plane / detector / optical axis (**bugs/0266**): it reuses the
exact base detector samples and only re-scales the display weight. It reads the **isolated** source records
(bugs/0272/0273), so evaluating it cannot disturb the object-driven imaging state.

## Verification

Guard `validate_open3d_source_object_coupling` (phase **241**), display-free and rayfile-free:

* **Synthetic sampler math (no trace)** — a hand-built peak-normalized map (bright centre, dark fold-X
  edges, uniform perp-Y): `sample_irradiance` reads the peak at centre (1.000), dark at the fold edge
  (0.254), bright at the perp edge (1.000), and **0.0** off-grid / non-finite / for a `None` map; nearest-bin
  is exact; `couple_imaging_records` multiplies base × irradiance and skips a record with no object origin.
* **Real trace on a portable coaxial-scatter fixture** — the coaxial area-LED layout with the FOV plane
  turned into a **Diffuse Object** (MIRROR base + built-in Lambertian, guided at an appended detector), driven
  by the built-in **"Random rectangle source"** (no OSRAM `.DAT`). Asserts: object index auto-detects (=2);
  the source → object map is asymmetric (fold **0.396** < perp **0.604**); coupling applies on ~961 imaging
  rays; coupled `weights == base_weights × irradiance` elementwise; the **coupled** detector image fold edge
  is dark (**0.268** ≤ 0.45) while perp stays uniform (**1.000** ≥ 0.80); coupling is **not a no-op** and
  **deepens** the fold dip versus the base (base fold **0.616** → coupled **0.268**, ≥ 0.15 margin).
* **bugs/0266 guardrail** — the coupled terminal geometry (x/y) and the un-coupled control weights are
  **byte-identical** to the untouched base detector samples (coupling changed only the weights, never the
  image plane); the object index (2) ≠ the detector index (3), so the object is never promoted to the image
  plane.

Deterministic and portable: the scene source is seeded (`source_seed`) and the Lambertian scatter
directions are a golden-angle **Fibonacci spiral** (no RNG), so any GitHub clone reproduces the exact
numbers with nothing to download (two runs gave identical metrics). Baseline updated in place (241 → pass).

## Notes

* **In-app eyeball owed (follow-up):** the coupled sampler is wired but not yet surfaced as a dedicated
  analysis mode. The natural next step is an **"Illumination-weighted image"** toggle in the detector-analysis
  panel that plots `_illumination_weighted_detector_spot_samples` (coupled) beside the plain spot — so the
  user *sees* the dark edges in the actual image, not just the overlay. Headless can't drive the embedded-VTK
  inspector.
* **Still deferred** (bugs/0270/0271): the emission footprint is an area-matched **disk** that over-sizes a
  rectangular face; per-face scatter-params dialog.
* **Option A** (unified scatter trace, exact truth-mode) remains the optional Stage-4 toggle in the design.
