Chapter 12: Photon Optics
=========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 12.

In-text exercises
-----------------

.. rubric:: Exercise 12.1-1 — Photons in a Gaussian beam

Normalize :math:`e^{-2\rho^2/W_0^2}` over the plane.  The probability inside
:math:`W_0` is :math:`\boxed{1-e^{-2}=0.8647}`; for :math:`n` independent
photons the expected count is :math:`n(1-e^{-2})`.

.. rubric:: Exercise 12.1-2 — Mercury recoil

:math:`p_\gamma=E/c` and :math:`v_r=p_\gamma/(198u)` give
:math:`\boxed{v_r=7.93\times10^{-3}\ \mathrm{m/s}}`.  From
:math:`mv_{rms}^2/2=3kT/2`, :math:`v_{rms}=\boxed{194\ \mathrm{m/s}}`; thermal
motion is about :math:`2.45\times10^4` times larger.

.. rubric:: Exercise 12.1-3 — One photon in a Mach--Zehnder

The chosen output probability is
:math:`\boxed{P_D=\cos^2(\pi d/\lambda)}` (the other port has sine squared;
port labels may swap).  At a nonunity value the photon state is a coherent
superposition of the two output possibilities, not a classical fraction in
each arm.

.. rubric:: Exercise 12.1-4 — Gaussian wavepacket uncertainty

Normalize :math:`|a(t)|^2=e^{-t^2/(2T^2)}` to obtain
:math:`\sigma_t=T` and :math:`\sigma_z=cT`.  Fourier transformation gives
:math:`\sigma_\omega=1/(2T)`, so
:math:`\boxed{\sigma_E\sigma_t=\hbar/2}` and, with
:math:`p_z=E/c`, :math:`\boxed{\sigma_z\sigma_p=\hbar/2}`.

.. rubric:: Exercise 12.2-1 — Mean thermal-mode energy

Average :math:`nh\nu` over the geometric distribution to get
:math:`\boxed{\bar E=h\nu/[e^{h\nu/kT}-1]}`.  For
:math:`h\nu\ll kT`, expand the exponential and recover
:math:`\bar E\to kT`; increasing frequency or lowering temperature suppresses
the mean energy exponentially.

End-of-chapter problems
-----------------------

.. rubric:: Problem 12.1-5 — Combining photon energies

(a) :math:`eV=hc/\lambda` gives :math:`\boxed{V=1.425\ \mathrm V}` at 0.87
micrometres.  (b) Sum-frequency energy gives
:math:`1/\lambda_3=1/1.06+1/10.6`, hence
:math:`\boxed{\lambda_3=0.9636\ \mathrm{\mu m}}`.

.. rubric:: Problem 12.1-6 — Exponential radial beam

Radial normalization uses :math:`2\pi\int_0^\infty\rho e^{-\rho/\rho_0}d\rho`.
Inside :math:`\rho_0`, :math:`\boxed{P=1-2/e=0.26424}`; one million photons
therefore give :math:`\boxed{2.6424\times10^5}` on average.

.. rubric:: Problem 12.1-7 — Momentum comparisons

The 10-J light pulse has :math:`p=E/c=\boxed{3.336\times10^{-8}}`
kg m/s; the 1-g body has :math:`10^{-5}` kg m/s; a nonrelativistic electron
at :math:`c/10` has :math:`2.73\times10^{-23}` kg m/s.

.. rubric:: Problem 12.1-8 — Gaussian photon momentum

The angular-spectrum probability is Gaussian; integration inside the
:math:`1/e^2` divergence angle gives :math:`\boxed{1-e^{-2}}`.  Every plane
wave component still has :math:`|\mathbf p|=E/c`, but its direction is random;
the mean axial momentum is slightly below :math:`E/c`.

.. rubric:: Problem 12.1-9 — Ideal atom levitation

:math:`F_g=mg=1.63\times10^{-26}` N.  One absorbed 1-eV photon per second
gives :math:`5.34\times10^{-28}` N, so :math:`\boxed{30.5}` photons/s and
:math:`\boxed{4.88\times10^{-18}\ \mathrm W}` balance gravity.  Perfect
reflection doubles momentum transfer and halves the rate to 15.2 photons/s.

.. rubric:: Problem 12.1-10 — One cavity photon

:math:`k=10^5\pi/d`, so the in-medium wavelength is 0.20 micrometres, free
wavelength :math:`\boxed{0.300\ \mathrm{\mu m}}`, and energy
:math:`\boxed{4.13\ \mathrm{eV}}`.  The high-order standing-wave position is
nearly uniform over 1 cm, :math:`\sigma_x\simeq d/\sqrt{12}`; momentum has
equal :math:`\pm\hbar k` outcomes.  Their product greatly exceeds
:math:`\hbar/2`; this is not a minimum-uncertainty packet.

.. rubric:: Problem 12.1-11 — Single-photon beating

Normalize over one beat period:
:math:`p(t)=T^{-1}[1+\cos(2\pi t/T)]`; it vanishes at
:math:`\boxed{t=T/2}`.  Resolving which energy to better than
:math:`h|\nu_2-\nu_1|` requires :math:`\Delta t\gtrsim1/[4\pi|\Delta\nu|]`,
of the beat-period order, destroying the timing information needed to see the
interference.

.. rubric:: Problem 12.1-12 — Beamsplitter momentum

Before incidence :math:`\mathbf p=\hbar\mathbf k_i`.  Afterward measurement
returns :math:`\hbar\mathbf k_t` with probability :math:`T` or
:math:`\hbar\mathbf k_r` with probability :math:`R=1-T`; before measurement
the photon occupies their coherent superposition.

.. rubric:: Problem 12.2-2 — One photon per cycle

Photon rate is :math:`\nu` and photon energy :math:`h\nu`, so
:math:`\boxed{P=h\nu^2=hc^2/\lambda^2}`.

.. rubric:: Problem 12.2-3 — Poisson moments

Using :math:`\sum\bar n^n/n!=e^{\bar n}` proves normalization.  Differentiating
that generating function once and twice gives
:math:`\boxed{\langle n\rangle=\bar n}` and
:math:`\boxed{\operatorname{var}n=\bar n}`.

.. rubric:: Problem 12.2-4 — Weak coherent He--Ne beam

Total mean in 100 ns is :math:`PT/(hc/\lambda)=31.86`; inside :math:`W_0`,
:math:`\boxed{\bar n=27.55}`.  Poisson RMS fluctuation is
:math:`\boxed{5.25}` and zero-count probability
:math:`\boxed{e^{-27.55}=1.08\times10^{-12}}`.

.. rubric:: Problem 12.2-5 — Bose--Einstein counts

Geometric-series sums give normalization, mean :math:`\bar n`, and variance
:math:`\bar n+\bar n^2`.  Mean flux one/ns over 20 ns gives
:math:`\bar n=20`, so :math:`\boxed{P(0)=1/(1+\bar n)=1/21}`.

.. rubric:: Problem 12.2-6 — Negative-binomial limits

Set :math:`M=1` to recover the geometric distribution.  For fixed
:math:`\bar n` and :math:`M\to\infty`, use
:math:`(1+\bar n/M)^{-M}\to e^{-\bar n}` and the factorial ratio
:math:`\to M^n/n!`; the result is Poisson.

.. rubric:: Problem 12.2-7 — Multimode thermal variance

Independent mode means/variances add.  With total
:math:`\bar n=M\bar n_1`,
:math:`\boxed{\sigma_n^2=\bar n+\bar n^2/M}`; more modes average thermal
bunching toward Poisson statistics.

.. rubric:: Problem 12.2-8 — Gamma-mixed Poisson process

Insert the gamma density in Mandel's integral
:math:`P(n)=\int e^{-w}w^n p(w)dw/n!`.  The remaining gamma integral is
:math:`\Gamma(n+M)` and simplification gives exactly the negative-binomial
distribution of Problem 12.2-6.

.. rubric:: Problem 12.2-9 — Doubly stochastic moments

Conditional Poisson moments are :math:`E[n|W]=W` and
:math:`\operatorname{var}(n|W)=W`.  Total expectation/variance therefore give
:math:`\boxed{E[n]=E[W]}` and
:math:`\boxed{\operatorname{var}n=E[W]+\operatorname{var}W}`.

.. rubric:: Problem 12.2-10 — Partitioned coherent light

Binomial thinning of a Poisson generating function
:math:`G(z)=e^{\bar n(z-1)}` gives
:math:`G_R(z)=G[T+Rz]=e^{R\bar n(z-1)}`.  Thus reflected counts remain
Poisson with mean/variance :math:`\boxed{R\bar n}`.

.. rubric:: Problem 12.2-11 — Partitioned thermal light

Apply the same substitution to geometric
:math:`G(z)=[1+\bar n(1-z)]^{-1}`.  It remains geometric with mean
:math:`R\bar n` and variance :math:`R\bar n+(R\bar n)^2`, proving all three
parts.

.. rubric:: Problem 12.2-12 — Absorber thinning

:math:`d\bar n/dx=-\alpha\bar n` gives
:math:`\bar n(x)=\bar n_0e^{-\alpha x}`.  Coherent input remains Poisson with
that mean under independent absorption.  A single photon survives thickness
:math:`d` with probability :math:`\boxed{e^{-\alpha d}}`.

.. rubric:: Problem 12.3-1 — Binomial light

Send an :math:`M`-photon number state through a beamsplitter of transmission
:math:`p`.  The binomial theorem proves normalization and gives
:math:`\bar n=Mp`, :math:`\sigma^2=Mp(1-p)`, and
:math:`\boxed{\mathrm{SNR}=\bar n/(1-p)}` for power SNR
:math:`\bar n^2/\sigma^2`.  :math:`p\to0` approaches Poisson thinning;
:math:`p\to1` approaches a noiseless number state.

.. rubric:: Problem 12.3-2 — Discrete-uniform source

For uniform integers :math:`0,\ldots,2\bar n`, finite sums give
:math:`\sigma^2=\bar n(\bar n+1)/3` and
:math:`\boxed{\mathrm{SNR}=3\bar n/(\bar n+1)}`.  Relative to Poisson SNR
:math:`\bar n`, it is quieter for :math:`\bar n<2`, equal at 2, and noisier
above 2; its SNR is exactly three times the single-mode thermal value
:math:`\bar n/(1+\bar n)`.
