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
