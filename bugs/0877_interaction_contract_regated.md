# 0877 -- the embedded 3D interaction contract was never gated, and 23 of its checks had rotted

`validate_3d_interaction_contract.py` is a 258-check source contract covering the mouse bindings,
the STEP pick / carry / rotate / snap paths, the placement gizmos, the thickness dimensions, the
optical-axis guides and where every dialog lives. **It was never registered as a penta phase**, so
the gate has never run it. Nothing noticed when its assertions stopped describing the code.

Found while finishing 0876: it failed with 23 names, none of them caused by that work.

## What had rotted, and why

| check | what actually happened |
|---|---|
| fixed drag: constant sensitivity / preserves focal point / azimuth+elevation only | the pre-0206 implementation. Replaced **on purpose** by a rigid Rodrigues orbit that carries the view-up THROUGH the pole (flag 20260702_152020: the VTK path flipped 90° mid-drag and clamped at ±79°) |
| Coating / Diffuse / Beam Splitter / Error Map / Advanced Surface "lives outside layout_editor" | their fields moved into `row_forms/` during 0869-0873 -- the claim got *more* true while the assertion broke |
| STEP normal snap "defaults to surface-center" | the default anchor evolved `surface_center` → `pick_point` → `body_center`, so the body lands where you clicked |
| STEP promotion / placement acceptance | moved from the top-controls strip into `Open3DStepAdminPanel`; the button is "Promote STEP Row" now |
| thickness dimension click | now classified as `PickTarget.THICKNESS_DIMENSION` and handled by `ThicknessDimensionWidget` |
| thickness editor `grab_set` | asserted it was **absent**; it was added deliberately -- the embedded VTK canvas took focus-follows-mouse focus while the user typed, which is what made the editor vanish |
| hover badge `vtkTextActor` | `_update_hover_status` is timing-decorated; the real body is `_update_hover_status_impl` |
| internal face picking | `prefer_internal` grew a Beam-Splitter clause so a promoted cube's 45° diagonal still hovers |
| optical-axis highlight | `_set_optical_axis_highlight` is a one-line delegation to `SelectionRepresentation` |
| initial-refresh retrace | the `if requires_open3d_retrace:` branch gained `and not explicit_products` |
| launch family | bugs/0737 replaced "reaches the image" with "visible without clipping" so the Clipped toggle is honoured |
| axis guides | one chief ray is not enough for a beam splitter -- the guides now keep one representative per distinct fold direction |
| escaped-ray colour | the opacity ladder gained a `missed_detector` rung; the string match broke, the claim did not |
| placement drag | a translate previews with cheap actor transforms and commits once at release (bugs/0012) |

**Two assertions were matching the code's own comments.** `"translate_scene_row_pose" not in
placement_drag` matched the comment explaining why it is *not* called per drag step, and my first
replacement for the drag check asserted `"OrthogonalizeViewUp" not in rotation` against a
docstring that says "do NOT OrthogonalizeViewUp here". That is exactly the trap in
`feedback_guards_assert_claims_not_calls`, hit from both sides in one bug.

## Where the implementation was superseded, the check now MEASURES

Re-pointing a string at its new home keeps a source contract honest only while the source looks
the same. For the two checks whose implementation was genuinely replaced, the assertion now
computes the claim:

- `_fixed_drag_orbit_behaviour()` calls `Kraken3DInspector._orbit_camera_pose` and measures that
  100 px turns 10.0° and 200 px turns 20.0° (constant rate, linear), that `|pos - focal|` is
  unchanged (a rigid orbit, so the focal point cannot drift), and that 1200 px of vertical drag
  really turns 120° with a unit view-up still square to the view direction -- the ±79° clamp is
  gone and the frame is carried, not re-derived.
- the escaped-ray colour check calls `_ray_terminal_3d_style` with an unmistakable probe colour
  and asserts escaped keeps it while absorbed and stopped are recoloured.

## Gated from now on

`run_checks()` added (the harness wants `(passed, notes)`; `main()` keeps printing), registered as
**penta phase 655**. 258 checks pass.

## Files

- `KrakenOS/UI/validate_3d_interaction_contract.py`
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` -- phase 655
