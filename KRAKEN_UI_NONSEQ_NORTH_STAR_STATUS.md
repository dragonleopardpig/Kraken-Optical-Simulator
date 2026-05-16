# Kraken UI Non-Sequential North Star Status

Branch assessed: `nonseq-display-refactor`

Last updated: 2026-05-16

## Executive Summary

The branch is moving in the right direction, but the North Star is only partially achieved.

The current architecture is a transitional hybrid:

- real non-sequential tracing exists in the KrakenOS kernel;
- UI preview can automatically select non-sequential tracing for many scene workflows;
- sources, branches, detector data, interaction metadata, and projected scene objects exist;
- `RayKeeper` now emits typed kernel `TraceEventRecord` entries in `TRACE_EVENTS` for traced surface interactions and non-sequential trace terminal policy, and `SceneBundle` consumes those records into read-only canonical `RayEvent3D` surface/terminal events with typed terminal point/direction geometry, folded detector terminal provenance, event-owned display `RayPath3D` geometry, Ray Events CSV export, event-backed Ray/Trace Path Inspector hit rows, event-backed detector/path analysis records, and event-backed Gaussian branch-q diagnostics;
- but the UI is still primarily row-prescription driven, with non-sequential behavior selected by heuristics and special surface rows.

Estimated status:

- **Non-sequential tracing plumbing:** 98% present.
- **North Star invariant enforcement:** 97% present.
- **3D scene with 2D projections:** 91% present.
- **Main remaining gap:** finish replacing legacy scalar `PrevN` mirrors at the remaining compatibility boundaries, then finish moving display clipping and plot annotations behind the canonical event table.

## Progress Snapshot

| North Star area | Current status | Progress | Recent movement |
| --- | --- | --- | --- |
| Native non-sequential tracing | Partially achieved | `█████████░ 98%` | Branch snapshots and raykeeper terminal events now preserve final `NonSequentialRayState` medium/index/inside-volume stack in addition to using ray-state incident index for surface physics. |
| 3D scene with 2D projections | Improving | `█████████░ 91%` | Ray display filtering and endpoint marker legends now use projected terminal status from `RayEvent3D` terminal records, while the vendor prism Sphinx page shows the generated penta/right-angle cascade with equal port/fold lengths and the right-angle hypotenuse as Uncoated/TIR. |
| Separate sources, objects, detectors | Partially achieved | `██████░░░░ 63%` | Explicit Detector metadata now terminates non-sequential rays with detector media-state and interaction records instead of relying on incidental row position. |
| Event-law physics and diagnostics | Partially achieved | `█████████░ 97%` | Terminal `TraceEventRecord` rows now carry final medium state, so escaped, stopped, absorbed, detector, reflected, and transmitted paths have terminal media context instead of only surface-event media context. |
| Regression coverage for arbitrary prisms/solids | Improving | `█████████░ 98%` | Regression coverage now checks optical-solid media state, non-STL transitions, authoritative ray-state incident index selection, final branch/terminal media-state preservation, UI and saved/exported typed terminal policy records, branch child media-event population, media-stack diagnostics, detector-miss diagnostics, typed raykeeper-originated canonical ray-event export, event-backed inspector rows, event-backed detector analysis samples, and event-backed Gaussian q/frame records. |

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
- Non-sequential hit physics now uses `NonSequentialRayState.current_index` as the incident refractive index for ordinary surfaces, optical solids, scatter children, splitter children, and terminal surfaces; scalar `PrevN` is synchronized from the resulting state instead of being the authority.
- If the legacy scalar incident index diverges from `NonSequentialRayState.current_index`, the media event records an `incident_index_from_ray_state` diagnostic.
- Branch result snapshots now preserve final `NonSequentialRayState` fields as final medium, refractive index, inside-volume stack, and state method.
- `RayKeeper` now stores those final branch media-state fields and copies them onto terminal `TraceEventRecord` rows, so terminal events expose final media context even when the ray escaped without another surface hit.
- Runtime ray events now preserve `VOLUME_ID`, `MEDIA_IN`, `MEDIA_OUT`, `MEDIA_TRANSITION`, `MEDIA_STATE_METHOD`, `INSIDE_VOLUMES_BEFORE`, and `INSIDE_VOLUMES_AFTER`.
- Ordinary non-STL refractive hits now update the same ray state from surface material, e.g. `AIR -> BK7` at entry and `BK7 -> AIR` at exit.
- `ABSORB` surfaces, explicit Detector rows, and final target planes now stop rays through shared terminal media-state events instead of looking like ordinary anonymous transmission.
- Splitter and scatter branch children now use the same media-event helper as ordinary and terminal hits, so child rays carry consistent media transition and media-state method fields.
- Media-event records now include `MEDIA_STATE_DIAGNOSTIC`, so impossible volume-stack transitions are preserved with the ray event instead of being hidden behind a plausible path.
- Branch snapshots now preserve path-level termination diagnostics for no-next-intersection escape, failed candidate intersections, repeated-surface stalls, step-limit stops, and branch-result truncation.
- Raykeeper, `RayHit3D`, `RayPath3D`, scene ray hits, Ray Inspector, Trace Path Inspector, and CSV export now expose the same media-state and termination diagnostic fields.
- `RayKeeper` now emits typed kernel `TraceEventRecord` entries in `TRACE_EVENTS` for traced surface interactions, branch-terminal interactions, and UI non-sequential target/detector terminal policy without importing UI types.
- `SceneBundle` now converts retained raykeeper `TraceEventRecord` surface records into canonical read-only `RayEvent3D` events, preserves raykeeper-originated terminal policy and terminal point/direction geometry provenance on terminal `RayEvent3D` rows, and records `event_source=raykeeper_trace_events` in the Ray Events CSV/export table.
- UI non-sequential preview tracing now feeds `terminal_target_surface`, `terminal_detector_surfaces`, and `terminal_policy_source=ui_nonseq_trace_request` through launch metadata into `RayKeeper`.
- Saved/exported non-sequential trace requests now feed the same terminal policy fields with `terminal_policy_source=saved_nonseq_trace_request`.
- Scene terminal event geometry now prefers typed raykeeper terminal records, while filtered display-path surface ids and diagnostics are retained when they intentionally hide non-detector Image sentinel hits.
- `RayPath3D` display `points_world` and displayed `surface_ids` are now resynchronized from canonical `RayEvent3D` surface/terminal records when finite event geometry is available, with `display_geometry_source` and `display_geometry_diagnostic` provenance on each path.
- Folded-layout detector reach is now recorded by replacing the canonical terminal event with folded-display status metadata first, then synchronizing `RayPath3D.reaches_image` and termination state from that terminal event instead of setting path flags before terminal-event construction.
- The 2D projector and trace-preview summary now derive image/detector-hit display state from canonical terminal `RayEvent3D` metadata before falling back to the `RayPath3D.reaches_image` convenience flag.
- Layout-editor ray analysis and branch-inspector records now use the same terminal-event detector/image reach helper when a scene path is available.
- `ProjectedRay2D` now carries a compact terminal status such as `hit_detector`, `missed_detector`, `absorbed`, `escaped`, or `stopped`, sourced from the canonical terminal event when available.
- The 2D renderer, endpoint markers, marker legend, and ray-display filter now use projected terminal status instead of reading the detector-hit boolean directly.
- Raykeeper-originated surface events are filtered through the retained `RayPath3D.hits` steps, so stripped display-only or nonterminal hits do not reappear as canonical scene events.
- `SceneBundle.ray_events` and the Ray Events CSV export expose those events with stable ids, source/branch metadata, geometry vectors, media state, face provenance, power terms, termination reason, and diagnostics.
- `RayEvent3D` now carries source name/role/model, wavelength, branch power/phase, Fresnel/coating coefficients, separate media diagnostics, and separate face-match diagnostics.
- Ray Inspector and Trace Path Inspector now prefer canonical `RayEvent3D` surface events for their hit rows when a scene bundle is available, while retaining legacy raykeeper fallbacks.
- `scene_bundle_ray_analysis_records` now derives ray-level analysis records from canonical scene events for branch throughput, detector maps, path PSF/MTF, coherent detector, source illumination, and best-image detector RMS workflows.
- `_collect_ray_analysis_records` builds a scene bundle from the current traced system/rays when analysis runs before a display panel has populated `_last_scene_bundle`, so event-backed analysis is not dependent on opening an inspector first.
- Ray Inspector refresh/export and the Branch Gaussian q report now consume `_collect_ray_analysis_records`, so the visible diagnostic tables, copied reports, and CSV exports use the same canonical event-backed ray records as detector/path analysis.
- Source illumination auto-target selection now ranks terminal surfaces before intermediate hit surfaces, so event-backed aperture hits stay visible without stealing the default detector/image target.

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
- [`KrakenOS/TraceEvents.py`](KrakenOS/TraceEvents.py#L1) - typed kernel trace-event contract.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L189) - raykeeper `TRACE_EVENTS` production.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L214) - media-state and branch termination diagnostic raykeeper propagation.
- [`KrakenOS/UI/validate_interaction_accounting.py`](KrakenOS/UI/validate_interaction_accounting.py#L144) - non-STL media-state regression.
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L187) - `RayEvent3D`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1029) - raykeeper trace-event to `RayEvent3D` adapter.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1277) - canonical ray-event CSV records.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29063) - inspector hit rows derived from canonical ray events.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1182) - event-backed ray analysis records.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29617) - UI analysis collector backed by scene events.

Remaining gap:

- The UI data model is still row-first. `SurfaceRow` remains the central prescription object, with scene semantics stored in `advanced` metadata.
- Saved/exported layout tracing now shares the same trace-intent resolver as the live UI; remaining risk is ensuring every future scene trigger is added to that resolver instead of local call sites.
- Non-sequential preview failures now surface a diagnostic instead of silently falling back to sequential tracing.
- Mesh adaptation, hit-cell capture, runtime cell-to-face labeling, scene boundary-face promotion, runtime boundary index attachment, scene volume promotion, runtime volume index attachment, non-STL media-state updates, terminal media-state updates, authoritative ray-state incident-index selection, final branch/terminal media-state preservation, typed raykeeper-originated canonical surface/terminal events, event-backed display paths, folded terminal reach provenance, event-backed inspector rows, and event-backed detector/path analysis are now centralized enough to inspect. Remaining work is to remove the remaining scalar-index compatibility mirrors and to finish routing all display clipping and plot annotations through the same typed trace-event boundary.

### 2. Optical elements and rays are represented in 3D; 2D plots are projections of traced 3D data.

Status: **mostly achieved for preview/display, not yet universally enforced**.

What exists:

- `SceneBundle` carries sources, surface curves, surface meshes, ray paths, planes, labels, pick regions, bounds, and display metadata.
- `SceneBundle` carries `OpticalVolume3D` records for closed optical solids, including material and owning boundary face ids.
- `SceneBundle` also carries `BoundaryFace3D` records for optical-solid faces, which keeps CAD/STL face identity attached to the scene instead of only row `advanced` metadata.
- `SceneBundle` now carries typed raykeeper-backed `RayEvent3D` records beside `RayPath3D`, so display and export can inspect a path as ordered 3D events rather than only as plotted line segments.
- The non-sequential scene graph shows optical volume nodes beneath optical-solid rows, with boundary face nodes beneath the owning volume where available.
- `ProjectedScene2D` is explicitly a projected display shape.
- `project_scene_bundle` projects a full scene bundle into 2D.
- Ray paths and hit records are reconstructed from raykeeper data instead of being separate 2D-only simulations.
- The layout display now renders a user-selected primary YZ, XZ, or XY view together with auxiliary panes for the two unselected slices.
- The YZ/XZ/XY selector sits in the plot toolbar beside `Open 3D`, so 2D projection choice is treated as plot-view state rather than a left-panel prescription field.
- Saved layouts store the selected plane as Kraken UI state, and legacy `Vertical`/`Horizontal` settings normalize to the canonical YZ plane.
- The selected projection rebuilds row pick regions so clicking geometry in XZ or XY can still select the editable table row.
- The 2D projector and preview summary now read detector/image-hit status from terminal `RayEvent3D` metadata before using the path convenience flag, so projected visibility follows the same event table that CSV/export and inspectors use.
- The vendor prism placement Sphinx page now documents the generated `attachment/penta.py` YZ cascade with a penta-prism orientation example and a right-angle-prism orientation example, equal-length visual port/fold guides, the 42779 ray sequence matching the snapshot, and the 32336 hypotenuse assigned as `Uncoated` / TIR.
- The auxiliary and selected non-YZ slices use traced 3D ray coordinates and 3D mesh outlines, which is a direct step toward treating every 2D plot as a projection of the same 3D scene.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L247) - `SceneBundle`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L322) - scene-bundle volume and boundary-face promotion.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1029) - raykeeper trace-event to `RayEvent3D` adapter.
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
- Event-backed source illumination keeps intermediate aperture/object hit events available for manual analysis while defaulting Auto target selection to terminal detector/image surfaces when rays reach them.
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
- Impossible volume-stack transitions now emit `MEDIA_STATE_DIAGNOSTIC`, currently covering duplicate volume entry, exit without prior entry, and exits that leave the volume stack unchanged.
- Path-level ray records now emit termination diagnostics such as detector/image miss after prism exit, no downstream object intersection, candidate surface intersection failure, non-sequential limit exceeded, and branch-result limit reached.
- Ray Inspector, Trace Path Inspector, and their CSV exports include the same volume/media-state and path termination diagnostic columns so the state is inspectable outside the plot.
- Canonical read-only `RayEvent3D` records now combine typed raykeeper-originated surface events and scene-synchronized terminal events into one table with stable event ids and explicit event-source metadata.
- The Ray Inspector window now offers a separate Ray Events CSV export, making the event-law table directly inspectable in browser/spreadsheet workflows without scraping the plot.
- Ray Inspector and Trace Path Inspector now consume canonical `RayEvent3D` surface events for hit rows when a scene bundle is present, so the UI tables carry the same stable event ids as the Ray Events CSV.
- The canonical event table now carries wavelength, Fresnel/coating response coefficients, separate media diagnostics, and separate face-match diagnostics instead of only a combined diagnostic string.
- Branch throughput, detector-map, path PSF/MTF, coherent detector, source illumination, and detector RMS analysis now call a scene-event ray-analysis adapter before falling back to legacy inspector records.
- Branch Gaussian q diagnostics and Gaussian local-frame validation now use the same scene-event ray-analysis adapter, including event-derived T/S/K frame fields.
- Detector/path validation now asserts that detector and coherent-detector samples are sourced from `ray_events`.

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
- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L187) - canonical `RayEvent3D` event fields.
- [`KrakenOS/TraceEvents.py`](KrakenOS/TraceEvents.py#L1) - typed kernel trace-event contract.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L189) - `TRACE_EVENTS` production from raykeeper arrays.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1029) - raykeeper trace-event to `RayEvent3D` adapter.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1277) - canonical ray-event record export.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L2675) - optical-solid hit media and volume-record bridge.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L28931) - Ray Inspector and Trace Path Inspector volume/media-state and termination diagnostic columns.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29063) - `RayEvent3D` to inspector-hit adapter.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29979) - Ray Events CSV export.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L31211) - path throughput from event-backed analysis records.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L31821) - detector-path samples from event-backed analysis records.
- [`KrakenOS/UI/validate_branch_analysis.py`](KrakenOS/UI/validate_branch_analysis.py#L149) - regression for detector samples sourced from canonical ray events.

Remaining gap:

- `NsTraceLoop` failure now clears the attempted raykeeper output and raises a UI diagnostic; sequential fallback is suppressed for non-sequential-required scenes.
- Some physics events are classified too generically in scene display, especially diffraction.
- Some optical-solid face roles are display/metadata concepts but do not yet enforce complete face-native physics.
- Converted meshes, hit-cell metadata, scene volume records, terminal records, branch-child media records, explicit media-state event fields, path-level termination diagnostics, canonical read-only ray events, event-backed inspector rows, and event-backed detector/path analysis now solve the first inspectability problem: a ray event reports which volume or material medium it is entering, reflecting inside, transmitting through, splitting/scattering from, terminating on, exiting, or missing after a valid continuation, and reports obvious stack contradictions or branch truncation. The remaining deeper gap is to make this state the authoritative physics input for every surface family, especially nested/cemented volumes, instead of a diagnostic bridge around scalar index handling.

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
- Finish migrating any remaining downstream analysis services from inspector-specific hit dictionaries to the typed canonical ray-event path.

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

This is still a bridge, not the final tracer architecture. Optical-solid entry/exit now uses `inside_volumes`, ordinary Standard-surface hits now update the medium name from the refractive material, and branch/terminal event records share one event builder. Other surface families and analysis paths still depend on scalar refractive-index state and row ordering.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L95) - `OpticalVolume3D`.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L148) - scene optical-volume records.
- [`KrakenOS/UI/nonseq_output_ports.py`](KrakenOS/UI/nonseq_output_ports.py#L1352) - runtime optical-volume index attachment.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L60) - `NonSequentialRayState`.
- [`KrakenOS/KrakenSys.py`](KrakenOS/KrakenSys.py#L2675) - current optical-volume media bridge.

Expected fix:

- Make `NonSequentialRayState` the source of truth for `medium_in` and `medium_out` across all non-sequential hits, not just the event-export bridge.
- Replace remaining row-order/scalar-index media decisions with scene object/volume adjacency.
- Add diagnostics when the state stack and geometry disagree, for example an exit hit on a volume the ray is not inside.

### Display paths and folded reach now derive from canonical events

Risk: medium.

`RayKeeper` now produces typed `TraceEventRecord` entries in `TRACE_EVENTS` for ordinary, batch, and branch trace pushes. UI preview and saved/exported non-sequential requests also feed target/detector terminal policy into launch metadata, so typed terminal records carry `terminal_policy_source`, `terminal_target_surface`, `terminal_detector_surfaces`, `reaches_target`, `reaches_detector`, and terminal point/direction geometry. `SceneBundle` converts retained surface records into `RayEvent3D`, preserves raykeeper terminal policy on canonical terminal rows, and prefers typed terminal point/direction geometry while exporting that provenance and retaining filtered display-path surface ids when non-detector Image sentinels are intentionally hidden. `RayPath3D` display points and displayed surface ids are now resynchronized from canonical surface/terminal events when finite event geometry exists, and paths carry display-geometry provenance. Folded detector reach now updates the canonical terminal event with folded-display status, detector surface, and tolerance diagnostics before path state is synchronized back from events. Ray Inspector, Trace Path Inspector, branch throughput, detector maps, path PSF/MTF, coherent detector, and source illumination consume event-backed analysis records when available. The remaining transitional part is display clipping policy and plot annotations that still read `RayPath3D` convenience flags directly instead of querying the event table.

Relevant code:

- [`KrakenOS/UI/scene_geometry.py`](KrakenOS/UI/scene_geometry.py#L187) - `RayEvent3D`.
- [`KrakenOS/TraceEvents.py`](KrakenOS/TraceEvents.py#L1) - `TraceEventRecord`.
- [`KrakenOS/RayKeeper.py`](KrakenOS/RayKeeper.py#L189) - raykeeper trace-event producer.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1029) - read-only ray-event adapter.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L1182) - read-only ray-event analysis adapter.
- [`KrakenOS/UI/scene_builder.py`](KrakenOS/UI/scene_builder.py#L2412) - folded terminal event synchronization.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29063) - inspector adapter from ray events.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L29979) - Ray Events CSV export.
- [`KrakenOS/UI/layout_editor.py`](KrakenOS/UI/layout_editor.py#L53032) - UI non-sequential terminal policy launch metadata.
- [`KrakenOS/UI/source_trace_helpers.py`](KrakenOS/UI/source_trace_helpers.py#L409) - saved/exported non-sequential terminal policy launch metadata.
- [`KrakenOS/UI/validate_interaction_accounting.py`](KrakenOS/UI/validate_interaction_accounting.py#L399) - regression checks for typed raykeeper event records.
- [`KrakenOS/UI/validate_scene_sources.py`](KrakenOS/UI/validate_scene_sources.py#L652) - regression checks for saved/exported typed terminal policy records.
- [`KrakenOS/UI/validate_vendor_prism_42779.py`](KrakenOS/UI/validate_vendor_prism_42779.py#L1390) - penta-prism event export regression.

Expected fix:

- Move display clipping policy and 2D/3D plot annotations behind the canonical ray-event table instead of reading `RayPath3D` convenience flags directly.
- Add object id and fuller polarization payloads to `TraceEventRecord` as the upstream trace state becomes authoritative.
- Route plot geometry/annotation and remaining specialized reports through the same event table.
- Keep `RayPath3D` as a display/path convenience derived from canonical events, not the other way around.

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

   The bridge now exists for optical solids, ordinary Standard surfaces, absorber terminals, Detector terminals, target-plane terminals, and branch-child event export. The next step is to route nested/cemented volume boundaries through it with diagnostics when the state stack conflicts with geometry.

2. Make display paths event-owned.

   UI preview and saved/exported non-sequential traces now feed target/detector terminal policy into typed `TraceEventRecord` terminal rows, and `SceneBundle` preserves that policy plus typed terminal point/direction geometry provenance in canonical terminal events. `RayPath3D` display points and displayed surface ids now derive from canonical events when finite event geometry is available. Folded detector reach now updates the terminal event first and synchronizes path flags from that event. The next step is to move display clipping policy and plot annotations behind the same event-owned boundary.

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

   A typed raykeeper-originated read-only table now includes source id/name/role/model, wavelength, branch id/path/power/phase, surface id, event law/type, incoming/outgoing direction, normal, n0/n1, Fresnel/coating response, power in/out/loss, media state, face provenance, termination reason, UI and saved/exported non-sequential terminal policy, terminal point/direction geometry provenance, folded detector reach provenance, diagnostics, event-source provenance, and event-owned display-path provenance. Remaining fields include object id and fuller polarization payloads.

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

1. Add `Scene`, `OpticalVolume`, `BoundaryFace`, `RayState`, and `RayEvent` dataclasses. `BoundaryFace3D`, `OpticalVolume3D`, richer read-only `RayEvent3D` records, and typed raykeeper-originated `TraceEventRecord` entries now exist; `NonSequentialRayState` exists in the trace kernel as a media-state bridge; UI preview and saved/exported non-sequential terminal policy and terminal geometry now reach typed terminal records; `RayPath3D` display geometry and folded detector reach now derive from canonical events when finite event geometry is available. The remaining gap is to make display clipping, plot annotation, and authoritative media state come from that typed trace boundary.
2. Build a row-to-scene adapter from current layout rows and settings.
3. Promote the now-persisted CAD/STL `triangle_id -> face_id` mapping from row metadata into scene-graph `BoundaryFace` records. Initial `BoundaryFace3D` scene-bundle promotion and runtime boundary index attachment are complete.
4. Promote optical-solid rows into scene-owned `OpticalVolume` records. Initial `OpticalVolume3D` scene-bundle promotion, runtime volume index attachment, and volume entry/exit event labeling are complete.
5. Replace optical-solid hit handling with a scene tracer that tracks region/media state. Initial media-state tracking and event export are complete for optical-solid entry/internal reflection/exit, ordinary Standard-surface material transitions, absorber/detector/target terminal events, branch-child event records, volume-stack diagnostics, and path termination diagnostics. The remaining gap is to make the state stack authoritative for all non-sequential surface families.
6. Route 2D/3D plots, detector analysis, illumination reports, and CSV export through `RayEvent` records. Typed RayKeeper-backed Ray Events CSV export, Ray/Trace Path Inspector consumption, event-owned display path geometry, folded terminal reach provenance, detector/path analysis, source illumination consumption, and Gaussian-q branch analysis exist; the remaining work is to move display clipping policy, plot annotation, and any remaining specialized reports onto the canonical table.
7. Add diagnostics for every terminal condition and unsupported boundary law. Initial media-stack contradiction, detector/image miss, no-next-intersection, step-limit, and branch-truncation diagnostics are complete; next diagnostic targets are unsupported/ambiguous boundary laws and richer detector miss distance vectors.
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
