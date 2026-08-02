Chapter 3: Beam Optics
======================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 3.  Beam radius :math:`W` is the field's :math:`1/e` radius.

In-text exercises
-----------------

.. rubric:: Exercise 3.1-1 — He--Ne Gaussian beam

For :math:`W_0=0.05\ \mathrm{mm}` and :math:`\lambda=633\ \mathrm{nm}`,
:math:`\theta_0=\lambda/(\pi W_0)=4.03\ \mathrm{mrad}` and
:math:`2z_0=2\pi W_0^2/\lambda=24.8\ \mathrm{mm}`.  At the Moon the diameter
is approximately :math:`2\theta_0z=\boxed{2.82\times10^3\ \mathrm{km}}`.
:math:`R(0)=\infty`, :math:`R(z_0)=2z_0`, and :math:`R(2z_0)=2.5z_0`.
For :math:`P=1\ \mathrm{mW}`, :math:`I(0,0)=2P/(\pi W_0^2)=25.5`
:math:`\mathrm{W,cm^{-2}}` and :math:`I(0,z_0)=12.7`
:math:`\mathrm{W,cm^{-2}}`; a 100-W isotropic source at :math:`z_0` gives
only :math:`5.14\ \mathrm{W,cm^{-2}}`.

.. rubric:: Exercise 3.1-2 — Paraxial validity

For a Gaussian beam, transverse variation is :math:`\partial_xA\sim A/W`
and longitudinal variation is :math:`\partial_zA\sim A/z_0`.  Their ratio in
the neglected Helmholtz term is :math:`1/(kz_0)\sim\theta_0^2/2`; therefore
:math:`\theta_0\ll1` implies :math:`|\partial_z^2A|\ll|2k\partial_zA|`.

.. rubric:: Exercise 3.1-3 — Recovering a beam from :math:`W,R`

Use :math:`q^{-1}=R^{-1}-j\lambda/(\pi W^2)` and write
:math:`q=z+jz_0`.  Taking real and imaginary parts gives
:math:`z=R/[1+(\lambda R/\pi W^2)^2]` and
:math:`W_0=W/[1+(\pi W^2/\lambda R)^2]^{1/2}` (with the propagation-side sign
set by :math:`R`).

.. rubric:: Exercise 3.1-4 — Propagating known width and curvature

The given values give
:math:`q_1=[1/R_1-j\lambda/(\pi W_1^2)]^{-1}=0.908000+j0.289025`
m.  Since :math:`q_2=q_1+0.1`, conversion back yields
:math:`\boxed{W_2=1.10046\ \mathrm{mm}}` and
:math:`\boxed{R_2=1.09087\ \mathrm m}`.

.. rubric:: Exercise 3.1-5 — Two measured curvatures

Write :math:`R_i=z_i+z_0^2/z_i` with :math:`z_2=z_1+d`.
Eliminating :math:`z_0` gives the printed
:math:`z_1=-d(R_2-d)/(R_2-R_1-2d)`; back-substitution gives the stated
:math:`z_0^2`.  The physical root requires :math:`z_0^2>0`.

.. rubric:: Exercise 3.2-1 — Periodic beam relay

Apply :math:`q'=(Aq+B)/(Cq+D)` to one lens-spacing cell and impose the same
waist after the cell.  The resulting real :math:`z_0` contains
:math:`\sqrt{d(4f-d)}`; hence a physical self-reproducing beam exists only for
:math:`\boxed{0\leq d\leq4f}`.

.. rubric:: Exercise 3.2-2 — Lens and collimation

With incident :math:`q=z+jz_0`, a lens gives
:math:`q'=q/(1-q/f)`.  Separating its real part (new waist position) and
imaginary part reproduces Eq. (3.2-18).  Setting the outgoing waist far away
requires the incident wavefront curvature at the lens to satisfy
:math:`R(z)=f`; real solutions exist only when :math:`f\geq2z_0`.

.. rubric:: Exercise 3.2-3 — Two-lens beam expander

Apply the ABCD law to :math:`M=L(f_2)P(s)L(f_1)`.  In the collimated limit
:math:`s=f_1+f_2`, the waist and divergence transform as
:math:`\boxed{W_{0,out}/W_{0,in}=f_2/f_1}` and
:math:`\theta_{out}/\theta_{in}=f_1/f_2`; the product
:math:`W_0\theta=\lambda/\pi` is unchanged.

.. rubric:: Exercise 3.2-4 — Gaussian-reflectance mirror

Multiplying the incident field by
:math:`r(\rho)=e^{-\rho^2/W_m^2}` adds reciprocal squared widths, while the
spherical phase changes the curvature as reflection does:
:math:`\boxed{W_2^{-2}=W_1^{-2}+W_m^{-2}}` and
:math:`\boxed{R_2^{-1}=2R^{-1}-R_1^{-1}}` in the reflected propagation
coordinate.

.. rubric:: Exercise 3.2-5 — Plane-parallel plate

The complete air--plate--air ABCD matrix is
:math:`\begin{bmatrix}1&d/n\\0&1\end{bmatrix}` for reduced angle.  Thus
:math:`\boxed{q_{out}=q_{in}+d/n}`: the beam emerging in air has the original
waist and divergence but is advanced relative to free propagation by
:math:`d(1-1/n)`.

.. rubric:: Exercise 3.3-1 — Incoherent donut beam

Adding the (1,0) and (0,1) intensities gives
:math:`I\propto\rho^2e^{-2\rho^2/W_0^2}`.  Its peak is at
:math:`\boxed{\rho=W_0/\sqrt2=0.7071\ \mathrm{mm}}`; solving
:math:`I/I_{max}=e^{-2}` gives the two radii
:math:`\boxed{0.1620\ \mathrm{mm}}` and
:math:`\boxed{1.5009\ \mathrm{mm}}` for :math:`W_0=1` mm.

End-of-chapter problems
-----------------------

.. rubric:: Problem 3.1-6 — Nd:YAG beam parameters

The stated full divergence is :math:`2\theta_0=1` mrad, so
:math:`W_0=\lambda/(\pi\theta_0)=\boxed{0.675\ \mathrm{mm}}`,
:math:`2z_0=2\pi W_0^2/\lambda=\boxed{2.70\ \mathrm m}`, and
:math:`I_{max}=2P/(\pi W_0^2)=\boxed{1.40\times10^6\ \mathrm{W,m^{-2}}}`.
At :math:`z=1` m multiply by :math:`[1+(z/z_0)^2]^{-1}` to obtain
:math:`\boxed{9.05\times10^5\ \mathrm{W,m^{-2}}}`.

.. rubric:: Problem 3.1-7 — Beam from two widths

Solve :math:`W_i^2=W_0^2[1+(z_i/z_0)^2]`,
:math:`z_2=z_1+0.1` m, and :math:`z_0=\pi W_0^2/\lambda`.  The solution is
:math:`\boxed{W_0=0.2000\ \mathrm{mm}}`; the waist lies
:math:`\boxed{100.0\ \mathrm{mm}}` before the first measurement plane.

.. rubric:: Problem 3.1-8 — Elliptic Gaussian beam

Each axis propagates independently:
:math:`z_{0i}=\pi W_{0i}^2/\lambda`,
:math:`\theta_i=\lambda/(\pi W_{0i})`, and
:math:`R_i=z[1+(z_{0i}/z)^2]`.  If :math:`W_{0x}=2W_{0y}`, the waist is twice
as wide in :math:`x`, but the far field is twice as wide in :math:`y`; the
ellipse rotates its major-axis orientation by :math:`90^\circ`.

.. rubric:: Problem 3.2-6 — Smallest focusing lens

:math:`z_0=\pi W_0^2/\lambda=1.609` m.  Requiring
:math:`W'_0/W_0=0.1` in
:math:`z'_0/z_0=f^2/[(z-f)^2+z_0^2]` gives the existence condition
:math:`f\geq z_0/10`.  Therefore the shortest lens is
:math:`\boxed{f=160.9\ \mathrm{mm}}`, placed :math:`z=f` from the original
waist; it produces the requested :math:`100\ \mathrm{\mu m}` diameter.

.. rubric:: Problem 3.2-7 — Focused-waist plot

Plot
:math:`W'_0=W_0f/[ (z-f)^2+z_0^2]^{1/2}` with
:math:`W_0=\sqrt{\lambda z_0/\pi}`.  Direct expansion gives the distant-beam
and geometric-focus limits of Eqs. (3.2-10), (3.2-12), while :math:`z\ll z_0`
gives :math:`W'_0/W_0=f/\sqrt{f^2+z_0^2}`, Eq. (3.2-13).

.. rubric:: Problem 3.2-8 — Refraction of a waist

The transverse waist is continuous at the plane boundary and the wavelength
falls to :math:`\lambda_0/n`; consequently
:math:`\boxed{\theta_t=\theta_i/n=0.667\ \mathrm{mrad}}` and the Rayleigh
range grows by :math:`n`.  The sketch is the same waist followed by a more
slowly expanding cone.

.. rubric:: Problem 3.2-9 — Gaussian beam in a GRIN slab

With :math:`q_0=jz_0` and the stated matrix,
:math:`q(d)=[jq_0\cos(ad)+\sin(ad)/a]/[\cos(ad)-ja z_0\sin(ad)]`.
Use :math:`W^2=-\lambda/[\pi\operatorname{Im}(1/q)]`; simplification gives

.. math::

   \boxed{W^2(d)=W_0^2\left[\cos^2(ad)+
   \frac{\sin^2(ad)}{a^2z_0^2}\right]}.

The width breathes periodically; it is constant only for :math:`az_0=1`.

.. rubric:: Problem 3.3-2 — Enclosed Hermite--Gaussian power

At radius :math:`sW`, the fractions are
:math:`F_{00}=1-e^{-2s^2}`,
:math:`F_{10}=F_{01}=1-e^{-2s^2}(1+2s^2)`, and
:math:`F_{11}=1-e^{-2s^2}(1+2s^2+2s^4)`.  Thus at :math:`s=1` they are
:math:`\boxed{0.8647,0.5940,0.5940,0.3233}`.  At :math:`s=\sqrt2`,
:math:`F_{00}=\boxed{0.9817}` and :math:`F_{11}=\boxed{0.7619}`.

.. rubric:: Problem 3.3-3 — Coherent (1,0)+(0,1)

Equal complex coefficients give field
:math:`U\propto(x+y)e^{-\rho^2/W^2}`.  Its intensity has a dark diagonal
:math:`y=-x` and two lobes along :math:`y=x`; rotating coordinates by
:math:`45^\circ` identifies it as a first-order HG mode.

.. rubric:: Problem 3.3-4 — Axial phase modes

Between :math:`-z_0` and :math:`z_0`, the phase is
:math:`2kz_0-(l+m+1)\pi/2`.  Setting it to :math:`N\pi` gives

.. math:: \boxed{\nu_{Nlm}=\frac{c}{4z_0}
   \left[N+\frac{l+m+1}{2}\right]}.

For :math:`z_0=0.30` m, adjacent :math:`N` values are 250 MHz apart; retain
the integers whose values fall in :math:`10^{14}\pm2` GHz.
