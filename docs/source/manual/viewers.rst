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
* ``Actions -> 3D Place/Orient Selected STL Solid`` for in-view STL placement,
  axis alignment, and centring inside the existing 3D view
* ``Shape...`` path staging for ``Solid_3d_stl``
* row tilt/decenter alignment for the solid object
* ``Actions -> Inspect Optical STL Solids`` topology and scale diagnostics
* Non-Sequential Scene Graph inspection of STL rows
* non-sequential tracing and trace-path diagnostics

An imported STL row stores the native KrakenOS ``Solid_3d_stl`` attribute in row
advanced metadata. The row material controls refraction, the STL supplies only
geometry, and mesh dimensions are interpreted as millimetres. ``Auto`` scene
trace resolves to ``Non-Sequential Preview`` for these rows so rays are traced
with KrakenOS ``NsTraceLoop`` instead of the axial sequential special case. The
2D plot shows a projected STL footprint outline for file-backed solids so the
solid body remains visible even when rays pass through or overlap it.

For arbitrary prism shapes, use closed/manifold STL meshes with correct face
normals. Start from ``KrakenOS/Examples/Examp_Phase6_Optical_STL_Prism.py`` and
replace the STL path, material, pose, and source bundle.

The STL diagnostics report checks triangle count, bounds, open boundary edges,
non-manifold edges, degenerate triangles, signed volume, and likely face winding.
It cannot certify optical design intent; it only catches the common mesh defects
that make a closed prism fail to steer rays according to Snell/reflection laws.

Placement workflow
~~~~~~~~~~~~~~~~~~

After importing an STL, select that row and open
``Actions -> 3D Place/Orient Selected STL Solid``. Import also opens the
current 3D view automatically. If embedded VTK/Tk is available, the embedded 3D
inspector highlights the STL row and exposes an STL placement toolbar above the
viewer. If only the legacy PyVista viewer is available, the bottom ``STL`` row
contains the placement buttons. Both paths write the row ``TiltX``, ``TiltY``,
``TiltZ``, ``DespX``, ``DespY``, and ``DespZ`` values while the 3D view
refreshes.

Use ``Fit+Z``, ``Fit+X``, or ``Fit+Y`` to state which STL-local axis should
become the layout optical axis (layout ``+Z``). For example, use ``Fit+Z`` when
the prism was modeled along local Z, or ``Fit+X`` when the CAD model's length is
local X. ``Center`` translates the rotated mesh so its X/Y bounding-box centre
lies on the optical axis. ``Front`` translates the rotated mesh so its minimum Z
bound sits on the selected row plane.

The 3D view also provides one-click ``X/Y +/-90`` rotations for STL rows. Close
the 3D view or press ``Done -> 2D`` to refresh the 2D plot from the same row
pose.

KrakenOS placement semantics are important:

* the previous row's ``Thickness`` sets the selected STL row's nominal Z station
* ``TiltX/Y/Z`` rotate the STL mesh about the STL file origin
* ``DespX/Y/Z`` translate the rotated STL mesh
* ``AxisMove`` affects transform propagation to later rows, not the local STL
  orientation itself

STEP and CAD overlays
---------------------

STEP support is beyond the 2021 manual but is available in the UI for real
hardware context:

* lens/camera/LED STEP import
* CAD axis offset picking
* STEP export
* external camera overlay workflows

When imported vendor STEP CAD is present, ``Export 3D STEP`` preserves the
original imported STEP BReps, applies the same placement transform used by the
3D view, and adds the traced preview ray bundle as thin solid STEP tubes. The
ray bundle is exported as renderable solid geometry because several CAD viewers
import STEP wire curves but do not display them by default. This produces a full
assembly-style export for mechanical review; file size is expected to be at
least the sum of the imported vendor STEP files plus the ray tubes and analytic
optical surfaces.
