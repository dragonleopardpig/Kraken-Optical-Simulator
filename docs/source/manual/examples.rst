Manual Example Inventory
========================

The appendix of the provisional manual demonstrates the breadth of KrakenOS.
The table below maps the manual examples to current UI or repository coverage.

.. list-table::
   :header-rows: 1

   * - Manual example
     - Core feature
     - Current coverage
   * - Ray
     - Direct ``Trace`` with a single ray.
     - Sequential preview and Ray Inspector.
   * - Perfect Lens
     - Ideal lens behavior.
     - Thin Lens row and paraxial analysis.
   * - Doublet Lens 3D Color
     - Multi-surface refractive system and 3D display.
     - Common doublet layouts and embedded/legacy 3D viewers.
   * - Doublet Lens Tilt
     - Tilted surfaces and exact 3D transforms.
     - Table tilt/decenter columns and folded/non-sequential previews.
   * - Doublet Lens Paraxial Calculations
     - ``Parax`` and matrix outputs.
     - Paraxial Calculator, Paraxial Matrix Report, and Gaussian Beam Report.
   * - Doublet Lens Tilt Nulls
     - Null transformations and off-axis testing.
     - Transform columns and trace-mode controls.
   * - Doublet Lens NonSec
     - ``NsTrace``.
     - Non-Sequential Preview, Scene Graph, Ray Inspector, Branch Tree Inspector.
   * - Doublet Lens Zernike
     - ``ZNK`` surface deformation.
     - Shape Builder and wavefront/Zernike analysis.
   * - Doublet Lens Tilt NonSec
     - Tilted non-sequential tracing.
     - Non-sequential trace controls and diagnostics examples.
   * - Doublet Lens Pupil
     - ``PupilCalc``.
     - Source/Pupil panel.
   * - Doublet Lens Commands System
     - System/ray arrays.
     - Ray Inspector and CSV export.
   * - Doublet Lens Pupil Seidel
     - Seidel sums.
     - Seidel analysis mode.
   * - Doublet Lens Cylinder
     - Cylindrical/toroidal surfaces.
     - Advanced Surface ``Cylinder_Rxy_Ratio``.
   * - Axicon
     - Axicon surface.
     - Table/Advanced Surface axicon field.
   * - Axicon And Cylinder
     - Combined non-spherical geometry.
     - Table and Shape Builder workflows.
   * - Flat Mirror 45 Deg
     - Mirror, fold, and ``AxisMove``.
     - Mirror rows, folded preview, non-sequential preview.
   * - Beam Splitter 50/50 Example
     - Deterministic finite-plate beam splitter.
     - ``Beam Splitter`` front face, BK7 substrate thickness, rear AIR face, detector arm-placement helpers, ``Element`` arm metadata, deterministic transmitted/reflected branches, scene/branch diagnostics.
   * - Beam Splitter Two Arm Doublets
     - Transmitted and reflected splitter arms, each with one doublet.
     - One canonical non-sequential surface table with transmit/reflect ``Element`` metadata, arm labels, and per-arm detectors.
   * - Michelson Interferometer (Interferogram)
     - Source/object split, return arms, detector arm, second splitter encounter, and detector interferogram.
     - Independent physical source direction, 45 degree deterministic splitter, two return mirrors, four recombination-path branch records, ``Interf`` analysis, and ``KrakenOS/Examples/Examp_Michelson_Interferometer.py``.
   * - Parabole Mirror Shift
     - Off-axis conic via shift.
     - ``k`` plus ``ShiftX``/``ShiftY`` in Advanced Surface.
   * - Diffraction Grating Transmission
     - Transmission grating.
     - Grating row plus Additional Settings.
   * - Diffraction Grating Reflection
     - Reflection grating.
     - Grating row plus Additional Settings.
   * - Tel 2M Spyder Spot Diagram
     - Mask/obstruction and spot diagram.
     - Shape Builder mask presets and spot analysis.
   * - Tel 2M Spyder Spot Tilt M2
     - Tilted telescope mirrors and masks.
     - Element grouping, transform columns, spot analysis.
   * - Tel 2M Pupila
     - Telescope pupil generation.
     - Source/Pupil panel and pupil analysis.
   * - Tel 2M Error Map
     - Measured surface error map.
     - Error Map import/clear/validate workflow.
   * - Tel 2M Wavefront Fitting
     - Wavefront and Zernike fitting.
     - Wavefront/Zernike reports and CSV exports.
   * - Tel 2M STL ImageSlicer
     - STL-backed non-sequential assembly.
     - ``Solid_3d_stl`` staging, scene graph inspection, non-sequential tracing.
   * - Tel 2M Atmospheric Refraction Corrector
     - Atmospheric refraction and correction.
     - Atmospheric dispersion/residual analysis.
   * - Extra Shape Micro Lens Array
     - Custom ``ExtraData`` sag.
     - Shape Builder safe custom-sag presets.
   * - Extra Shape Radial Sine
     - Custom radial surface.
     - Shape Builder radial sine preset.
   * - Extra Shape XY Cosines
     - Custom x/y cosine surface.
     - Shape Builder x/y cosine preset.
   * - Multicore
     - Parallel tracing.
     - Batch tracing and background analysis workers.
   * - Solid Objects STL Array
     - Multiple STL solids.
     - STL path staging and non-sequential diagnostics.
   * - Source Distribution Function
     - ``SourceRnd.fun`` angular weighting.
     - SourceRnd angular weight presets and source statistics.
   * - Beam Splitter 50/50
     - Direct API deterministic finite-plate splitter.
     - ``KrakenOS/Examples/Examp_Beam_Splitter_50_50.py`` and the UI common layout.
