# Kraken UI Phase 1 Plan

This file turns Phase 1 from `KRAKEN_UI_FUTURE_ROADMAP.md` into concrete
execution slices. Phase 1 is the "Kraken-specific differentiators" pass, but
it is still too large to implement as one patch. The first deliverable is the
non-sequential foundation because the rest depends on it.


## Phase 1 Scope

1. True non-sequential UI mode
2. Advanced surface editor
3. User-defined/custom surfaces
4. Ray inspector


## What Phase 1 Is Not

- not a full rewrite of the current sequential editor
- not immediate beam-splitter branching physics in one step
- not 3D scene unification; that remains a later architecture cleanup phase
- not merely preserving hidden attrs; the goal is first-class workflows


## Guiding Principles

1. Land useful diagnostics before changing tracing semantics.
2. Separate UI scene-model work from core tracer work.
3. Keep sequential/folded workflows working while non-sequential capability is
   introduced.
4. Reuse the existing scene-bundle pipeline instead of adding more one-off
   display code.


## Milestone Breakdown

### M1. Trace Diagnostics and Ray Inspector

Goal:
- expose what the current preview trace actually did
- give the user a way to inspect individual rays and surface hits

Deliverables:
- explicit trace summary in the Information panel
- ray inspector window with per-ray and per-hit detail
- refresh the inspector when the plot is updated

Notes:
- this still inspects the current sequential/folded preview tracer
- this is the first safe step before branching or target-surface logic


### M2. Explicit Trace Mode Plumbing

Goal:
- make trace semantics visible in the editor instead of hidden in special-case
  display logic

Deliverables:
- UI-level trace mode state
  - Sequential
  - Folded Preview
  - Non-Sequential Preview
- include trace mode in cache/signature keys
- route scene-bundle build through an explicit trace-mode selector

Notes:
- Folded Preview remains the compatibility bridge while real non-sequential
  preview is added


### M3. Non-Sequential Preview Data Model

Goal:
- support world-space rays that are not limited to a single ordered surface
  chain

Deliverables:
- extend scene geometry with branch-aware ray records
- support hit order, target surface, termination reason, and branch id
- preserve enough metadata to inspect missed, clipped, reflected, and
  transmitted paths separately

Notes:
- this is still a preview/display model; it does not yet require full splitter
  branching in the core engine


### M4. Core Non-Sequential Trace Bridge

Goal:
- connect the editor to Kraken's non-sequential engine where it exists today

Deliverables:
- editor path for `system.NsTrace()` / `NsTraceLoop()` scenes
- non-sequential example import path that keeps the scene in non-sequential
  mode
- diagnostics for scenes that still require unsupported branching semantics

Notes:
- this is where prisms, tilted solids, STL scenes, and mirror-heavy examples
  should begin to run through the editor without special display buttons


### M5. Advanced Surface Editor

Goal:
- make currently hidden surface attributes editable

Deliverables:
- advanced surface dialog or expandable card
- first-class controls for:
  - `AspherData`
  - `ZNK`
  - `SubAperture`
  - `Mask_Type` / `Mask_Shape`
  - shifts / decenters / rotations
  - coatings / metal mode where relevant

Notes:
- many of these attrs already survive import/save/load on this branch
- the missing part is the editor workflow


### M6. User-Defined / Custom Surfaces

Goal:
- expose one of KrakenOS's more distinctive capabilities

Deliverables:
- editor support for `ExtraData`
- editor support for `UDA`
- serializer-safe layout persistence for the common custom-surface cases
- validation/error reporting when a custom surface cannot be replayed


## Recommended Execution Order

1. M1 Trace Diagnostics and Ray Inspector
2. M2 Explicit Trace Mode Plumbing
3. M3 Non-Sequential Preview Data Model
4. M4 Core Non-Sequential Trace Bridge
5. M5 Advanced Surface Editor
6. M6 User-Defined / Custom Surfaces


## Acceptance Criteria

### Phase 1A complete

- user can inspect preview rays and their hit chains
- Information panel reports trace family, backend, ray counts, and image hits
- no regression in existing folded/sequential layouts

### Phase 1B complete

- editor exposes trace mode explicitly
- at least one current Kraken non-sequential example can be loaded and traced
  through the editor path without relying on old special-case display code

### Phase 1C complete

- advanced surface editing is usable for common asphere / mask / sub-aperture
  cases
- at least one `ExtraData` or `UDA` example can be edited and replayed from the
  UI


## Current Implementation Status

Phase 1A is implemented:

1. the Information panel reports trace family, backend, ray counts, and image hits
2. the Ray Inspector shows per-ray and per-hit data from KrakenOS `raykeeper`
   with explicit interaction labels such as refraction, reflection, aperture,
   and image hits
3. sequential and folded preview paths remain compatible with the scene-bundle pipeline

Phase 1B is implemented for the current preview bridge:

1. explicit trace mode state exists for Sequential, Folded Preview, and Non-Sequential Preview
2. explicit Non-Sequential Preview now routes preview bundles through KrakenOS `NsTraceLoop()`
3. imported examples that call `NsTraceLoop()` or `system.NsTrace()` are opened in non-sequential mode
4. scene-bundle ray paths now carry per-hit diagnostic records, so coating,
   polarization, and future non-sequential branch tooling do not need to
   re-parse raw `raykeeper` arrays independently

Phase 1C is partially implemented:

1. the Advanced Surface dialog edits common KrakenOS-native attrs such as `AspherData`, `ZNK`, masks, sub-apertures, coatings, notes, and native variable fields
2. `ExtraData` and `UDA` can be edited for literal/list-based custom surface cases
3. imported callable/object custom surfaces are preserved in memory, but remain read-only in the dialog and may be omitted on save when they cannot be serialized safely

Remaining Phase 1 work before declaring the phase complete:

1. finish branch-aware non-sequential path-tree modeling beyond the current
   single-branch preview records
2. add specialized validation/previews for complex advanced attrs such as measured error maps and coating tables
3. implement callable custom-surface authoring/replay for `ExtraData`, `UDA`, and `SPECIAL_SURF_FUNC`
