.. _krakenos-map-optical-system-design:

Optical System Design
=====================

This map uses Robert E. Fischer, Biljana Tadic-Galeb, and Paul R. Yoder,
*Optical System Design*, second edition.  Its system-engineering scope is wider
than KrakenOS, but it provides a practical context for specifications,
performance evaluation, Gaussian beams, tolerancing, sensors, polarization,
and stray-light work.

Coverage by chapter
-------------------

.. list-table:: Fischer/Tadic-Galeb/Yoder-to-KrakenOS coverage
   :header-rows: 1
   :widths: 18 14 68

   * - Book section
     - Match
     - KrakenOS implementation
   * - Chs. 1--2, specifications, basic optics, stops, and pupils
     - **Partial/direct**
     - The paraxial report, surface apertures, stop flags, pupils, ray bundles,
       and field sampling support optical specifications, not requirements flow.
   * - Chs. 3--5, diffraction and aberrations
     - **Direct/partial**
     - Exact ray aberrations, OPD, Zernike fitting, Seidel estimates, PSF, and
       MTF cover the optical calculations but not every design rule.
   * - Chs. 6--8, glass, surfaces, design forms, and prisms
     - **Direct/related**
     - Catalog dispersion, conic/polynomial/user surfaces, exact refraction,
       mirrors, prisms, and layout examples are implemented.
   * - Chs. 9--10, optimization and performance
     - **Direct/partial**
     - Bounded merit optimization, ray fans/spots, OPD, wavefront RMS, MTF,
       detector maps, and captured-image metrics are available.
   * - Ch. 11, Gaussian beam imagery
     - **Direct for TEM00**
     - ``GaussianBeam.py`` propagates circular and astigmatic :math:`q`
       parameters, clipping, and cavity modes.
   * - Chs. 12--14, IR/UV, diffractives, and illumination
     - **Partial/related**
     - Wavelength-dependent rays, gratings, field propagation, and illumination
       layouts exist; thermal radiometry and general illumination design do not.
   * - Ch. 15, optical testing
     - **Partial**
     - Simulated/captured PSF and MTF, USAF targets, and wavefront fits are
       present; most interferometer and laboratory reduction procedures are not.
   * - Ch. 16, tolerancing and producibility
     - **Direct/partial**
     - Seeded Monte Carlo, stackups, compensators, correlations, and yield
       reports implement the computational core, not producibility management.
   * - Chs. 17--18, optomechanics and manufacturing
     - **Related/not modelled**
     - CAD solids can participate in traces; structural design and manufacture
       are outside KrakenOS.
   * - Chs. 19--20, polarization and thin films
     - **Partial**
     - S/P Fresnel power, normalized Jones rays, branch transport, and coating
       tables are available; arbitrary Mueller/Jones components and film design
       are absent.
   * - Chs. 22--23, design examples and sensor systems
     - **Partial/related**
     - Merit operands, image simulation, detector geometry, slanted-edge MTF,
       and USAF MTF cover parts of these workflows.
   * - Ch. 24, stray light and scattering
     - **Direct/partial**
     - Non-sequential ghosts, CAD occlusion, TIR, deterministic diffuse/BRDF
       branches, ancestry, and detector power support path analysis.

Aspheric sag: Chapter 7
-----------------------

The rotationally symmetric surface on printed p. 116 is

.. math::

   z(r)=\frac{cr^2}{1+\sqrt{1-(1+k)c^2r^2}}
        +\sum_i a_i r^{2i}.

``conic__surf`` and ``aspheric__surf`` in ``MathShapesClass.py`` evaluate the
two terms directly; ``SurfaceShape`` combines them with Zernike, error-map,
axicon, and user contributions.  KrakenOS' ``AspherData`` begins at
:math:`r^2`, while some optical-design exports begin at :math:`r^4`.  Verify
the coefficient order rather than copying a column blindly.

Performance evaluation: Chapters 3 and 10
------------------------------------------

The book separates geometrical spots and ray fans from wavefront and
diffraction metrics.  KrakenOS does the same:

* Exact image-plane intercepts provide transverse ray error and geometrical
  RMS spots.
* ``PhaseCalc.py`` and ``WavefrontFit.py`` reconstruct and fit OPD.
* ``PSFCalc.py`` forms a diffraction PSF and MTF from a complex pupil.
* ``EdgeMTF.py`` and ``USAFMTF.py`` analyze captured images rather than the
  ideal optical pupil.

Do not compare an RMS spot diameter directly with an Airy diameter or MTF50.
They answer different questions and use different weighting.  The book's
encircled-energy discussion on printed pp. 189--191 is related to integration
of a normalized detector/PSF map within increasing radius; the core module
does not expose one universal encircled-energy API for every analysis path.

Gaussian beams: Chapter 11
--------------------------

For a TEM00 beam with waist radius :math:`w_0`, Chapter 11 uses

.. math::

   I(r,z)=I_0(z)\exp\!\left[-\frac{2r^2}{w^2(z)}\right],\qquad
   z_R=\frac{\pi n w_0^2}{M^2\lambda_0},\qquad
   w(z)=w_0\sqrt{1+(z/z_R)^2}.

``GaussianBeam.py`` stores the equivalent complex parameter and propagates it
with :math:`q_2=(Aq_1+B)/(Cq_1+D)`.  It reports beam radius, curvature,
Rayleigh range, divergence, Gouy phase, clipping, and separate tangential and
sagittal solutions.  ``gaussian_beam_from_diameter_divergence`` is the closest
entry point to the book's diameter/divergence specification.

The implementation is **direct for a paraxial TEM00 model**.  It is not a
physical-optics calculation of arbitrary laser modes, coherence defects,
thermal lensing, damage, or diffraction after severe clipping.

Tolerance analysis: Chapter 16
------------------------------

The book warns that RSS addition can fail when unlike aberrations and
refocusing interact, and recommends Monte Carlo trials for realistic
production prediction.  KrakenOS supports both summaries.  For independent
linearized contributors,

.. math::

   \sigma_P\simeq
   \sqrt{\sum_i\left(\frac{\partial P}{\partial x_i}\sigma_i\right)^2}.

The tolerance service perturbs radius, thickness, index, decentre, tilt, and
other configured variables; rebuilds and retraces the system; applies an
optional compensator; and reports distributions, percentiles, yield, and
ranked sensitivities.  ``docs/source/tutorials/tolerance_monte_carlo.rst``
contains the reproducible UI/API workflow.

Polarization: Chapter 19
------------------------

At an isotropic interface, ``Physics/optics.py`` calculates S/P Fresnel power
and phase.  Non-sequential branch records can carry complex Jones components,
and detector analysis can sum projected fields coherently.  This covers the
interface part of the chapter and supports polarization-sensitive beam
splitters.

The match is **partial**: KrakenOS does not provide a general sequence of Jones
or Mueller matrices for retarders, diattenuators, depolarizers, birefringent
crystals, stress birefringence, or polarization aberration.  A scalar coating
table is not automatically a complex thin-film polarization model.

Stray light: Chapter 24
-----------------------

The book's scatter-path workflow on printed pp. 714--715 maps closely to
``system.NsTrace``: launch representative in-field and out-of-field bundles,
include the mechanical geometry, trace nearest physical hits, and inspect
paths that reach a detector.  Fresnel/coating branches reveal ghosts and TIR;
diffuse-object settings spawn Lambertian, cosine-lobe, Oren--Nayar, or optional
pySCATMECH BRDF children.  Branch paths and depth expose the number and kind
of interactions.

The veiling-glare contrast relation, Eq. (24.4), is

.. math::

   C=\frac{I_{\max}-I_{\min}}{I_{\max}+I_{\min}}.

Adding a uniform stray-light pedestal to both levels lowers this contrast.
KrakenOS can form relative detector maps needed for that experiment, but a
calibrated prediction requires source radiance, BSDF/BTDF normalization,
throughput, spectral transmission, pixel response, and noise.  See
:doc:`stray_light_analysis_and_control` for the sharper radiometric boundary.

Important gaps
--------------

Requirements allocation, cost and schedule trades, optomechanical stress and
thermal analysis, fabrication planning, coatings design, detector electronics,
absolute radiometry, illumination optimization, and test-equipment design are
not KrakenOS capabilities.  The code is strongest from an optical prescription
through rays, fields, relative power, image metrics, and tolerances.
