# Bug tracking

User-flagged bugs in the KrakenOS Open 3D inspector get a numbered record
here, fixed, pinned with a small targeted test, and folded into the
comprehensive penta-telescope regression validator.

## Workflow (per bug)

1. **Document** — add `NNNN-short-slug.md` (next free number, see the
   register below). Capture: symptom (the user's own words), the in-app
   repro bundle it came from, root cause, the fix (files + line refs), the
   test that pins it, and which validator phase now guards it.
2. **Fix** — make the change. Keep it minimal and root-cause, not a
   band-aid over the symptom.
3. **Test immediately** — write a small, specific test that fails before
   the fix and passes after. Prefer a display-free unit test against the
   narrowest seam (e.g. a `@staticmethod` on a real VTK actor) so it runs
   without an X server. **For a *visual* bug (selection color, ghost /
   leftover actors, handles — anything about what the user sees), a
   property-only test is NOT sufficient:** it must also render the scene to
   a PNG (off-screen under Xvfb) and check pixels (e.g. "negligible red,
   pink fill present"), and the fixer must open that PNG and visually confirm
   it. The all-red fix (0001) passed every vtkProperty assertion yet a
   second actor still painted a red block (0002) — only a rendered image
   caught it.
4. **Integrate** — add a phase to
   `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` so the
   bug is re-checked end-to-end on the real penta-prism cascade (load,
   cascade one by one, select / unselect, observe optical axis). Then
   regenerate the pre-push gate baseline:
   `python tools/penta_validator_gate.py --update-baseline`.

## Where reproductions come from

Users flag bugs with the in-app event recorder
(`KrakenOS/UI/services/open3d_event_recorder.py`). Bundles land under
`attachment/recorded_bug_repros/flag_<timestamp>/` (gitignored): a
`description.txt` (the complaint), a `screenshot.png`, and a `state.json`
snapshot. Analyze the newest by mtime; correlate with the matching
`recording_<timestamp>.json` event log.

## Test layers

- **Unit / display-free** — `KrakenOS/UI/validate_open3d_<bug>.py`, run via
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_<bug>`.
- **Image-snapshot (visual bugs)** — `validate_open3d_<bug>_snapshot.py`
  renders the real scene to a PNG and counts pixels; it boots its own Xvfb
  when `DISPLAY` is unset. Inspect the PNG by eye, not just the counts.
- **Regression / end-to-end** — a numbered phase in
  `validate_open3d_penta_telescope_comprehensive.py`, gated on push by
  `.githooks/pre-push` -> `tools/penta_validator_gate.py` (boots Xvfb,
  blocks only on a PASS->FAIL flip vs `tools/penta_validator_baseline.json`).

## Register

| ID | Title | Status | Fix tests |
|----|-------|--------|-----------|
| [0001](0001-analytic-lens-selection-all-red.md) | Selecting an analytic lens renders solid red, no slide handle | Fixed | `validate_open3d_analytic_lens_select_not_all_red` + Phase 10 |
| [0002](0002-analytic-lens-selection-ghost-red-block.md) | Selected analytic lens leaves a "ghost red block"; slide-along-axis has no handle | Fixed (red block); slide-handle is a UX gap, not a bug | `validate_open3d_analytic_lens_selection_snapshot` + Phase 10 image check |
| [0003](0003-aspheric-achromat-many-faces-snapshot-key.md) | Aspheric achromat: "so many faces", `s` snapshot key dead in face editor, InvalidMeshWarning | Fixed (snapshot key + dialog-pixel capture, InvalidMeshWarning, all-red selection, 160-face display grouping, then root-cause OCC B-Rep import → 7 real faces) | `validate_open3d_step_promotion_mesh_warning_free`, `validate_open3d_optical_solid_face_grouping`, `validate_open3d_flag_dialog_capture`, `validate_open3d_brep_optical_solid_faces` (+ `_snapshot`) |
| [0004](0004-step-combined-move-rotate-gizmo.md) | "no slide handles" — combine rotate + translate into one Move/Rotate gizmo; arrows clear the arcs; free axial travel; live edge-gap readout | Fixed | `validate_step_rotation_handles`, `validate_open3d_step_translate_gap` + Phase 11 |
| [0005](0005-ghost-red-face-hover-edges.md) | "ghost red edges" — STEP face hover highlight painted red, reads edge-on as a red bar through the lens | Fixed (hover now uses shared gold accent) | `validate_open3d_step_face_hover_not_red` (+ `_snapshot`) + Phase 12 |
| [0006](0006-promoted-row-translate-arrows-shrink.md) | After promoting a STEP to an analytic lens, re-selecting it shrinks the big Move arrows to short grid stubs | Fixed (row gizmo sized off the body, shared length seam) | `validate_open3d_promoted_row_translate_arrow_length` (+ `_snapshot`) + Phase 13 |
| [0007](0007-thickness-dimension-on-optical-axis.md) | Thickness dimension label/arrow sits on the optical axis instead of offset to the side | Fixed (camera-aware offset into the screen plane, 8% margin like the 2D distance arrows) | `validate_open3d_thickness_dimension_offset` (+ `_snapshot`) + Phase 14 |
| [0008](0008-step-delete-clears-unselected-lens.md) | "lens element dissapear" — a stray Delete/BackSpace erased the imported lens with nothing selected | Fixed (delete-only label candidates drop the hardcoded "optical" fallback) | `validate_open3d_step_delete_requires_selection` (+ `_snapshot`) + Phase 15 |
| [0009](0009-thickness-overlay-skips-lens.md) | "thickness overlay skip the lens element" — persistent arrow measures straight through an imported lens; thicken both distances | Fixed (split row span around intervening overlays; refresh draws dimensions after the STEP bodies register; shared thicker line knobs) | `validate_open3d_thickness_overlay_skips_lens` (+ `_snapshot`) + Phase 16 |
| [0010](0010-ghost-yellow-face-highlights.md) | "ghost surfaces" — hover *edge* highlights stranded at the lens's old spot after Place→Center Row→Optical axis snaps the (aspheric) lens; re-light on hovering the now-empty region | Fixed (verified by user; resolved with the session's refresh-ordering/hover-clear changes + restart; recorder instrumentation kept as a tripwire) | recorder `stray_props_above_body` / `hover_outline_bounds` tripwire |
| [0011](0011-thickness-overlay-stale-after-move.md) | "Thickness overlay not auto-updated" — after a gizmo move the persistent `gap =` arrows keep the lens's old position; live readout is correct | Fixed (move commit does a full refresh when dimensions are shown, so they recompute at the new position) | `validate_open3d_thickness_overlay_live_update` + Phase 17 |
| [0012](0012-promoted-analytic-row-cant-slide.md) | "after changing to analytical lens, can't slide" — promoted optical-solid row fired a ~0.5 s retrace per drag step ("computes hard"); then handles lagged; then it reverted on release | Fixed (live cheap actor move of body+handles, defer the retrace to release; body centre tracks the live pose instead of the cached `center_world`) | `validate_open3d_promoted_row_slide`, `validate_open3d_saved_native_center_tracks_pose` + Phases 18, 19 |
| [0015](0015-terminal-element-rays-vanish.md) | "the ray still missing" — a beam splitter (any non-Image element) dropped on the **terminal** surface stripped its detector role, so the display filter silently dropped every traced ray | Fixed (final prescription surface is the terminal image plane regardless of optical type; physics/branching unchanged) | `validate_random_terminal_element_ray_display` + Phase 24 |
| [0016](0016-promoted-beam-splitter-cube-rays-vanish.md) | "the ray is still missing" — a promoted beam-splitter **cube** made every traced ray invisible (`ray_actor_count=0`); even all-Uncoated showed nothing | Fixed (promotion defaults faces to Uncoated not Absorber; display keeps every traced ray up to its terminal surface, only *un-folded* `escaped` gated by Show Clipped Rays — refined by 0018 so a deliberately folded reflect branch stays visible; analytic fit selects the flagged optical-axis pair so it doesn't over-count uncoated side walls) | `validate_open3d_traced_rays_always_visible` + Phase 25; `validate_open3d_promotion_auto_lens_faces`, `validate_open3d_promotion_analytic_fit` |
| [0017](0017-beam-splitter-cube-transmit-and-second-axis.md) | "ray transmitting stop right at the imaging lens entrance" + reflected branch had no optical axis | Fixed (an inferred straight-through cube exit no longer snaps the downstream Image plane onto the cube face in front of the lens; the traced-axis builder emits one axis per distinct fold direction so the reflected branch earns Optical Axis 2) | `validate_open3d_beam_splitter_transmit_and_second_axis` + Phase 26 |
| [0018](0018-reflected-branch-detector-plane-runaway.md) | "rays exit still bent" → then "where is the beam splitter 2nd path ray?" — reflected branch first rendered as a bent diagonal band (2D collapsed to a dot), then *vanished* after the first fix | Fixed twice: (1) the escaped-ray detector-plane projector force-landed grazing reflected rays ~6×10⁵ mm off-axis — now a ray must head within cos 80° of the plane normal before projecting, so the +X fold keeps its sane ~232 mm length; (2) that reclassified the fold `escaped`, which the 3D filter hides with Show Clipped Rays OFF — now an escaped ray that was folded by non-refractive steering (reflect/split/mirror/TIR) stays visible, so the 2nd path renders | `validate_open3d_reflected_branch_detector_bounds` (+ display-filter guards) + Phase 27 |
| [0044](0044-wavefront-3d-real-surface.md) | *Enhancement* — user: "can we just generate this wavefront directly in 3D? … Much better than this fake 3D from 2D" | Implemented (real z-buffered PyVista/VTK surface in a subprocess window via the **WFront 3D** button; 2D Zemax waterfall kept as the printout panel; no new dependency) | `validate_wavefront_3d_surface` + Phase 50 |
| [0045](0045-surface-shape-builder-nameerror.md) | Surface Shape Builder button crashed with `NameError: encode_custom_surface_value` (silent in UI — traceback only on console) | Fixed (workbench imports the symbol directly instead of relying on the editor's globals-sync, which only carried `decode_`; plus a `report_callback_exception` override so no UI action ever fails silently again) | `validate_surface_shape_builder_dialog_bindings` (display-free AST binding guard) |
| [0046](0046-cemented-doublet-thin-cement-body.md) | "3D lens element not matching 2D" / "duplicating itself" — a cemented doublet (`Doublet_4_surf_no_TDE.zmx`) models the bond as a real 7.5 µm `___BLANK` cement, so KrakenOS drew that microns-thick glass as a full-aperture standalone slab; 3D read as a third element while 2D collapsed it to a hairline (not a North-Star #2 violation — same data, a 3D legibility artifact) | Fixed in BOTH render paths (a sub-0.05 mm cement/bond layer keeps its actor + AAA optical surface but is drawn at opacity 0: hidden in `_iter_3d_side_body_meshes`, and kept hidden through the live `open3d_scene_refresh` rays-on opacity clamp that otherwise re-inflated it to a slab + extra rim; ray tracing untouched). A follow-up flag ("extra rim still there") traced to each lens row drawing BOTH a cap rim and a mechanical body-drum OD rim (5 rings, want 3) — round analytic bodies now draw their glassy fill but no duplicate OD ring, so the doublet reads as 3 rim lines | `validate_cemented_doublet_body_count` (display-free) + `validate_cemented_doublet_body_count_snapshot` (live rays-on render, asserts rim_count==3) + Phase 51 |
| [0047](0047-det-mode-blanks-reference-disks.md) | "Clicking Refs show only the Object disk, click Det, Object Disk vanish, not showing any Image Disk" — on the on-axis cemented doublet (no detector), toggling Det blanked the Object/Image reference disks | Det-blank fixed (suppression now gated on `Open3DSceneRefreshService._detector_coverage_will_draw` — a real detector target with active sensor dims AND `max_real_image_height > 0`, i.e. only when the coverage overlay actually replaces the disks; a strict subset, so detector phases 37–39 are unchanged). The "1 mm Image disk" half (on-axis Infinity focuses to a near-point) is a faithful read, left as an open design item (Finite-mode starter, or a real-detector footprint fallback) | `validate_det_coverage_gate` (display-free gate logic) + `validate_det_mode_keeps_reference_disks` (live Det-toggle render) + Phase 52 |
| [0048](0048-open3d-iso-orbit-clips-converging-cone.md) | "first view … second view, it starts clipping … 3rd view, clipped" — orbiting/zooming the Open-3D view **right after startup** sliced off the converging cone + image plane, but the same orbit was fine **after clicking a cardinal preset** (XZ/YZ/…) | Fixed (the "Iso" view's `set_camera_preset` else-branch used PERSPECTIVE — no `parallel_scale` — while every cardinal preset is PARALLEL; a perspective camera sits a finite distance away so an orbit swings the far geometry behind it into the clamped-positive near clip plane. Iso now fits an orthographic `parallel_scale` like the cardinal buttons; parallel renders behind-camera geometry and makes camera distance visually free. Backed by a parallel "keep the camera clear of the complete scene" dolly after refresh + on every interaction — both no-ops on the rendered image) | `validate_camera_iso_orbit_no_clip` (live: Iso is orthographic, orbit keeps all 8 scene corners in front, fixed frame draws the image-plane geometry the recorded perspective camera clips) + Phase 53 |
| [0049](0049-open3d-step-reselect-accumulates-gizmos.md) | "Camera selcted, but the Imaging Lens still get selected" / "LED STEP selected, previous two selection are not cleared" — clicking a different imported STEP solid left the previous solid's rotation gizmo on screen; three picks stacked three gizmos (recorded `rotation_handle_count` 6 → 12 → 18) | Fixed (`show_step_rotation_handler` was add-only — `ensure_for_label` returns early when a label has handles and adds six when it has none, but nothing removed the *prior* label's six. Now the inspector tracks a `_selected_step_labels` set and reconciles the live gizmos to it: a plain click collapses to `{label}` (tearing down the prior gizmo — the reported fix), Shift+click toggles a label in/out for intentional multi-select, and Ctrl is left as the camera-orbit modifier so it is not overloaded. New `Open3DStepRotationHandleService.remove_for_label`/`reconcile_to_labels` do the per-label teardown; the scene refresh re-applies the set so multi-select survives a rebuild) | `validate_open3d_step_reselect_single_gizmo` (display-free: selection-set logic + service reconcile never accumulates) + Phase 54 |
