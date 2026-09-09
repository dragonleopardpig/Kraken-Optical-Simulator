Chapter 6: Polarization Optics
==============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 6.  Global Jones phases are physically immaterial.

In-text exercises
-----------------

Exercise 6.1-1 — Measuring Stokes parameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Send the light to a calibrated
photodetector through

* a rotatable ideal linear polarizer, and
* a removable quarter-wave plate whose fast axis can also be rotated.

The detector readings below are background-subtracted intensities.  Denote by
:math:`I_H`, :math:`I_V`, :math:`I_D`, and :math:`I_A` the intensities passed
by linear analysers at :math:`0^\circ`, :math:`90^\circ`, :math:`45^\circ`,
and :math:`135^\circ`, respectively.  Denote by :math:`I_R` and :math:`I_L`
the readings of right- and left-circular analysers.  The latter are made by
placing the quarter-wave plate **before** the linear polarizer and setting its
fast axis at :math:`+45^\circ` or :math:`-45^\circ` relative to the polarizer
axis.  Which setting is called right-handed depends on the viewing and time
convention; label it so that :math:`S_3=I_R-I_L`, as in this chapter.

.. _fop-exercise-6-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_01_01.svg
   :alt: Illustrated calculation map for Exercise 6.1-1, Measuring Stokes parameters
   :align: center
   :width: 95%

   **Figure 48 — Exercise 6.1-1: Measuring Stokes parameters.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  For a linear analyser at angle
:math:`\theta`, the transmitted intensity is

.. math::
   :label: fop-exercise-6-1-1-linear-analyser

   I_{\mathrm{lin}}(\theta)
   =\frac{1}{2}\left(S_0+S_1\cos 2\theta+S_2\sin 2\theta\right).

The two circular-analyser readings are

.. math::
   :label: fop-exercise-6-1-1-circular-analyser

   I_R=\frac{1}{2}(S_0+S_3),
   \qquad
   I_L=\frac{1}{2}(S_0-S_3).

A rotating linear polarizer alone can therefore determine :math:`S_0`,
:math:`S_1`, and :math:`S_2`, but not :math:`S_3`: the quarter-wave plate is
what converts circular polarization (the quadrature component) into a linear
intensity difference.

**Step 3 — Worked derivation.**  Keep the incident beam power constant while
recording the following six settings.  A six-state measurement is slightly
redundant, but the redundancy exposes source drift and analyser errors.

.. list-table::
   :header-rows: 1
   :widths: 18 34 48

   * - Reading
     - Optics before the detector
     - Information supplied
   * - :math:`I_H`
     - Linear polarizer at :math:`0^\circ`
     - :math:`I_H=(S_0+S_1)/2`
   * - :math:`I_V`
     - Linear polarizer at :math:`90^\circ`
     - :math:`I_V=(S_0-S_1)/2`
   * - :math:`I_D`
     - Linear polarizer at :math:`45^\circ`
     - :math:`I_D=(S_0+S_2)/2`
   * - :math:`I_A`
     - Linear polarizer at :math:`135^\circ`
     - :math:`I_A=(S_0-S_2)/2`
   * - :math:`I_R`
     - Quarter-wave plate and polarizer set as a right-circular analyser
     - :math:`I_R=(S_0+S_3)/2`
   * - :math:`I_L`
     - Quarter-wave plate and polarizer set as a left-circular analyser
     - :math:`I_L=(S_0-S_3)/2`

Subtracting each orthogonal pair isolates one signed Stokes component, while
adding either member pair gives the total intensity:

.. math::
   :label: fop-exercise-6-1-1-six-state-reconstruction

   \begin{aligned}
   S_0 &= I_H+I_V,\\
   S_1 &= I_H-I_V,\\
   S_2 &= I_D-I_A,\\
   S_3 &= I_R-I_L.
   \end{aligned}

Ideally, :math:`I_H+I_V=I_D+I_A=I_R+I_L`.  In a real experiment, use the
average of these three sums for a lower-noise estimate of :math:`S_0`, after
correcting the channels for detector gain and optical throughput.

**Step 4 — State the numbered result.**  The requested method returns the
complete Stokes vector

.. math::
   :label: fop-exercise-6-1-1-result

   \boxed{
   \mathbf S=
   \begin{bmatrix}S_0\\S_1\\S_2\\S_3\end{bmatrix}
   =
   \begin{bmatrix}
   I_H+I_V\\
   I_H-I_V\\
   I_D-I_A\\
   I_R-I_L
   \end{bmatrix}}

This works for fully, partially, or unpolarized stationary light; it does not
require the light to possess a Jones vector.  If only the minimum number of
readings is desired, measure :math:`I_H`, :math:`I_V`, :math:`I_D`, and
:math:`I_R`.  Then use :math:`S_0=I_H+I_V`,
:math:`S_1=I_H-I_V`, :math:`S_2=2I_D-S_0`, and
:math:`S_3=2I_R-S_0`.  The six-reading method is normally preferable because
each component is formed from a balanced difference.

**Step 5 — Check.**  A physical Stokes vector must satisfy

.. math::
   :label: fop-exercise-6-1-1-physicality

   S_0\geq 0,
   \qquad
   S_1^2+S_2^2+S_3^2\leq S_0^2.

The degree of polarization is
:math:`P=\sqrt{S_1^2+S_2^2+S_3^2}/S_0`, so :math:`0\leq P\leq1`.
Useful calibration states are horizontal linear light,
:math:`(S_0,S_0,0,0)`, :math:`45^\circ` linear light,
:math:`(S_0,0,S_0,0)`, and right-circular light,
:math:`(S_0,0,0,S_0)` in the adopted handedness convention.  If the source
fluctuates appreciably during sequential readings, split the beam into six
simultaneous analyser channels, or monitor its power with a reference
detector and normalize every reading before taking the differences.

Exercise 6.1-2 — Cascaded quarter-wave plates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_01_02.svg
   :alt: Illustrated calculation map for Exercise 6.1-2, Cascaded quarter-wave plates
   :align: center
   :width: 95%

   **Figure 49 — Exercise 6.1-2: Cascaded quarter-wave plates.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\operatorname{diag}(1,j)^2=\operatorname{diag}(1,-1)`, a half-wave
plate.  Orthogonal fast axes give
:math:`\operatorname{diag}(1,j)\operatorname{diag}(j,1)=jI`, so polarization
is unchanged apart from global phase.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-1-2-result

   \operatorname{diag}(1,j)\operatorname{diag}(j,1)=jI


**Step 5 — Check.**  Equation :eq:`fop-exercise-6-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 6.1-3 — Rotated polarizer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-1-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_01_03.svg
   :alt: Illustrated calculation map for Exercise 6.1-3, Rotated polarizer
   :align: center
   :width: 95%

   **Figure 50 — Exercise 6.1-3: Rotated polarizer.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`matrix multiplication and eigenvalue rules <fop-formula-matrices>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`T(\theta)=R(-\theta)\operatorname{diag}(1,0)R(\theta)` evaluates to
:math:`\boxed{\begin{bmatrix}\cos^2\theta&\sin\theta\cos\theta\\
\sin\theta\cos\theta&\sin^2\theta\end{bmatrix}}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-1-3-result

   \boxed{\begin{bmatrix}\cos^2\theta&\sin\theta\cos\theta\\
   \sin\theta\cos\theta&\sin^2\theta\end{bmatrix}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-6-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Multiply the matrices independently in the stated input-to-output order and verify that every product has compatible dimensions.

Exercise 6.1-4 — Normal polarization modes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-1-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_01_04.svg
   :alt: Illustrated calculation map for Exercise 6.1-4, Normal polarization modes
   :align: center
   :width: 95%

   **Figure 51 — Exercise 6.1-4: Normal polarization modes.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The polarizer eigenvectors are its pass/block linear axes, eigenvalues 1,0;
the retarder eigenvectors are its fast/slow linear axes, eigenvalues
:math:`1,e^{-j\Gamma}`; the rotator eigenvectors are RCP/LCP, eigenvalues
:math:`e^{\mp j\theta}`.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 6.2-1 — Brewster window
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_02_01.svg
   :alt: Illustrated calculation map for Exercise 6.2-1, Brewster window
   :align: center
   :width: 95%

   **Figure 52 — Exercise 6.2-1: Brewster window.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\theta_B=\tan^{-1}(1.5)=\boxed{56.31^\circ}` from the normal.  The
internal angle is :math:`33.69^\circ`, which is the reverse-interface Brewster
angle, so TM reflection vanishes at both parallel faces.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-2-1-result

   \theta_B=\tan^{-1}(1.5)=\boxed{56.31^\circ}


**Step 5 — Check.**  Equation :eq:`fop-exercise-6-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 6.2-2 — Conductive reflector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_02_02.svg
   :alt: Illustrated calculation map for Exercise 6.2-2, Conductive reflector
   :align: center
   :width: 95%

   **Figure 53 — Exercise 6.2-2: Conductive reflector.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

As :math:`\sigma\to\infty`, impedance tends to zero and :math:`R\to1`.
The Hagen--Rubens result
:math:`R\simeq1-2\sqrt{2\epsilon_0\omega/\sigma}` gives copper reflectances
:math:`\boxed{0.9534}` at 1.06 micrometres and :math:`\boxed{0.9853}` at
10.6 micrometres.  In the lossless sub-plasma-frequency Drude region the
index is imaginary, so no net transmitted power exists and :math:`R=1`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-2-2-result

   \boxed{0.9853}


**Step 5 — Check.**  Equation :eq:`fop-exercise-6-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 6.4-1 — Optical rotatory power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-6-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_06_04_01.svg
   :alt: Illustrated calculation map for Exercise 6.4-1, Optical rotatory power
   :align: center
   :width: 95%

   **Figure 54 — Exercise 6.4-1: Optical rotatory power.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Circular eigenindices satisfy :math:`n_\pm\simeq n\pm G/(2n)` for
:math:`G\ll n`.  Linear polarization is their equal superposition, so its
rotation per length is half their phase difference:
:math:`\boxed{\rho=(k_0/2)(n_+-n_-)\simeq k_0G/(2n)}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-6-4-1-result

   \boxed{\rho=(k_0/2)(n_+-n_-)\simeq k_0G/(2n)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-6-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 6.1-5 — Orthogonal ellipses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Remove the physically irrelevant common phase and
write one normalized, fully polarized state as
:math:`\mathbf J_1=(a,b e^{j\delta})^T`, where :math:`a,b\geq0` and
:math:`a^2+b^2=1`.  Jones states are orthogonal when their Hermitian inner
product is zero.  For a noncircular ellipse, let :math:`\psi` denote the
major-axis angle and :math:`\chi` its ellipticity angle; the sign of
:math:`\chi` specifies handedness.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication
and eigenvalue rules <fop-formula-matrices>` and the Stokes-to-ellipse
relations :math:`2\psi=\operatorname{atan2}(S_2,S_1)` and
:math:`\sin 2\chi=S_3/S_0`.

**Worked derivation.**  A normalized vector orthogonal to :math:`\mathbf J_1`
is

.. math::
   :label: fop-problem-6-1-5-orthogonal-vector

   \mathbf J_2=
   \begin{bmatrix}b\\-a e^{j\delta}\end{bmatrix},
   \qquad
   \mathbf J_1^\dagger\mathbf J_2
   =ab-ab=0.

For :math:`\mathbf J_1`, the three polarization-dependent Stokes components
are :math:`S_1=a^2-b^2`, :math:`S_2=2ab\cos\delta`, and (with the chapter's
handedness convention) :math:`S_3=-2ab\sin\delta`.  Substitution of
:math:`\mathbf J_2` changes the sign of every one of them but leaves
:math:`S_0=1` unchanged:

.. math::
   :label: fop-problem-6-1-5-antipodal-stokes

   (S_1,S_2,S_3)_2=-(S_1,S_2,S_3)_1.

Consequently,
:math:`\operatorname{atan2}(-S_2,-S_1)=\operatorname{atan2}(S_2,S_1)+\pi`.
Halving this angle gives :math:`\psi_2=\psi_1+\pi/2` modulo :math:`\pi`, so
the major axes are perpendicular.  Also
:math:`\sin 2\chi_2=-\sin 2\chi_1`, hence :math:`\chi_2=-\chi_1`: the two
fields rotate in opposite senses.

**Numbered result.**  Orthogonal polarization states occupy antipodal points
on the Poincaré sphere, which gives

.. math::
   :label: fop-problem-6-1-5-result

   \boxed{\psi_2=\psi_1+90^\circ\pmod{180^\circ},
   \qquad \chi_2=-\chi_1.}

**Check.**  For :math:`\delta=0`, both states are linear and their Jones
vectors point along perpendicular lines.  For :math:`a=b` and
:math:`|\delta|=90^\circ`, the pair is right- and left-circular; handedness is
still opposite, although a circle has no unique major-axis direction.

Problem 6.1-6 — Rotator under coordinate rotation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The chapter's passive coordinate-rotation matrix
and the Jones matrix of a physical rotator through :math:`\theta` are

.. math::
   :label: fop-problem-6-1-6-matrices

   R(\alpha)=
   \begin{bmatrix}\cos\alpha&\sin\alpha\\-\sin\alpha&\cos\alpha\end{bmatrix},
   \qquad
   T(\theta)=
   \begin{bmatrix}\cos\theta&-\sin\theta\\
                   \sin\theta& \cos\theta\end{bmatrix}=R(-\theta).

Rotate the coordinate axes through an arbitrary angle :math:`\alpha`; this
changes the matrix representation to :math:`T'=R(\alpha)TR(-\alpha)`.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication
and eigenvalue rules <fop-formula-matrices>` and
:math:`R(a)R(b)=R(a+b)`.

**Worked derivation.**  Two-dimensional rotations commute, so

.. math::
   :label: fop-problem-6-1-6-transformation

   \begin{aligned}
   T'&=R(\alpha)R(-\theta)R(-\alpha)\\
     &=R(\alpha-\theta-\alpha)\\
     &=R(-\theta)=T.
   \end{aligned}

The cancellation holds for every :math:`\alpha`; no direction in the
transverse plane is preferred by an ideal optical rotator.

**Numbered result.**

.. math::
   :label: fop-problem-6-1-6-result

   \boxed{R(\alpha)T(\theta)R(-\alpha)=T(\theta).}

**Check.**  Direct multiplication gives the same four matrix elements.
Setting :math:`\alpha=90^\circ` also leaves :math:`T` unchanged, whereas the
matrix of a fixed-axis retarder generally changes under that operation.

Problem 6.1-7 — Half-wave plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Take the fast axis as :math:`x`.  Apart from a
common phase, an ideal half-wave retarder has
:math:`H_0=\operatorname{diag}(1,-1)`.  The input is linearly polarized at
:math:`\theta` to that axis, so
:math:`\mathbf J_{\rm in}=(\cos\theta,\sin\theta)^T`.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and
small-angle identities <fop-formula-trigonometry>` and the rotated-device rule
:math:`H(\beta)=R(-\beta)H_0R(\beta)`.

**Worked derivation.**  With the plate axes unrotated,

.. math::
   :label: fop-problem-6-1-7-axis-aligned

   \mathbf J_{\rm out}=H_0\mathbf J_{\rm in}
   =\begin{bmatrix}\cos\theta\\-\sin\theta\end{bmatrix}
   =\mathbf J_{\rm lin}(-\theta).

Thus the output polarization lies at :math:`-\theta`; relative to the input it
has turned through :math:`-2\theta` (a magnitude :math:`2\theta`, toward and
through the fast axis).  More generally, if the fast axis is at
:math:`\beta`, application of the rotated matrix gives

.. math::
   :label: fop-problem-6-1-7-rotated-plate

   H(\beta)\mathbf J_{\rm lin}(\theta)
   =\mathbf J_{\rm lin}(2\beta-\theta).

A true rotator would instead produce
:math:`\mathbf J_{\rm lin}(\theta+\gamma)` with one fixed :math:`\gamma` for
every input angle.  The half-wave plate's change,
:math:`2(\beta-\theta)`, depends on the input orientation.  It also reverses
the handedness of circular or elliptical light, which an ideal rotator does
not.

**Numbered result.**

.. math::
   :label: fop-problem-6-1-7-result

   \boxed{\theta_{\rm out}=-\theta,
   \qquad \Delta\theta=-2\theta}

for a fast axis along :math:`x`.

**Check.**  Input along either plate axis remains on that axis.  For
:math:`\theta=45^\circ`, the output is at :math:`-45^\circ`, a
:math:`90^\circ` turn in magnitude, as expected for a half-wave plate.

Problem 6.1-8 — Three retarders
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  A retarder with fast axis :math:`x` and phase
delay :math:`\Gamma` has
:math:`W_x(\Gamma)=\operatorname{diag}(1,e^{-j\Gamma})`.  The light first
meets (a), then (b), then (c), so the system matrix is
:math:`T_{abc}=T_cT_bT_a`; the first element encountered stands at the right.

**Mathematical formulas used.**  The working uses :ref:`matrix multiplication
and eigenvalue rules <fop-formula-matrices>` and the coordinate-rotation
matrix defined in Problem 6.1-6.

**Worked derivation.**  The three requested Jones matrices are

.. math::
   :label: fop-problem-6-1-8-element-matrices

   Q_x=\begin{bmatrix}1&0\\0&-j\end{bmatrix},\qquad
   H_{45}=R(-45^\circ)
      \begin{bmatrix}1&0\\0&-1\end{bmatrix}R(45^\circ)
      =\begin{bmatrix}0&1\\1&0\end{bmatrix},\qquad
   Q_y=\begin{bmatrix}-j&0\\0&1\end{bmatrix}.

Multiplying in propagation order gives

.. math::
   :label: fop-problem-6-1-8-forward-product

   T_{abc}=Q_yH_{45}Q_x
   =\begin{bmatrix}0&-1\\1&0\end{bmatrix}
   =T(+90^\circ).

It sends :math:`x` polarization to :math:`y` and :math:`y` polarization to
:math:`-x`, precisely a :math:`+90^\circ` rotation.  If the physical order is
reversed, the matrix order is also reversed:

.. math::
   :label: fop-problem-6-1-8-reverse-product

   T_{cba}=Q_xH_{45}Q_y
   =\begin{bmatrix}0&1\\-1&0\end{bmatrix}
   =T(-90^\circ).

Changing the sign convention for retarder phase can multiply intermediate
matrices by common phases, but it does not change either observable rotation.

**Numbered result.**

.. math::
   :label: fop-problem-6-1-8-result

   \boxed{T_{abc}=T(+90^\circ),\qquad
          T_{cba}=T(-90^\circ).}

**Check.**  Both products are unitary with determinant :math:`+1`.  Their
product is the identity, confirming that reversing this noncommuting sequence
reverses the rotation rather than reproducing it.

Problem 6.1-9 — Circular polarization at reflection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Consider normal reflection from an ideal isotropic
mirror.  Let the incident propagation basis
:math:`(\hat{\mathbf x}_i,\hat{\mathbf y}_i,\hat{\mathbf z}_i)` be
right-handed, with :math:`\hat{\mathbf z}_i` along the incident wavevector.
After reflection :math:`\hat{\mathbf z}_r=-\hat{\mathbf z}_i`.  A convenient
right-handed reflected basis is therefore
:math:`\hat{\mathbf x}_r=\hat{\mathbf x}_i` and
:math:`\hat{\mathbf y}_r=-\hat{\mathbf y}_i`.

**Mathematical formulas used.**  The working uses the Jones vectors
:math:`\mathbf e_R=(1,j)^T/\sqrt2` and
:math:`\mathbf e_L=(1,-j)^T/\sqrt2` in each local right-handed propagation
basis.  Reversing the viewing direction is essential: handedness is defined
relative to the direction of propagation, not to fixed laboratory axes.

**Worked derivation.**  At an ideal mirror both tangential laboratory-field
components acquire the same reflection phase.  Taking that phase as
:math:`-1`, the laboratory components become
:math:`(-A_x,-A_y)`.  Expressing the reflected field in its local basis flips
the sign of its :math:`y` coordinate once more, hence

.. math::
   :label: fop-problem-6-1-9-reflection-map

   \begin{bmatrix}A_x\\A_y\end{bmatrix}_{i}
   \longmapsto
   \begin{bmatrix}-A_x\\A_y\end{bmatrix}_{r}.

Apply this map to the two circular states:

.. math::
   :label: fop-problem-6-1-9-circular-map

   \mathbf e_R\longmapsto
   \frac{1}{\sqrt2}\begin{bmatrix}-1\\j\end{bmatrix}
   \doteq\mathbf e_L,
   \qquad
   \mathbf e_L\longmapsto
   \frac{1}{\sqrt2}\begin{bmatrix}-1\\-j\end{bmatrix}
   \doteq\mathbf e_R,

where :math:`\doteq` means equality apart from a physically irrelevant common
phase.

**Numbered result.**

.. math::
   :label: fop-problem-6-1-9-result

   \boxed{R\ \overset{\text{mirror reflection}}{\longleftrightarrow}\ L.}

**Check.**  Two successive mirror reflections restore the original
propagation direction and handedness.  For a real mirror at oblique incidence,
unequal TE and TM phases can additionally make the state elliptical; the pure
handedness swap above is the ideal normal-incidence result asked for here.

Problem 6.1-10 — Anti-glare screen
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Place, from the observer toward the window, a
linear polarizer followed by a quarter-wave retarder.  Let the polarizer pass
:math:`x` polarization and set either principal axis of the retarder at
:math:`45^\circ` to :math:`x`.  Background light travels from the observer's
side toward the window, reflects, and returns through the same elements.  Light
from the self-luminous object makes only the final one-way passage toward the
observer.

**Mathematical formulas used.**  A :math:`45^\circ` quarter-wave plate
converts linear light into circular light on the outward pass.  Problem 6.1-9
shows that mirror reflection reverses circular handedness.  On the return pass,
the same reciprocal plate converts that reversed circular state into the
linear state orthogonal to the original one.

**Worked derivation.**

1. The first polarizer converts arbitrary background light to linear
   :math:`x` polarization.
2. The quarter-wave plate resolves that field equally along its fast and slow
   axes and adds a :math:`90^\circ` relative phase, producing circular light.
3. Reflection at the glass reverses its handedness.
4. A second passage through the same retarder adds the complementary
   quarter-wave delay.  The returning field is therefore linear along
   :math:`y`, rather than :math:`x`.
5. The polarizer rejects this returned :math:`y` component, removing the
   specular background glare.  Object light approaching from behind the window
   is not first prepared by the polarizer; one component survives its single
   pass and remains visible, although attenuated.

Equivalently, the double passage through the retarder, together with the
handedness reversal, acts as a half-wave transformation between the outward
and return passes:

.. math::
   :label: fop-problem-6-1-10-round-trip

   \mathbf e_x\ \longrightarrow\ \mathbf e_R
   \ \xrightarrow{\rm reflection}\ \mathbf e_L
   \ \longrightarrow\ \mathbf e_y,
   \qquad P_x\mathbf e_y=0.

**Numbered result.**

.. math::
   :label: fop-problem-6-1-10-result

   \boxed{\text{linear polarizer}
   \;\rightarrow\;45^\circ\text{ quarter-wave plate}
   \;\rightarrow\;\text{window}.}

**Check.**  Without the quarter-wave plate, the reflected :math:`x` state
would pass back through the polarizer, so the retarder's role is essential.
The screen is **not** an optical isolator: all of its elements are reciprocal,
it suppresses only the prepared reflection path, and it attenuates desired
unpolarized object light.  A true isolator requires a nonreciprocal element
such as a Faraday rotator.

Problem 6.2-3 — Fresnel TE coefficient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  A TE-polarized plane wave is incident from medium
1 onto medium 2.  The media have characteristic impedances
:math:`\eta_1,\eta_2`, refractive indices :math:`n_1,n_2`, and propagation
angles :math:`\theta_1,\theta_2` measured from the interface normal.  Normalize
the incident electric amplitude to one and write the reflected and transmitted
amplitudes as :math:`r_s` and :math:`t_s`.

**Mathematical formulas used.**  Apply continuity of tangential
:math:`\mathbf E` and :math:`\mathbf H`, Snell's law, and
:math:`\eta_i=\eta_0/n_i` for nonmagnetic lossless dielectrics.  The algebra
uses :ref:`trigonometric and small-angle identities
<fop-formula-trigonometry>`.

**Worked derivation.**  For TE polarization the electric field is wholly
tangential.  The magnetic field has tangential magnitude
:math:`E\cos\theta/\eta`; its sign reverses for the reflected wave.  The two
boundary equations are therefore

.. math::
   :label: fop-problem-6-2-3-boundary-conditions

   1+r_s=t_s,
   \qquad
   \frac{\cos\theta_1}{\eta_1}(1-r_s)
   =\frac{\cos\theta_2}{\eta_2}t_s.

Insert :math:`t_s=1+r_s` into the magnetic-field equation and collect the
terms in :math:`r_s`:

.. math::
   :label: fop-problem-6-2-3-impedance-result

   r_s=
   \frac{\eta_2\sec\theta_2-\eta_1\sec\theta_1}
        {\eta_2\sec\theta_2+\eta_1\sec\theta_1},
   \qquad t_s=1+r_s.

This is the requested reflection relation, Eq. (6.2-6).  For nonmagnetic
dielectrics, substitute :math:`\eta_i=\eta_0/n_i` and cancel the common
factors to obtain the TE Fresnel coefficient.

**Numbered result.**

.. math::
   :label: fop-problem-6-2-3-result

   \boxed{r_s=
   \frac{n_1\cos\theta_1-n_2\cos\theta_2}
        {n_1\cos\theta_1+n_2\cos\theta_2}.}

For a finite beam, first Fourier-decompose its transverse field into an angular
spectrum of plane waves.  For each transverse wavevector, define its own plane
of incidence, resolve the field into TE and TM components, multiply by the
corresponding Fresnel coefficient, include the reflected propagation phase,
and inverse-transform the spectrum.  Replacing the whole beam by the coefficient
at its central angle is only a narrow-angle approximation and misses effects
such as the Goos--Hänchen shift.

**Check.**  At normal incidence this becomes
:math:`r_s=(n_1-n_2)/(n_1+n_2)`.  If :math:`n_1=n_2`, Snell's law gives
:math:`\theta_1=\theta_2` and the coefficient vanishes, as it must when there
is no optical discontinuity.

Problem 6.2-4 — Glass at 45 degrees
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Light travels from air,
:math:`n_1=1`, into glass, :math:`n_2=1.5`, at
:math:`\theta_1=45^\circ`.  For lossless media the power reflectance is the
squared magnitude of the electric-field reflection coefficient:
:math:`R_s=|r_s|^2` and :math:`R_p=|r_p|^2`.

**Mathematical formulas used.**  Use Snell's law and the TE/TM Fresnel
coefficients.  For the TM magnitude it is convenient to use
:math:`r_p=(n_2\cos\theta_1-n_1\cos\theta_2)/
(n_2\cos\theta_1+n_1\cos\theta_2)`; a different reflected-axis convention
may reverse its sign but not its power reflectance.

**Worked derivation.**  First find the transmitted angle:

.. math::
   :label: fop-problem-6-2-4-snell

   \theta_2=\sin^{-1}\!\left(\frac{n_1}{n_2}\sin45^\circ\right)
   =\sin^{-1}(0.4714045)=28.1255^\circ.

Now substitute :math:`\cos45^\circ=0.7071068` and
:math:`\cos28.1255^\circ=0.8819171`:

.. math::
   :label: fop-problem-6-2-4-amplitudes

   \begin{aligned}
   r_s&=\frac{1(0.7071068)-1.5(0.8819171)}
              {1(0.7071068)+1.5(0.8819171)}=-0.303337,\\
   r_p&=\frac{1.5(0.7071068)-1(0.8819171)}
              {1.5(0.7071068)+1(0.8819171)}=0.0920134.
   \end{aligned}

Squaring gives :math:`R_s=0.092013` and :math:`R_p=0.0084665`.  Unpolarized
light carries equal mean power in the two orthogonal modes, so its reflectance
is their arithmetic mean.

**Numbered result.**

.. math::
   :label: fop-problem-6-2-4-result

   \boxed{R_{\rm TE}=9.201\%,\qquad
          R_{\rm TM}=0.8467\%,\qquad
          R_{\rm unpol}=\frac{R_{\rm TE}+R_{\rm TM}}{2}=5.024\%.}

**Check.**  The TM reflectance is small because :math:`45^\circ` is fairly
close to the air--glass Brewster angle
:math:`\tan^{-1}(1.5)=56.31^\circ`.  Both values lie between zero and one, and
the unpolarized result lies exactly between them.

Problem 6.2-5 — Brewster geometry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  At the Brewster angle the TM reflection
coefficient vanishes.  Its numerator gives the supplied condition
:math:`n_1\sec\theta_1=n_2\sec\theta_2`; phase matching also requires
:math:`n_1\sin\theta_1=n_2\sin\theta_2`.

**Mathematical formulas used.**  The working uses Snell's law and
:ref:`trigonometric and small-angle identities
<fop-formula-trigonometry>`.

**Worked derivation.**  Rewrite the zero-reflection condition as
:math:`n_1\cos\theta_2=n_2\cos\theta_1`.  Together with Snell's law this gives

.. math::
   :label: fop-problem-6-2-5-ratio

   \frac{\sin\theta_1}{\sin\theta_2}
   =\frac{n_2}{n_1}
   =\frac{\cos\theta_2}{\cos\theta_1}.

Therefore :math:`\sin\theta_1\cos\theta_1
=\sin\theta_2\cos\theta_2`, or
:math:`\sin2\theta_1=\sin2\theta_2`.  For refraction into a different medium,
the nontrivial physical solution is
:math:`2\theta_1=\pi-2\theta_2`, hence
:math:`\theta_1+\theta_2=90^\circ`.  Put
:math:`\sin\theta_2=\cos\theta_1` into Snell's law:

.. math::
   :label: fop-problem-6-2-5-brewster

   n_1\sin\theta_B=n_2\cos\theta_B
   \quad\Longrightarrow\quad
   \tan\theta_B=\frac{n_2}{n_1}.

Since the reflected angle equals :math:`\theta_B`, the reflected and refracted
rays differ by :math:`180^\circ-(\theta_B+\theta_2)=90^\circ`.

**Numbered result.**

.. math::
   :label: fop-problem-6-2-5-result

   \boxed{\theta_B=\tan^{-1}\!\left(\frac{n_2}{n_1}\right),
   \qquad \theta_B+\theta_2=90^\circ.}

The transmitted TM electric field lies in the plane of incidence and is
perpendicular to its propagation direction.  It is consequently parallel to
the reflected-ray direction.  In the dipole-scattering picture, a dipole
cannot radiate along its own oscillation axis, explaining the missing TM
reflection.

**Check.**  For air to glass, the formula gives :math:`56.31^\circ` and Snell's
law gives :math:`33.69^\circ`; their sum is :math:`90^\circ` and direct
substitution makes the TM Fresnel numerator zero.

Problem 6.2-6 — TIR retardance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Reflection is from glass
:math:`n_1=1.5` into air :math:`n_2=1`.  Define
:math:`m=n_2/n_1=2/3` and measure phase as in
:math:`r_{s,p}=e^{j\phi_{s,p}}`.  The requested retardance of TM relative to TE
is :math:`\Gamma=\phi_p-\phi_s`.

**Mathematical formulas used.**  Above the critical angle, define
:math:`q=\sqrt{\sin^2\theta-m^2}`.  The unit-magnitude Fresnel coefficients
have phases
:math:`\phi_s=-2\tan^{-1}(q/\cos\theta)` and
:math:`\phi_p=-2\tan^{-1}[q/(m^2\cos\theta)]` in this phase convention.

**Worked derivation.**  The critical and specified angles are

.. math::
   :label: fop-problem-6-2-6-angles

   \theta_c=\sin^{-1}\!\left(\frac{1}{1.5}\right)=41.8103^\circ,
   \qquad
   \theta=1.2\theta_c=50.1724^\circ.

At this angle,
:math:`q=\sqrt{\sin^2(50.1724^\circ)-(2/3)^2}`.  Substitution into the two
phase expressions gives

.. math::
   :label: fop-problem-6-2-6-phases

   \phi_s=-61.52^\circ,
   \qquad
   \phi_p=-106.50^\circ,
   \qquad
   \Gamma=\phi_p-\phi_s=-44.98^\circ.

The negative sign says that, under the chosen phasor convention, the TM phase
lags the TE phase by :math:`44.98^\circ`.  Interchanging the definition of
retardance or the time-harmonic convention reverses the sign but not the
physical phase difference.

**Numbered result.**

.. math::
   :label: fop-problem-6-2-6-result

   \boxed{|\Gamma|=44.98^\circ\ \text{per reflection}.}

**Check.**  Both reflection magnitudes equal one, so TIR changes phase but not
power.  At :math:`\theta=\theta_c`, :math:`q=0` and both phases vanish; at
grazing incidence both approach the same limiting phase, so their difference
again tends to zero.

Problem 6.2-7 — Goos--Hänchen shift
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Two equal-amplitude TE plane waves in the denser
medium have incidence angles :math:`\theta` and
:math:`\theta+d\theta`.  Let :math:`x` run along the interface and let
:math:`k` be their common wavenumber.  Under TIR the reflection coefficient is
:math:`r_s=e^{j\phi_s(\theta)}`; write
:math:`d\phi_s=\dot\phi_s\,d\theta`.

**Mathematical formulas used.**  With
:math:`m=n_2/n_1=\sin\theta_c` and
:math:`q=\sqrt{\sin^2\theta-m^2}`, use the TE phase from Problem 6.2-6,
:math:`\phi_s=-2\tan^{-1}(q/\cos\theta)`.  The transverse wavevector is
:math:`k_x=k\sin\theta`, so
:math:`dk_x=k\cos\theta\,d\theta`.

**Worked derivation.**  Differentiate the TIR phase.  Since
:math:`dq/d\theta=\sin\theta\cos\theta/q`, the chain rule simplifies to

.. math::
   :label: fop-problem-6-2-7-phase-slope

   \dot\phi_s=\frac{d\phi_s}{d\theta}
   =-\frac{2\sin\theta}
           {\sqrt{\sin^2\theta-\sin^2\theta_c}}.

At the interface, the two incident waves form fringes proportional to
:math:`\cos^2(dk_x x/2)`.  Reflection adds :math:`d\phi_s` to the phase
difference, so the reflected fringes are proportional to
:math:`\cos^2[(dk_xx+d\phi_s)/2]`.  A reflected maximum therefore occurs where
the corresponding incident maximum would occur after a translation
:math:`\Delta` satisfying

.. math::
   :label: fop-problem-6-2-7-fringe-translation

   dk_x\Delta+d\phi_s=0
   \quad\Longrightarrow\quad
   \Delta=-\frac{1}{k\cos\theta}\frac{d\phi_s}{d\theta}.

A finite beam is a continuous superposition of just such neighboring angular
components.  The same spectral phase slope therefore displaces its reflected
envelope—the Goos--Hänchen effect.

**Numbered result.**  In the present sign convention,

.. math::
   :label: fop-problem-6-2-7-result

   \boxed{\Delta=
   \frac{2\tan\theta}
        {k\sqrt{\sin^2\theta-\sin^2\theta_c}}.}

Reversing the positive :math:`x` direction or phase convention reverses the
reported sign; the measurable magnitude is unchanged.

**Check.**  The result has dimensions :math:`1/k`, hence length.  The
two-plane-wave expression grows near the critical angle because the reflection
phase changes rapidly there; a real beam's finite angular width regularizes
that idealized divergence.

Problem 6.2-8 — Absorbing-medium reflection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Light is normally incident from free space onto a
nonmagnetic absorbing medium of real refractive index :math:`n` and intensity
absorption coefficient :math:`\alpha`.  Define

.. math::
   :label: fop-problem-6-2-8-complex-index

   \widetilde n=n-j\kappa,
   \qquad
   \kappa=\frac{\alpha c_0}{2\omega},
   \qquad
   \widetilde\eta=\frac{\eta_0}{\widetilde n}.

The factor two occurs because intensity decays as :math:`e^{-\alpha z}` while
field amplitude decays as :math:`e^{-\alpha z/2}`.

**Mathematical formulas used.**  Apply Maxwell's normal-incidence relation
:math:`H=E/\eta` and continuity of tangential :math:`E` and :math:`H` at the
boundary.

**Worked derivation.**  In one common fixed-laboratory-axis convention,
normalizing the incident field gives
:math:`1+r_E=t` and :math:`1-r_E=\widetilde n t`.  Solving,

.. math::
   :label: fop-problem-6-2-8-laboratory-coefficient

   r_E=\frac{1-\widetilde n}{1+\widetilde n}.

The problem defines the reflected Jones component along the reflected wave's
local transverse axis, which is opposite to this fixed-axis amplitude.  Thus
:math:`r=-r_E`, and insertion of :math:`\widetilde n` gives the requested
form.

**Numbered result.**

.. math::
   :label: fop-problem-6-2-8-result

   \boxed{r=
   \frac{(n-j\alpha c_0/2\omega)-1}
        {(n-j\alpha c_0/2\omega)+1}.}

The convention-independent power reflectance is

.. math::
   :label: fop-problem-6-2-8-power

   R=|r|^2=
   \frac{(n-1)^2+\kappa^2}{(n+1)^2+\kappa^2}.

**Check.**  When :math:`\alpha=0`, this reduces in magnitude to the ordinary
normal-incidence Fresnel result.  When :math:`n=1` and :math:`\alpha=0`, the
interface disappears and :math:`r=0`; as absorption becomes very large,
:math:`R\rightarrow1`.

Problem 6.3-1 — Quartz retardation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Quartz is positive uniaxial with
:math:`n_e=1.553`, :math:`n_o=1.544`, and vacuum wavelength
:math:`\lambda_0=633\ \mathrm{nm}`.  Retardation is largest when the
wavevector is perpendicular to the optic axis, because the two eigenmodes then
sample :math:`n_e` and :math:`n_o` directly.

**Mathematical formulas used.**  The relative phase accumulated through
thickness :math:`d` is
:math:`\Gamma=k_0(n_e-n_o)d=2\pi(n_e-n_o)d/\lambda_0`.

**Worked derivation.**  The maximum birefringence is
:math:`\Delta n=n_e-n_o=0.009`.  For :math:`d=1\ \mathrm{mm}`,

.. math::
   :label: fop-problem-6-3-1-per-millimetre

   \Gamma_{1\,\mathrm{mm}}
   =2\pi\frac{0.009(1.000\times10^{-3})}{633\times10^{-9}}
   =89.33\ \mathrm{rad}
   =2\pi(14.218).

Thus one millimetre produces 14.218 full retardation cycles.  A quarter-wave
retarder needs an odd multiple of :math:`\pi/2`:

.. math::
   :label: fop-problem-6-3-1-quarter-wave-condition

   \frac{2\pi\Delta n d}{\lambda_0}
   =\frac{(2q+1)\pi}{2},
   \qquad q=0,1,2,\ldots

Solving gives all possible thicknesses.  Values with even :math:`q` have
retardance :math:`+\pi/2` modulo :math:`2\pi`; odd :math:`q` give the
complementary :math:`-\pi/2` action.

**Numbered result.**

.. math::
   :label: fop-problem-6-3-1-result

   \boxed{d_q=\frac{(2q+1)\lambda_0}{4\Delta n}
   =(2q+1)(17.58\ \mathrm{\mu m}),
   \qquad q=0,1,2,\ldots}

The thinnest plate is therefore :math:`17.58\ \mathrm{\mu m}`; the next is
:math:`52.75\ \mathrm{\mu m}`.

**Check.**  Substituting the first thickness gives
:math:`\Delta n d/\lambda_0=1/4`, hence :math:`\Gamma=\pi/2`.  The expression
has units of length and every increase by
:math:`\lambda_0/(2\Delta n)` adds exactly :math:`\pi` of retardance.

Problem 6.3-2 — Maximum extraordinary walk-off
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Let :math:`\theta` be the angle from the optic axis
to the extraordinary wavevector :math:`\mathbf k`, and :math:`\phi` the angle
from that axis to the Poynting vector :math:`\mathbf S`.  Their difference
:math:`\rho=\theta-\phi` is the extraordinary ray walk-off.  For quartz,
:math:`n_e=1.553` and :math:`n_o=1.544`.

**Mathematical formulas used.**  The normal to the extraordinary
:math:`k`-surface gives

.. math::
   :label: fop-problem-6-3-2-ray-wave-relation

   \tan\phi=r\tan\theta,
   \qquad r=\left(\frac{n_o}{n_e}\right)^2.

Maximize :math:`\rho` using the :ref:`stationary-value condition
<fop-formula-stationary>`.

**Worked derivation.**  Differentiate
:math:`\rho(\theta)=\theta-\tan^{-1}(r\tan\theta)`:

.. math::
   :label: fop-problem-6-3-2-stationary-condition

   \frac{d\rho}{d\theta}
   =1-\frac{r\sec^2\theta}{1+r^2\tan^2\theta}=0.

Let :math:`u=\tan\theta`.  Rearrangement gives
:math:`1+r^2u^2=r(1+u^2)`, and because :math:`r\ne1`,
:math:`u^2=1/r`.  In the first quadrant,

.. math::
   :label: fop-problem-6-3-2-optimum-angle

   \tan\theta_{\max}=\frac{1}{\sqrt r}=\frac{n_e}{n_o},
   \qquad
   \tan\phi_{\max}=\sqrt r=\frac{n_o}{n_e}.

The two tangents are reciprocals, so
:math:`\phi_{\max}=90^\circ-\theta_{\max}`.  Numerically,
:math:`\theta_{\max}=45.1665^\circ`,
:math:`\phi_{\max}=44.8335^\circ`, and their difference is
:math:`0.3330^\circ`.

**Numbered result.**

.. math::
   :label: fop-problem-6-3-2-result

   \boxed{\theta_{\max}=45.1665^\circ\ \text{from the optic axis},
   \qquad \rho_{\max}=0.3330^\circ.}

**Check.**  At :math:`\theta=0^\circ` or :math:`90^\circ`, symmetry forces
:math:`\mathbf S\parallel\mathbf k`, so the walk-off vanishes.  If
:math:`n_e=n_o`, then :math:`r=1` and it vanishes at every angle, as required
for an isotropic medium.

Problem 6.3-3 — Double refraction in quartz
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  An unpolarized wave in air strikes quartz at
:math:`\theta_i=30^\circ`.  Quartz has :math:`n_o=1.544` and
:math:`n_e=1.553`.  The optic axis lies in the incidence plane and is
perpendicular to the incident wavevector; because an optic axis is an
unoriented line, take it at :math:`-60^\circ` from the inward surface normal.
Angles :math:`\theta_o` and :math:`\theta_e` below are wavevector angles from
that normal.

**Mathematical formulas used.**  Tangential phase matching requires
:math:`n\sin\theta=\sin\theta_i`.  For the extraordinary wave, whose
wavevector is at :math:`\gamma=\theta_e+60^\circ` to the optic axis, use

.. math::
   :label: fop-problem-6-3-3-extraordinary-index

   \frac{1}{n^2(\gamma)}
   =\frac{\cos^2\gamma}{n_o^2}
   +\frac{\sin^2\gamma}{n_e^2}.

The extraordinary ray direction :math:`\phi` measured from the optic axis
satisfies :math:`\tan\phi=(n_o/n_e)^2\tan\gamma`.

**Worked derivation.**  The ordinary refractive index is direction
independent, hence

.. math::
   :label: fop-problem-6-3-3-ordinary-angle

   \theta_o=\sin^{-1}\!\left(\frac{\sin30^\circ}{1.544}\right)
   =18.89496^\circ.

Its spherical :math:`k`-surface makes the ordinary Poynting vector parallel to
its wavevector, so the ordinary wave and ray have this same direction.

For the extraordinary component, :math:`n` depends on the unknown direction;
solve the single scalar equation

.. math::
   :label: fop-problem-6-3-3-extraordinary-phase-match

   n(\theta_e+60^\circ)\sin\theta_e=sin30^\circ.

Iteration gives
:math:`\theta_e=18.78566^\circ`,
:math:`\gamma=78.78566^\circ`, and
:math:`n(\gamma)=1.552657`.  The normal to the extraordinary
:math:`k`-surface then gives
:math:`\phi=78.65792^\circ` from the optic axis.  Since the axis is at
:math:`-60^\circ`, the extraordinary ray is at
:math:`78.65792^\circ-60^\circ=18.65792^\circ` from the surface normal.

**Numbered result.**

.. math::
   :label: fop-problem-6-3-3-result

   \boxed{\begin{array}{c|cc}
   &\text{wavevector from normal}&\text{ray from normal}\\ \hline
   \text{ordinary}&18.89496^\circ&18.89496^\circ\\
   \text{extraordinary}&18.78566^\circ&18.65792^\circ
   \end{array}}

**Check.**  Substitution gives
:math:`1.544\sin18.89496^\circ=0.5` and
:math:`1.552657\sin18.78566^\circ=0.5`, confirming tangential phase matching.
The extraordinary ray differs from its wavevector by
:math:`0.12774^\circ`, whereas the ordinary ray has zero walk-off.

Problem 6.3-4 — Geometry for largest separation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Let a parallel-sided plate of a positive uniaxial
crystal have thickness :math:`L`, ordinary index :math:`n_o`, and principal
extraordinary index :math:`n_e>n_o`.  Send the light normally into the plate,
so both transmitted wavevectors are normal to its faces.  Put the optic axis
in the plane in which the beam separation is wanted, and let :math:`\theta`
be the angle from that axis to the common wavevector.  The ordinary ray is
parallel to its wavevector.  The extraordinary ray makes an angle
:math:`\phi` with the optic axis and therefore walks away from the ordinary
ray by :math:`\rho=\theta-\phi`.

**Mathematical formulas used.**  For a positive uniaxial crystal, the
extraordinary ray and wave-normal angles obey

.. math::
   :label: fop-problem-6-3-4-ray-angle

   \tan\phi=\left(\frac{n_o}{n_e}\right)^2\tan\theta .

Problem 6.3-2 showed that the stationary (and maximum) walk-off occurs when
:math:`\tan\theta=n_e/n_o`.  A ray crossing a distance :math:`L` at angle
:math:`\rho` to the face normal acquires lateral displacement
:math:`\Delta x=L\tan\rho`.

**Worked derivation.**  At the optimum orientation,

.. math::
   :label: fop-problem-6-3-4-optimum-angles

   \theta_* = \tan^{-1}\!\left(\frac{n_e}{n_o}\right),
   \qquad
   \phi_* = \tan^{-1}\!\left(\frac{n_o}{n_e}\right)
           =90^\circ-\theta_* .

Consequently, the largest ray--wavevector angle is

.. math::
   :label: fop-problem-6-3-4-max-walkoff

   \rho_{\max}=\theta_*-\phi_*
   =2\tan^{-1}\!\left(\frac{n_e}{n_o}\right)-90^\circ .

The ordinary ray travels straight through the plate.  The extraordinary ray
tilts by :math:`\rho_{\max}` *toward the optic axis*, so the two spots on the
second face are separated by :math:`L\tan\rho_{\max}`.  At that parallel exit
face both wavevectors have zero tangential component; after refraction into
air the two output beams are again normal to the faces and parallel to one
another.  The separation produced inside the plate remains.

**Numbered result.**  The required cut and maximum lateral separation are

.. math::
   :label: fop-problem-6-3-4-result

   \boxed{\begin{gathered}
   \text{optic-axis angle to the plate normal:}\quad
   \theta_*=\tan^{-1}(n_e/n_o),\\
   \Delta x_{\max}=L\tan\!\left[
   2\tan^{-1}(n_e/n_o)-90^\circ\right].
   \end{gathered}}

**Check.**  If :math:`n_e=n_o`, the material becomes isotropic;
:math:`\theta_*=45^\circ`, :math:`\rho_{\max}=0`, and the separation
vanishes.  The result also scales linearly with :math:`L`, as a geometrical
displacement must.  Choosing the optic axis either parallel or perpendicular
to the wavevector gives zero walk-off, confirming that the optimum lies
between those orientations.

Problem 6.3-5 — One-centimetre LiNbO3 plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The He--Ne wavelength is
:math:`\lambda_0=633\ \mathrm{nm}`.  The LiNbO\ :sub:`3` plate has
:math:`n_o=2.20`, :math:`n_e=2.29`, and thickness
:math:`L=1.00\ \mathrm{cm}`.  Its optic axis is at
:math:`\theta=45^\circ` to the plate normal.  Normal incidence makes the
ordinary and extraordinary *wavevectors* normal to the faces, but the
extraordinary energy ray walks toward the optic axis.  Unpolarized input is
resolved into incoherent ordinary and extraordinary components; the same
geometry and phase difference apply to a coherent input containing both
components.

**Mathematical formulas used.**  For a wavevector at angle :math:`\theta`
to the optic axis, the extraordinary phase index and ray angle are

.. math::
   :label: fop-problem-6-3-5-formulas

   \frac{1}{n^2(\theta)}=
   \frac{\cos^2\theta}{n_o^2}+\frac{\sin^2\theta}{n_e^2},
   \qquad
   \tan\phi=\left(\frac{n_o}{n_e}\right)^2\tan\theta .

Thus the walk-off is :math:`\rho=\theta-\phi`, the lateral separation at the
exit face is :math:`\Delta x=L\tan\rho`, and the relative phase accumulated
between the extraordinary and ordinary waves is

.. math::
   :label: fop-problem-6-3-5-retardance-formula

   \Gamma=\frac{2\pi L}{\lambda_0}\,[n(\theta)-n_o].

**Worked derivation.**  First calculate the phase index without prematurely
rounding it:

.. math::
   :label: fop-problem-6-3-5-index

   n(45^\circ)=
   \left[\frac{1/2}{(2.20)^2}+\frac{1/2}{(2.29)^2}\right]^{-1/2}
   =2.2436473.

The extraordinary ray direction and walk-off are then

.. math::
   :label: fop-problem-6-3-5-walkoff

   \phi=\tan^{-1}\!\left[\left(\frac{2.20}{2.29}\right)^2\right]
   =42.7052^\circ,
   \qquad
   \rho=45^\circ-\phi=2.29479^\circ.

It follows that

.. math::
   :label: fop-problem-6-3-5-shift

   \Delta x=(10.0\ \mathrm{mm})\tan(2.29479^\circ)
   =0.40073\ \mathrm{mm}.

For the retardation,

.. math::
   :label: fop-problem-6-3-5-retardance

   \frac{\Gamma}{2\pi}
   =\frac{(2.2436473-2.20)(0.0100\ \mathrm{m})}
          {633\times10^{-9}\ \mathrm{m}}
   =689.53097.

The integer 689 represents complete cycles.  The observable residual is
:math:`0.53097` cycle, or :math:`191.15^\circ`, although the unwrapped phase
is :math:`\Gamma=4332.45\ \mathrm{rad}`.

**Numbered result.**  At the output face,

.. math::
   :label: fop-problem-6-3-5-result

   \boxed{\Delta x=0.4007\ \mathrm{mm},\qquad
   \Gamma=2\pi(689.531)=4332.45\ \mathrm{rad}
   \equiv191.15^\circ\pmod{360^\circ}.}

**Check.**  The calculated index satisfies
:math:`n_o<n(45^\circ)<n_e`, as it must.  Because this is a positive
uniaxial crystal, the extraordinary ray bends toward the optic axis, giving
the positive shift above.  Finally,
:math:`10\ \mathrm{mm}\times\tan(2.3^\circ)\approx0.40\ \mathrm{mm}`, an
independent magnitude check.

Problem 6.3-6 — Conical refraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Consider a parallel-sided biaxial-crystal plate
of thickness :math:`L`.  One optic axis is normal to both faces, and a narrow
ray in air is normally incident along that axis.  Let :math:`\beta` denote
the semi-angle of the cone of energy-flow directions inside the crystal.
Wavevector :math:`\mathbf k` specifies phase propagation, whereas the ray
direction is the group velocity (or Poynting-vector direction); in an
anisotropic crystal these directions need not coincide.

**Mathematical formulas used.**  At fixed frequency the group velocity is
normal to the constant-frequency :math:`k` surface,

.. math::
   :label: fop-problem-6-3-6-group-velocity

   \mathbf v_g=\nabla_{\mathbf k}\omega,
   \qquad \mathbf v_g\perp\{\mathbf k:\omega(\mathbf k)=\text{constant}\}.

The radius reached by a ray that crosses axial thickness :math:`L` at cone
angle :math:`\beta` is simply :math:`R=L\tan\beta`.

**Worked derivation.**  Away from an optic axis, a specified wavevector
intersects two smooth sheets of the biaxial :math:`k` surface and therefore
has two normal modes.  On an optic axis those sheets touch.  Near the contact
point their common surface is locally conical, so it has not one unique
normal but a continuous family of normals indexed by azimuth.  The normally
incident field can therefore excite a continuum of energy-flow directions.
Those normals all make the same semi-angle :math:`\beta` with the optic axis:
the refracted rays fill a cone rather than separating into only two rays.

After propagating through the plate, the conical rays intersect the second
face on a circle of radius

.. math::
   :label: fop-problem-6-3-6-ring-radius

   R=L\tan\beta .

All of these modes nevertheless share the axial wavevector at the conical
contact point.  Hence its tangential component at the parallel output face is
zero for every azimuth.  Tangential phase matching makes every ray refract
normally into air.  The emerging rays are parallel, but originate around the
circle, forming a hollow cylindrical bundle; a transverse screen records a
bright ring.

**Numbered result.**  The geometrical outcome is

.. math::
   :label: fop-problem-6-3-6-result

   \boxed{\text{inside: a ray cone of semi-angle }\beta;qquad
   \text{outside: a parallel hollow cylinder of radius }L\tan\beta.}

**Check.**  Rotational symmetry around the chosen optic axis requires a
circle rather than a preferred transverse direction.  In the isotropic or
uniaxial limiting case the conical contact disappears,
:math:`\beta\rightarrow0`, and the ring collapses to the ordinary on-axis
spot.  Doubling :math:`L` doubles the ring radius, consistent with straight
ray propagation inside the plate.

Problem 6.6-1 — Circular dichroic selector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Use the book's circular-polarization convention

.. math::
   :label: fop-problem-6-6-1-circular-basis

   \mathbf e_R=\frac{1}{\sqrt2}\begin{bmatrix}1\\j\end{bmatrix},
   \qquad
   \mathbf e_L=\frac{1}{\sqrt2}\begin{bmatrix}1\\-j\end{bmatrix}.

An ideal right-circular dichroic selector transmits the RCP component with
unit amplitude and absorbs the LCP component completely.  In the circular
basis its Jones matrix is therefore
:math:`T_c=\operatorname{diag}(1,0)`.

**Mathematical formulas used.**  If
:math:`C=[\mathbf e_R\;\mathbf e_L]` changes circular-basis components into
linear-basis components, then :math:`T=CT_cC^\dagger`.  Equivalently, an
ideal selector is the outer-product projector
:math:`T=\mathbf e_R\mathbf e_R^\dagger`.

**Worked derivation.**  Carrying out the outer product gives

.. math::
   :label: fop-problem-6-6-1-projector

   T=\mathbf e_R\mathbf e_R^\dagger
   =\frac12
   \begin{bmatrix}1\\j\end{bmatrix}
   \begin{bmatrix}1&-j\end{bmatrix}
   =\frac12\begin{bmatrix}1&-j\\j&1\end{bmatrix}.

For an arbitrary incident Jones vector
:math:`\mathbf J=[A_x\;A_y]^T`,

.. math::
   :label: fop-problem-6-6-1-arbitrary-input

   T\mathbf J
   =\frac12\begin{bmatrix}A_x-jA_y\\jA_x+A_y\end{bmatrix}
   =\mathbf e_R\frac{A_x-jA_y}{\sqrt2}.

Thus every *nonzero transmitted field* is proportional to
:math:`\mathbf e_R` and is right circularly polarized.  The qualification is
important: a passive selector cannot produce light from a pure LCP input;
that input is extinguished rather than converted with nonzero efficiency.

**Numbered result.**  In the linear :math:`x,y` basis, the required Jones
matrix is

.. math::
   :label: fop-problem-6-6-1-result

   \boxed{T_R=\frac12\begin{bmatrix}1&-j\\j&1\end{bmatrix}.}

**Check.**  Direct multiplication gives
:math:`T_R\mathbf e_R=\mathbf e_R`,
:math:`T_R\mathbf e_L=\mathbf0`, and :math:`T_R^2=T_R`.  These are exactly
the transmission, absorption, and projector properties required of the
ideal circular dichroic device.

Problem 6.6-2 — Many weakly rotated polarizers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The incident field is linearly polarized along
:math:`x`, with normalized Jones vector
:math:`\mathbf u_0=[1\;0]^T`.  There are :math:`N` ideal linear polarizers.
The :math:`m`th transmission axis is at
:math:`\alpha_m=m\theta`, where
:math:`\theta=\pi/(2N)` and :math:`m=1,\ldots,N`.  Define a unit vector along
that axis by

.. math::
   :label: fop-problem-6-6-2-axis-vector

   \mathbf u_m=\begin{bmatrix}\cos(m\theta)\\\sin(m\theta)\end{bmatrix}.

The final axis is :math:`\alpha_N=N\theta=\pi/2`, so it points along
:math:`y`.

**Mathematical formulas used.**  An ideal polarizer is a projector,
:math:`P_m=\mathbf u_m\mathbf u_m^T`.  Adjacent axes differ by
:math:`\theta`, and hence

.. math::
   :label: fop-problem-6-6-2-overlap

   \mathbf u_m^T\mathbf u_{m-1}
   =\cos(m\theta)\cos[(m-1)\theta]
    +\sin(m\theta)\sin[(m-1)\theta]
   =\cos\theta.

Each projection therefore multiplies the field amplitude by
:math:`\cos\theta` and aligns it with the new axis.

**Worked derivation.**  After the first polarizer,
:math:`\mathbf J_1=P_1\mathbf u_0=\cos\theta\,\mathbf u_1`.  If after
:math:`m-1` polarizers
:math:`\mathbf J_{m-1}=\cos^{m-1}\theta\,\mathbf u_{m-1}`, then

.. math::
   :label: fop-problem-6-6-2-induction

   \mathbf J_m=P_m\mathbf J_{m-1}
   =\cos^{m-1}\theta\,\mathbf u_m
      (\mathbf u_m^T\mathbf u_{m-1})
   =\cos^m\theta\,\mathbf u_m.

Induction to :math:`m=N` proves that the output points along :math:`y` and
has amplitude factor :math:`\cos^N[\pi/(2N)]`.  The power transmittance is
the square of that factor.  To evaluate the large-:math:`N` limit, use
:math:`\ln\cos x=-x^2/2+O(x^4)`:

.. math::
   :label: fop-problem-6-6-2-limit

   \ln\!\left\{\cos^N\!\left(\frac{\pi}{2N}\right)\right\}
   =N\ln\cos\!\left(\frac{\pi}{2N}\right)
   =-\frac{\pi^2}{8N}+O(N^{-3})\longrightarrow0.

Exponentiating shows that both the amplitude factor and the power
transmittance tend to unity even though the polarization turns through
:math:`90^\circ`.

**Numbered result.**  The transmitted field and power are

.. math::
   :label: fop-problem-6-6-2-result

   \boxed{\mathbf J_N=
   \cos^N\!\left(\frac{\pi}{2N}\right)\begin{bmatrix}0\\1\end{bmatrix},
   \qquad
   \frac{I_N}{I_0}=\cos^{2N}\!\left(\frac{\pi}{2N}\right),
   \qquad
   \lim_{N\to\infty}\frac{I_N}{I_0}=1.}

**Check.**  For :math:`N=1`, the single polarizer is crossed with the input,
and the formula gives zero transmission.  For :math:`N=2`, the axes are at
:math:`45^\circ` and :math:`90^\circ`; the amplitude is
:math:`(1/\sqrt2)^2=1/2` and the power is :math:`1/4`, agreeing with two
successive applications of Malus's law.
