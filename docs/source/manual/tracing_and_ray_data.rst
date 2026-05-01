Tracing And Ray Data
====================

Sequential tracing
------------------

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

* explicit Non-Sequential Preview mode
* ``NsLimit``
* target surface selection using ``TargSurf``/``TargSurfRest``
* ``energy_probability`` for probabilistic coating branch splitting
* Non-Sequential Scene Graph inspection and CSV export
* Branch Tree inspection and CSV export

Branches are produced by KrakenOS during ``NsTrace``/``NsTraceLoop``. They are
not hand-authored nodes; the UI shows them as trace diagnostics after the ray
trace.

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

Multicore and batch tracing
---------------------------

The manual appendix includes a multicore example. The current UI uses batch
tracing where safe, scalar tracing where required by custom surface behavior,
and background workers for heavier analyses and optimization.
