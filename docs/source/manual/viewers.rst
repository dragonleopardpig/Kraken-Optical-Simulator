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

Lens drawing PDF export
~~~~~~~~~~~~~~~~~~~~~~~

``File -> Export Lens Drawing...`` opens a surface-properties dialog before it
writes the ISO-style PDF. The dialog saves drawing-only metadata in each row's
``DrawingProperties`` advanced attribute: clear aperture, form/power callout,
scratch-dig, coating note, and surface note. Blank fields remain placeholders in
the generated drawing. These fields are fabrication notes only; the ray tracer
continues to use the native KrakenOS surface attributes such as ``Rc``,
``Diameter``, ``Glass``, ``Coating``, and ``Drawing``.

3D display
----------

The manual's 3D viewer supports optical surfaces, rays, and STL-backed objects.
Current UI coverage:

* embedded 3D viewer
* legacy 3D viewer compatibility
* ray show/hide toggles
* 3D ray click-to-inspect
* plain left-click selection without camera motion; left hold-drag rotates
  around the current view focal point with fixed sensitivity, and ``Ctrl`` +
  left drag follows the same path for compatibility
* ``Center Row->Ray`` click workflow for centering a selected surface or
  CAD/STL row on a traced ray
* optical surface meshes and solid-body meshes in the shared scene bundle
* row selection highlighting for surfaces and elements
* imported STEP axis centering: click ``Center STEP Axis`` and then click a
  planar/circular outer feature on any imported STEP component; the picked
  feature center moves onto the optical axis. If a STEP component is already
  selected, clicking a KrakenOS optical surface centers that STEP axis on the
  surface center.
* long dotted optical-axis guide in 3D at ``X=0, Y=0``

CAD/STL optical solids
----------------------

The manual examples include STL solids, an image slicer, and solid object
arrays. Vendor parts are more often supplied as STEP/IGES, so the UI accepts
STL directly and meshes STEP/STP/IGES/IGS through ``gmsh`` into a cached STL for
KrakenOS tracing. Current UI workflows:

* ``File -> Import Optical CAD/STL Solid...`` for first-class optical-solid
  import; after the row is inserted the face-assignment dialog opens
  automatically
* ``Actions -> 3D Place/Orient Selected CAD/STL Solid`` for in-view placement,
  axis alignment, and centring inside the existing 3D view
* ``Actions -> Assign CAD/STL Optical Faces`` for recording face roles, with
  assigned roles shown as coloured normal markers in the 3D inspector and
  placement preview; the face preview uses the same click-select and left-drag
  fixed-speed rotate behaviour as Open 3D
* ``Shape...`` path staging for ``Solid_3d_stl``
* row tilt/decenter alignment for the solid object
* ``Actions -> Inspect Optical CAD/STL Solids`` topology and scale diagnostics
* Non-Sequential Scene Graph inspection of CAD/STL rows
* non-sequential tracing and trace-path diagnostics

An imported row stores the native KrakenOS ``Solid_3d_stl`` attribute in row
advanced metadata. For CAD sources, ``OpticalSolidSourcePath`` records the
original STEP/IGES file and ``Solid_3d_stl`` points to the cached mesh. The row
material controls refraction, the mesh supplies only geometry, and dimensions
are interpreted as millimetres. ``Auto`` scene trace resolves to
``Non-Sequential Preview`` for these rows so rays are traced with KrakenOS
``NsTraceLoop`` instead of the axial sequential special case. The 2D plot shows
a projected mesh footprint outline for file-backed solids so the solid body
remains visible even when rays pass through or overlap it.

For arbitrary prism shapes, use closed/manifold meshes with correct face
normals. Start from ``KrakenOS/Examples/Examp_Phase6_Optical_STL_Prism.py`` and
replace the mesh path, material, pose, and source bundle.

Arbitrary-prism workflow status: the current UI can import, diagnose, trace, and
display a closed optical solid, but raw table pose editing is not the intended
authoring experience. Treat ``TiltX/Y/Z`` and ``DespX/Y/Z`` as the saved
KrakenOS execution representation. The practical workflow should be a
face-role scene-object workflow:

1. Import the STEP/STL/IGES file. The UI inserts the optical-solid row and
   immediately opens the CAD/STL face-assignment dialog.
2. Select mesh/CAD faces and assign a 2D side label plus an optical function.
   Side labels are ``Left``, ``Right``, ``Up``, ``Down``, ``Front``, and
   ``Back``; the first four are referenced to the YZ 2D plot. Functions are
   ``Transmit/Port``, ``TIR``, ``Mirror``, ``Beam Splitter``, or
   ``Absorber/Mechanical``.
3. Assign the solid material and face coatings. A beam-splitter face also needs
   split ratio, loss, phase, and later P/S/Jones behavior.
4. Keep ``On Save: orient Left face as ray input`` enabled for the common
   prism convention. When roles are saved, the labeled ``Left`` face is
   centered on the row plane and its outward normal is aligned to layout
   ``-Z``; this means the layout chief ray travels ``+Z`` into the prism. The
   ``Up``/``Down``/``Front``/``Back`` labels provide the roll constraint.
5. If the input ray is not the row optical axis, select the layout ray/path
   that should enter the prism and snap the chosen face to that ray instead.
6. Let the UI solve the object pose, then write only the solved transform back
   to the surface row.
7. Validate with a live chief-ray and bundle trace: show hit sequence, face
   role, incident/outgoing medium, surface normal, Snell/TIR/reflection/split
   decision, and stop reason.

For the standard axial prism workflow, side labels are enough to create an
initial pose because ``Left`` defines the input face and the other side labels
define roll. General off-axis placement still needs a ray/path target,
face-normal flip controls, clear apertures, internal reflecting faces,
material/dispersion, and optional virtual internal planes for vendor cube beam
splitters whose CAD contains only the outer cube.

The implemented face-role slice is available through ``Actions -> Assign
CAD/STL Optical Faces``. The dialog renders the actual STL/CAD mesh at the
current row pose and creates one selectable 3D actor per planar face candidate.
Click a coloured face in the preview to select that candidate, then assign a
``2D side`` and an ``Optical function`` with the quick buttons or the detailed
form on the right. A plain click selects; left hold-drag rotates the preview
around the current focal point with fixed sensitivity, matching Open 3D instead
of VTK's default accelerated trackball behaviour. ``Left``/``Right`` are along
the 2D layout Z direction and ``Up``/``Down`` are along Y; ``Front``/``Back``
are available for full 3D orientation notes. By default, ``Save Roles`` also
uses the ``Left`` label as the input-face convention and writes the solved
``TiltX/Y/Z`` and ``DespX/Y/Z`` pose back to the row. The face list remains available as a fallback and as a
compact audit table. The face list emulates cell wrapping from the current
column width because Tk's native tree table does not wrap cell text by itself.
Drag a column separator to reflow the visible cells, or double-click a column
separator to auto-fit that column to its full content. ``TIR`` means total
internal reflection. Split ratio is only shown and editable for faces whose
function is ``Beam Splitter``; phase and loss are enabled only for face
functions where those quantities are meaningful. If one physical optical
interface appears as two CAD
faces, such as a split cube-beam-splitter interface, select both face rows with
Shift/Ctrl and press ``Splitter`` so the same function metadata is applied to
both candidates.

If the installed VTK package does not ship ``libvtkRenderingTk.so``, the dialog
uses the Matplotlib/Tk 3D picker directly instead of first trying the broken
VTK/Tk widget path. This is expected for the standard pip VTK wheels: they ship
the Python ``vtkTkRenderWindowInteractor`` wrapper but not the native
``libvtkRenderingTk.so`` Tk widget library.

The same dialog now includes a ``Virtual Internal Plane`` workbench for
cube-style beam-splitter CAD. After labeling the outer ``Left``, ``Right``,
``Up``, and ``Down`` faces, use ``Auto Cube Splitter Plane`` to derive a saved
45-degree internal diagonal with split, loss, phase, and aperture metadata.
The plane is previewed in 3D and stored alongside the face labels inside
``OpticalSolidFaces``.

.. figure:: ../_static/manual/ui/cad_stl_face_assignment.png
   :alt: CAD/STL optical face-assignment dialog with face table, 3D preview, side labels, and optical functions
   :width: 100%

   ``Actions -> Assign CAD/STL Optical Faces`` opens the face table, 3D face
   preview, side labels, and optical-function quick buttons for the selected
   optical solid row.

The project devenv uses ``python313Packages.vtk`` from nixpkgs for the VTK
Python module and sets ``KRAKEN_VTK_TK_LIB_DIR`` to the same package's ``lib``
directory. ``kraken-install`` removes any pip-installed ``vtk`` wheel so the
venv does not shadow the Nix VTK build. Use ``devenv shell kraken-vtk-tk-check``
to verify that the UI can see the native VTK/Tk widget.

For a non-devenv setup, install or build VTK with ``VTK_USE_TK=ON`` and make the
directory containing ``libvtkRenderingTk.so`` visible to the UI. KrakenOS
searches the VTK package directory, the Python ``lib`` directory,
``/usr/local/lib``, ``TCLLIBPATH``, ``LD_LIBRARY_PATH``, and the explicit
``KRAKEN_VTK_TK_LIB_DIR`` or ``VTK_TK_LIB_DIR`` environment variables. Keep the
Python ``vtk`` module and ``libvtkRenderingTk.so`` from the same VTK build to
avoid ABI mismatches.

Assigned side/function labels are saved with the optical solid row as
``OpticalSolidFaces`` metadata and are drawn in the embedded 3D inspector and
isolated placement preview as coloured face-centre/normal markers. Snap-to-ray
pose solving remains the next scene-object workflow step.

The future prism workflow should validate these cases before it is considered
complete:

* BK7 wedge-prism deviation with the expected media transition
* right-angle prism total internal reflection
* classic prism dispersion pose, including visible output steering
* missed-ray and clipped-ray diagnostics on the selected solid
* agreement between 2D slice, 3D view, ray inspector, and STEP ray-envelope export

Vendor CAD caveat: a downloaded cube beam-splitter STEP is usually mechanical
geometry, not a complete optical prescription. Import it for external cube
boundaries/placement, then add a table ``Beam Splitter`` surface or use
``Insert Component Below -> Cube Beam Splitter`` for the internal 45 degree
coating/path physics. The CAD mesh alone cannot infer coating ratio, phase, or
cemented internal splitter behavior.

The new virtual internal plane metadata helps author that missing diagonal and
keep it attached to the imported CAD row, but current tracing still follows the
closed STL/CAD envelope. Treat the virtual plane as saved authoring intent and
3D preview data for now; use the validated cube primitive or a real
``Beam Splitter`` row when you need traced reflected/transmitted branches today.

Face roles do not move or center a CAD/STL solid. They say which imported faces
are optically meaningful. To put the cube/prism on the beam, use
``Actions -> 3D Place/Orient Selected CAD/STL Solid`` and then
``Center Row->Ray`` in the 3D inspector, or edit row ``TiltX/Y/Z`` and
``DespX/Y/Z`` directly. A future snap solver should combine the selected input
face, a clicked beam/path, and a roll/output constraint to solve this placement
automatically.

The placement dialog now provides the first explicit anchor/roll slice of that
future solver:

* ``Anchor face`` chooses one assigned optical face or ``Auto``.
* ``Roll constraint`` can use the saved side labels as a simple roll guide.
* ``Face -> +Z`` or ``Face -> -Z`` aligns the chosen face normal to the layout
  optical axis, then recenters that face on the row plane.
* ``Face -> Ray`` or ``Face <- Ray`` aligns the chosen face to the currently
  selected traced ray and snaps the face anchor onto the nearest picked point on
  that ray.
* ``Face -> Path`` or ``Face <- Path`` aligns the chosen face to the currently
  selected Path-view frame and snaps the face anchor onto the nearest point on
  that traced path axis.
* ``Anchor X/Y`` and ``Anchor On Row`` shift the selected face centroid instead
  of the whole mesh bounding box.

The selected ray can come from the 2D plot, 3D view, or Ray Inspector. The
current path frame comes from the top ``Path`` dropdown above the 2D plot. This
is still not a full output-constrained prism solver, but it is now a real
path-frame placement bridge between saved face metadata and traced scene data.

Virtual internal planes are drawn in the embedded 3D inspector and CAD placement
preview as translucent diagonal overlays with a normal arrow, so the stored
cube-splitter authoring intent remains visible while you place the solid.

The mesh diagnostics report checks triangle count, bounds, open boundary edges,
non-manifold edges, degenerate triangles, signed volume, and likely face winding.
It cannot certify optical design intent; it only catches the common mesh defects
that make a closed prism fail to steer rays according to Snell/reflection laws.

Placement workflow
~~~~~~~~~~~~~~~~~~

After importing a CAD/STL solid, first complete the automatically opened face
assignment dialog. If the saved ``Left`` input convention is not enough, select
that row and open ``Actions -> 3D Place/Orient Selected CAD/STL Solid`` for
manual pose controls. If embedded VTK/Tk is available, the embedded 3D
inspector highlights the solid row and opens a
``CAD/STL placement handler`` right-side panel inside the 3D inspector. The
panel stays visible when the main UI is tiled or fullscreen and does not cover
the 3D scene. If only the legacy PyVista viewer is available, the bottom
``STL`` row contains the placement buttons. Both paths
write the row ``TiltX``, ``TiltY``, ``TiltZ``, ``DespX``, ``DespY``, and
``DespZ`` values while the 3D view refreshes.

Use ``Fit+Z``, ``Fit+X``, or ``Fit+Y`` to state which STL-local axis should
become the layout optical axis (layout ``+Z``). For example, use ``Fit+Z`` when
the prism was modeled along local Z, or ``Fit+X`` when the CAD model's length is
local X. ``Center`` translates the rotated mesh so its X/Y bounding-box centre
lies on the optical axis. ``Front`` translates the rotated mesh so its minimum Z
bound sits on the selected row plane.

The embedded handler also provides one-click ``X/Y/Z +/-90`` rotations,
``Center X/Y``, ``Front On Row``, and ``Done -> 2D``. Closing only the handler
keeps the 3D view open; pressing ``Done -> 2D`` refreshes the 2D plot from the
same row pose.

If ``OpticalSolidFaces`` metadata is present on the selected row, the 3D view
draws assigned side/function labels as coloured markers:

* grey: side-only or unassigned function
* blue: ``Transmit/Port``
* amber: ``TIR``
* silver: ``Mirror``
* red: ``Beam Splitter``
* black: ``Absorber/Mechanical``

Use the ``Faces...`` button in the embedded 3D inspector, or ``Assign Optical
Faces`` in the isolated placement preview, to reopen the role editor for the
selected solid. After saving roles, press ``Refresh`` or ``Render`` to redraw
the markers.

Use ``Center Row->Ray`` when manual CAD placement is hard to judge visually.
Click the button, click the surface/CAD row to move, then click the target ray.
For ordinary rows the editor computes the selected row's surface plane, finds
where the picked ray crosses that plane, and writes the row ``DespX/Y/Z``
values so the surface center moves onto the ray without changing the row
orientation. For file-backed CAD/STL solids with saved ``OpticalSolidFaces``
metadata, the same action now prefers the best assigned optical-face anchor
instead of the generic row center. That makes snap-to-ray placement more useful
for prisms and vendor CAD where the meaningful optical entry face is not the
mesh centroid. This is still an alignment aid; use ``Fit Axis`` and ``Min Z On
Row`` first when the CAD solid also needs orientation or front-face placement.

KrakenOS placement semantics are important:

* the previous row's ``Thickness`` sets the selected CAD/STL row's nominal Z station
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
* selected STEP overlay rotation through a click-open ``STEP rotation handler``
  near the selected component, with persistent ``X/Y/Z +/-90`` buttons for
  successive orientation changes
* selected CAD/STL row placement through a click-open ``CAD/STL placement
  handler`` with axis-fit, rotation, centering, front-plane, and ``Done -> 2D``
  actions
* active 3D workflow badges for ``Center STEP Axis``, ``Obj->LED``,
  ``Center Row->Ray``, and ``Source Target`` pick modes
* STEP export
* external camera overlay workflows

When imported vendor STEP CAD is present, ``Export 3D STEP`` preserves the
original imported STEP BReps, applies the same placement transform used by the
3D view, and adds only the outer traced ray envelope as thin solid STEP tubes.
The ray envelope is exported as renderable solid geometry because several CAD
viewers import STEP wire curves but do not display them by default. This keeps
mechanical review focused on clearance and beam footprint instead of every
individual preview ray. File size is expected to be at least the sum of the
imported vendor STEP files plus the ray envelope tubes and analytic optical
surfaces.
