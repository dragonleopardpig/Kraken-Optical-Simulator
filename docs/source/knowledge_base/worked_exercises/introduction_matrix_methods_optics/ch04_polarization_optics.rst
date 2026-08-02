Chapter IV: Matrices in Polarization Optics
===========================================

Source: Gerrard and Burch, *Introduction to Matrix Methods in Optics* (1975),
Chapter IV.  Jones vectors are normalized only when an absolute intensity is
needed; common phase factors are discarded.

Illustrative problems
---------------------

.. rubric:: Problem 4.1 — Malus's law and three-polarizer transmission

An ideal polarizer with pass direction
:math:`\mathbf p=(\cos\theta,\sin\theta)^T` has Jones matrix
:math:`J_p=\mathbf p\mathbf p^T`.  Acting on a unit field polarized along
:math:`x` gives transmitted amplitude :math:`\cos\theta`, hence

.. math::

   \boxed{I=\cos^2\theta}.

For initially crossed polarizers with an intermediate polarizer at angle
:math:`\phi` from the extinction setting, successive projection gives

.. math::

   I=\cos^2\phi\sin^2\phi
    =\boxed{\frac14\sin^2(2\phi)}.

The result vanishes with no rotation and peaks at :math:`1/4` for the middle
polarizer at :math:`45^\circ`.

.. rubric:: Problem 4.2 — Three polaroids illuminated by unpolarized light

The first polarizer transmits half the unpolarized incident intensity.  The
relative rotations of the next two pass planes are :math:`12^\circ` and
:math:`24^\circ`, so repeated use of Malus's law gives

.. math::

   \boxed{\frac{I_{out}}{I_{in}}
   =\frac12\cos^2(12^\circ)\cos^2(24^\circ)
   \simeq0.399}.

Using the book's two-decimal trigonometric values gives 0.396.  Mueller
calculus is required for the first step because the entering beam is
unpolarized; after that projection, Jones calculus gives the same result.

.. rubric:: Problem 4.3 — Orientation and axes of a polarization ellipse

For :math:`E_x=H\cos\omega t` and
:math:`E_y=K\cos(\omega t+\Delta)`, form

.. math::

   I=H^2+K^2,\qquad Q=H^2-K^2,\qquad
   U=2HK\cos\Delta.

The ellipse orientation is therefore

.. math::

   \boxed{\tan2\alpha=\frac{U}{Q}
   =\frac{2HK\cos\Delta}{H^2-K^2}}.

Its squared semiaxes are the eigenvalues of the real polarization quadratic
form:

.. math::

   \boxed{a^2,b^2=
   \frac12\left[I\pm\sqrt{Q^2+U^2}\right]}.

The sign of :math:`V=2HK\sin\Delta` selects handedness but does not change the
axis lengths.

.. rubric:: Problem 4.4 — Recovering an ellipse from extinction settings

Multiply the unknown Jones vector by the quarter-wave-plate matrix at
:math:`30^\circ` and the polarizer projector at :math:`60^\circ`.  Extinction
requires both components of the final vector to vanish, so the ratio of the
two unknown incident components is fixed.  Separating its real and imaginary
parts gives the amplitude and phase parameters; substituting them into the
ellipse formulas of Problem 4.3 yields

.. math::

   \boxed{\text{minor axis at }30^\circ},
   \qquad
   \boxed{a/b=\sqrt3}.

Reapplying the plate and analyzer to this recovered Jones vector gives the
zero vector, providing a direct check.

.. rubric:: Problem 4.5 — Circular light through quarter- and eighth-wave plates

Use a normalized right-circular input and a vertical fast axis.  The
quarter-wave plate cancels the incident quadrature, leaving equal real
components of opposite sign.  The output is therefore

.. math::

   \boxed{\text{linear polarization at }-45^\circ}.

The eighth-wave plate leaves a relative phase of :math:`135^\circ`.  The
result is a right-handed ellipse whose quadratic form can be written, after
normalization,

.. math::

   x^2-\sqrt2xy+y^2=1.

Its major axis lies at :math:`45^\circ` and its axial ratio is
:math:`\boxed{1+\sqrt2}`.  A unitary retarder preserves total intensity in
both cases.

.. rubric:: Problem 4.6 — Analyzer angle for a phase-shifted equal-amplitude wave

The field has equal component amplitudes and phase difference :math:`\pi/4`.
Projection onto a polarizer at angle :math:`\theta` gives

.. math::

   I(\theta)=A^2\left[1+rac{1}{\sqrt2}\sin2\theta\right].

Thus the maximum occurs at :math:`\boxed{\theta=45^\circ}`.  With the
pass-plane along :math:`y`, :math:`I_y=A^2`; therefore

.. math::

   \boxed{\frac{I_{max}}{I_y}=1+\frac1{\sqrt2}}.

The derivative vanishes at :math:`45^\circ`, and the negative second
derivative confirms a maximum.

.. rubric:: Problem 4.7 — Elliptical beam through a linear polarizer

Choose the ellipse axes as coordinates.  A right-handed field may be written
:math:`(H,iK)^T`; a polarizer at angle :math:`\alpha` projects it onto
:math:`(\cos\alpha,\sin\alpha)^T`.  The projected complex amplitude is
:math:`H\cos\alpha+iK\sin\alpha`, so

.. math::

   \boxed{I=H^2\cos^2\alpha+K^2\sin^2\alpha}.

The cross term vanishes because the components are in quadrature.  The limits
:math:`\alpha=0` and :math:`\pi/2` recover the major- and minor-axis
intensities.

.. rubric:: Problem 4.8 — Photoelasticity with Jones matrices

Model the stressed specimen as a linear retarder with optic-axis angle
:math:`\alpha` and retardance :math:`\delta=csd`, where :math:`s` is strain,
:math:`d` thickness, and :math:`c` the strain-optical coefficient.  Cascade
the entrance polarizer, specimen, and crossed analyzer.

For the book's polarizers at :math:`+45^\circ` and :math:`-45^\circ`, matrix
multiplication gives

.. math::

   \boxed{\frac{I}{I_0}=\cos^2(2\alpha)
   \sin^2\left(\frac\delta2\right)}.

For horizontal and vertical crossed polarizers the complementary convention
is :math:`\sin^2(2\alpha)\sin^2(\delta/2)`.  Adding mutually perpendicular
quarter-wave plates creates a circular polariscope and removes the axis-angle
factor:

.. math::

   \boxed{\frac{I}{I_0}=\sin^2\left(\frac\delta2\right)}.

Zero strain gives extinction, while a half-wave retardance gives the maximum
available transmission.
