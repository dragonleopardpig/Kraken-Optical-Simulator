Core Model: Surfaces And Systems
================================

The manual describes KrakenOS as two primary object types:

``surf``
   One optical interface or object. It stores geometry, aperture, material,
   coating, drawing, and transform state.

``system``
   An ordered list of ``surf`` objects plus the methods that trace rays and
   expose ray state.

Surface attributes
------------------

The provisional manual highlights these core ``surf`` fields. The current
layout editor exposes the scalar fields directly in the table and the remaining
fields through Advanced Surface, Shape Builder, grating additional settings,
catalog import, or element grouping.

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
     - Current UI exposure
   * - ``Name``, ``Note``
     - Human labels and per-surface comments.
     - Table name plus Advanced Surface notes.
   * - ``Rc``, ``k``, ``AspherData``, ``ZNK``
     - Spherical, conic, aspheric, and Zernike surface shape.
     - Table ``Rc``/``k`` plus ``Shape...`` and Advanced Surface.
   * - ``Cylinder_Rxy_Ratio``, ``Axicon``
     - Cylindrical/toroidal ratio and axicon angle.
     - Table/Advanced Surface.
   * - ``Thickness``, ``Diameter``, ``InDiameter``
     - Axial spacing and clear/inner apertures.
     - Table/Advanced Surface.
   * - ``DespX``, ``DespY``, ``DespZ``
     - Decenter in the surface coordinate system.
     - Table.
   * - ``TiltX``, ``TiltY``, ``TiltZ``
     - Surface rotations.
     - Table.
   * - ``Order``, ``AxisMove``
     - Transformation order and optical-axis propagation.
     - Table/Advanced Surface.
   * - ``Diff_Ord``, ``Grating_D``, ``Grating_Angle``
     - Diffraction grating order, period, and orientation.
     - Row right-click Additional Settings for grating rows.
   * - ``ShiftX``, ``ShiftY``
     - Surface-profile offset for off-axis shapes.
     - Advanced Surface.
   * - ``Mask_Type``, ``Mask_Shape``, ``UDA``
     - Aperture masks and user-defined apertures.
     - ``Shape...`` presets and Advanced Surface.
   * - ``ExtraData``
     - User-defined sag function plus coefficients.
     - ``Shape...`` safe presets; arbitrary Python is preserved on import.
   * - ``Error_map``
     - Measured surface error map ``[X, Y, Z, spacing]``.
     - Error Map workflow and Phase 2 reports.
   * - ``Drawing``, ``Color``, ``Nm_Pos``, ``NumLabel``
     - Display behavior, color, and labels.
     - Advanced Surface and display code.
   * - ``DrawingProperties`` UI metadata
     - Fabrication-drawing callouts such as clear aperture, form/power,
       scratch-dig, coating notes, and surface notes. This is UI metadata saved
       in row advanced attributes; it does not change ray physics.
     - ``File -> Lens Drawing Surface Properties...`` and
       ``File -> Export Lens Drawing...`` before PDF generation.
   * - ``Solid_3d_stl``
     - STL-backed optical solid.
     - ``Shape...`` path staging and Non-Sequential Scene Graph.
   * - ``Coating``, ``CoatingMet``
     - Dielectric and metal coating data.
     - Coating/material workflow and polarization reports.
   * - ``BeamSplitter``
     - UI metadata for splitter mode, reflectance, loss, phase, and branch
       limits.
     - ``Beam Splitter`` row plus right-click settings; deterministic
       non-sequential tracing spawns transmitted/reflected child branches, with
       a generated coating table retained as a legacy fallback.
   * - ``Object Target``
     - Semantic UI surface type for a source/object split target.
     - Runtime maps to ``MIRROR`` as a specular proxy for fixtures that still
       need a single return ray.
   * - ``DiffuseScatter``
     - Diffuse/BRDF metadata for ``Diffuse Object`` rows.
     - Built-in Lambertian rows spawn deterministic child branches in
       ``NsTrace``.  ``pySCATMECH`` BRDF/BSDF is the planned optional physics
       backend behind the same metadata.

System methods and state
------------------------

The manual identifies ``system.Trace()`` for sequential tracing and
``system.NsTrace()`` for non-sequential tracing. The UI now exposes both modes
through the trace-mode selector. Phase 5 adds ``NsLimit``, target-surface
selection, probabilistic coating splitting via ``energy_probability``, and
non-sequential scene/trace-path diagnostics. Beam-splitter rows add deterministic
transmit/reflect child branches, and ``Diffuse Object`` rows add deterministic
Lambertian scatter child branches, in ``NsTrace()``/``NsTraceLoop()``.

The manual also describes system ray arrays such as ``SURFACE``, ``NAME``,
``GLASS``, ``XYZ``, ``S_XYZ``, ``T_XYZ``, ``OST_XYZ``, ``DISTANCE``, ``OP``,
``TOP``, ``TOP_S``, ``ALPHA``, ``BULK_TRANS``, ``S_LMN``, ``LMN``, ``R_LMN``,
``N0``, ``N1``, ``WAV``, ``G_LMN``, ``ORDER``, ``GRATING_D``, ``RP``, ``RS``,
``TP``, ``TS``, ``TTBE``, and ``TT``. The UI also adds scene-source and branch
metadata arrays such as ``SOURCE_ID``, ``SOURCE_NAME``, ``SOURCE_ROLE``,
``SOURCE_MODEL``, ``SOURCE_XYZ``, ``SOURCE_LMN``, ``SOURCE_POWER``,
``SOURCE_WEIGHT``, ``SOURCE_WAVELENGTH``, ``BRANCH_ID``, ``BRANCH_PATH``,
``BRANCH_POWER``, and ``BRANCH_PHASE``. These are collected through
``raykeeper`` and surfaced in the UI through the Ray Inspector, Trace Path
Inspector, Non-Sequential Scene Graph, and CSV exports.

Glass catalogs
--------------

The manual describes ``Setup`` as the configuration object that loads glass
catalogs from ``KrakenOS/Cat``. The current UI exposes this through:

* File -> Glass Catalog Browser
* row material editing
* stock lens import
* enhanced Zemax text import with embedded ``n/V`` fallback glasses
