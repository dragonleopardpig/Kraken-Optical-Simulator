Chapter 1: Ray Optics
=====================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 1.  Prompts are paraphrased.  Distances and radii use the book's sign
convention; :math:`P(d)` and :math:`L(f)` denote free-space and thin-lens ray
matrices.

In-text exercises
-----------------

.. rubric:: Exercise 1.1-1 — Snell's law from stationary optical path

Introduce a multiplier :math:`\lambda` for
:math:`d_1\tan\theta _1+d_2\tan\theta _2=d`.  Differentiating
:math:`n_1d_1\sec\theta _1+n_2d_2\sec\theta _2` gives
:math:`n_i\sec\theta_i\tan\theta_i+\lambda\sec^2\theta_i=0`.
Thus :math:`\lambda=-n_i\sin\theta_i` on both sides and

.. math:: \boxed{n_1\sin\theta _1=n_2\sin\theta _2}.

.. rubric:: Exercise 1.2-1 — Spherical-mirror imaging

At height :math:`y`, the paraxial surface normal has angle :math:`y/R`.
Reflection gives :math:`(y-y_1)/z_1+(y-y_2)/z_2=2y/R`.
For the coefficient of the arbitrary intercept :math:`y` to vanish,
:math:`1/z_1+1/z_2=2/R=1/f`.  The remaining term gives
:math:`y_2=-y_1z_2/z_1`; hence every ray from one object point reaches the
same, inverted image point.

.. rubric:: Exercise 1.2-2 — One spherical refracting boundary

Paraxial Snell refraction at height :math:`y` gives
:math:`n_1(y-y_1)/z_1+n_2(y_2-y)/z_2=(n_2-n_1)y/R`.
Equating the coefficient and constant terms yields

.. math::

   \frac{n_1}{z_1}+\frac{n_2}{z_2}=\frac{n_2-n_1}{R},
   \qquad y_2=-\frac{n_1z_2}{n_2z_1}y_1.

.. rubric:: Exercise 1.2-3 — Aberration-free refracting surface

Let a surface point be :math:`(y,z)`, with the two axial conjugates at
:math:`(0,-z_1)` and :math:`(0,z_2)`.  Fermat's principle requires

.. math::

   \boxed{n_1\sqrt{y^2+(z+z_1)^2}
   +n_2\sqrt{y^2+(z_2-z)^2}=n_1z_1+n_2z_2}.

This Cartesian oval, not a sphere in general, makes the optical path identical
for every ray and therefore images without spherical aberration.

.. rubric:: Exercise 1.2-4 — Thin-lens formulas

Apply the preceding boundary equation first at :math:`R_1`, then at
:math:`R_2`, and let the center thickness tend to zero.  The intermediate
image distance cancels, leaving

.. math::

   \frac1{z_1}+\frac1{z_2}=\frac1f,
   \qquad
   \boxed{\frac1f=(n-1)\left(\frac1{R_1}-\frac1{R_2}\right)},
   \qquad m=-\frac{z_2}{z_1}.

.. rubric:: Exercise 1.2-5 — Step-index fibre acceptance

At the core-cladding boundary, the limiting ray obeys
:math:`\sin\theta_c=n_2/n_1`.  Geometry gives
:math:`\sin\theta_z=\cos\theta_c`; applying Snell's law at the input face then
gives

.. math:: \boxed{\mathrm{NA}=\sin\theta_a=\sqrt{n_1^2-n_2^2}}.

.. rubric:: Exercise 1.2-6 — Light trapped in a high-index block

Only rays within the internal escape cone
:math:`\theta_c=\sin^{-1}(1/n)` leave a face; the rest undergo total internal
reflection.  For GaAs, :math:`n=3.6`, so
:math:`\boxed{\theta_c=16.13^\circ}` (a full cone of :math:`32.26^\circ`).

.. rubric:: Exercise 1.3-1 — A SELFOC slab as a lens

For :math:`n(y)\simeq n_0(1-a^2y^2/2)`, the paraxial ray equation is
:math:`y''+a^2y=0`.  Propagating its sine-cosine solution through length
:math:`d` and extending the exit tangent to the axis gives

.. math::

   \boxed{f=\frac{1}{n_0a\sin(ad)}},\qquad
   AH=\frac{\tan(ad/2)}{n_0a}.

At :math:`d=\pi/(2a)` all rays cross the axis at the exit quarter-pitch; at
:math:`d=\pi/a` they form an inverted unit-magnification half-pitch image.

.. rubric:: Exercise 1.3-2 — Graded-index fibre acceptance

The conserved paraxial ray energy is
:math:`(y')^2+a^2y^2=\theta_0^2`.  Confinement to :math:`|y|\leq a_f`
requires :math:`\theta_0\leq aa_f`; input-face Snell refraction therefore
gives :math:`\boxed{\mathrm{NA}\simeq n_0aa_f}`.  Since
:math:`n(a_f)\simeq n_0(1-a^2a_f^2/2)`, the matched step-index result
:math:`\sqrt{n_0^2-n(a_f)^2}` has the same first-order value.

.. rubric:: Exercise 1.4-1 — Zero elements of an ABCD matrix

From :math:`y_2=Ay_1+B\theta_1` and
:math:`\theta_2=Cy_1+D\theta_1`: :math:`A=0` maps equal input angles to one
output height; :math:`B=0` images an input plane; :math:`C=0` is afocal; and
:math:`D=0` maps equal input heights to one output angle.

.. rubric:: Exercise 1.4-2 — Parallel plates

Using reduced angle :math:`n\theta`, each plate is
:math:`\begin{bmatrix}1&d_i/n_i\\0&1\end{bmatrix}`.  Such shear matrices add,
so

.. math::

   \boxed{M=\begin{bmatrix}1&\sum_i d_i/n_i\\0&1\end{bmatrix}}.

.. rubric:: Exercise 1.4-3 — Gap followed by a lens

Direct multiplication gives

.. math::

   \boxed{L(f)P(d)=
   \begin{bmatrix}1&0\\-1/f&1\end{bmatrix}
   \begin{bmatrix}1&d\\0&1\end{bmatrix}
   =\begin{bmatrix}1&d\\-1/f&1-d/f\end{bmatrix}}.

.. rubric:: Exercise 1.4-4 — Single-lens imaging

For :math:`M=P(d_2)L(f)P(d_1)`, the element
:math:`B=d_1+d_2-d_1d_2/f`.  The imaging law makes :math:`B=0`, so
:math:`y_2=Ay_1=-(d_2/d_1)y_1`, independently of input angle.  Setting
:math:`d_2=f` instead makes :math:`A=0`, so all rays of one input angle meet
at :math:`y_2=f\theta_1`.

.. rubric:: Exercise 1.4-5 — Thick symmetric lens

Multiplying the two spherical refractions and the internal translation gives
the equivalent power

.. math::

   \Phi=(n-1)\left(\frac1{R_1}-\frac1{R_2}
   +\frac{(n-1)d}{nR_1R_2}\right),\qquad f=\Phi^{-1}.

Locating the principal planes from the resulting :math:`A,D` elements changes
the vertex distances to :math:`z_1=d_1+h_1` and :math:`z_2=d_2+h_2`.
The condition :math:`B=0` then reduces to
:math:`1/z_1+1/z_2=1/f`, which proves the stated thick-lens form.

.. rubric:: Exercise 1.4-6 — Alternating periodic lenses

Multiply one complete cell and apply the unimodular stability test
:math:`|\operatorname{tr}M/2|<1`.  The trace simplifies to

.. math::

   \boxed{0<\left(1-\frac d{2f_1}\right)
   \left(1-\frac d{2f_2}\right)<1}.

.. rubric:: Exercise 1.4-7 — Two-mirror resonator

The round-trip matrix is the product of two translations and two mirror
powers.  With :math:`g_i=1+d/R_i` in the book's radius convention,
:math:`(\operatorname{tr}M+2)/4=g_1g_2`.  Hence bounded rays require
:math:`\boxed{0<g_1g_2<1}` (equality is marginal).

End-of-chapter problems
-----------------------

.. rubric:: Problem 1.1-2 — Stationary time need not be a minimum

The ellipse has constant :math:`AP+PB`; its first variation at the tangent
point is zero.  An internally tangent surface lies inside the ellipse nearby,
so its adjacent broken paths are shorter and :math:`P` is a local maximum.
A surface crossing the ellipse lies on opposite sides on either side of
:math:`P`; the path difference changes sign, making the stationary path an
inflection.  Fermat's principle therefore means *stationary*, not always
minimum, time.

.. rubric:: Problem 1.2-7 — Plane-parallel plate or stack

Snell gives :math:`\sin\theta=n_1\sin\theta_1` at entry and the reverse at
exit, so the emergent angle is :math:`\theta`.  Geometry gives the lateral
shift

.. math:: \boxed{s=d\,\frac{\sin(\theta-\theta_1)}{\cos\theta_1}}.

For a stack, tangential wavevector conservation gives
:math:`n_m\sin\theta_m=\sin\theta` in every layer and the last boundary again
returns angle :math:`\theta`; the individual lateral shifts add.

.. rubric:: Problem 1.2-8 — Biconvex lens in air and water

For :math:`R_1=0.20\ \mathrm m`, :math:`R_2=-0.30\ \mathrm m`,

.. math::

   \frac1f=\left(\frac{n_l}{n_m}-1\right)
   \left(\frac1{R_1}-\frac1{R_2}\right).

Thus :math:`f_{air}=1/[0.5(5+3.333)]=\boxed{0.240\ \mathrm m}`.  In water
(:math:`n_m=4/3`), :math:`n_l/n_m=1.125`, giving
:math:`\boxed{f_{water}=0.960\ \mathrm m}`.

.. rubric:: Problem 1.2-9 — Cladless fibre

:math:`\mathrm{NA}=\sqrt{1.46^2-1^2}=1.0647`.  Since an external numerical
aperture cannot exceed one, every ray in the incident air hemisphere can in
principle be accepted: :math:`\boxed{\theta_a=90^\circ}`.  The value above one
signals saturation, not a sine larger than one.

.. rubric:: Problem 1.2-10 — Spherical coupling lens

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

.. rubric:: Problem 1.2-11 — Extraction from an index-3.7 block

The escape-cone fraction after perfect recycling by the other faces is
:math:`1-\cos\theta_c`, where :math:`\theta_c=\sin^{-1}(1/3.7)=15.68^\circ`.
Therefore :math:`\boxed{3.72\%}` of isotropic directions can escape the front.
A plane-parallel :math:`n=1.4` layer does not increase the final air escape
cone: successive Snell laws still require
:math:`3.7\sin\theta_{core}\leq1`.  Texture or a nonparallel extractor would
be required.

.. rubric:: Problem 1.3-3 — Axially graded plate

Apply Snell's law to infinitesimal parallel layers:
:math:`n(z)\sin\theta(z)=\sin\theta_0`.  The exit medium is again air, so the
emergent angle is :math:`\theta_0`.  Since :math:`dy/dz=\tan\theta`,

.. math::

   \boxed{\left(\frac{dy}{dz}\right)^2
   =\left[\frac{n^2(z)}{\sin^2\theta_0}-1\right]^{-1}}.

.. rubric:: Problem 1.3-4 — Cylindrical GRIN ray equations

Writing the transverse paraxial equation
:math:`d(n\mathbf r_\perp')/dz=\nabla_\perp n` in polar components gives

.. math::

   \frac d{dz}(np')-np\phi'^2=\frac{dn}{dp},\qquad
   \frac d{dz}(np^2\phi')=0.

The second equation is conserved optical angular momentum.  For slowly
varying :math:`n`, these reduce to
:math:`p''-p\phi'^2=n^{-1}dn/dp` and
:math:`\phi''+2p'\phi'/p=0`.

.. rubric:: Problem 1.4-8 — Convex/concave lens pair

For convex lens, gap, then concave lens,

.. math::

   M=L(-f)P(f)L(f)=
   \boxed{\begin{bmatrix}0&f\\-1/f&2\end{bmatrix}}.

Because :math:`A=0`, parallel rays of a given angle meet at the same output
height :math:`f\theta`; because :math:`B\ne0`, the chosen input and output
planes are not conjugate object/image planes.

.. rubric:: Problem 1.4-9 — GRIN-plate matrix

Solving :math:`y''+a^2y=0` over distance :math:`d` gives, for the reduced-angle
state :math:`(y,n_0\theta)`,

.. math::

   \boxed{M(d)=\begin{bmatrix}
   \cos ad&\sin(ad)/(n_0a)\\-n_0a\sin(ad)&\cos ad
   \end{bmatrix}}.

.. rubric:: Problem 1.4-10 — Periodic GRIN stability

The determinant is one and half the trace is :math:`b=\cos(ad)`, so
:math:`|b|\leq1` for every real :math:`d`.  The trajectory is stable for all
cell choices (marginal only when :math:`ad` is an integer multiple of
:math:`\pi`); physical stability therefore does not depend on how the
continuous plate is partitioned.

.. rubric:: Problem 1.4-11 — Plane-mirror recurrence

One round trip is simply :math:`M=P(2d)=\begin{bmatrix}1&2d\\0&1\end{bmatrix}`;
thus :math:`b=\operatorname{tr}M/2=1` and the repeated eigenvalue is one.
Since :math:`M^m=\begin{bmatrix}1&2md\\0&1\end{bmatrix}`,
:math:`\boxed{y_m=y_0+2md\theta_0=\alpha+m\beta}`.  Except for
:math:`\theta_0=0`, the planar resonator is marginal rather than bounded.

.. rubric:: Problem 1.4-12 — Four-dimensional ray matrices

For state :math:`(x,y,\theta_x,\theta_y)^T`, free propagation and a cylindrical
lens focusing only in :math:`y` are

.. math::

   \boxed{P_4(d)=\begin{bmatrix}1&0&d&0\\0&1&0&d\\0&0&1&0\\0&0&0&1\end{bmatrix}},
   \qquad
   \boxed{L_y(f)=\begin{bmatrix}1&0&0&0\\0&1&0&0\\0&0&1&0\\0&-1/f&0&1\end{bmatrix}}.
