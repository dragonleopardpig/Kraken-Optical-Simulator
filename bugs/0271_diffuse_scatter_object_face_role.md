# 0271 — "Diffuse / Scatter Object" role on promoted CAD faces (Stage 2)

Stage 2 of the Source+Object separation (`bugs/DESIGN_source_object_separation.md`): let a promoted CAD/STL
solid face be marked as a **diffuse scatterer**, so the object demotes from emitter to scatterer. The
non-sequential scatter engine (Lambertian / Oren-Nayar / Cosine-Lobe / PyScatMech BSDF) already existed but only
at the **row/surface level** ("Diffuse Object" surface); an in-code tooltip said it was *"not wired on imported
CAD faces yet; use a Diffuse Object row."* This wires it to a face.

## Approach — mirror the Beam Splitter face-role pattern

Unlike the illumination sentinels (a scene source, not a coating), diffuse scatter is a **real per-face optical
interaction**, so it is a genuine internal function consumed at trace time via the per-face override — exactly
how a Beam Splitter face works.

* **Metadata** (`optical_solid_metadata.py`) — a real internal `"Diffuse Scatter"` value in
  `OPTICAL_SOLID_FACE_FUNCTION_VALUES`, UI label `"Diffuse / Scatter Object"` in the dropdown (+ combobox
  alias), a two-way UI↔internal map, a role color, and a preserved per-face `diffuse_scatter` settings dict.
  Because it is a real mapped value, selecting it in the Face Editor dropdown flows through the **normal apply
  path** — no sentinel interception (contrast the illumination role).
* **Build** (`layout_editor.py`) — `resolve_optical_solid_face_diffuse_scatter_for_face(face)` normalizes a
  scatter face's settings (default `DIFFUSE_SCATTER_DEFAULT_SETTINGS` when unauthored, None for a non-scatter
  face — the additive contract), and the promoted-solid build loop lands them on
  `surface.OpticalSolidFaceDiffuseScatter = {face_id: settings}` (alongside `OpticalSolidFaceCoatingTables`).
* **Trace** (`KrakenSys.py`) — five edits mirroring the beam-splitter path:
  * `__OpticalSolidFaceInteraction` carries the per-face scatter dict onto the `override` and sets
    `force_reflection` for a `Diffuse Scatter` face (an opaque scatterer — the parent reflects specularly and the
    scatter loop spawns the diffuse children, like the Diffuse Object MIRROR base).
  * `__DiffuseScatterSettings(j, face_override=None)` prefers the face override's settings over the surface-level
    `DiffuseScatter`.
  * the scatter loop calls `__DiffuseScatterSettings(j, face_override=face_override)`.
  * `__NsTraceHasDiffuseScatter` gains a per-face `OpticalSolidFaceDiffuseScatter` scan so the scene enters
    branching mode (else no scatter branches spawn).

## Verification

* **Display-free guard** `validate_optical_solid_face_scatter` (phase **239**): METADATA (real value + label +
  two-way map), RESOLVER (scatter → normalized default Lambertian, non-scatter → None, reflectance 0 → None,
  authored params honoured), BUILD (marking a face lands `surface.OpticalSolidFaceDiffuseScatter`), PHYSICS (a
  ray aimed at the marked face spawns exactly `sample_count` `/scatter` branches, power ==
  reflectance/sample_count), ADDITIVE (an Uncoated face spawns none). BUILD/PHYSICS SKIP without the STEP.
* Verified end-to-end: a marked prism face scatters **9 Lambertian branches** at power 0.0889 (= 0.8/9);
  Uncoated → none. Row-level `validate_diffuse_object_scatter` + `validate_optical_solid_face_coating` + the
  illumination-dropdown guard re-verified — no regression (the new `face_override` param defaults to None, so the
  surface-level path is untouched).

## Notes

* **Ships with default Lambertian params.** Marking a face "Diffuse / Scatter Object" scatters with the default
  settings (Lambertian, reflectance 0.8, 9 samples). **Deferred:** a per-face params editor — reuse
  `MainDiffuseScatterDialog` parameterized for a `(row, face_id)` target (write the candidate into the face
  record's `diffuse_scatter` instead of `row.advanced`), plus a "Scatter…" button in the Face Editor. Until then
  the params are default-only.
* **In-app eyeball owed:** mark a promoted-solid face "Diffuse / Scatter Object" and confirm the trace scatters
  off it.
* **Next — Stage 3 (0272):** the Option-B coupling — trace the (0269/0270) illumination through this Object
  scatter onto the detector (irradiance-weighted).
