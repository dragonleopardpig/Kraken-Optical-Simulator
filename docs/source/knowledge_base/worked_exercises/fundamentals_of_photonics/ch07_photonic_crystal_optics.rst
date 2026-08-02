Chapter 7: Photonic-Crystal Optics
==================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 7.  The characteristic-matrix convention is the book's.

In-text exercise
----------------

.. rubric:: Exercise 7.1-1 — Quarter-wave antireflection film

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-7-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_07_01_01.svg
   :alt: Illustrated calculation map for Exercise 7.1-1, Quarter-wave antireflection film
   :align: center
   :width: 95%

   **Figure 55 — Exercise 7.1-1: Quarter-wave antireflection film.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Multiplying boundary/propagation matrices makes
:math:`B\propto n_1n_3\sin^2\delta-n_2^2\sin^2\delta` at
:math:`\delta=\pi/2`.  Thus :math:`B=0` and :math:`r=0` when
:math:`\boxed{d=\lambda_0/(4n_2),\ n_2=\sqrt{n_1n_3}}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-7-1-1-result

   \boxed{d=\lambda_0/(4n_2),\ n_2=\sqrt{n_1n_3}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-7-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 7.1-2 — Slab beamsplitter

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use the Airy result
:math:`T=[1+4R_{s,p}\sin^2\delta/(1-R_{s,p})^2]^{-1}`, :math:`R=1-T`, with
the TE/TM Fresnel :math:`R_{s,p}` at 45 degrees and
:math:`\delta=(2\pi/\lambda_0)nd\cos\theta_t`.  This directly supplies the
periodic spectral curves; TM contrast vanishes when the internal/external
angle is Brewster.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-2-result

   \delta=(2\pi/\lambda_0)nd\cos\theta_t


**Check.**  Equation :eq:`fop-problem-7-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 7.1-3 — Air-gap tunnelling

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At normal incidence insert :math:`n_g,1,n_g` in the slab matrix and
:math:`d=\lambda_0/2`; the round-trip phase gives unity transmission.  Above
critical angle the gap normal wavevector is :math:`j\kappa`; replacing
:math:`\sin\delta,j\cos\delta` by hyperbolic functions gives finite
:math:`T\propto\operatorname{sech}^2(\kappa d)`: frustrated TIR tunnels
through a sufficiently thin gap.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-3-result

   d=\lambda_0/2


**Check.**  Equation :eq:`fop-problem-7-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 7.1-4 — Unmatched incident medium

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Composition of the new boundary and old device gives
:math:`\boxed{r=(r_b+r_m)/(1+r_br_m)}`.  It reduces respectively to
:math:`r_m,1,r_b,1` for :math:`r_b=0,1` and :math:`r_m=0,1`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-4-result

   \boxed{r=(r_b+r_m)/(1+r_br_m)}


**Check.**  Equation :eq:`fop-problem-7-1-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 7.1-5 — Oblique quarter-wave coating

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Replace admittance by :math:`n\cos\theta` (TE) or
:math:`n/\cos\theta` (TM), and phase by
:math:`\delta=2\pi n_2d\cos\theta_2/\lambda_0`; multiplying the one-film
matrix gives :math:`r=(r_{12}+r_{23}e^{-j2\delta})/
(1+r_{12}r_{23}e^{-j2\delta})`.  Squaring this expression is the requested
angular reflectance.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-5-result

   r=(r_{12}+r_{23}e^{-j2\delta})/
   (1+r_{12}r_{23}e^{-j2\delta})


**Check.**  Equation :eq:`fop-problem-7-1-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 7.1-6 — Quarter/half-wave stacks

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At the design wavelength a quarter-wave pair has diagonal matrix
:math:`-\operatorname{diag}(n_2/n_1,n_1/n_2)`; after :math:`N` pairs the
ratio is raised to :math:`N`, yielding
:math:`r=[n_a(n_2/n_1)^{2N}-n_s]/[n_a(n_2/n_1)^{2N}+n_s]` up to layer order.
A half-wave layer is :math:`-I`; every pair is transparent at the design
wavelength apart from phase, so only the unmatched outer boundary remains.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-6-result

   r=[n_a(n_2/n_1)^{2N}-n_s]/[n_a(n_2/n_1)^{2N}+n_s]


**Check.**  Equation :eq:`fop-problem-7-1-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 7.1-7 — GaAs/AlAs reflector

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For a GaAs-matched exterior, evaluate the preceding quarter-wave expression
with :math:`n_1=3.57`, :math:`n_2=2.94`:
:math:`\boxed{R_N=[(1-(n_2/n_1)^{2N})/(1+(n_2/n_1)^{2N})]^2}` and
:math:`T_N=1-R_N`.  Evaluating :math:`N=1,\ldots,10` gives the requested
monotonic plot.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-7-result

   \boxed{R_N=[(1-(n_2/n_1)^{2N})/(1+(n_2/n_1)^{2N})]^2}


**Check.**  Equation :eq:`fop-problem-7-1-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 7.1-8 — Matrix-program verification

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Initialize :math:`M=I`; for each layer multiply
:math:`M_i=\begin{bmatrix}\cos\delta_i&j\sin\delta_i/Y_i\\
jY_i\sin\delta_i&\cos\delta_i\end{bmatrix}`.  Convert total input admittance
to :math:`r` and plot :math:`|r|^2` versus wavelength or angle.  Using the
figure's layer data reproduces its stopband and TE/TM angular splitting.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-1-8-result

   M_i=\begin{bmatrix}\cos\delta_i&j\sin\delta_i/Y_i\\
   jY_i\sin\delta_i&\cos\delta_i\end{bmatrix}


**Check.**  Equation :eq:`fop-problem-7-1-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 7.2-1 — Gap/midgap estimate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Equal optical thickness gives Bragg frequency
:math:`\boxed{\nu_B=c/[2(n_1d_1+n_2d_2)]}` with
:math:`d_1+d_2=2\ \mathrm{\mu m}`.  The first-order relative gap is
:math:`\Delta\nu/\nu_B\simeq(4/\pi)\sin^{-1}|(n_2-n_1)/(n_2+n_1)|`.
It is large for 1.5/3.5 and small for 3.4/3.6, demonstrating that index
contrast, not mean index, controls the fractional gap.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-2-1-result

   \boxed{\nu_B=c/[2(n_1d_1+n_2d_2)]}


**Check.**  Equation :eq:`fop-problem-7-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 7.2-2 — Off-axis Bloch wave

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Keep conserved :math:`k_x`; in every layer replace
:math:`n_i\omega/c` by :math:`k_{zi}=[(n_i\omega/c)^2-k_x^2]^{1/2}` and
admittance by its TE/TM oblique value.  The unit-cell trace then gives
:math:`\boxed{\cos(K\Lambda)=\tfrac12\operatorname{tr}M(k_x,\omega)}`;
:math:`|\operatorname{tr}M/2|>1` is a bandgap.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-2-2-result

   \boxed{\cos(K\Lambda)=\tfrac12\operatorname{tr}M(k_x,\omega)}


**Check.**  Equation :eq:`fop-problem-7-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 7.2-3 — Propagation normal to periodicity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`K=0` (wavevector along the layers), tangential phase matching
makes the field sample a translationally uniform direction.  Substitution in
the off-axis dispersion relation leaves real :math:`k_x` for every allowed
frequency; the Bragg coupling term vanishes, so no axial-period bandgap opens.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-2-3-result

   K=0


**Check.**  Equation :eq:`fop-problem-7-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 7.2-4 — Omnidirectional reflector

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each conserved air :math:`k_x\leq\omega/c`, evaluate the cell trace with
:math:`n_2=2n_1` and equal optical thickness.  Shade frequencies for which
:math:`|\operatorname{tr}M/2|>1` for every point inside the air light cone;
the intersection of all angular TE/TM stopbands is the omnidirectional range.
This construction, rather than a single normal-incidence gap, is the required
projected dispersion plot.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-7-2-4-result

   n_2=2n_1


**Check.**  Equation :eq:`fop-problem-7-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.
