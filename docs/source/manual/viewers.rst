Display And Viewers
===================

The provisional manual documents ``Kos.display2d`` and ``Kos.display3d`` as the
primary display entry points for scripts. The current UI preserves those core
ideas but routes user interaction through shared scene data.

2D display
----------

The layout editor 2D view shows the optical layout, ray paths, folded previews,
ray clipping, cardinal markers, physical-distance annotations, and plot-linked
selection. Phase 4 unified the 2D drawing path around ``SceneBundle``.

3D display
----------

The manual's 3D viewer supports optical surfaces, rays, and STL-backed objects.
Current UI coverage:

* embedded 3D viewer
* legacy 3D viewer compatibility
* ray show/hide toggles
* 3D ray click-to-inspect
* optical surface meshes and solid-body meshes in the shared scene bundle
* row selection highlighting for surfaces and elements

STL solids
----------

The manual examples include STL solids, an image slicer, and solid object
arrays. Current UI workflows:

* ``Shape...`` path staging for ``Solid_3d_stl``
* row tilt/decenter alignment for the solid object
* Non-Sequential Scene Graph inspection of STL rows
* non-sequential tracing and branch diagnostics

STEP and CAD overlays
---------------------

STEP support is beyond the 2021 manual but is available in the UI for real
hardware context:

* lens/camera/LED STEP import
* CAD axis offset picking
* STEP export
* external camera overlay workflows
