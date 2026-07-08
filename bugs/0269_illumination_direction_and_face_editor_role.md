# 0269 — illumination aims into the solid (default) + Face Editor shows the role

User flag `flag_20260708_201818_309` (testing bugs/0267 + bugs/0268 on the MV-150 coaxial scene) raised three
things:

> *"promoted to illumination source. There is an extra image/sensor. Is there a way to specify illumination
> direction? It should illuminate into the BS instead."*
> (+ follow-up) *"in the Face Editor pop up, after assigning the illumination source, the Left Table 'Function'
> column still showing 'Unassigned'."*

## (1) Illumination direction — aim INTO the solid (fixed)

`create_illumination_source_at_face` (and the per-trace `resync_face_bound_scene_sources`) always aimed the
emission **outward** (away from the solid body centre, bugs/0264). So marking a beam-splitter face flooded the
emission into empty space instead of INTO the cube. The screenshot showed the cyan flood leaving the BS's
outer face into nothing.

Fix — a stored **aim** the create + resync both respect:

* `_face_aimed_normal(row, origin, normal, aim)` — `outward` floods the scene (the 0264 behaviour); `inward`
  (the **default**) shines INTO the solid the face sits on — the coupling case (light into a BS cube → folds
  down to the FOV).
* `create_illumination_source_at_face(..., aim="inward")` records `face_anchor_aim` on the marker.
* `resync_face_bound_scene_sources` reads `face_anchor_aim` (default inward — legacy 0268 markers had none and
  are coupling into a solid) so it **never re-forces outward** the direction the user chose.
* Face Editor dropdown now offers **two** variants — **"Illumination Source (into solid)"** (default) and
  **"Illumination Source (outward)"** — and preselects the one matching the bound marker's aim. New helper
  `face_bound_illumination_aim(row, face_id)`.

So "is there a way to specify illumination direction?" → yes, pick the variant; and the default now points into
the BS, which is what the user wanted.

## (3) Face Editor left-table Function column showed "Unassigned" (fixed)

A face qualifies as a scene-source anchor via its *side/role* (`assigned_only=True` passes on any non-default
attribute), so its `function` can genuinely be "Unassigned" even while it is a valid, marked illumination
source. bugs/0268 fixed the combobox but not the left-table **tree** column, which reads the stored `function`.
Now `raw_tree_values` shows "Illumination Source (into solid / outward)" whenever a marker is bound to the face
(via `face_bound_illumination_aim`), instead of the masking "Unassigned".

## (2) The "extra image/sensor" — the beam-splitter reflected branch (explained, not a bug)

The second `Sensor 23.0×23.0` / `Image circle Ø32.6` near the BS + "Optical Axis 2" are the **imaging trace
branching at the beam splitter**: `derive_branch_detectors` (synthetic row base 100000) and the
`traced_chief_ray_segment` axis both come from the *imaging* rays (object → BS) splitting — a beam splitter
makes two images. It is **not** caused by the illumination marker: the marker is excluded from the imaging
trace (bugs/0266 holds — the real image is still correct at z=657, not relocated), and the 0267 emission is
render-only. The reflected branch is legitimate non-sequential physics (display follows physics). If the user
wants ghost/loss branches de-emphasised on the display, that is a separate feature (not done here).

## Verification

* **Display-free guard** `validate_open3d_face_illumination_direction` (`run_checks()`): METADATA (both aim
  variants in the UI values + combobox alias, NOT internal coating tokens, normalize to default), WIRING
  (create takes an aim + stores `face_anchor_aim`; resync consults it via `_face_aimed_normal`; the dialog
  offers the outward variant + preselects the aim), BINDING (inward aims INTO the body — `dot(dir, outward)<0`
  — outward away, aim stored + reported, **resync preserves it both ways**, default inward; SKIPs without the
  STEP fixture).
* **Phase 238** wraps the guard; `tools/penta_validator_baseline.json` updated (238 → pass). Siblings 0267
  (236), 0268 (237) re-verified — no regression (the label change rides on the constant).

## Notes

* **In-app eyeball owed:** open the promoted BS's Face Editor, pick "Illumination Source (into solid)" for the
  entry face → the cyan emission should now flood INTO the BS (Overlays → "Illum emission"), the left-table
  Function column should read "Illumination Source (into solid)", and re-opening should preselect it.
* The three illumination bugs (0267 emission, 0268 dropdown, 0269 direction + tree) complete the interactive
  authoring of a face illumination source. **Next — Stage 2 (0270):** the "Diffuse / Scatter Object" face role;
  **Stage 3 (0271):** the Option-B coupling that traces the (now correctly-aimed) illumination through the
  Object scatter onto the detector.
