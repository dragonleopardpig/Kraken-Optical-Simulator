Chapter 14: Laser Amplifiers
============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 14.

In-text exercises
-----------------

.. rubric:: Exercise 14.1-1 — Ruby absorption and inversion

Use Boltzmann :math:`N_2/N_1=e^{-hc/(\lambda kT)}` with
:math:`N_1+N_2=N_a`; at 300 K the upper population is negligible, so
:math:`N\simeq-N_a`.  Line-centre coefficient is
:math:`\gamma_0=N\sigma_0`; the inversion required for 0.5/cm gain is
:math:`\boxed{N=0.5/\sigma_0}`, with :math:`\sigma_0` obtained from the
Lorentzian lifetime formula in Sec. 13.3.

.. rubric:: Exercise 14.2-1 — Optical pumping

Steady state gives :math:`N_2=R_2t_{sp}` and pump depletion
:math:`R_2=(N_a-2N_2)W`.  Solving yields
:math:`\boxed{N_2=N_at_{sp}W/(1+2t_{sp}W)}`; it approaches only :math:`N_a/2`.

.. rubric:: Exercise 14.2-2 — Saturation time

Insert the lifetime inequalities in the general expression for :math:`T_s`;
all fast nonradiative/level-1 terms drop out, leaving
:math:`\boxed{T_s\simeq t_{sp}}`.

.. rubric:: Exercise 14.2-3 — Three/four-level pump power

Set the steady population-difference formulas to zero: the three-level system
has a finite transparency threshold, while an ideal four-level system reaches
zero difference at zero pump.  Substitution of :math:`W=2/t_{sp}` and
:math:`1/(2t_{sp})` gives :math:`N=N_a/3` in both; the three-level system
requires four times the transition rate and correspondingly greater pump.

.. rubric:: Exercise 14.4-1 — Ruby saturation

Evaluate :math:`\boxed{\phi_s(\nu_0)=1/[\sigma(\nu_0)T_s]}` using
:math:`T_s=2t_{sp}` and Table 14.3-1; the corresponding intensity is
:math:`\boxed{I_s=h\nu_0\phi_s}`.

.. rubric:: Exercise 14.4-2 — Saturation broadening

Insert Lorentzian :math:`g(\nu)` in
:math:`\gamma=\gamma_0/[1+\phi/\phi_s(\nu)]`.  Half maximum occurs at a
detuning enlarged by :math:`\sqrt{1+\phi/\phi_s(\nu_0)}`, so
:math:`\boxed{\Delta\nu_{sat}=\Delta\nu
\sqrt{1+\phi/\phi_s(\nu_0)}}`.

.. rubric:: Exercise 14.5-1 — Amplified spontaneous emission

Solve :math:`d\phi/dz=\gamma_0\phi+r_{sp}` with zero input:
:math:`\boxed{\phi(d)=\phi_{sp}(e^{\gamma_0d}-1)}`.  For large gain a
Lorentzian exponent narrows near line centre by approximately
:math:`1/\sqrt{\gamma_0d}`.

End-of-chapter problems
-----------------------

.. rubric:: Problem 14.1-2 — Longer ruby rod

:math:`G=e^{\gamma d}`; therefore
:math:`\boxed{G_{20}=12^{20/15}=27.47}`.

.. rubric:: Problem 14.1-3 — Nd:glass inversion

:math:`\gamma_0=\ln10/(15\ \mathrm{cm})=0.1535\ \mathrm{cm^{-1}}`; use the
Table 14.3-1 peak cross section to obtain
:math:`\boxed{N=0.1535/\sigma_0\ \mathrm{cm^{-3}}}`.

.. rubric:: Problem 14.1-4 — Broadband signal

Average :math:`\gamma(\nu)-\alpha_s` over the uniform two-linewidth band:
:math:`\bar\gamma=(2\Delta\nu)^{-1}
\int_{\nu_0-\Delta\nu}^{\nu_0+\Delta\nu}
[0.1/(1+4\delta\nu^2/\Delta\nu^2)-0.05]d\nu`.
This yields the net logarithmic one-centimetre gain; exponentiation gives the
power ratio.

.. rubric:: Problem 14.2-4 — Why two-level pumping fails

The pump drives upward and stimulated downward transitions at the same rate:
:math:`\dot N_2=W(N_1-N_2)-N_2/t_{sp}`.  Steady state gives
:math:`N_2/N_1=Wt_{sp}/(1+Wt_{sp})<1`; inversion is impossible.

.. rubric:: Problem 14.2-5 — Two simultaneous laser lines

Write :math:`\dot N_3=R_3-N_3/T_{31}`,
:math:`\dot N_2=R_2-N_2/T_{21}`, and
:math:`\dot N_1=N_3/T_{31}+N_2/T_{21}-N_1/T_1` plus stimulated terms.
Their zero derivatives give :math:`N_3=R_3T_{31}`, :math:`N_2=R_2T_{21}` and
:math:`N_1=T_1(R_2+R_3)` before lasing.  Stimulated 2-to-1 emission raises
:math:`N_1`, thereby reducing :math:`N_3-N_1` and competing with the other
line.

.. rubric:: Problem 14.4-3 — Meaning of saturation flux

Stimulated decay adds :math:`\sigma\phi` to :math:`1/T_2`; half lifetime
requires :math:`\sigma\phi=1/T_2`.  Thus :math:`\phi=1/(\sigma T_2)`, equal
to the saturation flux when the lower-level relaxation terms make
:math:`T_s=T_2` (otherwise scaled by :math:`T_s/T_2`).

.. rubric:: Problem 14.4-4 — Ruby and Nd:YAG saturation

For each Table 14.3-1 row evaluate
:math:`\boxed{\phi_s=1/(\sigma_0T_s)}` and
:math:`\boxed{I_s=(hc/\lambda_0)\phi_s}`.  Keep square-centimetre units for
the tabulated cross sections before converting intensity.

.. rubric:: Problem 14.4-5 — Saturated growth plot

Integrating :math:`d\phi/dz=\gamma_0\phi/(1+\phi/\phi_s)` gives
:math:`\boxed{\ln(\phi/\phi_0)+(\phi-\phi_0)/\phi_s=\gamma_0z}`.  Plot this
implicit relation for :math:`\phi_0/\phi_s=0.05`; saturation begins near
:math:`\phi/\phi_s=1`.

.. rubric:: Problem 14.4-6 — Hot two-level absorber

For each temperature use :math:`N_2/N_1=e^{-2.48/kT}` and
:math:`N_1+N_2=10^{23}`.  Then spontaneous rate is :math:`N_2/t_{sp}`,
:math:`\alpha_0=(N_1-N_2)\sigma_0`, Lorentzian frequency dependence, and
:math:`\phi_s=1/(\sigma_0T_s)`.  Transmitted flux follows the implicit
saturable-absorber equation obtained from Problem 14.4-5 with negative gain;
at one linewidth detuning insert the Lorentzian quarter-peak cross section.

.. rubric:: Problem 14.4-7 — Measured saturated amplifier

Insert the stated input/output in
:math:`\ln(\phi_d/\phi_0)+(\phi_d-\phi_0)/\phi_s=\gamma_0d` to obtain
:math:`G_0=e^{\gamma_0d}` and :math:`\gamma_0`.  A fivefold coefficient drop
requires :math:`1+\phi/\phi_s=5`, so :math:`\phi=4\phi_s`.  At the final high
input, :math:`\gamma=\gamma_0/(1+10)` and total gain is below small-signal
gain.

.. rubric:: Problem 14.5-2 — Signal-to-ASE ratio

:math:`\phi_s(d)=\phi_s(0)e^x` and
:math:`\phi_{ASE}=\phi_{sp}(e^x-1)`, :math:`x=\gamma_0d`; hence
:math:`\boxed{\phi_s(d)/\phi_{ASE}=[\phi_s(0)/\phi_{sp}]/(1-e^{-x})}`.  It
falls from infinity and asymptotes to the input/spontaneous ratio.

.. rubric:: Problem 14.5-3 — Amplified coherent-light statistics

Moments of the noncentral chi-square density give
:math:`\bar w=w_s+w_{ASE}` and
:math:`\operatorname{var}w=w_{ASE}^2+2w_sw_{ASE}`.  Mandel's identities then
give :math:`\bar n=\bar w/(h\nu)` and
:math:`\operatorname{var}n=\bar n+operatorname{var}w/(h\nu)^2`.
