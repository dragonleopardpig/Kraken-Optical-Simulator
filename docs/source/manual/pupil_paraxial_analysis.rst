Pupil, Paraxial, And Analysis Tools
===================================

Paraxial tool
-------------

The provisional manual describes ``system.Parax(wavelength)`` returning system
matrix and paraxial quantities such as EFFL, principal plane positions, and
surface matrices.

Current UI coverage:

* Help -> Paraxial Calculator
* Actions -> Paraxial Matrix Report
* Actions -> Gaussian Beam Report, using the same ABCD chain for q propagation
* CSV export for the paraxial matrix chain
* native optimization variables that can use paraxial and image-quality metrics

PupilCalc
---------

The manual describes ``Kos.PupilCalc(system, surface, wavelength, aperture_type,
aperture_value)`` as the ray generator for entrance-pupil-aware field sampling.
Important manual fields include:

.. list-table::
   :header-rows: 1

   * - PupilCalc field
     - Meaning
     - UI exposure
   * - ``Samp``
     - Sampling count.
     - Ray count.
   * - ``Ptype``
     - Pupil pattern such as fan, square, hexapolar, random disk, chief ray, or r/theta.
     - Source/Pupil controls.
   * - ``FieldType``
     - Angle or object-height field.
     - Field type selector.
   * - ``FieldX``, ``FieldY``
     - Field coordinates.
     - Field value/count grid controls.
   * - ``AperType``, ``AperVal``
     - Aperture definition.
     - Aperture type/value controls.

Atmospheric refraction
----------------------

The manual's atmospheric refraction section uses PupilCalc with wavelength,
temperature, pressure, humidity, CO2, zenith angle, latitude, and altitude
settings. The UI exposes this in Phase 3:

* atmospheric refraction/dispersion plot
* current-optics atmospheric image residual plot
* observatory and atmosphere parameter controls
* common-layout atmospheric examples

Wavefront and aberration tools
------------------------------

The manual appendix demonstrates Seidel sums and wavefront fitting. Current UI
coverage includes:

* Seidel analysis
* wavefront phase, Zemax-style Wavefront Function 3D wireframe OPD surface,
  wrapped phase, interferogram, and slope plots
* Zernike fitting report
* wavefront and Zernike CSV exports
* wide-field wavefront RMS maps

To reproduce the Zemax-like single-field Wavefront Function view, choose
``WFront`` in the analysis toolbar and click ``Update``. ``Wavefront Function``
is the default WFront style; ``Phase (unwrapped)``, wrapped phase,
interferogram, and slope maps remain selectable in the ``Wavefront style``
dropdown. The function plot removes the best-fit piston/tilt reference plane
and draws the wavefront OPD as a Zemax-style waterfall surface over the
normalized pupil, without 3D axes, and with a bottom report strip containing
P-V/RMS in waves. Use ``Layouts -> Analysis / Diagnostics -> Wavefront Function
Example`` for a ready-made layout.

.. figure:: ../_static/manual/ui/analysis_toolbar.png
   :alt: Analysis toolbar showing WFront and other analysis buttons
   :width: 100%

   The analysis toolbar sits above the 2D plot. Select ``WFront`` and then
   click ``Update`` to regenerate the selected analysis view.

For the F-theta validation screenshots from ``attachment/F-theta.pdf`` and
``attachment/swappy*.png``, use ``Layouts -> Analysis / Diagnostics -> F-Theta
Lens 50mm Wavefront 0 Deg`` for the pure sequential on-axis comparison. It
corresponds to the Zemax ``AT 0.00 DEG`` Wavefront Function screenshot and
intentionally excludes the Galvo scanner, beam expander, and fold mirror.

Do not compare those screenshots directly against ``Galvo F-Theta Laser
Scanner``. The Galvo layout is a folded laser workflow with source, beam
expander, mirror scan overlay, and pattern-coordinate fallback for collapsed
KrakenOS phase pupil coordinates; it is not the same sequential field
definition used by the Zemax Wavefront Function printouts.

The Zemax ``AT 20.00 DEG`` edge-field Wavefront Function remains a tracked core
limitation. KrakenOS ``Phase()`` currently fails before returning OPD samples
for this F-theta prescription at nonzero field, so the UI does not publish a
broken 20 degree Wavefront Function preset.

Zemax Wavefront Map comparison
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For direct numerical comparison against Zemax, export a Zemax Wavefront Map as
text and load it with ``File -> Import Zemax Wavefront Map...``. The import is a
reference overlay, not a prescription import. After loading the text file,
choose ``WFront`` and click ``Update``. The UI samples the imported Zemax grid
on the current KrakenOS normalized pupil, removes the same best-fit
piston/tilt reference plane from both datasets, and reports the residual RMS
and P-V in waves and nanometers.

The comparison tries the common export-orientation variants automatically:
exported orientation, X flip, Y flip, X/Y flip, and transpose. The selected
orientation appears in the results table. If the Zemax wavelength and the UI
wavelength differ, the results table keeps the comparison but reports the
wavelength mismatch.

Use the feature this way:

1. In Zemax/OpticStudio, run ``Wavefront Map`` for the same field, wavelength,
   stop, and pupil sampling you want to validate.
2. Save the Wavefront Map as a text export. Values in waves and values in
   nanometers are supported when the header states the grid units.
3. In KrakenOS, load the same optical layout, then use ``File -> Import Zemax
   Wavefront Map...``.
4. Select ``WFront`` and click ``Update``.
5. Optional: use ``Actions -> Export Wavefront CSV...``. The CSV includes
   ``zemax_reference_waves``, ``zemax_residual_waves``, and
   ``zemax_reference_file`` columns for downstream checks.

The parser and comparison helper can also be used from Python:
``KrakenOS/Examples/Examp_Zemax_Wavefront_Map_Import.py`` loads a text export
or creates a synthetic export when no path is supplied. The regression fixture
``python -m KrakenOS.UI.validate_zemax_wavefront_import`` validates UTF-16
Zemax-like parsing, wavelength headers written in nanometers, reference-grid
sampling, orientation selection, and residual calculation.

Local reference-tool audit:

* ``STOP-utils`` is directly useful for this feature because its Wavefront Map
  text-export parsing shows the same practical Zemax row-orientation issue.
  KrakenOS keeps a small internal parser instead of adding STOP-utils as a
  runtime dependency.
* ``PyZDDE`` is useful only as an external Windows/Zemax validation bridge.
  It is not suitable as a UI runtime dependency because it requires a live
  Zemax DDE connection.
* ``poppy`` is useful later for physical-optics propagation, PSF, and Fresnel
  experiments once KrakenOS provides a valid OPD/amplitude grid. It does not
  replace the current KrakenOS ``Phase()``-based Wavefront Function.

Image-quality maps
------------------

The original manual focuses on spot diagrams and wavefront examples. The UI now
adds Phase 3 map workflows:

* wide-field spot RMS map
* wide-field PSF image map
* wide-field illumination map
* wide-field wavefront map
* field curvature and distortion plots
