Responsive STEP Handling Architecture
=====================================

Problem Statement
-----------------

Large vendor STEP files, such as camera bodies and imaging lens barrels, can
make Open 3D interaction lag. The visible symptom is slow hover feedback:
moving the mouse over a CAD body waits a long time before an edge or face is
highlighted, and every small mouse move can restart the same lag cycle.

The same vendor files feel responsive in FreeCAD and normal CAD tools because
those tools keep the STEP model as CAD topology first. They tessellate for
display, but they do not treat the display mesh as the only source of truth for
selection, face identity, and assembly state.

Current Kraken Bottleneck
-------------------------

Kraken currently uses a mesh-first path for imported CAD in several places:

- ``cad_import_service.convert_step_to_stl`` converts STEP/IGES through Gmsh
  into STL. This is useful for the existing optical-solid kernel, but it loses
  STEP topology, assembly labels, stable face identity, and exact edge curves.
- Imported STEP overlay picking can synthesize a temporary optical-solid row
  plan via ``_step_overlay_optical_solid_row_plan`` just to resolve a face.
  That can involve transformed mesh generation, STL save/read paths, mesh
  diagnostics, scene placement metadata, and face metadata normalization.
- Hover/right-click picking can read STL triangles from disk, ray-test face
  triangles, rebuild planar outlines, and run PyVista/VTK feature-edge
  extraction during the interaction path.
- ``_picked_feature_info`` scans the actor's cells to find a coplanar connected
  component for a picked triangle. This is roughly proportional to mesh cell
  count for a new hovered cell, so dense camera/lens STEP meshes are painful.
- Triangle/cell IDs from generated STL are used as face-selection stand-ins.
  Those IDs are display artifacts; they are not stable STEP topology IDs.

This explains why the UI can lag even when the renderer itself can draw the
model. The renderer is not the only cost. The selection path is recomputing
geometry and topology-like information after the mouse moves.

What CadQuery Shows
-------------------

The local CadQuery source is useful as an architecture reference. It does not
solve the problem by magic; it shows the right layering.

- Simple STEP import uses OpenCascade ``STEPControl_Reader`` and returns
  ``TopoDS`` shapes wrapped by CadQuery ``Shape`` objects. The STEP shape is
  retained as CAD topology, not immediately collapsed to STL.
- Assembly/color/subshape workflows use XCAF concepts such as
  ``STEPCAFControl_Reader``, ``XCAFDoc_DocumentTool``, document explorers, and
  subshape labels. This is the path that can preserve vendor assembly names,
  colors, and subshape metadata.
- ``Shape.mesh`` checks whether OpenCascade triangulation already exists with
  ``BRepTools.Triangulation_s`` before calling ``BRepMesh_IncrementalMesh``.
  The triangulation is cached on the shape instead of recreated per hover.
- ``Shape.tessellate`` iterates CAD faces and pulls each face's existing
  triangulation through ``BRep_Tool.Triangulation_s``. That pattern naturally
  creates a face-id to triangle-range map.
- ``Shape.toVtkPolyData`` uses OpenCascade's IVtk bridge
  (``IVtkOCC_Shape``, ``IVtkOCC_ShapeMesher``, ``IVtkVTK_ShapeData``) and then
  splits display edges from display faces once for rendering.
- CadQuery assembly export keeps a compound cache to avoid remeshing the same
  repeated object instance.

The Kraken development environment currently has ``pythonocc-core`` available
as ``OCC``. It does not currently have CadQuery or ``cadquery-ocp``/``OCP``
installed. That means the first implementation should use the same
OpenCascade architecture with the available ``OCC`` backend, while keeping a
CadQuery/OCP adapter as an optional study path.

Target Architecture
-------------------

The fundamental change should be a persistent CAD scene cache. Imported STEP
should be loaded once into a document/shape cache and then exposed through
separate display, picking, and optical-physics views.

Proposed service boundary:

``CadDocumentCache``
    Owns the source file key, file timestamp/size/hash, unit, backend, and
    loaded OpenCascade document/shapes. This is the authoritative STEP state.

``CadTopologyIndex``
    Owns stable solids, shells, faces, edges, bounding boxes, centroids,
    normals, areas, surface type hints, assembly names, colors, and source
    labels. It should qualify face IDs by component/solid, not only ``F001``.

``CadDisplayMeshCache``
    Owns coarse/idle display tessellations, VTK/PyVista polydata, edge
    polydata, actor references, and cell-data arrays mapping each display cell
    back to ``component_id`` and ``face_id``.

``CadPickCache``
    Owns lightweight pick proxies: bounding boxes, face polygons, internal
    planes, and prebuilt highlight outlines. Hover should resolve actor/cell to
    face ID from cached data, not reread STL or rebuild face outlines.

``CadOpticalAdapter``
    Owns the mesh/triangle view used by current optical tracing. Short term it
    can still expose triangles, but with stable face IDs and no repeated disk
    reads. Longer term it can add exact OpenCascade ray/surface intersection or
    a BVH over cached triangles.

Interaction Rules
-----------------

The Open 3D interaction loop should become cheap:

1. Import STEP in a worker thread/process. Show a bounding box placeholder and
   progress/status text while topology and display caches are built.
2. Create body and edge actors once from cached polydata. During drag/rotate,
   update actor transforms only; do not remesh and do not rebuild face metadata.
3. On hover, use VTK picking to get actor/cell ID, then lookup face ID through
   cached cell data. If the actor/cell/face is unchanged, do nothing.
4. Highlight using prebuilt face outline actors or cached face-boundary
   polydata. Do not run ``extract_feature_edges`` on mouse move.
5. For transparent solids and internal beam-splitter planes, use pick proxies
   or a controlled pick list. Prefer internal pickable faces only when the
   active command needs them.
6. Right click should assign physics to the cached face ID. Promotion to a row
   must reuse the same face identity instead of generating a separate temporary
   mesh with different face labels.
7. Use level of detail: coarse mesh while interacting, refined mesh when idle.
   Optical tracing must use the validated optical mesh/cache, not the transient
   display LOD.

Expected Improvement
--------------------

The first major win is not exact NURBS tracing. It is removing expensive work
from the hover path.

With the cache architecture, hover should be reduced to:

- VTK pick.
- actor/cell/face lookup.
- optional highlight actor visibility or transform update.
- render.

That is the same basic model used by CAD tools: topology and tessellation are
prepared ahead of interaction, while hover only switches selection state.

Implementation Plan
-------------------

Phase 1: Profile And Freeze The Current Baseline
    Add a validator/diagnostic that imports a large camera or imaging-lens STEP
    and reports import time, triangle count, actor count, hover-pick latency,
    and highlight latency. The initial target should be p95 hover latency under
    50 ms, then under 16 ms for ordinary display-only hover. The branch now
    includes ``python -m KrakenOS.UI.diagnose_open3d_hover_latency`` as the
    headless cache/contract diagnostic; GUI picker timing can be added to that
    command when a stable display backend is available in CI.

Phase 2: Cache The Existing Mesh Path
    Before changing import backends, remove repeated work:

    - cache transformed STEP overlay meshes by source path plus transform;
    - cache STL triangle arrays in memory;
    - cache face metadata for imported overlays;
    - cache face-id to outline polydata;
    - remove temporary row-plan generation from hover/right-click face lookup.

    This phase should improve responsiveness without changing the optical
    tracing contract.

    Current branch progress: the mesh-path responsiveness foundation is
    complete. Open 3D imported STEP hover and transparent face-pick paths now
    reuse cached triangle arrays, cached face triangle slices, and cached
    face-outline artifacts for the existing mesh path. Ordinary passive hover is
    intentionally lightweight: it does not pick dense CAD body actors. It only
    uses a rotation-handle actor pick list, then defers transparent face-ray
    testing, feature scanning, and outline generation to explicit click,
    right-click assignment, or axis/face-pick commands.

Phase 3: Add An OpenCascade Topology Adapter
    Build a new adapter using the installed ``pythonocc-core``/``OCC`` backend:

    - import STEP using ``STEPControl_Reader`` for simple shapes;
    - study ``STEPCAFControl_Reader`` for vendor assembly names, colors, and
      subshape labels;
    - traverse solids/faces/edges with OpenCascade topology tools;
    - mesh once with ``BRepMesh_IncrementalMesh``;
    - write VTK cell arrays for ``component_id`` and ``face_id``.

    Current branch progress: Tier 3 is implemented for supported
    axisymmetric optical lenses. ``KrakenOS.UI.services.step_analytic_geometry``
    loads STEP with OpenCascade before any STL conversion, walks native solids
    and faces, qualifies face IDs by solid, extracts analytic face descriptors
    for plane, sphere, cylinder, cone, torus, and B-spline surfaces, detects
    duplicated cemented interior faces from multi-solid achromats, and produces
    a face-tagged tessellation. Open 3D STEP display and overlay face metadata
    now try this topology-preserving path before falling back to gmsh/STL.

    ``KrakenOS.UI.services.step_native_reconstruction`` uses the same topology
    with interior interfaces retained, groups split vendor patches into one
    optical surface, collapses duplicated cemented faces into a single native
    interface, rebuilds exact sphere/plane surfaces, fits supported
    axisymmetric B-spline surfaces into KrakenOS ``AspherData`` coefficients,
    and emits ordinary ``SurfaceRow`` records. Geometry-only STEP files are not
    treated as trace-ready because STEP often lacks optical glass data. The
    reconstruction reports ``material_sequence_required`` until the caller
    supplies one material after each native surface. Poor B-spline fits are
    likewise rejected with residual diagnostics instead of becoming plausible
    but wrong physics.

    The focused validator is:

    .. code-block:: bash

       python -m KrakenOS.UI.validate_fast_contracts --only step-native-reconstruction
       python -m KrakenOS.UI.validate_fast_contracts --only step-native-promotion

    The current fixture check rebuilds the aspherized achromat STEP as three
    native surfaces: a front sphere, one collapsed cemented spherical
    interface, and one split B-spline/asphere back surface. With a supplied
    material sequence, the result is a normal KrakenOS row stack that can be
    wrapped as ``Object`` / native surfaces / ``Image``. Open 3D exposes this
    as ``Promote STEP to Native Rows`` in the CAD/target menu and ``Native
    Rows`` in the STEP element browser. The command prompts for the material
    sequence, inserts ordinary analytic table rows, applies the current Open 3D
    placement/orientation as row ``Tilt``/``Desp`` values, clears the
    display-only overlay when requested, and keeps the source path plus
    reconstruction diagnostics in row metadata.

Phase 4: Compare CadQuery/OCP
    Install CadQuery/OCP only in an isolated optional environment and compare:

    - STEP import fidelity;
    - XCAF assembly/subshape metadata access;
    - IVtk meshing speed and display quality;
    - face/edge identity stability;
    - package size and deployment cost.

    If CadQuery/OCP is better, add it behind the same adapter interface. Do not
    make it a required runtime dependency until this is proven.

Phase 5: Integrate With Optical Physics
    Keep the North Star rule: display and UI convenience must not hide or
    corrupt native optical state. The topology cache must preserve face
    function, coating, material, detector/absorber roles, ray event metadata,
    and CSV/export diagnostics. If exact OpenCascade surface intersection is
    added later, it should be validated against the current triangle-based
    non-sequential trace before becoming default.

Recommended Immediate Next Step
-------------------------------

Start with the completed Phase 2 mesh path, not a full CadQuery dependency
jump. The current lag is addressed by eliminating repeated STL reads, repeated
face clustering, repeated temporary row-plan promotion, repeated feature-edge
extraction during hover, and full-scene body picking during ordinary mouse
motion.

Once a future requirement needs exact vendor topology beyond the current mesh
metadata, Phase 3 can replace the source of those caches with OpenCascade
topology. That keeps the architecture clean and gives a clear before/after
measurement for any future CadQuery/OCP adoption.
