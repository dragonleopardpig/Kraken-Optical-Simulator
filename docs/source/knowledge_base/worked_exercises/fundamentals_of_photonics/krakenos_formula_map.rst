.. _fop-krakenos-formula-map:

KrakenOS Formula and Code Map
=============================

This page connects equations in Bahaa E. A. Saleh and Malvin Carl Teich,
*Fundamentals of Photonics*, second edition, to the KrakenOS implementation.
It is a reading map, not a claim that KrakenOS implements the whole book.
The strongest correspondence is in ray, beam, Fourier, electromagnetic, and
polarization optics. A formula is marked **direct** only when the code
evaluates that formula, or an algebraically equivalent vector or matrix form.

The printed section, equation, and page numbers below refer to the second
edition used by this solution collection. The equations are restated in the
notation needed to explain the implementation; surrounding textbook prose and
figures are not reproduced. For general identities used in the worked
solutions, see :doc:`mathematical_formula_reference`.

How to read the map
-------------------

.. list-table:: Match levels
   :header-rows: 1
   :widths: 16 84

   * - Level
     - Meaning
   * - **Direct**
     - KrakenOS evaluates the stated equation or an algebraically equivalent
       vector, matrix, or discrete form.
   * - **Partial**
     - KrakenOS implements the named physics under additional assumptions, or
       produces only part of the textbook quantity.
   * - **Related**
     - The code can illustrate the section, but is not a solver for its full
       mathematical model.
   * - **Not modelled**
     - No corresponding first-principles model was found in the KrakenOS
       physics and analysis modules reviewed for this page.

.. important:: Units and conventions

   * Sequential and non-sequential geometry, distance, optical path length,
     radii, and focal lengths are in **millimetres**.
   * Public ray-trace and Gaussian-beam wavelength inputs are normally in
     **micrometres**. Code forming a phase therefore converts
     :math:`\lambda_0[\mathrm{\mu m}]` to
     :math:`\lambda_0[\mathrm{mm}]` with a factor of :math:`10^{-3}`.
   * Glass-catalog dispersion also evaluates wavelength in micrometres.
   * ``KrakenOS/Physics/photodiode.py`` uses explicit unit suffixes and mixes
     nanometres, micrometres, millimetres, and inverse centimetres. Do not
     pass its absorption coefficient to the core tracer without conversion.
   * The book writes the standard paraxial ray as :math:`(y,\theta)^T`.
     KrakenOS' legacy matrices store :math:`(u,y)^T`; ``kraken_to_abcd``
     performs the permutation before Gaussian-beam calculations.
   * Saleh and Teich use an :math:`\exp(+j\omega t)` time convention, giving
     spatial propagation factors such as :math:`\exp(-jkz)`. Some KrakenOS
     field code uses the complex-conjugate convention. Intensities are
     unchanged, but a reported phase sign must be interpreted consistently.

Coverage by chapter
-------------------

.. list-table:: Code coverage of the textbook
   :header-rows: 1
   :widths: 14 18 68

   * - Chapter
     - Coverage
     - KrakenOS capability
   * - 1 Ray Optics
     - **Direct**
     - Optical path, vector Snell refraction, reflection, total internal
       reflection, exact surface intersections, and paraxial matrices.
   * - 2 Wave Optics
     - **Partial**
     - Complex phasors, OPL phase, coherent/incoherent detector sums, thin
       lenses, mirrors, and diffraction gratings. No general Helmholtz solver.
   * - 3 Beam Optics
     - **Direct** for TEM00
     - Gaussian :math:`q` propagation, beam radius, curvature, Rayleigh range,
       divergence, Gouy phase, clipping, and astigmatic X/Y traces. General
       Hermite-, Laguerre-, and Bessel-Gaussian mode families are not solved.
   * - 4 Fourier Optics
     - **Direct/partial**
     - Paraxial Fresnel transfer-function propagation, Fraunhofer FFT,
       diffraction PSF, and MTF. Hologram recording/reconstruction is absent.
   * - 5 Electromagnetic Optics
     - **Partial**
     - Catalog dispersion, Sellmeier forms, exponential bulk attenuation, and
       complex-index metal reflectance. No Maxwell-field boundary-value solver.
   * - 6 Polarization Optics
     - **Partial**
     - P/S Fresnel power, normalized Jones states, branch transport, and
       coherent vector-field summation. Anisotropic media, optical activity,
       liquid crystals, and a general Jones-matrix device cascade are absent.
   * - 7-9 Photonic crystals, guides, fibers
     - **Related**
     - Layered coating tables and TIR ray guidance can illustrate interfaces
       and guided rays, but KrakenOS does not solve Bloch modes or waveguide and
       fiber eigenmodes.
   * - 10 Resonator Optics
     - **Direct/partial**
     - ABCD stability and the self-consistent Gaussian cavity eigenmode. No
       longitudinal spectrum or higher-order resonator-mode solver.
   * - 11 Statistical Optics
     - **Related**
     - Detector fields can be summed by source group, fully coherently, or as
       incoherent power. This is not a stochastic coherence-function solver.
   * - 12-17 Photon, atom, laser, semiconductor-source physics
     - **Not modelled**
     - Ray sources can represent emitted light, but KrakenOS does not solve
       quantum states, rate equations, laser gain, or semiconductor emitters.
   * - 18 Semiconductor Photon Detectors
     - **Partial teaching model**
     - Responsivity, absorption, silicon-slab transmission, diode I-V, and
       photovoltage helpers. Noise, avalanche multiplication, and array-device
       transport are not general device solvers.
   * - 19-24 Lightwave devices and systems
     - **Not modelled**
     - A static diffraction grating is not an acousto-optic interaction model;
       electro-optic, nonlinear, ultrafast, switching, and communication-system
       equations are outside the reviewed implementation.

Chapter 1: ray optics
---------------------

Optical path length
~~~~~~~~~~~~~~~~~~~

Section 1.1, Eq. (1.1-1), printed p. 3, defines

.. math::
   :label: fop-kraken-opl

   \mathcal L=\int_A^B n(\boldsymbol r)\,ds
   \quad\longrightarrow\quad
   \mathcal L=\sum_i n_i\ell_i

for piecewise homogeneous media. ``system.__CollectData`` in
``KrakenOS/KrakenSys.py`` calculates each geometric segment
``dist = norm(RayOrig - pTarget)``, appends ``dist * PrevN`` to ``OP``, and
accumulates it in ``TOP``. Thus ``system.OP[i]`` is :math:`n_i\ell_i`,
``system.TOP_S[i]`` is the cumulative OPL, and ``system.TOP`` is
:math:`\mathcal L`. This is a **direct** discrete implementation of
:eq:`fop-kraken-opl`.

Snell refraction and total internal reflection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 1.1, Eq. (1.1-3), printed p. 5, is Snell's law,

.. math::
   :label: fop-kraken-snell-scalar

   n_1\sin\theta_1=n_2\sin\theta_2.

``snell_refraction_vector_physics.calculate`` and
``batch_snell_refraction`` in ``KrakenOS/PhysicsClass.py`` use its vector
form. For unit incident direction :math:`\boldsymbol s`, a unit normal
:math:`\boldsymbol N` facing the incident ray, and
:math:`\eta=n_1/n_2`, the transmitted direction is

.. math::
   :label: fop-kraken-snell-vector

   \boldsymbol t
   =\eta\boldsymbol s+
    \left(\eta c_1-\sqrt{1-\eta^2(1-c_1^2)}\right)\boldsymbol N,
   \qquad c_1=-\boldsymbol N\!\cdot\!\boldsymbol s.

The code tests
:math:`\eta^2|\boldsymbol N\times\boldsymbol s|^2>1`. This is exactly the
condition that the square root in :eq:`fop-kraken-snell-vector` would be
imaginary, so the path is changed to reflection. The scalar and batched
implementations are equivalent. The code also uses a negative-index sentinel
for a mirror and a ``Secuen`` flag for forced reflection; neither is a physical
negative-index material model.

Paraxial ray matrices
~~~~~~~~~~~~~~~~~~~~~

Section 1.4, Eqs. (1.4-1) to (1.4-3), printed p. 25, writes

.. math::
   :label: fop-kraken-abcd

   \begin{bmatrix}y_2\\\theta_2\end{bmatrix}
   =\begin{bmatrix}A&B\\C&D\end{bmatrix}
    \begin{bmatrix}y_1\\\theta_1\end{bmatrix}.

The component matrices used by ``build_paraxial_matrix_trace`` in
``KrakenOS/ParaxialMatrix.py`` are the book's matrices from Sec. 1.4B:

.. math::
   :label: fop-kraken-component-matrices

   M_{\rm gap}=\begin{bmatrix}1&d\\0&1\end{bmatrix},\qquad
   M_{\rm sphere}=\begin{bmatrix}
       1&0\\(n_1-n_2)/(n_2R)&n_1/n_2
   \end{bmatrix},\qquad
   M_{\rm lens}=\begin{bmatrix}1&0\\-1/f&1\end{bmatrix}.

These correspond to Eqs. (1.4-4), (1.4-6), and (1.4-7), respectively.
For a mirror, the implementation changes the incident-index sign, reducing
the powered-surface term to :math:`-2/R`, as in Eq. (1.4-9). It multiplies
the steps in ray order as required by the cascade rule Eq. (1.4-10).

The apparent transposition in the source is intentional. The legacy matrix
acts on :math:`(u,y)^T`; ``kraken_to_abcd`` converts it to the standard
:math:`(y,u)^T` form in :eq:`fop-kraken-abcd`. Use
``ParaxialMatrixTrace.system_matrix_abcd`` when comparing a numerical result
with the book.

Chapters 2 and 3: waves, gratings, and Gaussian beams
-----------------------------------------------------

Phase, intensity, and interference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 2.2 defines a complex amplitude in Eq. (2.2-2) and its intensity in
Eq. (2.2-10). Section 2.5, Eqs. (2.5-1) and (2.5-4), then gives

.. math::
   :label: fop-kraken-interference

   U=U_1+U_2,\qquad I=|U|^2
   =I_1+I_2+2\sqrt{I_1I_2}\cos(\phi_2-\phi_1).

The coherent-detector path in
``KrakenOS/UI/panels/main_path_detector_analysis.py`` converts each ray's OPL
to a relative phase and then adds complex field amplitudes:

.. math::
   :label: fop-kraken-opl-phase

   \phi_i=\frac{2\pi(\mathcal L_i-\mathcal L_{\rm ref})}{\lambda_0}
           +\phi_{i,\rm branch},\qquad
   U_{\rm pixel}=\sum_i\sqrt{P_i}\,e^{j\phi_i},\qquad
   I_{\rm pixel}=|U_{\rm pixel}|^2.

The code performs the wavelength conversion before evaluating
:eq:`fop-kraken-opl-phase`. It can sum all rays coherently, keep separate
source-coherence groups, or add only incoherent power. This is a **direct
discrete** implementation of Sec. 2.5, subject to the chosen grouping model.

Diffraction grating
~~~~~~~~~~~~~~~~~~~

Section 2.4, Eq. (2.4-13), printed p. 56, gives the one-dimensional grating
equation

.. math::
   :label: fop-kraken-grating

   \sin\theta_q=\sin\theta_i+q\frac{\lambda}{\Lambda}.

``diffraction_grating_physics.calculate`` in
``KrakenOS/PhysicsClass.py`` evaluates a three-dimensional vector generalization
using the surface normal, groove direction, incident and outgoing refractive
indexes, order ``Ord``, wavelength ``W``, and period ``d``. Equation
:eq:`fop-kraken-grating` is its coplanar, same-index limit. KrakenOS determines
the output ray direction; it does **not** calculate the diffraction efficiency
of each order from groove shape.

Gaussian :math:`q` parameter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 3.1, Eqs. (3.1-5), (3.1-6), and (3.1-11), printed pp. 76-77, uses

.. math::
   :label: fop-kraken-q-definition

   q(z)=z+jz_R,\qquad
   \frac1q=\frac1R-j\frac{\lambda_0}{\pi nW^2},\qquad
   z_R=\frac{\pi nW_0^2}{\lambda_0}.

Section 3.2, Eq. (3.2-21), printed p. 92, supplies the ABCD law

.. math::
   :label: fop-kraken-q-abcd

   q_2=\frac{Aq_1+B}{Cq_1+D}.

``propagate_gaussian_beam`` in ``KrakenOS/GaussianBeam.py`` constructs
:math:`q_1` from the waist and applies :eq:`fop-kraken-q-abcd` to every
``abcd_matrix`` step. ``_beam_quantities`` then inverts :math:`q` to recover
:math:`W`, :math:`R`, waist position, :math:`z_R`, divergence, and Gouy phase.
For ``m2=1`` it is a **direct** implementation. For ``m2>1`` the code replaces
:math:`\lambda_0` by :math:`M^2\lambda_0`, the usual real-beam engineering
extension rather than the ideal Gaussian beam assumed in Eqs. (3.1-5) to
(3.1-11).

The finite-aperture helper ``_gaussian_clip_transmission`` evaluates

.. math::
   :label: fop-kraken-gaussian-clip

   \frac{P(\rho<a)}{P}=1-\exp\!\left(-\frac{2a^2}{W^2}\right),

which is Eq. (3.1-17) with :math:`\rho_0=a`. Astigmatic traces propagate
independent tangential and sagittal :math:`q` values through the currently
axisymmetric ABCD sequence.

Chapter 4: Fourier optics and image quality
-------------------------------------------

Fresnel transfer function
~~~~~~~~~~~~~~~~~~~~~~~~~

Section 4.1B, Eq. (4.1-11), printed p. 113, is the paraxial free-space
transfer function. With a convention matching KrakenOS it can be written

.. math::
   :label: fop-kraken-fresnel-transfer

   H(f_x,f_y;d)=e^{jkd}
   \exp\!\left[-j\pi\frac{\lambda_0d}{n}(f_x^2+f_y^2)\right],
   \qquad k=\frac{2\pi n}{\lambda_0}.

``propagate_branch_field`` in ``KrakenOS/BranchField.py`` constructs exactly
this array, multiplies the orthonormal FFT of the sampled field by it, and
inverse-transforms the result. The expression is the complex conjugate of
the book's :math:`\exp(+j\omega t)` convention, as noted above. This is a
paraxial scalar propagator; it does not retain the evanescent spectrum in the
exact transfer function Eq. (4.1-9).

Fraunhofer field and angular axis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 4.2A, Eq. (4.2-1), printed p. 116, states that the far field is a
scaled Fourier transform of the near field. The corresponding sampled form
is

.. math::
   :label: fop-kraken-fraunhofer

   U_\infty(f_x,f_y)\propto\mathcal F\{U_0(x,y)\},\qquad
   \theta_x=\sin^{-1}(\lambda_0 f_x),\quad
   \theta_y=\sin^{-1}(\lambda_0 f_y).

``fft_vector_field_intensity`` and ``fft_angle_axis_mrad`` in
``KrakenOS/UI/coherent_detector_analysis.py`` apply
:eq:`fop-kraken-fraunhofer` independently to the three field components and
sum their intensities. This is a **direct sampled** Fraunhofer calculation.
Its validity still requires the far-field conditions in Eq. (4.2-2), or an
equivalent Fourier-transforming optical system.

Pupil, PSF, and MTF
~~~~~~~~~~~~~~~~~~~

For a focused imaging system, Sec. 4.4C, Eqs. (4.4-11) and (4.4-12), printed
pp. 133-134, makes the amplitude impulse response proportional to the Fourier
transform of the pupil. KrakenOS represents an aberrated pupil as

.. math::
   :label: fop-kraken-pupil-psf

   U_p(\rho,\varphi)=T(\rho,\varphi)
      e^{-j2\pi W(\rho,\varphi)},\qquad
   \mathrm{PSF}=\left|\mathcal F\{U_p\}\right|^2,

where :math:`W` is in waves. ``psf4mtf`` and ``psf`` in
``KrakenOS/PSFCalc.py`` build this pupil from Zernike coefficients, FFT it,
and square its magnitude. ``calculate_mtf`` normalizes the PSF, Fourier
transforms it, and returns the magnitude of the resulting OTF. The PSF step
is a direct discretization of Sec. 4.4; the named MTF calculation is a
standard incoherent-imaging extension, not an explicitly numbered equation
in that section of this edition.

``Zernike_Fitting`` in ``KrakenOS/WavefrontFit.py`` obtains coefficients by
least squares. Zernike decomposition is KrakenOS analysis machinery rather
than a formula developed in Chapters 1-4 of this textbook.

Chapters 5 and 6: materials and polarization
--------------------------------------------

Absorption and dispersion
~~~~~~~~~~~~~~~~~~~~~~~~~

The derivation following Sec. 5.5 Eq. (5.5-3), printed p. 171, gives the
intensity attenuation law

.. math::
   :label: fop-kraken-beer

   I(z)=I(0)e^{-\alpha z}.

Glass transmission tables are converted to
:math:`\alpha=-\ln(T)/d` by ``n_wave_dispersion`` in
``KrakenOS/Physics/optics.py``. ``system.__CollectData`` then appends
``exp(-alpha * dist)`` to ``BULK_TRANS``. This is a **direct** use of
:eq:`fop-kraken-beer`; both :math:`d` and :math:`\alpha^{-1}` must use the
core trace's millimetre length unit.

Section 5.5, Eq. (5.5-28), printed p. 180, gives the Sellmeier form

.. math::
   :label: fop-kraken-sellmeier

   n^2(\lambda)=1+\sum_i
   \frac{B_i\lambda^2}{\lambda^2-C_i}.

For Zemax dispersion formula 2, ``n_wave_dispersion`` evaluates the three-term
version of :eq:`fop-kraken-sellmeier`. It also supports other catalog forms
(Schott, Herzberger, Conrady, extended, and additional Sellmeier variants).
The coefficients are empirical catalog data and must only be used over their
specified wavelength range.

Fresnel reflection and Jones state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 6.2, Eqs. (6.2-8) and (6.2-9), printed p. 211, gives the dielectric
Fresnel amplitude coefficients. In the usual s/p notation,

.. math::
   :label: fop-kraken-fresnel

   r_s=\frac{n_1\cos\theta_1-n_2\cos\theta_2}
            {n_1\cos\theta_1+n_2\cos\theta_2},\qquad
   r_p=\frac{n_2\cos\theta_1-n_1\cos\theta_2}
            {n_2\cos\theta_1+n_1\cos\theta_2},
   \qquad R_{s,p}=|r_{s,p}|^2.

``fresnel_dielectric`` in ``KrakenOS/Physics/optics.py`` evaluates
:eq:`fop-kraken-fresnel` from dot products of the ray and surface-normal
vectors. ``fresnel_metal`` uses a complex refractive index. The public
results ``RP``, ``RS``, ``TP``, and ``TS`` are **power coefficients**, not the
complex amplitudes :math:`r_p,r_s,t_p,t_s`. For an uncoated lossless
dielectric the code sets :math:`T=1-R`.

This distinction matters for polarization interference. Section 6.1,
Eq. (6.1-10), printed p. 203, defines a Jones vector. KrakenOS stores
normalized P/S Jones components and transports an equivalent complex 3-D
polarization vector along each branch. Fresnel power changes are applied as
square-root amplitude weights, while optional coating/beam-splitter phase
settings supply relative phase. The current dielectric helper does **not**
preserve the intrinsic sign or complex phase of every Fresnel amplitude, so it
is a partial Jones implementation rather than a general Jones-matrix solver.

Chapters 10 and 18: cavity and detector helpers
-----------------------------------------------

Gaussian cavity eigenmode
~~~~~~~~~~~~~~~~~~~~~~~~~

Section 10.2A, Eq. (10.2-5), printed p. 379, gives the ABCD trace stability
condition. The self-consistent Gaussian mode also satisfies the fixed-point
form of the Chapter 3 ABCD law:

.. math::
   :label: fop-kraken-cavity

   \left|\frac{A+D}{2\sqrt{AD-BC}}\right|<1,\qquad
   q=\frac{Aq+B}{Cq+D}
   \quad\Longrightarrow\quad
   Cq^2+(D-A)q-B=0.

``solve_gaussian_cavity_eigenmode`` in ``KrakenOS/GaussianBeam.py`` evaluates
the stability parameter, solves the quadratic, and selects the root with
:math:`\operatorname{Im}q>0`. Equality is treated as a boundary rather than a
robust stable mode. The input matrix must represent one complete round trip
at the chosen reference plane.

Semiconductor detector relations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 18.1B, Eqs. (18.1-3) and (18.1-5), printed pp. 753-754, gives

.. math::
   :label: fop-kraken-detector

   \eta=(1-R)\,\zeta\,[1-e^{-\alpha d}],\qquad
   \mathcal R=\frac{\eta e}{h\nu}
             =\frac{\eta\lambda_0}{hc_0}.

``absorption_intensity``, ``absorption_power``, and the silicon-slab helpers
in ``KrakenOS/Physics/photodiode.py`` provide the exponential absorption and
surface-reflection factors. They do not model the carrier collection factor
:math:`\zeta`. ``responsivity`` is a direct numerical implementation of the
second relation in :eq:`fop-kraken-detector`, returning A/W.

Section 18.3, Eq. (18.3-1), printed p. 763, has the photodiode form

.. math::
   :label: fop-kraken-photodiode-iv

   i=i_s\!\left[\exp\!\left(\frac{eV}{k_BT}\right)-1\right]-i_p.

``photodiode_current_density`` implements the same structure per unit area,
with :math:`i_p/A=eL_pG`. Its ``ideality_factor`` generalizes the textbook
exponent to :math:`eV/(m k_BT)`, with :math:`m=1` reproducing
:eq:`fop-kraken-photodiode-iv`. ``photovoltage`` sets the current to zero and
solves for the open-circuit voltage. The function docstrings cite equation
numbers from *Photonics Essentials*, for which these teaching helpers were
originally written; :eq:`fop-kraken-photodiode-iv` is the corresponding
equation in *Fundamentals of Photonics*.

A short code-to-book workflow
-----------------------------

The following pattern keeps the book's ABCD convention throughout. It assumes
``system`` is an already constructed KrakenOS sequential system.

.. code-block:: python

   import KrakenOS as Kos

   # Book Sec. 1.4: obtain the conventional (y, theta) ABCD trace.
   paraxial = system.ParaxMatrices(0.6328)  # wavelength in um
   matrix = paraxial.system_matrix_abcd

   # Book Secs. 3.1-3.2: define a waist and apply q2=(Aq1+B)/(Cq1+D).
   beam = Kos.GaussianBeamInput(
       wavelength_um=0.6328,
       waist_radius_mm=0.25,
       waist_offset_mm=0.0,
       m2=1.0,
       input_index=1.0,
   )
   result = Kos.propagate_gaussian_beam(paraxial, beam)
   last = result.final

   print(matrix)
   print(last.beam_radius_mm, last.wavefront_radius_mm)

For an equation-level check, calculate :math:`q_1=j\pi W_0^2/\lambda_0`
in millimetres and apply :eq:`fop-kraken-q-abcd` to ``matrix`` by hand. Its
real and imaginary parts should agree with ``result.final.q_real_mm`` and
``q_imag_mm`` to floating-point precision.

Limits of this cross-reference
------------------------------

KrakenOS is primarily a geometrical optical-system simulator with selected
paraxial and scalar-wave analyses. A matching variable name is not evidence
of a matching physical model. In particular:

* ``GRIN`` currently resolves to a placeholder bulk index in the catalog
  helper; it is not the continuous ray-equation solver of Sec. 1.3.
* A coating table supplies interpolated P/S power and optional phase data; it
  is not automatically the multilayer transfer-matrix derivation of Chapter 7.
* Geometrical PSF/MTF panels and diffraction PSF/MTF functions are different
  models. ``KrakenOS/PSFCalc.py`` is the Fourier-pupil implementation mapped
  above.
* The photodiode module is a teaching model and is separate from ray landing
  on a camera sensor. It does not make every traced image a semiconductor
  carrier-transport simulation.
* No code correspondence should be inferred for chapters marked **not
  modelled** until a solver and a validation test for that physics exist.
