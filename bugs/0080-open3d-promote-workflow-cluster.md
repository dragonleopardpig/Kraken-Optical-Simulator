# 0080 — Open 3D: beam-splitter promote-workflow cluster (focus-earlier, 45° pick unstable, direct-assign placement, no split)

## Symptoms (user, recordings `flag_20260613_2201xx`–`2204xx`)

> [220211] Right click "Promote to Optical Element" won't work, not face editor pop up.
> [220325] after direct assigning the partial reflecting surface by right clicking
> (every time I selected the 45 degree surface, right click will change to another
> surface, please make it permanent during right click).
> [220452, + follow-up] after clicking Show Rays … the ray not splitting at the
> beam splitter, the ray go pass the detector … some rays missed the aperture in
> the lens surrogate … the ray focus earlier, not later from the image detector.

State (220452): row 6 = the cube, `desp_z = −367`, thickness 55, on-axis; `ray_actor_count=729`, **one branch** (no split); image row at z≈645.8.

## Physics framing

A plane-parallel plate displaces the image by `Δ = t·(1 − 1/n)` **downstream
(later)** — ~17 mm for 55 mm BK7 — independent of where it sits. "Focus **earlier**"
is the signature of the bug: the promote shoved the **detector** by the cube's
raw 55 mm (more than the 17 mm the focus moved), so the detector overshot the
focus → rays converge before it and pass through. Hold the detector fixed → the
focus is correctly ~17 mm later.

## Fixes

- **Direct-assign placement (extends bugs/0079):** the user reached the broken
  state via the *direct face-assign* right-click ("Promote and set …"), which
  called `promote_imported_step_to_optical_solid_row` WITHOUT
  `inpath_axial_placement` — so the detector got over-pushed (the
  `desp_z = −367`). `_promote_step_and_assign_face_function` now passes
  `inpath_axial_placement=True`, so the direct-assign path also gap-splits and
  holds the lens + image plane fixed. (The "rays miss the lens aperture" /
  "focus earlier" follow from the mis-placement and clear up with this.)
- **45° face pick is now stable (the user's "make it permanent"):**
  `step_feature_pick_for_display_xy` tried the VTK cell picker first, which
  returns the nearest EXTERNAL shell face of a translucent solid and varies
  pixel-to-pixel — so the internal 45° coating couldn't be reliably (re-)selected.
  For a clean solid (`<40` faces — a cube/prism, not a tessellated lens) it now
  prefers the DETERMINISTIC ray pick when that lands on an internal face; external
  hits and tessellated lenses still use the cell pick (no behaviour/perf change for
  them). Stable diagonal selection → the coating lands on the right face → the
  splitter splits.

## Still open — needs in-app diagnosis

- **[220211] "Promote to Optical Element" → no Face Editor.** The editor is
  scheduled at `promote_imported_step_to_optical_solid_row` line ~1251
  (`if open_face_editor: self.after(120, … open_optical_solid_face_role_editor)`),
  and the right-click routes through `_promote_step_from_context` →
  `promote_selected_step_to_optical_solid_row(open_face_editor=True)`. Could not
  reproduce headlessly (live Tk + render). **Need to know:** does it create a row
  (promote OK, editor just doesn't pop) or no row at all (promote fails)? The
  direct-assign right-click ("Promote and set Beam Splitter") is the working path
  and now carries the placement fix.

## Test

`validate_open3d_inpath_element_placement` (penta Phase 78) — added C5 (direct-assign
opts into in-path placement) + C6 (face pick prefers a deterministic internal-face
hit). Display-free; the rendered rays are confirmed in-app.
