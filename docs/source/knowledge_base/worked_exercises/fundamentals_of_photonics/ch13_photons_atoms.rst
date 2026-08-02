Chapter 13: Photons and Atoms
=============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 13.

In-text exercises
-----------------

.. rubric:: Exercise 13.3-1 — Spontaneous-emission spectrum

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-13-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_13_03_01.svg
   :alt: Illustrated calculation map for Exercise 13.3-1, Spontaneous-emission spectrum
   :align: center
   :width: 95%

   **Figure 78 — Exercise 13.3-1: Spontaneous-emission spectrum.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The total spontaneous rate is :math:`1/t_{sp}` and normalized lineshape
:math:`\int g(\nu)d\nu=1`; therefore
:math:`\boxed{P_{sp}(\nu)=g(\nu)/t_{sp}}`.  A large photon histogram converges
to this probability density and is consequently proportional to :math:`g`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-13-3-1-result

   \boxed{P_{sp}(\nu)=g(\nu)/t_{sp}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-13-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Exercise 13.3-2 — Doppler broadening

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-13-3-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_13_03_02.svg
   :alt: Illustrated calculation map for Exercise 13.3-2, Doppler broadening
   :align: center
   :width: 95%

   **Figure 79 — Exercise 13.3-2: Doppler broadening.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Map velocity to frequency shift :math:`\delta\nu=\nu_0v/c`.  The Gaussian
standard deviation is :math:`\sigma_\nu=(\nu_0/c)\sqrt{kT/M}`; convolution
with the natural Lorentzian gives a Voigt profile.  In the Doppler-dominated
limit its FWHM is
:math:`\boxed{\Delta\nu_D=(2\nu_0/c)\sqrt{2kT\ln2/M}}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-13-3-2-result

   \boxed{\Delta\nu_D=(2\nu_0/c)\sqrt{2kT\ln2/M}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-13-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

.. rubric:: Exercise 13.4-1 — Blackbody peak in frequency

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-13-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_13_04_01.svg
   :alt: Illustrated calculation map for Exercise 13.4-1, Blackbody peak in frequency
   :align: center
   :width: 95%

   **Figure 80 — Exercise 13.4-1: Blackbody peak in frequency.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiating :math:`\nu^3/(e^{h\nu/kT}-1)` gives
:math:`3(1-e^{-x})=x`; Newton iteration yields :math:`x=2.82144`.  At 300 K,
:math:`\boxed{\nu_p=1.764\times10^{13}\ \mathrm{Hz}}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-13-4-1-result

   \boxed{\nu_p=1.764\times10^{13}\ \mathrm{Hz}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-13-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 13.3-3 — Stimulated versus spontaneous decay

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For either populated cavity mode, evaluate
:math:`P_{st}=n(c/V)\sigma(\nu)` with Lorentzian
:math:`\sigma=Sg(\nu)` and :math:`S=\lambda_0^2/(8\pi n^2t_{sp})` under the
book's polarization convention.  The upper population decays with
:math:`\tau^{-1}=t_{sp}^{-1}+\sum P_{st}`.  Equality of stimulated and total
spontaneous rates follows by setting :math:`\sum n(c/V)\sigma=t_{sp}^{-1}`;
this equation gives the requested replacement photon number unambiguously.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-3-3-result

   \sum n(c/V)\sigma=t_{sp}^{-1}


**Check.**  Equation :eq:`fop-problem-13-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 13.3-4 — Emission into cavity modes

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For a 1-micrometre cube, :math:`\nu=(c/2L)sqrt{q_x^2+q_y^2+q_z^2}`.  The
lowest :math:`(1,1,1)` mode is 260 THz and the next permutations of
:math:`(2,1,1)` are 367 THz.  Spontaneous probability is proportional to
mode degeneracy times :math:`\nu^2g(\nu)` (or the transition lineshape at
that frequency); include the three permutations when forming
:math:`P_{sp,2}/P_{sp,1}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-3-4-result

   \nu=(c/2L)sqrt{q_x^2+q_y^2+q_z^2}


**Check.**  Equation :eq:`fop-problem-13-3-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Problem 13.4-2 — Broadband rate equations

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`M(\nu_0)\Delta\nu` resonator modes,
:math:`\dot N_2=-N_2/t_{sp}-(N_2-N_1)B\rho` and
:math:`\dot n=[N_2/t_{sp}+(N_2-N_1)B\rho]/M- n/t_p`; add the companion
:math:`\dot N_1=-\dot N_2` for conserved atoms.  Here :math:`\rho` is the
energy density represented by the common mode occupation :math:`n`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-2-result

   \dot N_1=-\dot N_2


**Check.**  Equation :eq:`fop-problem-13-4-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 13.4-3 — Two-dimensional blackbody

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Chapter 10 counting gives :math:`M_2(\nu)/A=2\pi\nu/c^2`; multiplying by the
Planck mean energy gives
:math:`\boxed{Q_2(\nu)=2\pi h\nu^2/[c^2(e^{h\nu/kT}-1)]}`.  An atom's
spontaneous rate into this cavity is its per-mode rate times this 2-D mode
density; it is inhibited relative to the 3-D :math:`\nu^2` density according
to their ratio and the cavity thickness normalization.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-3-result

   \boxed{Q_2(\nu)=2\pi h\nu^2/[c^2(e^{h\nu/kT}-1)]}


**Check.**  Equation :eq:`fop-problem-13-4-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 13.4-4 — Equal stimulated/spontaneous rates

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Their ratio is the mean thermal occupation :math:`\bar n`.
:math:`\bar n=1` implies :math:`e^{hc/(\lambda kT)}=2`; at one micrometre,
:math:`\boxed{T=2.076\times10^4\ \mathrm K}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-4-result

   \boxed{T=2.076\times10^4\ \mathrm K}


**Check.**  Equation :eq:`fop-problem-13-4-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 13.4-5 — Wien displacement law

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Change variables using :math:`Q_\lambda=Q_\nu|d\nu/d\lambda|`; maximizing
:math:`\lambda^{-5}/(e^{hc/\lambda kT}-1)` gives
:math:`5(1-e^{-y})=y`, :math:`y=4.96511`, and
:math:`\boxed{\lambda_pT=2.8978\times10^{-3}\ \mathrm{m,K}}`.  The frequency
and wavelength densities have different Jacobians, so
:math:`\lambda_p\ne c/\nu_p`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-5-result

   \boxed{\lambda_pT=2.8978\times10^{-3}\ \mathrm{m,K}}


**Check.**  Equation :eq:`fop-problem-13-4-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 13.4-6 — One-dimensional blackbody

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Including two traveling directions/polarizations according to the book's
1-D convention gives constant :math:`M_1/L=2/c`; hence
:math:`\boxed{Q_1(\nu)=2h\nu/[c(e^{h\nu/kT}-1)]}`.  It tends to
:math:`2kT/c` at zero frequency and decays exponentially at high frequency.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-6-result

   \boxed{Q_1(\nu)=2h\nu/[c(e^{h\nu/kT}-1)]}


**Check.**  Equation :eq:`fop-problem-13-4-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 13.4-7 — Stefan--Boltzmann law

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Integrating the Planck spectrum with
:math:`\int_0^\infty x^3/(e^x-1)dx=\pi^4/15` and multiplying isotropic energy
density by :math:`c/4` gives
:math:`\boxed{P/A=\sigma T^4}` with
:math:`\boxed{\sigma=2\pi^5k^4/(15h^3c^2)=5.6704\times10^{-8}
\ \mathrm{W,m^{-2}K^{-4}}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-4-7-result

   \boxed{\sigma=2\pi^5k^4/(15h^3c^2)=5.6704\times10^{-8}
   \ \mathrm{W,m^{-2}K^{-4}}}


**Check.**  Equation :eq:`fop-problem-13-4-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 13.5-1 — Compound-Poisson cathodoluminescence

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`expectation, variance, and probability identities <fop-formula-probability>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Condition on :math:`m` incident electrons: photons are Poisson with mean
:math:`mG`; mix this over Poisson :math:`m` to get generating function
:math:`\boxed{G_N(z)=\exp\{\bar m[e^{G(z-1)}-1]\}}` (Neyman type A).
Differentiation gives :math:`\boxed{\bar n=\bar mG}` and
:math:`\boxed{\operatorname{var}n=\bar mG(1+G)}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-13-5-1-result

   \boxed{\operatorname{var}n=\bar mG(1+G)}


**Check.**  Equation :eq:`fop-problem-13-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.
