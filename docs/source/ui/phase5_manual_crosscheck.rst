Phase 5 Manual Cross-Check
==========================

This page cross-checks the provisional manual against the Phase 5 UI coverage
audit. The manual does not reveal an unexposed high-value KrakenOS core feature
for Phase 1 through Phase 5. Remaining items are future refinements, not missing
core exposure.

Manual topic coverage
---------------------

.. list-table::
   :header-rows: 1

   * - Manual topic
     - Manual feature
     - Phase 5 status
   * - Surface geometry
     - ``Rc``, ``k``, axicon, cylindrical ratio, asphere, Zernike, shifts.
     - Covered by table fields, Advanced Surface, and Shape Builder.
   * - Transforms
     - decenter, tilt, transform order, axis move.
     - Covered by table fields, element grouping, folded preview, and exact tracing.
   * - Masks and UDA
     - ``Mask_Type``, ``Mask_Shape``, spider/obstruction examples.
     - Covered by Shape Builder and Advanced Surface.
   * - Custom surfaces
     - ``ExtraData`` callable plus coefficients.
     - Covered for safe preset authoring; arbitrary Python remains import/preserve only by design.
   * - Error maps
     - ``Error_map = [X, Y, Z, SPACE]``.
     - Covered by the measured error-map workflow.
   * - STL solids
     - ``Solid_3d_stl`` examples.
     - Covered by Shape Builder path staging and Non-Sequential Scene Graph inspection.
   * - Glass catalogs
     - ``Setup`` and catalog-backed material lookup.
     - Covered by Glass Catalog Browser, stock lens import, and enhanced Zemax import.
   * - Sequential tracing
     - ``system.Trace``.
     - Covered by standard preview and analysis workflows.
   * - Non-sequential tracing
     - ``system.NsTrace`` and STL/non-sequential examples.
     - Covered by Non-Sequential Preview, ``NsLimit``, target surface, energy probability, Scene Graph, Ray Inspector, and Trace Path Inspector.
   * - Ray arrays
     - ``SURFACE``, ``XYZ``, ``LMN``, ``OP``, ``N0/N1``, polarization arrays.
     - Covered by Ray Inspector, branch/hit tables, 2D/3D ray picking, and CSV export.
   * - Paraxial tool
     - ``system.Parax``.
     - Covered by Paraxial Calculator and Paraxial Matrix Report.
   * - PupilCalc
     - pupil sampling, field type, aperture controls.
     - Covered by Source/Pupil controls including chief and r/theta sampling.
   * - Atmospheric refraction
     - PupilCalc atmosphere parameters.
     - Covered by atmospheric dispersion and current-optics residual plots.
   * - Viewers
     - 2D/3D display and STL visualization.
     - Covered by 2D, embedded 3D, legacy 3D, scene bundles, and ray toggles.
   * - SourceRnd
     - source distribution function.
     - Covered by random circle/square/line/point-cone source controls and angular weighting presets.

Manual-driven follow-ups
------------------------

These are useful future refinements, but they are not Phase 5 blockers:

* Add more turnkey STL/image-slicer scene examples if users work heavily with
  telescope slicers.
* Add grating-order analysis plots if diffraction-grating workflows become more
  central.
* Add weighted PSF/MTF accumulation for nonuniform ``SourceRnd.fun`` sources.
* Add specialized ADC authoring if grouped prism/table editing is not adequate.
* Add coherent Gaussian ``q`` propagation and interference accumulation on top
  of the deterministic beam-splitter branches before Michelson/interferometer
  analysis.

Roadmap status
--------------

``KRAKEN_UI_CORE_COVERAGE.md`` and ``KRAKEN_UI_FUTURE_ROADMAP.md`` now mark the
Phase 1 through Phase 5 scopes complete. Any remaining ``Partial`` rows are
post-Phase future features such as coherent branch recombination, not hidden
Phase 1-5 blockers.
