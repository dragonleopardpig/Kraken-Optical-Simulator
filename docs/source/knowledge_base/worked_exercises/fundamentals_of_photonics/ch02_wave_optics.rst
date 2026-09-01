Chapter 2: Wave Optics
======================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 2.  The time convention is the one used by the text.

In-text exercises
-----------------

Exercise 2.2-1 — Fresnel-approximation region
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_02_01.svg
   :alt: Illustrated calculation map for Exercise 2.2-1, Fresnel-approximation region
   :align: center
   :width: 95%

   **Figure 17 — Exercise 2.2-1: Fresnel-approximation region.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At the usual boundary estimate :math:`a^4=4z^3\lambda`, with
:math:`z=1\ \mathrm m` and :math:`\lambda=633\ \mathrm{nm}`,
:math:`\boxed{a=39.9\ \mathrm{mm}}`,
:math:`\boxed{\theta_m=a/z=0.0399\ \mathrm{rad}=2.29^\circ}`, and
:math:`\boxed{N_F=a^2/(\lambda z)=2.51\times10^3}`.  Strict Fresnel validity
requires a radius appreciably smaller than this equality limit because
:math:`N_F\theta_m^2/4\ll1`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-2-1-result

   \boxed{N_F=a^2/(\lambda z)=2.51\times10^3}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 2.2-2 — Paraboloidal and Gaussian waves
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_02_02.svg
   :alt: Illustrated calculation map for Exercise 2.2-2, Paraboloidal and Gaussian waves
   :align: center
   :width: 95%

   **Figure 18 — Exercise 2.2-2: Paraboloidal and Gaussian waves.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`integration identities <fop-formula-integration>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Substitution of :math:`A=(A_0/z)e^{-jk\rho^2/(2z)}` into
:math:`\nabla_T^2A-2jk\,\partial_zA=0` makes the constant and
:math:`\rho^2` terms cancel.  Replacing :math:`z` by
:math:`q=z+jz_0` preserves the cancellation because :math:`dq/dz=1`.
At :math:`z=0`, :math:`|A|^2=|A_1|^2z_0^{-2}
e^{-k\rho^2/z_0}`, a circular Gaussian.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-2-2-result

   |A|^2=|A_1|^2z_0^{-2}
   e^{-k\rho^2/z_0}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

Exercise 2.4-1 — Thin prism
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Let :math:`x` be measured upward from the
apex of the inverted prism, as in textbook Fig. 2.4-6.  The local glass
thickness is :math:`d(x)`, the small apex angle is :math:`\alpha`, the largest
thickness is :math:`d_0`, and the refractive index is :math:`n`.  Thus
:math:`d(x)=\alpha x` within the thin-prism approximation, with
:math:`d_0=\alpha x_{\max}`.  The free-space wavenumber is
:math:`k_0=2\pi/\lambda_0`; the incident plane wave travels along :math:`+z`.

.. _fop-exercise-2-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_01.svg
   :alt: Illustrated calculation map for Exercise 2.4-1, Thin prism
   :align: center
   :width: 95%

   **Figure 19 — Exercise 2.4-1: Thin prism.**  The thickness
   :math:`d(x)=\alpha x` grows toward :math:`+x`; therefore, with the book's
   :math:`e^{-j\boldsymbol k\cdot\boldsymbol r}` convention, the output
   wavevector has :math:`k_x>0`.  The diagram labels the apex angle,
   thickness, wavevectors, and resulting positive deflection.

**Step 2 — Mathematical formulas used.**  The governing phase law is the
variable-thickness-plate transmittance in textbook Eq. (2.4-5), printed p. 53.
The result is checked against the thin-prism ray law in textbook Eq. (1.2-7),
printed p. 11.  The algebra uses :ref:`phasor identities
<fop-formula-exponentials>` and :ref:`small-angle identities
<fop-formula-trigonometry>`.

**Step 3 — Worked derivation.**  At height :math:`x`, the ray crosses glass of
thickness :math:`d(x)` and air of thickness :math:`d_0-d(x)`.  Neglecting
surface reflection, the two propagation factors multiply:

.. math::
   :label: fop-exercise-2-4-1-layer-product

   t(x,y)
   \simeq e^{-jnk_0d(x)}e^{-jk_0[d_0-d(x)]}.

Factor out the phase accumulated across the reference thickness,
:math:`h_0=e^{-jk_0d_0}`.  This gives exactly the form of textbook
Eq. (2.4-5):

.. math::
   :label: fop-exercise-2-4-1-phase-law

   t(x,y)\simeq h_0e^{-j(n-1)k_0d(x)}.

For the inverted prism, its sloping face gives

.. math::
   :label: fop-exercise-2-4-1-thickness

   d(x)=x\tan\alpha\simeq\alpha x,

so the prism transmittance is a linear phase ramp:

.. math::
   :label: fop-exercise-2-4-1-transmittance

   t(x,y)\simeq h_0e^{-j(n-1)k_0\alpha x}.

Immediately after the prism, an incident axial plane wave therefore has the
form

.. math::
   :label: fop-exercise-2-4-1-output-wave

   U_{\mathrm{out}}(x,z)
   =U_0h_0e^{-j(k_xx+k_zz)},
   \qquad k_x=(n-1)k_0\alpha.

Because the output propagates in air, :math:`|\boldsymbol k|=k_0`.  If
:math:`\theta` is measured from :math:`+z` toward :math:`+x`, then

.. math::
   :label: fop-exercise-2-4-1-angle-exact

   \sin\theta=\frac{k_x}{k_0}=(n-1)\alpha.

Finally, :math:`\sin\theta\simeq\theta` for a thin paraxial prism, so

.. math::
   :label: fop-exercise-2-4-1-angle-paraxial

   \theta\simeq(n-1)\alpha.

This is the same magnitude and direction as the ray-optics result in textbook
Eq. (1.2-7).

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-1-result

   \boxed{t(x,y)\simeq h_0e^{-j(n-1)k_0\alpha x}},
   \qquad
   \boxed{\theta\simeq(n-1)\alpha}


**Step 5 — Check.**  The phase exponent is dimensionless because
:math:`k_0x` is dimensionless and :math:`n-1` and :math:`\alpha` are
dimensionless.  Setting :math:`\alpha=0` or :math:`n=1` removes the phase ramp
and gives zero deflection.  Since :math:`d(x)` grows toward :math:`+x`, the
coefficient of :math:`x` in the book's
:math:`e^{-j\boldsymbol k\cdot\boldsymbol r}` convention gives
:math:`k_x>0`, agreeing with the upward deflection in textbook Fig. 2.4-6.
Equation
:eq:`fop-exercise-2-4-1-result` also reproduces the ray result (1.2-7).

Exercise 2.4-2 — Double-convex lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Let
:math:`\rho^2=x^2+y^2`.  Put the vertex of the front surface at :math:`z=0`
and the vertex of the rear surface at :math:`z=d_0`, where :math:`d_0` is the
central lens thickness.  At radius :math:`\rho`, the two surface positions are
:math:`z_1(\rho)` and :math:`z_2(\rho)`, so the local glass thickness is
:math:`d(\rho)=z_2(\rho)-z_1(\rho)`.

The textbook sign convention gives :math:`R_1>0` for the front convex
surface and :math:`R_2<0` for the rear surface in Fig. 2.4-8.  The lens has
uniform refractive index :math:`n`, is surrounded by air, and is thin and
paraxial: :math:`\rho\ll |R_1|,|R_2|`.  Surface reflection and absorption are
neglected, exactly as in the derivation of textbook Eq. (2.4-5).

.. _fop-exercise-2-4-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_02.svg
   :alt: Illustrated calculation map for Exercise 2.4-2, Double-convex lens
   :align: center
   :width: 95%

   **Figure 20 — Exercise 2.4-2: Double-convex lens.**  The signed surface
   radii determine the two paraxial sags.  Their difference gives the local
   thickness :math:`d(\rho)`, whose quadratic part becomes the lens phase.

**Step 2 — Mathematical formulas used.**  The requested starting point is
the variable-thickness plate law, textbook Eq. (2.4-5), printed p. 53:

.. math::
   :label: fop-exercise-2-4-2-plate-law

   t(x,y)\simeq h_{\mathrm{air}}
   \exp[-j(n-1)k_0d(x,y)],
   \qquad h_{\mathrm{air}}=e^{-jk_0d_0}.

The target is the thin-lens transmittance in textbook Eq. (2.4-9), with the
focal length required by Eq. (2.4-11), printed p. 55.  The only approximation
needed for the geometry is the Taylor expansion
:math:`\sqrt{1-u}\simeq1-u/2` for :math:`|u|\ll1`.  The algebra also uses
:ref:`phasor identities <fop-formula-exponentials>` and
:ref:`small-angle identities <fop-formula-trigonometry>`.

**Step 3 — Worked derivation.**

**Route A: use the general variable-thickness formula.**  For either signed
spherical radius :math:`R_i`, the surface sag measured from its vertex is

.. math::
   :label: fop-exercise-2-4-2-surface-sag

   s_i(\rho)
   =R_i-\operatorname{sgn}(R_i)
    \sqrt{R_i^2-\rho^2}
   \simeq \frac{\rho^2}{2R_i}.

For :math:`R_1>0`, this sag is positive, so the front surface moves toward
:math:`+z` away from its vertex.  For :math:`R_2<0`, it is negative, so the
rear surface moves toward :math:`-z`.  Therefore

.. math::
   :label: fop-exercise-2-4-2-surface-positions

   z_1(\rho)&\simeq\frac{\rho^2}{2R_1},\\
   z_2(\rho)&\simeq d_0+\frac{\rho^2}{2R_2}.

Subtracting the front position from the rear position gives the glass
thickness:

.. math::
   :label: fop-exercise-2-4-2-thickness

   d(\rho)
   &=z_2(\rho)-z_1(\rho)\\
   &\simeq d_0-\frac{\rho^2}{2}
      \left(\frac{1}{R_1}-\frac{1}{R_2}\right).

Because :math:`R_2<0`, the quantity in parentheses is positive.  Thus the
double-convex lens is thickest on axis and becomes thinner as :math:`\rho`
increases, as it should.

Insert :eq:`fop-exercise-2-4-2-thickness` into the plate law
:eq:`fop-exercise-2-4-2-plate-law`:

.. math::
   :label: fop-exercise-2-4-2-direct-phase

   t(x,y)
   &\simeq h_{\mathrm{air}}e^{-j(n-1)k_0d_0}
   \exp\!\left[
      \frac{jk_0\rho^2}{2}(n-1)
      \left(\frac{1}{R_1}-\frac{1}{R_2}\right)
   \right]\\
   &=h_0\exp\!\left(\frac{jk_0\rho^2}{2f}\right),
   \qquad h_0=e^{-jnk_0d_0},

provided that

.. math::
   :label: fop-exercise-2-4-2-lens-power

   \frac{1}{f}
   =(n-1)\left(\frac{1}{R_1}-\frac{1}{R_2}\right).

This is exactly textbook Eq. (2.4-9) with the focal length of Eq. (2.4-11).
The positive sign in the quadratic exponent is required by the book's
:math:`e^{-j\boldsymbol k\cdot\boldsymbol r}` convention.

**Route B: cascade two plano-convex lenses.**  Split the lens at an internal
plane.  The front plano-convex part has power :math:`(n-1)/R_1`.  The rear
part is reversed; its positive physical curvature magnitude is
:math:`-R_2`, because :math:`R_2<0`.  Hence

.. math::
   :label: fop-exercise-2-4-2-cascade-powers

   \frac{1}{f_{\mathrm{front}}}=\frac{n-1}{R_1},
   \qquad
   \frac{1}{f_{\mathrm{rear}}}=\frac{n-1}{-R_2}.

Each part contributes a transmittance of the form (2.4-9).  Their
coordinate-independent phase factors combine into the single constant
:math:`h_0`; multiplying the two transmittances adds their quadratic phases:

.. math::
   :label: fop-exercise-2-4-2-cascade-phase

   t_{\mathrm{front}}t_{\mathrm{rear}}
   &=h_0\exp\!\left[
      \frac{jk_0\rho^2}{2}
      \left(\frac{1}{f_{\mathrm{front}}}
           +\frac{1}{f_{\mathrm{rear}}}\right)
   \right]\\
   &=h_0\exp\!\left[
      \frac{jk_0\rho^2}{2}(n-1)
      \left(\frac{1}{R_1}-\frac{1}{R_2}\right)
   \right].

Thus the cascade proof gives the same phase and the same focal length as the
direct thickness proof.

**Step 4 — State the numbered result.**  The requested complex amplitude
transmittance and focal length are

.. math::
   :label: fop-exercise-2-4-2-result

   \boxed{
   t(x,y)\simeq h_0
   \exp\!\left[\frac{jk_0}{2f}(x^2+y^2)\right]},
   \qquad h_0=e^{-jnk_0d_0},
   \qquad
   \boxed{
   \frac{1}{f}=(n-1)
   \left(\frac{1}{R_1}-\frac{1}{R_2}\right)}.


**Step 5 — Check.**

* **Symmetric double-convex lens:** if :math:`R_1=R` and :math:`R_2=-R`,
  then :math:`1/f=2(n-1)/R>0`.  Both surfaces add positive converging power;
  they do not cancel.
* **Plano-convex limit:** letting :math:`R_2\rightarrow\infty` gives
  :math:`f=R_1/(n-1)`, which is textbook Eq. (2.4-10).
* **No index contrast:** as :math:`n\rightarrow1`, :math:`1/f\rightarrow0`
  and the transverse quadratic phase disappears.
* **Dimensions and phase sign:** each :math:`1/R_i` and :math:`1/f` has units
  of inverse length, while :math:`k_0\rho^2/f` is dimensionless.  With the
  textbook phasor convention, the positive quadratic phase in
  :eq:`fop-exercise-2-4-2-result` is the converging-lens phase of Eq. (2.4-9).

Exercise 2.4-3 — Lens focusing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-4-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_03.svg
   :alt: Illustrated calculation map for Exercise 2.4-3, Lens focusing
   :align: center
   :width: 95%

   **Figure 21 — Exercise 2.4-3: Lens focusing.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

An axial plane wave multiplied by the lens phase becomes
:math:`A_0e^{-jk_0\rho^2/(2f)}`, the converging paraboloidal wave centered at
:math:`z=f`.  Incidence angle :math:`\theta` contributes
:math:`e^{-jk_0x\theta}` and translates the focus to
:math:`\boxed{x_f=f\theta}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-3-result

   \boxed{x_f=f\theta}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-4-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 2.4-4 — Imaging by phase matching
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-4-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_04.svg
   :alt: Illustrated calculation map for Exercise 2.4-4, Imaging by phase matching
   :align: center
   :width: 95%

   **Figure 22 — Exercise 2.4-4: Imaging by phase matching.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The incident paraboloid contributes :math:`+k\rho^2/(2z_1)` and the lens
:math:`-k\rho^2/(2f)`.  The result equals the outgoing paraboloid phase
:math:`-k\rho^2/(2z_2)` precisely when
:math:`\boxed{z_1^{-1}+z_2^{-1}=f^{-1}}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-4-result

   \boxed{z_1^{-1}+z_2^{-1}=f^{-1}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-4-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 2.4-5 — Sinusoidal phase grating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-4-5-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_05.svg
   :alt: Illustrated calculation map for Exercise 2.4-5, Sinusoidal phase grating
   :align: center
   :width: 95%

   **Figure 23 — Exercise 2.4-5: Sinusoidal phase grating.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Insertion of :math:`d=d_0[1+\cos(2\pi x/\Lambda)]/2` gives the stated phase
grating.  The Jacobi--Anger expansion
:math:`e^{-j\beta\cos Kx}=\sum_q(-j)^qJ_q(\beta)e^{jqKx}` produces orders

.. math::
   :label: fop-exercise-2-4-5-eq-1

   \boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda},

with complex amplitudes :math:`h_0(-j)^qJ_q(\beta)` and
:math:`\beta=(n-1)k_0d_0/2`.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-2-4-5-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 2.4-6 — GRIN plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-4-6-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_04_06.svg
   :alt: Illustrated calculation map for Exercise 2.4-6, GRIN plate
   :align: center
   :width: 95%

   **Figure 24 — Exercise 2.4-6: GRIN plate.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The accumulated phase is
:math:`-k_0n_0d_0+k_0n_0d_0a^2\rho^2/2`; comparison with a thin-lens
quadratic phase gives :math:`\boxed{f=(n_0d_0a^2)^{-1}}` (the sign follows
the propagation convention).

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-4-6-result

   \boxed{f=(n_0d_0a^2)^{-1}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-4-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 2.5-1 — Plane/spherical interference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-5-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_05_01.svg
   :alt: Illustrated calculation map for Exercise 2.5-1, Plane/spherical interference
   :align: center
   :width: 95%

   **Figure 25 — Exercise 2.5-1: Plane/spherical interference.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Writing the phase difference as :math:`\phi=k(x^2+y^2)/(2d)+\phi_0`,

.. math::
   :label: fop-exercise-2-5-1-eq-1

   I=I_1+I_2+2\sqrt{I_1I_2}\cos\phi.

For equal intensities, zeros obey
:math:`k\rho_m^2/(2d)+\phi_0=(2m+1)\pi`; they are concentric circular rings.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-2-5-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 2.5-2 — Young interference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-5-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_05_02.svg
   :alt: Illustrated calculation map for Exercise 2.5-2, Young interference
   :align: center
   :width: 95%

   **Figure 26 — Exercise 2.5-2: Young interference.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The two Fresnel phases differ by :math:`2kax/d=kx\theta`, where
:math:`\theta\simeq2a/d`.  Thus
:math:`\boxed{I=2I_0[1+\cos(2\pi x\theta/\lambda)]}` and the fringe spacing is
:math:`\lambda/\theta=\lambda d/(2a)`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-5-2-result

   \boxed{I=2I_0[1+\cos(2\pi x\theta/\lambda)]}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-5-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 2.5-3 — Bragg reflection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-5-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_05_03.svg
   :alt: Illustrated calculation map for Exercise 2.5-3, Bragg reflection
   :align: center
   :width: 95%

   **Figure 27 — Exercise 2.5-3: Bragg reflection.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Adjacent planes add path :math:`2\Lambda\sin\theta`, so
:math:`\phi=2k\Lambda\sin\theta`.  The phasors align when
:math:`\boxed{2\Lambda\sin\theta=m\lambda}`; the peak intensity scales as
:math:`M^2` for :math:`M` equal-amplitude planes.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-5-3-result

   \boxed{2\Lambda\sin\theta=m\lambda}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-5-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Exercise 2.6-1 — Optical Doppler radar
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-2-6-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_02_06_01.svg
   :alt: Illustrated calculation map for Exercise 2.6-1, Optical Doppler radar
   :align: center
   :width: 95%

   **Figure 28 — Exercise 2.6-1: Optical Doppler radar.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Superposing reference and return fields gives
:math:`I=I_1+I_2+2\sqrt{I_1I_2}\cos(2\pi\Delta\nu t+\phi)`.
Measure the electrical beat frequency and use
:math:`\boxed{v=c|\Delta\nu|/(2\nu)=\lambda|\Delta\nu|/2}`; quadrature phase
or a frequency offset resolves the velocity sign.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-2-6-1-result

   \boxed{v=c|\Delta\nu|/(2\nu)=\lambda|\Delta\nu|/2}


**Step 5 — Check.**  Equation :eq:`fop-exercise-2-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 2.2-3 — Spherical Helmholtz solution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.2-4 — Spherical-wave intensity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.2-5 — Cylindrical wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.2-6 — Paraxial Helmholtz equation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.2-7 — Conjugate waves
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`U` and :math:`U^*` have identical intensity but opposite phase and
opposite wavefront normals.  Thus the conjugate of the stated plane wave
travels along :math:`-(\hat x+\hat y)/\sqrt2`; the conjugate of an outgoing
:math:`e^{-jkr}/r` spherical wave is an incoming :math:`e^{+jkr}/r` wave.

**Check.**  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 2.3-1 — Wavefronts in a SELFOC slab
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Wavefront normals follow the sinusoidal GRIN rays.  Draw curves orthogonal to
that ray family: initially planar fronts bend toward the high-index axis,
become most curved before the quarter pitch, planar again at a focus crossing,
and repeat with the pitch :math:`2\pi/a`.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 2.4-7 — Spherical wave at a plane mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.4-8 — Optical path through layers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.4-9 — Binary phase grating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.4-10 — Spherical mirror as a phase element
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.5-4 — Standing wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.5-5 — Fringe visibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Problem 2.5-6 — Misaligned Michelson mirror
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The returning waves have a linear transverse phase difference and therefore
form straight, equally spaced fringes perpendicular to the tilt.  Translating
the other mirror adds a uniform phase :math:`4\pi\Delta z/\lambda`, so the
whole fringe set slides; one fringe passes a point per :math:`\lambda/2` of
mirror travel.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 2.6-2 — Pulsed spherical wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
