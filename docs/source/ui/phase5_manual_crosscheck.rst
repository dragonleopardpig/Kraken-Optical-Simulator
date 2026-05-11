Phase 5 Manual Cross-Check
==========================

This page cross-checks the provisional manual against the Phase 5 UI coverage
audit. The manual does not reveal an unexposed high-value KrakenOS core feature
for Phase 1 through Phase 5. Remaining items are future refinements, not missing
core exposure.

Current status
--------------

As of the Phase 8D service-extraction work, this cross-check remains closed for
Phase 5. Later Phase 6 through Phase 8 work extends the UI beyond the manual
baseline with non-sequential scene/source workflows, deterministic beam-splitter
branches, coherent detector accumulation, diffraction detector FFTs, branch-local
Gaussian ``q`` diagnostics, and ``BField`` branch-field propagation. Those later
features are not evidence of missed Phase 5 manual coverage; they are deliberate
post-Phase-5 expansion layers.

For presentation and release checks, ``python -m KrakenOS.UI.validate_menu_smoke``
now verifies that UI-loadable menu Layouts, Machine Vision layouts, and Examples
load into table rows and render in both 2-D and offscreen 3-D. Script-only
examples remain part of the repository/manual inventory, but they are excluded
from the UI menu by design. Examples that write files during import are also
kept out of the UI menu so presentation smoke checks do not mutate fixtures.

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
* Continue higher-order branch-field/physical-optics propagation for thick
  tilted splitter plates and arbitrary prism/CAD assemblies. Detector-bin
  coherent accumulation, Gaussian ``q`` diagnostics, Gaussian detector
  recombination, and first scalar ``BField`` propagation are already implemented
  after Phase 5.

Roadmap status
--------------

``KRAKEN_UI_CORE_COVERAGE.md`` and ``KRAKEN_UI_FUTURE_ROADMAP.md`` now mark the
Phase 1 through Phase 5 scopes complete. ``Partial`` may still appear in status
legends or in explicitly post-Phase-6 research items, but there are no hidden
Phase 1-5 blockers in this cross-check. New Phase 8D service modules
(``branch_gaussian_q_report``, ``branch_throughput_analysis``,
``coherent_detector_analysis``, ``branch_field_analysis``,
``detector_path_analysis``, ``source_illumination_analysis`` including
source-illumination record/sample assembly, and ``scene_source_analysis`` for
source-spec normalization/source-object/summary helpers, and
``optical_solid_metadata`` for CAD/STL face-role metadata and virtual splitter
plane helpers, world transforms, face-fit/snap-to-ray placement helpers, and
hit-sequence classification, plus ``stl_geometry`` for STL diagnostics and
transformed-bounds helpers, and ``cad_import_service`` for CAD cache/conversion
plumbing) are
UI-architecture hardening for later analysis features, not newly discovered
Phase 5 manual gaps.
The display smoke validator is a Phase 8D presentation guardrail over the same
menu-backed coverage; it does not reopen the completed Phase 5 manual audit.
