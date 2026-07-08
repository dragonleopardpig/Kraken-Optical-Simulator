# 0268 — Face Editor exposes + reflects the "Illumination Source" role

User flag `flag_20260708_171116_895` (the other half, after 0267's emission):

> *"direct assignment on the surface, not sure whether it is working. So I open up face editor. Found that it
> is still Absorbing. Check the drop down option, there is no Illumination surface in Face Editor."*

Marking a CAD/STL face as an illumination source (bugs/0264) is invisible in the **Face Editor**: the face
still shows its coating (e.g. "Absorbing"), and the function dropdown has no "Illumination Source" option.
The two systems never talked — illumination is a scene-level `SceneSource3D` (`layout_scene_source_specs`,
keyed by `face_anchor_row` / `face_anchor_face_id`), while the face's optical function is separate
`OpticalSolidFaces` advanced-attr metadata edited by the dialog.

## Fix — a UI-only "Illumination Source" sentinel that bridges the two

`"Illumination Source"` is added to the Face Editor function dropdown (`OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES`)
as a **UI-only sentinel** — deliberately absent from the internal `VALUES` and the UI↔internal maps, so
`normalize_optical_solid_face_function()` maps it to the default if it ever reaches persistence (it is not a
coating). The dialog handles it specially:

* **Select "Illumination Source"** → intercepted at the top of `auto_apply_selected_face_identity` **before**
  the coating apply (which would else reset the face to Unassigned): it calls
  `create_illumination_source_at_face(row, face_id)` and refreshes. The face now floods full-surface emission
  (Overlays → "Illum emission", bugs/0267).
* **Select a real coating while a marker is bound** → `unbind_face_illumination_source(row, face_id)` first,
  then the normal coating apply runs.
* **Preselect** (`load_selected`) → if a marker is bound to the face, the dropdown shows "Illumination Source"
  instead of the underlying coating (closes the misleading "Absorbing").

Two new editor helpers (`services/source_modeling.py`):

* `face_bound_illumination_source_id(row, face_id)` — the reverse of `create_illumination_source_at_face`'s
  in-place-update lookup (returns the bound marker's `source_id`, or None).
* `unbind_face_illumination_source(row, face_id)` — removes the marker(s) for a face. Unlike
  `delete_scene_source_by_id` it has **no last-source floor** (an emptied scene-source list is fine — the
  imaging trace falls back to the pupil/field reference, bugs/0266).

## Why a sentinel, not a real coating token

Illumination is a **scene source**, orthogonal to the face's coating (a face can be, say, an uncoated glass
interface AND a marked emitter). Making "Illumination Source" a real coating token would conflate the two and
let the coating apply overwrite the face function. The sentinel keeps illumination in its own system
(`SceneSource3D`) while still surfacing it in the dropdown the user reached for.

## Verification

* **Display-free guard** `validate_open3d_face_illumination_dropdown` (`run_checks()`): METADATA (sentinel in
  the UI values + the combobox alias, NOT in the internal `VALUES` / UI↔internal maps, normalizes to default),
  WIRING (editor exposes the reverse-lookup + unbind; the dialog references the sentinel, binds via
  `create_illumination_source_at_face`, unbinds on change-away, preselects a bound marker), BEHAVIOUR
  (reverse-lookup exact row+face match; unbind drops only the marker + leaves other sources + is idempotent).
* **Phase 237** wraps the guard; `tools/penta_validator_baseline.json` updated (237 → pass). Siblings 0264
  (phase 233), 0266 (phase 235), 0267 (phase 236) re-verified — no regression.

## Notes

* **In-app eyeball owed:** headless can't drive the embedded-VTK Face Editor combobox. The user should open a
  promoted solid's Face Editor, pick "Illumination Source" for a face, confirm the emission floods (Overlays →
  "Illum emission") and the dropdown reflects "Illumination Source" on reselect; then pick a coating and
  confirm it unbinds.
* Together with bugs/0267 this closes flag `flag_20260708_171116_895` (visible emission + Face Editor
  confirmation). **Next — Stage 2/3:** the "Diffuse / Scatter Object" face role and the Option-B coupling that
  traces the illumination through the Object scatter onto the detector.
