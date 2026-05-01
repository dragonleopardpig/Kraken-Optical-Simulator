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
   * - ``Solid_3d_stl``
     - STL-backed optical solid.
     - ``Shape...`` path staging and Non-Sequential Scene Graph.
   * - ``Coating``, ``CoatingMet``
     - Dielectric and metal coating data.
     - Coating/material workflow and polarization reports.

System methods and state
------------------------

The manual identifies ``system.Trace()`` for sequential tracing and
``system.NsTrace()`` for non-sequential tracing. The UI now exposes both modes
through the trace-mode selector. Phase 5 adds ``NsLimit``, target-surface
selection, probabilistic coating splitting via ``energy_probability``, and
non-sequential scene/branch diagnostics.

The manual also describes system ray arrays such as ``SURFACE``, ``NAME``,
``GLASS``, ``XYZ``, ``S_XYZ``, ``T_XYZ``, ``OST_XYZ``, ``DISTANCE``, ``OP``,
``TOP``, ``TOP_S``, ``ALPHA``, ``BULK_TRANS``, ``S_LMN``, ``LMN``, ``R_LMN``,
``N0``, ``N1``, ``WAV``, ``G_LMN``, ``ORDER``, ``GRATING_D``, ``RP``, ``RS``,
``TP``, ``TS``, ``TTBE``, and ``TT``. These are collected through
``raykeeper`` and surfaced in the UI through the Ray Inspector, Branch Tree
Inspector, and CSV exports.

Glass catalogs
--------------

The manual describes ``Setup`` as the configuration object that loads glass
catalogs from ``KrakenOS/Cat``. The current UI exposes this through:

* File -> Glass Catalog Browser
* row material editing
* stock lens import
* enhanced Zemax text import with embedded ``n/V`` fallback glasses
