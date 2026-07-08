# DESIGN — Source + Object separation (illumination emits, object scatters)

**Status:** PROPOSAL, awaiting user decision on the coupling model (A vs B below). No code yet.
**Origin:** flag `flag_20260708_171116_895` on the MV-150 coaxial-LED scene + the follow-up discussion.
**Predecessors:** bugs/0263–0266 (the "Set as Illumination Source" arc); this is the next step (likely bug 0267+).

---

## The problem (what the user hit)

The user marked a CAD/STL face as an illumination source (the bugs/0264 ergonomic path) and got **no usable
feedback**:

1. The **Face Editor still shows the face as "Absorbing"** and offers **no "Illumination surface" option** in
   its function dropdown.
2. **No full-surface rays** flood off the marked face — *"The rays seem not changing. No additional full-surface
   rays from that surface."*

Root cause of the silence is two-fold:
* **Two disjoint systems.** An illumination source is a scene-level `SceneSource3D` in
  `layout_scene_source_specs` (keys `face_anchor_row`, `face_anchor_face_id`). A face's optical *function* is
  separate `OpticalSolidFaces` advanced-attr metadata that the Face Editor edits. They never talk, so the Face
  Editor cannot display or set "illumination".
* **The marker is deliberately non-emitting.** bugs/0266 made a face-bound marker a *display designation* that is
  excluded from every imaging launch (so it can't hijack the image plane/detector/axis). Today
  `create_illumination_source_at_face` (`services/source_modeling.py:777`) also hard-codes the emitter as a **2 mm
  collimated disk** (`radius=2.0`, `cone_deg=20`, `ray_count=400`) — so even if it did emit, it wouldn't look like
  a face-sized flood.

The user's framing: today the **object** is the emitter (imaging rays launch *from* the object plane, treated as
self-luminous). They want to **split** that into a real **Source** (emits) + an **Object** (scatters what the
source delivers) — the true MV-150 coaxial geometry (LED emits → object reflects → lens images).

---

## The headline: this is NOT a from-scratch architecture

The physics — *source emits → object scatters → lens images the scattered light* — **already exists in the engine
and is proven end-to-end headless.** The "whole new architecture" is really an **authoring + interactive-preview
wiring** problem, not a ray-physics problem.

### What already works today

1. **Object-as-scatterer (the engine).** The core engine consumes an `advanced.DiffuseScatter` dict on a surface
   and spawns real non-sequential **scatter branches**:
   * `KrakenSys.py:2749` `__DiffuseScatterSettings(j)` — reads the per-surface config.
   * `KrakenSys.py:2884` / `:2889` `__NsTraceHasDiffuseScatter` — non-seq gate (scatter forces non-sequential,
     same as a deterministic beam-splitter).
   * `KrakenSys.py:4287` — the scatter trace itself (spawns `sample_count` child branches; each branch power ≈
     `reflectance / sample_count`; `BRANCH_PATH` gets "/scatter").
   * Models available in `scatter_backend.py`: **Lambertian, Oren-Nayar, cosine-lobe, and full PyScatMech BSDF.**
2. **The "Diffuse Object" surface pattern (proven layout).** `common_optical_layouts/diffuse_object_lambertian_scatter.py`
   uses a surface literally named `"Diffuse Object"` with `glass="MIRROR"` + `advanced.DiffuseScatter`
   (`reflectance=0.75, sample_count=9, model="Lambertian"`). Guard: `validate_diffuse_object_scatter.py` (+ oren_nayar
   / cosine_lobe / pyscatmech variants). This is the user's *"assign a diffuse or mirror surface so it reflects
   accordingly"* — it already exists as a role.
3. **Source→Object→Detector as one path.** `machine_vision_150mm_coaxial_led.py` (+ `_folded`) and
   `zemax_led_beam_splitter_imaging.py` already trace a real LED through a beam-splitter onto a target,
   non-sequentially.
4. **Irradiance at the object (measurement).** The bugs/0259–0262 relative-illumination heatmap already bins
   source-ray hits at a target plane into a 2-D map (`source_illumination_analysis.py`).

So three-quarters of the "new architecture" is already built — at the **engine + headless-layout** level. The gap
is **exposing it in the interactive Open 3D UX and coupling it without breaking imaging conjugates**.

---

## Answering the user's two questions directly

* *"The ray should sample across the full surface, like object emission but bigger."* → **Yes** — Gap #1 is to
  size the emitter to the actual face polygon (area emission), replacing today's fixed 2 mm disk.
* *"If illumination takes the 'illuminating object' role, how do we handle the object? Assign a diffuse or mirror
  surface so it reflects accordingly?"* → **Exactly right.** The object is **demoted from emitter to scatterer**:
  it becomes a `"Diffuse Object"` scatter surface (Lambertian / Oren-Nayar / mirror / BSDF), and the existing
  engine spawns scatter branches toward the lens. Your instinct maps 1:1 onto the existing scatter role.

---

## The real gaps to build (UI + wiring, not physics)

1. **Full-surface emission** from a marked source face — area-sample the face polygon instead of a 2 mm disk;
   ray count/divergence authorable.
2. **Two new face roles on promoted CAD faces** in the Face Editor. Today the dropdown
   (`optical_solid_metadata.py:36-48`, `OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES`) has only
   *Unassigned / Uncoated / Full Reflecting / Partial Reflecting / Absorbing* — **no scatter, no illumination.**
   Add **"Illumination Source"** and **"Diffuse / Scatter Object"**, and bridge the SceneSource3D ↔ face-function
   metadata split so the Face Editor *confirms* the role (fixing the "still shows Absorbing / no option" symptom).
   Reuse `main_diffuse_scatter_dialog.py` for the scatter parameters.
3. **Interactive coupling** source → object-scatter → detector in the live preview — **without** illumination
   redefining the image plane / detector / optical axis (protect the bugs/0266 fix).

---

## The one real design choice: how illumination couples to imaging

* **(A) Unified non-seq trace.** The source's full-surface rays hit the Diffuse Object, scatter, and the survivors
  that reach the lens *are* the imaging rays. Most physically honest (display-follows-physics); the engine already
  supports it. **Cost:** scatter fan-out is expensive for a live preview, and something else must still define the
  optical axis / conjugates (the object is no longer the emitter).
* **(B) Two decoupled stages.** Stage 1: trace source→object, bin irradiance with the existing 0259–0262 heatmap.
  Stage 2: keep the object→lens imaging trace but **weight each imaging ray by the local irradiance** from Stage 1.
  Cheaper, reuses existing binning, conjugates stay trivial. **Cost:** it factorizes (illumination × imaging)
  instead of tracing one continuous path — a standard approximation, but an approximation.

### Recommendation

**Build B first; keep A as an optional "truth" mode.** In **both** cases, keep a lightweight object→lens **imaging
reference** (pupil/field) that *defines* conjugates / axis / detector, and run illumination **additively** for
photometry. That is exactly the separation bugs/0266 established (marker excluded from imaging launches), so it
protects the fix and gives the visible win (full-surface rays + irradiance-weighted image) fast, before paying for
full scatter fan-out in the live preview.

---

## Staged delivery

1. **Full-surface emission + Face Editor feedback** — mark a face, *see* rays flood off the whole surface, editor
   confirms the role. (Directly answers the user's complaint.)
2. **"Diffuse / Scatter Object" face role** — wire the existing `DiffuseScatter` / `main_diffuse_scatter_dialog.py`
   onto promoted CAD faces.
3. **Coupling (Option B)** — irradiance-weighted imaging; the dark-edge rolloff then appears in the actual image,
   not just the overlay.
4. **(Optional) Option A truth-mode toggle** — full unified scatter trace for validation.

Stages 1–2 (the authoring UI) are needed for either coupling model, so they're not wasted whichever way A vs B
lands.

**Main tradeoff:** B ships visible feedback quickly and reuses everything but is a factorized approximation; A is
exact but expensive and needs the conjugate-reference discipline to stay live-preview-friendly.

---

## Guardrails to preserve

* **bugs/0266** — illumination must never define the imaging image plane / detector / optical axis. The
  `scene_source_spec_is_face_bound_marker` predicate + the imaging-launch exclusions stay. Any new emission path
  must be **additive**, not a replacement of the imaging trace.
* **Display follows physics** (standing feedback) — draw the flood rays from the *same* transform the trace uses;
  no synthetic cartoon cone.
* **Standing workflow** — when this becomes code: document under `bugs/00XX`, display-free guard exposing
  `run_checks() -> (bool, list[str])`, add penta phase (next = 236), regen `tools/penta_validator_baseline.json`
  surgically, one commit per bug (`Open 3D: … (00XX)`), push to `nonseq-display-refactor`, end with the status
  table. In-app eyeball owed (headless can't drive the embedded-VTK inspector).

---

## Key file references (verified 2026-07-08)

* `services/source_modeling.py:706-794` — `create_illumination_source_at_face` (2 mm disk today → needs full-surface).
* `KrakenOS/scatter_backend.py` — Lambertian / Oren-Nayar / cosine-lobe / PyScatMech backends.
* `KrakenOS/KrakenSys.py:2749, 2884, 4287` — DiffuseScatter settings, non-seq gate, scatter trace.
* `KrakenOS/common_optical_layouts/diffuse_object_lambertian_scatter.py` — "Diffuse Object" MIRROR + DiffuseScatter.
* `KrakenOS/common_optical_layouts/machine_vision_150mm_coaxial_led.py` (+ `_folded`),
  `zemax_led_beam_splitter_imaging.py` — real LED→BS→target layouts.
* `KrakenOS/UI/optical_solid_metadata.py:36-48` — the promoted-face function dropdown (the gap: no scatter/illum).
* `KrakenOS/UI/panels/main_optical_solid_face_roles_dialog.py:~401` — the Face Editor function combobox.
* `KrakenOS/UI/main_diffuse_scatter_dialog.py` — existing scatter-parameter dialog to reuse.
* `KrakenOS/UI/source_illumination_analysis.py` — the 0259–0262 irradiance binning to reuse for Stage 1.
* `KrakenOS/UI/services/trace_preview.py:38-97` — `_trace_preview_rays` early-return (the bugs/0266 hinge).

## Open decision for the user (resume here)

Pick the coupling model — **A (unified scatter trace)** vs **B (irradiance-weighted, recommended)** — or approve
"B first, A later." Then scope Stage 1 into bug 0267 (full-surface emission + Face Editor feedback).
