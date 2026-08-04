.. _krakenos-map-modern-optical-engineering:

Modern Optical Engineering
==========================

This map uses Warren J. Smith, *Modern Optical Engineering: The Design of
Optical Systems*, fourth edition.  It is the closest reference for the
classical imaging core of KrakenOS, and Chapter 19 is also a direct source of
numerical prescriptions in the repository.

Coverage by chapter
-------------------

.. list-table:: Smith-to-KrakenOS coverage
   :header-rows: 1
   :widths: 18 14 68

   * - Book section
     - Match
     - KrakenOS implementation
   * - Chs. 2--4, Gaussian and paraxial optics
     - **Direct/partial**
     - ``ParaxialMatrix.py`` evaluates gap, refracting-surface, mirror, and
       thin-lens matrices, cardinal quantities, stops, and pupils.
   * - Chs. 5--6, primary and third-order aberrations
     - **Direct/partial**
     - Exact ray intercepts and OPD are direct; ``SeidelTool.py`` estimates
       Seidel sums and the knowledge base derives Smith's ray polynomial.
   * - Chs. 7 and 9, prisms, mirrors, stops, and diffraction
     - **Direct/partial**
     - Refraction, reflection, TIR, coordinate breaks, stops, pupil tools,
       Gaussian beams, and diffraction PSF/MTF are available.
   * - Chs. 10--12, materials, coatings, and radiometry
     - **Partial/related**
     - Catalog dispersion, absorption, metal reflectance, Fresnel power, and
       coating tables are present; absolute radiometry is not.
   * - Chs. 13--14, system layout
     - **Related/direct**
     - The UI and common layout library support complete sequential and
       non-sequential systems, folded paths, CAD solids, and detectors.
   * - Ch. 15, image evaluation
     - **Direct/partial**
     - OPD, fitted wavefronts, geometrical spots, PSF, MTF, and energy maps are
       implemented, but not every chart and tolerance criterion in the book.
   * - Chs. 16--18, lens, mirror, and catadioptric forms
     - **Related**
     - KrakenOS can model and optimize these forms; it does not automatically
       synthesize the book's starting points.
   * - Ch. 19, selected designs
     - **Direct data**
     - All 62 printed prescriptions are encoded in
       ``common_optical_layouts/_modern_optical_engineering_ch19.py``.
   * - Ch. 20, manufacture, tolerances, mounts, and laboratory practice
     - **Partial/related**
     - Monte Carlo tolerance and compensator tools cover part of the chapter;
       manufacture, mounts, drawings, and laboratory practice are not solvers.
   * - App. A, ray tracing and aberration calculation
     - **Direct**
     - KrakenOS uses equivalent three-dimensional vector intersection and
       refraction methods for meridional and skew rays, including aspheres.

Paraxial refraction and system matrices
---------------------------------------

Sections 3.1--3.6 develop refraction, translation, several-surface tracing,
thin lenses, and mirrors.  In the conventional ray order
:math:`\boldsymbol r=(y,u)^T`, KrakenOS' component matrices are

.. math::

   M_{\rm gap}=\begin{bmatrix}1&d\\0&1\end{bmatrix},\qquad
   M_{\rm surface}=\begin{bmatrix}
      1&0\\(n_1-n_2)/(n_2R)&n_1/n_2
   \end{bmatrix}.

``build_paraxial_matrix_trace`` multiplies these in ray order.  The legacy
internal matrices use :math:`(u,y)^T`; ``kraken_to_abcd`` performs the
permutation.  ``ParaxialMatrixTrace`` reports effective focal length, front and
back focal lengths, principal planes, entrance/exit pupils, and magnification.
This is a **direct matrix equivalent** of the book's paraxial trace, not its
row-by-row scalar worksheet.

Aberration polynomial: Eqs. (5.1) and (5.2)
------------------------------------------------

Section 5.2, printed pp. 62--67, expands the transverse ray intercept in field
height, pupil radius, and pupil azimuth.  KrakenOS does not use the series to
propagate a real ray: it traces exact surfaces.  The relationship is therefore
best used to interpret a traced spot or fit its symmetry and orders.

The full invariant derivation and coefficient meanings are given in
:doc:`../../aberration_polynomial`.  It shows why centred systems contain
odd transverse orders and connects the third-order coefficients to spherical
aberration, coma, astigmatism, Petzval curvature, and distortion.
``SeidelTool.Seidel.calculate`` supplies a lower-order diagnostic, while
``PhaseCalc.py`` and ``WavefrontFit.py`` recover OPD and fitted wavefront
coefficients from exact rays.  These are complementary analyses, not identical
coefficient normalizations.

Stops, diffraction, and Gaussian beams: Chapter 9
-------------------------------------------------

Sections 9.2--9.7 define the aperture stop, pupils, field stop, vignetting,
telecentricity, :math:`f`-number, and numerical aperture.  These map to surface
clear apertures, stop flags, pupil analysis, ray acceptance, and paraxial
reports.  A CAD face that blocks a non-sequential ray is a physical occluder;
it is not automatically the paraxial aperture stop.

Sections 9.9--9.11 cover aperture diffraction, resolution, and TEM00 beams.
The implemented Gaussian relations are

.. math::

   q_2=\frac{Aq_1+B}{Cq_1+D},\qquad
   \frac{1}{q}=\frac{1}{R}-j\frac{\lambda_0 M^2}{\pi n w^2}.

``GaussianBeam.propagate_gaussian_beam`` evaluates these through the paraxial
trace and reports waist radius, curvature, Rayleigh range, divergence, Gouy
phase, and clipping.  ``PSFCalc.py`` separately evaluates a sampled diffraction
PSF.  A Gaussian :math:`1/e^2` beam radius, geometrical RMS spot radius, and
Airy radius are three different quantities.

Image evaluation: Chapter 15
----------------------------

Sections 15.2--15.4 connect focus, spherical aberration, wavefront error, and
tolerances.  ``KrakenSys`` accumulates OPL per ray, ``PhaseCalc`` removes a
reference sphere/tilt, and ``WavefrontFit`` fits the residual.  The wavelength
must be converted from micrometres to millimetres before an OPL in millimetres
is expressed in waves.

Sections 15.5--15.10 cover energy distributions, spread functions, MTF, and
square-wave targets.  ``PSFCalc`` supplies the diffraction path; ``EdgeMTF``
and ``USAFMTF`` supply captured-image paths.  For the detailed transform and
measurement equations, see :doc:`modulation_transfer_function`.

Chapter 19: exact prescriptions in the repository
-------------------------------------------------

``KrakenOS/common_optical_layouts/_modern_optical_engineering_ch19.py`` cites
Smith Chapter 19, figures 19.1--19.62, book pp. 534--596.  It encodes every
surface row in propagation order, including radii, spacings, glass index and
Abbe number, apertures, stops, wavelength, image surface, and the two aspheric
Schwarzschild designs.

The translation rules are explicit:

* A blank radius becomes a plane surface.
* Historical or discontinued glasses use embedded ``nvk`` index/Abbe data so
  that a catalog rename cannot silently change the prescription.
* Smith's printed conic value :math:`p` becomes KrakenOS
  :math:`\kappa=p-1` for figures 19.61--19.62.
* Smith's ``AD``, ``AE``, ``AF``, and ``AG`` coefficients become radial
  :math:`A_4`, :math:`A_6`, :math:`A_8`, and :math:`A_{10}` terms.

The designs are exposed through the UI layout library.  Run
``python -m KrakenOS.UI.validate_modern_optical_engineering_layouts`` to check
construction and traceability.  Numerical reproduction of a prescription is
not proof that a plotted ray fan matches the book: wavelength, focus plane,
field sampling, aperture normalization, and glass data must also match.

Important gaps
--------------

KrakenOS has no automatic first-order architecture generator, glass-map search,
thermal/structural finite-element solver, optomechanical mount analysis,
manufacturing drawing generator, coating-stack optimizer, or laboratory test
planner.  Chapter 19 prescriptions are source data, not licensed substitutes
for the book's design commentary and plots.
