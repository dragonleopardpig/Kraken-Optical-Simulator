Chapter 1: Ray Optics
=====================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 1.  Prompts are paraphrased.  Distances and radii use the book's sign
convention; :math:`P(d)` and :math:`L(f)` denote free-space and thin-lens ray
matrices.

In-text exercises
-----------------

.. rubric:: Exercise 1.1-1 — Snell's law from stationary optical path

**Problem in our own words.**  A ray travels from a fixed point :math:`A` in
medium 1 to a fixed point :math:`B` in medium 2, crossing their planar
interface at a movable point :math:`P`.  Show that making the optical path
stationary with respect to :math:`P` gives Snell's law.

.. _fop-exercise-1-1-1-geometry:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/snells_law_geometry.svg
   :alt: Labeled geometry of a refracted ray from A through interface point P to B
   :align: center
   :width: 95%

   **Figure 1 — Exercise 1.1-1: Snell's law from stationary
   optical path.** The crossing point has horizontal coordinate :math:`x`.
   Every geometrical variable used in the derivation is defined in the drawing.

**Definitions and assumptions.**

* :math:`n_1,n_2` are the constant refractive indices above and below the
  interface.
* :math:`d_1,d_2>0` are the perpendicular distances from :math:`A` and
  :math:`B` to the interface; :math:`d>0` is their total horizontal
  separation.
* :math:`x` is the horizontal distance from the projection of :math:`A` to
  :math:`P`, so the second horizontal leg is :math:`d-x` and
  :math:`0<x<d`.
* :math:`\ell_1,\ell_2` are the two geometrical path lengths.
* :math:`\theta_1,\theta_2` are measured from the interface normal, not from
  the interface itself.
* The media are homogeneous and isotropic, the interface is planar, and the
  endpoints are fixed.  Reflections and any phase shift at the boundary do
  not affect the ray path being varied.

By the Pythagorean theorem, the segment lengths in the figure are

.. math::
   :label: fop-ex-1-1-1-path-lengths

   \ell_1(x)=\sqrt{d_1^2+x^2},\qquad
   \ell_2(x)=\sqrt{d_2^2+(d-x)^2}.

**Mathematical formulas used.**  The calculation uses
:ref:`optical path and Fermat's principle <fop-formula-fermat>`, the
:ref:`stationary-value condition <fop-formula-stationary>`, the
:ref:`chain rule and square-root derivative <fop-formula-product-chain>`, and
the :ref:`right-triangle definitions of sine <fop-formula-trigonometry>`.

**Step 1 — Write the quantity that must be stationary.**  In a homogeneous
piece of medium, OPL equals refractive index times geometrical length.
Therefore the total OPL through :math:`P(x)` is

.. math::
   :label: fop-ex-1-1-1-opl

   \mathcal L(x)
   =n_1\ell_1(x)+n_2\ell_2(x)
   =n_1\sqrt{d_1^2+x^2}
    +n_2\sqrt{d_2^2+(d-x)^2}.

The transit time is :math:`T(x)=\mathcal L(x)/c`; since :math:`c` is
constant, :math:`dT/dx=0` and :math:`d\mathcal L/dx=0` are equivalent.

**Step 2 — Differentiate every term explicitly.**  For the first square root,
take :math:`u_1=d_1^2+x^2`.  Then :math:`u_1'=2x`, so Equation
:eq:`fop-formula-square-root-derivative` gives

.. math::
   :label: fop-ex-1-1-1-first-derivative

   \frac{d}{dx}\sqrt{d_1^2+x^2}
   =\frac{2x}{2\sqrt{d_1^2+x^2}}
   =\frac{x}{\sqrt{d_1^2+x^2}}.

For the second square root, let :math:`u_2=d_2^2+(d-x)^2`.  The nested
derivative is

.. math::
   :label: fop-ex-1-1-1-inner-derivative

   u_2'(x)=2(d-x)\frac{d}{dx}(d-x)
          =2(d-x)(-1)=-2(d-x).

The minus sign appears because moving :math:`P` to the right lengthens the
first horizontal leg but shortens the second.  Applying the square-root rule
again,

.. math::
   :label: fop-ex-1-1-1-second-derivative

   \frac{d}{dx}\sqrt{d_2^2+(d-x)^2}
   =-\frac{d-x}{\sqrt{d_2^2+(d-x)^2}}.

Combining Equations :eq:`fop-ex-1-1-1-first-derivative` and
:eq:`fop-ex-1-1-1-second-derivative` yields

.. math::
   :label: fop-ex-1-1-1-opl-derivative

   \frac{d\mathcal L}{dx}
   =n_1\frac{x}{\sqrt{d_1^2+x^2}}
    -n_2\frac{d-x}{\sqrt{d_2^2+(d-x)^2}}.

**Step 3 — Impose stationarity.**  Fermat's principle and Equation
:eq:`fop-formula-stationary-condition` require

.. math::
   :label: fop-ex-1-1-1-stationary

   0=\left.\frac{d\mathcal L}{dx}\right|_{x=x_*}
   \quad\Longrightarrow\quad
   n_1\frac{x_*}{\sqrt{d_1^2+x_*^2}}
   =n_2\frac{d-x_*}{\sqrt{d_2^2+(d-x_*)^2}},

where :math:`x_*` is the physical crossing point.

**Step 4 — Translate the geometrical ratios into angles.**  From the two
right triangles in the SVG,

.. math::
   :label: fop-ex-1-1-1-angle-definitions

   \sin\theta_1
   =\frac{x_*}{\ell_1}
   =\frac{x_*}{\sqrt{d_1^2+x_*^2}},\qquad
   \sin\theta_2
   =\frac{d-x_*}{\ell_2}
   =\frac{d-x_*}{\sqrt{d_2^2+(d-x_*)^2}}.

Substituting Equation :eq:`fop-ex-1-1-1-angle-definitions` into Equation
:eq:`fop-ex-1-1-1-stationary` gives the required law:

.. math::
   :label: fop-ex-1-1-1-snell-law

   \boxed{n_1\sin\theta_1=n_2\sin\theta_2}.

**Checks.**  Both sides of Equation :eq:`fop-ex-1-1-1-snell-law` are
dimensionless.  If :math:`n_1=n_2`, then
:math:`\sin\theta_1=\sin\theta_2`; for angles between :math:`0` and
:math:`\pi/2`, this gives :math:`\theta_1=\theta_2`, so the two segments form
one straight line.  At normal incidence, :math:`x_*=0` and :math:`d-x_*=0`
in the corresponding aligned geometry (:math:`d=0`), and both sides vanish.
These limits agree with physical expectation.

.. rubric:: Exercise 1.2-1 — Spherical-mirror imaging

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_01.svg
   :alt: Illustrated calculation map for Exercise 1.2-1, Spherical-mirror imaging
   :align: center
   :width: 95%

   **Figure 2 — Exercise 1.2-1: Spherical-mirror imaging.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At height :math:`y`, the paraxial surface normal has angle :math:`y/R`.
Reflection gives :math:`(y-y_1)/z_1+(y-y_2)/z_2=2y/R`.
For the coefficient of the arbitrary intercept :math:`y` to vanish,
:math:`1/z_1+1/z_2=2/R=1/f`.  The remaining term gives
:math:`y_2=-y_1z_2/z_1`; hence every ray from one object point reaches the
same, inverted image point.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-2-1-result

   y_2=-y_1z_2/z_1


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 1.2-2 — One spherical refracting boundary

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_02.svg
   :alt: Illustrated calculation map for Exercise 1.2-2, One spherical refracting boundary
   :align: center
   :width: 95%

   **Figure 3 — Exercise 1.2-2: One spherical refracting boundary.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Paraxial Snell refraction at height :math:`y` gives
:math:`n_1(y-y_1)/z_1+n_2(y_2-y)/z_2=(n_2-n_1)y/R`.
Equating the coefficient and constant terms yields

.. math::
   :label: fop-exercise-1-2-2-eq-1

   \frac{n_1}{z_1}+\frac{n_2}{z_2}=\frac{n_2-n_1}{R},
   \qquad y_2=-\frac{n_1z_2}{n_2z_1}y_1.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 1.2-3 — Aberration-free refracting surface

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_03.svg
   :alt: Illustrated calculation map for Exercise 1.2-3, Aberration-free refracting surface
   :align: center
   :width: 95%

   **Figure 4 — Exercise 1.2-3: Aberration-free refracting surface.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`optical path and Fermat's principle <fop-formula-fermat>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Let a surface point be :math:`(y,z)`, with the two axial conjugates at
:math:`(0,-z_1)` and :math:`(0,z_2)`.  Fermat's principle requires

.. math::
   :label: fop-exercise-1-2-3-eq-1

   \boxed{n_1\sqrt{y^2+(z+z_1)^2}
   +n_2\sqrt{y^2+(z_2-z)^2}=n_1z_1+n_2z_2}.

This Cartesian oval, not a sphere in general, makes the optical path identical
for every ray and therefore images without spherical aberration.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 1.2-4 — Thin-lens formulas

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_04.svg
   :alt: Illustrated calculation map for Exercise 1.2-4, Thin-lens formulas
   :align: center
   :width: 95%

   **Figure 5 — Exercise 1.2-4: Thin-lens formulas.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Apply the preceding boundary equation first at :math:`R_1`, then at
:math:`R_2`, and let the center thickness tend to zero.  The intermediate
image distance cancels, leaving

.. math::
   :label: fop-exercise-1-2-4-eq-1

   \frac1{z_1}+\frac1{z_2}=\frac1f,
   \qquad
   \boxed{\frac1f=(n-1)\left(\frac1{R_1}-\frac1{R_2}\right)},
   \qquad m=-\frac{z_2}{z_1}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-4-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 1.2-5 — Step-index fibre acceptance

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-5-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_05.svg
   :alt: Illustrated calculation map for Exercise 1.2-5, Step-index fibre acceptance
   :align: center
   :width: 95%

   **Figure 6 — Exercise 1.2-5: Step-index fibre acceptance.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At the core-cladding boundary, the limiting ray obeys
:math:`\sin\theta_c=n_2/n_1`.  Geometry gives
:math:`\sin\theta_z=\cos\theta_c`; applying Snell's law at the input face then
gives

.. math::
   :label: fop-exercise-1-2-5-eq-1

   \boxed{\mathrm{NA}=\sin\theta_a=\sqrt{n_1^2-n_2^2}}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-5-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 1.2-6 — Light trapped in a high-index block

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-2-6-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_02_06.svg
   :alt: Illustrated calculation map for Exercise 1.2-6, Light trapped in a high-index block
   :align: center
   :width: 95%

   **Figure 7 — Exercise 1.2-6: Light trapped in a high-index block.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Only rays within the internal escape cone
:math:`\theta_c=\sin^{-1}(1/n)` leave a face; the rest undergo total internal
reflection.  For GaAs, :math:`n=3.6`, so
:math:`\boxed{\theta_c=16.13^\circ}` (a full cone of :math:`32.26^\circ`).

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-2-6-result

   \boxed{\theta_c=16.13^\circ}


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-2-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 1.3-1 — A SELFOC slab as a lens

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_03_01.svg
   :alt: Illustrated calculation map for Exercise 1.3-1, A SELFOC slab as a lens
   :align: center
   :width: 95%

   **Figure 8 — Exercise 1.3-1: A SELFOC slab as a lens.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`n(y)\simeq n_0(1-a^2y^2/2)`, the paraxial ray equation is
:math:`y''+a^2y=0`.  Propagating its sine-cosine solution through length
:math:`d` and extending the exit tangent to the axis gives

.. math::
   :label: fop-exercise-1-3-1-eq-1

   \boxed{f=\frac{1}{n_0a\sin(ad)}},\qquad
   AH=\frac{\tan(ad/2)}{n_0a}.

At :math:`d=\pi/(2a)` all rays cross the axis at the exit quarter-pitch; at
:math:`d=\pi/a` they form an inverted unit-magnification half-pitch image.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-3-1-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 1.3-2 — Graded-index fibre acceptance

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-3-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_03_02.svg
   :alt: Illustrated calculation map for Exercise 1.3-2, Graded-index fibre acceptance
   :align: center
   :width: 95%

   **Figure 9 — Exercise 1.3-2: Graded-index fibre acceptance.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The conserved paraxial ray energy is
:math:`(y')^2+a^2y^2=\theta_0^2`.  Confinement to :math:`|y|\leq a_f`
requires :math:`\theta_0\leq aa_f`; input-face Snell refraction therefore
gives :math:`\boxed{\mathrm{NA}\simeq n_0aa_f}`.  Since
:math:`n(a_f)\simeq n_0(1-a^2a_f^2/2)`, the matched step-index result
:math:`\sqrt{n_0^2-n(a_f)^2}` has the same first-order value.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-3-2-result

   \boxed{\mathrm{NA}\simeq n_0aa_f}


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 1.4-1 — Zero elements of an ABCD matrix

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_01.svg
   :alt: Illustrated calculation map for Exercise 1.4-1, Zero elements of an ABCD matrix
   :align: center
   :width: 95%

   **Figure 10 — Exercise 1.4-1: Zero elements of an ABCD matrix.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

From :math:`y_2=Ay_1+B\theta_1` and
:math:`\theta_2=Cy_1+D\theta_1`: :math:`A=0` maps equal input angles to one
output height; :math:`B=0` images an input plane; :math:`C=0` is afocal; and
:math:`D=0` maps equal input heights to one output angle.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-4-1-result

   D=0


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Exercise 1.4-2 — Parallel plates

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_02.svg
   :alt: Illustrated calculation map for Exercise 1.4-2, Parallel plates
   :align: center
   :width: 95%

   **Figure 11 — Exercise 1.4-2: Parallel plates.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Using reduced angle :math:`n\theta`, each plate is
:math:`\begin{bmatrix}1&d_i/n_i\\0&1\end{bmatrix}`.  Such shear matrices add,
so

.. math::
   :label: fop-exercise-1-4-2-eq-1

   \boxed{M=\begin{bmatrix}1&\sum_i d_i/n_i\\0&1\end{bmatrix}}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Exercise 1.4-3 — Gap followed by a lens

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_03.svg
   :alt: Illustrated calculation map for Exercise 1.4-3, Gap followed by a lens
   :align: center
   :width: 95%

   **Figure 12 — Exercise 1.4-3: Gap followed by a lens.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Direct multiplication gives

.. math::
   :label: fop-exercise-1-4-3-eq-1

   \boxed{L(f)P(d)=
   \begin{bmatrix}1&0\\-1/f&1\end{bmatrix}
   \begin{bmatrix}1&d\\0&1\end{bmatrix}
   =\begin{bmatrix}1&d\\-1/f&1-d/f\end{bmatrix}}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Exercise 1.4-4 — Single-lens imaging

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_04.svg
   :alt: Illustrated calculation map for Exercise 1.4-4, Single-lens imaging
   :align: center
   :width: 95%

   **Figure 13 — Exercise 1.4-4: Single-lens imaging.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`M=P(d_2)L(f)P(d_1)`, the element
:math:`B=d_1+d_2-d_1d_2/f`.  The imaging law makes :math:`B=0`, so
:math:`y_2=Ay_1=-(d_2/d_1)y_1`, independently of input angle.  Setting
:math:`d_2=f` instead makes :math:`A=0`, so all rays of one input angle meet
at :math:`y_2=f\theta_1`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-4-4-result

   y_2=f\theta_1


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 1.4-5 — Thick symmetric lens

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-5-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_05.svg
   :alt: Illustrated calculation map for Exercise 1.4-5, Thick symmetric lens
   :align: center
   :width: 95%

   **Figure 14 — Exercise 1.4-5: Thick symmetric lens.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Multiplying the two spherical refractions and the internal translation gives
the equivalent power

.. math::
   :label: fop-exercise-1-4-5-eq-1

   \Phi=(n-1)\left(\frac1{R_1}-\frac1{R_2}
   +\frac{(n-1)d}{nR_1R_2}\right),\qquad f=\Phi^{-1}.

Locating the principal planes from the resulting :math:`A,D` elements changes
the vertex distances to :math:`z_1=d_1+h_1` and :math:`z_2=d_2+h_2`.
The condition :math:`B=0` then reduces to
:math:`1/z_1+1/z_2=1/f`, which proves the stated thick-lens form.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-5-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 1.4-6 — Alternating periodic lenses

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-6-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_06.svg
   :alt: Illustrated calculation map for Exercise 1.4-6, Alternating periodic lenses
   :align: center
   :width: 95%

   **Figure 15 — Exercise 1.4-6: Alternating periodic lenses.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Multiply one complete cell and apply the unimodular stability test
:math:`|\operatorname{tr}M/2|<1`.  The trace simplifies to

.. math::
   :label: fop-exercise-1-4-6-eq-1

   \boxed{0<\left(1-\frac d{2f_1}\right)
   \left(1-\frac d{2f_2}\right)<1}.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-6-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 1.4-7 — Two-mirror resonator

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-1-4-7-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_01_04_07.svg
   :alt: Illustrated calculation map for Exercise 1.4-7, Two-mirror resonator
   :align: center
   :width: 95%

   **Figure 16 — Exercise 1.4-7: Two-mirror resonator.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The round-trip matrix is the product of two translations and two mirror
powers.  With :math:`g_i=1+d/R_i` in the book's radius convention,
:math:`(\operatorname{tr}M+2)/4=g_1g_2`.  Hence bounded rays require
:math:`\boxed{0<g_1g_2<1}` (equality is marginal).

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-1-4-7-result

   \boxed{0<g_1g_2<1}


**Step 5 — Check.**  Equation :eq:`fop-exercise-1-4-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 1.1-2 — Stationary time need not be a minimum

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`optical path and Fermat's principle <fop-formula-fermat>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The ellipse has constant :math:`AP+PB`; its first variation at the tangent
point is zero.  An internally tangent surface lies inside the ellipse nearby,
so its adjacent broken paths are shorter and :math:`P` is a local maximum.
A surface crossing the ellipse lies on opposite sides on either side of
:math:`P`; the path difference changes sign, making the stationary path an
inflection.  Fermat's principle therefore means *stationary*, not always
minimum, time.

**Check.**  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 1.2-7 — Plane-parallel plate or stack

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Snell gives :math:`\sin\theta=n_1\sin\theta_1` at entry and the reverse at
exit, so the emergent angle is :math:`\theta`.  Geometry gives the lateral
shift

.. math::
   :label: fop-problem-1-2-7-eq-1

   \boxed{s=d\,\frac{\sin(\theta-\theta_1)}{\cos\theta_1}}.

For a stack, tangential wavevector conservation gives
:math:`n_m\sin\theta_m=\sin\theta` in every layer and the last boundary again
returns angle :math:`\theta`; the individual lateral shifts add.

**Check.**  Equation :eq:`fop-problem-1-2-7-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 1.2-8 — Biconvex lens in air and water

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`R_1=0.20\ \mathrm m`, :math:`R_2=-0.30\ \mathrm m`,

.. math::
   :label: fop-problem-1-2-8-eq-1

   \frac1f=\left(\frac{n_l}{n_m}-1\right)
   \left(\frac1{R_1}-\frac1{R_2}\right).

Thus :math:`f_{air}=1/[0.5(5+3.333)]=\boxed{0.240\ \mathrm m}`.  In water
(:math:`n_m=4/3`), :math:`n_l/n_m=1.125`, giving
:math:`\boxed{f_{water}=0.960\ \mathrm m}`.

**Check.**  Equation :eq:`fop-problem-1-2-8-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 1.2-9 — Cladless fibre

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\mathrm{NA}=\sqrt{1.46^2-1^2}=1.0647`.  Since an external numerical
aperture cannot exceed one, every ray in the incident air hemisphere can in
principle be accepted: :math:`\boxed{\theta_a=90^\circ}`.  The value above one
signals saturation, not a sine larger than one.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-1-2-9-result

   \boxed{\theta_a=90^\circ}


**Check.**  Equation :eq:`fop-problem-1-2-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 1.2-10 — Spherical coupling lens

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Trace the ray through the two spherical interfaces with vector Snell
refraction.  At the first hit :math:`(z,y)=(-\sqrt{1-0.7^2},0.7)` mm; applying
:math:`n=1\rightarrow1.8`, intersecting the far sphere, and applying
:math:`1.8\rightarrow1` gives the second hit
:math:`(z,y)=(0.999725,0.023451)` mm and emergent direction
:math:`(l,m)=(0.730362,-0.683060)`.  Its axial intercept is
:math:`z=1.024800` mm, hence
:math:`\boxed{f=0.02480\ \mathrm{mm}}` beyond the rear vertex.  This exact
meridional trace is preferable to the paraxial ball-lens BFL
:math:`na/[2(n-1)]-a=0.125\ \mathrm{mm}` because :math:`y/a=0.7` is far
outside the paraxial region.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-1-2-10-result

   \boxed{f=0.02480\ \mathrm{mm}}


**Check.**  Equation :eq:`fop-problem-1-2-10-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 1.2-11 — Extraction from an index-3.7 block

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The escape-cone fraction after perfect recycling by the other faces is
:math:`1-\cos\theta_c`, where :math:`\theta_c=\sin^{-1}(1/3.7)=15.68^\circ`.
Therefore :math:`\boxed{3.72\%}` of isotropic directions can escape the front.
A plane-parallel :math:`n=1.4` layer does not increase the final air escape
cone: successive Snell laws still require
:math:`3.7\sin\theta_{core}\leq1`.  Texture or a nonparallel extractor would
be required.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-1-2-11-result

   \boxed{3.72\%}


**Check.**  Equation :eq:`fop-problem-1-2-11-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 1.3-3 — Axially graded plate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Apply Snell's law to infinitesimal parallel layers:
:math:`n(z)\sin\theta(z)=\sin\theta_0`.  The exit medium is again air, so the
emergent angle is :math:`\theta_0`.  Since :math:`dy/dz=\tan\theta`,

.. math::
   :label: fop-problem-1-3-3-eq-1

   \boxed{\left(\frac{dy}{dz}\right)^2
   =\left[\frac{n^2(z)}{\sin^2\theta_0}-1\right]^{-1}}.

**Check.**  Equation :eq:`fop-problem-1-3-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 1.3-4 — Cylindrical GRIN ray equations

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`vector-calculus identities <fop-formula-vector-calculus>`, :ref:`common differential-equation solutions <fop-formula-odes>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Writing the transverse paraxial equation
:math:`d(n\mathbf r_\perp')/dz=\nabla_\perp n` in polar components gives

.. math::
   :label: fop-problem-1-3-4-eq-1

   \frac d{dz}(np')-np\phi'^2=\frac{dn}{dp},\qquad
   \frac d{dz}(np^2\phi')=0.

The second equation is conserved optical angular momentum.  For slowly
varying :math:`n`, these reduce to
:math:`p''-p\phi'^2=n^{-1}dn/dp` and
:math:`\phi''+2p'\phi'/p=0`.

**Check.**  Equation :eq:`fop-problem-1-3-4-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Problem 1.4-8 — Convex/concave lens pair

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For convex lens, gap, then concave lens,

.. math::
   :label: fop-problem-1-4-8-eq-1

   M=L(-f)P(f)L(f)=
   \boxed{\begin{bmatrix}0&f\\-1/f&2\end{bmatrix}}.

Because :math:`A=0`, parallel rays of a given angle meet at the same output
height :math:`f\theta`; because :math:`B\ne0`, the chosen input and output
planes are not conjugate object/image planes.

**Check.**  Equation :eq:`fop-problem-1-4-8-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 1.4-9 — GRIN-plate matrix

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`common differential-equation solutions <fop-formula-odes>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Solving :math:`y''+a^2y=0` over distance :math:`d` gives, for the reduced-angle
state :math:`(y,n_0\theta)`,

.. math::
   :label: fop-problem-1-4-9-eq-1

   \boxed{M(d)=\begin{bmatrix}
   \cos ad&\sin(ad)/(n_0a)\\-n_0a\sin(ad)&\cos ad
   \end{bmatrix}}.

**Check.**  Equation :eq:`fop-problem-1-4-9-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 1.4-10 — Periodic GRIN stability

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The determinant is one and half the trace is :math:`b=\cos(ad)`, so
:math:`|b|\leq1` for every real :math:`d`.  The trajectory is stable for all
cell choices (marginal only when :math:`ad` is an integer multiple of
:math:`\pi`); physical stability therefore does not depend on how the
continuous plate is partitioned.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-1-4-10-result

   b=\cos(ad)


**Check.**  Equation :eq:`fop-problem-1-4-10-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 1.4-11 — Plane-mirror recurrence

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

One round trip is simply :math:`M=P(2d)=\begin{bmatrix}1&2d\\0&1\end{bmatrix}`;
thus :math:`b=\operatorname{tr}M/2=1` and the repeated eigenvalue is one.
Since :math:`M^m=\begin{bmatrix}1&2md\\0&1\end{bmatrix}`,
:math:`\boxed{y_m=y_0+2md\theta_0=\alpha+m\beta}`.  Except for
:math:`\theta_0=0`, the planar resonator is marginal rather than bounded.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-1-4-11-result

   \boxed{y_m=y_0+2md\theta_0=\alpha+m\beta}


**Check.**  Equation :eq:`fop-problem-1-4-11-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

.. rubric:: Problem 1.4-12 — Four-dimensional ray matrices

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For state :math:`(x,y,\theta_x,\theta_y)^T`, free propagation and a cylindrical
lens focusing only in :math:`y` are

.. math::
   :label: fop-problem-1-4-12-eq-1

   \boxed{P_4(d)=\begin{bmatrix}1&0&d&0\\0&1&0&d\\0&0&1&0\\0&0&0&1\end{bmatrix}},
   \qquad
   \boxed{L_y(f)=\begin{bmatrix}1&0&0&0\\0&1&0&0\\0&0&1&0\\0&-1/f&0&1\end{bmatrix}}.

**Check.**  Equation :eq:`fop-problem-1-4-12-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.
