Tracing And Ray Data
====================

Scene-first UI model
--------------------

The UI is moving toward a non-sequential scene-first architecture. The editable
table is treated as a KrakenOS scene/object list. Exact sequential tracing is
still first-class, but it is the axial ordered-surface special case of that
scene model rather than the UI's long-term organizing principle.

The ``Scene trace`` control therefore behaves as follows:

* ``Auto`` uses KrakenOS ``NsTraceLoop`` when the layout contains a physical
  source, a beam splitter, an STL optical solid, off-axis/tilted scene geometry,
  a non-sequential target surface, or probabilistic non-sequential coating.
* ``Non-Sequential Preview`` explicitly forces the scene trace path.
* ``Sequential`` explicitly forces the ordered-surface axial compatibility
  path.
* ``Folded Preview`` remains a legacy display compatibility mode for simple
  mirror-folded layouts.

2D slices, 3D scenes, and CAD envelopes
---------------------------------------

The UI keeps ray generation 3D-first for scene/CAD workflows:

* The 2D layout is a display slice/projection. In ``YZ`` it intentionally shows
  a meridional fan through the 3D bundle, so a finite-object cone appears as a
  triangular slice rather than a filled cone.
* The 3D inspector is not produced by revolving the 2D sketch. It retraces a
  source-driven 3D boundary bundle around the entrance pupil/object cone, then
  adapts inward to the through-going pupil envelope if the outer launch boundary
  is clipped by the optical train. The 3D ``Full Pupil`` toggle still requests a
  dense full-pupil bundle.
* ``Export 3D STEP`` uses the same source-driven 3D boundary bundle and then
  writes only the outer ray envelope as solid STEP tubes for mechanical review.

This separation matters for arbitrary shapes: STL/STEP solids, prisms, beam
splitters, and future non-sequential components must see true world-coordinate
ray directions, while the 2D view remains a readable diagnostic slice.

Sequential tracing special case
-------------------------------

The manual's basic workflow is:

1. Build ``surf`` objects for Object, optical surfaces, stops, mirrors, and
   Image.
2. Create ``config = Kos.Setup()``.
3. Create ``system = Kos.system(surface_list, config)``.
4. Trace rays with ``system.Trace(source_point, direction_cosines, wavelength)``.
5. Push traced rays into ``Kos.raykeeper(system)``.

Minimal example:

.. code-block:: python

   import KrakenOS as Kos

   obj = Kos.surf()
   obj.Thickness = 100.0
   obj.Glass = "AIR"
   obj.Diameter = 30.0

   lens = Kos.surf()
   lens.Rc = 92.847
   lens.Thickness = 6.0
   lens.Glass = "BK7"
   lens.Diameter = 30.0

   image = Kos.surf()
   image.Glass = "AIR"
   image.Diameter = 20.0

   system = Kos.system([obj, lens, image], Kos.Setup())
   rays = Kos.raykeeper(system)
   system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
   rays.push()

Non-sequential tracing
----------------------

The manual introduces ``system.NsTrace(source_point, direction_cosines,
wavelength)``. Current UI coverage adds:

* ``Auto`` scene tracing that resolves to ``NsTraceLoop`` for source-driven,
  beam-splitter, off-axis, target-surface, or coating-probability scenes
* explicit Non-Sequential Preview mode
* ``NsLimit``
* target surface selection using ``TargSurf``/``TargSurfRest``
* ``energy_probability`` for probabilistic coating branch splitting
* ``Beam Splitter`` rows that persist splitter settings, spawn deterministic
  reflected/transmitted child paths, and write coating tables as a fallback
* file-backed optical STL solids through native ``Solid_3d_stl`` rows; closed
  STL solids use the row material for non-sequential entry/exit regardless of
  the tilted mesh side selected by the hit chooser
* Non-Sequential Scene Graph inspection and CSV export
* Trace Path inspection and CSV export

Branches are produced by KrakenOS during ``NsTrace``/``NsTraceLoop``. They are
not hand-authored nodes; the UI shows them as trace diagnostics after the ray
trace. Deterministic beam-splitter mode records branch identity, parent
identity, power, phase metadata, and branch labels in ``raykeeper``.

Scene source records
--------------------

The UI maps the current Source panel to a first-class ``SceneSource3D`` record.
Saved layouts can also declare multiple physical emitters with
``SETTINGS["scene_sources"]``. Each entry uses the same source shape as the
panel-backed source, for example:

.. code-block:: python

   SETTINGS = {
       "scene_sources": [
           {
               "source_id": "source:left",
               "name": "Left illuminator",
               "model": "Collimated disk source",
               "origin": [0.0, -10.0, 0.0],
               "direction": [0.0, 0.124, 0.992],
               "radius": 1.2,
               "ray_count": 5,
               "power": 0.6,
           },
           {
               "source_id": "source:right",
               "name": "Right illuminator",
               "model": "Collimated disk source",
               "origin": [0.0, 10.0, 0.0],
               "direction": [0.0, -0.124, 0.992],
               "radius": 1.2,
               "ray_count": 5,
               "power": 0.4,
           },
       ],
   }

The source record is carried by ``SceneBundle.sources`` and exposed in the
Non-Sequential Scene Graph. Physical source modes such as ``Collimated disk
source`` and ``Gaussian beam`` are marked as illumination sources. The legacy
``Pupil / field source`` mode is marked as a ``pupil_field_reference`` because
it is not a physical emitter independent of the Object row.

The editable table still stores KrakenOS optical surfaces. A future visible
``Illumination Source`` table entry should be a scene row backed by
``SceneSource3D``, not a KrakenOS ``surf`` row. That distinction keeps source
authoring from shifting detector/path surface indices.

``SceneBundle.scene_row_mapping`` carries the bridge for that future table. It
maps scene rows to current table rows and KrakenOS trace surfaces. For a reset
scene with one physical source, the future scene-row order is:

.. list-table::
   :header-rows: 1

   * - Scene row
     - Kind
     - Trace surface
   * - ``0`` / ``S0 Object``
     - Surface
     - ``0``
   * - ``1`` / ``Src1 Source 1``
     - Illumination source
     - None
   * - ``2`` / ``S1 Image``
     - Surface
     - ``1``

This lets the UI later show ``Object`` + ``Illumination Source`` + ``Image``
without changing the trace indices consumed by raykeeper, detector paths, and
analysis tools.

Each traced ray also carries source identity metadata:

* ``SOURCE_ID``: stable source key such as ``source:0`` or ``source:left``
* ``SOURCE_NAME``: user-facing source name such as ``Source 1`` or
  ``Left illuminator``
* ``SOURCE_ROLE``: ``illumination`` or ``pupil_field_reference``
* ``SOURCE_MODEL``, ``SOURCE_XYZ``, ``SOURCE_LMN``, ``SOURCE_POWER``,
  ``SOURCE_WEIGHT``, and ``SOURCE_WAVELENGTH``: launch model and launch state

Validate this plumbing with:

.. code-block:: bash

   python -m KrakenOS.UI.validate_scene_sources
   python -m KrakenOS.UI.validate_multi_scene_sources
   python -m KrakenOS.UI.validate_scene_row_mapping
   python -m KrakenOS.UI.validate_scene_source_row_contract

Optical STL prism check
-----------------------

For a prism STL rotated into the classic dispersion pose, the first STL hit
should not report ``n=1 -> 1``.  A BK7 prism entry should report approximately
``n=1 -> 1.518`` at ``0.55 um`` and the outgoing direction should bend toward
the prism base.  Run the regression check with:

.. code-block:: bash

   python -m KrakenOS.UI.validate_stl_prism_media

Raykeeper data
--------------

The manual lists the raykeeper arrays as the persistent version of ``system``
ray state. The UI Ray Inspector exposes the same categories:

.. list-table::
   :header-rows: 1

   * - Category
     - Manual arrays
     - UI data product
   * - Surface path
     - ``SURFACE``, ``NAME``, ``GLASS``
     - Ray Inspector hit table and CSV.
   * - Coordinates
     - ``XYZ``, ``S_XYZ``, ``T_XYZ``, ``OST_XYZ``
     - Ray Inspector XYZ columns and 2D/3D ray picking.
   * - Direction cosines
     - ``S_LMN``, ``LMN``, ``R_LMN``
     - Ray Inspector incoming/outgoing direction columns.
   * - Optical path
     - ``DISTANCE``, ``OP``, ``TOP``, ``TOP_S``
     - Ray Inspector distance/OP totals and CSV.
   * - Index and material
     - ``N0``, ``N1``, ``ALPHA``, ``BULK_TRANS``
     - Ray Inspector refractive index and transmission fields.
   * - Gratings
     - ``G_LMN``, ``ORDER``, ``GRATING_D``
     - Grating rows plus inspector output.
   * - Polarization
     - ``RP``, ``RS``, ``TP``, ``TS``, ``TTBE``, ``TT``
     - Ray Inspector and coating/polarization report.
   * - Source identity
     - ``SOURCE_ID``, ``SOURCE_NAME``, ``SOURCE_ROLE``, ``SOURCE_MODEL``,
       ``SOURCE_XYZ``, ``SOURCE_LMN``, ``SOURCE_POWER``, ``SOURCE_WEIGHT``,
       ``SOURCE_WAVELENGTH``
     - Scene source records, Ray Inspector source columns, and branch analysis.

Multicore and batch tracing
---------------------------

The manual appendix includes a multicore example. The current UI uses batch
tracing where safe, scalar tracing where required by custom surface behavior,
and background workers for heavier analyses and optimization.
