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
     - Non-Sequential Preview, Scene Graph, Ray Inspector, Trace Path Inspector.
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
     - ``Beam Splitter`` front face, BK7 substrate thickness, rear AIR face, detector path-placement helpers, ``Element`` path metadata, deterministic transmitted/reflected paths, scene/path diagnostics.
   * - Beam Splitter Coating Table Example
     - Deterministic branch powers from coating-table interpolation.
     - ``KrakenOS/Examples/Examp_Beam_Splitter_Coating_Table.py`` uses ``split_mode = "Deterministic coating table"`` and verifies angle/wavelength coating data drives reflected/transmitted child powers.
   * - Beam Splitter Fresnel Polarization Example
     - Deterministic branch powers from KrakenOS core P/S Fresnel coefficients.
     - ``KrakenOS/Examples/Examp_Beam_Splitter_Fresnel_Polarization.py`` uses ``split_mode = "Deterministic Fresnel P/S"`` and compares pure P, equal P/S, pure S, and reflected S-retardance cases plus ``BRANCH_JONES_P``/``BRANCH_JONES_S`` and ``BRANCH_POLARIZATION_XYZ`` on a finite BK7 splitter.
   * - Beam Splitter Two Path Doublets
     - Transmitted and reflected splitter paths, each with one doublet.
     - One canonical non-sequential surface table with transmit/reflect ``Element`` metadata, path labels, and per-path detectors.
   * - Right-Angle Beam-Splitter Illumination
     - Physical illumination source at 90 degrees to the object/reference axis.
     - ``Layouts -> Beam Splitters / Folds -> Right-Angle Beam-Splitter Illumination`` plus ``KrakenOS/Examples/Examp_Right_Angle_Beam_Splitter_Illumination.py``. Source 1 launches from ``(0, -80, 45) mm`` along ``+Y``; the splitter reflects illumination to a left-side specular object proxy on ``-Z``, then the object-return transmitted branch passes through a clear aperture to the right-side camera/Image row while the Object row remains reference geometry. The layout declares ``scene_row_order="before_object"`` for the future source-visible table.
   * - Zemax LED Beam-Splitter Imaging
     - Vendor Zemax LED rayfile source, top-port illumination, splitter/object return, imaging lens, and Image plane.
     - ``Layouts -> Beam Splitters / Folds -> Zemax LED Beam-Splitter Imaging`` plus ``KrakenOS/Examples/Examp_Zemax_LED_Beam_Splitter_Imaging.py``. The OSRAM ``.DAT`` source launches from ``(0, 45, 45) mm`` along ``-Y``; the Object row is reference only. The useful branch reflects from the 45 degree splitter to the left-side specular object proxy, returns to the splitter, transmits through a simple BK7 imaging lens, and reaches Image. This is the first vendor-rayfile source/object split fixture; diffuse object BRDF/scattering remains future work.
   * - Multi-Source Illumination Example
     - Two independent layout-defined physical illumination sources.
     - ``Layouts -> Sources / Illumination -> Multi-Source Illumination Example`` plus ``KrakenOS/Examples/Examp_Multi_Source_Illumination.py``. The layout declares ``SETTINGS["scene_sources"]`` with ``source:left`` and ``source:right``; both trace to a shared detector while preserving per-ray ``SOURCE_ID`` metadata.
   * - Galvo F-Theta Laser Scanner
     - Folded laser source path, beam expander, 45 degree scan mirror, F-theta lens, and scan plane.
     - ``Common Optical Layout -> Galvo F-Theta Laser Scanner`` plus
       ``KrakenOS/Examples/Examp_Galvo_FTheta_Laser_Scanner.py``. The scanner
       uses the 50 mm Figure 8 F-theta prescription extracted from
       ``attachment/F-theta.pdf``; ``K9`` is mapped to CDGM ``H-K9L``. Type
       ``-50,-45,-40`` in the mirror ``TiltX`` cell to overlay a conservative
       ``-10,0,+10`` degree optical scan; ``-55,-45,-35`` is the lens' nominal
       full ``-20,0,+20`` degree optical scan. Full folded Gaussian
       q/astigmatic propagation remains post-Phase-6 work.
   * - F-Theta Lens 50mm Figure 8
     - Standalone 0.65 um, 50 mm F-theta lens from ``attachment/F-theta.pdf`` Figure 8.
     - Includes the Zemax stop spacing, four refractive elements, and final scan plane.
   * - F-Theta Lens 50mm Wavefront 0 Deg
     - Pure sequential Wavefront Function validation for the Figure 8 F-theta lens at ``0.00 DEG`` field.
     - Use this layout when comparing against the on-axis Zemax screenshot in ``attachment/swappy*.png``. It intentionally excludes the Galvo scanner, beam expander, and folded mirror.
   * - Zemax Wavefront Map Import
     - External Zemax Wavefront Map text export validation.
     - ``File -> Import Zemax Wavefront Map...`` loads a Zemax text export as a numerical reference for ``WFront``. ``KrakenOS/Examples/Examp_Zemax_Wavefront_Map_Import.py`` demonstrates standalone loading and normalized-pupil sampling; ``python -m KrakenOS.UI.validate_zemax_wavefront_import`` validates parsing and residual comparison.
   * - Attachment Zemax Prescriptions
     - Recursive text ``.zmx`` prescription import examples.
     - ``Examples -> Zemax Prescriptions (attachment)`` lists text prescriptions found under ``attachment/zemax`` grouped by subfolder and loads them with the same converter as ``File -> Import Zemax File...``. ``python -m KrakenOS.UI.validate_testing_zemax_examples`` validates the scan and parser coverage.
   * - Michelson Interferometer (Interferogram)
     - Source/object split, return paths, detector path, second splitter encounter, and detector interferogram.
     - Independent physical source direction, Edmund Optics 68551 25 mm cube-beam-splitter primitive, internal 45 degree deterministic splitter, two return mirrors, four recombination-path branch records, ``Interf`` analysis, and ``KrakenOS/Examples/Examp_Michelson_Interferometer.py``.
   * - Twyman-Green Interferometer (Interferogram)
     - Test/reference return paths and detector-port interferogram.
     - Common layout preset plus ``KrakenOS/Examples/Examp_Twyman_Green_Interferometer.py``; uses the tested deterministic return-path recombination workflow with Twyman-Green test optic/reference flat naming.
   * - Mach-Zehnder Interferometer (Interferogram)
     - Two splitters, two fold mirrors, cross/return output detector ports, and path-average interferogram.
     - Common layout preset plus ``KrakenOS/Examples/Examp_Mach_Zehnder_Interferometer.py``; both paths reach the second splitter, the editable table exposes physical ``Path 1`` through ``Path 5`` assignment, and the trace path inspector records transmit-reflect, reflect-transmit, transmit-transmit, and reflect-reflect histories for the current analytic interferogram diagnostic.
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
     - Wavefront Function, phase maps, and Zernike fitting.
     - Wavefront/Zernike reports and CSV exports.
   * - Tel 2M STL ImageSlicer
     - STL-backed non-sequential assembly.
     - ``Solid_3d_stl`` staging, scene graph inspection, non-sequential tracing.
   * - Phase 6 Optical STL Prism
     - Arbitrary closed STL optical solid with material-driven refraction.
     - ``File -> Import Optical CAD/STL Solid...``, 3D inspector CAD/STL placement, and ``KrakenOS/Examples/Examp_Phase6_Optical_STL_Prism.py`` show the same native ``Solid_3d_stl`` workflow with ``NsTrace`` rays. STEP/IGES vendor CAD is meshed to cached STL first.
   * - Phase 6 Path Component Placement
     - Path-local component insertion from a beam splitter.
     - ``KrakenOS/Examples/Examp_Phase6_Path_Component_Placement.py`` demonstrates the same helper used by ``Add component to transmitted/reflected path...`` and prints native row Tilt/Decenter plus ``Element`` metadata for detector, aperture, thin lens, refractive surface, mirror rows, and a rigid stock-catalog lens block placed on a path.
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
