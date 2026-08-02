Chapter 17: Semiconductor Photon Sources
=========================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 17.

In-text exercises
-----------------

Exercise 17.1-1 — Pumped quasi-Fermi levels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-17-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_17_01_01.svg
   :alt: Illustrated calculation map for Exercise 17.1-1, Pumped quasi-Fermi levels
   :align: center
   :width: 95%

   **Figure 100 — Exercise 17.1-1: Pumped quasi-Fermi levels.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At zero temperature, state counting gives
:math:`E_{Fc}-E_c=\hbar^2(3\pi^2\Delta n)^{2/3}/(2m_e)` and
:math:`E_v-E_{Fv}=\hbar^2(3\pi^2\Delta p)^{2/3}/(2m_h)`; charge-pair injection
sets :math:`\Delta n=\Delta p`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-17-1-1-result

   \Delta n=\Delta p


**Step 5 — Check.**  Equation :eq:`fop-exercise-17-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 17.1-2 — Weak-injection spectrum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-17-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_17_01_02.svg
   :alt: Illustrated calculation map for Exercise 17.1-2, Weak-injection spectrum
   :align: center
   :width: 95%

   **Figure 101 — Exercise 17.1-2: Weak-injection spectrum.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Replace electron and hole Fermi factors by Boltzmann tails.  Their product is
:math:`e^{-(h\nu-E_g)/kT}`; multiplying the direct-gap joint DOS yields
:math:`\boxed{r_{sp}\propto\sqrt{h\nu-E_g},
e^{-(h\nu-E_g)/kT}}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-17-1-2-result

   \boxed{r_{sp}\propto\sqrt{h\nu-E_g},
   e^{-(h\nu-E_g)/kT}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-17-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 17.1-3 — LED peak and width
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-17-1-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_17_01_03.svg
   :alt: Illustrated calculation map for Exercise 17.1-3, LED peak and width
   :align: center
   :width: 95%

   **Figure 102 — Exercise 17.1-3: LED peak and width.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiation gives :math:`h\nu_p=E_g+kT/2`.  Solve the two half-maximum
roots of :math:`\sqrt{x}e^{-x/kT}`; their difference is proportional to
:math:`kT`, and wavelength width is
:math:`\Delta\lambda\simeq(\lambda_p^2/hc)\Delta E`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-17-1-3-result

   h\nu_p=E_g+kT/2


**Step 5 — Check.**  Equation :eq:`fop-exercise-17-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 17.1-4 — Planar LED extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-17-1-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_17_01_04.svg
   :alt: Illustrated calculation map for Exercise 17.1-4, Planar LED extraction
   :align: center
   :width: 95%

   **Figure 103 — Exercise 17.1-4: Planar LED extraction.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Escape half-angle is :math:`\sin^{-1}(1/n)` and isotropic one-face fraction
:math:`[1-\cos\theta_c]/2`.  Critical angles for GaAs, GaN, polymer are
:math:`16.13^\circ,23.58^\circ,41.81^\circ`; fractions are 1.99%, 4.17%, and
12.73% before Fresnel loss.  An index-matched hemispherical dome removes the
planar TIR restriction for rays reaching it normally.

End-of-chapter problems
-----------------------

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 17.1-5 — LED widths from plots
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Read both half-height wavelengths for each of the seven curves, then convert
with :math:`\Delta\nu\simeq c\Delta\lambda/\lambda_0^2` and
:math:`\Delta E=h\Delta\nu`.  Compare to Exercise 17.1-3; the 0.53-micrometre
curve's excess in quadrature/width over the thermal prediction is alloy
broadening.  Preserve graph-read uncertainty in the table.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-1-5-result

   \Delta E=h\Delta\nu


**Check.**  Equation :eq:`fop-problem-17-1-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.1-6 — Fresnel-corrected extraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Integrate unpolarized transmission over the internal escape cone:
:math:`\boxed{\eta_e=\tfrac12\int_0^{\theta_c}
[T_s(\theta)+T_p(\theta)]\sin\theta,d\theta}` with the intensity Fresnel
coefficients including the refractive-index flux factor.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-1-6-result

   \boxed{\eta_e=\tfrac12\int_0^{\theta_c}
   [T_s(\theta)+T_p(\theta)]\sin\theta,d\theta}


**Check.**  Equation :eq:`fop-problem-17-1-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 17.1-7 — LED-to-fibre coupling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The internal acceptance satisfies
:math:`n_{LED}\sin\theta_a=\mathrm{NA}`.  Normalize the
:math:`\cos^4\theta` emission over a hemisphere; integration gives
:math:`\boxed{\eta=1-\cos^5[\sin^{-1}(0.1/3.6)]\simeq1.93\times10^{-3}}`
before interface Fresnel loss.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-1-7-result

   \boxed{\eta=1-\cos^5[\sin^{-1}(0.1/3.6)]\simeq1.93\times10^{-3}}


**Check.**  Equation :eq:`fop-problem-17-1-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 17.2-1 — SOA bandwidth graph
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At each injected density read the two zero-gain frequencies from Fig. 17.2-3,
subtract them, and least-squares fit :math:`B=a\Delta n+b`.  Pair each width
with the graph's peak gain to plot gain versus bandwidth; quote pixel/line
reading uncertainty rather than fabricated precision.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-2-1-result

   B=a\Delta n+b


**Check.**  Equation :eq:`fop-problem-17-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.2-2 — Zero-temperature SOA peak
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Gain is positive between :math:`E_g` and
:math:`E_{Fc}-E_{Fv}` and peaks at the quasi-Fermi separation.  Substitute the
zero-temperature density expressions from Exercise 17.1-1 into the direct-gap
gain formula to obtain :math:`\gamma_p(\Delta n)`; evaluating the supplied
InGaAsP masses/lifetime produces the requested density plot.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 17.2-3 — GaAs gain program
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each :math:`\Delta n`, solve charge neutrality for quasi-Fermi levels;
evaluate joint DOS times :math:`f_c-f_v` over photon energy at 0 K and 300 K.
Extract peak, zero crossings, transparency density, and widths, then compare
with Fig. P17.2-3.  This algorithm covers all six requested plots and makes
temperature broadening explicit.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 17.2-4 — Band-tail gap reduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Insert p-type :math:`n\ll p` or intrinsic injection
:math:`n=p=\Delta n` into the empirical equation and solve
:math:`\Delta E_g=-0.02` eV for concentration.  Add that result to nominal
:math:`E_g`; it should coincide, within graph uncertainty, with the low-energy
zero of the measured gain curve.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-2-4-result

   \Delta E_g=-0.02


**Check.**  Equation :eq:`fop-problem-17-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.2-5 — GaAs amplifier capacity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Steady excess density is :math:`\Delta n=(I/eV)\tau`, with active volume
:math:`dwl`.  Use zero-K quasi-Fermi levels to get gain window and peak gain;
total gain is :math:`e^{\gamma_pd}`.  Channel count is
:math:`\lfloor B/4\ \mathrm{kHz}\rfloor` and bit rate is that count times
64 kbit/s.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-2-5-result

   \Delta n=(I/eV)\tau


**Check.**  Equation :eq:`fop-problem-17-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 17.2-6 — Semiconductor transition cross section
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Define :math:`\sigma(\nu)=\gamma(\nu)/(N_2-N_1)` using the calculated
same-k occupation difference.  It changes strongly with carrier density and
photon energy because both DOS and Fermi levels change; unlike discrete-ion
amplifiers, no material-only cross section conveniently describes an SOA.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-2-6-result

   \sigma(\nu)=\gamma(\nu)/(N_2-N_1)


**Check.**  Equation :eq:`fop-problem-17-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.2-7 — Residual facet ripple
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The Airy peak-to-valley ratio for equal facets is
:math:`[(1+R)/(1-R)]^2`.  Requiring it below 1.10 gives
:math:`\boxed{R<[\sqrt{1.10}-1]/[\sqrt{1.10}+1]\simeq0.0238}`; gain inside
the chip tightens this bound through effective round-trip reflectance.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-2-7-result

   \boxed{R<[\sqrt{1.10}-1]/[\sqrt{1.10}+1]\simeq0.0238}


**Check.**  Equation :eq:`fop-problem-17-2-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.3-1 — Index dependence of LED output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

In Eq. (17.3-10), index appears in internal optical mode density, photon
velocity :math:`c/n`, Fresnel/escape efficiency, and the conversion between
internal and external solid angles.  Mark these factors before simplifying;
carrier recombination rate itself is not independently index-free because
the radiative coefficient also contains photonic DOS.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 17.3-2 — Number of longitudinal laser modes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Available gain energy is :math:`0.96-0.91=0.05` eV, so
:math:`B=0.05/h`.  Cavity spacing is :math:`c/(2nd)`; therefore maximum count
is :math:`\boxed{1+\lfloor B/[c/(2nd)]\rfloor}` (apply edge conventions to a
mode exactly at a zero-gain endpoint).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-3-2-result

   \boxed{1+\lfloor B/[c/(2nd)]\rfloor}


**Check.**  Equation :eq:`fop-problem-17-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 17.3-3 — Cleaved-facet threshold
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Facet reflectance is :math:`R=[(3.5-1)/(3.5+1)]^2=0.3086`.  With identical
facets and :math:`d=0.05` cm,
:math:`\boxed{\gamma_t=-\ln R/d=23.52\ \mathrm{cm^{-1}}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-3-3-result

   \boxed{\gamma_t=-\ln R/d=23.52\ \mathrm{cm^{-1}}}


**Check.**  Equation :eq:`fop-problem-17-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 17.3-4 — Dispersive mode spacing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The wavelength spacing is
:math:`\Delta\lambda=\lambda^2/[2d(n-\lambda,dn/d\lambda)]`, involving group
index rather than phase index.  Insert 0.12 nm to solve
:math:`n_g=\lambda_c^2/(2d\Delta\lambda)` and then
:math:`a=(n_g-n_0)/\lambda_c`.  Gas-laser mode pulling is gain-dispersion
shifting a cavity resonance; here ordinary semiconductor material dispersion
sets the baseline spacing by the same group-delay principle.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-17-3-4-result

   a=(n_g-n_0)/\lambda_c


**Check.**  Equation :eq:`fop-problem-17-3-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.
