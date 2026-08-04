.. _krakenos-map-stray-light-analysis:

Stray Light Analysis and Control
================================

This map uses Eric C. Fest, *Stray Light Analysis and Control* (SPIE Press,
2013).  It is the best of the five references for interpreting KrakenOS'
non-sequential branches, ghosts, CAD occlusion, diffuse scattering, and path
history.  It also defines the absolute radiometric quantities that KrakenOS
does **not** yet calculate as a complete calibrated system.

Coverage by chapter
-------------------

.. list-table:: Fest-to-KrakenOS coverage
   :header-rows: 1
   :widths: 18 14 68

   * - Book section
     - Match
     - KrakenOS implementation
   * - Ch. 1, terminology
     - **Related**
     - Surface roles, interaction types, branch paths, media transitions, and
       detector hits provide concrete counterparts to path terminology.
   * - Ch. 2, radiometry
     - **Partial/not modelled**
     - Relative branch power and detector sums exist; general radiance,
       throughput, PST, VGI, NEI, and thermal detector response do not.
   * - Ch. 3, basic ray tracing
     - **Direct/partial**
     - Non-sequential geometry, branching, ray depth, detector acceptance,
       ancestry-like paths, and scatter targeting are implemented.  Statistical
       convergence analysis and a general backward tracer are absent.
   * - Ch. 4, optical roughness scatter
     - **Partial**
     - Optional pySCATMECH BRDF models include microroughness/PSD physics and
       weight deterministic child directions.  KrakenOS does not fit Fest's
       models from metrology data itself.
   * - Chs. 5--6, contamination and black-surface scatter
     - **Partial/related**
     - Imported BRDF parameters and Lambertian, cosine-lobe, Oren--Nayar, or
       pySCATMECH surfaces can approximate them; contamination budgets and
       measured black-coating databases are absent.
   * - Ch. 7, ghosts and diffraction
     - **Direct/partial**
     - Fresnel/coating split branches, TIR, and path/power records model ghosts.
       Aperture diffraction is available in separate field/PSF tools, not as a
       BDDF child in the non-sequential tracer.
   * - Ch. 8, stray-light-aware optical design
     - **Related**
     - Out-of-field launches, detector maps, branch filtering, and layout edits
       support the process; KrakenOS does not optimize directly for PST.
   * - Ch. 9, baffles and cold shields
     - **Partial/related**
     - CAD or analytic absorbing/scattering geometry can test baffles.  There
       is no automatic baffle designer or thermal cold-shield emission model.
   * - Ch. 10, BSDF/TIS and system measurements
     - **Not modelled/related**
     - External measured BRDF values may be supplied, but KrakenOS is not a
       goniometer or stray-light measurement reduction package.
   * - Ch. 11, engineering process
     - **Related**
     - Saved layouts, reports, validators, and reproducible traces help with
       verification, but do not implement the organizational process.

Radiometric boundary: Chapter 2
-------------------------------

Section 2.1.6, Eq. (2.17), printed p. 22, defines throughput (étendue)
between source and collector areas:

.. math::

   G=\iint
   \frac{dA_s\cos\theta_s\,dA_c\cos\theta_c}{d^2}
   =\int dA_s\cos\theta_s\,d\Omega_c.

Equation (2.20) gives the index-weighted invariant
:math:`n_1^2G_1=n_2^2G_2`.  KrakenOS traces the geometry needed to estimate
area and solid-angle acceptance, but it does not expose a general étendue
integrator or enforce radiance conservation as an absolute unit contract.

Section 2.1.10, Eq. (2.27), printed p. 25, defines

.. math::

   \operatorname{BSDF}(\theta_i,\phi_i,\theta_s,\phi_s)
   =\frac{dL_s}{dE_i},

and Eq. (2.32), printed p. 28, integrates it over projected solid angle:

.. math::

   \operatorname{TIS}=\int_{2\pi}
      \operatorname{BSDF}\cos\theta_s\,d\Omega_s.

``scatter_backend.pyscatmech_scalar_brdf`` evaluates a selected scalar BRDF at
an incident/outgoing direction.  ``KrakenSys.__LambertianScatterSamples``
multiplies sampled BRDF values by :math:`\cos\theta_s`, normalizes the sampled
weights, and distributes the user-specified total reflectance among child
rays.  This preserves the configured child-power budget, but it is **not** a
quadrature evaluation of Eq. (2.32), nor does it turn the result into absolute
radiance.  The built-in Lambertian and lobe models are teaching/engineering
approximations with the same limitation.

Non-sequential paths: Chapter 3
-------------------------------

Section 3.1 requires both optical and mechanical geometry plus surface optical
properties.  ``system.NsTrace`` intersects analytic surfaces, optical solids,
and promoted CAD faces; per-face roles can select optical, mirror, absorbing,
diffuse-scatter, detector, or mechanical behaviour.  Each hit records surface,
face, point, direction, normal, media transition, interaction type/model,
branch path, power, and OPL.

Section 3.2.7, printed pp. 54--55, describes ancestry as the number of ray
splits and uses it to classify first- and higher-order stray paths.  KrakenOS'
closest direct representation is a hierarchical branch path such as
``root/R/T/scatter01`` plus branch depth and parent/child records.  It is more
descriptive than one ancestry integer because it retains interaction kind.
Power/depth thresholds bound the tree.

Section 3.2.8 discusses Monte Carlo ray splitting.  KrakenOS normally creates
a deterministic set of hemispherical or targeted scatter directions and
normalizes their powers.  It can therefore compare repeatable paths, but its
default scatter operation is not Fest's stochastic ray-splitting estimator and
does not report estimator variance or convergence versus ray count.

Section 3.2.3's backward trace is also a real gap.  Launching a ray in the
opposite direction or reversing a sequential prescription can answer some
reciprocal geometry questions, but KrakenOS has no general adjoint radiometric
tracer that starts at every detector pixel and preserves the book's source and
throughput bookkeeping automatically.

Roughness and BRDF models: Chapters 4--6
-----------------------------------------

The optional pySCATMECH backend connects most closely to Chapter 4.  A surface
may select ``Microroughness_BRDF_Model`` and pass its wavelength-dependent
parameters; the backend converts KrakenOS vectors to incidence, scatter, and
azimuth angles and requests a scalar BRDF.  Other pySCATMECH models can be
named through the same interface.

``docs/source/manual/diffuse_scattering.rst`` documents the complete setup and
fallback rules.  If pySCATMECH is unavailable or returns no usable weights,
KrakenOS falls back to a built-in model.  A successful trace therefore needs a
backend-status check before it is cited as a microroughness prediction.

KrakenOS does not derive a PSD from a surface map, infer contamination level,
fit an Harvey--Shack/ABg model, validate reciprocity, or integrate TIS from a
measured data set.  Those preprocessing and verification steps must be done
outside the tracer.

Ghost reflections: Chapter 7
----------------------------

For an uncoated dielectric boundary, Sec. 7.1.1 uses the Fresnel amplitude
coefficients.  KrakenOS evaluates their S/P vector equivalent and converts to
power.  At normal incidence this reduces to

.. math::

   R=\left|\frac{n_1-n_2}{n_1+n_2}\right|^2,
   \qquad T=1-R

for lossless real media.  Coating tables can replace the interface split, and
bulk absorption reduces power along a segment.  ``NsTrace`` follows reflected
and transmitted descendants, so a two-reflection lens ghost appears as an
explicit path rather than a paraxial estimate.

Path existence alone is not a quantitative ghost result.  Coating wavelength
and angle, complex phase, bulk loss, aperture clipping, focus, source extent,
detector sampling, scatter, and branch cutoffs all affect the final artifact.

Practical KrakenOS workflow
---------------------------

1. Model every optically visible mechanical surface, not only the prescription.
2. Assign measured or defensible Fresnel, coating, absorption, and scatter data.
3. Launch both in-field and plausible out-of-field sources over angle and
   wavelength.
4. Inspect detector-reaching branch paths before interpreting a heat map.
5. Increase ray/scatter sampling and branch limits until the quantity of
   interest is stable.
6. Normalize to a stated incident power, then perform the missing absolute
   radiometric conversion externally when watts, radiance, irradiance, PST, or
   detector signal are required.

Important gaps
--------------

No complete absolute-radiance engine, blackbody/internal thermal emission,
PST/PSNIT/VGI/NEI calculator, statistically controlled Monte Carlo estimator,
backward/adjoint tracer, contamination budget, diffraction-as-BDDF branch,
automatic baffle designer, BSDF/TIS measurement reducer, or uncertainty
propagator was found in the reviewed implementation.
