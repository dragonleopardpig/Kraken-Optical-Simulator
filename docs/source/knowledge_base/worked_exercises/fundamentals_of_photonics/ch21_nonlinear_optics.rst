Chapter 21: Nonlinear Optics
============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 21.

In-text exercises
-----------------

Exercise 21.1-1 — Intensity needed for nonlinearity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_01_01.svg
   :alt: Illustrated calculation map for Exercise 21.1-1, Intensity needed for nonlinearity
   :align: center
   :width: 95%

   **Figure 113 — Exercise 21.1-1: Intensity needed for nonlinearity.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Since :math:`P_L=\epsilon_0(n^2-1)E`, :math:`P_2=2dE^2`,
:math:`P_3=4\chi^{(3)}E^3`, and :math:`I=E^2/(\eta_0/n)`, setting the requested
ratios to 0.01 gives

.. math::
   :label: fop-exercise-21-1-1-eq-1

   \boxed{I_{\rm ADP}=2.64\times10^{13}\ \mathrm{W/cm^2}},\qquad
   \boxed{I_{\rm CS_2}=3.33\times10^{11}\ \mathrm{W/cm^2}}.

The enormous values explain why focused laser fields are normally required.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-21-1-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.2-1 — Non-collinear type-II SHG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_02_01.svg
   :alt: Illustrated calculation map for Exercise 21.2-1, Non-collinear type-II SHG
   :align: center
   :width: 95%

   **Figure 114 — Exercise 21.2-1: Non-collinear type-II SHG.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`n_e(\vartheta)^{-2}=\cos^2\vartheta/n_e^2+
\sin^2\vartheta/n_o^2`, solve

.. math::
   :label: fop-exercise-21-2-1-eq-1

   n_o(\omega)\sin\theta_1=n_e(\theta+\theta_2,\omega)\sin\theta_2,
   \quad
   n_o(\omega)\cos\theta_1+n_e(\theta+\theta_2,\omega)\cos\theta_2
   =2n_e(\theta,2\omega).

Sellmeier values for KDP at 1.06 and 0.53 micrometres inserted in these two
equations give the complete one-parameter family; a root finder over
:math:`(\theta,\theta_1,\theta_2)` reproduces it.  The collinear endpoint is
:math:`\boxed{\theta\simeq41^\circ,\ \theta_1=\theta_2=0}`, and continuation
from that root gives the non-collinear branches.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-21-2-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.3-1 — DC-field-induced Kerr effect
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_03_01.svg
   :alt: Illustrated calculation map for Exercise 21.3-1, DC-field-induced Kerr effect
   :align: center
   :width: 95%

   **Figure 115 — Exercise 21.3-1: DC-field-induced Kerr effect.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Expanding :math:`4\chi^{(3)}[E(0)+E(\omega)]^3`, the terms at :math:`\omega`
are :math:`12\chi^{(3)}E^2(0)E(\omega)`.  Equating this to
:math:`2n\epsilon_0\Delta nE(\omega)` gives
:math:`\Delta n=6\chi^{(3)}E^2(0)/(n\epsilon_0)=-s n^3E^2(0)/2`, hence
:math:`\boxed{s=-12\chi^{(3)}/(\epsilon_0n^4)}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-3-1-result

   \boxed{s=-12\chi^{(3)}/(\epsilon_0n^4)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 21.3-2 — Optical Kerr lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-3-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_03_02.svg
   :alt: Illustrated calculation map for Exercise 21.3-2, Optical Kerr lens
   :align: center
   :width: 95%

   **Figure 116 — Exercise 21.3-2: Optical Kerr lens.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Near the beam axis,
:math:`n(I)d\simeq\mathrm{constant}-n_2I_0d(x^2+y^2)/W^2`.  Matching its
phase to :math:`\exp[jk_0(x^2+y^2)/(2f)]` gives
:math:`\boxed{f=W^2/(2n_2I_0d)}`; the sign follows the sign convention for
propagation and :math:`n_2`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-3-2-result

   \boxed{f=W^2/(2n_2I_0d)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.3-3 — Self- and cross-phase modulation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-3-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_03_03.svg
   :alt: Illustrated calculation map for Exercise 21.3-3, Self- and cross-phase modulation
   :align: center
   :width: 95%

   **Figure 117 — Exercise 21.3-3: Self- and cross-phase modulation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Collecting all cubic products at :math:`\omega_1` gives a self term
:math:`|E_1|^2E_1` and two permutations for each other wave.  Converting field
strength to intensity yields
:math:`\boxed{\Delta n_1=n_2(I_1+2I_2+2I_3)}`.  Therefore wave 1 propagates
at :math:`c_0/(n+\Delta n_1)`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-3-3-result

   \boxed{\Delta n_1=n_2(I_1+2I_2+2I_3)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 21.4-1 — Degenerate three-wave mixing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_01.svg
   :alt: Illustrated calculation map for Exercise 21.4-1, Degenerate three-wave mixing
   :align: center
   :width: 95%

   **Figure 118 — Exercise 21.4-1: Degenerate three-wave mixing.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Put :math:`E=E_1e^{j\omega t}+E_3e^{j2\omega t}+\mathrm{c.c.}` in
:math:`P_{NL}=2dE^2`.  Terms at :math:`\omega` occur twice, whereas the
:math:`2\omega` product :math:`E_1E_1` occurs once.  Applying
:math:`S=\mu_0\partial_t^2P_{NL}` gives
:math:`\boxed{S_1=2\mu_0\omega^2dE_3E_1^*,\ S_3=4\mu_0\omega^2dE_1^2}`,
equivalent to Eqs. (21.4-14)--(21.4-16).

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-1-result

   \boxed{S_1=2\mu_0\omega^2dE_3E_1^*,\ S_3=4\mu_0\omega^2dE_1^2}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.4-2 — Manley--Rowe relation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_02.svg
   :alt: Illustrated calculation map for Exercise 21.4-2, Manley–Rowe relation
   :align: center
   :width: 95%

   **Figure 119 — Exercise 21.4-2: Manley–Rowe relation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Multiply each coupled equation by its conjugate amplitude and add the complex
conjugate.  The common interaction term then gives
:math:`\boxed{d|a_1|^2/dz=d|a_2|^2/dz=-d|a_3|^2/dz}`.  These are photon-flux
changes: one photon from each lower-frequency wave makes one sum-frequency
photon.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-2-result

   \boxed{d|a_1|^2/dz=d|a_2|^2/dz=-d|a_3|^2/dz}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 21.4-3 — Energy conservation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_03.svg
   :alt: Illustrated calculation map for Exercise 21.4-3, Energy conservation
   :align: center
   :width: 95%

   **Figure 120 — Exercise 21.4-3: Energy conservation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Weight the preceding derivatives by :math:`\hbar\omega_q`.  Because
:math:`\omega_1+\omega_2=\omega_3`, their sum vanishes:
:math:`\boxed{d[\hbar\sum_q\omega_q|a_q|^2]/dz=0}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-3-result

   \boxed{d[\hbar\sum_q\omega_q|a_q|^2]/dz=0}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 21.4-4 — SHG envelope equations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_04.svg
   :alt: Illustrated calculation map for Exercise 21.4-4, SHG envelope equations
   :align: center
   :width: 95%

   **Figure 121 — Exercise 21.4-4: SHG envelope equations.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Substitute :math:`E_q=a_q(z)e^{-jk_qz}` in the two Helmholtz equations and
use :math:`|a_q''|\ll|k_qa_q'|`.  Division by :math:`-2jk_q` gives
:math:`da_1/dz=-j2g a_1^*a_3e^{j\Delta kz}` and
:math:`da_3/dz=-jg a_1^2e^{-j\Delta kz}`, with the chapter normalization of
:math:`g`; the factor two occurs only in the fundamental equation.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-4-result

   da_3/dz=-jg a_1^2e^{-j\Delta kz}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiating the proposed solution and substituting it into the original differential equation verifies the functional form.

Exercise 21.4-5 — Infrared up-conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-5-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_05.svg
   :alt: Illustrated calculation map for Exercise 21.4-5, Infrared up-conversion
   :align: center
   :width: 95%

   **Figure 122 — Exercise 21.4-5: Infrared up-conversion.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Frequency addition gives
:math:`\lambda_3^{-1}=\lambda_1^{-1}+\lambda_2^{-1}`, hence
:math:`\boxed{\lambda_3=0.9636\ \mu\mathrm m}`.  With the undepleted-pump
formula and the given :math:`d^2/n^3`, area, power, and 1-cm length,
:math:`\boxed{\eta_{\rm OFC}=5.31\times10^{-3}}` (0.531%).

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-5-result

   \boxed{\eta_{\rm OFC}=5.31\times10^{-3}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.4-6 — KTP parametric amplifier
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-4-6-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_04_06.svg
   :alt: Illustrated calculation map for Exercise 21.4-6, KTP parametric amplifier
   :align: center
   :width: 95%

   **Figure 123 — Exercise 21.4-6: KTP parametric amplifier.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Difference-frequency conservation gives :math:`\boxed{\lambda_i=1.852\
\mu\mathrm m}`.  From Eq. (21.4-47),
:math:`C=[2\omega_s\omega_i(\eta_0/n)^3d^2]^{1/2}=
\boxed{8.99\times10^{-5}}` in its stated SI normalization.  A 3-dB power gain
requires :math:`\cosh^2(C L\sqrt{P/A})=2`, so
:math:`\boxed{P/A=2.40\times10^{11}\ \mathrm{W/m^2}}`; for example, a
1-W pump focused to :math:`4.16\times10^{-12}\ \mathrm{m^2}` satisfies it.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-4-6-result

   \boxed{P/A=2.40\times10^{11}\ \mathrm{W/m^2}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-4-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.5-1 — Undepleted-pump THG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-5-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_05_01.svg
   :alt: Illustrated calculation map for Exercise 21.5-1, Undepleted-pump THG
   :align: center
   :width: 95%

   **Figure 124 — Exercise 21.5-1: Undepleted-pump THG.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Retaining the cubic source terms at :math:`\omega` and :math:`3\omega`, then
applying SVEA, gives
:math:`da_3/dz=-jg a_1^3e^{-j\Delta kz}` when :math:`a_1` is undepleted, with
:math:`\boxed{g=3\chi^{(3)}\omega_3(\eta_1^3\eta_3)^{1/2}/2}` under the
chapter's flux-amplitude normalization.  Integration adds the familiar
:math:`L\,\mathrm{sinc}(\Delta kL/2)` phase-matching factor.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-5-1-result

   \boxed{g=3\chi^{(3)}\omega_3(\eta_1^3\eta_3)^{1/2}/2}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 21.7-1 — Anharmonic oscillator polarization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-7-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_07_01.svg
   :alt: Illustrated calculation map for Exercise 21.7-1, Anharmonic oscillator polarization
   :align: center
   :width: 95%

   **Figure 125 — Exercise 21.7-1: Anharmonic oscillator polarization.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Start with :math:`m\ddot x+m\gamma\dot x+Kx+K_2x^2=-eE` and set
:math:`P=-Nex`.  Multiplication by :math:`-Ne/m` gives Eq. (21.7-8), with
:math:`\boxed{\omega_0^2=K/m,\ \chi_0=Ne^2/(\epsilon_0m\omega_0^2),\
b=K_2/(e^3N^2)}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-7-1-result

   \boxed{\omega_0^2=K/m,\ \chi_0=Ne^2/(\epsilon_0m\omega_0^2),\
   b=K_2/(e^3N^2)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-7-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiating the proposed solution and substituting it into the original differential equation verifies the functional form.

Exercise 21.7-2 — Miller's rule
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-21-7-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_21_07_02.svg
   :alt: Illustrated calculation map for Exercise 21.7-2, Miller's rule
   :align: center
   :width: 95%

   **Figure 126 — Exercise 21.7-2: Miller's rule.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The first iteration supplies :math:`P_1(\omega)=\epsilon_0\chi(\omega)E(\omega)`.
Driving the linear oscillator at :math:`\omega_3=\omega_1+\omega_2` with
:math:`-bP_1^2` supplies one susceptibility at each of the three frequencies:
:math:`\boxed{d(\omega_3;\omega_1,\omega_2)=C_M
\chi(\omega_3)\chi(\omega_1)\chi(\omega_2)}`, where the material constant
:math:`C_M` follows from :math:`b,\chi_0`, proving Miller's rule.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-21-7-2-result

   \boxed{d(\omega_3;\omega_1,\omega_2)=C_M
   \chi(\omega_3)\chi(\omega_1)\chi(\omega_2)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-21-7-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiating the proposed solution and substituting it into the original differential equation verifies the functional form.

Problem 21.2-2 — Up-conversion power exchange
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`1/\lambda_p=1/0.5-1/1.3` gives
:math:`\boxed{\lambda_p=0.8125\ \mu\mathrm m}`.  One lost 1.3-micrometre photon
creates one 0.5-micrometre photon while consuming one pump photon.  Thus a
1-mW signal loss gives :math:`\boxed{2.60\ \mathrm{mW}}` at 0.5 micrometres
and :math:`\boxed{1.60\ \mathrm{mW}}` pump loss.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-2-result

   \boxed{1.60\ \mathrm{mW}}


**Check.**  Equation :eq:`fop-problem-21-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.2-3 — Collinear type-II KDP matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each trial :math:`\theta`, evaluate the extraordinary index and solve
:math:`n_o(\omega)+n_e(\theta,\omega)=2n_o(2\omega)` for o-e-o, or replace
the right side by :math:`2n_e(\theta,2\omega)` for o-e-e.  Bracketing
:math:`0<\theta<90^\circ` with the Table 5.5-1 Sellmeier equations gives the
requested cut angles; substitution back into the equation is the residual
check (a configuration with no sign change has no physical cut angle).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-3-result

   n_o(\omega)+n_e(\theta,\omega)=2n_o(2\omega)


**Check.**  Equation :eq:`fop-problem-21-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.2-4 — Degenerate KDP down-conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Try the allowed type-I condition :math:`n_e(\theta,0.6)=n_o(1.2)`.  The given
indexes bracket 1.490, and
:math:`n_e(\theta)^{-2}=\cos^2\theta/1.468^2+sin^2\theta/1.509^2` gives
:math:`\boxed{\theta=47.2^\circ}`.  The 0.6-micrometre pump is extraordinary;
both collinear 1.2-micrometre daughter waves are ordinary.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-4-result

   \boxed{\theta=47.2^\circ}


**Check.**  Equation :eq:`fop-problem-21-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.2-5 — Linear-dispersion matching obstruction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`n(\lambda)=n_0-\beta\lambda` and
:math:`1/\lambda_3=1/\lambda_1+1/\lambda_2`, the :math:`n_0` terms satisfy
energy conservation but the three :math:`-\beta` contributions leave a
nonzero constant in :math:`k_1+k_2-k_3`; co-propagating exact matching is
impossible for :math:`\beta\ne0`.  Reversing one wave changes a wavevector
sign and can supply a root, so counter-propagating matching is possible.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-5-result

   1/\lambda_3=1/\lambda_1+1/\lambda_2


**Check.**  Equation :eq:`fop-problem-21-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 21.2-6 — Finite-volume phase mismatch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

In the radiation integral use
:math:`|\mathbf r-\mathbf r'|\simeq r-\hat{\mathbf r}\cdot\mathbf r'`.
For a uniform rectangular source the remaining integral factorizes into
:math:`V\prod_i\mathrm{sinc}(\Delta k_iL_i/2)`.  Thus intensity contains
:math:`\prod_i\mathrm{sinc}^2(\Delta k_iL_i/2)` and the longitudinal first
zero is :math:`|\Delta k_z|=2\pi/L_z`, quantifying phase-mismatch tolerance.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-6-result

   |\Delta k_z|=2\pi/L_z


**Check.**  Equation :eq:`fop-problem-21-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.2-7 — Backward quasi-phase-matched SHG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Momentum conservation including grating vector :math:`K=2\pi/\Lambda` is
:math:`-k_{2\omega}=2k_\omega-mK`, so
:math:`\boxed{mK=2k_\omega+k_{2\omega}}`.  If dispersion is neglected,
:math:`k_{2\omega}=2k_\omega`; for :math:`m=7`,
:math:`\boxed{\Lambda/\lambda_\omega=7/4}` where :math:`\lambda_\omega` is
the fundamental wavelength in the crystal.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-2-7-result

   \boxed{\Lambda/\lambda_\omega=7/4}


**Check.**  Equation :eq:`fop-problem-21-2-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 21.3-4 — Four-wave Manley--Rowe invariants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

One elementary event destroys photons 1 and 2 and creates photons 3 and 4:
:math:`d\Phi_1=d\Phi_2=-d\Phi_3=-d\Phi_4`.  Therefore
:math:`\Phi_1-\Phi_2`, :math:`\Phi_3-\Phi_4`, and
:math:`\Phi_1+\Phi_3` are invariant; multiplying by photon energies and using
:math:`\omega_1+\omega_2=\omega_3+\omega_4` proves energy conservation.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-3-4-result

   \omega_1+\omega_2=\omega_3+\omega_4


**Check.**  Equation :eq:`fop-problem-21-3-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 21.3-5 — Spatial-soliton power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`I(x)=I_0\,\mathrm{sech}^2(x/W_0)`, integration gives
:math:`P'=\int I\,dx=2I_0W_0`.  The soliton condition has
:math:`I_0\propto W_0^{-2}`, so
:math:`\boxed{P'\propto W_0^{-1}}` (power per unit extent in the invariant
transverse direction).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-3-5-result

   \boxed{P'\propto W_0^{-1}}


**Check.**  Equation :eq:`fop-problem-21-3-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.3-6 — Light-controlled phase modulator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`n_2=3\eta_0\chi^{(3)}/(\epsilon_0n^2)=2.19\times10^{-18}`
:math:`\mathrm{m^2/W}`.  Setting :math:`k_0n_2IL=\pi` gives
:math:`I_\pi=1.24\times10^{12}\ \mathrm{W/m^2}` and, for a square
:math:`0.1`-mm beam, :math:`\boxed{P_\pi\simeq12.4\ \mathrm{kW}}` (multiply
by :math:`\pi/4` instead for a circular diameter convention).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-3-6-result

   \boxed{P_\pi\simeq12.4\ \mathrm{kW}}


**Check.**  Equation :eq:`fop-problem-21-3-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.3-7 — DC-assisted SHG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The cubic product :math:`4\chi^{(3)}[E_0+E_\omega]^3` contains a
:math:`2\omega` term proportional to :math:`E_0E_\omega^2`.  It acts like an
effective quadratic coefficient :math:`d_{\rm eff}\propto\chi^{(3)}E_0`;
conversion therefore scales as :math:`|\chi^{(3)}|^2E_0^2I_\omega L^2`
times the phase-matching sinc-squared factor.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 21.4-7 — KDP amplifier gain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The idler wavelength is :math:`0.8570` micrometres.  Equation (21.4-47) gives
:math:`C=1.295\times10^{-4}` and
:math:`\gamma=2C\sqrt I=25.90\ \mathrm{m^{-1}}` at
:math:`10^6\ \mathrm{W/cm^2}`.  Thus
:math:`\boxed{G=\cosh^2(\gamma L/2)=1.293=1.12\ \mathrm{dB}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-4-7-result

   \boxed{G=\cosh^2(\gamma L/2)=1.293=1.12\ \mathrm{dB}}


**Check.**  Equation :eq:`fop-problem-21-4-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.4-8 — Degenerate down-converter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Degeneracy combines the two signal equations into
:math:`da/dz=-j2ga^*a_pe^{j\Delta kz}` and
:math:`da_p/dz=-jga^2e^{-j\Delta kz}`.  At exact match choose phases so the
amplitudes are real; the invariants give
:math:`\Phi(z)+2\Phi_p(z)=2\Phi_p(0)` and the solution is the standard
:math:`\mathrm{sech}^2/\tanh^2` exchange.  Consequently
:math:`\Phi_p=\Phi_p(0)\mathrm{sech}^2(\kappa z)` and
:math:`\Phi=2\Phi_p(0)\tanh^2(\kappa z)`, proving both energy and photon
conservation and giving :math:`\eta=\tanh^2(\kappa L)`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-4-8-result

   \eta=\tanh^2(\kappa L)


**Check.**  Equation :eq:`fop-problem-21-4-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.4-9 — OPO threshold
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At degeneracy :math:`\lambda_s=\lambda_i=1.064` micrometres.  Requiring the
round-trip power gain to cancel two 0.98 reflectances gives
:math:`\cosh^2(C L\sqrt I)R^2=1`.  With
:math:`C=2.244\times10^{-4}`, the result is
:math:`\boxed{I_{th}=3.23\times10^4\ \mathrm{W/cm^2}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-4-9-result

   \boxed{I_{th}=3.23\times10^4\ \mathrm{W/cm^2}}


**Check.**  Equation :eq:`fop-problem-21-4-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 21.5-1 — Simultaneous SHG and SFG
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For envelopes :math:`A_1,A_2,B_1,B_2,C` at
:math:`\omega_1,\omega_2,2\omega_1,2\omega_2,\omega_1+\omega_2`, write one
SVE equation for every resonant quadratic product:
:math:`A_1^2\leftrightarrow B_1`, :math:`A_2^2\leftrightarrow B_2`, and
:math:`A_1A_2\leftrightarrow C`, plus conjugate back-action terms.  A
Runge--Kutta integration preserving
:math:`\sum\hbar\omega_q|A_q|^2` shows suppression of SHG1 as the SFG channel
draws photons from :math:`A_1`; energy-invariant error is the numerical check.

**Check.**  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

Problem 21.5-2 — Degenerate four-wave equations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Keeping resonant cubic products and exact phase matching gives
:math:`dA_1/dz=-j\kappa A_2^*A_3^2`,
:math:`dA_2/dz=-j\kappa A_1^*A_3^2`, and
:math:`dA_3/dz=-j2\kappa^*A_1A_2A_3^*`, together with self/cross-phase terms
if they are not absorbed into propagation constants.  The factor two in the
pump equation accounts for its two degenerate photons.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-5-2-result

   dA_3/dz=-j2\kappa^*A_1A_2A_3^*


**Check.**  Equation :eq:`fop-problem-21-5-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 21.6-1 — Type-II coefficient in 3m BBO
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Insert the ordinary and extraordinary unit polarization vectors in
:math:`d_{\rm eff}=\hat e_3\boldsymbol d:(\hat e_1\hat e_2)`.  Applying the
3m tensor symmetries cancels the sine terms and leaves
:math:`\boxed{d_{\rm eff}=d_{22}\cos^2\theta\cos3\phi}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-6-1-result

   \boxed{d_{\rm eff}=d_{22}\cos^2\theta\cos3\phi}


**Check.**  Equation :eq:`fop-problem-21-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 21.6-2 — Electro-optic/nonlinear tensors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`\boldsymbol\eta=\boldsymbol\epsilon^{-1}\epsilon_0`, variation of
an inverse matrix gives
:math:`\delta\eta=-\epsilon_0\epsilon^{-1}(\delta\epsilon)\epsilon^{-1}`.
Substitute the quadratic and cubic field-dependent polarization terms and
differentiate once or twice with respect to the DC field.  Component matching
gives
:math:`\boxed{r_{ijk}=-4\epsilon_0d_{ijk}/(\epsilon_{ii}\epsilon_{jj})}` and
:math:`\boxed{s_{ijkl}=-12\epsilon_0\chi^{(3)}_{ijkl}/
(\epsilon_{ii}\epsilon_{jj})}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-21-6-2-result

   \boxed{s_{ijkl}=-12\epsilon_0\chi^{(3)}_{ijkl}/
   (\epsilon_{ii}\epsilon_{jj})}


**Check.**  Equation :eq:`fop-problem-21-6-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.
