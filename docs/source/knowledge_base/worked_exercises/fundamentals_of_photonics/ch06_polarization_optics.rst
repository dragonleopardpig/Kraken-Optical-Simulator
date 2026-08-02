Chapter 6: Polarization Optics
==============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 6.  Global Jones phases are physically immaterial.

In-text exercises
-----------------

.. rubric:: Exercise 6.1-1 — Measuring Stokes parameters

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Projecting :math:`(A_x,A_y)` on horizontal/vertical, :math:`\pm45^\circ`, and
right/left circular analyser vectors gives
:math:`S_0=I_x+I_y`, :math:`S_1=I_x-I_y`,
:math:`S_2=I_{45}-I_{135}=2\Re(A_xA_y^*)`, and
:math:`S_3=I_R-I_L=2\Im(A_xA_y^*)` with the book's handedness sign.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-1-1-result

   S_3=I_R-I_L=2\Im(A_xA_y^*)


**Check.**  Equation :eq:`fop-exercise-6-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 6.1-2 — Cascaded quarter-wave plates

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\operatorname{diag}(1,j)^2=\operatorname{diag}(1,-1)`, a half-wave
plate.  Orthogonal fast axes give
:math:`\operatorname{diag}(1,j)\operatorname{diag}(j,1)=jI`, so polarization
is unchanged apart from global phase.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-1-2-result

   \operatorname{diag}(1,j)\operatorname{diag}(j,1)=jI


**Check.**  Equation :eq:`fop-exercise-6-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 6.1-3 — Rotated polarizer

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`T(\theta)=R(-\theta)\operatorname{diag}(1,0)R(\theta)` evaluates to
:math:`\boxed{\begin{bmatrix}\cos^2\theta&\sin\theta\cos\theta\\
\sin\theta\cos\theta&\sin^2\theta\end{bmatrix}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-1-3-result

   \boxed{\begin{bmatrix}\cos^2\theta&\sin\theta\cos\theta\\
   \sin\theta\cos\theta&\sin^2\theta\end{bmatrix}}


**Check.**  Equation :eq:`fop-exercise-6-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Exercise 6.1-4 — Normal polarization modes

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The polarizer eigenvectors are its pass/block linear axes, eigenvalues 1,0;
the retarder eigenvectors are its fast/slow linear axes, eigenvalues
:math:`1,e^{-j\Gamma}`; the rotator eigenvectors are RCP/LCP, eigenvalues
:math:`e^{\mp j\theta}`.

**Check.**  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 6.2-1 — Brewster window

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\theta_B=\tan^{-1}(1.5)=\boxed{56.31^\circ}` from the normal.  The
internal angle is :math:`33.69^\circ`, which is the reverse-interface Brewster
angle, so TM reflection vanishes at both parallel faces.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-2-1-result

   \theta_B=\tan^{-1}(1.5)=\boxed{56.31^\circ}


**Check.**  Equation :eq:`fop-exercise-6-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 6.2-2 — Conductive reflector

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

As :math:`\sigma\to\infty`, impedance tends to zero and :math:`R\to1`.
The Hagen--Rubens result
:math:`R\simeq1-2\sqrt{2\epsilon_0\omega/\sigma}` gives copper reflectances
:math:`\boxed{0.9534}` at 1.06 micrometres and :math:`\boxed{0.9853}` at
10.6 micrometres.  In the lossless sub-plasma-frequency Drude region the
index is imaginary, so no net transmitted power exists and :math:`R=1`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-2-2-result

   \boxed{0.9853}


**Check.**  Equation :eq:`fop-exercise-6-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 6.4-1 — Optical rotatory power

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Circular eigenindices satisfy :math:`n_\pm\simeq n\pm G/(2n)` for
:math:`G\ll n`.  Linear polarization is their equal superposition, so its
rotation per length is half their phase difference:
:math:`\boxed{\rho=(k_0/2)(n_+-n_-)\simeq k_0G/(2n)}`.

End-of-chapter problems
-----------------------

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-4-1-result

   \boxed{\rho=(k_0/2)(n_+-n_-)\simeq k_0G/(2n)}


**Check.**  Equation :eq:`fop-exercise-6-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 6.1-5 — Orthogonal ellipses

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Orthogonal Jones vectors can be written
:math:`(a,b e^{j\delta})` and :math:`(-b,a e^{j\delta})` after a common phase.
Their ellipse quadratic forms have swapped principal axes, while the sign of
:math:`\Im(A_xA_y^*)` reverses.  Thus major axes are perpendicular and
handedness is opposite.

**Check.**  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 6.1-6 — Rotator under coordinate rotation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Coordinate rotation produces :math:`R(-\alpha)R(\theta)R(\alpha)`.  Ordinary
2-D rotation matrices commute and add angles, so this equals
:math:`R(\theta)`; the rotator is basis-rotation invariant.

**Check.**  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 6.1-7 — Half-wave plate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Acting on :math:`(\cos\theta,\sin\theta)` with
:math:`\operatorname{diag}(1,-1)` gives
:math:`(\cos\theta,-\sin\theta)`, a line at :math:`-\theta` and rotation
:math:`-2\theta`.  Unlike a true rotator the result depends on orientation to
fixed fast/slow axes and reverses under a :math:`90^\circ` plate rotation.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.1-8 — Three retarders

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use :math:`Q_x=\operatorname{diag}(1,j)`,
:math:`H_{45}=R(-45^\circ)\operatorname{diag}(1,-1)R(45^\circ)`, and
:math:`Q_y=\operatorname{diag}(j,1)`.  Multiplication gives
:math:`Q_yH_{45}Q_x\doteq R(90^\circ)`; reversing the noncommuting sequence
gives :math:`R(-90^\circ)` (where :math:`\doteq` ignores global phase).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-1-8-result

   Q_y=\operatorname{diag}(j,1)


**Check.**  Equation :eq:`fop-problem-6-1-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.1-9 — Circular polarization at reflection

**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.

Mirror reversal changes propagation direction while the transverse field's
laboratory rotation does not change.  Handedness is defined looking along
propagation, so RCP becomes LCP and conversely.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.1-10 — Anti-glare screen

**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.

The polarizer plus 45-degree quarter-wave plate sends circular light to the
window.  Reflection reverses handedness; the return pass through the plate is
then linear orthogonal to the polarizer and is rejected.  It is not a general
optical isolator: it is reciprocal, lossy, and protects only the selected
polarization/reflection path.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.2-3 — Fresnel TE coefficient

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Tangential :math:`E` continuity gives :math:`1+r=t`; tangential :math:`H`
continuity gives :math:`n_1\cos\theta_1(1-r)=n_2\cos\theta_2t`.  Solving,
:math:`r_s=(n_1\cos\theta_1-n_2\cos\theta_2)/
(n_1\cos\theta_1+n_2\cos\theta_2)`.  For a beam, angular-spectrum decompose
it, apply the coefficient to every plane-wave component, then recombine.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-3-result

   r_s=(n_1\cos\theta_1-n_2\cos\theta_2)/
   (n_1\cos\theta_1+n_2\cos\theta_2)


**Check.**  Equation :eq:`fop-problem-6-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.2-4 — Glass at 45 degrees

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Snell gives :math:`\theta_2=28.13^\circ`.  Substitution in the Fresnel
coefficients gives :math:`\boxed{R_{TE}=0.09201}`,
:math:`\boxed{R_{TM}=0.008466}`, and unpolarized
:math:`\boxed{R=0.05024}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-4-result

   \boxed{R=0.05024}


**Check.**  Equation :eq:`fop-problem-6-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.2-5 — Brewster geometry

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Combining :math:`n_1\sec\theta_1=n_2\sec\theta_2` with Snell and eliminating
:math:`\theta_2` yields
:math:`\boxed{\tan\theta_B=n_2/n_1}`.  Substitution also gives
:math:`\theta_1+\theta_2=90^\circ`; a dipole parallel to the reflected-ray
direction cannot radiate into that direction.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-5-result

   \boxed{\tan\theta_B=n_2/n_1}


**Check.**  Equation :eq:`fop-problem-6-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.2-6 — TIR retardance

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\theta_c=41.81^\circ` and :math:`\theta=1.2\theta_c=50.18^\circ`.
Using the unit-magnitude TIR Fresnel phases gives
:math:`\phi_s=-61.52^\circ`, :math:`\phi_p=-106.50^\circ`; therefore the
relative retardance is :math:`\boxed{-44.98^\circ}` (magnitude
:math:`44.98^\circ`).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-6-result

   \boxed{-44.98^\circ}


**Check.**  Equation :eq:`fop-problem-6-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.2-7 — Goos--Hänchen shift

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

If :math:`r=e^{j\phi(\theta)}`, adjacent angular components acquire
:math:`d\phi=(d\phi/d\theta)d\theta`.  Their reflected interference pattern is
translated by
:math:`\boxed{\Delta=-[k\cos\theta]^{-1}d\phi/d\theta}` along the interface;
this follows by equating the added phase to the transverse fringe phase
:math:`k\cos\theta\,d\theta\,\Delta`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-7-result

   \boxed{\Delta=-[k\cos\theta]^{-1}d\phi/d\theta}


**Check.**  Equation :eq:`fop-problem-6-2-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.2-8 — Absorbing-medium reflection

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Write the complex index as :math:`\tilde n=n-j\alpha c_0/(2\omega)` and apply
normal-incidence boundary continuity.  The result is
:math:`\boxed{r=(\tilde n-1)/(\tilde n+1)}` (the sign reverses if reflectance
is defined on the opposite traveling-wave convention).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-2-8-result

   \boxed{r=(\tilde n-1)/(\tilde n+1)}


**Check.**  Equation :eq:`fop-problem-6-2-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 6.3-1 — Quartz retardation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Maximum birefringence is :math:`\Delta n=0.009`.  At 633 nm, one millimetre
introduces :math:`\boxed{89.33\ \mathrm{rad}=14.218\ cycles}`.  Quarter-wave
thicknesses are
:math:`\boxed{d=(m+1/4)\lambda_0/\Delta n}` or the complementary
:math:`(m+3/4)` family for the opposite fast-axis convention; the smallest is
:math:`17.58\ \mathrm{\mu m}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-3-1-result

   \boxed{d=(m+1/4)\lambda_0/\Delta n}


**Check.**  Equation :eq:`fop-problem-6-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.3-2 — Maximum extraordinary walk-off

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`r=(n_o/n_e)^2`, ray and wave-normal angles satisfy
:math:`\tan\phi=r\tan\theta`.  Maximizing :math:`|\theta-\phi|` gives
:math:`\tan\theta=1/\sqrt r=n_e/n_o`.  For quartz,
:math:`\boxed{\theta=45.1665^\circ}` and maximum walk-off
:math:`\boxed{0.3330^\circ}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-3-2-result

   \boxed{0.3330^\circ}


**Check.**  Equation :eq:`fop-problem-6-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.3-3 — Double refraction in quartz

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The ordinary wave obeys :math:`n_o\sin\theta_o=\sin30^\circ`, giving both its
wavevector and ray at :math:`\boxed{18.895^\circ}`.  Solving tangential
wavevector continuity with the extraordinary index ellipse gives
:math:`\boxed{\theta_{k,e}=18.786^\circ}`; the normal to that ellipse gives
the extraordinary ray at :math:`\boxed{18.658^\circ}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-3-3-result

   \boxed{18.658^\circ}


**Check.**  Equation :eq:`fop-problem-6-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.3-4 — Geometry for largest separation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Put the optic axis in the incidence plane, choose the extraordinary internal
wave-normal angle satisfying :math:`\tan\theta=n_e/n_o` from Problem 6.3-2,
and use a normally cut exit face.  The ordinary ray follows its wavevector;
the extraordinary ray is displaced through the maximum walk-off angle, so a
long plate maximizes lateral separation :math:`L\tan\rho_{max}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-3-4-result

   \tan\theta=n_e/n_o


**Check.**  Equation :eq:`fop-problem-6-3-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 6.3-5 — One-centimetre LiNbO3 plate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At a 45-degree optic-axis angle,
:math:`n_e(45^\circ)=[\cos^2(45^\circ)/n_o^2+sin^2(45^\circ)/n_e^2]^{-1/2}
=2.24365`.  The walk-off is :math:`2.2948^\circ`, giving lateral shift
:math:`\boxed{0.4007\ \mathrm{mm}}`.  Retardance is
:math:`2\pi(n_e(45^\circ)-n_o)L/\lambda=
\boxed{2\pi(689.531)}` (equivalent phase :math:`191.15^\circ` modulo
:math:`360^\circ`).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-3-5-result

   2\pi(n_e(45^\circ)-n_o)L/\lambda=
   \boxed{2\pi(689.531)}


**Check.**  Equation :eq:`fop-problem-6-3-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 6.3-6 — Conical refraction

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At the biaxial optic-axis contact point, one incident tangential wavevector
maps to every normal of the local conical :math:`k` surface, so refracted
Poynting vectors form a cone.  At a parallel exit face the wavevectors regain
one external direction, but different exit positions/directions form a hollow
ring (the external conical-refraction pattern).

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

.. rubric:: Problem 6.6-1 — Circular dichroic selector

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

In the circular basis take :math:`T_c=\operatorname{diag}(1,0)`.  Transforming
to the linear basis gives, for the book's RCP sign,
:math:`\boxed{T=\tfrac12\begin{bmatrix}1&-j\\j&1\end{bmatrix}}`.  Every input
component that survives is RCP.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-6-1-result

   \boxed{T=\tfrac12\begin{bmatrix}1&-j\\j&1\end{bmatrix}}


**Check.**  Equation :eq:`fop-problem-6-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 6.6-2 — Many weakly rotated polarizers

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Each adjacent projection contributes :math:`\cos\theta`; after :math:`N`
plates the field is along :math:`N\theta=90^\circ` with amplitude
:math:`\boxed{\cos^N(\pi/2N)}`.  Its logarithm is
:math:`N\ln\cos(\pi/2N)\sim-\pi^2/(8N)\to0`, so transmission tends to unity
while polarization rotates by 90 degrees (the optical Zeno limit).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-6-6-2-result

   \boxed{\cos^N(\pi/2N)}


**Check.**  Equation :eq:`fop-problem-6-6-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.
