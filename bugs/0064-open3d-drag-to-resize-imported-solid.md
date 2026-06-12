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
* `validate_open3d_resize_gesture.py` — pure gesture planner, 24 checks
  (face→axis/anchor/coupling, drag→clamped extent, the apply-ready tuple, live
  readout, purity, and a geometry-integration *killer*: feeds the plan through the
  real kernel on a synthetic cube and asserts the coating stays at 45° for a
  coupled drag while a single-axis change would break it). Penta Phase 70.

## Gesture step 3 — the drag-a-face planner (commit `f143bbd`)

Step 3's gesture (click face → drag arrow → live thickness readout → click to
confirm → direct-edit) is split into a **pure planning core** and a **live VTK
widget**, mirroring how the geometry kernel landed before the popup wiring.

`KrakenOS/UI/services/open3d_resize_gesture.py` is the pure core (no Tk/VTK/editor
state, so it unit-tests without a renderer — the live inspector SIGSEGVs headless).
`plan_face_drag(face_normal_native, resize_axes)` resolves the grabbed face into a
`ResizeDragPlan`: which native axis it grows (`dominant_axis`), which end is
anchored (the opposite/fixed face → `anchor_at_max = comps[axis] < 0`), and
splitter coupling (both diagonal axes in the target vs a free depth axis vs a plain
single axis). `resolve_resize_drag(...)` returns `(target_extents, anchor_axis,
anchor_at_max, coupled, new_extent)` — **exactly** the
`_apply_step_overlay_resize_solve` arguments plus the live-readout size — so the
live gesture and the numeric popup commit on **one** tested codepath.

## Status / follow-up
* **Done:** geometry kernel, overlay+promotion wiring, right-click "Resize Solid…"
  popup (testable end-to-end), and the **pure gesture planner** (`f143bbd`, Phase 70).
* **Next (in-app confirmed):** the live arrow-handle widget — a new
  `PickTarget`/`AbstractWidget` + hold-drag that draws the grabbed-face arrow, calls
  `resolve_resize_drag` each motion for the live readout, and on release routes the
  resolved tuple into the existing popup/apply (the small seam:
  `_apply_step_overlay_resize_solve(..., anchor_at_max=…)` passthrough so a −axis
  grab can hold the +axis face, + a `prefill_extents` arg on
  `_open_step_overlay_resize_popup`). This is live VTK, unverifiable headless.
* **Docs:** BRANCH_README + Sphinx manual entries for the resize/coating/off-beam arc.
* Verify undo/redo reverts a resize (the spec is set under a history capture; the
  capture's attribute coverage of `{label}_step_resize` needs a live check).

## Follow-up — beam-splitter coating selectable (testing fallout, DONE)

After promoting the resized cube, the face-editor table had **no row for the
center 45° coating**, so the user could not assign the splitter coating (step 5).

Root cause: a cube beam-splitter is two cemented right-angle prisms; the 45°
coating is an **interior duplicate** face. `load_step_analytic_document` kept it in
`document.faces` (centroid (25,25,25), normal (1,1,0)/√2) but with **zero
triangles** and excluded it from `document.outer_faces`, so it never became a face
record / table row (both metadata paths drop it — analytic = `outer_faces` only;
clustering = `extract_surface` drops buried faces). It also sits inside the body,
so it is not clickable from outside.

Fix: `_is_recoverable_interior_coating` + a recovery in `load_step_analytic_document`
force-includes **one** *oblique* (non axis-aligned) interior coating per duplicate
group as a real, tessellated `outer_faces` entry tagged `recovered_coating=True`
(preserved through `normalize_optical_solid_face_metadata`). It flows uniformly to
the face-tagged display mesh and the face-role metadata, so it appears as a
selectable `Unassigned` row with real geometry; the user assigns it `Beam Splitter`.
Tightly gated — axis-perpendicular doublet cement (normal ~(0,0,1)) is **not**
oblique, and single-solid prisms have no interior duplicate, so both are untouched
(verified on the real doublet + penta parts). Guard:
`validate_open3d_beam_splitter_coating_recovered` (11 checks, display-free, real
parts skip-if-absent).

**Stale-cache gotcha:** the analytic display mesh is cached on disk
(`…analytic.vtp`, keyed by source path + mtime, *not* code version), and
`_load_step_mesh` reads it before the document loader runs — so the first test
still showed no coating (the cube's cache predated the fix). Fixed by versioning
the cache: `_ANALYTIC_MESH_CACHE_VERSION` ("v2") is folded into
`_cached_analytic_cad_mesh_path`, so a geometry-pipeline change regenerates stale
caches instead of silently reusing them. **An already-promoted row keeps its baked
`OpticalSolidFaces` metadata, so the existing row must be re-promoted** (delete +
re-import + promote) to pick up the recovered coating; future imports/promotes get
it automatically.

## Follow-up — off-beam non-sequential trace (RESOLVED → bugs/0065)

User parked the promoted cube off the beam path and the on-axis rays went wrong
(focus short of the detector + diverging). First attempt (commit `02323d2`)
exempted off-beam solids from the non-seq mode triggers in `trace_intent`; it
*engaged* (layout went sequential) but regressed to "rays stop half way" — a
promoted **solid** parked off-axis becomes a vignetting thin surface in the
sequential path. Reverted (`01a7743`). Real cause: a promoted off-beam solid
should be a **display-only scene body** outside the optical trace path (not a
sequential surface, not a non-seq launch perturbation) until it is on the beam or
coated.

**Resolved in bugs/0065.** The leak was the solid's lateral decenter
(`desp_x`/`desp_y`) copied verbatim onto `surface.DespX`/`DespY` in
`_build_system_from_specs` as a *propagating* coordinate break, dragging the
off-axis cube into the centered prescription. The fix
(`services/offbeam_optical_solid.neutralize_offbeam_inert_solids`, called at the
top of `_build_system_from_specs`) replaces each off-beam inert promoted solid
with a flat zero-power AIR surface at the on-axis station — zero optical effect,
the 3-D body still draws. See `bugs/0065-open3d-offbeam-promoted-solid-display-only.md`,
guard `validate_open3d_offbeam_solid_display_only` (18 checks), penta Phase 66.
The live ray render still can't be confirmed headless (SIGSEGV); pinned by the
display-free prescription guard, user confirms in-app.
