Chapter 19: Acousto-Optics
===========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 19.

In-text exercises
-----------------

Exercise 19.2-1 — Modulator parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-19-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_19_02_01.svg
   :alt: Illustrated calculation map for Exercise 19.2-1, Modulator parameters
   :align: center
   :width: 95%

   **Figure 107 — Exercise 19.2-1: Modulator parameters.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use the internal optical wavelength :math:`\lambda=\lambda _0/n`,
:math:`\sin\theta_B=\lambda f/(2v_s)`, and :math:`B=v_s\delta\theta/\lambda`
(or :math:`B=v_s/D`).  The two designs give

.. math::
   :label: fop-exercise-19-2-1-eq-1

   \boxed{\theta_{B1}=0.1035^\circ,\quad B_1=13.84\ {\rm MHz}},
   \qquad
   \boxed{\theta_{B2}=2.877^\circ,\quad B_2=2.20\ {\rm MHz}}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-19-2-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 19.2-2 — Scanner parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-19-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_19_02_02.svg
   :alt: Illustrated calculation map for Exercise 19.2-2, Scanner parameters
   :align: center
   :width: 95%

   **Figure 108 — Exercise 19.2-2: Scanner parameters.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Here :math:`N=BT=D B/v_s` and
:math:`\Delta\theta=(\lambda_0/n)B/v_s`.  With :math:`B=20` MHz, fused
quartz therefore needs :math:`\boxed{D=30.0\ \mathrm{mm}}` and scans
:math:`\boxed{1.445\ \mathrm{mrad}=0.0828^\circ}`.  Flint glass needs only
:math:`15.5` mm for the same 100 spots and scans :math:`2.797` mrad; slower
sound gives both a smaller aperture and a larger scan.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-19-2-2-result

   \boxed{1.445\ \mathrm{mrad}=0.0828^\circ}


**Step 5 — Check.**  Equation :eq:`fop-exercise-19-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 19.2-3 — Filter resolving power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-19-2-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_19_02_03.svg
   :alt: Illustrated calculation map for Exercise 19.2-3, Filter resolving power
   :align: center
   :width: 95%

   **Figure 109 — Exercise 19.2-3: Filter resolving power.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiate :math:`\sin\theta=\lambda f/(2v_s)` at fixed angle:
:math:`|\Delta\lambda|/\lambda=|\Delta f|/f`.  A finite interaction time
:math:`T` resolves acoustic frequencies no closer than :math:`1/T`; hence
:math:`\boxed{\lambda/\Delta\lambda=fT}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-19-2-3-result

   \boxed{\lambda/\Delta\lambda=fT}


**Step 5 — Check.**  Equation :eq:`fop-exercise-19-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 19.3-1 — Transverse strain in a cubic crystal
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-19-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_19_03_01.svg
   :alt: Illustrated calculation map for Exercise 19.3-1, Transverse strain in a cubic crystal
   :align: center
   :width: 95%

   **Figure 110 — Exercise 19.3-1: Transverse strain in a cubic crystal.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The shear wave has only :math:`s_{13}=s_{31}=S`.  The impermeability block in
the :math:`x`--:math:`z` plane is
:math:`\bigl[\begin{smallmatrix}n^{-2}&p_{44}S\\p_{44}S&n^{-2}\end{smallmatrix}\bigr]`.
Its eigenvectors are at :math:`\pm45^\circ`, with eigenvalues
:math:`n^{-2}\pm p_{44}S`; the unchanged :math:`y` eigenvalue is
:math:`n^{-2}`.  Thus the crystal is biaxial and, to first order,
:math:`\boxed{n_\pm\simeq n\mp n^3p_{44}S/2,\ n_y=n}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-19-3-1-result

   \boxed{n_\pm\simeq n\mp n^3p_{44}S/2,\ n_y=n}


**Step 5 — Check.**  Equation :eq:`fop-exercise-19-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 19.1-1 — Four periodic structures

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

A traveling acoustic grating supplies :math:`(\mathbf q,\Omega)`, so the two
Bragg choices have :math:`\mathbf k_r=\mathbf k\pm\mathbf q` and optical
frequency :math:`\omega_r=\omega\pm\Omega`.  A standing acoustic wave is the
sum of both traveling gratings and produces both shifts.  A static sinusoidal
index grating supplies :math:`\pm\mathbf q` but zero frequency, while a static
layered lattice supplies reciprocal vectors :math:`m\mathbf q` and elastic
diffraction orders with no optical frequency shift.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-1-1-result

   \omega_r=\omega\pm\Omega


**Check.**  Equation :eq:`fop-problem-19-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 19.1-2 — Bragg scattering integral

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At exact phase matching the source phase cancels the Green-function phase, so
the far-field amplitude is proportional to source volume :math:`V=AD`.  Dividing
the scattered flux by incident flux gives
:math:`R=\sin^2(\kappa D)` in the coupled-wave solution and
:math:`\boxed{R\simeq(\kappa D)^2}` in the first-Born limit.  With the chapter's
photoelastic perturbation, :math:`\kappa=\pi\Delta n/\lambda`; this is the
small-signal expansion of Eq. (19.1-22).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-1-2-result

   \boxed{R\simeq(\kappa D)^2}


**Check.**  Equation :eq:`fop-problem-19-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 19.1-3 — Raman--Nath width limit

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The thin-grating condition is that diffraction separation accumulated across
the sound width remain below one acoustic period.  Using diffraction angle
:math:`\lambda/\Lambda` gives the Klein--Cook parameter
:math:`Q=2\pi\lambda D_s/\Lambda^2`; Raman--Nath operation requires
:math:`Q\lesssim1`, or
:math:`\boxed{D_s\lesssim\Lambda^2/(2\pi\lambda)}` (order-one conventions move
the numerical boundary but not the scaling).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-1-3-result

   \boxed{D_s\lesssim\Lambda^2/(2\pi\lambda)}


**Check.**  Equation :eq:`fop-problem-19-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 19.1-4 — Combined lithium-niobate modulation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\Lambda=v_s/f=2.467\ \mu\mathrm m` and
:math:`\lambda=633/2.3=275.2` nm, so
:math:`\boxed{\theta_B=3.198^\circ}`.  Electro-optic phase modulation produces
carrier-centered sidebands :math:`\omega+m\Omega`; reflection translates every
one by :math:`\pm\Omega`.  For a short microwave pulse the electro-optic
sidebands appear immediately, whereas the delayed acoustic packet contributes
only after its sound transit time through the illuminated region.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-1-4-result

   \boxed{\theta_B=3.198^\circ}


**Check.**  Equation :eq:`fop-problem-19-1-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 19.2-4 — Producing sinusoidal amplitude modulation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Split the input equally and send the branches to oppositely oriented Bragg
cells.  Their first orders are :math:`(A/2)e^{j(\omega+\Omega)t}` and
:math:`(A/2)e^{j(\omega-\Omega)t}`.  Recombine them in phase:
:math:`\boxed{U_o=A\cos(\Omega t)e^{j\omega t}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-2-4-result

   \boxed{U_o=A\cos(\Omega t)e^{j\omega t}}


**Check.**  Equation :eq:`fop-problem-19-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 19.2-5 — Deflection without frequency translation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Cascade two equal Bragg cells with acoustic wavevectors chosen so both
deflections add, but drive one on its upshift order and the other on its
downshift order.  The net wavevector changes by the desired two grating
momenta while :math:`(+\Omega)+(-\Omega)=0`; spatially filter the selected
first-order path after each cell.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-2-5-result

   (+\Omega)+(-\Omega)=0


**Check.**  Equation :eq:`fop-problem-19-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 19.3-2 — Front Bragg diffraction

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The incident extraordinary and reflected ordinary waves obey
:math:`q=k_o+k_e`; hence
:math:`\boxed{\Lambda=\lambda_0/(n_o+n_e)}` and the reflected wave is polarized
ordinary, perpendicular to the optic-axis plane.  With the stated indexes and
:math:`\lambda_0=633` nm,
:math:`\boxed{\Lambda=141.1\ \mathrm{nm}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-19-3-2-result

   \boxed{\Lambda=141.1\ \mathrm{nm}}


**Check.**  Equation :eq:`fop-problem-19-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.
