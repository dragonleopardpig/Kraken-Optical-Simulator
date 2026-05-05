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

For the F-theta validation screenshots from ``testing/F-theta.pdf`` and
``testing/swappy*.png``, use ``Layouts -> Analysis / Diagnostics -> F-Theta
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

Image-quality maps
------------------

The original manual focuses on spot diagrams and wavefront examples. The UI now
adds Phase 3 map workflows:

* wide-field spot RMS map
* wide-field PSF image map
* wide-field illumination map
* wide-field wavefront map
* field curvature and distortion plots
