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

- **Non-sequential tracing plumbing:** 89-92% present.
- **North Star invariant enforcement:** 84-87% present.
- **Main remaining gap:** move the new `NonSequentialRayState` bridge from diagnostic/event metadata into the authoritative physics state for all surface classes, then make canonical `RayEvent` records the source of truth for plots, inspectors, detector analysis, and CSV export.

## Progress Snapshot

| North Star area | Current status | Progress | Recent movement |
| --- | --- | --- | --- |
| Native non-sequential tracing | Partially achieved | `█████████░ 89%` | `NonSequentialRayState` now records terminal absorber, detector, and target-plane events in addition to refractive media transitions. |
| 3D scene with 2D projections | Improving | `████████░░ 80%` | `SceneBundle` now promotes optical solids into both `OpticalVolume3D` and `BoundaryFace3D` records, and the scene graph exposes volumes above their boundary faces. |
| Separate sources, objects, detectors | Partially achieved | `██████░░░░ 62%` | Explicit Detector metadata now terminates non-sequential rays with detector media-state and interaction records instead of relying on incidental row position. |
| Event-law physics and diagnostics | Partially achieved | `████████░░ 82%` | Ray events now expose concrete medium changes and explicit terminal laws: absorption, detector termination, and target-plane termination. |
| Regression coverage for arbitrary prisms/solids | Improving | `████████░░ 86%` | Regression coverage now checks optical-solid media state, non-STL `AIR -> BK7 -> AIR` transitions, absorber termination, detector termination, and target-plane termination. |

## North Star Invariants

### 1. True non-sequential tracing is native; sequential tracing is the ordered-path special case.

Status: **partially achieved**.

What exists:

- `NsTrace` is a real non-sequential trace path with nearest-object selection, STL/solid handling, face overrides, coatings, beam-splitter branching, diffuse scattering, terminal segments, and branch result snapshots.
- UI Auto mode selects non-sequential preview for physical source, beam splitter, diffuse scatter, optical STL solid, off-axis geometry, probabilistic non-sequential coating, and target-surface workflows.
- Saved/exported layout tracing now uses the same shared trace-intent resolver instead of a narrower saved-layout-only heuristic.
- `TraceLoop`, `BatchTraceLoop`, and `NsTraceLoop` share launch metadata plumbing.
- Non-sequential intersection now uses a shared mesh adapter so UDA/custom/STL-like PyVista datasets satisfy one ray-traceable mesh contract before selection or hit-normal evaluation.
- Non-sequential solid hit records now carry mesh cell id, original cell id, and matched face id through the core trace and raykeeper metadata.
- CAD/STL face candidates now preserve exact STL triangle membership in normalized face metadata.
- Runtime optical-solid mesh cells are labeled from that exact triangle/cell membership when available; face-plane inference remains a compatibility fallback.
- Optical-solid face-law resolution now uses the direct cell face id and carries the face-match method, score, and warning text through trace arrays, raykeeper, scene hits, and Ray Inspector CSV export.
- Optical-solid hits that fall back to geometric face-plane inference now emit a diagnostic warning instead of looking equivalent to exact triangle-membership hits.
- `SceneBundle` now promotes optical-solid face metadata into `BoundaryFace3D` records with face id, side/function, port role, material/coating fields, world centroid/normal, triangle membership, and diagnostics.
- The non-sequential scene graph now shows those boundary faces as children of the owning optical-solid surface row, and CSV export inherits the same records through the scene graph table.
- UI-built trace systems now attach `_scene_boundary_faces_by_surface`, a runtime boundary-face index derived from the scene boundary records.
- `KrakenSys.__OpticalSolidWorldFaces` now prefers that attached scene boundary index before falling back to `SDT[*].OpticalSolidFaces`, so runtime face-law lookup is no longer exclusively row-metadata driven.
- `SceneBundle` now promotes each optical solid into an `OpticalVolume3D` with material, ambient medium, source STL, boundary face ids, world bounds, and diagnostics.
- UI-built trace systems now attach `_scene_optical_volumes_by_surface`, a runtime optical-volume index derived from scene volume records.
- Optical-solid runtime hits now look up the attached volume record, preserve the native Kraken material such as BK7, and emit volume entry/exit interaction models around face-law events.
- The non-sequential kernel now carries a `NonSequentialRayState` bridge with `current_medium`, `current_index`, and `inside_volumes`.
- Runtime ray events now preserve `VOLUME_ID`, `MEDIA_IN`, `MEDIA_OUT`, `MEDIA_TRANSITION`, `MEDIA_STATE_METHOD`, `INSIDE_VOLUMES_BEFORE`, and `INSIDE_VOLUMES_AFTER`.
- Ordinary non-STL refractive hits now update the same ray state from surface material, e.g. `AIR -> BK7` at entry and `BK7 -> AIR` at exit.
- `ABSORB` surfaces, explicit Detector rows, and final target planes now stop rays through shared terminal media-state events instead of looking like ordinary anonymous transmission.
- Raykeeper, `RayHit3D`, scene ray hits, Ray Inspector, and Ray Inspector CSV export now expose the same media-state fields.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L3092) - `NsTrace`.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L1527) - beam-splitter settings.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L1638) - diffuse scatter settings.
- [`KrakenOS/UI/trace_intent.py`](KrakenOS/UI/trace_intent.py#L1) - shared trace-intent resolver.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L15145) - UI trace-mode adapter.
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L409) - saved/exported layout tracing.
- [`KrakenOS/TraceLoopTool.py`](KrakenOS/TraceLoopTool.py#L82) - `NsTraceLoop`.
- [`KrakenOS/MeshRayTrace.py`](KrakenOS/MeshRayTrace.py#L1) - shared PyVista mesh ray-trace adapter.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L502) - non-sequential chooser mesh intersection.
- [`KrakenOS/InterNormalCalc.py`](KrakenOS/InterNormalCalc.py#L345) - hit-normal mesh intersection.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L170) - mesh hit identity arrays.
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L66) - `BoundaryFace3D`.
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L95) - `OpticalVolume3D`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L40) - scene boundary-face builder.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L148) - scene optical-volume builder.
- [`KrakenOS/UI/nonseq_output_ports.py`](KrakenOS/UI/nonseq_output_ports.py#L1352) - runtime optical-volume index attachment.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L447) - runtime boundary-face lookup preference.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L503) - runtime optical-volume lookup.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L60) - `NonSequentialRayState`.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L185) - media-state raykeeper propagation.
- [`KrakenOS/UI/validate_interaction_accounting.py`](KrakenOS/UI/validate_interaction_accounting.py#L144) - non-STL media-state regression.

Remaining gap:

- The UI data model is still row-first. `SurfaceRow` remains the central prescription object, with scene semantics stored in `advanced` metadata.
- Saved/exported layout tracing now shares the same trace-intent resolver as the live UI; remaining risk is ensuring every future scene trigger is added to that resolver instead of local call sites.
- Non-sequential preview failures now surface a diagnostic instead of silently falling back to sequential tracing.
- Mesh adaptation, hit-cell capture, runtime cell-to-face labeling, scene boundary-face promotion, runtime boundary index attachment, scene volume promotion, runtime volume index attachment, non-STL media-state updates, terminal media-state updates, and media-state event export are now centralized enough to inspect. Remaining work is to make `NonSequentialRayState` the authoritative physics input everywhere instead of a bridge layered around the current scalar-index path, and to emit a service-owned canonical ray-event export.

### 2. Optical elements and rays are represented in 3D; 2D plots are projections of traced 3D data.

Status: **mostly achieved for preview/display, not yet universally enforced**.

What exists:

- `SceneBundle` carries sources, surface curves, surface meshes, ray paths, planes, labels, pick regions, bounds, and display metadata.
- `SceneBundle` carries `OpticalVolume3D` records for closed optical solids, including material and owning boundary face ids.
- `SceneBundle` also carries `BoundaryFace3D` records for optical-solid faces, which keeps CAD/STL face identity attached to the scene instead of only row `advanced` metadata.
- The non-sequential scene graph shows optical volume nodes beneath optical-solid rows, with boundary face nodes beneath the owning volume where available.
- `ProjectedScene2D` is explicitly a projected display shape.
- `project_scene_bundle` projects a full scene bundle into 2D.
- Ray paths and hit records are reconstructed from raykeeper data instead of being separate 2D-only simulations.
- The layout display now renders a user-selected primary YZ, XZ, or XY view together with auxiliary panes for the two unselected slices.
- The YZ/XZ/XY selector sits in the plot toolbar beside `Open 3D`, so 2D projection choice is treated as plot-view state rather than a left-panel prescription field.
- Saved layouts store the selected plane as Kraken UI state, and legacy `Vertical`/`Horizontal` settings normalize to the canonical YZ plane.
- The selected projection rebuilds row pick regions so clicking geometry in XZ or XY can still select the editable table row.
- The auxiliary and selected non-YZ slices use traced 3D ray coordinates and 3D mesh outlines, which is a direct step toward treating every 2D plot as a projection of the same 3D scene.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L247) - `SceneBundle`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L322) - scene-bundle volume and boundary-face promotion.
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
- Raykeeper also stores mesh cell id, original mesh cell id, matched mesh face id, face-match method, and face-match score for non-sequential solid hits.
- Branch metadata includes branch id, parent branch id, power, phase, label, path, Jones P/S, and polarization vector.
- Scene hit records expose interaction metadata to the UI.
- STL mesh diagnostics detect empty, open, non-manifold, degenerate, inverted, tiny, huge, and slow meshes.
- The non-sequential geometry boundary now converts PyVista datasets without `ray_trace` into surface meshes, or raises `MeshRayTraceError` with context if conversion is impossible.
- For optical solids with configured faces, runtime meshes now receive `KrakenFaceId` cell data, allowing the intersected cell to choose the face law directly.
- Runtime meshes also receive `KrakenFaceMatchMethod`; exact STL triangle membership is recorded as `triangle_membership`, while older or incomplete metadata can still use `plane_inference`.
- `RayHit3D`, Ray Inspector, Trace Path Inspector, and their CSV exports expose the same face-match provenance and warning text.
- Runtime optical-solid hit handling now attaches `volume_id`, `volume_material`, `ambient_material`, and `media_transition` to scene boundary overrides where a scene volume is known.
- Volume entry and exit are now visible as interaction models such as `optical_volume_entry_ray_state_inside_volumes:volume:1` and `optical_volume_exit_ray_state_inside_volumes:volume:1`.
- Runtime events and scene ray hits expose media state before and after the event, including `AIR -> BK7` entry, unchanged `BK7 -> BK7` internal reflections, and `BK7 -> AIR` exit for a mirror-coated penta-prism path.
- Ordinary non-STL refractive surfaces now report material medium changes using the same event fields, so conventional non-sequential Standard-surface traces no longer show only anonymous scalar-index changes.
- Absorber, Detector, and final target-plane hits now report terminal media transitions such as `absorb`, `detector_termination`, and `target_termination`; absorber hits also force zero outgoing power.
- Ray Inspector and Ray Inspector CSV export include the same volume/media-state columns so the state is inspectable outside the plot.

Relevant code:

- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L575) - interaction collection fields.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L660) - ray event data collection.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L290) - raykeeper interaction, mesh-face provenance, and branch metadata.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L800) - `RayHit3D` construction.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L28931) - Ray Inspector hit table and CSV columns.
- [`KrakenOS/UI/stl_geometry.py`](KrakenOS/UI/stl_geometry.py#L23) - STL diagnostics fields.
- [`KrakenOS/MeshRayTrace.py`](KrakenOS/MeshRayTrace.py#L1) - shared mesh trace diagnostics.
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L93) - `RayHit3D` mesh hit identity fields.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L860) - mesh hit identity extraction into scene hits.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L2675) - optical-solid hit media and volume-record bridge.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L28931) - Ray Inspector volume/media-state columns and CSV export.

Remaining gap:

- `NsTraceLoop` failure now clears the attempted raykeeper output and raises a UI diagnostic; sequential fallback is suppressed for non-sequential-required scenes.
- Some physics events are classified too generically in scene display, especially diffraction.
- Branch truncation has a hard limit but is not surfaced strongly as a diagnostic.
- Some optical-solid face roles are display/metadata concepts but do not yet enforce complete face-native physics.
- Converted meshes, hit-cell metadata, scene volume records, terminal records, and explicit media-state event fields now solve the first inspectability problem: a ray event reports which volume or material medium it is entering, reflecting inside, transmitting through, terminating on, or exiting. The remaining deeper gap is to make this state the authoritative physics input for every surface family, including nested/cemented volumes and all branch children.

## Practical Rule Assessment

The practical rule is mostly implemented in live UI preview, but not uniformly across all paths.

| Workflow trigger | Current status |
| --- | --- |
| Physical source | Live UI and saved/exported tracing share the same Auto non-sequential trigger. |
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

Risk: mitigated.

`_trace_preview_bundles` now fails closed for non-sequential-required layouts. If `NsTraceLoop` raises, the UI clears attempted raykeeper output, records the trace failure, and draws a diagnostic panel instead of tracing the same launch bundle through sequential `TraceLoop`.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L50447)

Remaining follow-up:

- Expand the diagnostic panel with per-surface/face ambiguity details once face-native law resolution is consolidated.

### PyVista mesh types without `ray_trace`

Risk: mitigated at the shared intersection boundary.

UDA and custom-surface generation can produce visible PyVista datasets such as `UnstructuredGrid` that do not expose the `ray_trace` method used by the non-sequential chooser and hit-normal calculator. Those meshes previously caused non-sequential preview failure before any physics law could be evaluated.

`MeshRayTrace.py` now normalizes these datasets through surface extraction, triangulation, cleaning, and cell-normal preparation. Non-convertible geometry raises `MeshRayTraceError` with surface context instead of an attribute error.

Relevant code:

- [`KrakenOS/MeshRayTrace.py`](KrakenOS/MeshRayTrace.py#L1)
- [`KrakenOS/Prerequisites3D.py`](KrakenOS/Prerequisites3D.py#L240)
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L502)
- [`KrakenOS/InterNormalCalc.py`](KrakenOS/InterNormalCalc.py#L345)

Remaining follow-up:

- Promote exact triangle/cell membership into scene-graph `BoundaryFace` records rather than keeping it in row `advanced` metadata.
- Move Ray Inspector / Trace Path Inspector CSV schemas into a service-owned canonical ray-event exporter.

### CAD/STL face membership can still fall back to plane inference

Risk: diagnosed, but not eliminated.

Newly assigned CAD/STL optical-solid faces now preserve exact `triangle_indices`, and runtime mesh cells use that membership before geometric matching. Older layouts or externally authored metadata without `triangle_indices` still fall back to face-plane inference, but those hits now carry `MESH_FACE_MATCH_WARNING` / `mesh_face_match_warning` so the diagnostic path is visible in raykeeper, scene hits, Ray Inspector, Trace Path Inspector, and CSV export.

Relevant code:

- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L1403) - planar face clustering preserves STL triangle indices.
- [`KrakenOS/UI/optical_solid_metadata.py`](KrakenOS/UI/optical_solid_metadata.py#L276) - normalized face records persist `triangle_indices`.
- [`KrakenOS/MeshRayTrace.py`](KrakenOS/MeshRayTrace.py#L106) - runtime mesh cells prefer exact membership and record match method.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L179) - raykeeper preserves face-match warnings.
- [`KrakenOS/UI/validate_vendor_prism_42779.py`](KrakenOS/UI/validate_vendor_prism_42779.py#L269) - regression requires triangle membership and runtime `triangle_membership` hit methods.

Expected fix:

- Add migration diagnostics for old optical-solid metadata without membership.
- Treat `plane_inference` hits as warning-grade diagnostics for optical solids whose authored face metadata should have exact membership.

### Optical volume media state is a bridge, not yet the whole physics engine

Risk: medium to high.

`OpticalVolume3D` records and `_scene_optical_volumes_by_surface` now give runtime tracing an explicit scene-owned volume record with material, ambient medium, source STL, and boundary face ids. `NonSequentialRayState` now carries `current_medium`, `current_index`, and `inside_volumes`; optical-solid events export media-in/out and inside-volume state before/after each hit.

This is still a bridge, not the final tracer architecture. Optical-solid entry/exit now uses `inside_volumes`, and ordinary Standard-surface hits now update the medium name from the refractive material. Other surface families and analysis paths still depend on scalar refractive-index state and row ordering.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L95) - `OpticalVolume3D`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L148) - scene optical-volume records.
- [`KrakenOS/UI/nonseq_output_ports.py`](KrakenOS/UI/nonseq_output_ports.py#L1352) - runtime optical-volume index attachment.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L60) - `NonSequentialRayState`.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L2675) - current optical-volume media bridge.

Expected fix:

- Make `NonSequentialRayState` the source of truth for `medium_in` and `medium_out` across all non-sequential hits and branch children.
- Replace remaining row-order/scalar-index media decisions with scene object/volume adjacency.
- Add diagnostics when the state stack and geometry disagree, for example an exit hit on a volume the ray is not inside.

### STEP/STL side labels vs physical axes

Risk: low, but the UI wording can be confusing.

The current face editor has two different concepts:

- `Left`, `Right`, `Up`, and `Down` are 2D projection side labels used by the YZ-style layout workflow, face-role dialogs, and human-readable prism path reports.
- `+Y normal`, `-Y normal`, `+Z normal`, `-Z normal`, `+X normal`, and `-X normal` are physical/world or placement-axis references.

These should not be treated as equivalent. The North Star direction is to make physical face normals and cell/face identity authoritative for tracing, while side labels remain optional UI hints for display and quick selection.

Expected fix:

- Rename side labels as projection labels in the UI.
- Prefer physical normal/axis controls for placement and fit.
- Keep side labels synchronized from the selected projection when useful, but never use them as the source of physical truth.

### Future non-sequential triggers can bypass the shared resolver

Risk: medium.

The live UI and saved/exported ray builders now share one trace-intent resolver. The remaining risk is architectural drift: future scene triggers could be added directly to one call site instead of to `trace_intent.py`, recreating the old preview/export mismatch.

Relevant code:

- [`KrakenOS/UI/trace_intent.py`](KrakenOS/UI/trace_intent.py#L1)
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L15145)
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L409)

Expected fix:

- Treat `trace_intent.py` as the only allowed place for Auto non-sequential trigger policy.
- Add regression checks whenever a new physical source, object type, coating law, detector/path workflow, or CAD/STL face role is added.

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

1. Make `NonSequentialRayState` authoritative for all non-sequential media decisions.

   The bridge now exists for optical solids, ordinary Standard surfaces, absorber terminals, Detector terminals, and target-plane terminals. The next step is to route all branch children and nested/cemented volume boundaries through it with diagnostics when the state stack conflicts with geometry.

2. Promote runtime trace output into canonical `RayEvent` records.

   The event table should be produced by the trace service and consumed by 2D/3D plots, Ray Inspector, path analysis, detector analysis, illumination reports, and CSV export.

3. Finish moving scene entities above row metadata.

   Rows can remain as the prescription editor, but runtime tracing should consume a scene graph containing objects, sources, detectors, masks, coatings, solids, volumes, boundary faces, and path metadata.

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

1. Add `Scene`, `OpticalVolume`, `BoundaryFace`, `RayState`, and `RayEvent` dataclasses. `BoundaryFace3D` and `OpticalVolume3D` now exist in the UI scene bundle; `NonSequentialRayState` now exists in the trace kernel as a media-state bridge; canonical `RayEvent` records are still the next architecture gap.
2. Build a row-to-scene adapter from current layout rows and settings.
3. Promote the now-persisted CAD/STL `triangle_id -> face_id` mapping from row metadata into scene-graph `BoundaryFace` records. Initial `BoundaryFace3D` scene-bundle promotion and runtime boundary index attachment are complete.
4. Promote optical-solid rows into scene-owned `OpticalVolume` records. Initial `OpticalVolume3D` scene-bundle promotion, runtime volume index attachment, and volume entry/exit event labeling are complete.
5. Replace optical-solid hit handling with a scene tracer that tracks region/media state. Initial media-state tracking and event export are complete for optical-solid entry/internal reflection/exit, ordinary Standard-surface material transitions, and absorber/detector/target terminal events. The remaining gap is to make the state stack authoritative for all non-sequential surface families.
6. Route 2D/3D plots, detector analysis, illumination reports, and CSV export through `RayEvent` records.
7. Add diagnostics for every terminal condition and unsupported boundary law.
8. Add regression tests for:

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
