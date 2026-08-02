Chapter 2: Wave Optics
======================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 2.  The time convention is the one used by the text.

In-text exercises
-----------------

.. rubric:: Exercise 2.2-1 — Fresnel-approximation region

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At the usual boundary estimate :math:`a^4=4z^3\lambda`, with
:math:`z=1\ \mathrm m` and :math:`\lambda=633\ \mathrm{nm}`,
:math:`\boxed{a=39.9\ \mathrm{mm}}`,
:math:`\boxed{\theta_m=a/z=0.0399\ \mathrm{rad}=2.29^\circ}`, and
:math:`\boxed{N_F=a^2/(\lambda z)=2.51\times10^3}`.  Strict Fresnel validity
requires a radius appreciably smaller than this equality limit because
:math:`N_F\theta_m^2/4\ll1`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-2-1-result

   \boxed{N_F=a^2/(\lambda z)=2.51\times10^3}


**Check.**  Equation :eq:`fop-exercise-2-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 2.2-2 — Paraboloidal and Gaussian waves

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`integration identities <fop-formula-integration>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Substitution of :math:`A=(A_0/z)e^{-jk\rho^2/(2z)}` into
:math:`\nabla_T^2A-2jk\,\partial_zA=0` makes the constant and
:math:`\rho^2` terms cancel.  Replacing :math:`z` by
:math:`q=z+jz_0` preserves the cancellation because :math:`dq/dz=1`.
At :math:`z=0`, :math:`|A|^2=|A_1|^2z_0^{-2}
e^{-k\rho^2/z_0}`, a circular Gaussian.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-2-2-result

   |A|^2=|A_1|^2z_0^{-2}
   e^{-k\rho^2/z_0}


**Check.**  Equation :eq:`fop-exercise-2-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Exercise 2.4-1 — Thin prism

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`d(x)=d_0-ax`, the phase plate law
:math:`t=e^{-jk_0[n d(x)+d_0-d(x)]}` gives
:math:`t=h_0e^{-j(n-1)k_0ax}`.  Multiplying an axial plane wave adds transverse
wavevector :math:`k_x=(n-1)k_0a`; hence
:math:`\boxed{\theta\simeq(n-1)a}`, identical to the small-angle ray result.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-1-result

   \boxed{\theta\simeq(n-1)a}


**Check.**  Equation :eq:`fop-exercise-2-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.4-2 — Double-convex lens

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Adding the two parabolic surface sags leaves the quadratic phase
:math:`t=h_0\exp[-jk_0(x^2+y^2)/(2f)]`, where
:math:`\boxed{f^{-1}=(n-1)(R_1^{-1}-R_2^{-1})}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-2-result

   \boxed{f^{-1}=(n-1)(R_1^{-1}-R_2^{-1})}


**Check.**  Equation :eq:`fop-exercise-2-4-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 2.4-3 — Lens focusing

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

An axial plane wave multiplied by the lens phase becomes
:math:`A_0e^{-jk_0\rho^2/(2f)}`, the converging paraboloidal wave centered at
:math:`z=f`.  Incidence angle :math:`\theta` contributes
:math:`e^{-jk_0x\theta}` and translates the focus to
:math:`\boxed{x_f=f\theta}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-3-result

   \boxed{x_f=f\theta}


**Check.**  Equation :eq:`fop-exercise-2-4-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.4-4 — Imaging by phase matching

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The incident paraboloid contributes :math:`+k\rho^2/(2z_1)` and the lens
:math:`-k\rho^2/(2f)`.  The result equals the outgoing paraboloid phase
:math:`-k\rho^2/(2z_2)` precisely when
:math:`\boxed{z_1^{-1}+z_2^{-1}=f^{-1}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-4-result

   \boxed{z_1^{-1}+z_2^{-1}=f^{-1}}


**Check.**  Equation :eq:`fop-exercise-2-4-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 2.4-5 — Sinusoidal phase grating

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Insertion of :math:`d=d_0[1+\cos(2\pi x/\Lambda)]/2` gives the stated phase
grating.  The Jacobi--Anger expansion
:math:`e^{-j\beta\cos Kx}=\sum_q(-j)^qJ_q(\beta)e^{jqKx}` produces orders

.. math::
   :label: fop-exercise-2-4-5-eq-1

   \boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda},

with complex amplitudes :math:`h_0(-j)^qJ_q(\beta)` and
:math:`\beta=(n-1)k_0d_0/2`.

**Check.**  Equation :eq:`fop-exercise-2-4-5-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.4-6 — GRIN plate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The accumulated phase is
:math:`-k_0n_0d_0+k_0n_0d_0a^2\rho^2/2`; comparison with a thin-lens
quadratic phase gives :math:`\boxed{f=(n_0d_0a^2)^{-1}}` (the sign follows
the propagation convention).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-6-result

   \boxed{f=(n_0d_0a^2)^{-1}}


**Check.**  Equation :eq:`fop-exercise-2-4-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 2.5-1 — Plane/spherical interference

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Writing the phase difference as :math:`\phi=k(x^2+y^2)/(2d)+\phi_0`,

.. math::
   :label: fop-exercise-2-5-1-eq-1

   I=I_1+I_2+2\sqrt{I_1I_2}\cos\phi.

For equal intensities, zeros obey
:math:`k\rho_m^2/(2d)+\phi_0=(2m+1)\pi`; they are concentric circular rings.

**Check.**  Equation :eq:`fop-exercise-2-5-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.5-2 — Young interference

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The two Fresnel phases differ by :math:`2kax/d=kx\theta`, where
:math:`\theta\simeq2a/d`.  Thus
:math:`\boxed{I=2I_0[1+\cos(2\pi x\theta/\lambda)]}` and the fringe spacing is
:math:`\lambda/\theta=\lambda d/(2a)`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-5-2-result

   \boxed{I=2I_0[1+\cos(2\pi x\theta/\lambda)]}


**Check.**  Equation :eq:`fop-exercise-2-5-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.5-3 — Bragg reflection

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Adjacent planes add path :math:`2\Lambda\sin\theta`, so
:math:`\phi=2k\Lambda\sin\theta`.  The phasors align when
:math:`\boxed{2\Lambda\sin\theta=m\lambda}`; the peak intensity scales as
:math:`M^2` for :math:`M` equal-amplitude planes.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-5-3-result

   \boxed{2\Lambda\sin\theta=m\lambda}


**Check.**  Equation :eq:`fop-exercise-2-5-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 2.6-1 — Optical Doppler radar

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Superposing reference and return fields gives
:math:`I=I_1+I_2+2\sqrt{I_1I_2}\cos(2\pi\Delta\nu t+\phi)`.
Measure the electrical beat frequency and use
:math:`\boxed{v=c|\Delta\nu|/(2\nu)=\lambda|\Delta\nu|/2}`; quadrature phase
or a frequency offset resolves the velocity sign.

End-of-chapter problems
-----------------------

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-6-1-result

   \boxed{v=c|\Delta\nu|/(2\nu)=\lambda|\Delta\nu|/2}


**Check.**  Equation :eq:`fop-exercise-2-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 2.2-3 — Spherical Helmholtz solution

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`U=Ae^{-jkr}/r`, spherical symmetry gives
:math:`\nabla^2U=r^{-2}\partial_r(r^2\partial_rU)=-k^2U` for :math:`r>0`;
therefore :math:`(\nabla^2+k^2)U=0` away from the point source.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-2-3-result

   (\nabla^2+k^2)U=0


**Check.**  Equation :eq:`fop-problem-2-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.2-4 — Spherical-wave intensity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Power conservation over a sphere gives
:math:`\boxed{I(r)=P/(4\pi r^2)}`.  For :math:`P=100\ \mathrm W` at
:math:`r=1\ \mathrm m`, :math:`\boxed{I=7.96\ \mathrm{W,m^{-2}}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-2-4-result

   \boxed{I=7.96\ \mathrm{W,m^{-2}}}


**Check.**  Equation :eq:`fop-problem-2-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 2.2-5 — Cylindrical wave

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The outgoing exact solution is :math:`U=A H_0^{(2)}(k\rho)` with
:math:`\rho=\sqrt{x^2+z^2}`.  For :math:`k\rho\gg1`,
:math:`U\propto e^{-jk\rho}/\sqrt{\rho}` and
:math:`\boxed{I=P_\ell/(2\pi\rho)}`, where :math:`P_\ell` is power per unit
length along the cylinder axis.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-2-5-result

   \boxed{I=P_\ell/(2\pi\rho)}


**Check.**  Equation :eq:`fop-problem-2-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.2-6 — Paraxial Helmholtz equation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Set :math:`U=Ae^{-jkz}` in :math:`(\nabla^2+k^2)U=0`.  Exact substitution
gives :math:`\nabla_T^2A+\partial_z^2A-2jk\partial_zA=0`; dropping the slowly
varying :math:`\partial_z^2A` term yields
:math:`\boxed{\nabla_T^2A-2jk\partial_zA=0}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-2-6-result

   \boxed{\nabla_T^2A-2jk\partial_zA=0}


**Check.**  Equation :eq:`fop-problem-2-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.2-7 — Conjugate waves

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`U` and :math:`U^*` have identical intensity but opposite phase and
opposite wavefront normals.  Thus the conjugate of the stated plane wave
travels along :math:`-(\hat x+\hat y)/\sqrt2`; the conjugate of an outgoing
:math:`e^{-jkr}/r` spherical wave is an incoming :math:`e^{+jkr}/r` wave.

**Check.**  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.3-1 — Wavefronts in a SELFOC slab

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Wavefront normals follow the sinusoidal GRIN rays.  Draw curves orthogonal to
that ray family: initially planar fronts bend toward the high-index axis,
become most curved before the quarter pitch, planar again at a focus crossing,
and repeat with the pitch :math:`2\pi/a`.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

.. rubric:: Problem 2.4-7 — Spherical wave at a plane mirror

**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.

Reflect every local plane-wave component by reversing its normal component.
Their normals then converge to the mirror image of the source, so the reflected
field is a spherical wave centered at the virtual image point, with the mirror
reflection coefficient multiplying its amplitude.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 2.4-8 — Optical path through layers

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`optical path and Fermat's principle <fop-formula-fermat>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Ignoring interface reflections,
:math:`t=\exp[-jk_0\sum_qn_qd_q]`.  Equal free-space phase requires
:math:`\boxed{d=\sum_qn_qd_q}`, exactly the optical path length.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-4-8-result

   \boxed{d=\sum_qn_qd_q}


**Check.**  Equation :eq:`fop-problem-2-4-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.4-9 — Binary phase grating

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For equal half-period levels with transmittances :math:`t_1,t_2`, Fourier
coefficients are :math:`c_0=(t_1+t_2)/2` and
:math:`c_q=(t_1-t_2)\sin(q\pi/2)/(q\pi)` for :math:`q\ne0` (up to the chosen
cell origin phase).  Each coefficient launches an order at
:math:`\boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda}`; even nonzero orders
vanish for the symmetric 50% duty cycle.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-4-9-result

   \boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda}


**Check.**  Equation :eq:`fop-problem-2-4-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

.. rubric:: Problem 2.4-10 — Spherical mirror as a phase element

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Reflection doubles the surface-sag phase.  With
:math:`s\simeq(x^2+y^2)/(2R)`,
:math:`r=h_0e^{-j2k_0s}=h_0e^{-jk_0(x^2+y^2)/R}`.  It equals the thin-lens
phase for :math:`\boxed{f=-R/2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-4-10-result

   \boxed{f=-R/2}


**Check.**  Equation :eq:`fop-problem-2-4-10-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 2.5-4 — Standing wave

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For equal counterpropagating fields,
:math:`U=2A\cos(kz)` and
:math:`\boxed{I(z)=4I_0\cos^2(kz)}`.  Nodes are separated by
:math:`\lambda/2` and alternate with antinodes.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-5-4-result

   \boxed{I(z)=4I_0\cos^2(kz)}


**Check.**  Equation :eq:`fop-problem-2-5-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 2.5-5 — Fringe visibility

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`I_{max,min}=I_1+I_2\pm2\sqrt{I_1I_2}`, hence
:math:`\boxed{V=2\sqrt{I_1I_2}/(I_1+I_2)}`.  Differentiating versus
:math:`I_1/I_2` gives the maximum :math:`V=1` at equal intensities.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-5-5-result

   \boxed{V=2\sqrt{I_1I_2}/(I_1+I_2)}


**Check.**  Equation :eq:`fop-problem-2-5-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 2.5-6 — Misaligned Michelson mirror

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The returning waves have a linear transverse phase difference and therefore
form straight, equally spaced fringes perpendicular to the tilt.  Translating
the other mirror adds a uniform phase :math:`4\pi\Delta z/\lambda`, so the
whole fringe set slides; one fringe passes a point per :math:`\lambda/2` of
mirror travel.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

.. rubric:: Problem 2.6-2 — Pulsed spherical wave

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Every spectral component propagates as :math:`e^{-jkr}/r`; inverse Fourier
transformation gives :math:`\boxed{U(r,t)=a(t-r/c)/r}`.  For
:math:`\lambda_0=585\ \mathrm{nm}` and RMS duration :math:`6\ \mathrm{fs}`,
the RMS interval contains :math:`c\sigma_t/\lambda_0=\boxed{3.08}` carrier
cycles.  At :math:`1\ \mathrm{ps}` the intensity is a Gaussian spherical shell
centered at :math:`r=ct=0.2998\ \mathrm{mm}`, RMS radial thickness
:math:`c\sigma_t=1.80\ \mathrm{\mu m}`, and amplitude falloff :math:`1/r^2`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-2-6-2-result

   c\sigma_t/\lambda_0=\boxed{3.08}


**Check.**  Equation :eq:`fop-problem-2-6-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.
