.. _aberration-polynomial:

Deriving the Axially Symmetric Aberration Polynomial
====================================================

This page derives Eqs. 5.1 and 5.2 from *Modern Optical Engineering*.
They give the image-plane intersection :math:`(x',y')` of a ray as a
power series in field height, pupil radius, and pupil azimuth.  The
derivation is useful beyond reproducing the equations: it explains why a
centred optical system has only odd-order transverse aberrations and why
the trigonometric factors occur in their particular combinations.

The equation numbers and coefficient names below follow Warren J. Smith,
*Modern Optical Engineering: The Design of Optical Systems*, 4th ed.,
Sec. 5.2.  Section 15.3 of the same source supplies the connection to the
wave-aberration polynomial.

Geometry and convention
-----------------------

Take the optical axis to be :math:`z`.  Rotational symmetry lets us put
the object point in the meridional :math:`(y,z)` plane without loss of
generality:

.. math::

   \boldsymbol H=(0,h).

Smith measures pupil azimuth :math:`\theta` from the positive
:math:`y`-axis, not from the positive :math:`x`-axis.  The pupil point is
therefore

.. math::

   \boldsymbol\rho=(p,q)
   =\left(s\sin\theta,\;s\cos\theta\right),

where :math:`s` is its radial pupil coordinate.  The ray intersects the
chosen image plane at

.. math::

   \boldsymbol r'=(x',y').

The three scalar products that can be formed from the field and pupil
vectors are

.. math::
   :label: aberration-invariants

   u=\boldsymbol\rho\mathbin{\cdot}\boldsymbol\rho=s^2,\qquad
   v=\boldsymbol\rho\mathbin{\cdot}\boldsymbol H
     =sh\cos\theta,\qquad
   w=\boldsymbol H\mathbin{\cdot}\boldsymbol H=h^2.

Why this is the complete starting point
---------------------------------------

Let :math:`Q` be any rotation or reflection in the transverse plane.
A centred system is unchanged by that transformation, so its ray map
must obey

.. math::

   \boldsymbol r'(Q\boldsymbol\rho,Q\boldsymbol H)
   =Q\,\boldsymbol r'(\boldsymbol\rho,\boldsymbol H).

Reflection symmetry excludes rotated pseudovectors such as
:math:`(-q,p)`.  Consequently, an ordinary transverse vector can only
be assembled from :math:`\boldsymbol\rho` and :math:`\boldsymbol H`,
multiplied by scalar functions of the three invariants in
Eq. :eq:`aberration-invariants`:

.. math::
   :label: invariant-vector-map

   \boldsymbol r'
   =\boldsymbol\rho\,F(u,v,w)+\boldsymbol H\,G(u,v,w).

This compact expression contains the parity result.  Each of
:math:`u,v,w` has total degree two in pupil and field coordinates.
Multiplication by either vector adds one more degree, so an analytic
centred-system ray map contains orders

.. math::

   1,\ 3,\ 5,\ 7,\ldots

and no even orders.  Tilting or decentring a surface breaks the
symmetry used above and permits even-order terms.

First-order terms
-----------------

The constant parts of :math:`F` and :math:`G` give

.. math::
   :label: first-order-vector-map

   \boldsymbol r'_A=A_1\boldsymbol\rho+A_2\boldsymbol H.

Taking components immediately gives

.. math::

   x'_A=A_1s\sin\theta,\qquad
   y'_A=A_1s\cos\theta+A_2h.

Thus :math:`A_2` is the paraxial magnification, while :math:`A_1`
measures defocus of the selected image plane.  At the paraxial image
plane, :math:`A_1=0`.

Third order: the five Seidel terms
----------------------------------

Symmetry fixes the available monomials.  Fermat's principle supplies
one additional third-order constraint: in canonical pupil coordinates,
the transverse ray error is proportional to the pupil gradient of a
scalar optical characteristic.  The common proportionality factor
(:math:`-l/n` when the scalar is OPD) can be absorbed into the
coefficients.

A fourth-degree characteristic containing the five independent
centred-system terms is

.. math::
   :label: fourth-degree-characteristic

   \Phi_4={B_1\over4}u^2+B_2uv
          +{B_3+B_4\over2}uw+B_3v^2+B_5vw.

Using

.. math::

   \nabla_{\boldsymbol\rho}u=2\boldsymbol\rho,\qquad
   \nabla_{\boldsymbol\rho}v=\boldsymbol H,\qquad
   \nabla_{\boldsymbol\rho}w=0,

its pupil gradient is

.. math::
   :label: third-order-vector-map

   \begin{aligned}
   \boldsymbol r'_B
   &=\nabla_{\boldsymbol\rho}\Phi_4\\
   &=\boldsymbol\rho
      \left[B_1u+2B_2v+(B_3+B_4)w\right]\\
   &\quad+\boldsymbol H
      \left[B_2u+2B_3v+B_5w\right].
   \end{aligned}

For the :math:`x` component, :math:`H_x=0`.  Substitution of
Eq. :eq:`aberration-invariants` and
:math:`2\sin\theta\cos\theta=\sin2\theta` gives

.. math::
   :label: third-order-x

   x'_B
   =B_1s^3\sin\theta
    +B_2s^2h\sin2\theta
    +(B_3+B_4)sh^2\sin\theta.

For the :math:`y` component, both vectors contribute.  In particular,
the coma factor follows from

.. math::

   2qv+hu
   =s^2h(2\cos^2\theta+1)
   =s^2h(2+\cos2\theta).

The result is

.. math::
   :label: third-order-y

   y'_B
   =B_1s^3\cos\theta
    +B_2s^2h(2+\cos2\theta)
    +(3B_3+B_4)sh^2\cos\theta
    +B_5h^3.

The five coefficients are spherical aberration :math:`B_1`, coma
:math:`B_2`, astigmatism :math:`B_3`, Petzval curvature :math:`B_4`,
and distortion :math:`B_5`.

Fifth order: constructing every allowed angular term
-----------------------------------------------------

At fifth order, :math:`F` and :math:`G` in
Eq. :eq:`invariant-vector-map` must be quadratic in :math:`u,v,w`.
The following coefficient grouping is chosen so that the final
components have Smith's :math:`C_1,\ldots,C_{12}` notation:

.. math::
   :label: fifth-order-scalar-functions

   \begin{aligned}
   F_4={}&C_1u^2+2C_3uv+C_5uw+C_6v^2
          +2C_9vw+C_{11}w^2,\\
   G_4={}&(C_2-C_3)u^2+(C_4-C_5)uv+(C_7-C_8)uw\\
         &+2(C_8-C_9)v^2+(C_{10}-C_{11})vw+C_{12}w^2.
   \end{aligned}

There is no missing physics in the coefficient differences: they are
just a change of basis from the monomials in :math:`u,v,w` to the
traditional aberration coefficients.  Because :math:`H_x=0`,

.. math::

   x'_C=pF_4,\qquad y'_C=qF_4+hG_4.

For example, the :math:`C_3` terms combine as

.. math::

   \begin{aligned}
   x'_{C_3}
     &=2C_3p\,uv=C_3s^4h\sin2\theta,\\
   y'_{C_2,C_3}
     &=2C_3q\,uv+(C_2-C_3)hu^2\\
     &=(C_2+C_3\cos2\theta)s^4h.
   \end{aligned}

Applying the same substitution to every monomial gives

.. math::
   :label: fifth-order-x

   \begin{aligned}
   x'_C={}&C_1s^5\sin\theta+C_3s^4h\sin2\theta\\
          &+(C_5+C_6\cos^2\theta)s^3h^2\sin\theta\\
          &+C_9s^2h^3\sin2\theta+C_{11}sh^4\sin\theta,
   \end{aligned}

and

.. math::
   :label: fifth-order-y

   \begin{aligned}
   y'_C={}&C_1s^5\cos\theta
          +(C_2+C_3\cos2\theta)s^4h\\
          &+(C_4+C_6\cos^2\theta)s^3h^2\cos\theta\\
          &+(C_7+C_8\cos2\theta)s^2h^3\\
          &+C_{10}sh^4\cos\theta+C_{12}h^5.
   \end{aligned}

The coefficient groups are fifth-order spherical
:math:`C_1`, linear coma :math:`C_2,C_3`, oblique spherical
:math:`C_4,C_5,C_6`, elliptical coma :math:`C_7,C_8,C_9`,
fifth-order Petzval/astigmatism :math:`C_{10},C_{11}`, and
fifth-order distortion :math:`C_{12}`.

The displayed seventh-order term
---------------------------------

Equations 5.1 and 5.2 show only the leading seventh-order spherical
term.  In invariant notation it is simply

.. math::

   \boldsymbol r'_{D_1}=D_1u^3\boldsymbol\rho,

so

.. math::

   x'_{D_1}=D_1s^7\sin\theta,\qquad
   y'_{D_1}=D_1s^7\cos\theta.

The omitted seventh- and higher-order structures are represented by
the ellipses.

The assembled equations
-----------------------

Adding the first-, third-, fifth-, and displayed seventh-order blocks
produces the requested equations:

.. _moe-equation-5-1:

**Equation 5.1**

.. math::

   \begin{aligned}
   y'={}&A_1s\cos\theta+A_2h\\
       &+B_1s^3\cos\theta+B_2s^2h(2+\cos2\theta)
        +(3B_3+B_4)sh^2\cos\theta+B_5h^3\\
       &+C_1s^5\cos\theta+(C_2+C_3\cos2\theta)s^4h\\
       &+(C_4+C_6\cos^2\theta)s^3h^2\cos\theta
        +(C_7+C_8\cos2\theta)s^2h^3\\
       &+C_{10}sh^4\cos\theta+C_{12}h^5
        +D_1s^7\cos\theta+\cdots .
   \end{aligned}

.. _moe-equation-5-2:

**Equation 5.2**

.. math::

   \begin{aligned}
   x'={}&A_1s\sin\theta\\
       &+B_1s^3\sin\theta+B_2s^2h\sin2\theta
        +(B_3+B_4)sh^2\sin\theta\\
       &+C_1s^5\sin\theta+C_3s^4h\sin2\theta\\
       &+(C_5+C_6\cos^2\theta)s^3h^2\sin\theta
        +C_9s^2h^3\sin2\theta\\
       &+C_{11}sh^4\sin\theta+D_1s^7\sin\theta+\cdots .
   \end{aligned}

Sanity checks
-------------

The finished equations satisfy several useful checks:

* **Meridional ray:** at :math:`\theta=0`, every term in :math:`x'`
  vanishes, so a ray in the meridional plane stays in that plane.
* **Mirror ray:** replacing :math:`\theta` by :math:`-\theta` leaves
  :math:`y'` unchanged and reverses :math:`x'`, as reflection symmetry
  requires.
* **Axial object:** with :math:`h=0`, the intercept is radial:

  .. math::

     \boldsymbol r'
     =\left(A_1s+B_1s^3+C_1s^5+D_1s^7+\cdots\right)
       (\sin\theta,\cos\theta).

* **Order count:** every displayed monomial has total degree
  :math:`1`, :math:`3`, :math:`5`, or :math:`7` in :math:`s` and
  :math:`h`.

Using the polynomial with KrakenOS
----------------------------------

KrakenOS traces the exact surface geometry; it does not need this
truncated polynomial to propagate a ray.  The polynomial is useful as
an interpretable fit to a set of traced image-plane intercepts:

#. Choose signed field samples :math:`h` and pupil samples
   :math:`(s,\theta)`.
#. In this convention calculate
   :math:`\theta=\operatorname{atan2}(p,q)`.  The more common
   :math:`\operatorname{atan2}(q,p)` measures from :math:`x` and would
   interchange the sine and cosine factors.
#. Trace each ray to a common reference image plane and record
   :math:`(x',y')`.
#. Build the basis columns displayed in :ref:`Eq. 5.1
   <moe-equation-5-1>` and :ref:`Eq. 5.2 <moe-equation-5-2>`, then
   solve for the coefficients by linear least squares.
#. Inspect the residual.  A structured residual indicates omitted
   seventh- or higher-order aberration, pupil distortion, or a broken
   centred-system assumption.

If :math:`h` and :math:`s` are normalized to unit field and unit pupil,
the fitted coefficients are the full-field/full-pupil transverse
contributions in the chosen image-length unit.  Changing either
normalization rescales the coefficients, so the normalization must
always accompany reported values.
