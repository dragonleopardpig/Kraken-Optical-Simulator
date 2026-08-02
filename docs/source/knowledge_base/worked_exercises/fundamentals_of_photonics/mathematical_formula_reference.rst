Mathematical Formula Reference
==============================

This page collects the mathematical identities used repeatedly in the worked
solutions.  A solution links to the relevant identity before applying it, so
the algebra can be followed without guessing which rule was used.  Symbols
are defined locally in each exercise; the symbols on this page are generic.

.. _fop-formula-algebra:

Algebra and dimensional checks
------------------------------

An equation may be rearranged by applying the same invertible operation to
both sides.  For nonzero :math:`a`, the linear and quadratic solutions are

.. math::
   :label: fop-formula-linear-quadratic

   ax+b=0\Rightarrow x=-\frac{b}{a},\qquad
   ax^2+bx+c=0\Rightarrow
   x=\frac{-b\pm\sqrt{b^2-4ac}}{2a}.

Every additive term in a physical equation must have the same dimensions.
The final unit is therefore an independent check on an algebraic result.

.. _fop-formula-product-chain:

Product, quotient, and chain rules
----------------------------------

For differentiable functions :math:`f(x)` and :math:`g(x)`,

.. math::
   :label: fop-formula-differentiation-rules

   \frac{d}{dx}(fg)=f'g+fg',\qquad
   \frac{d}{dx}\!\left(\frac{f}{g}\right)
   =\frac{f'g-fg'}{g^2},\qquad
   \frac{d}{dx}f(g(x))=f'(g(x))g'(x).

The last identity is the **chain rule**.  Applying it to a square root gives

.. math::
   :label: fop-formula-square-root-derivative

   \frac{d}{dx}\sqrt{u(x)}
   =\frac{u'(x)}{2\sqrt{u(x)}}.

.. _fop-formula-stationary:

Stationary-value condition
--------------------------

If a differentiable scalar function :math:`F(x)` is stationary at an
interior point :math:`x=x_0`, its first derivative vanishes there:

.. math::
   :label: fop-formula-stationary-condition

   \left.\frac{dF}{dx}\right|_{x=x_0}=0.

The condition identifies minima, maxima, and stationary inflection points;
the second derivative or physical context distinguishes them.  For a
constraint :math:`g(\boldsymbol{x})=0`, the equivalent Lagrange-multiplier
condition is

.. math::
   :label: fop-formula-lagrange-multiplier

   \nabla F+\lambda\nabla g=0,\qquad g=0.

.. _fop-formula-fermat:

Optical path and Fermat's principle
-----------------------------------

The optical path length (OPL) along a piecewise homogeneous path is

.. math::
   :label: fop-formula-optical-path

   \mathcal L=\int_A^B n(\boldsymbol r)\,ds
   \quad\longrightarrow\quad
   \mathcal L=\sum_i n_i\ell_i.

Fermat's principle states that the physical ray makes the OPL stationary:
:math:`\delta\mathcal L=0`.  It need not be a strict minimum.

.. _fop-formula-trigonometry:

Trigonometry and small-angle formulas
-------------------------------------

For a right triangle with opposite side :math:`a`, adjacent side :math:`b`,
and hypotenuse :math:`r=\sqrt{a^2+b^2}`,

.. math::
   :label: fop-formula-right-triangle

   \sin\theta=\frac{a}{r},\qquad
   \cos\theta=\frac{b}{r},\qquad
   \tan\theta=\frac{a}{b},\qquad
   \sin^2\theta+\cos^2\theta=1.

The first nonzero Taylor terms about :math:`x=0` are

.. math::
   :label: fop-formula-small-angle

   \sin x=x+O(x^3),\quad
   \tan x=x+O(x^3),\quad
   \cos x=1-\frac{x^2}{2}+O(x^4),\quad
   \sqrt{1+x}=1+\frac{x}{2}+O(x^2).

These approximations require a dimensionless :math:`|x|\ll1` (angles in
radians).

.. _fop-formula-solid-angle:

Solid angle and circular cones
------------------------------

On a unit sphere, polar angle :math:`\theta` and azimuth :math:`\phi` give
the differential solid angle :math:`d\Omega=\sin\theta\,d\theta\,d\phi`.
The solid angle of a circular cone with half-angle :math:`\alpha` is therefore

.. math::
   :label: fop-formula-circular-cone-solid-angle

   \Omega_{\mathrm{cone}}
   =\int_0^{2\pi}\!\int_0^\alpha
      \sin\theta\,d\theta\,d\phi
   =2\pi(1-\cos\alpha).

The full sphere contains :math:`4\pi` steradians.  For an isotropic source,
the fraction of its power in any non-overlapping collection of directions is
the collection's total solid angle divided by :math:`4\pi`.

.. _fop-formula-exponentials:

Exponentials, logarithms, and complex phasors
---------------------------------------------

Euler's identity and the elementary exponential derivatives are

.. math::
   :label: fop-formula-euler-exponential

   e^{j\phi}=\cos\phi+j\sin\phi,\qquad
   \frac{d}{dx}e^{ax}=ae^{ax},\qquad
   \frac{d}{dx}\ln x=\frac1x.

Consequently, multiplying a phasor by :math:`e^{j\phi}` adds phase
:math:`\phi`, while its magnitude is unchanged.

.. _fop-formula-integration:

Integration identities
----------------------

Integration by parts, substitution, and the Gaussian integral are

.. math::
   :label: fop-formula-integration-identities

   \int u\,dv=uv-\int v\,du,\qquad
   \int f(g(x))g'(x)\,dx=\int f(u)\,du,\qquad
   \int_{-\infty}^{\infty}e^{-ax^2}\,dx=\sqrt{\frac{\pi}{a}}
   \quad(\Re a>0).

For a normalized density :math:`p(x)`, always check
:math:`\int p(x)\,dx=1` before using it in an expectation.

.. _fop-formula-fourier:

Fourier transform, convolution, and correlation
------------------------------------------------

With the frequency convention used here,

.. math::
   :label: fop-formula-fourier-pair

   \widetilde f(\nu)=\int_{-\infty}^{\infty}f(t)e^{-j2\pi\nu t}\,dt,
   \qquad
   f(t)=\int_{-\infty}^{\infty}\widetilde f(\nu)e^{j2\pi\nu t}\,d\nu.

The convolution and correlation theorems are

.. math::
   :label: fop-formula-convolution-correlation

   \mathcal F\{f*g\}=\widetilde f\,\widetilde g,qquad
   \mathcal F\{f\star g\}=\widetilde f^{\,*}\widetilde g.

.. _fop-formula-matrices:

Matrices, determinants, and eigenvalues
----------------------------------------

For compatible matrices, multiplication is row by column and is generally
not commutative:

.. math::
   :label: fop-formula-matrix-product

   (AB)_{ij}=\sum_k A_{ik}B_{kj},\qquad AB\ne BA\ \text{in general}.

An eigenvalue :math:`\lambda` satisfies

.. math::
   :label: fop-formula-eigenvalue

   A\boldsymbol v=\lambda\boldsymbol v,qquad
   \det(A-\lambda I)=0.

For a lossless paraxial :math:`2\times2` ray matrix with
:math:`\det M=1`, bounded periodic rays require
:math:`|\operatorname{tr}M/2|<1`.

.. _fop-formula-vector-calculus:

Vector-calculus identities
--------------------------

The gradient, divergence, Laplacian, and curl identity used in the field
solutions are

.. math::
   :label: fop-formula-vector-identities

   \nabla f=\left(\partial_xf,\partial_yf,\partial_zf\right),\quad
   \nabla^2f=\nabla\!\cdot\nabla f,\quad
   \nabla\times(\nabla\times\boldsymbol A)
   =\nabla(\nabla\!\cdot\boldsymbol A)-\nabla^2\boldsymbol A.

.. _fop-formula-odes:

Common differential equations
-----------------------------

The constant-coefficient first- and second-order equations have solutions

.. math::
   :label: fop-formula-common-odes

   y'=ay\Rightarrow y=Ce^{ax},\qquad
   y''+\omega^2y=0\Rightarrow
   y=C_1\cos(\omega x)+C_2\sin(\omega x).

Boundary or initial conditions determine the constants.  Substitution into
the original differential equation is the quickest verification.

.. _fop-formula-probability:

Probability, expectation, and variance
---------------------------------------

For a discrete random variable :math:`N`,

.. math::
   :label: fop-formula-expectation-variance

   \mathbb E[N]=\sum_n nP(n),\qquad
   \operatorname{var}N=\mathbb E[N^2]-\mathbb E[N]^2.

For independent variables, variances add.  A Poisson random variable with
mean :math:`\mu` obeys

.. math::
   :label: fop-formula-poisson

   P(N=n)=e^{-\mu}\frac{\mu^n}{n!},\qquad
   \mathbb E[N]=\operatorname{var}N=\mu.

.. _fop-formula-power-decibels:

Power, intensity, and decibels
------------------------------

Power ratios use :math:`10\log_{10}`; field-amplitude ratios use
:math:`20\log_{10}` when power is proportional to amplitude squared:

.. math::
   :label: fop-formula-decibels

   G_{\mathrm{dB}}=10\log_{10}\!\left(\frac{P_2}{P_1}\right)
   =20\log_{10}\!\left|\frac{A_2}{A_1}\right|.

Independent losses add in decibels and multiply as linear power ratios.

.. _fop-formula-verification:

Verification methods
--------------------

Every quantitative solution should use at least one of these checks:

* substitute the result into the governing equation;
* verify dimensions and units term by term;
* test a known limit or symmetry;
* differentiate or integrate the proposed result;
* compare with an independent conservation law;
* reproduce the numerical value with unrounded intermediate quantities.

These are mathematical checks, not replacements for the derivation.
