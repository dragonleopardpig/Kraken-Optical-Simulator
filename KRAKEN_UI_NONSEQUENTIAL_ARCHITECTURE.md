# Kraken UI Non-Sequential-First Architecture

This document records the post-Phase-5 direction for the layout editor.

## North Star

The UI should be non-sequential by design. A KrakenOS layout is a scene of
optical objects, sources, detectors, coatings, masks, STL solids, and path
metadata. Sequential ray tracing remains important, but it should be treated as
the axial ordered-surface special case of the same scene workflow.

The practical rule is:

- use scene/non-sequential tracing whenever the user creates a physical source,
  beam splitter, target surface, probabilistic non-sequential coating, STL
  object, mirror fold, tilt/decenter scene, or detector/path workflow;
- keep exact sequential tracing for conventional lens-design prescriptions and
  paraxial/wavefront analyses that explicitly depend on ordered surfaces;
- never hide KrakenOS-native state behind a UI-only abstraction without
  preserving it in row metadata, scene graph diagnostics, raykeeper metadata, or
  CSV export.

## Current Architecture

The UI already has the necessary foundations:

- one editable surface/object table backed by KrakenOS `surf` rows;
- physical Source panel independent of the Object row;
- `SceneBundle` as the shared 2D/3D display data model;
- Non-Sequential Scene Graph inspector/export;
- Trace Path Inspector/export from KrakenOS `raykeeper` branch/hit metadata;
- deterministic beam-splitter child paths with power, phase, and polarization
  metadata;
- path-aware table filtering, detector-map, path PSF/MTF, throughput, and
  first coherent detector binning;
- source metadata on traced rays.

## Phase 6A: Scene Trace Semantics

Status: active.

Implemented in this slice:

- the left control label is now `Scene trace`;
- `Auto` prefers KrakenOS `NsTraceLoop` for scene-style requests:
  physical source, beam splitter, off-axis/tilted geometry, target surface, or
  probabilistic non-sequential coating;
- `Sequential` remains explicit and available, but is no longer the implied
  architecture for scene workflows.

Next refinements:

- add a small trace-state badge in the UI after Update:
  `Auto -> Non-Sequential Preview` or `Auto -> Sequential`;
- expose the same trace-state summary in exported scene graph headers;
- add regression snapshots for an off-axis physical-source scene that must
  resolve to `NsTraceLoop`.

## Phase 6B: Scene Object Model

Goal: make sources, detectors, beam splitters, mirrors, lenses, STL solids, and
path components feel like scene objects while preserving KrakenOS's ordered
`surf`/object list.

Recommended order:

1. Add a formal UI scene-object schema derived from rows and source settings.
2. Promote detector rows into a first-class detector element model.
3. Add source rows only if users need sources to be moved/reordered in the
   table; otherwise keep the Source panel as the scene source authority.
4. Add path-local component insertion using traced `BRANCH_PATH` frames.
5. Keep the table's row index as the KrakenOS surface/object index so imported
   examples and scripts remain debuggable.

## Phase 6C: Non-Sequential Path Workbench

Goal: users should add optics into a traced path without calculating global
decenter/tilt by hand.

Needed pieces:

- branch-local coordinate frame from incident direction, surface normal, and
  path tangent basis;
- insertion dialogs for lens, mirror, aperture, detector, and catalog element
  at distance along selected path;
- preservation of both global row pose and path-local metadata;
- support for cascaded/nested beam splitters through cumulative `BRANCH_PATH`;
- table filtering that shows common scene rows plus selected path objects.

## Phase 6D: Coherent And Laser Branch State

Goal: make interferometers and laser layouts physically honest.

Needed branch state:

- optical path length and phase through each deterministic child path;
- branch power and polarization vector/Jones metadata;
- Gaussian `q` state with tangential/sagittal separation for tilted optics;
- detector-grid coherent field accumulation;
- validation against Michelson, Mach-Zehnder, and Twyman-Green reference
  layouts.

Until this is complete, ray-only interferometer layouts should remain labeled
as ray/path geometry plus detector diagnostics, not full wave-optics
interferometers.

## Guardrail

When exposing KrakenOS gems, prefer a first-class workflow over raw attribute
passthrough. If a raw attribute is exposed, document what it means, where it is
stored, and how a user can verify its effect through the scene graph, ray
inspector, plot, report, or CSV export.
