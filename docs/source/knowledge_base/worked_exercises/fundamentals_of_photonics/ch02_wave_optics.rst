Chapter 2: Wave Optics
======================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 2.  The time convention is the one used by the text.

In-text exercises
-----------------

.. rubric:: Exercise 2.2-1 — Fresnel-approximation region

At the usual boundary estimate :math:`a^4=4z^3\lambda`, with
:math:`z=1\ \mathrm m` and :math:`\lambda=633\ \mathrm{nm}`,
:math:`\boxed{a=39.9\ \mathrm{mm}}`,
:math:`\boxed{\theta_m=a/z=0.0399\ \mathrm{rad}=2.29^\circ}`, and
:math:`\boxed{N_F=a^2/(\lambda z)=2.51\times10^3}`.  Strict Fresnel validity
requires a radius appreciably smaller than this equality limit because
:math:`N_F\theta_m^2/4\ll1`.

.. rubric:: Exercise 2.2-2 — Paraboloidal and Gaussian waves

Substitution of :math:`A=(A_0/z)e^{-jk\rho^2/(2z)}` into
:math:`\nabla_T^2A-2jk\,\partial_zA=0` makes the constant and
:math:`\rho^2` terms cancel.  Replacing :math:`z` by
:math:`q=z+jz_0` preserves the cancellation because :math:`dq/dz=1`.
At :math:`z=0`, :math:`|A|^2=|A_1|^2z_0^{-2}
e^{-k\rho^2/z_0}`, a circular Gaussian.

.. rubric:: Exercise 2.4-1 — Thin prism

With :math:`d(x)=d_0-ax`, the phase plate law
:math:`t=e^{-jk_0[n d(x)+d_0-d(x)]}` gives
:math:`t=h_0e^{-j(n-1)k_0ax}`.  Multiplying an axial plane wave adds transverse
wavevector :math:`k_x=(n-1)k_0a`; hence
:math:`\boxed{\theta\simeq(n-1)a}`, identical to the small-angle ray result.

.. rubric:: Exercise 2.4-2 — Double-convex lens

Adding the two parabolic surface sags leaves the quadratic phase
:math:`t=h_0\exp[-jk_0(x^2+y^2)/(2f)]`, where
:math:`\boxed{f^{-1}=(n-1)(R_1^{-1}-R_2^{-1})}`.

.. rubric:: Exercise 2.4-3 — Lens focusing

An axial plane wave multiplied by the lens phase becomes
:math:`A_0e^{-jk_0\rho^2/(2f)}`, the converging paraboloidal wave centered at
:math:`z=f`.  Incidence angle :math:`\theta` contributes
:math:`e^{-jk_0x\theta}` and translates the focus to
:math:`\boxed{x_f=f\theta}`.

.. rubric:: Exercise 2.4-4 — Imaging by phase matching

The incident paraboloid contributes :math:`+k\rho^2/(2z_1)` and the lens
:math:`-k\rho^2/(2f)`.  The result equals the outgoing paraboloid phase
:math:`-k\rho^2/(2z_2)` precisely when
:math:`\boxed{z_1^{-1}+z_2^{-1}=f^{-1}}`.

.. rubric:: Exercise 2.4-5 — Sinusoidal phase grating

Insertion of :math:`d=d_0[1+\cos(2\pi x/\Lambda)]/2` gives the stated phase
grating.  The Jacobi--Anger expansion
:math:`e^{-j\beta\cos Kx}=\sum_q(-j)^qJ_q(\beta)e^{jqKx}` produces orders

.. math:: \boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda},

with complex amplitudes :math:`h_0(-j)^qJ_q(\beta)` and
:math:`\beta=(n-1)k_0d_0/2`.

.. rubric:: Exercise 2.4-6 — GRIN plate

The accumulated phase is
:math:`-k_0n_0d_0+k_0n_0d_0a^2\rho^2/2`; comparison with a thin-lens
quadratic phase gives :math:`\boxed{f=(n_0d_0a^2)^{-1}}` (the sign follows
the propagation convention).

.. rubric:: Exercise 2.5-1 — Plane/spherical interference

Writing the phase difference as :math:`\phi=k(x^2+y^2)/(2d)+\phi_0`,

.. math:: I=I_1+I_2+2\sqrt{I_1I_2}\cos\phi.

For equal intensities, zeros obey
:math:`k\rho_m^2/(2d)+\phi_0=(2m+1)\pi`; they are concentric circular rings.

.. rubric:: Exercise 2.5-2 — Young interference

The two Fresnel phases differ by :math:`2kax/d=kx\theta`, where
:math:`\theta\simeq2a/d`.  Thus
:math:`\boxed{I=2I_0[1+\cos(2\pi x\theta/\lambda)]}` and the fringe spacing is
:math:`\lambda/\theta=\lambda d/(2a)`.

.. rubric:: Exercise 2.5-3 — Bragg reflection

Adjacent planes add path :math:`2\Lambda\sin\theta`, so
:math:`\phi=2k\Lambda\sin\theta`.  The phasors align when
:math:`\boxed{2\Lambda\sin\theta=m\lambda}`; the peak intensity scales as
:math:`M^2` for :math:`M` equal-amplitude planes.

.. rubric:: Exercise 2.6-1 — Optical Doppler radar

Superposing reference and return fields gives
:math:`I=I_1+I_2+2\sqrt{I_1I_2}\cos(2\pi\Delta\nu t+\phi)`.
Measure the electrical beat frequency and use
:math:`\boxed{v=c|\Delta\nu|/(2\nu)=\lambda|\Delta\nu|/2}`; quadrature phase
or a frequency offset resolves the velocity sign.

End-of-chapter problems
-----------------------

.. rubric:: Problem 2.2-3 — Spherical Helmholtz solution

For :math:`U=Ae^{-jkr}/r`, spherical symmetry gives
:math:`\nabla^2U=r^{-2}\partial_r(r^2\partial_rU)=-k^2U` for :math:`r>0`;
therefore :math:`(\nabla^2+k^2)U=0` away from the point source.

.. rubric:: Problem 2.2-4 — Spherical-wave intensity

Power conservation over a sphere gives
:math:`\boxed{I(r)=P/(4\pi r^2)}`.  For :math:`P=100\ \mathrm W` at
:math:`r=1\ \mathrm m`, :math:`\boxed{I=7.96\ \mathrm{W,m^{-2}}}`.

.. rubric:: Problem 2.2-5 — Cylindrical wave

The outgoing exact solution is :math:`U=A H_0^{(2)}(k\rho)` with
:math:`\rho=\sqrt{x^2+z^2}`.  For :math:`k\rho\gg1`,
:math:`U\propto e^{-jk\rho}/\sqrt{\rho}` and
:math:`\boxed{I=P_\ell/(2\pi\rho)}`, where :math:`P_\ell` is power per unit
length along the cylinder axis.

.. rubric:: Problem 2.2-6 — Paraxial Helmholtz equation

Set :math:`U=Ae^{-jkz}` in :math:`(\nabla^2+k^2)U=0`.  Exact substitution
gives :math:`\nabla_T^2A+\partial_z^2A-2jk\partial_zA=0`; dropping the slowly
varying :math:`\partial_z^2A` term yields
:math:`\boxed{\nabla_T^2A-2jk\partial_zA=0}`.

.. rubric:: Problem 2.2-7 — Conjugate waves

:math:`U` and :math:`U^*` have identical intensity but opposite phase and
opposite wavefront normals.  Thus the conjugate of the stated plane wave
travels along :math:`-(\hat x+\hat y)/\sqrt2`; the conjugate of an outgoing
:math:`e^{-jkr}/r` spherical wave is an incoming :math:`e^{+jkr}/r` wave.

.. rubric:: Problem 2.3-1 — Wavefronts in a SELFOC slab

Wavefront normals follow the sinusoidal GRIN rays.  Draw curves orthogonal to
that ray family: initially planar fronts bend toward the high-index axis,
become most curved before the quarter pitch, planar again at a focus crossing,
and repeat with the pitch :math:`2\pi/a`.

.. rubric:: Problem 2.4-7 — Spherical wave at a plane mirror

Reflect every local plane-wave component by reversing its normal component.
Their normals then converge to the mirror image of the source, so the reflected
field is a spherical wave centered at the virtual image point, with the mirror
reflection coefficient multiplying its amplitude.

.. rubric:: Problem 2.4-8 — Optical path through layers

Ignoring interface reflections,
:math:`t=\exp[-jk_0\sum_qn_qd_q]`.  Equal free-space phase requires
:math:`\boxed{d=\sum_qn_qd_q}`, exactly the optical path length.

.. rubric:: Problem 2.4-9 — Binary phase grating

For equal half-period levels with transmittances :math:`t_1,t_2`, Fourier
coefficients are :math:`c_0=(t_1+t_2)/2` and
:math:`c_q=(t_1-t_2)\sin(q\pi/2)/(q\pi)` for :math:`q\ne0` (up to the chosen
cell origin phase).  Each coefficient launches an order at
:math:`\boxed{\theta_q\simeq\theta_i+q\lambda/\Lambda}`; even nonzero orders
vanish for the symmetric 50% duty cycle.

.. rubric:: Problem 2.4-10 — Spherical mirror as a phase element

Reflection doubles the surface-sag phase.  With
:math:`s\simeq(x^2+y^2)/(2R)`,
:math:`r=h_0e^{-j2k_0s}=h_0e^{-jk_0(x^2+y^2)/R}`.  It equals the thin-lens
phase for :math:`\boxed{f=-R/2}`.

.. rubric:: Problem 2.5-4 — Standing wave

For equal counterpropagating fields,
:math:`U=2A\cos(kz)` and
:math:`\boxed{I(z)=4I_0\cos^2(kz)}`.  Nodes are separated by
:math:`\lambda/2` and alternate with antinodes.

.. rubric:: Problem 2.5-5 — Fringe visibility

:math:`I_{max,min}=I_1+I_2\pm2\sqrt{I_1I_2}`, hence
:math:`\boxed{V=2\sqrt{I_1I_2}/(I_1+I_2)}`.  Differentiating versus
:math:`I_1/I_2` gives the maximum :math:`V=1` at equal intensities.

.. rubric:: Problem 2.5-6 — Misaligned Michelson mirror

The returning waves have a linear transverse phase difference and therefore
form straight, equally spaced fringes perpendicular to the tilt.  Translating
the other mirror adds a uniform phase :math:`4\pi\Delta z/\lambda`, so the
whole fringe set slides; one fringe passes a point per :math:`\lambda/2` of
mirror travel.

.. rubric:: Problem 2.6-2 — Pulsed spherical wave

Every spectral component propagates as :math:`e^{-jkr}/r`; inverse Fourier
transformation gives :math:`\boxed{U(r,t)=a(t-r/c)/r}`.  For
:math:`\lambda_0=585\ \mathrm{nm}` and RMS duration :math:`6\ \mathrm{fs}`,
the RMS interval contains :math:`c\sigma_t/\lambda_0=\boxed{3.08}` carrier
cycles.  At :math:`1\ \mathrm{ps}` the intensity is a Gaussian spherical shell
centered at :math:`r=ct=0.2998\ \mathrm{mm}`, RMS radial thickness
:math:`c\sigma_t=1.80\ \mathrm{\mu m}`, and amplitude falloff :math:`1/r^2`.
