Chapter 8: Guided-Wave Optics
=============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 8.

In-text exercises
-----------------

.. rubric:: Exercise 8.1-1 — Modal power

For each constituent plane wave :math:`H=E/\eta`; its axial flux is reduced
by :math:`\cos\theta_m`.  Integrating the standing transverse pattern gives
:math:`\boxed{P_z=|a_m|^2\cos\theta_m/(2\eta)}` under the book's modal
normalization.

.. rubric:: Exercise 8.1-2 — Multimode power

Insert the modal sum in the Poynting integral.  Orthogonality makes every
cross integral zero, leaving
:math:`\boxed{P_z=\sum_m|a_m|^2\cos\theta_m/(2\eta)}`.

.. rubric:: Exercise 8.2-1 — Slab confinement

Integrate the sinusoidal core field and two exponential tails.  With
:math:`u=k_yd/2`, :math:`w=\gamma d/2`,
:math:`\Gamma=[1+\cos^2u/(2w(1/2+\sin2u/(4u)))]^{-1}` for an even TE mode.
The fundamental has the smallest :math:`u`, slowest evanescent leakage, and
therefore the largest confinement.

.. rubric:: Exercise 8.2-2 — Asymmetric slab

The stricter substrate interface sets
:math:`\sin\theta_{max}=\sqrt{1-(n_2/n_1)^2}` and
:math:`\mathrm{NA}=\sqrt{n_1^2-n_2^2}`.  Round-trip phase requires
:math:`2k_0n_1d\sin\theta-\phi_{12}-\phi_{13}=2\pi m`; for many modes,
:math:`M\simeq(2d/\lambda_0)\sqrt{n_1^2-n_2^2}` plus the endpoint mode.

End-of-chapter problems
-----------------------

.. rubric:: Problem 8.1-3 — Mirror-guide field

One exponential cannot vanish at both mirrors unless its amplitude is zero.
For two counter-inclined waves, imposing both zeros selects
:math:`k_y=m\pi/d`, equal :math:`\beta`, and relative sign determined by
parity; the statement's incompatible sign/parity choice is why the proposed
sum fails outside the matching sine/cosine family.

.. rubric:: Problem 8.1-4 — Mirror-guide dispersion

:math:`m_{max}=\lfloor2d/\lambda_0\rfloor=31` for each TE/TM family (with the
TEM endpoint counted by convention).  Since
:math:`v_{gm}=c\sqrt{1-(m\lambda_0/2d)^2}`, the fastest mode has :math:`c`, the
slowest :math:`0.19325c`; over 1 m the pulse spread is
:math:`\boxed{13.93\ \mathrm{ns}}`.

.. rubric:: Problem 8.2-3 — Film in index-1.4 cladding

:math:`\theta_c=\sin^{-1}(1.4/1.6)=61.05^\circ`, its complement is
:math:`28.95^\circ`, and :math:`\mathrm{NA}=0.77460` gives air acceptance
:math:`50.77^\circ`.  The normalized half-thickness is :math:`V=5.594`, so
there are four TE modes.  Solving :math:`u\tan u=\sqrt{V^2-u^2}` for TE0 gives
:math:`u=1.33063`, bounce angle :math:`6.612^\circ`, and
:math:`v_g\simeq(c/n_1)\cos\theta=\boxed{1.861\times10^8\ \mathrm{m/s}}`.

.. rubric:: Problem 8.2-4 — Film suspended in air

Now :math:`\theta_c=38.68^\circ`, complement :math:`51.32^\circ`, formal
:math:`\mathrm{NA}=1.249` (air acceptance saturates at 90 degrees), and
:math:`V=9.020`, giving six TE modes.  TE0 has
:math:`u=1.41345`, :math:`\theta=7.026^\circ`, and
:math:`v_g=1.860\times10^8\ \mathrm{m/s}`; lower cladding index mainly adds
higher modes and confinement.

.. rubric:: Problem 8.2-5 — TE0 field and confinement

Boundary continuity gives :math:`B=A\cos u\,e^{\gamma d/2}` for the outer
exponentials.  For the stated film, :math:`V=0.44812`,
:math:`u=0.41083`, :math:`w=0.17896`; integrating the three regions gives
:math:`\boxed{\Gamma=0.2871}` (28.7% of modal power in the core).

.. rubric:: Problem 8.2-6 — Maxwell derivation

For :math:`E_x=u(y)e^{-j\beta z}`,
:math:`H_y=-\beta E_x/(\omega\mu)` and
:math:`H_z=-j u'e^{-j\beta z}/(\omega\mu)` up to time-sign convention.
Continuity of :math:`E_x,H_z` gives continuity of :math:`u,u'`, producing
:math:`u\tan u=w` (even) or :math:`-u\cot u=w` (odd), with
:math:`u^2+w^2=V^2`—the ray phase/self-consistency equation.

.. rubric:: Problem 8.2-7 — Single-mode thickness

TE1 cutoff is :math:`V=\pi/2`, hence
:math:`\boxed{d_{max}=\lambda_0/[2\sqrt{n_1^2-n_2^2}]=1.889\ \mathrm{\mu m}}`.
At 0.85 micrometres the normalized frequency is 1.529 times larger and the
same slab carries :math:`\boxed{2}` TE modes.

.. rubric:: Problem 8.2-8 — Cutoff approximation

At cutoff the external decay is zero and :math:`k_yd=m\pi`; with
:math:`k_y^2=k_0^2(n_1^2-n_2^2)\simeq2k_0^2n_1\Delta n`, rearrangement gives
:math:`\boxed{\lambda_{0,c}^2\simeq8n_1\Delta n\,d^2/m^2}`.

.. rubric:: Problem 8.2-9 — TM modes

TM boundary continuity replaces the TE reflection phase by
:math:`\phi_{TM}=2\tan^{-1}[(n_1^2/n_2^2)
\sqrt{\sin^2\theta_c-\sin^2\theta}/\sin\theta]`.  Insert it in
:math:`2k_0n_1d\sin\theta-2\phi_{TM}=2\pi m`; plotting both sides for the
given parameters counts the intersections and supplies the TM bounce angles.

.. rubric:: Problem 8.3-1 — Rectangular-guide mode count

With area :math:`A=10^{-2}\ \mathrm{mm^2}` and NA 0.1, the high-frequency
count is :math:`\boxed{M_{TE}(\nu)\simeq A\pi(\mathrm{NA}\,\nu/c)^2/4}`
(adjust the factor for both polarizations).  Plotting this quadratic staircase
against frequency gives the 2-D analogue of the slab's linear count.

.. rubric:: Problem 8.4-1 — Two-slab coupler

Normalize the TE0 field from Problem 8.2-5 and evaluate the overlap in
Eq. (8.5-6); only the exponentially decaying tail of one guide overlaps the
other core, so :math:`\kappa` is exponentially sensitive to the 0.5-micrometre
edge gap.  After numerical quadrature, choose
:math:`\boxed{L_{3dB}=\pi/(4|\kappa|)}`; this is the reproducible result even
when field normalization is changed.
