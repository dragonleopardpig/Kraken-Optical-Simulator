# 0812 -- a guard must keep up with what it guards

User: "I sometimes see errors when you run validation but ignore them (previous known errors). Can you fix
them all?"

## Measured

After bugs/0810 restored the missing CAD caches, the census re-run left 48 penta phases failing. 11
of them fail before reaching any behaviour. Each guard builds a **double** of the editor or inspector
(a fake class, a `SimpleNamespace`, or an instance made with `__new__`), and a later production change
made the code under test call something the double never had.

| phase | guard | missing on the double | added by |
|---|---|---|---|
| 68 | `solid_resize_overlay` | `_step_overlay_mutation_signature` | 0143: re-apply skips invalidation when the pose did not change |
| 68 | same, source contract | "Resize Solid..." in `_show_surface_function_context_menu` | 0102: element verbs moved to `append_element_context_actions` |
| 68 | same, source contract | `refresh_from_editor` in the resize apply | the apply retraces through `_apply_model_change` |
| 123, 139 | `led_distance_glue_carry`, `object_led_distance_dialog` | `_carry_glued_scene_sources` | 0512: the glued emitter rides LED moves |
| 130 | `preset_view_squares_labels` | `_restore_sensor_isolation` | 0278: any preset leaves Normal-to-Sensor first |
| 148 | `navigation_cube_click` | `_viewport`, `_cell_signs`, `GetCellId`, the `sign` argument | pixel-square corner viewport; facet table; 0254 view-relative ISO |
| 250 | `add_illumination_source` | `_illumination_emitter_module_seed`, `_coaxial_illuminator_descriptor_from_module` | 0290, 0292 |
| 263 | `save_layout_button` | `_write_open3d_session_sidecar` | 0305: saving writes the 3D-session sidecar |
| 269 | `camera_coupling_persistence` | `_current_object_mode` | 0311: decouple resets the camera-pinned field |
| 294 | `step_selection_mode_toggle` | `_clear_selected_step_opening` | 0334: a face and an opening selection are exclusive |
| 296 | `opening_menu_add_bs` | `_add_clear_aperture_edge_menu_items` | 0379: edge-pick clear-aperture items |
| 477 | `0638_optical_axis_menu` | `open_inspection_part_dialog` | 0669: the axis menu opens the Inspection Part dialog |

Phase 148 also drives the live cube in the penta harness. Its wrapper around `_apply_orientation`
took two arguments where the widget now passes three, and it scanned the static viewport constant
instead of the live corner viewport.

No production code was wrong. Every one of these phases has reported a failure since its change
landed, and the "known failure" label hid it.

## Fix

Each double gains what production now calls:

* **Real methods where they exist.** Bound from the mixin, so the guard still exercises production
  code (68, 130, 250, 294, 296).
* **A recording stub where the real method would reach the disk or the scene.** The stub is then
  asserted:
  * 123: the -50 mm distance move carries glued emitters by (0, 0, -50), and a zero-shift move
    carries nothing;
  * 263: a successful save writes one sidecar next to the layout, and a cancelled save writes
    none;
  * 269: a legacy decouple resets the pinned Real Image Height to Object Height (new check P2d).
* **Source contracts follow the delegation** instead of a line that moved (68).

## Standalone guard

`validate_open3d_face_assignment_sampling_stability` (not a penta phase):

* the `__new__` inspector lacked `_placement_drag_state`;
* the fake `_build_preview_system_rays_bundle` lacked `trace_rays` (0400);
* the Machine Vision check did not ask for rays after the fast load (0646/0718 defer the trace until
  the user asks);
* it expected `world_envelope` where a sequential lens now draws `display_slice` (0203's rule; both
  are flat 2D fans);
* two source contracts had moved (`refresh_from_editor(force_retrace=..., geometry_changed=True)`,
  `_set_step_hover_outline_impl`).

It then reaches a **real finding**, left open:
`_validate_world_envelope_survives_off_axis_step_promotion`. On the default layout (Object, Image, no
lens), promoting a prism placed 42 mm off axis moves the collimated launch by 44.27 mm (y -1.6 ->
42.66); directions are unchanged. The Auto analysis surface is the narrowest intermediate row
(`_analysis_surface_index`), so the off-beam prism becomes the reference that
`_center_infinity_bundle_on_launch_reference` centres the beam on. This needs its own bug.

## Verified

The 11 phases pass one at a time in the penta harness (68, 123, 130, 139, 148, 250, 263, 269, 294, 296,
477). Before this change each failed on the missing attribute or signature.

## Second batch: source contracts that followed a refactor

| phase | guard | what moved | by |
|---|---|---|---|
| 147 | `navigation_cube` | the cube is chamfered PolyData from Points; there is no `vtkCubeSource` | 0249 |
| 226 | `nav_cube_hover` | `roll_specs` values are `(start, end)`; the guard read `v[3] - v[2]` | 0249 |
| 257 | `datasheet_lens_import` | the menu label is now "Import Lens from Folder (replaces scene)..." | 0381 |
| 299 | `context_menu_focus_restore` | the dismiss checks `grab_current()` before taking focus; the fake had none | 0348 |
| 440 | `0565_model_designation_lens` | the labelled-row and designation parsing moved to `_cardinals_from_text` | 0787 |

For each, the check now follows the current code:

* 147 requires the PolyData/Points classes;
* 226 reads the last two numbers of each spec;
* 257 matches the entry and its command, not one exact label;
* 440 checks both hops: the routing, and the labelled-before-designation order.

299 also gains check 1b: while a dialog holds the grab, a dismiss leaves focus with the dialog.

Phases 147, 226, 257, 299 and 440 pass in the penta harness.

## Third batch: the folded RA-mirror family, where the DESIGN moved

Five folded phases encoded contracts that later bugs deliberately replaced. The product is right; each
check now states the current contract and, where the old expectation had a point, keeps it as a
separate check.

| phase | what the check pinned | what the code does now |
|---|---|---|
| 181 | the folded cone carries >= 100 on-axis rays | bugs/0410 CAPS the folded preview's ray count (default 10) so the trace stays snappy: 81 launched, 65 through |
| 203 B | an identity fold transform yields no straight equivalent | bugs/0567: a promoted MIRROR row is a fold by construction, because a 0433-frozen scene reports no transform at all |
| 203 D | the AZ85 two-mirror detector sits at a coordinate measured in July | the scene has been re-saved since; the seat is the scene's own answer |
| 213 A | a folded Solve-for-Thickness MOVES the trailing mirror | bugs/0717-0719: it slides the LENS along its leg and leaves vendor hardware alone |
| 214, 261, 276 | 55 x 55 (54 mm) solves on the two-fold fixture | that field needs the lens +117.9 mm where 43.2 mm of room is left, so it is REFUSED with those numbers |

The checks now:

* **181** measures density against the scene's own launch -- the cone is dense when most of what it
  launches gets through (65 of 81), and the disk-not-fan and 3x-the-envelope checks are unchanged.
* **203** silences the bugs/0567 breadcrumb to test the transform gate on its own, adds B2 for the
  breadcrumb itself, and compares the detector with the folded Image seat the scene computes
  (detector == seat, 293 rays on it).
* **213** asserts what must hold either way: the mirror keeps its beam offset and the scene still
  images (477 rays on the sensor). The carry is still exercised by (B), where a segment split moves
  the arm 79 mm.
* **214** adds "OUT OF RANGE IS SAID": 55 x 55 is refused with the lens move it needs (117.91 mm), the
  room it has (43.22 mm) and Force FOV as the way to see the collision -- then runs the merged
  sequence at 32 x 32, the widest this fold delivers (35 x 35 needs 44.12 mm).
* **261** solves at 32 mm: |m| lands exactly on target with zero residual defocus and a 0.0 um spot.
* **276** solves at 32 mm and asserts the object-leg write lands in ONE row with no spill -- now the
  lens-side gap (row 2), since object -> mirror is fixed hardware.

Phases 181, 183, 185, 186, 189, 194, 202, 203, 213, 214, 261 and 276 all pass.

## Fourth batch: the illumination family, where the SCENE moved (and one starved measurement)

Eight illumination phases drive `attachment/machine_vision_150mm_test.py`. That scene has been
re-saved since these guards were written -- it now carries a **55 x 74 mm coaxial side LED**, where the
guards' own notes record it as `scene_sources: []`. Two production rules then apply and change what the
checks see:

* a **physical scene source REPLACES the imaging launch** (bugs/0680), so a scene with its own LED
  traces the flood, not the imaging chain -- no arm can reach the Image;
* the overlay prefers the **DIRECT density heatmap** whenever illumination reaches the sensor
  (bugs/0286), instead of the projection that three of these checks are about.

| phase | what it needed | fix |
|---|---|---|
| 251, 253, 254, 305 | the scene's optics with no source of their own | start from `layout_scene_source_specs = []`, so the source each check adds is the one under test |
| 253 | zero relayed samples for an object-plane LED | the scene's promoted beam splitter genuinely returns a little light (16 relayed against 173 direct): require DIRECT-dominated, not DIRECT-only |
| 251 | an arm stamped `reached_image` after the flood | there is none once the flood replaces the imaging launch: find the sensor's detector BY POSITION (the Image plane) and require it drawn and anchoring the heatmap |
| 255 | a drawn detector on a sequential row | the BS scene delivers the sensor as the transmit ARM's detector (row >= 100000) sitting on the Image plane: identify it by position |
| 233 | the face-bound emitter aims OUTWARD | bugs/0269 made the default aim INWARD (light into the solid, the BS coupling case); the check now asserts inward AND that `aim="outward"` is its opposite |
| 307 | a 2-ring cone loft | bugs/0419 samples the loft along the axis (41 rings) so a folded display can crease it; the check reads `axial_rings`, the end rings and the even spacing |

**241 was a starved measurement, not drift.** Its fixture traces an 800-ray LED through
`_trace_preview_rays` without `full_count_sources`, so bugs/0590's interactive 200-ray cap trimmed it:
the source -> object irradiance map came out as ~294 scattered hits over +-50 mm and the coupling had no
signal to act on (fold 0.375 -> 0.375). With the opt-out the same fixture gives 1242 irradiance hits and
the coupling deepens the fold dip **0.616 -> 0.268** while the perpendicular axis stays uniform at
**1.000** -- exactly what bugs/0274 built it to do.

Measured after the fixes: 253's LED footprint reads half **4.99 mm** (the 10 mm LED), imaged to a patch
lighting **5%** of the 23 mm sensor with a dark rim, where the old 0286 rescale lit 33%; 254's
module-seeded emitter lights **100%** against the bare panel's 5%.

Phases 233, 241, 251, 253, 254, 255, 305 and 307 pass.

## Fifth batch: the early interaction phases (0-40), where the INTERACTION moved

These run in sequence on one live app, so they must be judged in that sequence -- run alone, phase 6
finds no rows to edit and phase 10 frames a different scene. In sequence, six failed.

| phase | what it pinned | what the code does now |
|---|---|---|
| 1, 2 | arming a STEP draws rotation handles | bugs/0338 made the gizmo OPT-IN: arming selects, the handles appear while the toolbar's Move/Rotate-whole-body checkbox is ticked |
| 6 | a 5 mm thickness edit slides the next row 5 mm | the first Standard row here is a promoted BALL lens's S1, whose thickness IS the ball's diameter: growing it draws a clipped S2 cap |
| 10 | the selected lens fills > 500 pink pixels | the pink fill was correct; the ball rendered ~20 px wide at the frame's edge (289 px) |
| 18 | a 6-step drag moves 6 handle steps | a translate slide is SMOOTH (pixels * step / pixels-per-step = 11.892 mm, not 6 x 1.784) |
| 36 | Field Samples = 1 launches only the object centre | bugs/0522 adds four COMPULSORY FOV-corner probes |
| 39 | loading a layout auto-fills the field to cover the sensor | bugs/0673: a layout SAVED with an authored field keeps it (this one has carried 11.52 since April) |

The checks now:

* **1** ticks the checkbox as a user would AND asserts the gate: with it off, no handles draw.
* **2** ticks it once per fixture.
* **6** edits 1 mm, asserts the model's own station follows EXACTLY (1.0000 mm), and for two rows of the
  same glass element requires the drawn row to follow the edit's direction (the cap is re-cut).
* **10** frames the selected body before counting: 61103 pink pixels, 6 red.
* **18** expects the smooth slide and records `pixels_per_step` (18.0) with it.
* **36** requires the object centre plus at most the four FOV corners.
* **39** asserts the authored field survives the load (11.52 / aperture 25), then picks the camera as a
  user does and requires coverage (16.2917 / 32.5835).

Phases 0-40 pass in sequence.
