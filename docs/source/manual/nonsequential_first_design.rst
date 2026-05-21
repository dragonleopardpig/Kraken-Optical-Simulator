Non-Sequential-First Design Goals
=================================

The long-term UI target is a physical scene editor for KrakenOS. Sequential
optical design remains useful, but it is treated as the ordered-axis special
case of a more general non-sequential scene.

This page records the design invariants that future UI work should preserve.

Goal 1: non-sequential tracing is the native model
--------------------------------------------------

The UI should represent an optical layout as a 3D scene containing surfaces,
solid optical elements, sources, detectors, coatings, apertures, and analysis
targets.

Sequential tracing is still supported for conventional lens prescriptions,
paraxial tools, wavefront tools, and imported sequential examples. It should not
be a separate mental model. A sequential lens is simply the case where surfaces
are ordered along one dominant optical path and rays hit them in that order.

Required behavior:

* Scene-style layouts should resolve to KrakenOS non-sequential tracing
  automatically when the user adds physical sources, tilted/folded optics,
  beam splitters, STL solids, detector paths, target surfaces, or
  non-sequential coatings.
* Sequential tracing should remain explicit and reproducible for lens-design
  work that depends on ordered surface indices.
* The UI must keep native KrakenOS state visible through the scene graph, ray
  inspector, trace-path inspector, CSV exports, or advanced attributes.

Achievability:
   This is achievable. The current UI already has automatic scene-trace
   selection, beam-splitter branches, STL solid tracing, path filtering, detector
   analysis, and raykeeper diagnostics. The remaining work is to make all
   authoring workflows path-local and scene-object based instead of relying on
   the user to calculate global table poses by hand.

Goal 2: 3D tracing is authoritative; 2D is only a slice
--------------------------------------------------------

The optical computation should happen in 3D. The 2D ``YZ``/``XZ`` section
plots and ``XY`` footprint plot are diagnostic views of the same 3D ray data,
not independent simplified simulations.

Required behavior:

* Rays, sources, mirrors, beam splitters, prisms, STL solids, detector planes,
  and exported CAD geometry should be generated from 3D scene state.
* The 2D plot should display a selected plane, path, or projected slice of the
  traced 3D bundle.
* The 3D inspector, STEP export, detector map, and 2D slice should agree on
  which rays were traced, where they hit, and where they stop.
* If a 2D slice omits valid off-plane rays, that should be a view limitation,
  not a different tracing result.

Achievability:
   This is achievable. The current display path already uses 3D raykeeper data
   and adaptive 3D source envelopes. Sequential ``Pupil / field`` previews now
   trace shared 3D section bundles for the 2D projections, and Open 3D requests
   the world-envelope trace while preserving explicit fan patterns as section
   fans. Remaining work is mostly consistency: every analysis and export path
   should consume the same traced scene bundle instead of rebuilding an
   independent ray set unless explicitly requested.

Goal 3: object and illumination source are separate scene entities
------------------------------------------------------------------

The Object row defines the object, target, or reference geometry used by
traditional optical design. Illumination sources are physical emitters that can
be placed independently in the 3D scene.

This separation is required for microscopes, scanners, interferometers,
projectors, inspection systems, and beam-splitter illumination paths where the
source is not located at the object and may illuminate the object from another
angle.

Required behavior:

* Users should be able to define multiple illumination sources.
* Each source should have its own position, orientation, wavelength or spectrum,
  ray count, diameter/waist/divergence, power, polarization, and coherence
  metadata.
* Sources should be able to illuminate an object directly or through folded
  optics such as mirrors and beam splitters.
* Illumination analysis should report uniformity, vignetting, throughput, and
  missed-ray diagnostics on the selected object/detector surface.
* Source-only inputs should hide or disable object-only inputs, and object-only
  inputs should not silently affect physical source rays.

Achievability:
   This is achievable, and the source/object split is now implemented at the
   scene-record and authoring-dialog level. The current UI has a physical Source
   panel, Gaussian source input, explicit multi-source records through Scene
   Source Manager, beam-splitter paths, detector analysis, and a Source
   Illumination Report that groups target-surface hits by physical source. The
   ``Illum`` analysis button also plots source-driven target-surface uniformity
   from the same traced records for explicit scene-source layouts.

First implementation step:
   The existing single Source panel is now adapted into one ``SceneSource3D``
   record named ``Source 1``. This record is carried by ``SceneBundle``, shown
   in the Non-Sequential Scene Graph, and stamped onto traced rays through
   ``SOURCE_ID``, ``SOURCE_NAME``, ``SOURCE_ROLE``, and launch-sampling
   raykeeper metadata. This removes the previous hidden global-source assumption
   from the scene data path. Saved layouts may now also declare multiple source
   records through
   ``SETTINGS["scene_sources"]``; those sources trace as independent physical
   emitters, render as separate source markers, appear in the scene graph, and
   preserve per-ray source IDs. ``Actions -> Scene Source Manager...`` now edits
   those explicit multi-source records without turning sources into KrakenOS
   surface rows. Its ``Aim Direction At Row`` helper points a source origin at
   an Object, detector/Image, optical surface, or imported CAD/STL row center by
   computing normalized ``Source L/M/N`` direction cosines; it does not add or
   move prescription surfaces. If an imported CAD/STL row has assigned optical
   face roles, the same target selector can aim at an individual transformed
   face centroid; the CAD/STL face assignment dialog also has ``Use Face As
   Source Target`` to open Scene Source Manager with that face already selected.
   The 3D Inspector ``Source Target`` pick mode does the same from the rendered
   scene: click a surface/CAD solid and the closest assigned CAD/STL face anchor
   is used when available.
   Its ``Place Origin At Standoff`` helper uses the current source direction to
   place ``Source X/Y/Z`` a positive distance upstream of the selected row or
   face target.
   For a minimal editable starting point, load
   ``Layouts -> Sources / Illumination -> Mixed Source/Object Imaging Template``.
   That preset declares one physical ``SETTINGS["scene_sources"]`` emitter,
   places it before Object in the visible scene order, keeps Object as reference
   geometry, and sends source rays through an object-side aperture to the
   detector/Image row. The matching script
   ``KrakenOS/Examples/Examp_Mixed_Source_Object_Imaging_Template.py`` prints
   the source record, row-target aiming result, and detector-hit trace table.

Source row contract:
   The desired editor model is ``Object`` + one or more ``Illumination Source``
   scene entities + ``Image``. The source entries must be scene rows, not
   KrakenOS ``surf`` rows, because physical emitters are not optical boundary
   surfaces and must not consume trace surface indices. Before adding visible
   source rows to the editable table, all selection, detector, and analysis
   code goes through the source-aware ``SceneRowMapping`` bridge instead of
   assuming that UI row numbers and trace surface indices are identical. The
   bridge is carried by ``SceneBundle``. It supports both Object-first and
   source-first scene row orders, so the UI can swap Object and Illumination
   Source rows without touching KrakenOS surface indices. The Non-Sequential
   Scene Graph now shows this mapping explicitly as
   a ``Scene row order`` node. Validate it with ``python -m KrakenOS.UI.validate_scene_row_mapping`` and
   ``python -m KrakenOS.UI.validate_scene_source_row_contract``. The Source panel
   remains the fallback single-source authoring path; Scene Source Manager is the
   explicit multi-source authoring path.

Goal 4: every surface interaction obeys physics law
---------------------------------------------------

When a ray hits a defined optical boundary, the next ray state must be chosen by
the physical properties of that boundary: reflection, refraction, absorption,
diffraction, scattering, polarization, coating response, total internal
reflection, or termination at a detector/stop.

Required behavior:

* A mirror hit cannot transmit unless the row is explicitly configured as a
  partially transmitting mirror or beam splitter.
* A transmissive surface cannot reflect unless Fresnel, coating, metal, or
  beam-splitter behavior asks for a reflected child path.
* A ray that refracts through glass must use the correct incident medium,
  outgoing medium, wavelength, dispersion model, and surface normal.
* STL solid entry/exit events must use the solid material and the actual mesh
  boundary, not a neighboring sequential row assumption.
* Absorbed, missed, vignetted, reflected, transmitted, and detector-hit rays
  must be inspectable.
* Ambiguous or invalid geometry should produce diagnostics instead of a silent
  visually plausible but physically wrong path.

Achievability:
   This is achievable only if physics behavior is centralized in the tracing
   layer and guarded by regression tests. The current UI already validates
   several historical failure modes: splitter branch direction, mirror
   reflection, STL prism media entry/exit, branch detector hits, and 3D envelope
   clipping. More tests are needed for arbitrary solids, coatings,
   polarization, grating diffraction, and multi-source illumination.

Prism/CAD authoring note:
   Arbitrary prism tracing should stay based on real 3D solid geometry, but the
   present table-first pose workflow is not the intended final UX. Future work
   should promote imported prisms into manipulable scene objects in the 3D
   inspector, with visual face/axis selection, ray/path snapping, and direct
   entry/exit hit diagnostics before writing the saved pose back to the
   underlying ``Solid_3d_stl`` surface row.

Implementation checklist
------------------------

Use this checklist before marking a future phase complete:

* Does the workflow operate on a 3D scene object or traced path frame?
* Does sequential operation remain available as a special case?
* Does the 2D view derive from the same 3D trace used by 3D/export/analysis?
* Are physical sources separate from object/reference geometry?
* Can the user inspect why each ray reflected, transmitted, stopped, or missed?
* Is the KrakenOS-native state preserved in table metadata or advanced fields?
* Is there a regression validator for the important physics behavior?
