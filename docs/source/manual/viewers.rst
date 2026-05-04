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

* ``File -> Import Optical STL Solid...`` for first-class optical-solid import
* ``Shape...`` path staging for ``Solid_3d_stl``
* row tilt/decenter alignment for the solid object
* Non-Sequential Scene Graph inspection of STL rows
* non-sequential tracing and trace-path diagnostics

An imported STL row stores the native KrakenOS ``Solid_3d_stl`` attribute in row
advanced metadata. The row material controls refraction, the STL supplies only
geometry, and mesh dimensions are interpreted as millimetres. ``Auto`` scene
trace resolves to ``Non-Sequential Preview`` for these rows so rays are traced
with KrakenOS ``NsTraceLoop`` instead of the axial sequential special case.

For arbitrary prism shapes, use closed/manifold STL meshes with correct face
normals. Start from ``KrakenOS/Examples/Examp_Phase6_Optical_STL_Prism.py`` and
replace the STL path, material, pose, and source bundle.

STEP and CAD overlays
---------------------

STEP support is beyond the 2021 manual but is available in the UI for real
hardware context:

* lens/camera/LED STEP import
* CAD axis offset picking
* STEP export
* external camera overlay workflows
