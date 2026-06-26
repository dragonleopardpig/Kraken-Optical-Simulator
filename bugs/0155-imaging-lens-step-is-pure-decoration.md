# 0155 — Imported "Lens" STEP should be a pure decoration like LED/Camera (+ rename to "Imaging Lens")

User report: *"I noticed that the imported Imaging Lens (via 'Lens'), the right click is
different from LED and Camera. I think all these 3 should be the same. They serve no
optical function. Perhaps rename to Imaging Lens instead of Lens. All with actual optical
functions import should be under Optical Element (UI have this now, please double check)."*

Refinement: *"yes, make the lens a pure decoration, but with one synchronization: the
Imaging Lens STEP provided by vendor, surrogate built by us, the front Datum and Rear
Datum should match the Lens STEP, that is the only synchronization we need to make
although it is decoration. Just like the Camera STEP, the virtual detector size and
location should match and glue to the Camera STEP although it is decoration."*

## Symptom

The four STEP-overlay import kinds (`lens`, `optical`, `led`, `camera`) shared one
right-click menu builder, but only `led` and `camera` were registered as decorations.
So the imported **Lens** overlay uniquely still offered **"Promote to Optical Element"**
(and the optical face-assignment path), while LED/Camera did not — an inconsistent menu
for three CAD props that all "serve no optical function." The genuine optical-function
import already had its own path ("Optical Element", label `optical`).

## Root cause

A single gate, `is_step_overlay_decoration(label)` (step_overlay_labels.py), drove every
"this overlay is not an optical element" decision (Promote menu item, promote-from-context,
face-assign-from-context, the shared UI promote wrapper, and thickness-dimension carving).
Its set was `("led", "camera")`, so `lens` fell through to the promotable branch.

The "optical function" import the user asked to confirm **already exists** as the
`optical` kind — three entry points: File ▸ "Import Optical CAD/STL Solid…", the 3D
toolbar "Import Optical STEP…", and the Scene panel "Optical" button — all stamping
`_selected_step_label="optical"` and reaching the real promote/Face-Editor/non-seq path.

## Fix

* **Decoration set** (`step_overlay_labels.py`): add `lens` →
  `STEP_OVERLAY_DECORATION_LABELS = ("led", "camera", "lens")`. This is UI-layer policy:
  the lens menu now drops "Promote to Optical Element" and the optical face-assignment,
  exactly matching LED/Camera. The gate is consulted only by the UI/menu/carve layer, so
  the *service* methods `promote_imported_step_to_optical_solid_row` /
  `promote_imported_step_to_native_surface_rows` (label-agnostic mechanism) are unchanged
  and their validators keep passing.

* **The one synchronization is preserved untouched.** "Glue STEP to Surrogate" is added
  for every label *before* the decoration gate in `append_element_context_actions`, so the
  lens keeps it. It runs `glue_selected_step_to_surrogate()` which:
  * re-pins the surrogate **Front Datum** onto the STEP front face
    (`glue_step_overlay_to_surrogate` → `target_front_z=_lens_front_datum_z()`), and
  * moves the surrogate **Rear Datum** onto the STEP rear face
    (`improve_lens_surrogate_rear_to_step`) so the surrogate span matches the vendor CAD.

  This is the lens analogue of the camera's detector-size/location glue: the decoration is
  vendor truth, the native surrogate is what actually traces, and the only thing kept in
  sync is the front/rear datum.

* **Rename "Lens" → "Imaging Lens"** in the user-facing import labels (File menu, 3D
  toolbar Import STEP submenu, Scene panel button, import dialog title + display label,
  and the Scene-tree source name). The native prescription items ("Lens Drawing Surface
  Properties…", "Export Lens Drawing…", "Thin Lens", lens-row group labels) are left
  alone — those are not the decorative vendor import. The Scene browser category was
  already "Imaging Lens".

## Guard

`KrakenOS/UI/validate_open3d_imaging_lens_decoration.py` (penta phase 146) — display-free
on a tk-free fake editor + a label-collecting fake menu:

* `is_step_overlay_decoration("lens")` is True, `("optical")` is False;
* the real `append_element_context_actions` menu for `lens`/`led`/`camera` has **no**
  "Promote to Optical Element" while `optical` keeps it; `lens` keeps "Glue STEP to
  Surrogate" + "Resize Solid…";
* display label `_step_overlay_display_label("lens") == "Imaging Lens"` and the
  `import_lens_step` default `display_label == "Imaging Lens STEP"`;
* source-pin: `_glue_step_to_surrogate_from_context` calls
  `glue_selected_step_to_surrogate`, which calls both `glue_step_overlay_to_surrogate`
  (front datum) and `improve_lens_surrogate_rear_to_step` (rear datum).

`validate_open3d_decoration_not_promotable.py` was extended: the decoration set assertion
is now `{"led","camera","lens"}`, only `optical` stays promotable, and a new behavioral
check confirms the lens "Promote to Optical Element" path is blocked.

## Notes

* The decoration gate is **UI-layer only**, so the service-level promote validators
  (`validate_step_promotion_optical_solid`, `validate_step_native_promotion`) that promote
  a `lens`-labelled fixture keep passing — they exercise the placement math, not the menu
  policy.
* The thickness-carving path consults the same gate, so a lone Imaging Lens overlay no
  longer carves an optical thickness dimension by itself; the native surrogate rows (the
  real optical element) carry the optics and carve. (`validate_open3d_thickness_overlay_skips_lens_snapshot`
  and `validate_open3d_row_actions_parity` were already RED on this branch for unrelated
  render/source reasons — verified identical on the pre-change tree via a stash A/B.)
* In-app eyeball owed: the right-click menu shape + the surrogate datum glue render through
  the embedded VTK canvas, which the headless harness can't drive.
