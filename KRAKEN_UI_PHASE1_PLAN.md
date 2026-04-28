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


## Current Immediate Task

Start with M1:

1. add trace diagnostics to the Information panel
2. add a ray inspector window for the current preview trace
3. keep the implementation independent from later true branching support
