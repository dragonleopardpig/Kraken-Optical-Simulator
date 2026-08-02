Chapter II: Matrix Methods in Paraxial Optics
=============================================

Source: Gerrard and Burch, *Introduction to Matrix Methods in Optics* (1975),
Chapter II.  Distances below follow the book's reference-plane convention.

Illustrative problems
---------------------

Problem 2.1 — Refraction by the end of a plastic rod
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For the air-to-plastic surface,

.. math::

   P=\frac{n_2-n_1}{r}
    =\frac{1.56-1}{0.028}=20\ \mathrm{m^{-1}},
   \qquad R(P)=\begin{bmatrix}1&0\\-20&1\end{bmatrix}.

If :math:`x` is the image distance inside the plastic, form

.. math::

   M=T(x,1.56)R(20)T(0.15,1),
   \qquad T(t,n)=\begin{bmatrix}1&t/n\\0&1\end{bmatrix}.

Imaging requires :math:`B=0`, which gives
:math:`\boxed{x=0.117\ \mathrm m=11.7\ \mathrm{cm}}`.  At that distance
:math:`A=-0.5`, so a 2-cm object forms a
:math:`\boxed{1.0\ \mathrm{cm}}` inverted image.  The determinant remains
unity.

Problem 2.2 — Imaging through a double-convex glass rod
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Each surface has power :math:`P=(1.6-1)/0.024=25\ \mathrm{m^{-1}}`, and the
reduced thickness is :math:`0.028/1.6=0.0175\ \mathrm m`.  The rod matrix is

.. math::

   M_s=R(25)T(0.028,1.6)R(25)
   =\begin{bmatrix}
      0.5625&0.0175\\-39.0625&0.5625
     \end{bmatrix}.

Set :math:`B=0` in :math:`T(x,1)M_sT(0.08,1)`.  This gives

.. math::

   \boxed{x=2.439\ \mathrm{cm}},\qquad
   m=A=-0.39024.

The 2-cm object therefore produces a
:math:`\boxed{0.780\ \mathrm{cm}}` inverted image beyond the second surface.

Problem 2.3 — Back focal distance of a spherical bead
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a 2-cm-diameter bead of index 1.4, both refracting surfaces have power
:math:`40\ \mathrm{m^{-1}}`.  Thus

.. math::

   M_s=R(40)T(0.02,1.4)R(40)
   =\begin{bmatrix}
      3/7&1/70\\-400/7&3/7
     \end{bmatrix}.

A parallel input has :math:`V_1=0`.  After an air gap :math:`x`, its height is
:math:`(A+xC)y_1`; setting this to zero yields

.. math::

   \boxed{x=-A/C=7.5\ \mathrm{mm}}

beyond the bead.  Direct multiplication verifies :math:`AD-BC=1`.

Problem 2.4 — Lantern-slide projection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The image is 20 times the 2-inch slide height.  With object and image
distances :math:`u` and :math:`v`,

.. math::

   \frac vu=20,\qquad u+v=10.5\ \mathrm{ft}.

Hence :math:`u=0.5\ \mathrm{ft}=6\ \mathrm{in}` and
:math:`v=10\ \mathrm{ft}`.  The imaging condition gives

.. math::

   \boxed{f=\frac{uv}{u+v}=5.714\ \mathrm{in}}.

The lens is therefore 6 inches from the slide; the conjugate distances add
back to 10.5 feet.

Problem 2.5 — Positive and negative lens pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Working in metres, use :math:`P_1=12.5\ \mathrm{D}`,
:math:`P_2=-8.333\ \mathrm{D}`, and

.. math::

   M=T(x)R(P_2)T(0.06)R(P_1)T(0.24).

The top-right element is :math:`B=0.12-x`; hence
:math:`\boxed{x=12\ \mathrm{cm}}` to the right of the negative lens.  At this
plane :math:`A=-1`, so the final image is inverted and has the same 3-cm
height as the object.

Problem 2.6 — Longitudinal magnification
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For a thin lens of power :math:`P`, the image condition from
:math:`T(-V)R(P)T(U)` is

.. math::

   U-V+PUV=0,
   \qquad V=\frac{U}{1-PU}.

Differentiation gives

.. math::

   \boxed{\frac{dV}{dU}=\frac{1}{(1-PU)^2}}
   =\left(\frac VU\right)^2=m_T^2.

Thus longitudinal magnification is the square of lateral magnification.  Its
nonnegative sign is consistent with nearby conjugate planes moving in the
same longitudinal sense under the book's signed-distance convention.

Problem 2.7 — Minimum object-to-image distance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For real conjugates of a positive thin lens,
:math:`1/u+1/v=1/f`.  Therefore

.. math::

   \frac{u+v}{f}=\frac{(u+v)^2}{uv}
   =\frac uv+2+\frac vu\geq4.

Consequently

.. math::

   \boxed{u+v\geq4f},

with equality only at :math:`u=v=2f`.  This is also the stationary point of
the separation found by differentiating with respect to either conjugate.

Problem 2.8 — Cardinal points of a hemispherical lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Take the entrance plane surface as the first reference plane, translate a
reduced distance :math:`r/n`, and refract at the spherical exit.  Reducing the
matrix to principal-plane form gives

.. math::

   \boxed{f=\frac{r}{n-1}},\qquad
   \boxed{H_1\text{ lies }r/n\text{ inside the plane face}},
   \qquad
   \boxed{H_2\text{ is at the curved-surface vertex}}.

The result tends to infinite focal length as :math:`n\to1`, and the second
principal point remains at the vertex because there is no propagation after
the only powered surface.

Problem 2.9 — Cardinal points of a separated positive-negative pair
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The two-lens matrix is

.. math::

   M=R(-10)T(0.05)R(10)
    =\begin{bmatrix}0.5&0.05\\-5&1.5\end{bmatrix}.

Therefore the equivalent focal length is
:math:`\boxed{f=-1/C=20\ \mathrm{cm}}`.  Relative to the positive-lens plane,
the first focus is :math:`D/C=-30\ \mathrm{cm}` and the first principal plane
is :math:`(D-1)/C=-10\ \mathrm{cm}`.  Relative to the negative-lens plane, the
second focus is :math:`-A/C=+10\ \mathrm{cm}` and the second principal plane is
:math:`(1-A)/C=-10\ \mathrm{cm}`.  Each focus is 20 cm from its associated
principal plane.

Problem 2.10 — Two-lens eyepiece and chromatic error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Multiplication gives

.. math::

   R(P_2)T(t)R(P_1)=
   \begin{bmatrix}
      1-P_1t&t\\
      -(P_1+P_2-P_1P_2t)&1-P_2t
   \end{bmatrix},

so

.. math::

   \boxed{f=\frac{1}{P_1+P_2-P_1P_2t}}.

For lenses of the same glass, write :math:`P_i=(n-1)G_i` and set
:math:`d(1/f)/dn=0`.  The transverse-achromat condition is

.. math::

   \boxed{t=\frac12\left(\frac1{P_1}+\frac1{P_2}\right)}.

This removes chromatic change of magnification, but :math:`D=1-P_2t` still
varies with index, so the eyepiece retains longitudinal color.

Problem 2.11 — Cardinal points across unequal exterior indices
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In centimetres and inverse centimetres, the thick-lens matrix is

.. math::

   M=\begin{bmatrix}0.8&2\\-0.06&1.1\end{bmatrix},
   \qquad \det M=1,

with :math:`n_1=1` and :math:`n_2=1.4`.  The cardinal data are

.. list-table::
   :header-rows: 1
   :widths: 30 32 38

   * - Quantity
     - Input side, from first surface
     - Output side, from second surface
   * - Focus
     - :math:`F_1=D/C=-18.3\ \mathrm{cm}`
     - :math:`F_2=-n_2A/C=+18.7\ \mathrm{cm}`
   * - Principal point
     - :math:`H_1=(D-1)/C=-1.67\ \mathrm{cm}`
     - :math:`H_2=n_2(1-A)/C=-4.67\ \mathrm{cm}`
   * - Focal length
     - :math:`f_1=-n_1/C=16.7\ \mathrm{cm}`
     - :math:`f_2=-n_2/C=23.3\ \mathrm{cm}`

The two nodal points coincide at the common center of curvature: 5 cm to the
right of the first surface, equivalently 2 cm to the right of the second.

Problem 2.12 — Internally reflected glass sphere
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Construct the chain from refraction at the left surface, translation across
the sphere, reflection at the right surface, return translation, and final
refraction.  Moving both reference planes from the left surface to the sphere
center simplifies the result to

.. math::

   \boxed{M_c=
   \begin{bmatrix}
      -1&0\\[2pt]
      -\dfrac{2(2-n)}{nr}&-1
   \end{bmatrix}}.

The zero :math:`B` element shows that the center images onto itself with
lateral magnification :math:`-1`.  For :math:`1<n<2` the equivalent focal
length is positive.  At :math:`n=2`, :math:`C=0` and
:math:`M_c=-I`: the bead is afocal and retroreflects each incident ray (within
the paraxial and aberration limits).
