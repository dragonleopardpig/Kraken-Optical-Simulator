Chapter 8: Guided-Wave Optics
=============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 8.

In-text exercises
-----------------

.. rubric:: Exercise 8.1-1 — Modal power

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-8-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_01_01.svg
   :alt: Illustrated calculation map for Exercise 8.1-1, Modal power
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each constituent plane wave :math:`H=E/\eta`; its axial flux is reduced
by :math:`\cos\theta_m`.  Integrating the standing transverse pattern gives
:math:`\boxed{P_z=|a_m|^2\cos\theta_m/(2\eta)}` under the book's modal
normalization.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-8-1-1-result

   \boxed{P_z=|a_m|^2\cos\theta_m/(2\eta)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-8-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 8.1-2 — Multimode power

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-8-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_01_02.svg
   :alt: Illustrated calculation map for Exercise 8.1-2, Multimode power
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Insert the modal sum in the Poynting integral.  Orthogonality makes every
cross integral zero, leaving
:math:`\boxed{P_z=\sum_m|a_m|^2\cos\theta_m/(2\eta)}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-8-1-2-result

   \boxed{P_z=\sum_m|a_m|^2\cos\theta_m/(2\eta)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-8-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 8.2-1 — Slab confinement

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-8-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_02_01.svg
   :alt: Illustrated calculation map for Exercise 8.2-1, Slab confinement
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Integrate the sinusoidal core field and two exponential tails.  With
:math:`u=k_yd/2`, :math:`w=\gamma d/2`,
:math:`\Gamma=[1+\cos^2u/(2w(1/2+\sin2u/(4u)))]^{-1}` for an even TE mode.
The fundamental has the smallest :math:`u`, slowest evanescent leakage, and
therefore the largest confinement.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-8-2-1-result

   \Gamma=[1+\cos^2u/(2w(1/2+\sin2u/(4u)))]^{-1}


**Step 5 — Check.**  Equation :eq:`fop-exercise-8-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 8.2-2 — Asymmetric slab

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-8-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_02_02.svg
   :alt: Illustrated calculation map for Exercise 8.2-2, Asymmetric slab
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The stricter substrate interface sets
:math:`\sin\theta_{max}=\sqrt{1-(n_2/n_1)^2}` and
:math:`\mathrm{NA}=\sqrt{n_1^2-n_2^2}`.  Round-trip phase requires
:math:`2k_0n_1d\sin\theta-\phi_{12}-\phi_{13}=2\pi m`; for many modes,
:math:`M\simeq(2d/\lambda_0)\sqrt{n_1^2-n_2^2}` plus the endpoint mode.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-8-2-2-result

   2k_0n_1d\sin\theta-\phi_{12}-\phi_{13}=2\pi m


**Step 5 — Check.**  Equation :eq:`fop-exercise-8-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.1-3 — Mirror-guide field

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

One exponential cannot vanish at both mirrors unless its amplitude is zero.
For two counter-inclined waves, imposing both zeros selects
:math:`k_y=m\pi/d`, equal :math:`\beta`, and relative sign determined by
parity; the statement's incompatible sign/parity choice is why the proposed
sum fails outside the matching sine/cosine family.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-1-3-result

   k_y=m\pi/d


**Check.**  Equation :eq:`fop-problem-8-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 8.1-4 — Mirror-guide dispersion

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`m_{max}=\lfloor2d/\lambda_0\rfloor=31` for each TE/TM family (with the
TEM endpoint counted by convention).  Since
:math:`v_{gm}=c\sqrt{1-(m\lambda_0/2d)^2}`, the fastest mode has :math:`c`, the
slowest :math:`0.19325c`; over 1 m the pulse spread is
:math:`\boxed{13.93\ \mathrm{ns}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-1-4-result

   \boxed{13.93\ \mathrm{ns}}


**Check.**  Equation :eq:`fop-problem-8-1-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-3 — Film in index-1.4 cladding

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\theta_c=\sin^{-1}(1.4/1.6)=61.05^\circ`, its complement is
:math:`28.95^\circ`, and :math:`\mathrm{NA}=0.77460` gives air acceptance
:math:`50.77^\circ`.  The normalized half-thickness is :math:`V=5.594`, so
there are four TE modes.  Solving :math:`u\tan u=\sqrt{V^2-u^2}` for TE0 gives
:math:`u=1.33063`, bounce angle :math:`6.612^\circ`, and
:math:`v_g\simeq(c/n_1)\cos\theta=\boxed{1.861\times10^8\ \mathrm{m/s}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-3-result

   v_g\simeq(c/n_1)\cos\theta=\boxed{1.861\times10^8\ \mathrm{m/s}}


**Check.**  Equation :eq:`fop-problem-8-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-4 — Film suspended in air

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Now :math:`\theta_c=38.68^\circ`, complement :math:`51.32^\circ`, formal
:math:`\mathrm{NA}=1.249` (air acceptance saturates at 90 degrees), and
:math:`V=9.020`, giving six TE modes.  TE0 has
:math:`u=1.41345`, :math:`\theta=7.026^\circ`, and
:math:`v_g=1.860\times10^8\ \mathrm{m/s}`; lower cladding index mainly adds
higher modes and confinement.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-4-result

   v_g=1.860\times10^8\ \mathrm{m/s}


**Check.**  Equation :eq:`fop-problem-8-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-5 — TE0 field and confinement

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Boundary continuity gives :math:`B=A\cos u\,e^{\gamma d/2}` for the outer
exponentials.  For the stated film, :math:`V=0.44812`,
:math:`u=0.41083`, :math:`w=0.17896`; integrating the three regions gives
:math:`\boxed{\Gamma=0.2871}` (28.7% of modal power in the core).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-5-result

   \boxed{\Gamma=0.2871}


**Check.**  Equation :eq:`fop-problem-8-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-6 — Maxwell derivation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`E_x=u(y)e^{-j\beta z}`,
:math:`H_y=-\beta E_x/(\omega\mu)` and
:math:`H_z=-j u'e^{-j\beta z}/(\omega\mu)` up to time-sign convention.
Continuity of :math:`E_x,H_z` gives continuity of :math:`u,u'`, producing
:math:`u\tan u=w` (even) or :math:`-u\cot u=w` (odd), with
:math:`u^2+w^2=V^2`—the ray phase/self-consistency equation.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-6-result

   u^2+w^2=V^2


**Check.**  Equation :eq:`fop-problem-8-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-7 — Single-mode thickness

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

TE1 cutoff is :math:`V=\pi/2`, hence
:math:`\boxed{d_{max}=\lambda_0/[2\sqrt{n_1^2-n_2^2}]=1.889\ \mathrm{\mu m}}`.
At 0.85 micrometres the normalized frequency is 1.529 times larger and the
same slab carries :math:`\boxed{2}` TE modes.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-7-result

   \boxed{2}


**Check.**  Equation :eq:`fop-problem-8-2-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.2-8 — Cutoff approximation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At cutoff the external decay is zero and :math:`k_yd=m\pi`; with
:math:`k_y^2=k_0^2(n_1^2-n_2^2)\simeq2k_0^2n_1\Delta n`, rearrangement gives
:math:`\boxed{\lambda_{0,c}^2\simeq8n_1\Delta n\,d^2/m^2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-8-result

   \boxed{\lambda_{0,c}^2\simeq8n_1\Delta n\,d^2/m^2}


**Check.**  Equation :eq:`fop-problem-8-2-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 8.2-9 — TM modes

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

TM boundary continuity replaces the TE reflection phase by
:math:`\phi_{TM}=2\tan^{-1}[(n_1^2/n_2^2)
\sqrt{\sin^2\theta_c-\sin^2\theta}/\sin\theta]`.  Insert it in
:math:`2k_0n_1d\sin\theta-2\phi_{TM}=2\pi m`; plotting both sides for the
given parameters counts the intersections and supplies the TM bounce angles.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-2-9-result

   2k_0n_1d\sin\theta-2\phi_{TM}=2\pi m


**Check.**  Equation :eq:`fop-problem-8-2-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 8.3-1 — Rectangular-guide mode count

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With area :math:`A=10^{-2}\ \mathrm{mm^2}` and NA 0.1, the high-frequency
count is :math:`\boxed{M_{TE}(\nu)\simeq A\pi(\mathrm{NA}\,\nu/c)^2/4}`
(adjust the factor for both polarizations).  Plotting this quadratic staircase
against frequency gives the 2-D analogue of the slab's linear count.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-3-1-result

   \boxed{M_{TE}(\nu)\simeq A\pi(\mathrm{NA}\,\nu/c)^2/4}


**Check.**  Equation :eq:`fop-problem-8-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 8.4-1 — Two-slab coupler

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Normalize the TE0 field from Problem 8.2-5 and evaluate the overlap in
Eq. (8.5-6); only the exponentially decaying tail of one guide overlaps the
other core, so :math:`\kappa` is exponentially sensitive to the 0.5-micrometre
edge gap.  After numerical quadrature, choose
:math:`\boxed{L_{3dB}=\pi/(4|\kappa|)}`; this is the reproducible result even
when field normalization is changed.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-8-4-1-result

   \boxed{L_{3dB}=\pi/(4|\kappa|)}


**Check.**  Equation :eq:`fop-problem-8-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.
