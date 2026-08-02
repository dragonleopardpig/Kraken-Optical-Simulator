Chapter 10: Resonator Optics
============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 10.

In-text exercises
-----------------

.. rubric:: Exercise 10.1-1 — Ring and bow-tie resonances

Require total propagation plus mirror phase to equal :math:`2\pi q`.  For
round-trip optical length :math:`L_o`,
:math:`\boxed{\nu_q=c(q-N_m/2)/L_o}` and
:math:`\boxed{\nu_F=c/L_o}`; :math:`N_m=3,4` supplies the ring/bow-tie phase
offset, which can be absorbed into the integer for four mirrors.

.. rubric:: Exercise 10.1-2 — One-metre Fabry--Perot

:math:`\nu_F=c/(2d)=149.90` MHz.  With
:math:`\mathcal F=\pi(R_1R_2)^{1/4}/[1-\sqrt{R_1R_2}]=207.69`, the FWHM is
:math:`\boxed{0.7217\ \mathrm{MHz}}`.  Loss per round trip is 1.51%, small
enough for the high-finesse approximation.

.. rubric:: Exercise 10.2-1 — Maximum stable length

Using :math:`g_i=1-d/|R_i|`, stability requires
:math:`0<g_1g_2<1`.  For 0.50 and 1.00 m radii the stable intervals meet at
the marginal endpoints; the largest confined length is
:math:`\boxed{d<1.50\ \mathrm m}`.

.. rubric:: Exercise 10.2-2 — Plano-concave cavity

With :math:`g_1=1`, stability is :math:`0<d<|R_2|`.  The waist is at the
plane mirror, :math:`z_0=\sqrt{d(|R_2|-d)}`,
:math:`W_0^2=\lambda z_0/(\pi n)`, and
:math:`W_2=W_0\sqrt{1+(d/z_0)^2}` at the curved mirror.

.. rubric:: Exercise 10.2-3 — Confocal frequency comb

For :math:`d=0.30` m, :math:`\nu_F=c/(2d)=499.65` MHz and each increment of
:math:`l+m+1` shifts a comb by :math:`\nu_F/2=249.83` MHz.  The frequencies
in the requested band are
:math:`\nu=(q+(l+m+1)/2)\nu_F` satisfying
:math:`|\nu-5\times10^{14}|\leq2` GHz; enumerating the corresponding integers
produces two interleaved 249.83-MHz combs.

.. rubric:: Exercise 10.2-4 — Confocal degeneracy

The Gouy phase per half trip is :math:`\pi/2` in a confocal cavity, so
:math:`\nu_{qlm}=[q+(l+m+1)/2]\nu_F`.  Even transverse-order changes are
absorbed into :math:`q`; odd changes shift the line by :math:`\nu_F/2`.

.. rubric:: Exercise 10.3-1 — Two-dimensional mode density

Count lattice points :math:`(q_x,q_y)` inside a quarter-circle in wavevector
space and include two polarizations.  Differentiation gives
:math:`\boxed{M_2(\nu)/A=2\pi\nu/c^2}` modes per area per hertz.

End-of-chapter problems
-----------------------

.. rubric:: Problem 10.1-3 — Resonator with an etalon

Empty-cavity spacing is :math:`c/(2d)=\boxed{0.9993\ \mathrm{GHz}}` for
:math:`d=15` cm.  Replacing 2.5 cm of air by index 1.5 raises one-way optical
length to 16.25 cm, giving :math:`\boxed{0.9224\ \mathrm{GHz}}`.

.. rubric:: Problem 10.1-4 — Cleaved semiconductor cavity

:math:`R=[(3.6-1)/(3.6+1)]^2=0.31947` and
:math:`\nu_F=c/(2nd)=208.19` GHz.  Combine absorption and mirror loss as
:math:`\alpha_r=\alpha_s-[\ln(R_1R_2)]/(2d)=5.81\times10^3`
:math:`\mathrm{m^{-1}}`; this gives :math:`\mathcal F=2.71`, linewidth
:math:`76.9` GHz, and :math:`Q=\nu/\delta\nu\simeq2.51\times10^3` at 1.55
micrometres.  The longitudinal order is :math:`q=2nd/\lambda=\boxed{929}`.

.. rubric:: Problem 10.1-5 — Bragg-mirror etalon

At the Bragg frequency each 10-pair reflector has
:math:`R=[(1-(3.2/3.6)^{20})/(1+(3.2/3.6)^{20})]^2`.  Insert this in
:math:`\mathcal F=\pi\sqrt R/(1-R)` and
:math:`Q=q\mathcal F`; the same characteristic-matrix calculation also
includes penetration phase if the GaAs cavity thickness is specified.

.. rubric:: Problem 10.1-6 — Measured spectral response

:math:`d=c/(2\nu_F)=\boxed{0.9993\ \mathrm m}` and
:math:`\mathcal F=150/5=\boxed{30}`.  Solving
:math:`\mathcal F=\pi\sqrt R/(1-R)` for identical mirrors gives
:math:`\boxed{R=0.90062}`.

.. rubric:: Problem 10.1-7 — Half-energy time

The energy lifetime is :math:`\tau=\mathcal F/(2\pi\nu_F)`; therefore
:math:`t_{1/2}=\tau\ln2=\mathcal F nd\ln2/(\pi c)=
\boxed{36.80\ \mathrm{ns}}`.

.. rubric:: Problem 10.2-5 — Convex mirrors

Two convex mirrors have :math:`g_1,g_2>1`, so their product exceeds one and
cannot be stable.  One convex and one concave mirror can be stable when their
signed :math:`g` factors have a product strictly between zero and one.

.. rubric:: Problem 10.2-6 — Lens inside plane mirrors

The round-trip matrix is
:math:`M=P(d/2)L(f)P(d)L(f)P(d/2)` (choosing a mirror immediately after the
start plane).  Multiplication and :math:`|\operatorname{tr}M/2|<1` give
:math:`\boxed{0<d/f<4}`.  The matched Gaussian has waists symmetrically placed
about the lens and wavefronts planar at the mirrors.

.. rubric:: Problem 10.2-7 — Ray retracing

Here :math:`g=1-d/|R|=-1/2` and the round-trip eigenphase satisfies
:math:`\cos\mu=2g^2-1=-1/2`; hence :math:`\mu=2\pi/3` and every ray retraces
after :math:`\boxed{3}` round trips.

.. rubric:: Problem 10.2-8 — Unstable recurrence

The round-trip characteristic equation has real roots
:math:`h_{1,2}=b\pm\sqrt{b^2-1}`.  Diagonalizing the matrix gives
:math:`\boxed{y_m=\alpha_1h_1^m+\alpha_2h_2^m}`; one root has magnitude above
one, which is the exponential escape.

.. rubric:: Problem 10.2-9 — Symmetric unstable cavity

For :math:`R=-30` cm and :math:`d=65` cm,
:math:`g=1-d/30=-1.1667`, so :math:`g^2>1` is unstable.  Apply the explicit
round-trip ABCD matrix to :math:`(y_0,\theta_0)=(0,0.1^\circ)` repeatedly;
the first :math:`m` with :math:`|y_m|>2.5` cm is the aperture escape count.
The same recurrence plotted at 50 cm stays bounded while 65 cm grows.

.. rubric:: Problem 10.2-10 — Gaussian standing wave

Adding equal counterpropagating Gaussian fields gives the common transverse
envelope times :math:`2\cos[kz-(l+m+1)\psi(z)]`.  Requiring nodes/antinodes on
both matching mirror wavefronts yields
:math:`2knd-2(l+m+1)\Delta\psi=2\pi q`, the resonance formula (10.2-30).

.. rubric:: Problem 10.2-11 — Sixteen-centimetre confocal cavity

:math:`R_1=R_2=-d=\boxed{-16\ \mathrm{cm}}`,
:math:`z_0=d/2=8` cm, :math:`W_0=\sqrt{\lambda z_0/\pi}=
\boxed{159.6\ \mathrm{\mu m}}`, and mirror width 225.7 micrometres.  HG10
peaks are 319.2 micrometres apart.  Frequencies follow the confocal formula
above; mirror-only distributed loss is
:math:`-\ln(0.995^2)/(2d)=\boxed{0.0313\ \mathrm{m^{-1}}`.

.. rubric:: Problem 10.2-12 — One-percent diffraction aperture

Read :math:`N_F` at 1% loss for the (1,0) curve in Fig. 10.2-11, then use
:math:`\boxed{a=\sqrt{N_F\lambda d}}` with :math:`\lambda=1` micrometre and
:math:`d=0.16` m.  Reporting the graph-read :math:`N_F` beside the result
keeps the scan-dependent interpolation auditable.

.. rubric:: Problem 10.3-2 — Counts in 1-D, 2-D, and 3-D

For 1.06 micrometres, 120 GHz bandwidth, and 10-cm dimensions, the continuum
counts (including two polarizations in 2-D/3-D) are
:math:`\boxed{80.1}`, :math:`\boxed{2.37\times10^7}`, and
:math:`\boxed{8.95\times10^{12}}`, from
:math:`2d\Delta\nu/c`, :math:`A(2\pi\nu/c^2)\Delta\nu`, and
:math:`V(8\pi\nu^2/c^3)\Delta\nu`, respectively.
