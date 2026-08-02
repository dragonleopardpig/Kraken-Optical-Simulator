Chapter 5: Electromagnetic Optics
=================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 5.

In-text exercise
----------------

Exercise 5.5-1 — Dilute absorbing impurities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-5-5-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_05_05_01.svg
   :alt: Illustrated calculation map for Exercise 5.5-1, Dilute absorbing impurities
   :align: center
   :width: 95%

   **Figure 47 — Exercise 5.5-1: Dilute absorbing impurities.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The host has :math:`\epsilon_r=n_0^2`; adding dilute susceptibility gives
:math:`\epsilon_r=n_0^2+\chi'+j\chi''`.  Expanding
:math:`\tilde n=\sqrt{\epsilon_r}` to first order gives
:math:`n\simeq n_0+\chi'/(2n_0)` and extinction part
:math:`\kappa\simeq\chi''/(2n_0)`.  Therefore
:math:`\boxed{\alpha=2k_0\kappa=k_0\chi''/n_0}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-5-5-1-result

   \boxed{\alpha=2k_0\kappa=k_0\chi''/n_0}


**Step 5 — Check.**  Equation :eq:`fop-exercise-5-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiating the proposed solution and substituting it into the original differential equation verifies the functional form.

.. rubric:: Problem 5.1-1 — Gaussian electromagnetic pulse

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

This is an :math:`x`-polarized Gaussian-envelope carrier traveling in
:math:`+z` at :math:`c_0`.  Maxwell's plane-wave relation gives
:math:`\boxed{\mathbf H=\hat{\mathbf y},f(t-z/c_0)/\eta_0}`; the Poynting
vector points along :math:`+z`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-1-1-result

   \boxed{\mathbf H=\hat{\mathbf y},f(t-z/c_0)/\eta_0}


**Check.**  Equation :eq:`fop-problem-5-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 5.2-1 — Constitutive-law classification

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

(a) The spatial derivative makes the medium linear, homogeneous, temporally
nondispersive but spatially dispersive.  (b) :math:`P+aP^2=\epsilon_0\chi E`
is nonlinear, instantaneous, homogeneous, and local.  (c) time derivatives
make it linear, homogeneous, local, and temporally dispersive.  (d) the
position-dependent coefficient is linear, instantaneous, local, and
inhomogeneous.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-2-1-result

   P+aP^2=\epsilon_0\chi E


**Check.**  Equation :eq:`fop-problem-5-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 5.3-1 — Traveling standing wave

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The Helmholtz equation requires :math:`2\beta^2=k_0^2`, so
:math:`\boxed{\beta=k_0/\sqrt2}`.  From
:math:`\mathbf H=(j\omega\mu_0)^{-1}\nabla\times\mathbf E`, obtain the
:math:`y` and :math:`z` magnetic components.  Expanding
:math:`\sin\beta y` into exponentials shows two equal TEM waves with
:math:`\mathbf k_\pm=(0,\pm\beta,\beta)`, i.e. at :math:`\pm45^\circ` in the
:math:`y-z` plane.  Their transverse power cancels and mean power flows in
:math:`+z`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-3-1-result

   \boxed{\beta=k_0/\sqrt2}


**Check.**  Equation :eq:`fop-problem-5-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 5.4-1 — Focused electric-field strength

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For uniform area :math:`10^{-8}\ \mathrm{m^2}`, :math:`I=10^8`
:math:`\mathrm{W,m^{-2}}` and
:math:`E_0=\sqrt{2\eta_0I}=\boxed{2.75\times10^5\ \mathrm{V/m}}`.
For the Gaussian, :math:`I(0)=2P/(\pi W_0^2)=6.37\times10^7`
:math:`\mathrm{W,m^{-2}}`, hence
:math:`\boxed{E_0=2.19\times10^5\ \mathrm{V/m}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-4-1-result

   \boxed{E_0=2.19\times10^5\ \mathrm{V/m}}


**Check.**  Equation :eq:`fop-problem-5-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 5.5-2 — Modulation in dispersion

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Resolve the input into carrier and two sidebands.  After distance :math:`z`,

.. math::
   :label: fop-problem-5-5-2-eq-1

   A_z=e^{j2\pi\nu_0t-j\beta_0z}
   \left[1+\frac m2e^{j2\pi f_mt-j(\beta_2-\beta_0)z}
   +\frac m2e^{-j2\pi f_mt-j(\beta_1-\beta_0)z}\right].

The bracket is purely real apart from a common phase when
:math:`(\beta_2+\beta_1-2\beta_0)z=2\pi q`; at those distances the wave is
again pure AM (with a dispersion-dependent RF phase delay).

**Check.**  Equation :eq:`fop-problem-5-5-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 5.6-1 — Sellmeier dispersion

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`n^2=1+\sum_i A_i\lambda^2/(\lambda^2-\lambda_i^2)`, differentiate
analytically and use
:math:`\boxed{N=n-\lambda,dn/d\lambda}` and
:math:`\boxed{D_\lambda=-(\lambda/c_0)d^2n/d\lambda^2}`.  Evaluating these
expressions with the table coefficients reproduces the silica curves and,
with the three listed GaAs terms, the GaAs curves.  GaAs has much larger
index and stronger, resonance-proximate dispersion; silica has a broad
low-dispersion telecommunications region.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-6-1-result

   \boxed{D_\lambda=-(\lambda/c_0)d^2n/d\lambda^2}


**Check.**  Equation :eq:`fop-problem-5-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 5.6-2 — Air dispersion from three measurements

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`\lambda` in micrometres, the exact quadratic through the data is
:math:`n-1=-2.0000\times10^{-5}\lambda^2+2.5400\times10^{-5}\lambda
+2.59448\times10^{-4}`.  Then
:math:`v_g=c_0/[n-\lambda n']`; at 0.76, 0.81, and 0.86 micrometres it is
:math:`2.9971124`, :math:`2.9971077`, and :math:`2.9971027`
:math:`\times10^8\ \mathrm{m/s}`.  The constant curvature gives
:math:`D_\lambda=0.1014`, 0.1081, and 0.1147
:math:`\mathrm{ps/(km,nm)}`, hundreds of times smaller than ordinary silica
fibre dispersion.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-6-2-result

   D_\lambda=0.1014


**Check.**  Equation :eq:`fop-problem-5-6-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 5.6-3 — Drude phase/group velocities

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For the lossless Drude law :math:`k^2=(\omega^2-\omega_p^2)/c_0^2`,
:math:`v_p=\omega/k` and
:math:`v_g=d\omega/dk=c_0^2k/\omega`.  Therefore
:math:`\boxed{v_pv_g=c_0^2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-5-6-3-result

   \boxed{v_pv_g=c_0^2}


**Check.**  Equation :eq:`fop-problem-5-6-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.
