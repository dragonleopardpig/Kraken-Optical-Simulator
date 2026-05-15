# Kraken UI Non-Sequential North Star Status

Branch assessed: `nonseq-display-refactor`

Last updated: 2026-05-15

## Executive Summary

The branch is moving in the right direction, but the North Star is only partially achieved.

The current architecture is a transitional hybrid:

- real non-sequential tracing exists in the KrakenOS kernel;
- UI preview can automatically select non-sequential tracing for many scene workflows;
- sources, branches, detector data, interaction metadata, and projected scene objects exist;
- but the UI is still primarily row-prescription driven, with non-sequential behavior selected by heuristics and special surface rows.

Estimated status:

- **Non-sequential tracing plumbing:** 70-75% present.
- **North Star invariant enforcement:** 60-65% present.
- **Main remaining gap:** make the scene/ray-event model the single source of truth, and make invalid or ambiguous non-sequential physics fail with diagnostics rather than falling back to plausible sequential drawings.

## Progress Snapshot

| North Star area | Current status | Progress | Recent movement |
| --- | --- | --- | --- |
| Native non-sequential tracing | Partially achieved | `███████░░░ 70%` | Auto trace policy already routes physical sources, STL solids, off-axis scene geometry, beam splitters, diffuse scatter, target-surface workflows, and probabilistic coatings toward non-sequential tracing. |
| 3D scene with 2D projections | Improving | `████████░░ 75%` | The main 2D layout now has a canonical YZ/XZ/XY plane selector; saved layouts normalize legacy orientation values, the auxiliary panes show the two unselected slices, and row pick regions are rebuilt from the selected projection. |
| Separate sources, objects, detectors | Partially achieved | `██████░░░░ 60%` | Sources are separate `SceneSource3D` entities; default sequential `Image` rows are no longer promoted to non-sequential detectors unless explicitly marked or targeted. |
| Event-law physics and diagnostics | Partially achieved | `█████░░░░░ 50%` | Raykeeper carries interaction metadata, but face-native law resolution and mandatory ambiguity diagnostics still need consolidation. |
| Regression coverage for arbitrary prisms/solids | Improving | `██████░░░░ 62%` | Vendor prism validation now covers output-port continuation, explicit detector promotion behavior, display suppression of non-detector Image sentinels, and projection-plane row picking. |

## North Star Invariants

### 1. True non-sequential tracing is native; sequential tracing is the ordered-path special case.

Status: **partially achieved**.

What exists:

- `NsTrace` is a real non-sequential trace path with nearest-object selection, STL/solid handling, face overrides, coatings, beam-splitter branching, diffuse scattering, terminal segments, and branch result snapshots.
- UI Auto mode selects non-sequential preview for physical source, beam splitter, diffuse scatter, optical STL solid, off-axis geometry, probabilistic non-sequential coating, and target-surface workflows.
- `TraceLoop`, `BatchTraceLoop`, and `NsTraceLoop` share launch metadata plumbing.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L3092) - `NsTrace`.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L1527) - beam-splitter settings.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L1638) - diffuse scatter settings.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L15145) - UI trace-mode resolver.
- [`KrakenOS/TraceLoopTool.py`](KrakenOS/TraceLoopTool.py#L82) - `NsTraceLoop`.

Remaining gap:

- The UI data model is still row-first. `SurfaceRow` remains the central prescription object, with scene semantics stored in `advanced` metadata.
- Some saved/exported layout paths use a narrower non-sequential detection helper than the live UI resolver.
- Non-sequential preview can still silently fall back to sequential tracing after an exception.

### 2. Optical elements and rays are represented in 3D; 2D plots are projections of traced 3D data.

Status: **mostly achieved for preview/display, not yet universally enforced**.

What exists:

- `SceneBundle` carries sources, surface curves, surface meshes, ray paths, planes, labels, pick regions, bounds, and display metadata.
- `ProjectedScene2D` is explicitly a projected display shape.
- `project_scene_bundle` projects a full scene bundle into 2D.
- Ray paths and hit records are reconstructed from raykeeper data instead of being separate 2D-only simulations.
- The layout display now renders a user-selected primary YZ, XZ, or XY view together with auxiliary panes for the two unselected slices.
- Saved layouts store the selected plane as Kraken UI state, and legacy `Vertical`/`Horizontal` settings normalize to the canonical YZ plane.
- The selected projection rebuilds row pick regions so clicking geometry in XZ or XY can still select the editable table row.
- The auxiliary and selected non-YZ slices use traced 3D ray coordinates and 3D mesh outlines, which is a direct step toward treating every 2D plot as a projection of the same 3D scene.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L247) - `SceneBundle`.
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L267) - projected 2D scene objects.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L34) - `build_scene_bundle`.
- [`KrakenOS/UI/layout_plot_controller.py`](KrakenOS/UI/layout_plot_controller.py#L71) - `project_scene_bundle`.

Remaining gap:

- Some analysis paths still depend directly on ordered-surface assumptions.
- Folded preview remains a compatibility path rather than a projection of the same native non-sequential scene.
- Some surface cross-section curves are still pre-flattened to YZ display coordinates; XZ/XY plots therefore rely on mesh outlines and ray paths for true 3D information until surface curves become fully 3D scene geometry.
- The row table still determines much of the scene construction, instead of a scene graph owning objects first.

### 3. Object/reference geometry and illumination sources are separate scene entities.

Status: **substantially achieved, with incomplete object/detector semantics**.

What exists:

- `SceneSource3D` is explicitly not a KrakenOS surface row.
- Multiple source specifications can be normalized, deduplicated, traced, and attached to raykeeper metadata.
- Source illumination reports compute launched rays, hit rays, hit events, throughput, hit fraction, vignetted fraction, centroid, RMS, span, missed power, and missed terminal breakdown.
- Detector-map, branch-detector PSF/MTF, coherent detector, and diffraction detector CSV/report paths exist.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L67) - `SceneSource3D`.
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L254) - scene sources from settings.
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L384) - source metadata per traced ray.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L21) - launch/source metadata.
- [`KrakenOS/UI/source_illumination_analysis.py`](KrakenOS/UI/source_illumination_analysis.py#L58) - source illumination CSV/report fields.
- [`KrakenOS/UI/source_illumination_analysis.py`](KrakenOS/UI/source_illumination_analysis.py#L311) - source illumination record collection.

Remaining gap:

- `Object Target` currently traces as a specular reflective proxy rather than a true object/measurement/termination entity.
- Detector semantics are mostly row metadata layered onto Image/path rows.
- Imported CAD/STL diffuse face scattering is not wired as face-native physics.

### 4. Every ray/surface event obeys configured physics; ambiguity produces diagnostics.

Status: **partially achieved, but this is the weakest invariant**.

What exists:

- Raykeeper stores interaction type, interaction model, target surface, input power, coefficient, output power, loss power, and bulk term.
- Branch metadata includes branch id, parent branch id, power, phase, label, path, Jones P/S, and polarization vector.
- Scene hit records expose interaction metadata to the UI.
- STL mesh diagnostics detect empty, open, non-manifold, degenerate, inverted, tiny, huge, and slow meshes.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L575) - interaction collection fields.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L660) - ray event data collection.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L290) - raykeeper interaction and branch metadata.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L800) - `RayHit3D` construction.
- [`KrakenOS/UI/stl_geometry.py`](KrakenOS/UI/stl_geometry.py#L23) - STL diagnostics fields.

Remaining gap:

- `NsTraceLoop` failure falls back to sequential preview in at least one live preview path.
- Some physics events are classified too generically in scene display, especially diffraction.
- Branch truncation has a hard limit but is not surfaced strongly as a diagnostic.
- Some optical-solid face roles are display/metadata concepts but do not yet enforce complete face-native physics.

## Practical Rule Assessment

The practical rule is mostly implemented in live UI preview, but not uniformly across all paths.

| Workflow trigger | Current status |
| --- | --- |
| Physical source | Live UI Auto selects non-sequential; saved-layout helper is weaker. |
| Beam splitter | Non-sequential branching exists for Beam Splitter rows and cube primitive workflows. |
| Target surface | Live UI Auto can select non-sequential for target tracing. |
| Probabilistic non-sequential coating | Live UI Auto recognizes this. |
| STL object | Non-sequential tracing and diagnostics exist. Face-native physics is incomplete. |
| Mirror fold | Non-sequential can handle reflection, but fold behavior still often lives in row/path metadata. |
| Tilt/decenter scene | Live UI Auto treats off-axis geometry as non-sequential scene request. |
| Detector/path workflow | Detector/path analysis exists, but detector is still largely metadata layered onto rows. |
| Conventional lens design | Sequential, batch, paraxial, wavefront, and MTF analysis paths remain available. |

## Potential Bugs And Risks

### Silent sequential fallback after non-sequential failure

Risk: high.

In `_trace_preview_bundles`, a non-sequential preview failure clears rays and traces the same bundles with sequential `TraceLoop`. This can draw plausible but physically wrong paths for a beam splitter, STL solid, diffuse object, or scene-source workflow.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L50447)

Expected fix:

- For non-sequential-required layouts, fail closed with a visible diagnostic.
- Sequential fallback should be allowed only for explicitly sequential workflows.

### Non-sequential detection differs between live preview and saved/exported layout tracing

Risk: high.

The live resolver checks many triggers. `layout_uses_nonseq` only checks Beam Splitter, Diffuse Object, Object Target, and STL solids. Physical sources, off-axis geometry, mirror folds, probabilistic coating, and selected target surface can diverge between UI preview and saved-layout ray generation.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L15145)
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L408)

Expected fix:

- Replace duplicated heuristics with one shared trace-intent resolver.

### Source power may be double-counted in illumination reports

Risk: medium to high.

`SceneSource3D.weight_per_ray` is set to `power / ray_count`, but illumination reporting computes input power as `source_weight * source_power`. For source power values other than 1.0, total input power can become proportional to `power * power`.

Relevant code:

- [`KrakenOS/UI/scene_source_analysis.py`](KrakenOS/UI/scene_source_analysis.py#L190)
- [`KrakenOS/UI/source_illumination_analysis.py`](KrakenOS/UI/source_illumination_analysis.py#L354)

Expected fix:

- Decide whether `source_weight` is already power-per-ray or a dimensionless ray weight.
- Use one convention consistently in source metadata, branch accounting, detector analysis, and CSV export.

### Object Target is a reflective proxy

Risk: medium to high.

`Object Target` is explicitly documented in the UI as a specular reflective proxy. That can contaminate object illumination, detector, and path workflows where the object should terminate, absorb, measure, or scatter.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L23967)

Expected fix:

- Add explicit target interaction modes: terminate/measure, absorb, specular proxy, diffuse/BRDF, detector-like sampling.

### CAD/STL face physics is incomplete

Risk: medium to high.

Imported CAD/STL face roles can be assigned and previewed, but diffuse face scattering is not wired. Virtual internal beam-splitter planes are previewed but traced branch physics still requires a Beam Splitter row or cube primitive.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L10987)
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L11040)

Expected fix:

- Move face functions from metadata-only concepts into trace-enforced interaction laws.

### Optical solid face overrides enforce only part of the face model

Risk: medium.

`__OpticalSolidFaceInteraction` currently force-reflects Mirror/TIR functions and applies loss. Other configured face functions can remain display metadata unless they are mapped elsewhere.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L473)

Expected fix:

- Make every normalized face function map to an explicit trace law or a diagnostic saying it is unsupported.

### Diffraction can be mislabeled as generic transmission/refraction

Risk: medium.

The scene hit classifier mostly reports launch, image, aperture, reflection, scatter, absorb, refraction, and transmission. Grating order and spacing are stored, but diffraction is not promoted to a first-class interaction label here.

Relevant code:

- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L767)

Expected fix:

- If grating order/spacing indicates diffraction, label the event as diffraction and include order/spacing in exported ray-event records.

### Branch truncation can be silent

Risk: medium.

Non-sequential branching has a hard result cap of 4096 branches. This prevents runaway branch growth, but the cap should become visible in diagnostics and export metadata.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L2600)

Expected fix:

- Add a branch-truncated flag and show/export it.

### Fixed near-hit suppression can skip valid close geometry

Risk: medium.

The non-sequential chooser discards intersections closer than `0.05`. This may incorrectly skip thin air gaps, bonded optics, close detectors, or near coincident surfaces.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L502)

Expected fix:

- Make the epsilon scale-aware and diagnostic-visible.
- Consider per-scene/per-surface tolerance.

### Branch grouping heuristic can be wrong without explicit branch metadata

Risk: medium.

When explicit branch metadata is absent, scene builder infers branch boundaries from surface ordering and reflection labels. True non-sequential paths can revisit surfaces or move to lower-index surfaces without representing a new logical branch.

Relevant code:

- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L877)

Expected fix:

- Prefer explicit branch metadata for all `NsTrace` paths.
- Use heuristic grouping only for legacy sequential traces.

## Recommended Next Architecture Steps

1. Make a shared `TraceIntent` or `SceneTracePolicy` object.

   It should centralize the decision currently split between `_resolved_trace_mode` and `layout_uses_nonseq`.

2. Remove silent sequential fallback for non-sequential-required layouts.

   A non-sequential scene should either trace non-sequentially or report a diagnostic.

3. Promote scene entities above row metadata.

   Rows can remain as the prescription editor, but runtime tracing should consume a scene graph containing objects, sources, detectors, masks, coatings, solids, and path metadata.

4. Make detectors and object targets real interaction laws.

   They should not rely on Image-row or Mirror-proxy behavior unless the user explicitly selected that model.

5. Complete optical solid face physics.

   Every CAD/STL face function should map to one of:

   - reflection;
   - transmission/refraction;
   - absorption;
   - detector termination;
   - beam-splitter branch;
   - diffuse/BRDF scatter;
   - unsupported-with-diagnostic.

6. Export one canonical ray-event table.

   The table should include source id, branch id, surface id, object id, event law, incoming/outgoing direction, normal, n0/n1, wavelength, coating response, polarization, power in/out/loss, and diagnostics.

7. Make ambiguous geometry first-class diagnostics.

   Examples:

   - near-tie intersections;
   - skipped near hits;
   - non-manifold STL;
   - unsupported CAD face function;
   - branch truncation;
   - invalid detector target;
   - physical-source scene traced sequentially.

## Fundamental Architecture Change

The right fix is not to add one-off handling for each prism, cube, splitter, or vendor CAD file. That approach will never converge. The architecture needs to make arbitrary optical solids behave according to natural optical physics by default.

### Introduce a true scene graph

Runtime tracing should consume a scene model, not the UI row table directly:

```text
Scene
  OpticalVolume(id, geometry, material)
    BoundaryFace(id, triangle_ids, normal, default_law=Uncoated)
    Optional coating/law override
  Sources
  Detectors
  Apertures
  Masks
  Ambient medium
```

The surface table can remain as an editor and serialization view, but it should be an adapter into this scene graph. The trace kernel should not infer physical scene semantics from row order plus `advanced` dictionaries at runtime.

### Make closed optical solids physically native

For a closed BK7 prism or STL volume:

- the default face law should be **Uncoated dielectric boundary**;
- air to BK7 entry should refract by Snell's law;
- BK7 to air exit should refract or total-internally-reflect by Snell's law;
- Fresnel should determine reflected/transmitted power;
- coatings should override the default only when the user explicitly configures mirror, beam splitter, absorber, detector, or scatter behavior.

`TIR` should usually be an event result, not a user-assigned face type. Media plus incidence angle determine total internal reflection. Face metadata should represent coatings or special boundary laws, not replace physical law evaluation.

### Track medium by object region

Current non-sequential tracing relies heavily on `PrevN`, nearby surface identity, and row/side conventions. That is fragile for prisms, nested solids, cemented elements, and repeated hits on the same object.

Each ray state should instead carry explicit region state:

```text
RayState
  origin
  direction
  wavelength
  power
  polarization
  current_medium
  inside_volumes
  branch_path
```

At a boundary hit, the tracer should resolve:

```text
hit_object
hit_face
medium_in
medium_out
face_law
coating
```

That makes arbitrary prisms natural: if the ray is inside `prism_1:BK7` and hits a boundary adjacent to ambient air, the event law is BK7-to-air uncoated dielectric unless a coating overrides it.

### Use actual hit face ids

Imported CAD/STL geometry should retain a direct mapping:

```text
triangle_id -> face_id -> BoundaryFace -> law/coating/material boundary
```

The intersection engine should return the triangle or cell id. The trace code should not need to infer the face by nearest plane after the hit. Nearest-plane matching is useful for UI diagnostics, but it should not be the authoritative physics path.

### Use one event-law pipeline

Every ray/surface event should go through the same pipeline:

```text
geometry hit
  -> resolve object and face
  -> resolve medium_in and medium_out
  -> resolve face law and coating
  -> compute Snell/Fresnel/TIR/polarization/absorption
  -> spawn child ray states when needed
  -> emit RayEvent
```

The event result should be explicit:

```text
refract
reflect_tir
reflect_mirror
split_reflect
split_transmit
absorb
scatter
detector_hit
missed_detector
ambiguous_hit
unsupported_boundary_law
```

This removes the current split between drawn path, row metadata, physics calculation, and downstream analysis labels.

### Make diagnostics mandatory

The user should be able to inspect a prism trace and see why a path did or did not fold. For example:

```text
Ray 14:
  entered BK7 at F005
  uncoated BK7-air event at F003
  incidence = 22.5 deg
  critical angle = 41.2 deg
  result = refract out, not TIR
```

For detector misses:

```text
Ray 21:
  entered BK7 at F005
  reflected mirror at F003
  reflected mirror at F004
  refracted out at F006
  missed detector: detector active radius = 0.5 mm, miss distance = 9.8 mm
```

That is the behavior that prevents future debugging from becoming a case-by-case process.

### Keep sequential tracing as an adapter

Sequential lens design should remain exact and reproducible, but it should be represented as an ordered-path adapter:

```text
ordered surface prescription -> scene path with ordered axial boundaries
```

When the user adds physical sources, STL/CAD solids, prisms, folds, beam splitters, detectors, probabilistic coatings, or object/path workflows, the scene tracer should become authoritative.

### Implementation order

1. Add `Scene`, `OpticalVolume`, `BoundaryFace`, `RayState`, and `RayEvent` dataclasses.
2. Build a row-to-scene adapter from current layout rows and settings.
3. Persist CAD/STL `triangle_id -> face_id` mapping during import/meshing.
4. Replace optical-solid hit handling with a scene tracer that tracks region/media state.
5. Route 2D/3D plots, detector analysis, illumination reports, and CSV export through `RayEvent` records.
6. Add diagnostics for every terminal condition and unsupported boundary law.
7. Add regression tests for:

   - uncoated prism below critical angle;
   - uncoated prism above critical angle;
   - mirror-coated penta prism;
   - detector miss after valid prism exit;
   - beam splitter branch generation;
   - diffuse/BRDF face scattering;
   - nested or cemented optical solids.

## Bottom Line

The branch has real non-sequential infrastructure, not just UI mockups. It already supports many of the North Star concepts: non-sequential tracing, physical sources, raykeeper metadata, branch paths, detector analysis, source illumination reporting, STL diagnostics, and 3D-to-2D scene projection.

The remaining work is mostly architectural consolidation and stricter failure behavior. The UI must stop treating non-sequential tracing as a preview option layered on top of rows, and instead make the scene/ray-event model authoritative for every workflow that is physically non-sequential.
