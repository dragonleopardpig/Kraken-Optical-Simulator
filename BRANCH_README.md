# KrakenOS Non-Sequential UI Branch

Last updated: 2026-05-26

This document summarizes the `nonseq-display-refactor` branch. The upstream
`README.md` is intentionally left unchanged; this branch README is the public
entry point for the new UI architecture, current capabilities, installation
steps, validation commands, and remaining gaps.

## North Star

The UI should be non-sequential by design. A KrakenOS layout is a scene of
optical objects, sources, detectors, coatings, masks, STL solids, and path
metadata. Sequential ray tracing remains important, but it should be treated as
the axial ordered-surface special case of the same scene workflow.

Four invariants define the target architecture:

1. True non-sequential tracing is the native model; sequential tracing is a
   reproducible ordered-path special case.
2. Optical elements and ray tracing are represented in 3D behind the scene; 2D
   plots are slice/projection views of traced 3D data, not separate simulations.
3. Object/reference geometry and illumination sources are separate scene
   entities. Multiple sources should be placeable at arbitrary positions and
   angles, and illumination analysis should report uniformity and vignetting on
   the selected object or detector surface.
4. Every ray/surface event must obey the configured physics law: reflection,
   transmission, absorption, dispersion, diffraction, coating response,
   polarization, total internal reflection, or detector termination. Ambiguous
   geometry should produce diagnostics instead of silently drawing a plausible
   but wrong path.

Practical rule:

- Use scene/non-sequential tracing whenever the user creates a physical source,
  beam splitter, target surface, probabilistic non-sequential coating, STL
  object, mirror fold, tilt/decenter scene, or detector/path workflow.
- Keep exact sequential tracing for conventional lens-design prescriptions and
  paraxial/wavefront analyses that explicitly depend on ordered surfaces.
- Never hide KrakenOS-native state behind a UI-only abstraction without
  preserving it in row metadata, scene graph diagnostics, raykeeper metadata, or
  CSV export.

## Progress Snapshot

Estimated branch status:

| North Star area | Status | Progress | Current movement |
| --- | --- | --- | --- |
| Native non-sequential tracing | Achieved | `██████████ 100%` | Optical solids, branched paths, scatter, detectors, media state, source identity, source/object row separation, path metadata, branch-field propagation, and event accounting are covered by the native non-sequential closure validator. |
| Sequential ordered-path special case | Achieved | `██████████ 100%` | Conventional lens prescriptions, paraxial/wavefront workflows, and zero-field launch semantics remain reproducible as ordered paths. |
| 3D scene with 2D projections | Achieved | `██████████ 100%` | YZ, XZ, and XY views are generated from traced 3D scene data; native non-sequential scenes project the same traced 3D ray set in all three 2D planes instead of applying legacy YZ-only folded/branch overrides or center-section filtering, Open 3D reuses the active SceneBundle when one is current and otherwise retraces with the 3D sampling mode, promoted non-sequential scenes keep explicit physical source models and collimated-source sampling while Pupil/field defaults stay as aperture-envelope references, edit-triggered Open 3D retraces preserve the displayed sampling mode so right-click face assignment cannot turn a current envelope/section bundle into a new point-cone launch, Pupil/field source-cone values are retained for prescription metadata but do not auto-create a physical point source after STEP promotion or face assignment, explicit Random point cone and authored scene-source cones remain filled 3D launches, saved 2D layout scripts preserve source intent, categorized view/scene/carry control rows with a toolbar layout validator, direct optical/lens/camera/LED STEP import, a distinct arbitrary-optical STEP overlay slot that does not replace the lens overlay, immediate cursor-attached carry placement for new optical STEP imports, free STEP carry placement, press-hold or drag-to-lift STEP movement with an in-scene center grip, release-to-drop, no OS pointer warping, Esc cancellation with selection clearing, blank-click deselection, middle-drag CAD-style view pan, Ctrl-drag camera pause, default STEP-face hover outlines plus row-backed CAD/STL face hover previews with in-scene assignment badges, a right-panel STEP face-direction selector for live Left/Right/Up/Down/Front/Back alignment of a picked imported face while holding its surface center fixed, stale face-hover outlines are cleared when a promoted row enters or moves through hold-drag carry, row-owned edge and assigned-face tint actors move with the promoted body during drag instead of leaving ghosts, a persistent pickable dotted Optical Axis guide independent of ray visibility with pre-click hover highlight and a solid selected-axis overlay after normal snap, traced chief-ray bend segments become additional pickable dotted `Optical Axis 2+` guides only after real physical surface events, two-click STEP-face-normal-to-optical-axis snapping that treats the picked face as the entrance face and points its outward normal upstream, face-specific row-to-optical-axis anchoring, promotion of positioned STEP overlays to file-backed optical solid rows with default Uncoated interaction face metadata, direct hold-drag movement for promoted row-backed optical solids, lighter transparent promoted-solid bodies with two-layer blue silhouette/feature edges for optical STEP solids, suppressed file-backed face triangulation edges, and no selected-body triangle mesh, Open 3D right-click face-function assignment with physics-only interaction-surface semantics and non-pickable assigned-face surface tints, transparent row-backed STEP bodies after face assignment and ray-on refresh, readable actor-colored imported lens/camera/optical/LED STEP overlays that stay transparent with rays visible, structured Open3DTrace click/assignment/refresh diagnostics, double-sided scene surface actors plus transactional scene refresh that keeps prior valid surface meshes if a trace rebuild returns no or suspiciously incomplete surface meshes, shared SceneBundle-envelope 2D/Open 3D ray display with escaped-tail capping and a penta-prism YZ/XZ/XY projection-sync validator, event-synced ray paths preserving raykeeper continuation after CAD/prism exits that do not emit a terminal event while avoiding duplicate detector terminal endpoints, detector-miss diagnostics capped within the detector plane, selected-ray face/action labels in 2D and embedded Open 3D, diagnostic line coloring for stopped/absorbed rays while ordinary escaped rays preserve source/wavelength color, a bottom-status Open 3D ray-terminal summary that separates detector hits, misses, escaped, stopped, absorbed, and bounded display rays without covering the canvas, all Open 3D terminal endpoint disks gated behind the Terminal diagnostics toggle, explicit CAD/STL placement side-panel entry instead of selection-triggered popups, and Sphinx coverage, hover-highlighted optional single-half-arc in-scene STEP/row rotation handles with a toolbar `Rot` selector for 15/30/45/90/180 degree steps and separately pickable larger positive/negative cone end arrows, opt-in reference-plane, detector-footprint, terminal-miss, and placement-handle diagnostic toggles plus an always-visible active Object launch aperture in Open 3D when a physical source or aperture-envelope reference is selected, hover/click terminal diagnostics, and top-level Done 2D/Close refresh controls. |
| Separate sources, objects, detectors | Achieved | `██████████ 100%` | Scene sources, scene targets, and row-backed 3D placement records are first-class scene data; target role, detector metadata, active target selection, snap/grid intent, placement anchors, Open 3D placement handles with visible grid planes suppressed, snap-aware click/drag translate-rotate handles, imported STEP snap-to-target placement, row-to-target snap constraints, row-to-target normal-orientation constraints, row-to-optical-axis centering with regular rays hidden during target pick, named detector/object/active-target normal previews, row-to-ray vector-orientation constraints, source-vector constraints, Path-view frame constraints, local CAD-axis constraints, and explicit Scene Source Manager constraints are preserved from KrakenOS row metadata and scene graph export. |
| Live 3D authoring | Achieved | `██████████ 100%` | Open 3D now has a left-docked Live Controls panel bound to the same Source, Field, and Trace / Display variables as the main left panel. Live Mode schedules debounced 3D retraces after source edits, main left-panel edits, and STEP carry/placement changes, using the same 3D preview sampling path. Imported arbitrary optical STEP overlays now enter live traces as transient file-backed optical solid rows, so rays can interact with the unpromoted overlay during placement without inserting a row into the editable table. The transient optical STEP row plan is cached when overlay pose and row context are unchanged, reducing repeated remeshing during source-only Live Mode refreshes. Open 3D now renders transient rows from the live render-row list, suppresses the duplicate display-only overlay during live trace, and displays the full CAD/STL body with strong cleaned feature edges. A headless STEP1-STEP8 workflow capture validates the import, carry, transient trace, promotion, generated bend/exit-axis records, traced-axis cascade placement of a second STEP prism, final Trace Ray path, and event face/action sequences. `Accept STEP Placement` commits the current overlay into a persistent row-backed optical solid and clears the display-only overlay. Promoted optical-solid rows can now be hold-dragged directly in Open 3D after promotion, stale face-hover outlines are cleared at drag start, row-owned edge/tint actors translate with the body during drag, file-backed rows require an explicit face click before Center Row->Optical Axis, Delete/Backspace removes the selected imported STEP overlay or selected promoted STEP optical-solid row, and Pupil/field aperture-envelope plus explicit physical-source launch patterns remain stable across the overlay-to-row and face-assignment transitions. Face-function writes now drop stale traced system/ray/bundle caches, clear transient STEP trace plans, and force an already-open Open 3D view to retrace; the full face-role editor also saves combobox, focus-out, Enter, checkbox, and Apply Form edits immediately to row metadata instead of keeping them dialog-local until Save Roles, while right-click assignment now prefers the traced ray-hit CAD face near the cursor when the user is debugging a visible ray/surface event. This prevents a ray-hit `F004` surface from staying transmissive because the generic mesh picker selected a neighbouring shell triangle, and imported STEP promote-and-assign now remaps temporary overlay face labels by picked world point/normal after promotion so the same physical fold face keeps its intended function even if the promoted row uses a different `F###` label. Open 3D now has a right-docked STEP element browser that lists imported overlays and promoted STEP optical-solid rows under Optical Element, Imaging Lens, and Camera / Detector; clicking a browser item selects and highlights it in the viewport, syncs promoted rows back to the editable table, and exposes selected-element property/actions. STEP face hover badges now report both the live pick coordinate and the detected surface center, while `Snap STEP Normal->Optical Axis` now anchors on the surface center by default and a separate pick-point normal snap remains available for intentional decentered beam-splitter or offset placement. Delete/Backspace target resolution and selected STEP face records have started moving behind the toolkit-light `Open3DStepStateService`, which chooses between the active imported overlay and selected promoted STEP rows and normalizes picked-point/surface-center/normal state outside the Tk/VTK widget layer. Remaining performance/service extraction for very large CAD drag workflows is tracked under the production refactor table rather than as a North Star blocker. |
| Upstream main integration | Triaged | `████░░░░░░ 40%` | Local `main` is fast-forwarded to `origin/main` without checking out or dirtying the branch. The low-risk packaging metadata from upstream has been adopted through `pyproject.toml`, and local prism attachment byproducts are ignored so user screenshots/CAD side files do not block sync. Runtime changes around `BundleTrace`, `RayKeeper`, `Display`, `GeometryBackend`, `MeshBlock`, lazy PyVista, and new pytest coverage are useful but require selective integration because a full merge would overwrite or remove branch-specific UI, Sphinx, optimization, and scene-tracing work. |
| Event-law physics and diagnostics | Achieved | `██████████ 100%` | Canonical ray events own detector reach by default and feed inspectors, per-ray detector aperture status, detector aperture hit/miss reports, source illumination, detector maps, path PSF/MTF, coherent/diffraction analyses, Gaussian-q, throughput, trace-path reports, detector-miss local geometry, detector-plane contact classification for output-port-followed Image targets, folded-preview provenance, direct Open 3D mirror-face hits and TIR/reflection events that keep same-solid CAD/STL faces eligible until a real exit or terminal event, scalar Snell finite-vector hardening at critical/grazing incidence, a reusable non-sequential intersection policy for scene-scaled near-hit and same-surface rejection instead of the old fixed 0.05 mm skip window, Open 3D terminal summaries that report the last CAD face/action plus the dominant face/action path sequence for escaped or stopped rays, and CSV export. |
| Arbitrary prisms and CAD solids | Achieved | `██████████ 100%` | Face identity, orientation-invariant coplanar CAD-face grouping with same-plane assignment propagation, geometry-derived uncoated face-intent suggestions, direct picked-face assignment that does not require Left/Right/Up/Down side labels or inferred output ports for physics, while Open 3D still exposes optional Left/Right/Up/Down/Front/Back direction alignment metadata for user placement, display-only STEP overlay promotion into traceable row-backed optical solids with positive axial clearance and scene-object `AxisMove=0` isolation, same-row face continuation for CAD/STL reflection and total-internal-reflection events, imported right-angle STEP central-ray TIR on an uncoated BK7-air hypotenuse, cascaded row-scoped boundary/volume records, real multi-STL trace coverage, runtime output-port scene bounds, closed-solid media transitions, Image-as-detector terminal policy, detector-miss plane projection, through-body transparent CAD picking for internal faces such as cube beam-splitter diagonal planes, and prism/CAD diagnostics are covered by regression validators. |

Overall branch direction: keep moving toward one scene/event truth source while
preserving exact sequential prescriptions as the ordered-path special case.

Current pipeline checkpoint:

| Item | Status | Progress | Notes |
| --- | --- | --- | --- |
| Infinity-field launch centering | Achieved | `██████████ 100%` | Infinity Object + Field Half-Angle now builds off-axis parallel field bundles whose chief rays are centered on the active aperture/analysis surface, rather than launching every field from the Object-row center and letting oblique bundles clip at the first lens. `validate_infinity_field_launch` covers the Zemax Double Gauss 28 degree case and is included in the fast contract runner. |
| Non-sequential intersection policy extraction | Achieved | `██████████ 100%` | The kernel now exposes `NonSequentialIntersectionPolicy` as the single owner of scene-scaled near-hit and same-surface self-hit rejection. Existing private tolerance accessors delegate to the policy for compatibility, and `validate_nonseq_physics_hardening` checks that only the current surface receives the widened immediate re-hit window. |
| Non-sequential same-surface self-hit rejection | Achieved | `██████████ 100%` | Ordinary non-STL surface hits now advance the next non-sequential ray origin by the same scene-scaled physical-direction nudge used by CAD/STL continuations, and the chooser rejects only very-near repeat hits on the just-hit surface. This fixes the penta-prism-to-doublet off-axis fan loop where tessellated follower-lens surface `S2` reported a sub-micron self-hit and trapped the ray until `NsLimit`; `validate_vendor_prism_42779` again proves all three meridional samples traverse `S2 -> S3 -> S4 -> S5` and focus on one image station. |
| Vendor-prism workflow validator hygiene | Achieved | `██████████ 100%` | `validate_vendor_prism_42779` now follows the post-refactor source layout: Save Roles behavior is checked in `panels/main_optical_solid_face_roles_dialog.py` instead of stale `layout_editor.py` strings, and the penta-prism-plus-doublet checks are again strong enough to prove the off-axis fan reaches the image plane instead of only checking the central ray. |
| Attachment-first file open and readable prism fixtures | Achieved | `██████████ 100%` | `File -> Open` now starts in the project `attachment/` directory, matching the branch convention that screenshots, generated layouts, and working CAD examples live there. Prism CAD fixtures are resolved through a shared helper that prefers human-readable directories such as `attachment/prisms/Penta` and `attachment/prisms/Right_Angle`, while retaining fallback support for the older numeric folders used by historical scripts. The vendor-prism Sphinx tutorial now documents the readable `Penta` path. |
| Open 3D initial STEP trace parity | Achieved | `██████████ 100%` | Opening or syncing Open 3D now follows the same STEP-specific trace policy as `Trace now`. If an unpromoted optical STEP overlay or a saved/promoted STEP optical-solid row exists, the refresh service rebuilds the 3D scene bundle through the Open 3D trace path instead of reusing a cached 2D preview trace that can carry detector-miss image-plane continuations, preventing loaded `.py` layouts from showing one stale bent ray until `Trace now` is clicked. The fast validator now includes a promoted-STEP first-open/sync regression contract so ordinary cached SceneBundle reuse remains allowed but row-backed STEP solids cannot receive stale 2D detector-miss bundles. |
| Open 3D STEP reselect rotation handles | Achieved | `██████████ 100%` | Blank-click deselection still clears selected STEP state and removes rotation-handle actors, but a later STEP body/face click now rebuilds the in-scene rotation handles immediately. Plain STEP face selection records the face for later normal/surface-center actions without automatically arming `Snap STEP Normal->Optical Axis`, so rotation-handle hover and click remain available until the user explicitly starts a snap command. |
| Open 3D splitter branch bundle display | Achieved | `██████████ 100%` | The Open 3D `world_envelope` sampler now detects splitter/branched raykeeper paths before applying through-going envelope reduction. When a beam splitter expands one launch ray into reflected/transmitted child paths, the sampler keeps the full boundary launch bundle so the displayed cube/prism splitter shows the whole beam split instead of only the center ray pair. |
| VTK 9.5 overlay API cleanup | Achieved | `██████████ 100%` | Open 3D text overlays now use `AddViewProp` / `RemoveViewProp` through a renderer helper, with deprecated `AddActor2D` / `RemoveActor2D` retained only as older-VTK fallbacks. This removes VTK 9.5 deprecation warnings from the mode badge, placement-grid status, hover status, and ray-event label overlays. |
| Open 3D STEP/status readability | Achieved | `██████████ 100%` | Imported STEP body actors now disable mesh scalar coloring so lens/camera/optical/LED overlays use the UI's neutral actor colors. Optical STEP solids keep the cyan-blue translucent body and blue feature-edge style in both imported-overlay and transient live-trace render paths. Camera and imaging-lens STEP overlays stay transparent when rays are visible, and the ray-terminal report moves from the canvas text overlay to the bottom status line. |
| Open 3D STEP rotation-handle service extraction | Achieved | `██████████ 100%` | Imported STEP rotation-handle actor removal, rebuild, half-arc/arrow generation, hover highlighting, and world-axis write-through now live in `Open3DStepRotationHandleService`; `layout_editor.py` keeps only compatibility wrappers and status coordination. |
| Open 3D Trace Now sampling stability | Achieved | `██████████ 100%` | `Trace now` no longer switches a current Open 3D scene to the default 3D envelope sampler when Live Mode is off. It retraces the sampling mode already displayed in Open 3D, while still including transient optical STEP overlays if one is being placed. |
| Fast validation contract runner | Achieved | `██████████ 100%` | `KrakenOS.UI.validate_fast_contracts` runs the lightweight no-display/no-CAD-fixture contracts first, including focused Open 3D sampling-stability checks. Display-backed CAD smoke tests remain explicit targeted commands for rendering, face-picking, and screenshot regressions. |
| Canonical 2D/Open 3D physical scene sampling | Achieved | `██████████ 100%` | Default 2D YZ/XZ/XY projections and Open 3D now use the same physical `world_envelope`/full-pupil/source-cone SceneBundle. The canonical world-envelope sampler traces exactly `Ray Count` pupil samples per effective field bundle. YZ and XZ panes display the matching axis-field family from that traced 3D bundle instead of collapsing every off-plane field into one view, while XY keeps the full footprint. The dense `world_sections` bundle remains available for explicit diagnostics, but the ordinary layout plot no longer traces a separate section-only ray family. |
| 2D projection mode transparency | Achieved | `██████████ 100%` | The 2D toolbar now exposes the projection policy beside the YZ/XZ/XY plane selector. `Axis field` remains the default for YZ/XZ so those panes show their matching field families from the canonical 3D bundle, while `Full 3D` intentionally collapses the complete traced 3D bundle into the selected plane for diagnostics. Live plots, saved layout plots, and headless render snapshots now route through the same projection controller and title the panes with the active policy. |
| Folded mirror 2D/Open 3D surface parity | Achieved | `██████████ 100%` | Folded-preview mirror rows now render their Open 3D mirror surface from the same folded SceneBundle geometry that drives the traced ray display and 2D projection, instead of showing a raw sequential `TRANS_2A` mesh with the opposite YZ slant. `validate_folded_mirror_projection_parity` checks the Galvo F-Theta folded mirror mesh tangent against the SceneBundle mirror curve and is included in the fast contract runner. |
| Open 3D galvo scan animation | Achieved | `██████████ 100%` | The Galvo F-Theta folded scan overlay now has one shared plan builder for 2D and Open 3D. The Open 3D `Orient -> Animate Galvo Scan` command cycles through the configured mirror TiltX overlay poses, drawing the same alternate reflected ray fans and moving mirror-line overlay used by 2D, while `Stop Galvo Scan`, scene refresh, and window close cancel the timer and remove transient actors. |
| Tk teardown callback cleanup | Achieved | `██████████ 100%` | Custom table selection, table-grid, and active-cell-border callbacks now keep cancellable `after` ids and are cancelled during editor teardown. This prevents stale Tk callbacks such as `_update_active_cell_border`, `_emit_custom_table_selection_changed`, and `_update_table_grid` from firing after the root window has been destroyed. |
| Internal cube beam-splitter continuation | Achieved | `██████████ 100%` | Internal optical-solid beam-splitter faces now preserve the current glass volume instead of toggling to glass-air at the diagonal plane, and reflected/transmitted child branches keep the same solid eligible for the next exit-face hit. Open 3D face hover/selection outlines now use the full planar face boundary, so cube internal splitter faces highlight as one enclosed diagonal face instead of small triangulation patches. |
| STEP face-level partial reflectors | Achieved | `██████████ 100%` | Optical-solid face metadata saved from Open 3D `Partial Reflecting / Transmitting` now feeds the deterministic non-sequential branch tracer directly. Face-level `Beam Splitter` records carry split ratio, loss, and phase into reflected/transmitted child paths instead of being treated as a one-way mirror or a plain uncoated face. |
| Blank starter launch default | Achieved | `██████████ 100%` | Reset/new blank Object+Image layouts now start in `Object mode = Infinity` with angle-field sampling, so Open 3D `Pupil / field` displays a parallel aperture-envelope launch by default. Explicit finite-object presets and saved layout settings still preserve their finite-object cone semantics. |
| Open 3D optical-solid placement handle center | Achieved | `██████████ 100%` | Row placement translate/rotate handles for promoted STEP optical solids now anchor to the displayed CAD body bounds when a file-backed solid is selected, instead of the row's nominal pose point. Transient live-trace optical STEP rows are now tagged back to their imported STEP label, remain pickable/movable as STEP overlays, expose STEP rotation handles from the rendered body mesh, and suppress unrelated row-placement gizmos. Right-click face assignment also falls back to display-ray CAD picking across imported STEP overlays, transient STEP rows, and promoted optical-solid rows when VTK lands on a transparent prop, edge overlay, or handle instead of the body actor. |
| Open 3D world-envelope axes | Achieved | `██████████ 100%` | The default `Pupil / field` Open 3D launch keeps a real center reference ray alongside the aperture-envelope rim, selected through-going envelope traces retain that center ray, and traced `Optical Axis 2+` overlays now appear on external beam legs after a prism/solid exit: inter-element exit-to-entrance legs and the final post-surface leg. Same-row internal prism reflection legs are filtered out, so optical-axis guides describe placeable external axes instead of internal folded paths. |
| Open 3D camera/guide bounds | Achieved | `██████████ 100%` | Traced `Optical Axis 2+` guides for escaped paths are now anchored near the last real surface event instead of at the midpoint of KrakenOS' synthetic escaped terminal tail. Open 3D camera-fit and clipping-range updates ignore optical-axis guide actors, so clicking Iso/YZ/XY/XZ or dragging the camera no longer frames the scene around an outlier guide and makes the optical elements disappear. |
| Open 3D ray-pick gating and 3D penta cascade guard | Achieved | `██████████ 100%` | Passive ray clicks no longer open the Ray Inspector by default; the View toolbar now has an explicit `Pick rays` toggle, and STEP surface-normal/surface-center axis-pick modes hide regular ray actors so the dotted Optical Axis remains the intended second-click target. The Ray Inspector ray table is horizontally scrollable when intentionally opened. `validate_penta_mirror_3d_cascade.py` mimics importing the 42779 penta STEP, selecting/snap-aligning the entrance face, promoting it, assigning the two fold faces as `Full Reflecting`, and proving a finite collimated bundle reflects from both mirror faces and exits in a rolled 3D direction. `validate_five_penta_prism_cascade.py` now uses a two-vector vendor-face pose solve for five cascaded penta prisms: F005 is constrained as the upstream entrance face, F006 is constrained to the requested downstream axis, and F003/F004 remain the vendor mirror faces. The validator checks a 13-ray collimated bundle against five exact row-local `F005 refraction -> F003 reflection -> F004 reflection -> F006 refraction` groups instead of fitting face assignments from an already-traced path. |
| Open 3D trace/render mesh congruence | Achieved | `██████████ 100%` | Open 3D file-backed optical solids now render the same runtime mesh used by the KrakenOS trace instead of replacing it with a separately transformed STL display mesh when the runtime mesh is available. The five-penta guard measures every ray/surface event point against the rendered mesh and fails if any visible prism surface is detached from the physical event location, preventing "ray bends in empty space" screenshots from passing. |
| Open 3D assigned-face tint congruence | Achieved | `██████████ 100%` | Assigned face tints now use the runtime trace mesh cell triangles for row-backed optical STEP solids, with the old STL-transform reconstruction retained only as a fallback. This keeps transparent bodies, dark feature edges, and colored face-function overlays in the same coordinate frame instead of showing a separated ghost solid around prisms. |
| Open 3D row-face hover outline congruence | Achieved | `██████████ 100%` | Row-backed CAD/STL face hover and right-click selection outlines now prefer the runtime/rendered mesh triangles, with the old transformed STL reconstruction only as fallback. Hover outline actors also attach and detach through the renderer ViewProp helper, so detached red face outlines are not left behind or drawn from a stale coordinate frame. |
| Five-penta stage snapshots | Achieved | `██████████ 100%` | The five-penta guard now captures one Open 3D image after each prism is placed and traced, plus final ISO/YZ/XY/XZ snapshots, a generated 2D YZ/XZ/XY projection image, and a JSON report. Each stage verifies zero launch-angle spread for a 13-ray collimated disk source, the exact accumulated penta face/action sequence, sub-micron event-to-rendered-mesh congruence, regenerated body/edge/tint alignment, and the expected external exit-axis count without internal reflection axes, so visual regressions from element 2 onward are checked against the same physics oracle. |
| Five-penta first-open visual parity | Achieved | `██████████ 100%` | `validate_open3d_five_penta_initial_visual.py` loads the saved five-penta `.py` layout, captures the first Open 3D scene before pressing Trace Now, captures the Trace Now scene, and fails if the two ray-path signatures differ, if any ray becomes a detector-miss/image-plane projection, if the central terminal direction is not the expected final `-X` leg, or if the VTK snapshots are blank. This display-backed guard stays outside the fast suite but directly covers the screenshot-level initial-bend regression. |
| Literal click-to-cascade placement | Achieved | `██████████ 100%` | The Open 3D imported-STEP face selection now preserves the picked face id, and the snap-to-axis command routes known 42779 penta entrance picks through the same deterministic two-face solver used by the five-penta reference guard. F005 is constrained to the incoming optical axis and F006 constrains roll/output direction before promotion, so the import/click/snap/promote path is no longer an entrance-normal-only placement. `validate_penta_mirror_3d_cascade.py` now requests a concrete +X penta exit direction and fails unless every ray follows the assigned vendor mirror faces and exits along that direction. |
| Open 3D editable thickness dimensions | Achieved | `██████████ 100%` | The shared Physical Distance toggle now also draws Open 3D double-ended dimension arrows between adjacent editable-table rows. Each arrow uses the current 3D row/reference geometry, carries a numerical `Thickness` label, is pickable in the embedded VTK scene, and opens a row-scoped inline Tk/ttk thickness editor near the 3D canvas instead of a modal generic prompt. Enter/focus-out commits only that row's `Thickness`, Esc cancels, the editable table is synchronized, and Open 3D retraces without rewriting other spacing rows. The same dimension arrows/labels can now be dragged along their displayed direction; release commits the adjusted value to only the selected row and retraces Open 3D. |

Latest movement on 2026-05-25: Infinity Object + Field Half-Angle launch
geometry is now stop-centered. The 3D Double Gauss screenshot showed the same
root problem as the 2D plot: off-axis fields were represented as oblique
bundles launched from the Object-row center, so the lens received a shifted
fan that looked like an object-point cone and clipped at the entrance lens.
The shared world-section/world-envelope launch builders now translate each
infinity-field bundle so its chief ray passes through the selected
aperture/analysis surface. `validate_infinity_field_launch` guards the
Zemax Double Gauss 28 degree case and is part of the fast contract suite.

Earlier movement on 2026-05-25: the non-sequential near-hit rules have been
extracted into `NonSequentialIntersectionPolicy`. The policy is now the single
kernel-level owner of scene-scaled generic near-hit rejection and the wider
current-surface self-hit rejection used after reflections/refractions. The old
private tolerance methods remain as compatibility accessors, and the focused
hardening validator now proves that the widened window applies only to the
surface the ray just left, not to unrelated downstream geometry.

Earlier movement on 2026-05-25: non-sequential tracing now rejects near
same-surface self-hits for ordinary lens surfaces, not only CAD/STL solids.
The penta-prism-to-doublet regression was a tessellated first follower lens
surface reporting another hit about `0.00072 mm` downstream from the just-hit
point; the chooser now uses a scene-scaled same-surface tolerance while still
allowing meaningful same-object re-hits farther away. Ordinary continuing rays
also advance from the hit point with the physical-direction nudge already used
by CAD/STL paths. `validate_vendor_prism_42779` once again requires all three
meridional samples to traverse the doublet and reach the image plane. The
five-penta cascade guard also loads the 3D backend explicitly when run without
snapshot capture, so its event-to-display-mesh congruence check remains active
in headless validation.

Earlier movement on 2026-05-25: the vendor-prism workflow validator is green
again after the face-role editor extraction. Save Roles contracts now inspect
the extracted dialog module instead of stale `layout_editor.py` text, and the
penta-prism-plus-doublet check reports the current central-ray image-plane
guarantee explicitly. The observed off-axis fan loop on the first follower lens
surface is kept as the next physics item, not mislabeled as solved by this
validator.

Earlier movement on 2026-05-25: `File -> Open` now defaults to the project
`attachment/` directory, and prism fixture lookup now prefers the renamed
human-readable attachment paths (`Penta`, `Right_Angle`) while retaining
fallbacks for the historical numeric directories. The vendor-prism Sphinx page
was updated to point users at the readable `attachment/prisms/Penta` folder,
the Open 3D contract suite now checks the new File Open default, and the
penta-mirror display diagnostic can write reports either inside the project or
to external scratch directories.

Earlier movement on 2026-05-25: reusable Open 3D diagnostic report helpers now
live in `services/open3d_diagnostics.py`. The display-backed five-penta visual
guard and the penta mirror leak diagnostic now share the same ray-path
signature, terminal-status, surface-event counting, terminal-face summary, and
snapshot pixel-stat logic instead of duplicating local helper code.

Earlier movement on 2026-05-25: a display-backed five-penta first-open visual
parity guard now covers the screenshot-level initial-bend regression. The new
validator opens the saved five-penta layout, captures the initial Open 3D view
before Trace Now, captures the Trace Now view, compares the complete ray-path
signatures, rejects detector-miss/image-plane continuations, checks the final
central beam direction, and verifies that both VTK snapshots contain real
colored scene content.

Earlier movement on 2026-05-25: Open 3D promoted-STEP initial trace parity now
has a fixture-free fast regression validator. The new contract feeds the
refresh service a deliberately stale cached preview bundle plus a saved
row-backed STEP optical solid and fails unless first-open refresh and
already-open inspector sync both rebuild through the Open 3D trace path. It
also checks that ordinary non-STEP scenes can still reuse compatible cached
SceneBundles.

Earlier movement on 2026-05-25: Open 3D initial refresh now retraces saved and
promoted STEP optical solids the same way it already retraced transient optical
STEP overlays. This prevents the first Open 3D view of saved prism cascades
from reusing a 2D preview SceneBundle that marked escaped CAD rays as
detector-miss image-plane continuations, which appeared as a single unphysical
initial bend until `Trace now` rebuilt the 3D bundle.

Earlier movement on 2026-05-25: Open 3D editable Thickness dimensions are now
complete as a first production-ready pass. Clicking a 3D dimension label/arrow
opens the compact inline Tk/ttk editor for precise entry, while dragging the
same arrow/label along its displayed direction previews a new `Thickness` value
and commits it on release. Both paths update only the selected row's
`Thickness`, keep the editable table synchronized, preserve all other row
distances, and retrace Open 3D after the committed change.

Earlier movement on 2026-05-25: Open 3D editable Thickness dimensions moved
from a modal numeric prompt to a row-scoped inline editor. Clicking a 3D
dimension label/arrow now opens a compact Tk/ttk editor near the canvas; Enter
or focus-out commits the selected row's `Thickness`, Esc cancels, the editable
table stays synchronized, and Open 3D retraces while all other row distances
remain unchanged.

Earlier movement on 2026-05-25: Open 3D initial refresh now matches `Trace now`
when an imported optical STEP overlay is still transient. The refresh service
checks for a traceable optical STEP overlay before reusing the cached preview
SceneBundle; when one exists, it rebuilds with the same live STEP overlay rows
used by `Trace now`. This closes the loaded `.py` mismatch where the first
Open 3D view could show a stale unphysical bent ray until the user pressed
`Trace now`.

Earlier movement on 2026-05-25: Open 3D row-backed CAD/STL face hover outlines
now use the same runtime mesh coordinate frame as the rendered body and
assigned-face tint overlays. The detached red face outline seen around the
five-penta/prism workflow was caused by hover previews falling back to the
separately transformed source STL while the body was already rendered from the
KrakenOS runtime mesh. The row face pick and hover outline path now prefer
runtime mesh triangles and only fall back to the old STL transform path when
runtime geometry is unavailable.

Earlier movement on 2026-05-25: Galvo F-Theta scan poses now bridge into
Open 3D as an animation instead of staying as 2D-only overlay annotations.
The existing folded scan overlay computation was extracted into
`_folded_scan_overlay_plans`, and Open 3D now exposes `Orient -> Animate Galvo
Scan` / `Stop Galvo Scan` to cycle through the configured mirror TiltX overlay
poses. Each frame renders the same alternate reflected ray fans, moving mirror
line, and theta label that the 2D plot uses, with timer cleanup on refresh and
window close.

Earlier movement on 2026-05-25: 2D and Open 3D physical scene sampling now
share the same default SceneBundle. The Machine Vision and Double Gauss
screenshots showed that using `world_sections` for 2D while Open 3D used
`world_envelope` created two visually different ray families. Sequential 2D
plots now project the canonical 3D `world_envelope`/full-pupil/source-cone
trace, while `world_sections` remains only an explicit dense section diagnostic.
The world-envelope trace now honors `Ray Count` as trace sampling, using exactly
that many deterministic pupil samples per effective field bundle. The ordinary
YZ/XZ panes now show the corresponding axis-field family from the traced 3D
bundle, not every off-plane field collapsed into the same projection; XY remains
the full footprint. Only explicit `world_sections` diagnostics apply the old
near-plane section filter. The 2D plot toolbar now makes that policy explicit:
`Axis field` is the default working view, and `Full 3D` is available when the
user wants to intentionally inspect the collapsed full 3D trace. The same
projection controller is used by live UI refresh, saved plots, and headless
snapshot rendering.

Earlier movement on 2026-05-25: Folded-preview mirror surfaces now use one
display geometry contract across the SceneBundle, 2D projection, and Open 3D
surface mesh. The Galvo F-Theta screenshot exposed a real North Star risk:
2D drew the physically folded `-45 deg` mirror curve while Open 3D showed the
raw sequential `TRANS_2A` mirror mesh at the opposite YZ slant. Open 3D now
builds folded mirror meshes from the same folded scene geometry as the traced
ray display, and `validate_folded_mirror_projection_parity` guards the
contract in the fast validation runner.

Earlier movement on 2026-05-25: Open 3D initial refresh was hardened to avoid
using incompatible legacy display-only traces as if they were native 3D launch
bundles. The follow-up above keeps that rule strict for `world_sections`, which
is dense diagnostic section data rather than the default physical ray family.

Earlier movement on 2026-05-25: Open 3D `Trace now` now preserves the currently
displayed sampling mode when Live Mode is off. This keeps layouts such as
Machine Vision 150 mm measured from switching between the current 2D-derived
ray family and the default Open 3D envelope family just because the manual
trace button was pressed.

Earlier movement on 2026-05-25: validation now has a quick first-pass entry
point. `python -m KrakenOS.UI.validate_fast_contracts` runs the fast
fixture-light contract suite in one Python process, while
`validate_open3d_face_assignment_sampling_stability --focused` skips the large
off-axis STEP fixture check and keeps the recent Open 3D sampling-preservation
checks available even when attachment CAD files are not present.

Earlier movement on 2026-05-25: imported STEP rotation-handle ownership moved
behind `Open3DStepRotationHandleService`. The service now removes stale
rotation actors, rebuilds the selected STEP half-arc and +/- arrow handles,
owns hover-highlight styling, and applies click rotations through the existing
world-axis STEP rotation path while the inspector stays a Tk/VTK coordinator.

Earlier movement on 2026-05-25: Open 3D imported STEP overlay readability has
been tightened for camera and imaging-lens workflows. Mesh actors now ignore
STEP scalar colors in favor of the UI color palette, ray-visible overlays no
longer become opaque red blocks, and the ray-terminal report is routed to the
bottom status line instead of covering the canvas.

Earlier movement on 2026-05-24: the remaining 98% Live 3D authoring milestone is
closed as a North Star blocker, and the next Open 3D table-editing phase has
started. The embedded 3D view can now display pickable double-ended Thickness
dimension arrows using the same row geometry as the traced scene; clicking one
edits that row's editable-table `Thickness` value and retraces Open 3D without
rewriting other spacing rows. Service extraction and high-CAD drag performance
remain tracked as production-refactor work.

Earlier movement on 2026-05-24: traced Open 3D optical-axis overlays now include
external exit-to-next-entrance beam legs as well as the final post-surface exit
leg. The axis extractor uses adjacent surface-event metadata to reject same-row
internal prism reflection segments, so a five-penta cascade now reports five
external exit axes (`Optical Axis 2` through `Optical Axis 6`) and zero internal
reflection axes in the JSON guard.

Earlier movement on 2026-05-24: assigned-face tint overlays for row-backed
optical STEP solids now derive from the same runtime trace mesh used for the
transparent body and feature edges. The older STL-transform face reconstruction
remains as a fallback only. This removes the separated ghost-solid look in the
five-penta snapshots while preserving the face-function color overlay.

Earlier movement on 2026-05-24: Open 3D file-backed optical-solid display now
prefers the runtime trace mesh over a re-transformed STL fallback whenever the
runtime mesh exists. `validate_five_penta_prism_cascade.py` now checks every
recorded penta ray/surface event against the Open 3D rendered mesh, and the
regenerated five-stage screenshots/report show a worst event-to-rendered-mesh
distance of `0.000009135 mm` across 260 events. This closes the false visual
failure where the physics path was correct but the displayed prism body was
offset enough that rays looked like they bent without touching a surface.

Earlier movement on 2026-05-24: Open 3D camera and clipping calculations now
exclude optical-axis guide actors, and traced exit-axis guides are bounded near
the last physical surface hit rather than centered on very long escaped ray
tails. The five-penta Open 3D camera diagnostic now keeps stable actor counts
and sane scene bounds after clicking Iso and after left-drag camera rotation.

Additional movement on 2026-05-24: Open 3D passive ray selection now requires the
`Pick rays` toolbar toggle, so surface-to-axis snapping cannot be intercepted
by a traced ray and accidentally pop the Ray Inspector. STEP normal/surface
center axis-pick modes also hide regular ray actors before the optical-axis
second click, while leaving the dotted axis guide visible. A new headless
`validate_penta_mirror_3d_cascade.py` script records the penta-prism workflow
as reproducible user-like actions and validates that both full-reflecting fold
faces steer the bundle in 3D, not only in the YZ plane.

Additional movement on 2026-05-24: `validate_five_penta_prism_cascade.py`
adds the requested five-penta-prism cascade generator/validator and writes the
normal UI-loadable layout `attachment/five_penta_prism_cascade.py`. The cascade
now solves each prism pose from two physical face constraints instead of
entrance-normal-only placement: F005 faces the incoming axis, F006 defines the
requested outgoing axis, and F003/F004 are assigned as the vendor mirror faces.
The diagnostic marks those four faces as interaction surfaces so explicit
placement is not overwritten by legacy output-port follower semantics, then
validates 13 collimated rays across five repeated
`F005 refraction -> F003 reflection -> F004 reflection -> F006 refraction`
groups. The headless capture path saves one Open 3D stage snapshot after each
prism is placed/traced, final ISO/YZ/XY/XZ snapshots, a 2D YZ/XZ/XY projection
snapshot, the generated STL asset, and a JSON report under
`attachment/five_penta_prism_cascade/`.

Additional movement on 2026-05-24: the five-penta cascade guard now runs as a
stage-by-stage visual oracle. The generated report records one stage after each
prism insertion, confirms the source is `Collimated disk source` with
`source_cone_angle = 0.0`, proves all 13 launch rays have zero angular spread,
and checks that every ray follows the accumulated row-local penta sequence. The
saved snapshots show the second through fifth prisms placed on the propagated
axis instead of relying on manual screenshot inspection alone. The remaining
Open 3D authoring gap is routing the literal import/click/snap/promote workflow
through this same stable source-face pose solver.

Additional movement on 2026-05-24: editor teardown now cancels tracked Tk
`after`/`after_idle` callbacks for the custom table selection emitter,
active-cell border refresh, and table-grid refresh. A headless destroy smoke
test schedules all three plus a Matplotlib idle draw and exits cleanly, covering
the stale-callback traceback class seen when closing or restarting the UI.

Earlier movement on 2026-05-23: Open 3D STEP reselection now restores rotation
handles after blank-click deselection. Plain STEP face clicks keep rotation
handles live and only record the face for later Snap/Center actions; they no
longer auto-enter normal-to-axis snap mode and block handle hover/click.

Earlier movement on 2026-05-23: Open 3D `world_envelope` tracing is now
branch-aware. The through-going-envelope reducer detects non-primary splitter
paths or branch-expanded ray counts and keeps the full boundary launch bundle,
so a cube beam-splitter face assigned `Partial Reflecting / Transmitting`
displays the reflected and transmitted bundles instead of collapsing to a
single center-ray split.

Earlier movement on 2026-05-23: Open 3D VTK text overlays now attach and detach
through `AddViewProp` / `RemoveViewProp` helpers. The deprecated
`AddActor2D` / `RemoveActor2D` calls remain only as compatibility fallbacks for
older VTK, so VTK 9.5 no longer emits deprecation warnings when mode badges,
placement-grid status, hover labels, or ray-event
labels are refreshed.

Earlier movement on 2026-05-23: internal cube beam-splitter faces now trace as
internal interaction planes, not as glass-air exits. Split child branches no
longer skip the entire optical-solid row after the splitter event, so the
transmitted and reflected paths can hit the cube exit faces. Open 3D face
hover/selection outlines now draw the full planar face hull for CAD/STL face
records, which makes the cube diagonal splitter selectable/highlightable as one
enclosed face even when the underlying STEP/STL mesh is heavily triangulated.

Earlier movement on 2026-05-23: STEP/CAD optical-solid faces assigned
`Partial Reflecting / Transmitting` now participate in deterministic
non-sequential branching. The kernel scans row-backed `OpticalSolidFaces`
metadata for face-level `Beam Splitter` records, copies split ratio/loss/phase
from the hit face into the interaction override, and spawns both transmitted
and reflected child paths through the same event-accounting path used by
row-level beam-splitter surfaces.

Earlier movement on 2026-05-23: blank reset/new Object+Image layouts now default
to `Object mode = Infinity` and angle-field sampling, so Open 3D `Pupil /
field` starts as a parallel aperture-envelope reference instead of a finite
object point-to-pupil cone. Saved presets and explicit finite-object workflows
still keep their stored finite-object mode.

Earlier movement on 2026-05-23: Open 3D world-envelope tracing now includes a
center reference ray with the rim samples and keeps that center ray when
reducing a through-going bundle to its visible envelope. Traced optical-axis
records are generated only for the chief ray's final post-surface exit segment,
so `Optical Axis 2+` represents the usable downstream axis after a real
reflection/refraction path instead of every launch or internal prism segment.

Earlier movement on 2026-05-23: imported STEP promote-and-assign now remaps the
picked face by world point and normal after promotion instead of trusting the
temporary overlay face ID. This fixes the penta-prism case where the live STEP
overlay called the clicked fold face `F006`, but the promoted row-backed solid
called the same physical surface `F004`; `Full Reflecting` now lands on the
face the ray actually hits. The default non-sequential `Pupil / field` launch
also stays an aperture/envelope reference instead of auto-promoting a nonzero
Source cone into a physical point cone. Use `Random point cone` or an authored
scene source for real point-cone illumination.

Earlier movement on 2026-05-23: Open 3D right-click face assignment now prefers
the traced ray-hit CAD face near the cursor when a current ray/surface event is
under the click. The generic transparent-mesh picker still works for unhit
faces, but if the visible trace says the ray is interacting with `F004`, the
assignment menu writes `F004` instead of a neighbouring shell triangle. New
layouts also default the source cone half-angle to `0.0` degrees, so the
Infinity-object startup launch is collimated/parallel unless the user explicitly
requests a physical finite cone source.

Earlier movement on 2026-05-23: the CAD/STL face-role editor now writes
combobox changes, focus-out/Enter text edits, checkbox changes, and Apply Form
operations directly into the row-backed `OpticalSolidFaces` metadata. Each edit
invalidates the stale traced system, raykeeper, SceneBundle, and transient STEP
trace-plan caches as one physics-edit operation and forces an already-open Open
3D inspector to retrace. This closes the dialog-local edit path where selecting
`Full Reflecting` could still trace as the old `F004 refraction` row state until
Save Roles was pressed.

Earlier movement on 2026-05-23: Open 3D normal-to-axis placement now uses the
selected surface center as the default anchor, so most imported optical
components land with the optical axis through the face centroid while the face
normal is aligned to the axis. A separate `Snap STEP Pick-Point
Normal->Optical Axis` command keeps the older decentered anchor available when
that is intentional, for example an off-center beam-splitter pick or another
deliberate offset.

Earlier movement on 2026-05-23: `Open3DStepStateService` now owns the normalized
selected STEP face record used by axis-alignment actions. The inspector still
renders hover outlines and handles mouse events, but picked-point,
surface-center, normal-vector, and active imported-overlay validation now pass
through a service contract shared by normal snap and surface-center snap.

Earlier movement on 2026-05-23: Open 3D separated two STEP-to-axis alignment
intents and added hover badges for both the live pick coordinate and detected
surface center. `Center STEP Surface->Optical Axis` in the menu and `Center
Surface->Axis` in the browser translate the selected face centroid to the
clicked optical-axis guide point without changing the current orientation.

Earlier movement on 2026-05-23: The Open 3D STEP browser now treats
programmatic tree selections as passive state sync. Browser refresh can select
the imported item after a file dialog without re-entering the selection handler,
and selecting a browser row no longer arms STEP carry or cancels optical
cursor-carry placement unless the user explicitly presses `Carry`.

Earlier movement on 2026-05-23: Open 3D now includes a right-docked STEP
element browser, organized by Optical Element, Imaging Lens, and Camera /
Detector. The browser lists both display-only imported overlays and promoted
row-backed STEP optical solids; clicking an item highlights the matching 3D
component, selects promoted rows in the editable table, and shows selected-item
file, pose, face-count, carry, promote, accept, delete, face-editor, and
axis-alignment actions. The import commands remain separate internally because
optical, lens, camera, and LED STEP slots carry different placement defaults
and metadata, but the browser presents them as CAD roles rather than different
file formats.

Earlier movement on 2026-05-23: RayKeeper now sign-reconciles canonical
incoming/outgoing event directions against the traced physical polyline, and the
shared 2D/Open 3D escaped-ray capper also rejects terminal vectors that point
opposite the traced terminal segment. This fixes the false post-reflection tail
that looked like F004 leakage or a both-directions hypotenuse ray after an odd
number of reflections. Open 3D also keeps same-slot optical STEP imports
non-destructive by auto-promoting the previous unpromoted overlay before loading
the next one, and adds a targeted `Delete Selected STEP` command. The scalar
Snell solver now clips the critical/grazing radicand like the batch solver so a
near-critical uncoated interface cannot emit NaN vectors, and the non-sequential
solid chooser plus intersection-normal path now reject only scene-scaled
self-hits rather than every hit inside a fixed 0.05 mm window. Canonical
event-synced ray paths also avoid duplicating an Image/detector endpoint when
the terminal event already matches the last surface event. Traced Open 3D
optical-axis guide records now carry segment provenance (`launch`,
`between_surfaces`, or `post_surface`), source/target face/action metadata, and
segment start/midpoint/end vectors. The STEP1-STEP8 workflow uses that metadata
to snap the second right-angle prism to the real penta-prism exit axis instead
of a hard-coded pose. Open 3D also maps Delete/Backspace to the same targeted
STEP deletion action as `Delete Selected STEP`, including the currently picked
promoted row-backed STEP optical solid. The first STEP state-service extraction
is now in place: `Open3DStepStateService` resolves imported-overlay versus
promoted-row delete targets outside the Tk/VTK widget layer and is covered by a
focused headless validation. The Open 3D View toolbar now exposes the camera
presets as direct `Iso`, `YZ`, `XY`, `XZ`, and `Bottom` buttons instead of
hiding frequent view switches in a drop-down menu. The `open3d_face_pick`
service now ray-intersects every known CAD/STL face triangle from the display
pick ray and prefers internal planes when the body is transparent, so cube
beam-splitter diagonal coating faces can be hovered, selected for normal-to-axis
snapping, and right-click assigned even when an exterior shell face is closer to
the camera. A local diagnostic on vendor `step_32505.step` resolves the nearest
shell hit as `F007` but the through-body internal splitter hit as `F001` at the
cube center.
A headless diagnostic with only F004 assigned `Full Reflecting` records
`F004:reflection=12`, then the bundle exits at still default-Uncoated F003
(`last hit F003 refraction=12`). With both F003 and F004 assigned
`Full Reflecting`, the same diagnostic records
`F005 refract -> F004 reflect -> F003 reflect -> F006 refract` for all 12 rays.
The next pipeline item is cascade placement: consume the generated penta
exit-axis guides for the second prism instead of using a hard-coded pose.

## Upstream Main Sync

`main` was fast-forwarded to `origin/main` at commit `470c847` on 2026-05-21
without checking it out. This keeps the UI branch working tree on
`nonseq-display-refactor` and avoids accidental edits to `main`.

Useful upstream items reviewed:

| Upstream item | Integration status | Notes |
| --- | --- | --- |
| Modern package metadata | Merged | Added `pyproject.toml` so regular Python users can install the branch through the standard PEP 517 path as well as legacy `setup.py`. |
| Local generated/attachment cleanup | Merged | `.gitignore` now ignores nested prism screenshots, CAD side files, PDFs, and temporary STEP attachments while preserving tracked prism STEP fixtures. |
| BundleTrace / vectorized tracing prototypes | Deferred | Promising for future live-response speed, but it touches core tracing and raykeeper contracts; it should be integrated behind validators after the Live Mode transient-solid path exists. |
| RayKeeper result ingestion and public API tests | Deferred | Useful coverage, but the branch has extended raykeeper/event metadata and needs an adapted test contract instead of wholesale upstream tests. |
| Display / GeometryBackend / MeshBlock / lazy PyVista cleanup | Deferred | Good cleanup direction, but this branch has extensive 2D/Open 3D scene projection changes. Merge selectively after snapshot/projection validators cover the target behavior. |
| Upstream docs/manual reorganization | Deferred | The branch has separate Sphinx docs and public Branch README content; importing upstream docs directly would delete current UI-branch documentation. |

## Installation

### Regular Python Users

Use a normal virtual environment first. Python 3.10 to 3.12 is the safest
starting range for broad binary-wheel availability.

```bash
git clone https://github.com/Garchupiter/Kraken-Optical-Simulator.git
cd Kraken-Optical-Simulator
git checkout nonseq-display-refactor

python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip "setuptools<82" wheel
python -m pip install -e .
python -m pip install numpy scipy matplotlib pandas pyvista PyVTK vtk csv342
python -m KrakenOS.UI.layout_editor
```

Notes:

- The desktop UI uses Tkinter. If `import tkinter` fails, install the Tk package
  for your operating system, then recreate or refresh the virtual environment.
- STEP/IGES CAD import benefits from `pythonocc-core`; many users will find it
  easiest through conda-forge. STL import and cached STL workflows do not require
  STEP/IGES support.
- Optional developer extras used by this branch include `trimesh`, `meshio`,
  `sphinx`, `sphinx-rtd-theme`, `ruff`, and `basedpyright`.
- Optional GPU tracing requires a compatible CUDA/CuPy installation. CPU tracing
  remains the default reliable path.

### Nix Or Devenv Users

The branch also includes a `devenv.nix` environment for contributors who prefer
Nix-managed VTK/Tk, CAD, and documentation dependencies.

```bash
devenv shell
kraken-install
python -m KrakenOS.UI.layout_editor
```

Useful optional commands:

```bash
kraken-install-docs
kraken-install-notebooks
kraken-vtk-tk-check
```

## Feature Overview

### Layout Editor And Table Workflow

- Spreadsheet-style optical prescription table with undo/redo, copy/paste,
  grouped elements, right-click surface actions, advanced surface editing, and
  cell-local optimization variable markers.
- Text entries and editable table cells commit on focus loss, Tab, Enter, and
  normal selection changes.
- `Field Samples` is disabled and shown as `NA` when the active field span is
  zero; the requested count is restored when the field span becomes nonzero.
- Conventional sequential lens workflows keep `Field Samples` for field
  positions/angles and `Ray Count` for pupil or fan sampling.

### Scene And Display Pipeline

- The live 2D plot supports YZ, XZ, and XY projections of the traced 3D scene.
- The 2D projection selector sits with the plot controls so a design can remain
  editable while switching slice/projection views.
- Native non-sequential scenes, including promoted STEP optical solids, project
  the same traced 3D rays into YZ/XZ/XY and ignore legacy folded/branch display
  overrides that are only appropriate for folded sequential previews.
- 2D and Open 3D use the same SceneBundle scene envelope and bounded ray-point
  helper for escaped-tail capping and missed-detector display projection. The
  `validate_2d_3d_projection_sync` regression builds the 42779 penta prism from
  the tracked vendor STEP asset, launches a zero-cone collimated disk bundle,
  and verifies YZ/XZ/XY plots are exact projections of the Open 3D ray
  polylines. It also asserts that the final penta-prism exit segments remain
  collimated along scene `-Y`, so a correct YZ 2D exit cannot hide a bent 3D
  exit. Local penta-prism attachments should use that same collimated source
  intent; a nonzero `Pupil / field` source cone is retained as prescription
  metadata but does not auto-create a physical point emitter when a STEP overlay
  is promoted or a promoted face is assigned in a non-sequential scene.
- The Open 3D inspector shows traced scene geometry, STL/CAD placement,
  source-target picking, face anchors, and STEP overlay inspection.
- Open 3D refresh uses the active traced SceneBundle when one exists, and
  falls back to the 3D sampling mode when it has to rebuild locally. This keeps the
  viewport YZ/XZ/XY camera presets as views of the same traced data rather than
  separate simulations.
- A fresh Open 3D window starts in the active 2D projection camera: YZ opens as
  an orthographic YZ view, XZ as XZ, and XY as the top view. `Iso` remains
  available when the user wants a perspective 3D inspection view, but it is no
  longer the default comparison view for a 2D plot.
- Open 3D camera presets are exposed as direct `Iso`, `YZ`, `XY`, `XZ`, and
  `Bottom` toolbar buttons because users switch views frequently during STEP
  placement and face assignment. Optional reference, detector, and miss
  diagnostics remain grouped under `Overlays` so the top row stays usable on
  narrower windows.
- Non-sequential `Pupil / field` layouts launch the default Open 3D scene from
  a 3D Object/source reference aperture as a collimated aperture/envelope
  sampler. A nonzero `Pupil / field` Source cone remains visible for
  prescription and Scene Source Manager metadata, but it no longer means "make a
  physical point cone" in a non-sequential scene. A physical point-emitter cone
  is explicit: use `Random point cone` or a physical Scene Source Manager
  source. `Meridional fan`, `Fan X`, and `Fan Y` remain 2D plot/analysis labels,
  not instructions to collapse the 3D scene into a flat slice.
- Saved layout scripts that pass a traced raykeeper into the 2D renderer no
  longer retrace that raykeeper with a different preview sample. The saved 2D
  plot projects the ray events produced by the layout script.
- Open 3D top controls are split into a `View` row and a compact `Scene` row
  with CAD/target, placement, and orientation category menus, so camera and
  placement tools remain reachable when the window is not wide enough for one
  long button row.
- Open 3D has a docked `Live Controls` panel for the same Source, Field, and
  Trace / Display state that lives in the main left panel. It is docked on the
  left side of the Open 3D window, with the VTK viewport remaining the
  expanding right-hand canvas. `Live Mode` uses a debounced 3D retrace
  scheduler, so source changes and row-backed placement edits can update the
  ray scene without returning to the 2D editor. Manual `Trace now` uses the 3D
  sampling mode even when Live Mode is off.
- When an arbitrary optical STEP overlay is imported but not yet promoted,
  Live Mode builds a transient `Solid_3d_stl` optical row for the 3D trace
  bundle only. The editable table is restored immediately after the bundle is
  built, but Open 3D renders against the same transient row list so ray physics
  and displayed surfaces stay aligned while the user moves or tests placement.
  When the optical STEP pose and row context are unchanged, Live Mode reuses the
  transient row plan to avoid repeated CAD remeshing during source-only
  refreshes. `Accept STEP Placement` in the left panel and CAD/target menu
  promotes the active overlay into a persistent optical solid row, clears the
  display-only overlay and transient cache, selects the new row, and keeps face
  assignment as the next explicit user action.
- Open 3D defaults to a clean physical scene. `Refs`, `Det`, `Miss`, and
  `Placement handles` are explicit opt-in diagnostics, while `Done 2D` and
  `Close` on the top row refresh the 2D layout whenever 3D placement,
  promotion, or direct face assignment changed row metadata.
- Preview traces are explicitly invalidated after STEP import, clear, pose,
  snap, rotation, promotion, and direct face-role assignment changes. Open 3D
  face assignments force a retrace instead of reusing a stale scene bundle, so
  the displayed rays are rebuilt from the current row pose and role metadata.
  That edit-triggered retrace preserves the sampling mode already displayed in
  Open 3D, and `Done 2D` carries the same sampling choice back to the 2D plot,
  so assigning a face function changes only surface physics metadata and
  overlays; it does not silently swap an envelope/section bundle into a new
  point-cone launch.
- `Snap STEP Normal->Optical Axis` now uses an entrance-face convention: the
  selected face center lands on the optical axis, and the selected face's
  outward normal is aligned opposite the axis propagation direction. The hover
  badge reports both `Pick=(x,y,z)` and `Center=(x,y,z)`. The default centered
  snap is the right choice for most optical components; `Snap STEP Pick-Point
  Normal->Optical Axis` is the explicit decentered variant for intentional
  offsets, including beam-splitter placement where the user wants the clicked
  point rather than the face centroid on the axis. `Center STEP
  Surface->Optical Axis` / `Center Surface->Axis` remains a translation-only
  command for moving the detected face centroid to the axis without rotating
  the STEP component. This keeps the imported solid upstream-facing after snap,
  so a subsequent Uncoated entrance assignment followed by a Full Reflecting
  internal face assignment traces the intended closed-solid path instead of a
  backward single-boundary hit.
- Arbitrary optical STEP, lens, camera, and LED STEP overlays can now be
  imported directly from the Open 3D `CAD / target -> Import STEP` submenu. The
  generic optical STEP entry now uses a separate `optical` overlay slot, so it
  does not overwrite the existing lens STEP overlay in presets such as Machine
  Vision 150 mm. The imported optical component is selected immediately, enters
  cursor-carry placement until the next click drops it, and gets the same
  in-scene rotation handles. Each selected component gets one colored half-arc
  per X/Y/Z rotation axis, with narrow opposed cone arrowheads so the handle
  direction is visually unambiguous. Hovering a handle highlights it before
  click, and each end arrow applies either a `+90` or `-90` rotation around the
  visible world axis of that handle immediately around the selected STEP
  component center. If the pointer is not inside the 3D canvas when the
  file dialog closes, the first in-canvas pointer motion attaches the STEP
  center to the cursor plane so the component does not carry a large cursor
  offset. The generic optical STEP entry preserves all STEP components instead
  of reducing the import to the largest lens-like component.
- The Open 3D right panel is now a STEP element browser. It groups imported
  overlays and promoted row-backed STEP solids under Optical Element, Imaging
  Lens, and Camera / Detector, and a browser click drives the same 3D highlight
  and table selection state as clicking the component in the viewport. The
  selected-item property area reports file, pose, and face-assignment count,
  with Carry, Accept, Promote, Delete, Faces, Center Axis, Center Normal->Axis,
  Pick Normal->Axis, and Center Surface->Axis actions scoped to the browser
  selection.
- Open 3D imported STEP overlays are carried with free movement. Imported STEP
  carry now uses a press-hold or drag-to-lift gesture on an existing STEP body:
  hold briefly, or start
  dragging on the body, until the carry anchor snaps to the STEP center and an
  in-scene grip cursor appears on that center. Dragging moves the center grip
  and component together, and release drops/commits. The OS pointer is deliberately
  not warped during the hold-drag gesture; Tk/VTK can feed synthetic pointer
  motion back into the drag loop and make the component jump unpredictably. The
  carry path projects the current cursor ray onto a drag plane through the STEP
  center and moves continuously on that plane. Hold `Ctrl` while left-dragging
  to rotate the 3D view; middle-drag pans the whole view laterally in the
  current camera plane. Press `Esc` to cancel active carry/pick operations,
  clear the selected STEP component, and revert uncommitted free carry movement;
  clicking blank viewport space also clears the current 3D selection. To make
  placement optical instead of grid-driven, click a planar STEP face. The
  inspector then enters a second
  click mode where only the persistent dotted `Optical Axis` guide is accepted.
  Axis selection uses a screen-space nearest-line test against the same guide
  record that is drawn in the viewport, so it does not depend on VTK hitting a
  second actor and it still works when regular ray drawing is
  hidden. By default the picked face center moves onto the clicked guide point,
  and the picked face normal is rotated parallel to the layout optical axis. If
  the sign is not the intended one, use the colored rotation handles to flip the
  STEP before assigning Uncoated, Reflective, or other optical face functions.
  When the clicked point rather than the face centroid should land on the axis,
  use `Pick Normal->Axis` after selecting the face. Plain
  CAD/STL row selection no longer opens the placement panel by itself; pose
  controls open from explicit placement commands, while right-click face
  assignment remains available on the selected row. Hovering row-backed CAD/STL
  faces previews the picked face before right-click assignment and shows a small
  hover badge with the current face function and port role. New imported or
  promoted optical CAD solids default every detected face to `Uncoated` as a
  physical interaction surface; user changes are tracked separately so only
  explicitly assigned faces receive a color tint. Assigned optical faces are
  tinted as non-pickable filled surface overlays so previously authored
  Reflective, splitter, absorber, or explicitly confirmed Uncoated surfaces
  remain visible before the next pick without turning the whole solid into a
  triangulated mesh. The CAD/target promote menu
  turns the current placed overlay into a cached file-backed optical solid row
  with source STEP path, overlay rotation/offsets, row placement, and promotion
  provenance preserved in row metadata. The promoted row reserves positive
  axial thickness from the STEP world bounds, so starting from only Object and
  Image does not leave the Image/detector plane coincident with the prism
  entrance. A validator checks that the promoted optical-solid row lands at the
  same Open 3D world center as the original STEP overlay, pushes the downstream
  Image station beyond the inserted row, and remains present after all faces are
  assigned and the trace scene rebuilds.
- Imported lens, camera, and LED STEP overlays now rotate through selected
  in-scene colored handles instead of a separate floating STEP rotation popup.
  The handles use the same pickable 3D interaction style as row placement
  rotation controls, split each half-arc into separate `+90` and `-90` end-arrow
  commands, write the existing STEP rotation state, and are covered by a
  non-GUI handle-generation/write-through validator.
- Ray display filters show all rays, detector hits, missed detector paths,
  absorbed paths, escaped paths, diagnostic stops, and beam-splitter branches.
  The shared 2D/Open 3D display path bounds-caps escaped ray tails to the scene
  envelope before autoscale/rendering, so prism output direction remains visible
  without letting far escaped intersections dominate the view. It also caps
  missed-detector display diagnostics inside the detector plane instead of
  moving the endpoint to an arbitrary off-plane location. The canonical ray
  path, event metadata, raykeeper data, and CSV export remain unchanged.
- When canonical surface events exist but the kernel continues the ray after a
  CAD/STL/prism exit without emitting a terminal event, 2D and Open 3D preserve
  the raw raykeeper continuation point. This prevents a physically continued
  prism ray from appearing to stop on the last transmitted surface.
- Promoted/file-backed STEP optical solids retain a transparent cyan-blue body
  in Open 3D after face assignment and during ray-on refresh; manual face
  functions are still shown with separate non-pickable surface tints.
  File-backed optical solids draw blue silhouette/feature edges, suppress
  file-backed face-triangulation edges, and keep those edge/tint actors owned by
  the row so they translate with hold-drag movement instead of leaving a ghost.
  The prism or imported optical STEP remains readable without switching back to
  a mesh-heavy display.
- STEP/STL face clustering now treats opposite triangle winding on the same
  plane as one physical face while preserving the representative face-normal
  orientation used by placement and projection sync. Direct Open 3D face
  assignment updates all equivalent coplanar face records, preventing one
  physical CAD surface from acting partly reflective and partly uncoated when a
  vendor STEP splits that surface into multiple records.
- Open 3D rotation handles use the toolbar `Rot` selector for 15, 30, 45, 90,
  or 180 degree increments; the embedded CAD/STL side-panel `+/-Rot` buttons
  use the same value.
- Open 3D reports ray terminal counts in the viewport. If two groups of ray
  ends appear at different positions, the summary distinguishes detector hits,
  detector misses, escaped/bounded display tails, stopped/absorbed paths, and
  hidden endpoint markers instead of requiring visual guessing from the ray
  cluster positions alone. Escaped, stopped, terminated, or otherwise unknown
  paths also include the last CAD/STL face and event action, such as
  `last hit F003 refraction=12`, so a ray that reflects from one face and exits
  at another is not mistaken for leakage through the mirror face.
- Imported and Open 3D-promoted optical CAD/STL solids default to `AxisMove=0`.
  They are physical scene objects, so their decenter/tilt does not drag the
  downstream Image/detector plane into the prism. Explicit input/output ports
  remain the separate mechanism for anchoring follower rows to a traced port.
- When an escaped non-sequential ray has a configured detector/Image plane, the
  scene event layer projects the terminal marker to that detector plane and
  marks it as a detector miss without setting detector-reach flags.
- When the live editor places an Image plane from a traced optical-solid exit,
  a terminal point that lies on that target plane is classified as an Image
  contact in the canonical events. Explicit empty detector sets still remain
  diagnostic no-next-intersection cases.
- Direct Open 3D face-function assignment treats a `Full Reflecting` face as
  external only when the ray is outside the closed optical solid. Once the ray
  has entered the solid volume, reflected hits keep testing the same solid so a
  prism can naturally find its next mirror or exit face without requiring an
  explicit Input Port. Uncoated total-internal-reflection hits use the same
  same-solid continuation rule, so a valid TIR bounce does not terminate merely
  because multiple CAD faces are represented by one KrakenOS row.
- Dense 2D plots suppress detector-hit glyphs and ordinary escaped endpoint
  glyphs; missed detector/Image terminals use a distinct orange marker, while
  absorbed/stopped terminals remain visible diagnostics. Promoted STEP optical
  solids use compact projected labels such as `S1 Optical STEP` so YZ/XZ/XY
  views do not cover the prism or ray bundle. Open 3D uses plane-preserving
  crosshairs and suppresses escaped/missed endpoint disks that would imply a
  physical stop.
- Hovering or selecting a ray in the 2D plot, embedded 3D viewer, or legacy 3D
  viewer reports the canonical terminal status. Selecting a ray now also labels
  the selected path with canonical face/action tags such as `F003 Reflect`,
  `F006 Transmit`, or `F007 Miss`, using the same event metadata that feeds Ray
  Inspector and CSV export. Detector misses show the detector surface,
  projected plane distance, radial miss, active half-aperture, local
  detector-plane coordinates, active detector width/height, and original kernel
  terminal reason when available.
- Active detector/Image footprints are drawn from `SceneTarget3D` detector
  metadata in 2D and legacy 3D. Embedded Open 3D keeps them behind the `Det`
  diagnostic toggle so an orange detector footprint cannot be mistaken for a
  physical CAD face.
- Missed-detector terminal events still compute the projected detector-plane
  intercept and aperture miss distance, but embedded Open 3D draws those
  crosshairs only when `Miss` is enabled. This keeps red/orange terminal
  diagnostics available without making them look like ray-law stops.
- Object/Image reference rows remain scene targets. Embedded Open 3D keeps
  general reference disks behind the `Refs` diagnostic toggle, but shows the
  active Object launch aperture when a physical source or aperture/envelope
  reference is actually launching from that aperture. The Image reference disk
  stays diagnostic-only unless it is a detector target.

### Non-Sequential Physics And Metadata

- Scene/non-sequential tracing is selected for physical sources, beam splitters,
  probabilistic coatings, STL/CAD solids, mirror folds, tilted/decentered scenes,
  detectors, and path workflows.
- Ray events preserve reflection, transmission, absorption, split, scatter,
  diffraction, coating response, polarization, total internal reflection,
  detector termination, media transitions, and diagnostics.
- Launch metadata preserves requested versus effective field sampling, field
  basis/span, field-active state, ray count, pupil sampling label, trace intent,
  and sampling mode.
- Ray Inspector, Ray Events CSV, Trace Path Inspector, Branch Throughput,
  Detector Aperture Report, Branch Gaussian Q, Source Illumination, detector
  analyses, and path exports consume the active trace record set instead of
  relying on stale display state.
- Detector Aperture Report groups each detector/Image surface by ray/path count,
  detector hits, detector misses, stopped/other terminals, hit fraction, hit and
  miss power, worst miss margin, and dominant terminal reason. CSV export keeps
  the detector surface and worst-miss local X/Y/radial/active-aperture metadata.
- The normal results panel now shows detector aperture health after each trace,
  and the status bar adds a compact detector-miss warning when aperture clipping
  is present.
- Ray Inspector top rows now include per-ray detector aperture status and miss
  margin, and Ray Inspector CSV exports the same normalized aperture status
  fields beside the raw detector-miss event metadata.
- Ray-event and ray-analysis exports include detector-miss plane diagnostics:
  detector surface, projected miss distance, radial miss, active half-aperture,
  local detector-plane X/Y, active detector width/height, normal residual, and
  the original kernel terminal reason.
- Folded-preview detector reach is now an explicit policy. `Trace events`
  keeps KrakenOS terminal events authoritative and exports folded display
  status/residuals as diagnostics; `Display compatibility` preserves the legacy
  folded display detector rewrite for layouts that deliberately opt into it.

### Sources, Objects, And Detectors

- Scene Source Manager creates explicit physical illumination sources.
- Multiple sources can carry source id, role, model, wavelength, power, weight,
  ray count, position, aim direction, and target metadata.
- `SceneBundle.targets` records Object, Object Target, Aperture, Image/detector,
  and active analysis target rows as explicit scene targets without adding
  KrakenOS surface indices.
- `SceneBundle.placements` records movable target/CAD/STL placement anchors,
  row pose, grid visibility, linear snap spacing, and angular snap step as
  row-backed `ScenePlacement` metadata so 3D handles do not introduce a
  viewer-only transform.
- The Non-Sequential Scene Graph now includes a `Scene targets` namespace with
  target role, trace surface, detector metadata, center, normal, tangent, and
  active-target state.
- The Non-Sequential Scene Graph also includes a `3D placements` namespace for
  `ScenePlacement3D` records, and CSV export preserves those diagnostics beside
  sources, targets, volumes, and boundary faces.
- Open 3D uses the selected or first visible `ScenePlacement3D` record to drive
  placement handles and status text, but visible cube/grid planes are suppressed
  so face assignment and ray inspection are not obscured. Plain Object/Image
  reference targets do not become placement records; old placement metadata on
  those reference rows is ignored by the 3D handle layer.
- Open 3D placement handles can move the selected surface row along global
  X/Y/Z by the row's `ScenePlacement.snap_mm` when snap is enabled, or by the
  placement spacing when snap is off. The move writes `DespX/Y/Z` and
  `ScenePlacement` metadata through the same history/table path as other row
  pose edits.
- Open 3D placement rotation handles can rotate the selected surface row around
  global X/Y/Z by the row's `ScenePlacement.snap_deg` when snap is enabled, or
  by a coarse 15 degree step when snap is off. Rotation handles use one half-arc
  per axis with sharp opposed cone arrowheads; imported STEP overlays split
  those end arrows into separate `+90` and `-90` world-axis commands, and the
  handles can be hidden with the Open 3D `Rotation handles` checkbox.
  The rotation writes `TiltX/Y/Z` and `ScenePlacement` metadata through the same
  history/table path
  as other row pose edits.
- The same Open 3D placement handles also support drag authoring. Drag motion
  accumulates in screen space and repeatedly applies the same row-backed
  translation or rotation service; clicking without dragging remains the
  precise one-step fallback.
- Open 3D `Snap Row->Target` lets the user select a movable surface/CAD row or
  face, then a target row or face. The solved translation writes `DespX/Y/Z`
  and records `target_surface` constraint metadata in the row's
  `ScenePlacement` state.
- Open 3D `Orient Row->Target` lets the user select a movable surface/CAD row
  or face, then a target row or face. The solved rotation writes `TiltX/Y/Z`
  and records `target_normal` constraint metadata in the same row-backed
  `ScenePlacement` state.
- Open 3D `Center Row->Optical Axis` hides regular ray actors, lets the user
  select either a movable surface/CAD row or an imported STEP face with visible
  hover/selection highlighting. The optical-axis target is the persistent dotted
  `Optical Axis` guide itself, not an additional blue line; the guide is
  ignored by the first-click source picker so it cannot block surfaces/STEP
  faces, then only the guide is accepted as the second click. Passive ray
  inspection is opt-in through the View-row `Pick rays` toggle, and STEP
  normal/surface-center axis-pick modes hide regular ray actors before the
  optical-axis second click. Imported STEP face picks transition to STEP
  normal-to-axis
  alignment, and cached/throttled STEP face picking avoids rescanning large STEP
  meshes on every mouse move. `Show rays` now controls traced rays only; the
  dotted optical-axis guide remains visible and pickable. Row centering writes
  `DespX/Y/Z` so the row center, or the best assigned CAD/STL optical-face
  anchor, lands on the selected optical-axis guide. If the first click lands on
  a specific row-backed CAD/STL face, that face becomes the centering anchor so
  the user can re-snap a different entrance, exit, or slanted surface without
  editing `Left`/`Right`/`Up`/`Down` labels.
- Open 3D keeps detector active-footprint overlays, detector-miss crosshairs,
  row-sized Object/Image reference disks, and placement handles as explicit
  diagnostics. They are off by default and can be enabled independently through
  the `Det`, `Miss`, `Refs`, and `Placement handles` controls.
- Open 3D right-click on a CAD/STL optical face opens a compact function menu:
  `Uncoated`, `Full Reflecting`, `Partial Reflecting / Transmitting`,
  `Absorbing / Mechanical`, or `Unassigned`. The menu writes the same
  `OpticalSolidFaces` metadata as the full face-role editor and immediately
  rebuilds the traced Open 3D scene; it does not wait for the older face-role
  dialog's `Save Roles` button. If the current trace has a ray/surface event
  near the right-click, that traced event face wins over the generic mesh pick
  so assigning a visible `F004` refraction point updates `F004` physics. When
  the picked body is still a display-only
  imported STEP overlay, the command first promotes it into a row-backed
  `Solid_3d_stl` optical solid, clears the old display-only overlay, then stores
  the selected face function. This direct picked-face workflow does not require
  `Left`, `Right`, `Up`, `Down`, `+X`, or `-Y` labels for physics; those labels
  remain optional placement/roll aids. In this direct Open 3D workflow,
  `Uncoated` and `Full Reflecting` are stored as physical interaction surfaces
  rather than inferred output ports, so reassignment cycles do not create
  hidden output-port anchors or move the downstream `Image` row. Explicit
  input/output ports remain available in the full face-role editor for
  prescription-style port-chain placement. Newly imported/promoted optical CAD
  rows now start with default `Uncoated` interaction-surface records for every
  detected face; manual right-click assignments override that default and are
  the only faces tinted in the Open 3D scene.
- Open 3D writes structured `Open3DTrace` diagnostics to the Debug panel and
  `~/.cache/krakenos/logs/kraken_debug_latest.log`. The trace records left-click
  picks, right-click face context, matched face id/function, direct metadata
  writes, STEP promotion, `Show rays` toggles, scene-refresh mesh rows, actor
  counts, and row actors after refresh so a disappearing-component report can be
  reconstructed from the user's click sequence.
- Open 3D `Orient Row->Ray` lets the user select a movable surface/CAD row or
  face, then a traced ray. The solved rotation aligns the selected row or face
  normal to the clicked ray segment direction, writes `TiltX/Y/Z`, and records
  `target_ray` constraint metadata, ray index, branch path, source id, target
  point, target vector, and residual angle error in the same row-backed
  `ScenePlacement` state.
- Open 3D `Orient Row->Source` aligns the selected surface/CAD row or face
  normal to the Source panel aim vector. The solved rotation writes
  `TiltX/Y/Z` and records `source_vector` metadata, source origin, source
  direction, source model, target vector, and residual angle error in the same
  row-backed `ScenePlacement` state.
- Open 3D `Orient Row->Path` aligns the selected surface/CAD row or face normal
  to the selected Path-view frame near that row/face. The solved rotation
  writes `TiltX/Y/Z` and records `path_frame` metadata, branch path, sample
  count, origin surface, target point, target vector, and residual angle error
  in the same row-backed `ScenePlacement` state.
- Open 3D `Orient Row->CAD Axis` aligns the selected surface/CAD row or face
  normal to the selected local `+X/-X/+Y/-Y/+Z/-Z` axis after the row's current
  world transform is applied. The solved rotation writes `TiltX/Y/Z` and
  records `local_axis` metadata, the target axis row, axis label, axis vector,
  target vector, and residual angle error in the same row-backed
  `ScenePlacement` state.
- Open 3D `Orient Row->Scene Source` aligns the selected surface/CAD row or
  face normal to an explicit Scene Source Manager source. A selected source row
  in the editable table is used first; otherwise the first enabled physical
  scene source is used. The solved rotation writes `TiltX/Y/Z` and records
  `scene_source_vector` metadata, source id/name, origin, direction, source
  model, ray count, target vector, and residual angle error in the same
  row-backed `ScenePlacement` state.
- Open 3D named-normal placement uses the `Active target` / `Detector` /
  `Object` selector with `Preview Normal` and `Orient Row->Normal`. Preview
  reports the selected target row, role, normal vector, target point, and
  current angle error without mutating row pose. Apply writes `TiltX/Y/Z` and
  records `active_target_normal`, `detector_normal`, or `object_normal`
  metadata with the target row/id/name/role, target point, target normal, and
  residual angle error in the same row-backed `ScenePlacement` state.
- The scene graph `Edit Target` action writes row-backed `SceneTarget` metadata,
  detector active area, detector bins, pixel pitch, and active non-sequential
  `TargSurf` selection. Object Target, Diffuse Object, and Aperture choices use
  the existing surface-type defaults so tracing still sees normal KrakenOS
  prescription rows.
- Source-object aiming supports row targets and CAD/STL face anchors.
- Source Illumination reports hit power, vignetting, loss summaries, footprint
  coverage, centroid data, and per-source CSV rows.
- Detector workflows include detector maps, coherent detector fields,
  diffraction detector fields, path PSF, path MTF, and branch-field propagation.

### Beam Splitter And Path Workbench

- Beam splitter rows carry deterministic and probabilistic split metadata.
- Reflected/transmitted child states preserve branch power, phase, polarization,
  path labels, terminal state, and detector reach flags.
- Path-aware placement tools can add detectors, apertures, mirrors, thin lenses,
  refractive surfaces, and stock lenses along traced paths.
- Path-filtered reports cover detector maps, PSF, MTF, coherent detector,
  diffraction detector, source illumination, throughput, and Gaussian q.

### CAD, STL, And Prism Workflows

- Optical CAD/STL solids can be inserted, rendered, diagnosed, placed, and
  assigned boundary-face roles.
- STEP/IGES meshes can be converted and cached as STL for KrakenOS tracing when
  the optional CAD backend is available.
- Face anchors, snap-to-ray/path-frame placement, virtual internal planes,
  through-body transparent CAD face picking, and hit-sequence validators support
  prism and beam-splitter case studies.
- The CAD/STL face-role editor shows geometry-derived optical intent
  suggestions. Suggestions prefer Uncoated boundary physics so Snell/Fresnel
  tracing decides transmission or total internal reflection; mirror,
  beam-splitter, absorber, and detector semantics remain explicit user-authored
  choices. Applying suggestions fills only empty fields and preserves existing
  authored face roles.
- Cascaded optical-solid validation now covers output-port chaining, row-scoped
  scene boundary records, independent optical-volume IDs/materials, duplicated
  face IDs across different solids, and preserved face-intent suggestion
  metadata across a multi-solid layout.
- Raw STL optical solids now keep a minimal closed-volume state even before
  face-role metadata is attached, so the ray event stream can distinguish
  entry, internal reflection/TIR, and exit instead of treating each STL hit as
  another entry.
- Optical-solid hits record mesh cell id, original cell id, face id, face-match
  method, face-match diagnostics, volume identity, material, ambient medium,
  inside-volume stack, and media transition.

Important rule:

A ray that hits a surface should transmit, reflect, absorb, split, scatter,
diffract, or terminate at a detector according to configured physics. It should
not stop silently halfway. Total internal reflection is a physics result of
incident medium, transmitted medium, and angle; it should not require the user to
label a surface as a special TIR surface.

Physical `Random point cone` sources launch from one 3D point with azimuthal
direction samples across the configured cone half-angle. They are not generated
as a display-plane fan; any planar-looking result should be treated as a display
or sampling regression.

For an uncoated right-angle prism, total internal reflection is not a face type.
It is derived from the incident medium, transmitted medium, and angle. A central
BK7-air ray at a 45 degree hypotenuse should TIR, but a wide point cone can
physically split at the hypotenuse: marginal rays whose incidence falls below
the BK7 critical angle refract out while higher-angle rays reflect. Use a
collimated or narrower cone when the intended verification is "all rays TIR".

For non-sequential prism/CAD layouts, a plain final `Image` row is a reference
sentinel until the user marks it as an active detector/target. Escaped rays are
therefore shown as bounded escaped rays instead of long orange Image-plane miss
diagnostics that look like extra optical physics.

For conventional lens and beam-analysis workflows, the same plain final `Image`
row remains the detector plane unless the user overrides the target metadata.
This keeps Gaussian beam, coherent detector, PSF/MTF, and classic image-plane
analyses working while preventing CAD/prism scenes from inventing a detector.

### Sequential Lens Analysis

- Conventional prescriptions, paraxial solves, wavefront analysis, field maps,
  pupil maps, Zernike, Seidel, spot, PSF, MTF, lateral color, and classic lens
  diagnostics remain available.
- Sequential `Pupil / field` previews trace through a shared 3D section, then
  project that traced data into the selected 2D view.
- Finite-object mode derives launch geometry from object distance and entrance
  pupil rather than from the physical Source cone angle.

### Lens Fabrication Drawing Export

- Lens drawing surface properties can be edited from the UI.
- Lens fabrication drawing export produces PDF sheets for lens elements and
  assembly-level documentation.
- The export records drawing metadata, surface properties, diameters, thickness,
  material, radius, conic/asphere data where available, and manufacturing notes.
- A JSON sidecar preserves drawing settings for repeatable fabrication packages.
- Validators cover the drawing-property model and the PDF export case study.

### Optimization And Tolerancing

- Optimization variables, operands, merit functions, evaluators, and backend
  adapters are available.
- The UI supports merit operand setup, variable selection, bounds, worker count,
  SciPy/pygmo backend checks, saved solve presets, tolerance Monte Carlo,
  compensator sweeps, tolerance dashboards, and CSV export.
- SciPy remains the broadest default backend; pygmo is optional for global
  optimization workflows.

### Import, Examples, And Documentation

- Zemax prescription import, Zemax wavefront map import, AGF glass names, stock
  lens catalogs, common optical layouts, and saved layout snapshots are covered.
- Sphinx tutorials include sequential imaging, Gaussian beam expansion,
  interferometers, beam splitters, multi-source illumination, tolerance Monte
  Carlo, CAD/prism placement, lens drawing export, 3D hardware alignment, Cooke
  triplet optimization, Double Gauss analysis, and Galvo F-Theta scanning.
- SVG/PNG tutorial assets are generated from branch validators and capture
  scripts where practical.

## Validation

Regular Python environment:

```bash
python -m KrakenOS.UI.validate_fast_contracts
python -m KrakenOS.UI.validate_fast_contracts --list
python -m KrakenOS.UI.validate_fast_contracts --subprocess
python -m py_compile KrakenOS/UI/layout_editor.py
python -m KrakenOS.UI.validate_layout_plot_controller
python -m KrakenOS.UI.validate_branch_analysis
python -m KrakenOS.UI.validate_multi_scene_sources
python -m KrakenOS.UI.validate_mixed_source_object_template
python -m KrakenOS.UI.validate_ray_inspector_event_contract
python -m KrakenOS.UI.validate_detector_aperture_analysis
python -m KrakenOS.UI.validate_native_nonseq_closure
python -m KrakenOS.UI.validate_3d_interaction_contract
python -m KrakenOS.UI.validate_2d_3d_projection_sync
python -m KrakenOS.UI.validate_step_rotation_handles
python -m KrakenOS.UI.validate_step_promotion_optical_solid
python -m KrakenOS.UI.validate_open3d_face_context_assignment
python -m KrakenOS.UI.validate_open3d_face_assignment_sampling_stability
python -m KrakenOS.UI.validate_open3d_face_assignment_sampling_stability --focused --layout-smoke
python -m KrakenOS.UI.validate_open3d_live_mode
python -m KrakenOS.UI.validate_open3d_live_transient_step
python -m KrakenOS.UI.validate_step_carry_lightweight
python -m KrakenOS.UI.validate_open3d_toolbar_layout
python -m KrakenOS.UI.validate_scene_projection_terminal_bounds
python -m KrakenOS.UI.validate_selected_ray_event_labels
python -m KrakenOS.UI.validate_optical_solid_face_roles
python -m KrakenOS.UI.validate_optical_solid_chained_ports
python -m KrakenOS.UI.validate_optical_solid_hit_sequence
python -m KrakenOS.UI.validate_optical_solid_direct_mirror_faces
python -m KrakenOS.UI.validate_right_angle_prism_tir
python -m KrakenOS.UI.validate_optical_solid_multi_stl_trace
python -m KrakenOS.UI.validate_branch_gaussian_q_report
python -m KrakenOS.UI.validate_diffraction_detector
python -m KrakenOS.UI.validate_phase8_field_contract
python -m KrakenOS.UI.validate_galvo_f_theta_case_study
python -m KrakenOS.UI.validate_lens_drawing_properties
python -m KrakenOS.UI.validate_lens_drawing_pdf_case_study
```

Use `validate_fast_contracts` as the first pass for normal UI/non-sequential
changes. It runs the fast, fixture-light contracts that do not require an X
display, screenshot capture, or the large CAD attachment set. By default it runs
targets in one Python process to avoid repeated import/startup overhead; use
`--subprocess` when debugging a target that needs process isolation. The longer
validators and display-backed capture scripts below should still run when a
change touches CAD import, Open 3D rendering, face picking, or tutorial assets.
The Machine Vision Open 3D initial-sampler regression is covered by
`validate_open3d_face_assignment_sampling_stability --focused --layout-smoke`;
it loads the preset and is intentionally kept out of the default fast bundle.

Devenv users can run the same commands under `devenv shell`, for example:

```bash
devenv shell python -m KrakenOS.UI.validate_branch_analysis
```

Display-backed Open 3D smoke checks require a real X display or Xvfb:

```bash
python -m KrakenOS.UI.validate_step_carry_open3d_smoke
python -m KrakenOS.UI.validate_open3d_ray_toggle_scene_retention
python -m KrakenOS.UI.validate_step_carry_open3d_smoke --snapshot /tmp/kraken_step_carry.png
python -m KrakenOS.UI.capture_open3d_step_workflow_screenshots
python -m KrakenOS.UI.capture_penta_mirror_leak_diagnostic
```

`capture_open3d_step_workflow_screenshots` saves `STEP1.png` through
`STEP8.png` plus `step_workflow_report.json` under
`attachment/open3d_step_workflow_headless/`. The final step is the headless
equivalent of pressing Open 3D `Trace Ray` with one promoted penta prism and a
second transient optical STEP overlay; the report asserts that the transient
overlay is traced once as a live physics row instead of being drawn a second
time as display-only geometry.

`capture_penta_mirror_leak_diagnostic` saves
`f004_only_mirror.png`, `f003_f004_mirrors.png`, and
`penta_mirror_diagnostic_report.json` under
`attachment/open3d_penta_mirror_diagnostic/`. The report asserts that assigning
only F004 as `Full Reflecting` produces reflection at F004 and exit through
default-Uncoated F003, while assigning both F003 and F004 as mirrors exits
through F006 with no F004 transmission event.

## Known Risks

- Some older compatibility paths still exist for legacy sequential/table
  workflows. New work should prefer active scene and ray-event records.
- Source, object, and detector editing now preserves separate scene/source/target
  identity, but some editor controls are still row-driven for compatibility with
  conventional prescriptions.
- Some display annotations are still compatibility labels. Folded-preview
  terminal provenance states whether it is diagnostic or authoritative; future
  annotations should continue moving behind scene geometry, event records, or
  explicit diagnostics.
- CAD/prism additions must preserve face identity, media state, terminal policy,
  runtime scene bounds, and event diagnostics instead of adding case-specific
  display rays.
- CSV exports must continue to preserve launch metadata, source identity,
  terminal policy, target/detector reach flags, media state, and event
  diagnostics.

## Future Improvements

- Simplify the remaining legacy compatibility state around canonical scene/event
  records at UI boundaries.
- Expand source/object/detector editing into a fuller direct scene graph while keeping
  exact ordered-surface prescriptions available for sequential lens design.
- Continue reducing display-only annotations by backing them with physical
  scene geometry or explicit diagnostics.
- Keep broadening prism, CAD solid, coating, detector, and cascading-component
  regression coverage with real traced fixtures.

### Production Readiness Refactor Plan

The next UI phase is a maintainability and distribution pass, not a pixel-first
redesign. `layout_editor.py` is carrying too many responsibilities for a
production-maintained application. The priority is to split the file first,
theme second, while staying on Tk/ttk so the current working non-sequential
scene architecture is not disrupted.

Refactor order:

Production refactor progress:

| Slice | Status | Progress | Notes |
| --- | --- | --- | --- |
| `services/` boundary for Open 3D trace refresh | Complete | `██████████ 100%` | `PlotRefreshService` owns 2D layout refresh orchestration, auxiliary projection axes, analysis-axis dispatch, report refresh hooks, and fallback trace diagnostics. `Open3DSceneRefreshService` owns Open 3D actor rebuild orchestration for bodies, rays, axes, STEP overlays, thickness dimensions, and status actors. `Open3DMouseBindingsService` owns embedded VTK/Tk mouse binding setup for select, drag-rotate, press-hold carry, Ctrl navigation, middle-button pan, and right-click face menus. `Open3DInteractionService` owns Open 3D left-click picking and hover interaction routing for rows, rays, axes, STEP faces, placement handles, and rotation handles. `Open3DFaceAssignmentService` owns Open 3D right-click face-function menus, row-backed face assignment, and promote-and-assign imported STEP workflows. `StepOverlayImportService` owns imported STEP overlay slots, default placement/reset state, and import-time overwrite preservation. `StepOverlayPromotionService` owns imported STEP overlay planning and promotion into row-backed `Solid_3d_stl` optical solids. `Open3DTraceRefreshService` owns sampling-mode normalization, Live Mode preview-bundle creation, open-inspector synchronization, and transient STEP live-trace row creation through the editor trace contract. `Open3DLiveRefreshService` owns Live Mode debounce, cancellation, busy/pending stale-request handling, and retry scheduling while the inspector remains the scene-render target. `TracePreviewService` owns UI preview ray-bundle selection and dispatch for non-sequential, full-pupil, world-envelope, source-cone, and meridional preview tracing. `ResultsDisplayService` owns Information-panel result rows plus the 2D physical-distance overlay lifecycle. `EditableTableRowService` owns committed editable-table cell extraction back into row metadata. The `open3d_face_pick` service owns through-body transparent CAD face picking for internal planes, `Open3DStepStateService` owns delete-target resolution, selected STEP face records for normal/surface-center optical-axis actions, imported STEP promotion transitions, imported STEP carry start/drop validation, imported STEP carry spacing/cardinal-axis state construction, imported STEP carry pixel/drag-plane motion deltas, imported STEP carry finish/drop status transitions, imported STEP carry-follow/press-hold lift state preparation, imported STEP hold-arm/consume normalization, and row-backed optical-solid carry state/delta/drop transitions, `Open3DCarryGripService` owns the carry grip marker mesh, actor lifecycle, actor translation, and grip/center state update, `Open3DThicknessDimensionService` owns Open 3D table-Thickness dimension geometry plus the row-scoped edit and drag-adjust actions, `Open3DStepRotationHandleService` owns imported STEP rotation-handle actor removal, generation, hover styling, and click write-through, `Legacy3DSceneService` owns legacy PyVista scene body/ray/helper assembly, `LayoutSettingsService` owns persisted layout settings collect/apply for source, STEP import, operand, analysis, and tolerance-preset state, `LayoutFileWriterService` owns self-contained Python layout serialization, `RayInspectorRecordService` owns RayKeeper/SceneBundle Ray Inspector record collection, `NonSequentialSceneGraphRecordService` owns the scene/source/target/placement/volume/face records used by the Non-Sequential Scene Graph, `FormulaHelpService` owns the generated optics formula-sheet HTML, `ToleranceAnalysisService` owns Monte Carlo tolerance execution, solve-preset application, compensator sweeps, multi-compensator solves, and worst-sample comparisons, `ToleranceStackupService` owns stack-up dashboard/report/CSV record assembly, and `AnalysisPlotService` owns analysis-panel plot dispatch for spot, MTF, PSF, wavefront, interferogram, atmosphere, and tolerance views. Remaining heavy-CAD mesh reuse/throttling work is tracked separately under the Live Mode performance service milestone. |
| Optical-solid geometry helper service | Complete | `██████████ 100%` | `services/optical_solid_geometry.py` now owns STL triangle reading wrappers, mesh diagnostics wrappers, optical-solid face/virtual-plane dataclasses, planar face clustering, face metadata normalization compatibility helpers, face/virtual-plane world marker helpers, face-fit solve wrappers, and STL transform/hull helpers. `layout_editor.py` keeps backward-compatible imports for validators and panels, but the non-Tk CAD/STL geometry logic is no longer embedded in the main editor file. |
| Ray-display geometry helper service | Complete | `██████████ 100%` | `services/ray_display_geometry.py` now owns finite polyline cleanup, ray-bundle envelope selection for export/display, branch-path detection, bounds/span helpers, and traced chief-ray dotted-axis record generation. `layout_editor.py` still owns PyVista mesh actor creation, but the pure NumPy ray-display geometry no longer lives inside the Tk/VTK coordinator. |
| CAD/STEP export geometry service | Complete | `██████████ 100%` | `services/cad_step_export.py` now owns rotation/profile helpers, OpenCascade revolution-surface builders, mesh-to-faceted-STEP conversion, analytic optical-surface STEP export, native CAD-shape passthrough, and ray-tube STEP export. `layout_editor.py` keeps only the higher-level UI/cache/path wrappers around those export routines. |
| Error-map metadata service | Complete | `██████████ 100%` | `services/error_map_metadata.py` now owns measured error-map numeric coercion, X/Y/Z/SPACE validation, text/CSV/NPY/NPZ loaders, matrix-to-sample conversion, spacing inference, summaries, and validation messages. Advanced-surface dialogs still call the same compatibility symbols from `layout_editor.py`, but the file parsing code is isolated from the editor coordinator. |
| Beam/scatter surface metadata service | Complete | `██████████ 100%` | `services/beam_scatter_metadata.py` now owns beam-splitter default settings, deterministic/Fresnel/coating split normalization, branch-power validation, coating-table fallback generation, diffuse/BRDF scatter defaults, pySCATMECH parameter normalization, summaries, and validation messages. The editor retains the surface-type constants and UI wiring, while the optical interaction metadata rules have a focused service owner. |
| Element/scene target metadata service | Complete | `██████████ 100%` | `services/element_scene_metadata.py` now owns detector defaults, scene-target roles/editor-kind normalization, scene normal target choices, element arm/branch constants, element metadata normalization, and default-state checks. The remaining editor-local element summary wrapper only formats branch paths through the main editor compatibility method. |
| Catalog metadata service | Complete | `██████████ 100%` | `services/catalog_metadata.py` now owns bundled/attachment stock-lens catalog discovery, ZMF catalog loading/cache, stock-lens summaries, metal catalog spec normalization, metal catalog signatures, and setup-loading helpers. Glass conversion remains editor-local for now because it bridges into the cached KrakenOS setup builder. |
| Zemax prescription import service | Complete | `██████████ 100%` | `services/zemax_prescription_import.py` now owns text `.zmx` decoding, sequential SURF parsing, unit/wavelength/field extraction, Zemax glass fallback handling, asphere/note preservation, and construction of row/settings dictionaries. `layout_editor.py` supplies only the current UI default constants and cached glass-catalog resolver. |
| Surface value parsing service | Complete | `██████████ 100%` | `services/surface_value_parsing.py` now owns optimization flag/bounds coercion, compact attribute-name matching, native-variable aliases, native-variable list parsing, float-sequence parsing/deduplication, sequence formatting, and native-variable comparison. Editor-local advanced-surface normalization keeps only UI/backend-specific behavior. |
| Advanced surface validation service | Complete | `██████████ 100%` | `services/advanced_surface_validation.py` now owns coating/coating-metal validation, Lens Drawing payload validation forwarding, custom ExtraData/UDA preview checks, optical-solid virtual-plane diagnostics, and the combined advanced-surface input validator. `layout_editor.py` retains compatibility imports for existing panels and validators. |
| Source modeling mixin/service | Complete | `██████████ 100%` | `services/source_modeling.py` now owns physical source, pupil/field, Gaussian beam, scene-source, atmosphere-summary, random-source sampling, source bundle construction, trace terminal policy, launch metadata, and per-ray source metadata helpers. Shared source constants live in `source_trace_helpers.py`, while `layout_editor.py` keeps the same method names through `SourceModelingMixin`. |
| Tolerance modeling mixin/service | Complete | `██████████ 100%` | `services/tolerance_modeling.py` now owns tolerance Monte Carlo reports, tolerance variable coupling/manufacturing metadata, solve presets, compensator sweep/multi-compensator reports, nominal-vs-worst overlays, tolerance comparison plots/CSV, stack-up pass-throughs, and the tolerance dialog/service accessors. Shared tolerance constants live in `tolerance_constants.py`, while the editor keeps the same public method names through `ToleranceModelingMixin`. |
| Scene/STEP placement command mixin/service | Complete | `██████████ 100%` | `services/scene_placement_commands.py` now owns row pose translate/rotate commands, row-to-ray/axis/target centering, normal-orientation commands, source/path/local-axis orientation, STEP import/promotion pass-throughs, LED edge placement helpers, imported-STEP rotation/translation commands, STEP face metadata generation, face-to-axis and face-pair optical-axis snap, and direction-orientation commands. Dynamic CAD cache and STEP-label lookups still resolve through the editor module for validator compatibility. |
| Geometric analysis mixin/service | Complete | `██████████ 100%` | `services/geometric_analysis.py` now owns geometric PSF/MTF sampling, diffraction MTF fallback, PSF histogram/FFT helpers, field-sample image-plane builders, analysis chunk fan-out, optics summary metrics, and pupil-surface selection. Heavy worker functions remain exported from `layout_editor.py` for multiprocessing compatibility, with the mixin using late-bound wrappers. |
| Layout polyline display mixin/service | Complete | `██████████ 100%` | `services/layout_polyline_display.py` now owns 2D CAD/STEP mesh loading for layout overlays, external camera and lens mechanical overlay polylines, row/stl/optical-solid projected outline generation, and layout-pick distance helpers. Dynamic CAD cache, STEP conversion, PyVista, and legacy display-helper lookups resolve through the editor module at runtime so existing validators keep their monkeypatch points while the display projection logic leaves the main editor coordinator. |
| Paraxial/docs/focus tools mixin/service | Complete | `██████████ 100%` | `services/paraxial_tools.py` now owns paraxial cardinal calculations, 2F/object/image solve helpers, variable-thickness and folded-mirror solves, best-image focus search, formula/help docs launchers, and shared dialog-centering/popup cleanup utilities. System-build and row-spec signatures are still late-bound through `layout_editor.py` so multiprocessing/cache compatibility stays intact while solve orchestration leaves the main editor coordinator. |
| Analysis reports mixin/service | Complete | `██████████ 100%` | `services/analysis_reports.py` now owns Ray Inspector collection wrappers, Branch Gaussian Q, path throughput, source illumination, detector aperture, path detector map/PSF/MTF/coherent/branch-field/diffraction analysis helpers, branch-tree records, and Non-Sequential Scene Graph dialog/export orchestration. Existing panel/service classes still own widgets and pure record assembly, while the editor coordinator keeps the same public method surface through the mixin. |
| Open 3D inspector module | Complete | `██████████ 100%` | `KrakenOS/UI/open3d_inspector.py` now owns the embedded `Kraken3DInspector` Tk/VTK window, actor lifecycle, Open 3D panel wiring, camera controls, STEP/row carry interactions, face picking, rotation/placement handles, snapshots, live refresh hooks, and 3D scene refresh pass-throughs. `layout_editor.py` imports the inspector class instead of embedding the full window implementation, reducing the main file by more than eight thousand lines while keeping the existing `from KrakenOS.UI.layout_editor import Kraken3DInspector` compatibility path. |
| 3D scene tools mixin/service | Complete | `██████████ 100%` | `services/three_d_scene_tools.py` now owns Open 3D launch coordination, legacy PyVista plotter lifecycle, shared 3D ray/display geometry, detector-miss overlay helpers, folded-preview mirror meshes, legacy CAD/STL placement controls, 3D screenshot export, and the editor-side Open 3D refresh service accessors. `layout_editor.py` keeps the same inherited method surface for validators and external callers, while the main coordinator is reduced to about 20,790 lines. |
| Layout import/export mixin/service | Complete | `██████████ 100%` | `services/layout_import_export.py` now owns Glass Catalog Browser pass-throughs, Zemax prescription/rayfile/wavefront import workflows, stock-lens import insertion, File Open/Save/Save As, 3D STEP export orchestration and worker polling, Lens Fabrication Drawing export pass-throughs, layout-file writer access, example-script surface capture, example feature-gap reporting, row reconstruction from KrakenOS surfaces/layout dictionaries, special-row normalization, and flipped-name helpers. `layout_editor.py` keeps the same inherited file/import/export API while dropping below 20,000 lines. |
| Trace preview sampling mixin/service | Complete | `██████████ 100%` | `services/trace_preview_sampling.py` now owns finite fan samples, field samples, image-diameter preview helpers, default finite-cone/source-cone/world-envelope bundle builders, pupil disk/rim/sparse/full-grid sampling, infinity field bundle centering, selected through-envelope tracing, and source/pupil/gaussian accessors. `TracePreviewService` still owns dispatch, while `layout_editor.py` no longer embeds the launch-sampling implementation. |
| Analysis compute workflow mixin/service | Complete | `██████████ 100%` | `services/analysis_compute_workflow.py` now owns debug/progress text utilities, clipboard/CSV report exports, analysis progress indicators, backend reporting, analysis ray construction, serializable row-spec snapshots, worker-count capping, process-pool lifecycle, optimization backend preflight, merit operand resolution, optimization variable/value mapping, and optimization worker polling/finish handling. Multiprocessing worker entry points remain late-bound through `layout_editor.py` for spawn compatibility. |
| Layout table/workbench mixin/service | Complete | `██████████ 100%` | `services/layout_table_workbench.py` now owns custom border-only table selection, row border/focus state, layout reset/load runtime-state hydration, table undo/redo snapshots, table formatting/synchronization, row insert/delete/duplicate/paste/group/ungroup actions, arm/path workbench helpers, path-component row creation, scene target/source/editor actions, table editing/choice menus, surface defaults, material/coating/context actions, object/image diameter coupling, pending edit commit/cancel, popup choice menus, and optimization/tolerance marker toggles. The service currently uses a transitional late-bound compatibility sync for editor constants and helpers; the next cleanup should move those constants into dedicated modules. `layout_editor.py` is now about 4,053 lines. |
| Layout scene projection mixin/service | Complete | `██████████ 100%` | `services/layout_scene_projection.py` now owns 2D projection orientation/slice helpers, folded-layout preview geometry, world folded geometry, branch/path display overrides, galvo and pose-tolerance overlays, folded scan overlays, cardinal markers, optics/arm/ray labels, projected scene filtering, folded optics markers, and related 2D display-path helpers. It is still a transitional inherited mixin with late-bound compatibility access to editor constants, but the scene-display responsibility is no longer embedded in the main coordinator. `layout_editor.py` is now about 9,329 lines. |
| Optical-solid workflow mixin/service | Complete | `██████████ 100%` | `services/optical_solid_workflow.py` now owns optical CAD/STL row construction/import/convert actions, default uncoated face metadata, face-role dialog dispatch, row-backed and transient STEP face-record lookup, Open 3D face-function assignment, STL pose commands, explicit STEP axis/offset clearing, native STEP export shape collection, STEP ray/polyline export collection, 3D export mesh collection, STEP file prompting, Open 3D refresh fan-out, face-hover metadata clearing, and legacy 3D STEP actor refresh. The service keeps the same editor method names through inheritance while `layout_editor.py` drops to about 7,965 lines. |
| Layout shell/control mixin/service | Complete | `██████████ 100%` | `services/layout_shell_controls.py` now owns main panel accessors, source/field/trace/analysis control synchronization, left-sidebar reflow, source-model UI applicability, menu refresh, layout/example menu population, analysis/preview-mode switching, trace-mode resolution badges, non-sequential trace settings, source-model change handling, scene-source manager launch, and manual display-update dispatch. `layout_editor.py` now drops to about 6,605 lines. |
| Layout analysis display mixin/service | Complete | `██████████ 100%` | `services/layout_analysis_display.py` now owns PSF/MTF benchmarking entry points, KrakenOS system build orchestration, current wavelength/aperture/MTF/field/object/detector/wavefront settings, plot refresh service access, preview reset/autosave hooks, atmosphere residual display, interferogram sample/data/plot helpers, wavefront quality/reference/function plots, infinity-field centering helpers, and equal-axis/field-metric utilities. `layout_editor.py` now drops to about 4,859 lines. |
| Layout plot interaction mixin/service | Complete | `██████████ 100%` | `services/layout_plot_interaction.py` now owns 2D plot hover hints, row/ray picking, selected-ray overlay drawing, layout selection overlay refresh, hover highlight artists, system-viewer command discovery, and high-resolution plot image export/open actions. `layout_editor.py` now drops to about 4,443 lines. |
| Layout scene-bundle display mixin/service | Complete | `██████████ 100%` | `services/layout_scene_bundle_display.py` now owns field metrics, finite/infinity paraxial estimates, folded-surface output overrides, reference-plane and optical-solid image-plane overrides, source/branch output display frames, scene-bundle construction, physical-distance result dispatch, input/Gaussian overlays, example display defaults, and fallback trace diagnostics. `layout_editor.py` now drops to about 3,136 lines. |
| Main `layout_editor.py` coordinator reduction | Complete | `██████████ 100%` | The main editor file is now a thin Tk application coordinator: constructor/bootstrap state, window builder pass-throughs, tooltips, after-callback cleanup, destroy/quit handling, and saved-state guards. Operational code now lives in panels, widgets, and service/mixin modules; the remaining file is about 3,136 lines including imports, constants, compatibility functions, multiprocessing worker entry points, and the coordinator shell. |
| `panels/` boundary for Open 3D controls | Complete | `██████████ 100%` | `MainWindowBuilder` owns the main Tk menu and window shell construction, `Open3DLiveControlsPanel` owns the left-docked Live Controls UI, `Open3DTopControlsPanel` owns the View, Scene, and Carry toolbar rows, and `MainSourceControlsPanel`, `MainFieldControlsPanel`, `MainTraceDisplayControlsPanel`, `MainToleranceReportDialogs`, `MainNonSequentialSceneGraphDialog`, `MainPathDetectorAnalysis`, `MainAnalysisToolbarPanel`/`MainInformationPanel`, `MainBranchGaussianQDialog`, `MainBranchThroughputReportDialog`, `MainRayTraceInspectorDialogs`, `MainDetectorApertureReportDialog`, `MainSourceIlluminationReportDialog`, `MainOptimizationPanel`, `MainParaxialAnalysisDialogs`, `MainGlassCatalogBrowserDialog`, `MainOpticalSolidDialogs`, `MainOpticalSolidFaceRolesDialog`, `MainPathComponentPlacementDialog`, `MainLensDrawingDialogs`, `MainAtmospherePanel`, `MainCoatingMaterialDialog`, `MainDiffuseScatterDialog`, `MainSurfaceShapeBuilderDialog`, `MainBeamSplitterDialog`, `MainErrorMapDialog`, `MainAdvancedSurfaceDialog`, `MainSurfaceSettingsDialogs`, `MainContextMenu`, `MainSceneElementDialogs`, `MainSceneSourceManagerDialog`, `MainStockLensImporterDialog`, and `OpticalStlPlacementDialog` own the main window shell, Source, Field, Trace/Display, tolerance report, Non-Sequential Scene Graph, path detector map/PSF/MTF/coherent/branch-field/diffraction analysis orchestration, analysis-toolbar, Information, Branch Gaussian Q report, Path Throughput report, Ray Inspector/Trace Path Inspector, Detector Aperture report, Source Illumination report, Optimization panel and bounds dialog, Paraxial Matrix/Gaussian analysis dialogs and paraxial solve confirmations, Glass Catalog Browser, optical CAD/STL diagnostics, numeric placement, face-role assignment, traced path component placement, Lens Drawing Surface Properties/export dialogs, Atmosphere, Coating/Material, Diffuse/BRDF, Surface Shape Builder, Beam Splitter, Error Map, Advanced Surface, Galvo overlay, Grating settings, main table context-menu, Detector, Scene Target, Path-Local Pose, Element Settings, Scene Source Manager, stock-lens importer, and visual CAD/STL placement preview surfaces without moving analysis math, branch Gaussian q report, path throughput report, ray/trace-path inspector, detector aperture report, source illumination report, tolerance report, non-sequential scene graph, optimization, paraxial matrix/Gaussian dialog, glass-catalog browser, optical-solid utility dialog, optical-solid face-role editor, path-component insertion, lens drawing dialog, coating, scatter, shape, splitter, error-map, advanced-surface, galvo, grating, detector, scene-target, path-pose, element, source-manager, stock-lens importer, CAD/STL placement preview, or menu action execution out of the editor model. Remaining UI reductions should move services/widgets rather than grow this panel slice. |
| `widgets/` reusable Tk controls | Started | `█░░░░░░░░░ 10%` | `KrakenOS/UI/widgets/tooltips.py` now owns the reusable compact Tk tooltip used by toolbar and dialog controls. Validated entries, combobox commit helpers, projection selectors, menus, and table cell widgets still live mostly in `layout_editor.py`. |
| Fast validation contract runner | Complete | `██████████ 100%` | `KrakenOS.UI.validate_fast_contracts` runs the lightweight no-display/no-CAD-fixture contracts first, including focused Open 3D sampling-stability checks. Display-backed CAD smoke tests remain explicit targeted commands for rendering, face-picking, and screenshot regressions. |
| Live Mode performance service | Started | `██░░░░░░░░ 20%` | `Open3DLiveRefreshService` now owns debouncing, cancellation, busy/pending stale-request handling, and delayed retry scheduling. Mesh reuse/throttling and measured heavy-CAD refresh budgets remain before enabling Live Mode by default on large STEP scenes. |
| CadQuery CAD-topology study | Planned | `░░░░░░░░░░ 0%` | Study CadQuery/OCP patterns for STEP import/export, assembly traversal, face/edge selectors, tessellation, face center/normal handling, and tagged STEP metadata. Treat CadQuery as an optional reference and fixture-generation tool first; do not add it as a runtime UI dependency until Python-version support, package weight, and KrakenOS topology/metadata preservation are proven. |
| `sv-ttk` theme adapter | Pending | `░░░░░░░░░░ 0%` | Theme work waits until panels/widgets/services are split enough that styling is a thin layer instead of another responsibility inside `layout_editor.py`. |
| Public `kraken-os[ui]` install path | Pending | `░░░░░░░░░░ 0%` | The intended branch install command is documented below; packaging metadata and clean-venv validation are still needed. |

Latest movement on 2026-05-26: the embedded Open 3D inspector class moved out
of `layout_editor.py` into `KrakenOS/UI/open3d_inspector.py`, the editor-side
3D scene/legacy plotter bridge moved into `services/three_d_scene_tools.py`,
file/import/export workflows moved into `services/layout_import_export.py`,
trace preview sampling moved into `services/trace_preview_sampling.py`,
analysis/optimization progress workflow moved into
`services/analysis_compute_workflow.py`, and the editable table/workbench
workflow moved into `services/layout_table_workbench.py`. The 2D scene
projection, folded-preview, overlay, and label-display workflow now lives in
`services/layout_scene_projection.py`, and optical CAD/STL/STEP workflow now
lives in `services/optical_solid_workflow.py`. Main shell/control
synchronization now lives in `services/layout_shell_controls.py`. Analysis
display and system-build orchestration now lives in
`services/layout_analysis_display.py`. Plot hover/picking/viewer interaction
now lives in `services/layout_plot_interaction.py`. Remaining table-edit and
optimization marker helpers also moved into
`services/layout_table_workbench.py`. The main editor coordinator is now about
4,053 lines, while validators continue to access the same inherited public
method names through `KrakenLayoutEditor`. Scene-bundle display/default helpers
now live in `services/layout_scene_bundle_display.py`, reducing the main
editor coordinator to about 3,136 lines in the latest slice. The
layout-editor breakdown target is complete for this production-readiness pass:
the remaining class body is only bootstrap/lifecycle/saved-state coordination.
Element, detector, and scene-target metadata normalization now lives in
`services/element_scene_metadata.py`. Metal and stock-lens catalog helpers now
live in `services/catalog_metadata.py`. Zemax `.zmx` sequential prescription
parsing now lives in `services/zemax_prescription_import.py`. Surface value,
float-sequence, and native-variable parsing now lives in
`services/surface_value_parsing.py`, advanced-surface validation now lives
in `services/advanced_surface_validation.py`, source/pupil/Gaussian/
scene-source modeling now lives in `services/source_modeling.py`, and
tolerance modeling/report helpers now live in `services/tolerance_modeling.py`
with shared constants in `tolerance_constants.py`, and row/STEP placement
commands now live in `services/scene_placement_commands.py`. Geometric
PSF/MTF and optics-summary helpers now live in
`services/geometric_analysis.py`, and 2D layout CAD/STEP/external-camera
projected polyline display helpers now live in
`services/layout_polyline_display.py`. Paraxial solve, folded-mirror solve,
formula/docs launching, and best-image focus tools now live in
`services/paraxial_tools.py`. Ray/report/scene-graph UI orchestration now lives
in `services/analysis_reports.py`. The embedded Open 3D inspector window now
lives in `open3d_inspector.py`. Together these remove more than 23,400
source lines of non-Tk CAD/STL, ray-envelope, STEP-export, surface-metrology
parsing, optical-interaction metadata, source-launch modeling,
tolerance-report logic, placement-command logic, geometric-analysis logic, and
layout-projection CAD display/solve-tool/report-orchestration/Open-3D-window
logic from the editor coordinator while keeping backward-compatible symbols
available from `layout_editor.py` for existing validators and panels. The main
editor coordinator is now less than half of its pre-refactor size before the
next extraction slice.

Earlier movement on 2026-05-25: the Open 3D service boundary reached 100% for
the current production-readiness pass. Live Mode debounce/cancel/busy/pending
state moved from `layout_editor.py` into `Open3DLiveRefreshService`, so stale
scheduled refresh handling now has one service owner. The remaining large-CAD
work is tracked as the separate Live Mode performance milestone instead of
keeping the general service-boundary slice open.

Saved `.py` reload now preserves `StepOverlayPromotion` metadata and the Open 3D
right-panel browser also recognizes durable row-backed STEP solids from
`Solid_3d_stl` plus `OpticalSolidSourcePath`/`OpticalSolidSourceFormat`, so older
saved layouts whose transient promotion block is absent still list imported STEP
optical elements in the browser.

Latest movement on 2026-05-24: `StepFaceDirectionService` now owns the
calculation for Open 3D `Left`/`Right`/`Up`/`Down`/`Front`/`Back` STEP face
orientation. `layout_editor.py` now applies the planned rotation/offset and
refreshes the view, while the service keeps the picked face center anchored and
validates the finite face center/normal inputs outside the editor coordinator.

Latest movement on 2026-05-24: the CAD/STL face-role editor now preserves the
current Open 3D pose by default for rows promoted from imported STEP overlays.
`Save Roles` no longer auto-solves a second Tilt/Decenter pose for an already
placed Open 3D STEP solid unless the user explicitly enables `On Save: snap
Input Port to traced ray`. Face-role metadata saves also clear the Open 3D
hover/face-pick cache before rebuilding the scene, so stale offset outlines
cannot survive a face-role save or point to an invisible previous pose.

Latest movement on 2026-05-24: `Open3DStepStateService` now owns the imported
STEP overlay promotion transition used by the Open 3D `Accept STEP Placement`
and `Promote STEP` actions. The inspector still owns debug/status/refresh, but
the service now validates the active imported overlay, promotes it with
`clear_overlay=True`/`refresh_open_3d=False`, and clears stale transient live
STEP trace-plan cache state before returning the promoted row record.

Latest movement on 2026-05-24: `Open3DStepStateService` now also owns imported
STEP carry arm/drop decisions. `layout_editor.py` asks the service whether the
selected STEP overlay is still loaded before arming hold-drag carry or creating
motion state, and the service returns the user-facing arm/drop status while the
inspector remains responsible for VTK cursor, grip marker, and render updates.

Latest movement on 2026-05-25: `Open3DStepStateService` now also constructs the
imported STEP carry motion state for spacing, free-drag flags, and screen-axis
to cardinal-axis mapping. The inspector still supplies camera axes, scene scale,
and actor movement, but carry state defaults no longer live directly in the
large Tk/VTK coordinator. A new CadQuery CAD-topology study milestone has also
been added so the branch can deliberately learn from CadQuery's OpenCascade
face/edge selector, assembly, tessellation, and STEP metadata patterns without
making CadQuery a required runtime dependency yet.

Latest movement on 2026-05-25: `Open3DStepStateService` now computes imported
STEP carry pixel-motion and drag-plane deltas, including raw drag rebasing,
implausible jump rejection, applied-step counting, and live-refresh intent.
`layout_editor.py` now applies the returned movement to KrakenOS row/overlay
state and VTK actors, so Tk/VTK side effects remain local while carry motion
math is covered by service-level validation.

Latest movement on 2026-05-25: `Open3DStepStateService` now also owns imported
STEP carry finish/drop status transitions. The inspector still commits history,
clears cursors and grip actors, and refreshes the scene, but moved/no-movement
status text plus carry-drop live-refresh intent are now service-level behavior
with direct validation coverage.

Latest movement on 2026-05-25: `Open3DStepStateService` now prepares imported
STEP carry-follow state for cursor-attached placement. The service writes the
center, start center, drag-plane origin/normal, drag anchor, grip point, cursor
attach flag, and initial center-to-cursor delta; the inspector still computes
the cursor-plane point and applies any initial VTK/editor translation.

Latest movement on 2026-05-25: `Open3DStepStateService` now also prepares the
imported STEP press-hold lift state. The service validates the active loaded
overlay, writes hold/last-pointer/center/start/drag-plane/grip fields, and
returns the carry status text; the inspector still owns VTK picking,
cursor-plane projection, actor highlighting, grip marker rendering, and cursor
updates.

Latest movement on 2026-05-25: `Open3DStepStateService` now owns the imported
STEP hold-arm request, hold-delay constant, and pending hold-request consume
normalization. The inspector still starts/cancels the Tk `after` timer, but
loaded-overlay validation, press-position normalization, status text, and
pick-point normalization are covered by the service validation.

Latest movement on 2026-05-25: `Open3DStepStateService` now also owns
row-backed optical-solid carry state construction, press-hold activation state,
drag-plane movement deltas, implausible-jump rebasing, successful movement
bookkeeping, and drop status. `layout_editor.py` now supplies actor centers,
camera plane picks, and applies the returned row transform to KrakenOS row
state plus VTK actors.

Latest movement on 2026-05-25: `Open3DCarryGripService` now owns the in-scene
carry grip cursor actor lifecycle. The service builds the PyVista grip mesh,
removes/replaces the actor, translates the actor during drag, and updates
grip/center state after carry deltas; `layout_editor.py` now only asks the
service to show, update, or clear the marker.

1. Split `KrakenOS/UI/layout_editor.py` into a package-style structure inspired
   by the organization of `optiland_gui/`, while keeping KrakenOS on Tk/ttk.
   The first target package layout should be:

   - `KrakenOS/UI/panels/` for Source, Field, Trace/Display, analysis,
     optimization, drawing, scene-source, and Open 3D side panels.
   - `KrakenOS/UI/widgets/` for reusable table cells, validated entries,
     toolbar/menu helpers, projection selectors, log panes, dialogs, and
     small Tk/ttk controls.
   - `KrakenOS/UI/services/` for trace orchestration, scene bundle refresh,
     Open 3D commands, STEP/CAD import and promotion, face assignment,
     packaging/install helpers, snapshot/export actions, and validator-facing
     workflows.
   - Keep shared scene/event dataclasses in their existing scene modules unless
     there is a clear ownership reason to move them.

   First slices started: `KrakenOS/UI/services/open3d_trace_refresh.py` now
   owns Open 3D sampling-mode normalization, inspector refresh trace selection,
   Live Mode preview-bundle creation, and synchronization of an already-open 3D
   inspector. `KrakenOS/UI/services/open3d_thickness_dimensions.py` now owns
   Open 3D table-Thickness dimension geometry and editing, so adding dimension
   overlays does not grow the inspector class. `KrakenOS/UI/services/layout_settings.py`
   now owns persisted layout settings collection/application, so save/load and
   common-layout presets no longer add another state-serialization block to the
   editor coordinator. `KrakenOS/UI/services/ray_inspector_records.py` now owns
   Ray Inspector record collection from SceneBundle or RayKeeper data, so the
   inspector dialogs and CSV exports can use a service boundary without carrying
   another record-flattening block inside the editor.
   `KrakenOS/UI/services/nonseq_scene_graph_records.py` now owns the
   Non-Sequential Scene Graph's scene row, source, target, placement, optical
   volume, and boundary-face record assembly. `KrakenOS/UI/services/formula_help.py`
   now owns the generated optics formula-sheet HTML, keeping browser-help
   content out of the editor coordinator. `KrakenOS/UI/services/tolerance_stackup.py`
   now owns tolerance stack-up dashboard, report, and CSV record assembly.
   `KrakenOS/UI/services/layout_file_writer.py` now owns self-contained
   Python layout serialization, including saved runtime-system rebuild helpers.
   `KrakenOS/UI/services/legacy_3d_scene.py` now owns legacy PyVista scene
   body/ray/helper assembly, physical dimension arrows, and fallback viewer
   toolbar wiring. `KrakenOS/UI/services/analysis_plot.py` now owns
   analysis-panel plot dispatch while delegating editor state, analysis mode,
   and plot helper calls through the editor contract.
   `KrakenOS/UI/services/trace_preview.py` now owns preview ray-bundle
   selection and tracing dispatch for non-sequential, source-cone,
   world-envelope, full-pupil, pupilcalc, and meridional preview modes.
   `KrakenOS/UI/services/results_display.py` now owns Information-panel result
   rows and the 2D physical-distance overlay lifecycle.
   `KrakenOS/UI/services/editable_table_rows.py` now owns committed editable
   table-cell extraction back into `SurfaceRow` metadata, including Path view
   local-pose edits and grouped pose tolerance propagation.
   `KrakenOS/UI/services/plot_refresh.py` now owns 2D plot refresh
   orchestration, including shared scene sampling, auxiliary projection axes,
   analysis-axis dispatch, report refresh hooks, and fallback diagnostics.
   `KrakenOS/UI/services/open3d_scene_refresh.py` now owns Open 3D actor
   rebuild orchestration for surface bodies, ray actors, optical axes, STEP
   overlay display, thickness dimensions, and status actors.
   `KrakenOS/UI/services/open3d_mouse_bindings.py` now owns embedded VTK/Tk
   mouse binding setup for select, drag-rotate, press-hold carry, Ctrl
   navigation, middle-button pan, and right-click face menus.
   `KrakenOS/UI/services/open3d_interaction.py` now owns Open 3D left-click
   picking and hover routing for rows, rays, axes, STEP faces, placement
   handles, and rotation handles.
   `KrakenOS/UI/services/open3d_face_assignment.py` now owns Open 3D
   right-click face-function menus, row-backed face assignment, and imported
   STEP promote-and-assign workflows.
   `KrakenOS/UI/services/tolerance_analysis.py` now owns tolerance Monte
   Carlo execution, solve-preset application, compensator sweeps,
   multi-compensator solves, and worst-sample comparison reports.
   `KrakenOS/UI/services/step_overlay_promotion.py` now owns imported STEP
   overlay row-plan generation and promotion into persistent row-backed
   `Solid_3d_stl` optical solids.
   `KrakenOS/UI/widgets/tooltips.py`
   starts the reusable Tk widget boundary. `KrakenOS/UI/panels/main_source_controls.py`,
   `KrakenOS/UI/panels/main_field_controls.py`, and
   `KrakenOS/UI/panels/main_trace_display_controls.py`, and
   `KrakenOS/UI/panels/main_analysis_controls.py`,
   `KrakenOS/UI/panels/main_optimization_panel.py`,
   `KrakenOS/UI/panels/main_atmosphere_panel.py`,
   `KrakenOS/UI/panels/main_coating_material_dialog.py`,
   `KrakenOS/UI/panels/main_diffuse_scatter_dialog.py`,
   `KrakenOS/UI/panels/main_surface_shape_builder_dialog.py`,
   `KrakenOS/UI/panels/main_beam_splitter_dialog.py`,
   `KrakenOS/UI/panels/main_error_map_dialog.py`,
   `KrakenOS/UI/panels/main_advanced_surface_dialog.py`, and
   `KrakenOS/UI/panels/main_surface_settings_dialogs.py`, and
   `KrakenOS/UI/panels/main_context_menu.py`, and
   `KrakenOS/UI/panels/main_scene_element_dialogs.py`,
   `KrakenOS/UI/panels/main_optical_solid_face_roles_dialog.py`, and
   `KrakenOS/UI/panels/main_scene_source_manager_dialog.py`, and
   `KrakenOS/UI/panels/main_path_component_placement_dialog.py` now own the main
   Source, Field, Trace/Display, Analysis toolbar, Information table,
   Optimization, Atmosphere, Coating/Material, Diffuse/BRDF, Surface Shape
   Builder, Beam Splitter, Error Map, Advanced Surface, Galvo overlay, Grating,
   main table context-menu, Detector, Scene Target, Path-Local Pose, Element
   Settings, Scene Source Manager controls, and traced path component
   placement dialog while delegating state and callbacks back to the editor.
   The large optical CAD/STL face-role assignment workflow is now panel-owned
   too, which removes another high-churn dialog from the editor coordinator
   without changing the row metadata contract.
   `KrakenOS/UI/panels/main_window.py` now owns the main menu and Tk shell
   construction while delegating actions and state back to the editor model.
   `KrakenOS/UI/panels/open3d_live_controls.py` now owns the left-docked Live
   Controls panel construction, and
   `KrakenOS/UI/panels/open3d_top_controls.py` owns the top View, Scene, and
   Carry toolbar rows. `layout_editor.py` still owns rendering and
   interaction, but trace/refresh policy and the first Open 3D panel surfaces
   are now behind reusable module boundaries.

2. Preserve behavior while splitting. Each extraction should move one ownership
   boundary with no UI feature redesign in the same commit. The validation bar
   is the current non-sequential validators plus focused smoke checks for
   editable-table commits, Open 3D placement, face assignment, 2D/3D projection
   sync, and saved layout rendering.

3. Move Live Mode performance into service ownership. The lag observed when
   enabling Live Mode should be handled by a trace/update service that can own
   debouncing, CAD row-plan caching, mesh reuse, stale-request cancellation,
   and UI-state synchronization. This keeps performance fixes out of panel and
   widget code.

4. Adopt `sv-ttk` only after the split. It is the closest Tk gets to a
   Qt-grade visual layer without changing toolkits, but theming should not be
   mixed with the structural extraction. Once panels/widgets/services exist,
   introduce a small theme adapter that initializes `sv-ttk`, centralizes
   spacing/font/style tokens, and leaves the physics/scene services untouched.

5. Establish a public install story for the branch. The target is
   `pip install kraken-os[ui]` from a normal Python environment. Before a
   packaged release exists, the documented bridge can be:

   ```bash
   python -m pip install -e "git+https://github.com/Garchupiter/Kraken-Optical-Simulator.git@nonseq-display-refactor#egg=kraken-os[ui]"
   ```

   The packaging work should make Tk/VTK/PyVista/CAD extras explicit, keep CPU
   tracing as the reliable default, and document optional CAD/STEP dependencies
   separately from the core optical package.

6. Leave Qt as a long-horizon option. A toolkit change is only justified if the
   interaction model changes substantially, for example real dockable
   multi-viewport workspaces, a command palette, an embedded scripting console,
   or a richer scene-tree shell. If that point arrives, the pragmatic path is
   to fork/adapt an Optiland-style GUI shell rather than rebuilding a Qt shell
   from scratch.

Acceptance criteria for this phase:

- `layout_editor.py` becomes a coordinator instead of the owner of panels,
  widgets, tracing services, Open 3D actions, dialogs, and export flows.
- Extracted modules have clear imports and do not create circular dependencies
  around `KrakenLayoutEditor`.
- Existing North Star behavior remains covered by validators after each slice.
- The public install command is documented and tested in a clean virtual
  environment.
- The visual theme pass is small, reversible, and independent of scene physics.

Current STEP workflow observations from the STEP1-STEP8 screenshots:

- The F004-only penta-prism case is diagnostically clear now: F004 is reflective
  for all traced rays, and any visible outgoing bundle in that setup is the
  subsequent F003 Uncoated exit unless F003 is also assigned as a mirror.
- The F003 red-circle diagnostic was a rendering artifact, not a physics event:
  mirrored penta hits recorded `reflect` events, but the old 2D Line2D join/cap
  could visually overrun a sharp mirror vertex. Ray drawing now uses segmented
  `LineCollection` strokes with butt caps so event vertices stop at the hit.
- Imported STEP solids can still pass through a display-only phase where rays
  continue to the detector without interacting with the solid.
- Face assignment and promotion can still change visual state too strongly,
  including mesh-like body rendering and stale/duplicate solid actors in later
  views.
- Trace state can change after assignment or placement, producing escaped-ray
  groups, apparent duplicate output bundles, or solids that remain visible but
  are no longer the active physics object.
- These are not prism-specific failures. They point to the remaining
  architecture work: transient overlay state, promoted row state, face-role
  metadata, and Live Mode refresh policy must converge through one service
  boundary before the UI can guarantee that every visible STEP object is the
  same object being traced.

### Feasibility Notes

White-beam prism dispersion is feasible as a native scene workflow, not as a
painted display effect. The right implementation is a spectral source bundle
that traces the same physical beam over multiple wavelengths, lets KrakenOS
material dispersion compute each wavelength's refraction through an equilateral
prism, and renders ray color from wavelength in both 2D and 3D. The required
work is a wavelength-sampled source model, per-wavelength ray metadata in the
active trace records, renderer color-by-wavelength support, and a prism case
study/validator that verifies wavelength-dependent detector positions.

Direct STEP optical-component placement in the 3D plot is also feasible. The
branch already imports STEP/IGES through cached STL, displays CAD/STL solids in
3D, stores face roles, supports path/face anchors, publishes row-backed
`ScenePlacement3D` records for snap/grid/anchor intent, suppresses visible
placement grid planes inside Open 3D, and provides translate handles for
selected rows plus optional arrowheaded rotate handles for `TiltX/Y/Z`. Those
handles can now be clicked for one edit or dragged for repeated edits while
immediately persisting back to row pose plus `ScenePlacement` metadata. Open 3D
also supports row-to-target snapping, where a movable row or face is translated
onto another row or face and the solved constraint is preserved as row-backed
metadata. It also supports row-to-target normal orientation, where a movable
row or face normal is aligned to a target row or face normal and the solved
tilt is preserved as row-backed metadata. It now includes row-to-ray
orientation, where a movable row or face normal is aligned to a clicked traced
ray segment, plus source-vector and Path-view-frame orientation, where the
same row or face normal is aligned to the Source panel aim vector or selected
Path view. Open 3D also supports local CAD-axis orientation through the
`+X/-X/+Y/-Y/+Z/-Z` selector and explicit Scene Source Manager orientation,
where a selected source row wins and the first enabled physical source is the
fallback. These vector constraints are preserved as row-backed metadata. The
named-normal selector now provides detector, object, and active-target normal
previews before applying the row pose, and the applied target is exported in
scene graph/CSV diagnostics. Chained optical-solid placement now refreshes
runtime boundary and optical-volume records after the output-port pose graph is
applied, so real multi-STL trace events, 2D/3D scene bounds, diagnostics, and
CSV/export consumers use the same placed geometry. The important constraint
remains that 3D placement must update the same scene state used by 2D
projection, tracing, scene graph diagnostics, and CSV export.

## Historical Notes

Older branch planning files were consolidated into this README to reduce
root-level document sprawl. The upstream project `README.md` and the Sphinx
documentation tree remain separate on purpose.

## Next Pipeline Step

Continue the production-readiness refactor by replacing transitional late-bound
sync points with dedicated constants/helper modules, then run a clean
packaging/install pass for `kraken-os[ui]`. Keep `layout_editor.py` as the
application coordinator instead of moving behavior back into it.

Before that larger extraction resumes, run a focused Open 3D correction pass:

1. Saved layout reload must restore the STEP element browser. Opening a saved
   `.py` layout that contains promoted optical STEP rows should rebuild the
   right-panel browser from row-backed file/STL/STEP metadata, not only from
   transient in-memory overlay slots. If a saved optical solid traces and draws
   but is absent from the browser, treat that as a persistence/reconstruction
   bug in the saved layout writer or browser inventory service.
2. Open 3D has restored explicit `Left`, `Right`, `Up`, `Down`, `Front`, and
   `Back` STEP face-direction controls in the right-panel browser. After the
   user clicks an imported STEP face, changing this selector rotates the STEP
   immediately so the picked face normal points in the selected layout
   direction while the detected face center stays anchored. These labels remain
   optional placement/orientation aids; physics still comes from the selected
   face function (`Uncoated`, `Full Reflecting`, `Partial Reflecting`, etc.).
3. Audit Source panel control applicability by source model. For `Pupil / field`,
   `Source Radius` does not affect the launch; the active aperture/envelope is
   driven by Object/Image/field/pupil settings instead. Gray out or hide controls
   that do not participate in the selected source model, and do the same for
   every other source-model/control combination where the value is retained only
   as metadata. The validator should confirm disabled controls are restored when
   switching back to a model that uses them.
4. Keep these UI-state fixes behavior-preserving: they should not change ray
   physics, only ensure saved state, browser state, face metadata, and enabled
   controls truthfully reflect the active scene model.
