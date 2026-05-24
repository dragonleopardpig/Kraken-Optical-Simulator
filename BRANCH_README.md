# KrakenOS Non-Sequential UI Branch

Last updated: 2026-05-24

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
| 3D scene with 2D projections | Achieved | `██████████ 100%` | YZ, XZ, and XY views are generated from traced 3D scene data; native non-sequential scenes project the same traced 3D ray set in all three 2D planes instead of applying legacy YZ-only folded/branch overrides or center-section filtering, Open 3D reuses the active SceneBundle when one is current and otherwise retraces with the 3D sampling mode, promoted non-sequential scenes keep explicit physical source models and collimated-source sampling while Pupil/field defaults stay as aperture-envelope references, edit-triggered Open 3D retraces preserve the displayed sampling mode so right-click face assignment cannot turn a current envelope/section bundle into a new point-cone launch, Pupil/field source-cone values are retained for prescription metadata but do not auto-create a physical point source after STEP promotion or face assignment, explicit Random point cone and authored scene-source cones remain filled 3D launches, saved 2D layout scripts preserve source intent, categorized view/scene/carry control rows with a toolbar layout validator, direct optical/lens/camera/LED STEP import, a distinct arbitrary-optical STEP overlay slot that does not replace the lens overlay, immediate cursor-attached carry placement for new optical STEP imports, free STEP carry placement, press-hold or drag-to-lift STEP movement with an in-scene center grip, release-to-drop, no OS pointer warping, Esc cancellation with selection clearing, blank-click deselection, middle-drag CAD-style view pan, Ctrl-drag camera pause, default STEP-face hover outlines plus row-backed CAD/STL face hover previews with in-scene assignment badges, stale face-hover outlines are cleared when a promoted row enters or moves through hold-drag carry, row-owned edge and assigned-face tint actors move with the promoted body during drag instead of leaving ghosts, a persistent pickable dotted Optical Axis guide independent of ray visibility with pre-click hover highlight and a solid selected-axis overlay after normal snap, traced chief-ray bend segments become additional pickable dotted `Optical Axis 2+` guides only after real physical surface events, two-click STEP-face-normal-to-optical-axis snapping that treats the picked face as the entrance face and points its outward normal upstream, face-specific row-to-optical-axis anchoring, promotion of positioned STEP overlays to file-backed optical solid rows with default Uncoated interaction face metadata, direct hold-drag movement for promoted row-backed optical solids, lighter transparent promoted-solid bodies with two-layer dark silhouette/body-colored feature edges, suppressed file-backed face triangulation edges, and no selected-body triangle mesh, Open 3D right-click face-function assignment with physics-only interaction-surface semantics and non-pickable assigned-face surface tints, transparent row-backed STEP bodies after face assignment and ray-on refresh, structured Open3DTrace click/assignment/refresh diagnostics, double-sided scene surface actors plus transactional scene refresh that keeps prior valid surface meshes if a trace rebuild returns no or suspiciously incomplete surface meshes, shared SceneBundle-envelope 2D/Open 3D ray display with escaped-tail capping and a penta-prism YZ/XZ/XY projection-sync validator, event-synced ray paths preserving raykeeper continuation after CAD/prism exits that do not emit a terminal event while avoiding duplicate detector terminal endpoints, detector-miss diagnostics capped within the detector plane, selected-ray face/action labels in 2D and embedded Open 3D, diagnostic line coloring for stopped/absorbed rays while ordinary escaped rays preserve source/wavelength color, an in-viewport Open 3D ray-terminal summary that separates detector hits, misses, escaped, stopped, absorbed, and bounded display rays, all Open 3D terminal endpoint disks gated behind the Terminal diagnostics toggle, explicit CAD/STL placement side-panel entry instead of selection-triggered popups, and Sphinx coverage, hover-highlighted optional single-half-arc in-scene STEP/row rotation handles with a toolbar `Rot` selector for 15/30/45/90/180 degree steps and separately pickable larger positive/negative cone end arrows, opt-in reference-plane, detector-footprint, terminal-miss, and placement-handle diagnostic toggles plus an always-visible active Object launch aperture in Open 3D when a physical source or aperture-envelope reference is selected, hover/click terminal diagnostics, and top-level Done 2D/Close refresh controls. |
| Separate sources, objects, detectors | Achieved | `██████████ 100%` | Scene sources, scene targets, and row-backed 3D placement records are first-class scene data; target role, detector metadata, active target selection, snap/grid intent, placement anchors, Open 3D placement handles with visible grid planes suppressed, snap-aware click/drag translate-rotate handles, imported STEP snap-to-target placement, row-to-target snap constraints, row-to-target normal-orientation constraints, row-to-optical-axis centering with regular rays hidden during target pick, named detector/object/active-target normal previews, row-to-ray vector-orientation constraints, source-vector constraints, Path-view frame constraints, local CAD-axis constraints, and explicit Scene Source Manager constraints are preserved from KrakenOS row metadata and scene graph export. |
| Live 3D authoring | Achieved | `██████████ 100%` | Open 3D now has a left-docked Live Controls panel bound to the same Source, Field, and Trace / Display variables as the main left panel. Live Mode schedules debounced 3D retraces after source edits, main left-panel edits, and STEP carry/placement changes, using the same 3D preview sampling path. Imported arbitrary optical STEP overlays now enter live traces as transient file-backed optical solid rows, so rays can interact with the unpromoted overlay during placement without inserting a row into the editable table. The transient optical STEP row plan is cached when overlay pose and row context are unchanged, reducing repeated remeshing during source-only Live Mode refreshes. Open 3D now renders transient rows from the live render-row list, suppresses the duplicate display-only overlay during live trace, and displays the full CAD/STL body with strong cleaned feature edges. A headless STEP1-STEP8 workflow capture validates the import, carry, transient trace, promotion, generated bend/exit-axis records, traced-axis cascade placement of a second STEP prism, final Trace Ray path, and event face/action sequences. `Accept STEP Placement` commits the current overlay into a persistent row-backed optical solid and clears the display-only overlay. Promoted optical-solid rows can now be hold-dragged directly in Open 3D after promotion, stale face-hover outlines are cleared at drag start, row-owned edge/tint actors translate with the body during drag, file-backed rows require an explicit face click before Center Row->Optical Axis, Delete/Backspace removes the selected imported STEP overlay or selected promoted STEP optical-solid row, and Pupil/field aperture-envelope plus explicit physical-source launch patterns remain stable across the overlay-to-row and face-assignment transitions. Face-function writes now drop stale traced system/ray/bundle caches, clear transient STEP trace plans, and force an already-open Open 3D view to retrace; the full face-role editor also saves combobox, focus-out, Enter, checkbox, and Apply Form edits immediately to row metadata instead of keeping them dialog-local until Save Roles, while right-click assignment now prefers the traced ray-hit CAD face near the cursor when the user is debugging a visible ray/surface event. This prevents a ray-hit `F004` surface from staying transmissive because the generic mesh picker selected a neighbouring shell triangle, and imported STEP promote-and-assign now remaps temporary overlay face labels by picked world point/normal after promotion so the same physical fold face keeps its intended function even if the promoted row uses a different `F###` label. Open 3D now has a right-docked STEP element browser that lists imported overlays and promoted STEP optical-solid rows under Optical Element, Imaging Lens, and Camera / Detector; clicking a browser item selects and highlights it in the viewport, syncs promoted rows back to the editable table, and exposes selected-element property/actions. STEP face hover badges now report both the live pick coordinate and the detected surface center, while `Snap STEP Normal->Optical Axis` now anchors on the surface center by default and a separate pick-point normal snap remains available for intentional decentered beam-splitter or offset placement. Delete/Backspace target resolution and selected STEP face records have started moving behind the toolkit-light `Open3DStepStateService`, which chooses between the active imported overlay and selected promoted STEP rows and normalizes picked-point/surface-center/normal state outside the Tk/VTK widget layer. Remaining performance/service extraction for very large CAD drag workflows is tracked under the production refactor table rather than as a North Star blocker. |
| Upstream main integration | Triaged | `████░░░░░░ 40%` | Local `main` is fast-forwarded to `origin/main` without checking out or dirtying the branch. The low-risk packaging metadata from upstream has been adopted through `pyproject.toml`, and local prism attachment byproducts are ignored so user screenshots/CAD side files do not block sync. Runtime changes around `BundleTrace`, `RayKeeper`, `Display`, `GeometryBackend`, `MeshBlock`, lazy PyVista, and new pytest coverage are useful but require selective integration because a full merge would overwrite or remove branch-specific UI, Sphinx, optimization, and scene-tracing work. |
| Event-law physics and diagnostics | Achieved | `██████████ 100%` | Canonical ray events own detector reach by default and feed inspectors, per-ray detector aperture status, detector aperture hit/miss reports, source illumination, detector maps, path PSF/MTF, coherent/diffraction analyses, Gaussian-q, throughput, trace-path reports, detector-miss local geometry, detector-plane contact classification for output-port-followed Image targets, folded-preview provenance, direct Open 3D mirror-face hits and TIR/reflection events that keep same-solid CAD/STL faces eligible until a real exit or terminal event, scalar Snell finite-vector hardening at critical/grazing incidence, scene-scaled non-sequential near-hit tolerances instead of the old fixed 0.05 mm skip window, Open 3D terminal summaries that report the last CAD face/action plus the dominant face/action path sequence for escaped or stopped rays, and CSV export. |
| Arbitrary prisms and CAD solids | Achieved | `██████████ 100%` | Face identity, orientation-invariant coplanar CAD-face grouping with same-plane assignment propagation, geometry-derived uncoated face-intent suggestions, direct picked-face assignment without Left/Right/Up/Down side labels or inferred output ports, display-only STEP overlay promotion into traceable row-backed optical solids with positive axial clearance and scene-object `AxisMove=0` isolation, same-row face continuation for CAD/STL reflection and total-internal-reflection events, imported right-angle STEP central-ray TIR on an uncoated BK7-air hypotenuse, cascaded row-scoped boundary/volume records, real multi-STL trace coverage, runtime output-port scene bounds, closed-solid media transitions, Image-as-detector terminal policy, detector-miss plane projection, through-body transparent CAD picking for internal faces such as cube beam-splitter diagonal planes, and prism/CAD diagnostics are covered by regression validators. |

Overall branch direction: keep moving toward one scene/event truth source while
preserving exact sequential prescriptions as the ordered-path special case.

Current pipeline checkpoint:

| Item | Status | Progress | Notes |
| --- | --- | --- | --- |
| Open 3D STEP reselect rotation handles | Achieved | `██████████ 100%` | Blank-click deselection still clears selected STEP state and removes rotation-handle actors, but a later STEP body/face click now rebuilds the in-scene rotation handles immediately. Plain STEP face selection records the face for later normal/surface-center actions without automatically arming `Snap STEP Normal->Optical Axis`, so rotation-handle hover and click remain available until the user explicitly starts a snap command. |
| Open 3D splitter branch bundle display | Achieved | `██████████ 100%` | The Open 3D `world_envelope` sampler now detects splitter/branched raykeeper paths before applying through-going envelope reduction. When a beam splitter expands one launch ray into reflected/transmitted child paths, the sampler keeps the full boundary launch bundle so the displayed cube/prism splitter shows the whole beam split instead of only the center ray pair. |
| VTK 9.5 overlay API cleanup | Achieved | `██████████ 100%` | Open 3D text overlays now use `AddViewProp` / `RemoveViewProp` through a renderer helper, with deprecated `AddActor2D` / `RemoveActor2D` retained only as older-VTK fallbacks. This removes VTK 9.5 deprecation warnings from the mode badge, ray-terminal summary, placement-grid status, hover status, and ray-event label overlays. |
| Tk teardown callback cleanup | Achieved | `██████████ 100%` | Custom table selection, table-grid, and active-cell-border callbacks now keep cancellable `after` ids and are cancelled during editor teardown. This prevents stale Tk callbacks such as `_update_active_cell_border`, `_emit_custom_table_selection_changed`, and `_update_table_grid` from firing after the root window has been destroyed. |
| Internal cube beam-splitter continuation | Achieved | `██████████ 100%` | Internal optical-solid beam-splitter faces now preserve the current glass volume instead of toggling to glass-air at the diagonal plane, and reflected/transmitted child branches keep the same solid eligible for the next exit-face hit. Open 3D face hover/selection outlines now use the full planar face boundary, so cube internal splitter faces highlight as one enclosed diagonal face instead of small triangulation patches. |
| STEP face-level partial reflectors | Achieved | `██████████ 100%` | Optical-solid face metadata saved from Open 3D `Partial Reflecting / Transmitting` now feeds the deterministic non-sequential branch tracer directly. Face-level `Beam Splitter` records carry split ratio, loss, and phase into reflected/transmitted child paths instead of being treated as a one-way mirror or a plain uncoated face. |
| Blank starter launch default | Achieved | `██████████ 100%` | Reset/new blank Object+Image layouts now start in `Object mode = Infinity` with angle-field sampling, so Open 3D `Pupil / field` displays a parallel aperture-envelope launch by default. Explicit finite-object presets and saved layout settings still preserve their finite-object cone semantics. |
| Open 3D world-envelope axes | Achieved | `██████████ 100%` | The default `Pupil / field` Open 3D launch keeps a real center reference ray alongside the aperture-envelope rim, selected through-going envelope traces retain that center ray, and traced `Optical Axis 2+` overlays now appear on external beam legs after a prism/solid exit: inter-element exit-to-entrance legs and the final post-surface leg. Same-row internal prism reflection legs are filtered out, so optical-axis guides describe placeable external axes instead of internal folded paths. |
| Open 3D camera/guide bounds | Achieved | `██████████ 100%` | Traced `Optical Axis 2+` guides for escaped paths are now anchored near the last real surface event instead of at the midpoint of KrakenOS' synthetic escaped terminal tail. Open 3D camera-fit and clipping-range updates ignore optical-axis guide actors, so clicking Iso/YZ/XY/XZ or dragging the camera no longer frames the scene around an outlier guide and makes the optical elements disappear. |
| Open 3D ray-pick gating and 3D penta cascade guard | Achieved | `██████████ 100%` | Passive ray clicks no longer open the Ray Inspector by default; the View toolbar now has an explicit `Pick rays` toggle, and STEP surface-normal/surface-center axis-pick modes hide regular ray actors so the dotted Optical Axis remains the intended second-click target. The Ray Inspector ray table is horizontally scrollable when intentionally opened. `validate_penta_mirror_3d_cascade.py` mimics importing the 42779 penta STEP, selecting/snap-aligning the entrance face, promoting it, assigning the two fold faces as `Full Reflecting`, and proving a finite collimated bundle reflects from both mirror faces and exits in a rolled 3D direction. `validate_five_penta_prism_cascade.py` now uses a two-vector vendor-face pose solve for five cascaded penta prisms: F005 is constrained as the upstream entrance face, F006 is constrained to the requested downstream axis, and F003/F004 remain the vendor mirror faces. The validator checks a 13-ray collimated bundle against five exact row-local `F005 refraction -> F003 reflection -> F004 reflection -> F006 refraction` groups instead of fitting face assignments from an already-traced path. |
| Open 3D trace/render mesh congruence | Achieved | `██████████ 100%` | Open 3D file-backed optical solids now render the same runtime mesh used by the KrakenOS trace instead of replacing it with a separately transformed STL display mesh when the runtime mesh is available. The five-penta guard measures every ray/surface event point against the rendered mesh and fails if any visible prism surface is detached from the physical event location, preventing "ray bends in empty space" screenshots from passing. |
| Open 3D assigned-face tint congruence | Achieved | `██████████ 100%` | Assigned face tints now use the runtime trace mesh cell triangles for row-backed optical STEP solids, with the old STL-transform reconstruction retained only as a fallback. This keeps transparent bodies, dark feature edges, and colored face-function overlays in the same coordinate frame instead of showing a separated ghost solid around prisms. |
| Five-penta stage snapshots | Achieved | `██████████ 100%` | The five-penta guard now captures one Open 3D image after each prism is placed and traced, plus final ISO/YZ/XY/XZ snapshots, a generated 2D YZ/XZ/XY projection image, and a JSON report. Each stage verifies zero launch-angle spread for a 13-ray collimated disk source, the exact accumulated penta face/action sequence, sub-micron event-to-rendered-mesh congruence, regenerated body/edge/tint alignment, and the expected external exit-axis count without internal reflection axes, so visual regressions from element 2 onward are checked against the same physics oracle. |
| Literal click-to-cascade placement | Achieved | `██████████ 100%` | The Open 3D imported-STEP face selection now preserves the picked face id, and the snap-to-axis command routes known 42779 penta entrance picks through the same deterministic two-face solver used by the five-penta reference guard. F005 is constrained to the incoming optical axis and F006 constrains roll/output direction before promotion, so the import/click/snap/promote path is no longer an entrance-normal-only placement. `validate_penta_mirror_3d_cascade.py` now requests a concrete +X penta exit direction and fails unless every ray follows the assigned vendor mirror faces and exits along that direction. |
| Open 3D editable thickness dimensions | Started | `██████░░░░ 60%` | The shared Physical Distance toggle now also draws Open 3D double-ended dimension arrows between adjacent editable-table rows. Each arrow uses the current 3D row/reference geometry, carries a numerical `Thickness` label, is pickable in the embedded VTK scene, and opens a row-scoped thickness editor that updates only that table row before forcing an Open 3D retrace. Remaining work is replacing the modal numeric prompt with an inline label editor and adding drag-to-adjust distance handles. |

Latest movement on 2026-05-24: the remaining 98% Live 3D authoring milestone is
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
ray-terminal summaries, placement-grid status, hover labels, or ray-event
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
- Promoted/file-backed STEP optical solids retain a transparent body in Open 3D
  after face assignment and during ray-on refresh; manual face functions are
  still shown with separate non-pickable surface tints. File-backed solids now
  draw a dark silhouette edge plus a body-colored feature edge, suppress
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
| `services/` boundary for Open 3D trace refresh | Started | `██████████ 98%` | `Open3DTraceRefreshService` owns sampling-mode normalization, Live Mode preview-bundle creation, open-inspector synchronization, and transient STEP live-trace row creation through the editor trace contract. The `open3d_face_pick` service owns through-body transparent CAD face picking for internal planes, `Open3DStepStateService` owns delete-target resolution plus selected STEP face records for normal/surface-center optical-axis actions, `Open3DThicknessDimensionService` owns Open 3D table-Thickness dimension geometry plus the row-scoped edit action, `Legacy3DSceneService` owns legacy PyVista scene body/ray/helper assembly, `LayoutSettingsService` owns persisted layout settings collect/apply for source, STEP import, operand, analysis, and tolerance-preset state, `LayoutFileWriterService` owns self-contained Python layout serialization, `RayInspectorRecordService` owns RayKeeper/SceneBundle Ray Inspector record collection, `NonSequentialSceneGraphRecordService` owns the scene/source/target/placement/volume/face records used by the Non-Sequential Scene Graph, `FormulaHelpService` owns the generated optics formula-sheet HTML, and `ToleranceStackupService` owns stack-up dashboard/report/CSV record assembly. Remaining service work is stale-request cancellation, CAD mesh reuse/throttling, and moving STEP overlay import/carry/promotion/face-assignment transitions behind one service-owned state machine. |
| `panels/` boundary for Open 3D controls | Complete | `██████████ 100%` | `Open3DLiveControlsPanel` owns the left-docked Live Controls UI, `Open3DTopControlsPanel` owns the View, Scene, and Carry toolbar rows, and `MainSourceControlsPanel`, `MainFieldControlsPanel`, `MainTraceDisplayControlsPanel`, `MainToleranceReportDialogs`, `MainNonSequentialSceneGraphDialog`, `MainPathDetectorAnalysis`, `MainAnalysisToolbarPanel`/`MainInformationPanel`, `MainBranchGaussianQDialog`, `MainBranchThroughputReportDialog`, `MainRayTraceInspectorDialogs`, `MainDetectorApertureReportDialog`, `MainSourceIlluminationReportDialog`, `MainOptimizationPanel`, `MainParaxialAnalysisDialogs`, `MainGlassCatalogBrowserDialog`, `MainOpticalSolidDialogs`, `MainOpticalSolidFaceRolesDialog`, `MainPathComponentPlacementDialog`, `MainLensDrawingDialogs`, `MainAtmospherePanel`, `MainCoatingMaterialDialog`, `MainDiffuseScatterDialog`, `MainSurfaceShapeBuilderDialog`, `MainBeamSplitterDialog`, `MainErrorMapDialog`, `MainAdvancedSurfaceDialog`, `MainSurfaceSettingsDialogs`, `MainContextMenu`, `MainSceneElementDialogs`, `MainSceneSourceManagerDialog`, and `MainStockLensImporterDialog` own the main Source, Field, Trace/Display, tolerance report, Non-Sequential Scene Graph, path detector map/PSF/MTF/coherent/branch-field/diffraction analysis orchestration, analysis-toolbar, Information, Branch Gaussian Q report, Path Throughput report, Ray Inspector/Trace Path Inspector, Detector Aperture report, Source Illumination report, Optimization panel and bounds dialog, Paraxial Matrix/Gaussian analysis dialogs and paraxial solve confirmations, Glass Catalog Browser, optical CAD/STL diagnostics, numeric placement, face-role assignment, traced path component placement, Lens Drawing Surface Properties/export dialogs, Atmosphere, Coating/Material, Diffuse/BRDF, Surface Shape Builder, Beam Splitter, Error Map, Advanced Surface, Galvo overlay, Grating settings, main table context-menu, Detector, Scene Target, Path-Local Pose, Element Settings, Scene Source Manager, and stock-lens importer surfaces without moving analysis math, branch Gaussian q report, path throughput report, ray/trace-path inspector, detector aperture report, source illumination report, tolerance report, non-sequential scene graph, optimization, paraxial matrix/Gaussian dialog, glass-catalog browser, optical-solid utility dialog, optical-solid face-role editor, path-component insertion, lens drawing dialog, coating, scatter, shape, splitter, error-map, advanced-surface, galvo, grating, detector, scene-target, path-pose, element, source-manager, stock-lens importer, or menu action execution out of the editor model. Remaining UI reductions should move services/widgets rather than grow this panel slice. |
| `widgets/` reusable Tk controls | Started | `█░░░░░░░░░ 10%` | `KrakenOS/UI/widgets/tooltips.py` now owns the reusable compact Tk tooltip used by toolbar and dialog controls. Validated entries, combobox commit helpers, projection selectors, menus, and table cell widgets still live mostly in `layout_editor.py`. |
| Live Mode performance service | Pending | `░░░░░░░░░░ 0%` | Debouncing exists; cancellation, mesh throttling, and row-plan reuse need a stronger service contract before enabling Live Mode by default on heavy CAD scenes. |
| `sv-ttk` theme adapter | Pending | `░░░░░░░░░░ 0%` | Theme work waits until panels/widgets/services are split enough that styling is a thin layer instead of another responsibility inside `layout_editor.py`. |
| Public `kraken-os[ui]` install path | Pending | `░░░░░░░░░░ 0%` | The intended branch install command is documented below; packaging metadata and clean-venv validation are still needed. |

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
   toolbar wiring.
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

Continue the production-readiness refactor by moving Open 3D STEP overlay
import/carry/promotion transitions into `Open3DStepStateService`. The target is
one state machine for transient STEP overlays and promoted optical solid rows,
so stale actors, duplicate visible solids, and display-only solids cannot
diverge from the traced physics state. The next validator should drive import,
carry/drop, accept/promote, face assignment, reassignment, and Trace Ray through
service-owned transition records rather than direct widget fields inside
`Kraken3DInspector`.
