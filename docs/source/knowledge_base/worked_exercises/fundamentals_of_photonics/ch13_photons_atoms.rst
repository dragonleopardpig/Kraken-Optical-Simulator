Chapter 13: Photons and Atoms
=============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 13.

In-text exercises
-----------------

.. rubric:: Exercise 13.3-1 — Spontaneous-emission spectrum

The total spontaneous rate is :math:`1/t_{sp}` and normalized lineshape
:math:`\int g(\nu)d\nu=1`; therefore
:math:`\boxed{P_{sp}(\nu)=g(\nu)/t_{sp}}`.  A large photon histogram converges
to this probability density and is consequently proportional to :math:`g`.

.. rubric:: Exercise 13.3-2 — Doppler broadening

Map velocity to frequency shift :math:`\delta\nu=\nu_0v/c`.  The Gaussian
standard deviation is :math:`\sigma_\nu=(\nu_0/c)\sqrt{kT/M}`; convolution
with the natural Lorentzian gives a Voigt profile.  In the Doppler-dominated
limit its FWHM is
:math:`\boxed{\Delta\nu_D=(2\nu_0/c)\sqrt{2kT\ln2/M}}`.

.. rubric:: Exercise 13.4-1 — Blackbody peak in frequency

Differentiating :math:`\nu^3/(e^{h\nu/kT}-1)` gives
:math:`3(1-e^{-x})=x`; Newton iteration yields :math:`x=2.82144`.  At 300 K,
:math:`\boxed{\nu_p=1.764\times10^{13}\ \mathrm{Hz}}`.

End-of-chapter problems
-----------------------

.. rubric:: Problem 13.3-3 — Stimulated versus spontaneous decay

For either populated cavity mode, evaluate
:math:`P_{st}=n(c/V)\sigma(\nu)` with Lorentzian
:math:`\sigma=Sg(\nu)` and :math:`S=\lambda_0^2/(8\pi n^2t_{sp})` under the
book's polarization convention.  The upper population decays with
:math:`\tau^{-1}=t_{sp}^{-1}+\sum P_{st}`.  Equality of stimulated and total
spontaneous rates follows by setting :math:`\sum n(c/V)\sigma=t_{sp}^{-1}`;
this equation gives the requested replacement photon number unambiguously.

.. rubric:: Problem 13.3-4 — Emission into cavity modes

For a 1-micrometre cube, :math:`\nu=(c/2L)sqrt{q_x^2+q_y^2+q_z^2}`.  The
lowest :math:`(1,1,1)` mode is 260 THz and the next permutations of
:math:`(2,1,1)` are 367 THz.  Spontaneous probability is proportional to
mode degeneracy times :math:`\nu^2g(\nu)` (or the transition lineshape at
that frequency); include the three permutations when forming
:math:`P_{sp,2}/P_{sp,1}`.

.. rubric:: Problem 13.4-2 — Broadband rate equations

With :math:`M(\nu_0)\Delta\nu` resonator modes,
:math:`\dot N_2=-N_2/t_{sp}-(N_2-N_1)B\rho` and
:math:`\dot n=[N_2/t_{sp}+(N_2-N_1)B\rho]/M- n/t_p`; add the companion
:math:`\dot N_1=-\dot N_2` for conserved atoms.  Here :math:`\rho` is the
energy density represented by the common mode occupation :math:`n`.

.. rubric:: Problem 13.4-3 — Two-dimensional blackbody

Chapter 10 counting gives :math:`M_2(\nu)/A=2\pi\nu/c^2`; multiplying by the
Planck mean energy gives
:math:`\boxed{Q_2(\nu)=2\pi h\nu^2/[c^2(e^{h\nu/kT}-1)]}`.  An atom's
spontaneous rate into this cavity is its per-mode rate times this 2-D mode
density; it is inhibited relative to the 3-D :math:`\nu^2` density according
to their ratio and the cavity thickness normalization.

.. rubric:: Problem 13.4-4 — Equal stimulated/spontaneous rates

Their ratio is the mean thermal occupation :math:`\bar n`.
:math:`\bar n=1` implies :math:`e^{hc/(\lambda kT)}=2`; at one micrometre,
:math:`\boxed{T=2.076\times10^4\ \mathrm K}`.

.. rubric:: Problem 13.4-5 — Wien displacement law

Change variables using :math:`Q_\lambda=Q_\nu|d\nu/d\lambda|`; maximizing
:math:`\lambda^{-5}/(e^{hc/\lambda kT}-1)` gives
:math:`5(1-e^{-y})=y`, :math:`y=4.96511`, and
:math:`\boxed{\lambda_pT=2.8978\times10^{-3}\ \mathrm{m,K}}`.  The frequency
and wavelength densities have different Jacobians, so
:math:`\lambda_p\ne c/\nu_p`.

.. rubric:: Problem 13.4-6 — One-dimensional blackbody

Including two traveling directions/polarizations according to the book's
1-D convention gives constant :math:`M_1/L=2/c`; hence
:math:`\boxed{Q_1(\nu)=2h\nu/[c(e^{h\nu/kT}-1)]}`.  It tends to
:math:`2kT/c` at zero frequency and decays exponentially at high frequency.

.. rubric:: Problem 13.4-7 — Stefan--Boltzmann law

Integrating the Planck spectrum with
:math:`\int_0^\infty x^3/(e^x-1)dx=\pi^4/15` and multiplying isotropic energy
density by :math:`c/4` gives
:math:`\boxed{P/A=\sigma T^4}` with
:math:`\boxed{\sigma=2\pi^5k^4/(15h^3c^2)=5.6704\times10^{-8}
\ \mathrm{W,m^{-2}K^{-4}}}`.

.. rubric:: Problem 13.5-1 — Compound-Poisson cathodoluminescence

Condition on :math:`m` incident electrons: photons are Poisson with mean
:math:`mG`; mix this over Poisson :math:`m` to get generating function
:math:`\boxed{G_N(z)=\exp\{\bar m[e^{G(z-1)}-1]\}}` (Neyman type A).
Differentiation gives :math:`\boxed{\bar n=\bar mG}` and
:math:`\boxed{\operatorname{var}n=\bar mG(1+G)}`.
