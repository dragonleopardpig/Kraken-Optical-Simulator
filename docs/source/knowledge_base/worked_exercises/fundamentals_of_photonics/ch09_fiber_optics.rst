Chapter 9: Fiber Optics
=======================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 9.

In-text exercises
-----------------

.. rubric:: Exercise 9.3-1 — Optimum power-law profile

Differentiate the modal propagation constant with respect to frequency,
including :math:`n_1(\omega)` and :math:`\Delta(\omega)`, to obtain Eq.
(9.3-10).  Its mode-dependent coefficient vanishes at
:math:`\boxed{p_{opt}=2+P_s}` to first order (reducing to the parabolic
:math:`p=2` profile when material parameters are wavelength independent).

.. rubric:: Exercise 9.3-2 — Rotated birefringent segments

Each half has polarization delay
:math:`(N_y-N_x)(0.5\ \mathrm{km})/c=1.668` ns and chromatic broadening
:math:`D L\Delta\lambda=500` ps.  Resolve the 45-degree input into the first
segment axes, delay/broaden both pulses, rotate those components by 45 degrees,
and repeat for the second segment.  The full-fibre principal states are the
eigenvectors of the product of the two frequency-dependent Jones matrices;
launching either eigenvector produces one output pulse rather than a
first-order split.

End-of-chapter problems
-----------------------

.. rubric:: Problem 9.1-1 — Source coupling

Integrating :math:`(P_0/\pi)\cos\theta` over the acceptance cone gives
:math:`P=P_0\sin^2\theta_a=P_0\mathrm{NA}^2`.  For the bonded LED,
:math:`\sin\theta_a=\sqrt{1.46^2-1.455^2}/3.5=0.03450`; hence
:math:`\boxed{\eta=1.190\times10^{-3}}` (0.119%).

.. rubric:: Problem 9.1-2 — Step versus graded NA

The step fibre gives :math:`n_1\sqrt{2\Delta}=0.2051`.  A parabolic profile
with the same center-to-edge :math:`\Delta_0` has
:math:`n_0aa_f=n_1\sqrt{2\Delta_0}` to first order, so its on-axis acceptance
NA is the same; acceptance decreases for off-axis launch in the graded fibre.

.. rubric:: Problem 9.2-1 — Single-mode cutoff

:math:`\mathrm{NA}\simeq n_1\sqrt{2\Delta}=0.0917` and setting
:math:`V=2\pi a\mathrm{NA}/\lambda=2.405` gives
:math:`\boxed{\lambda_c\simeq1.20\ \mathrm{\mu m}}`.  At half that wavelength
:math:`V=4.81`; guided LP families are :math:`(l,m)=(0,1),(1,1),(2,1),(0,2)`
with the usual polarization/azimuthal degeneracies.

.. rubric:: Problem 9.2-2 — Step-fibre modal pulse

Ray optics maps uniformly excited meridional angles to delays
:math:`t(\theta)=n_1L/(c\cos\theta)`, producing a continuous broadened tail
from the axial to limiting ray.  Wave optics replaces that continuum by a
finite comb at :math:`t_m=L/v_{gm}` for the allowed :math:`l=0` modes; each
delta-like modal contribution carries its launch-overlap weight.

.. rubric:: Problem 9.2-3 — Propagation constants from normalized curves

First :math:`a=V\lambda_0/(2\pi\sqrt{n_1^2-n_2^2})`; for :math:`V=10`,
:math:`\boxed{a=32.9\ \mathrm{\mu m}}`.  Read each :math:`l=0` normalized
:math:`b` from Fig. 9.2-3 and convert with
:math:`\beta^2=k_0^2[n_2^2+b(n_1^2-n_2^2)]`.  At :math:`V=4`, the same
:math:`b(V)` curve gives :math:`v_p=\omega/\beta` and
:math:`v_g=(d\beta/d\omega)^{-1}`; this states the complete reproducible
figure-reading calculation without inventing graph coordinates.

.. rubric:: Problem 9.2-4 — Step-index quasi-plane waves

For :math:`l=1`, use the allowed radial integers in
:math:`k_r^2+(l/r)^2+k_z^2=n_1^2k_0^2`; the largest/smallest roots of the
characteristic equation give the requested :math:`\beta=k_z`.  Turning radii
satisfy :math:`k_r=0`, and at :math:`r=5` micrometres the components are
:math:`(k_r,l/r,\beta)`.  Reject roots whose turning shell crosses the core
boundary without evanescent confinement.

.. rubric:: Problem 9.2-5 — Graded-index quasi-plane waves

Repeat Problem 9.2-4 with local
:math:`n^2(r)\simeq n_1^2[1-2\Delta(r/a)^2]`.  The radial equation is harmonic,
so :math:`\beta_q\simeq n_1k_0[1-(2\Delta/V)(2m+l+1)]`; setting
:math:`k_r^2=0` gives the inner/outer turning radii and the same local
wavevector-component construction.

.. rubric:: Problem 9.3-3 — Absorption plus Rayleigh scattering

Rayleigh loss scales as :math:`\lambda^{-4}`:
:math:`2.25(820/600)^4=7.85` dB/km.  Adding the measured 2 dB/km absorption
gives :math:`\boxed{9.85\ \mathrm{dB/km}}` total.

.. rubric:: Problem 9.3-4 — A 5000-mode step fibre

With :math:`M\simeq V^2/2`, :math:`V=100`; therefore
:math:`\boxed{a=V\lambda/(2\pi\mathrm{NA})=138.5\ \mathrm{\mu m}}`.
:math:`\Delta\simeq\mathrm{NA}^2/(2n_1^2)=0.002395`; the 2-km modal spread
:math:`LN_1\Delta/c` is :math:`\boxed{23.3\ \mathrm{ns}}`.

.. rubric:: Problem 9.3-5 — Power-law graded fibres

Here :math:`V=2\pi(a/\lambda)n_1\sqrt{2\Delta}=12.88` and
:math:`\boxed{M=[p/(p+2)]V^2/2}`.  Insert :math:`p=1.9,2,2.1,\infty` in this
and in the chapter result
:math:`\Delta\tau/L=(n_1\Delta/c)|p-2|/(p+2)` (retaining the second-order
:math:`\Delta^2` term at :math:`p=2`).  The parabolic profile has the smallest
spread; :math:`p=\infty` recovers the step fibre.

.. rubric:: Problem 9.3-6 — Pulse-width trends

Combine independent broadening in quadrature:
:math:`T_{out}^2\simeq T_0^2+[L\Delta\tau_m(p)]^2+
[L|D_\lambda|\Delta\lambda]^2`.  Increasing :math:`L,|D_\lambda|`, or source
linewidth always broadens; increasing :math:`T_0` raises absolute width but
reduces fractional broadening; moving :math:`p` toward its optimum reduces
modal spread; changing wavelength acts through :math:`D_\lambda`, NA, and
normalized frequency, so its sign cannot be stated without those dispersion
curves.
