.. _krakenos-map-introduction-lens-design:

Introduction to Lens Design
===========================

This map uses José Sasián, *Introduction to Lens Design* (Cambridge University
Press, 2019).  It is the most compact end-to-end companion for KrakenOS: the
book moves from surface shape and exact tracing to image evaluation,
optimization, tolerancing, and ghost analysis in 18 short chapters.

Coverage by chapter
-------------------

.. list-table:: Sasián-to-KrakenOS coverage
   :header-rows: 1
   :widths: 18 14 68

   * - Book section
     - Match
     - KrakenOS implementation
   * - Chs. 2 and 4, first-order optics and thin lenses
     - **Direct/partial**
     - ``ParaxialMatrix.py`` traces powered surfaces, gaps, thin lenses, and
       mirrors; ``SeidelTool.py`` reports third-order aberration estimates.
   * - Ch. 3, aspheric surfaces
     - **Direct**
     - ``MathShapesClass.py`` implements conic sag, even radial polynomial
       terms, user-defined sag, error maps, and Zernike surfaces.
   * - Ch. 5, ray tracing
     - **Direct**
     - ``HitOnSurf.py`` and ``InterNormalCalc.py`` solve intersections and
       normals; ``PhysicsClass.py`` applies vector Snell/reflection physics;
       ``KrakenSys.py`` supplies sequential and non-sequential traces.
   * - Chs. 7 and 8, colour correction and lens forms
     - **Partial/related**
     - Catalog dispersion and wavelength sweeps trace chromatic behaviour, but
       KrakenOS does not automatically synthesize the book's achromats.
   * - Ch. 9, image evaluation
     - **Direct/partial**
     - Ray spots, wavefront fits, diffraction PSF/MTF, encircled-energy-style
       detector data, and captured-image MTF are available in separate tools.
   * - Ch. 10, tolerancing
     - **Direct/partial**
     - The UI tolerance service provides seeded perturbations, distributions,
       compensator sweeps, Monte Carlo summaries, stackups, and yield reports.
   * - Ch. 11, lens-design software
     - **Direct/partial**
     - ``Optimization/`` implements bounded variables and weighted merit
       operands for spot RMS, wavefront RMS, MTF, paraxial targets, and
       thickness penalties.
   * - Chs. 12 and 13, lens forms and combinations
     - **Related**
     - The layout library contains comparable lens families, but not automatic
       synthesis of every construction in these chapters.
   * - Ch. 14, ghost images
     - **Direct/partial**
     - Fresnel/coating power and non-sequential reflected/transmitted branches
       expose real ghost paths, TIR, branch order, and detector arrival.
   * - Chs. 15--18, catalog lenses, mirrors, miniature and zoom lenses
     - **Related/partial**
     - Catalog import, mirrors, coordinate breaks, and multi-configuration
       layouts help construct these systems; automated zoom solving is absent.

Surface sag: Eqs. (3.1), (3.6), and (3.7)
------------------------------------------------

Section 3.2, printed p. 22, gives conic sag for
:math:`\rho^2=x^2+y^2` and vertex curvature :math:`c=1/R`:

.. math::

   z(\rho)=\frac{c\rho^2}
   {1+\sqrt{1-(1+k)c^2\rho^2}}.

``conic__surf.calculate`` in ``KrakenOS/MathShapesClass.py`` evaluates this
expression directly.  ``Rc`` supplies :math:`R`, ``k`` supplies :math:`k`,
and ``Cylinder_Rxy_Ratio`` changes the radial coordinate to
:math:`\rho^2=x^2+(q_y y)^2`.  The absolute value used inside the code's square
root is a numerical domain policy, not part of Eq. (3.1); a design outside the
real conic domain should not be made physically valid by that safeguard.

Sections 3.4, Eqs. (3.6)--(3.7), printed p. 24, add an even polynomial:

.. math::

   z_{\rm total}(\rho)=z_{\rm conic}(\rho)
      +A_2\rho^2+A_4\rho^4+A_6\rho^6+\cdots .

``aspheric__surf.calculate`` evaluates eight even terms through
:math:`\rho^{16}`.  ``SurfaceShape.calculate`` adds the conic, polynomial,
Zernike, error-map, axicon, and user-surface contributions.  This is a
**direct** implementation, provided the coefficient order is translated
correctly.  ``AspherData[0]`` is :math:`A_2`, not :math:`A_4`.

Optical path and exact rays: Chs. 2 and 5
-----------------------------------------

Section 2.3, Eqs. (2.3)--(2.4), printed pp. 11--12, defines optical path as

.. math::

   \mathrm{OPL}=\int n(s)\,ds
   \quad\longrightarrow\quad
   \mathrm{OPL}=\sum_i n_i s_i

for homogeneous segments.  ``system.__CollectData`` in
``KrakenOS/KrakenSys.py`` stores each :math:`n_i s_i` in ``OP``, the cumulative
values in ``TOP_S``, and the total in ``TOP``.

Sections 5.1--5.3, printed pp. 44--47, distinguish prescribed surface order
from nearest-hit non-sequential tracing and formulate refraction with ray and
surface-normal vectors.  KrakenOS has the same division:

* ``system.Trace`` follows ``SDT`` order and supports reverse traversal.
* ``system.NsTrace`` searches physical candidates and follows the nearest
  valid hit rather than the next row.
* ``Hit_Solver.SolveHit`` finds a root of the implicit surface equation.
* ``snell_refraction_vector_physics.calculate`` applies vector Snell refraction,
  reflection, and the TIR discriminant.

The correspondence is **direct**, but coordinate breaks and surface sign
conventions still have to agree with the book.  Negative index values used as
mirror sentinels are implementation control values, not negative-index media.

Image evaluation: Chapter 9
---------------------------

Sections 9.1--9.2, printed pp. 99--108, connect geometrical spot diagrams,
encircled energy, wave aberration, PSF, and MTF.  KrakenOS splits that chain
across modules:

.. math::

   U_{\rm pupil}=P\exp(-j2\pi W),\qquad
   \mathrm{PSF}=|\mathcal F\{U_{\rm pupil}\}|^2,qquad
   \mathrm{MTF}=|\mathcal F\{\mathrm{PSF}\}|.

``PhaseCalc.py`` reconstructs pupil OPD, ``WavefrontFit.py`` fits Zernike or
polynomial descriptions, and ``PSFCalc.psf4mtf`` plus ``calculate_mtf`` form
the sampled pupil, FFT PSF, and normalized MTF.  Geometrical detector spots
are a different result and should not be described as diffraction PSFs.

Tolerancing and optimization: Chapters 10 and 11
-------------------------------------------------

Section 10.7, printed p. 116, gives the root-sum-square estimate for
independent zero-mean contributions,

.. math::

   \sigma_T\simeq\sqrt{\sum_i \sigma_i^2}.

Section 10.8, printed pp. 117--119, instead samples simultaneous manufacturing
errors and evaluates the resulting population.  The tolerance UI implements
the latter route, including seeded normal/uniform distributions, correlated
groups, compensator sweeps, percentile summaries, and yield against a limit.
Its stackup dashboard also calculates RSS and worst-case summaries.  A Monte
Carlo result is only meaningful if the entered distribution widths and
compensator policy represent manufacturing reality.

Section 11.2, printed pp. 129--130, treats the merit function as a weighted sum
of departures from targets.  ``Optimization/merit.py`` uses the corresponding
least-squares structure

.. math::

   \mathcal M=\sum_i w_i\,[v_i(\boldsymbol x)-t_i]^2

with invalid-trace penalties.  ``Optimization/specs.py`` exposes spot,
wavefront, focal-length, magnification, pupil, MTF, and thickness operands.

Ghosts: Chapter 14
------------------

Section 14.1, printed p. 165, starts with normal-incidence uncoated surface
reflectivity,

.. math::

   R=\left(\frac{n_1-n_2}{n_1+n_2}\right)^2,

and Secs. 14.2--14.5 progress from first-order estimates to real rays and TIR
ghosts.  ``Physics/optics.py`` evaluates angle-dependent S/P Fresnel power;
coating tables can override interface values.  The non-sequential branch
engine creates reflected and transmitted children, records branch paths and
power, and stops branches below configured power or depth thresholds.  This
is stronger than the chapter's first-order construction for path geometry,
but it is only quantitatively predictive when coatings, bulk loss, apertures,
surface quality, and detector acceptance are modelled correctly.

Important gaps
--------------

KrakenOS does not automatically choose glasses, bend elements, synthesize the
book's lens families, create athermal solutions, or solve zoom cams.  Its core
trace is not a full radiometric exposure/noise model.  Manufacturing drawings,
asphere test design, narcissus thermal self-imaging, and a general illumination
solver remain outside the reviewed implementation.
