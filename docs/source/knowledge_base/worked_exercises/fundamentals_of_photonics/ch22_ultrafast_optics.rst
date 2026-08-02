Chapter 22: Ultrafast Optics
============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 22.

In-text exercises
-----------------

.. rubric:: Exercise 22.3-1 — Two-fiber dispersion compensation

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-22-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_22_03_01.svg
   :alt: Illustrated calculation map for Exercise 22.3-1, Two-fiber dispersion compensation
   :align: center
   :width: 95%

   **Figure 127 — Exercise 22.3-1: Two-fiber dispersion compensation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Convert :math:`D_\lambda` with
:math:`D_\nu=-(\lambda_0^2/c)D_\lambda=-1.603\times10^{-25}`
:math:`\mathrm{s^2/m}`.  Thus :math:`z_0=\pi T_0^2/D_\nu=-1.960` km and,
after 100 km,

.. math::
   :label: fop-exercise-22-3-1-eq-1

   \boxed{a=z/z_0=-51.02},\qquad
   \boxed{T=T_0\sqrt{1+a^2}=510.3\ \mathrm{ps}}.

Returning to the original width requires zero net GVD:
:math:`20(100)-100d_2=0`, so :math:`\boxed{d_2=20.0\ \mathrm{km}}`.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-22-3-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 22.3-2 — Periodic phase compensation

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-22-3-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_22_03_02.svg
   :alt: Illustrated calculation map for Exercise 22.3-2, Periodic phase compensation
   :align: center
   :width: 95%

   **Figure 128 — Exercise 22.3-2: Periodic phase compensation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Propagation from a pulse waist through distance :math:`d` gives
:math:`a=d/z_0` and :math:`T^2=T_0^2[1+(d/z_0)^2]`.  A quadratic phase changes
the chirp by :math:`\Delta a=\zeta T^2`.  Reflection symmetry about each
modulator demands :math:`a\mapsto-a`, hence

.. math::
   :label: fop-exercise-22-3-2-eq-1

   \boxed{\zeta=-{2a\over T^2}
   =-{2d/z_0\over T_0^2[1+(d/z_0)^2]}}.

The next length :math:`2d` brings the pulse to the same width and opposite
pre-modulator chirp, proving periodicity.

End-of-chapter problems
-----------------------

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-22-3-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 22.1-1 — Sum of unchirped and chirped Gaussians

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Let :math:`x=t^2/T^2`.  The sum envelope is
:math:`A=A_0e^{-x}(1+e^{jax})=2A_0e^{-x}e^{jax/2}\cos(ax/2)`.  Therefore
:math:`I=4|A_0|^2e^{-2x}\cos^2(ax/2)`, phase is :math:`ax/2` between cosine
zeros, and the local chirp coefficient is :math:`a/2` (with pi phase jumps at
zeros).  Fourier transforming each term gives

.. math::
   :label: fop-problem-22-1-1-eq-1

   \widetilde A(f)\propto e^{-\pi^2T^2f^2}
   +(1-ja)^{-1/2}e^{-\pi^2T^2f^2/(1-ja)};

its squared magnitude and argument are the requested spectral intensity and
phase, and differentiating that argument twice gives the spectral chirp.

**Check.**  Equation :eq:`fop-problem-22-1-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

.. rubric:: Problem 22.1-2 — Hyperbolic-secant pulse

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Half intensity satisfies :math:`\mathrm{sech}^2(t/T)=1/2`, so
:math:`T_{FWHM}=2T\operatorname{arcosh}\sqrt2=\boxed{1.763T}`.  The transform
pair :math:`\mathrm{sech}(t/T)\leftrightarrow\pi T\,
\mathrm{sech}(\pi^2Tf)` gives spectral intensity proportional to
:math:`\mathrm{sech}^2(\pi^2Tf)` and
:math:`\boxed{\Delta f=0.179/T}`.  Thus
:math:`T_{FWHM}\Delta f=0.315`, compared with 0.441 for a Gaussian.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-1-2-result

   \boxed{\Delta f=0.179/T}


**Check.**  Equation :eq:`fop-problem-22-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 22.2-1 — Symmetric Brewster prism

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiate Snell's law at both faces while imposing Brewster incidence and
the symmetric-ray condition.  The two angular derivatives are equal and add,
giving :math:`d\theta_d/dn=-2`.  Substitution in the angular-dispersion chirp
formula gives
:math:`\boxed{b=-4(n-N)^2R_0\lambda_0/(\pi c^2)}`.  The thin-prism result has
the same numerator multiplied by apex-angle squared, so the ratio is
:math:`\boxed{4/\alpha^2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-2-1-result

   \boxed{4/\alpha^2}


**Check.**  Equation :eq:`fop-problem-22-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 22.2-2 — Chirped Bragg grating

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The 0.44-ps transform-limited pulse has :math:`\Delta\nu=1.00` THz and
:math:`\Delta\lambda\simeq3.33` nm about 1 micrometre.  The group-delay sweep
of :math:`H(f)=e^{-jb\pi^2f^2}` is
:math:`\Delta\tau=\pi b\Delta\nu=12.57` ps.  A reflection grating therefore
needs :math:`\boxed{L=c\Delta\tau/(2n_g)=1.884/n_g\ \mathrm{mm}}`, and its
local pitch must cover
:math:`\boxed{\Lambda_{min}=998.33/(2n_{eff})\ \mathrm{nm}}` through
:math:`\boxed{\Lambda_{max}=1001.67/(2n_{eff})\ \mathrm{nm}}`.  Reverse the
pitch gradient to reverse the chirp sign.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-2-2-result

   \boxed{\Lambda_{max}=1001.67/(2n_{eff})\ \mathrm{nm}}


**Check.**  Equation :eq:`fop-problem-22-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 22.3-3 — Dispersed rectangular pulse

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The input spectrum is :math:`T\,\mathrm{sinc}(fT)`.  For
:math:`|b|\gg T^2`, stationary phase maps frequency to time by
:math:`f=t/(\pi b)`, so the output envelope is proportional to
:math:`\boxed{\mathrm{sinc}[tT/(\pi b)]}`: the stated sinc-shaped pulse.  Its
first zeros are at :math:`t=\pm\pi|b|/T`, giving zero-to-zero width
:math:`\boxed{2\pi|b|/T=2|D_\nu|z/T}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-3-3-result

   \boxed{2\pi|b|/T=2|D_\nu|z/T}


**Check.**  Equation :eq:`fop-problem-22-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 22.3-4 — Temporal imaging

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

In the far-dispersion limit the first fiber maps input time to frequency, the
quadratic modulator supplies a time-lens phase, and the second maps frequency
back to time.  Cancellation of the residual quadratic phase requires
:math:`\boxed{1/d_1+1/d_2=1/f}`, with :math:`f=-\pi/(\zeta D_\nu)`.  The
remaining kernel is a scaled delta function, so
:math:`A_o(t)\propto A_i(-t/M)` with
:math:`\boxed{|M|=T_2/T_1=d_2/d_1}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-3-4-result

   \boxed{|M|=T_2/T_1=d_2/d_1}


**Check.**  Equation :eq:`fop-problem-22-3-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 22.5-1 — Chirp matching and amplification

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Instantaneous energy conservation requires
:math:`\omega_{3i}(t)=\omega_{1i}(t)+\omega_{2i}(t)`.  For coincident pulses
this means their chirp rates obey
:math:`\boxed{a_3/T_3^2=a_1/T_1^2+a_2/T_2^2}`; group-delay matching keeps the
three time coordinates overlapped.  Therefore, for example,
:math:`a_1/T_1^2=a_3/T_3^2-a_2/T_2^2`, which can exceed the pump rate when
the idler chirp has the opposite sign.  This enables chirp magnification before
dispersive pulse compression or time-to-frequency conversion.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-5-1-result

   \boxed{a_3/T_3^2=a_1/T_1^2+a_2/T_2^2}


**Check.**  Equation :eq:`fop-problem-22-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 22.5-2 — Pulsed mixing with GVD

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Expand :math:`k_q(\omega_q+\Omega)` through :math:`\Omega^2`, apply SVEA,
and inverse transform.  Each envelope satisfies

.. math::
   :label: fop-problem-22-5-2-eq-1

   \left(\partial_z+v_q^{-1}\partial_t
   +{j\beta_{2q}\over2}\partial_t^2\right)A_q
   =-j\kappa_q A_r^{(*)}A_s^{(*)}e^{\pm j\Delta kz},

where conjugates are chosen for sum- or difference-frequency generation.
The first derivative is group delay, the second is GVD, and the right side is
exactly the resonant component of :math:`2dE^2`; these are Eqs. (22.5-3).

**Check.**  Equation :eq:`fop-problem-22-5-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

.. rubric:: Problem 22.5-3 — Equal-energy solitons at two dispersions

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For a fundamental soliton, :math:`I_0T_0^2\propto|D|` and energy
:math:`E\propto I_0T_0`.  Holding energy fixed gives
:math:`T_0\propto|D|`, :math:`I_0\propto1/|D|`, field peak
:math:`|A_0|\propto|D|^{-1/2}`, amplitude area
:math:`\int|A|dt\propto|D|^{1/2}`, and soliton distance
:math:`z_0\propto|D|`.  Thus the 20-versus-10 case has ratios
:math:`\boxed{2,\ 1/2,\ 1/\sqrt2,\ \sqrt2,\ 2}`, respectively.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-5-3-result

   \boxed{2,\ 1/2,\ 1/\sqrt2,\ \sqrt2,\ 2}


**Check.**  Equation :eq:`fop-problem-22-5-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 22.5-4 — Fiber-soliton intensity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Combining the fundamental-soliton condition with
:math:`z_0=\pi T_0^2/D_\nu` eliminates pulse width and gives
:math:`\boxed{I_0|z_0|=\lambda_0/(4\pi n_2)}`.  At 1.55 micrometres,
:math:`n_2=3.19\times10^{-20}\ \mathrm{m^2/W}`, and 30 km,
:math:`\boxed{I_0=1.29\times10^8\ \mathrm{W/m^2}=12.9\ \mathrm{kW/cm^2}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-5-4-result

   \boxed{I_0=1.29\times10^8\ \mathrm{W/m^2}=12.9\ \mathrm{kW/cm^2}}


**Check.**  Equation :eq:`fop-problem-22-5-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 22.6-1 — Gaussian-pulse autocorrelation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Convolving two equal Gaussian intensities broadens FWHM by :math:`\sqrt2`, so
the measured trace is Gaussian with :math:`\boxed{70.7\ \mathrm{fs}}` FWHM.
For one pulse to broaden fivefold, the 800-nm dispersion gives
:math:`z=z_0\sqrt{5^2-1}=\boxed{0.118\ \mathrm m}`.  Correlating 50-fs and
250-fs Gaussians gives :math:`\boxed{255\ \mathrm{fs}}`.  The unequal-arm
interferometric trace can reveal spectral phase sensitivity, but reduced
overlap, fiber loss/nonlinearity, and unknown fiber dispersion make inversion
less robust.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-22-6-1-result

   \boxed{255\ \mathrm{fs}}


**Check.**  Equation :eq:`fop-problem-22-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 22.6-2 — Two-photon versus SHG interferometry

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Write the recombined field as :math:`E_1+E_2`.  A two-photon detector measures
:math:`\int|E_1+E_2|^4dt`; expansion contains the two intensity-autocorrelation
terms, phase-sensitive :math:`E_1^2E_2^{*2}+\mathrm{c.c.}`, and oscillatory
cross terms.  SHG followed by a square-law detector produces the same fourth-
order structure after its generated field is integrated, apart from the SHG
phase-matching/filter response.  Hence an ideal instantaneous two-photon
absorber is the broadband analogue; a real absorber replaces the SHG transfer
function by its own two-photon spectral response.

**Check.**  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.
