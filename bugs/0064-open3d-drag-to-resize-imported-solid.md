# 0064 — Open 3D: resize an imported STEP solid (beam-splitter coupling)

## Reported (direct request)

> 1) I have downloaded a Cube Beam Splitter: 50x50x50mm
> 2) I want to quick modify it to 55x55x78mm
> 3) Add extrusion function to the imported STEP → click the highlighted surface
>    → drag the arrow → Thickness measurement grows → click mouse again to
>    confirm → direct edit the Thickness
> 4) Beam splitter make of two right angle prism, growing and shrinking must go
>    together.
> 5) User can then assign surface as usual optical element
> 6) Place it for example to overlap the LED, and they should glued together just
>    like the imaging Lens STEP glued to the surrogate lens.

The user wants to resize any imported solid, with a beam-splitter cube staying a
valid 45° splitter while doing so.

## Design decisions (confirmed with the user)

1. **Anchor** — the dragged face moves; the opposite face stays put (grow
   outward).
2. **All elements** — generic per-axis resize for any imported solid; the
   *coupled* 2-DOF mode auto-engages only for a detected beam-splitter.
3. **Auto-detect, user-overridable** — the coupling axes are detected; the user
   can override.
4. **Split ratio** — out of scope here; the default 50:50 lives in the existing
   face editor.

## Grounding (the real vendor part)

`attachment/prisms/Beam_Splitter/32704/step_32704.step` is **two right-angle
prisms** (2 solids), bbox **50×50×50**, and the cemented 45° coating faces have
normal **(1,1,0)/√2** — equal nonzero on two principal axes, ~0 on the third.

Two findings drive the implementation:

* **Coupling.** The 45° coating stays at 45° only when the two axes the diagonal
  spans (here X, Y) scale by the **same** factor; the third axis (Z, the coating
  extrusion direction) is free. So a splitter resizes with 2 DOF — a square
  **cross-section** + a free **depth** — which also makes "both prisms grow
  together" automatic (it is one shape scaled as a unit). `50³ → 55×55×78` holds
  the coating at `(0.707,0.707,0)`; a non-coupled `55×50×78` tilts it to
  `(0.673,0.74,0)`.
* **Mesh-space, not GTransform.** A non-uniform `BRepBuilderAPI_GTransform`
  silently degrades the analytic `Plane` faces to `BSpline`, which would hurt the
  face-role / analytic-fit heuristics. So the resize runs in **mesh space**
  (anchored per-axis vertex scale) — exact for box/prism solids, planar faces
  stay planar — while coupling **detection** reads the clean analytic planes off
  the *original* B-rep. The mesh-space inverse-transpose normal (`n/scales`
  renormalized) reproduces OCC's GTransform normal exactly.

## Implementation

### Geometry kernel — `KrakenOS/UI/services/open3d_solid_resize.py` (commit `bf9aa52`)
Pure, stateless: `detect_coupling` (B-rep 45° signature → `ResizeAxes`:
free axis + coupled pair), `extents_of`, `axis_scales_for_extents`,
`coupled_scales` (square cross-section + free depth), `anchor_point_for_fixed_face`,
`anchored_scale_matrix`, `resize_points`, `transform_normal`,
`is_coating_preserved`.

### Overlay + promotion wiring — `scene_placement_commands.py`, `layout_polyline_display.py`
* Per-overlay resize state in the solid's **native** frame:
  `_step_resize_for_label` / `_set_step_resize_for_label` (target extents +
  anchor axis + coupled flag), `_step_resize_signature` (cache key),
  `_step_overlay_resize_axes` (cached coupling detection),
  `_step_overlay_original_extents` (OCC bbox, popup prefill),
  `_apply_step_overlay_resize` (scales the loaded base mesh to the target before
  optical-axis alignment; strict no-op when unset).
* Each of the four `_transformed_imported_*_step_mesh` builders applies the
  resize after load and folds the resize signature into its memo key.
* **Promotion inherits the resize for free**: it meshes the *transformed*
  overlay, so the cached STL + `StepOverlayPromotion` bounds reflect the resized
  body; the setter invalidates the overlay face-metadata cache so promoted face
  centroids/normals track the resized geometry (step 5).
* **Glue (step 6)** reuses the existing placement/anchor metadata to overlap the
  body onto the LED — no new mechanism.

### Trigger — `open3d_inspector.py`, `open3d_face_assignment.py`
The imported-STEP right-click menu gains **Resize Solid…**, opening a popup
(`_open_step_overlay_resize_popup`): a detected splitter shows a single square
**Cross-section** + free **Depth**; any other solid shows independent
**Width × Height × Depth**, prefilled from current dimensions.
`_apply_step_overlay_resize_solve` captures history, sets the spec, and retraces.
This is the "direct edit the thickness" box from step 3.

## Tests
* `validate_open3d_solid_resize.py` — geometry kernel, 15 checks (incl. 3 against
  the real vendor STEP, skip-if-absent for portability).
* `validate_open3d_solid_resize_overlay.py` — overlay/promotion wiring + UI source
  contracts, 17 checks (set/get/signature, anchored apply, all 4 builders, vendor
  detection, the right-click "Resize Solid…" entry + popup + apply contracts).

## Status / follow-up
* **Done:** geometry kernel, overlay+promotion wiring, right-click "Resize Solid…"
  popup (testable end-to-end).
* **Next:** the drag-arrow gesture (click face → drag → live readout → confirm,
  routing into the same popup/apply); a render image-snapshot test; a penta phase
  + baseline; BRANCH_README + Sphinx manual entries.
* Verify undo/redo reverts a resize (the spec is set under a history capture; the
  capture's attribute coverage of `{label}_step_resize` needs a live check).

## Follow-up (testing fallout)

Stress-testing the resize surfaced interrelated beam-splitter-workflow issues:

* **Coating face not selectable** (in progress) — the 45° cement face between the
  two prisms is an interior duplicate face: `load_step_analytic_document` keeps it
  in `document.faces` (centroid 25,25,25, normal (1,1,0)/√2) but with **zero
  triangles**, and emits only `outer_faces`, so it never becomes a row in the face
  editor table. Both metadata paths drop it (analytic = outer_faces only;
  clustering = `extract_surface` drops buried faces). Fix designed: recover the
  coating as a selectable face with synthesized triangles, gated on the coupling
  detection.

* **Off-beam promoted solid flipped the non-sequential trace** (FIXED, this
  commit) — user parked the promoted cube ~149 mm off-axis and the on-axis
  conjugate rays focused short of the detector with extra diverging rays. Root
  cause: in `trace_intent._trace_flags` the promoted solid fired two mode-flips
  just by existing off to the side — `Solid_3d_stl` (STL optical solid) and its
  `desp` decenter (off-axis geometry) — flipping the conventional finite-conjugate
  layout to non-sequential, whose launch no longer reproduced the conjugate. An
  off-beam solid never touches a ray, so its presence must not change the trace
  (North Star #1/#4). Fix: `_solid_is_off_beam` + an exemption in `_trace_flags`
  so an inert promoted solid whose lateral offset clears the system aperture by
  its own radius no longer contributes the STL/off-axis triggers. On-beam solids,
  real beam-splitters (`Beam Splitter` surface / `BeamSplitter` advanced), mirrors,
  tilted elements and physical sources are unaffected. Guard:
  `validate_open3d_offbeam_solid_trace_mode` (display-free, the mode DECISION;
  the rendered ray geometry is verified in-app). NOTE: the live ray render can't
  be verified headless (this machine-vision layout class SIGSEGVs the offscreen
  renderer), so the render is user-verified.
