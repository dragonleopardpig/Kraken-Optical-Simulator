# 0357 — Illumination Source covering a BS side must block the reflected imaging arm

**Flag:** 20260719_203032_676 — "When there is an Illumination Source cover the entire BS Cube
side, the imaging ray shouldn't reflected out from it, and there shouldn't be any second optical
axis created. Can make the illumination source solid color instead of translucent one?"

**Status:** FULLY SHIPPED 2026-07-19 — glyph solid (earlier commit) + the trace-level block
(guard `validate_open3d_illumination_source_face_block`, penta phase 310). As built:
`_coverage_illumination_block_face_ids` (analysis_compute_workflow) detects a free physical
non-marker source panel seated on a promoted face (plane-parallel ≥0.985, |along| ≤ 3 mm, centre
within panel half-diagonal + 2 mm) via the 0264 world-face records, and merges those face_ids into
the 0273 `illumination_block_face_ids` map — the imaging trace force-absorbs at the plate, so the
reflect arm, its rays AND its branch optical axis die. The LED's own flood is exempted PER-BUNDLE:
the non-seq trace loop scopes `_suppress_illumination_face_absorption` to bundles whose source role
is "illumination" (trace_preview). The signature already keys on the block ids (0273), so no cache
gotcha.

## Shipped now

The 0283 scene-source glyph panel draws solid amber — the LED reads as the opaque plate it is.
(The 0356 hard stop already truncates the DRAWN reflected rays at the emitter plane.)

## Remaining defect

The imaging trace still REFLECTS at the BS diagonal into the LED-covered side: the branch spawns
its "Optical Axis 2" chief-ray segment and branch detector machinery (draw-suppressed since 0285,
but the axis + in-cube reflected stubs remain). Physically the covered side is an opaque emitter —
the imaging arm hitting it is absorbed (exactly the 0273 face-block physics, which today engages
only for MARKED faces, not for scene sources).

## CONFIRMED on build 5a955e86 (flag 20260719_204715_749)

The re-flag runs the newest build, so the 0356 display clip alone does not resolve the symptom:
the reflected arm still draws (in-cube stubs at minimum) and "Optical Axis 2" still spawns —
`traced_chief_ray_segment` is not a ray polyline and never sees the hard-stop planes. Root fix =
absorb at the covered face inside the trace (below); also verify in-app whether the 0356 clip
engages at all on this scene (the plane sits at the source panel origin, normal −emit_dir).

## Implementation anchors found 2026-07-19 (for the build session)

- Extension point: `analysis_compute_workflow._illumination_block_face_ids_by_row` (:571) —
  today marker-only (`face_anchor_row`/`face_anchor_face_id`); add coverage-derived entries from
  `_drawable_scene_source_descriptors()` (enabled+physical+non-marker).
- Face geometry: promoted rows' world-frame display mesh
  `_transformed_imported_step_mesh_for_label(label)` carries `kraken_step_face_index` cell data
  (NEVER mutate — memoized, bug 0331); per-face centroid/normal by grouping cells. Analytic route:
  `scene_placement_commands._step_overlay_fine_face_centroid_normal(label, face_index)` (:4722).
- ⚠️ OPEN VERIFICATION: face_id convention — raw faces use `f"F{face_index:03d}"`
  (round_lens_pick:230), but the trace-side `OpticalSolidFaceIlluminationBlock` matcher may
  compare metadata face_ids; confirm in `KrakenSys.__OpticalSolidFaceInteraction` before wiring.
- Row↔label: `_promoted_optical_solid_row_index(label)` (scene_placement_commands:2848) inverts.
- Cache: `_row_specs_signature` already keys on `illumination_block_face_ids`
  (row_spec_contracts:72) — coverage-derived ids flow into the same field, so the 0273 gotcha is
  covered automatically.

## Design (reuse 0273 wholesale)

Detect coverage at build time: for each enabled, physical, NON-marker scene source, find the
promoted-solid face whose plane matches the source panel (|n·d|≈1, in-plane distance small,
panel rect covers the face bbox) and add that face to the row's `illumination_block_face_ids` —
the exact hook 0273 built (`OpticalSolidFaceIlluminationBlock` → `force_absorption` → the 0108
absorbed-leaf chain drops the branch detector AND its axis). Remember the 0273 cache gotcha:
`_row_specs_signature` must key on the derived ids or the fix silently no-ops. Guard: covered
face absorbs, uncovered BS still splits (0090), the LED's own flood unaffected, second axis gone.
