Chapter 15: Lasers
==================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 15.

In-text exercises
-----------------

.. rubric:: Exercise 15.1-1 — Ruby threshold

Thermal absorption gives :math:`\sigma_0=0.2/(1.58\times10^{19})=
\boxed{1.27\times10^{-20}\ \mathrm{cm^2}}`.  Mirror loss is
:math:`\alpha_r=-\ln(R_1R_2)/(2d)`; threshold inversion is
:math:`\boxed{N_t=\alpha_r/\sigma_0}` and threshold excited population follows
from :math:`N=N_2-N_1=2N_2-N_a` for this three-level transition.

.. rubric:: Exercise 15.2-1 — Gas-laser oscillation band

Set Gaussian gain equal to loss at both band edges:
:math:`\boxed{B=\Delta\nu_D
\sqrt{\ln(\gamma_0/\alpha_r)/\ln2}}`.  Divide by cavity FSR
:math:`c/(2nd)` and count the integer modes whose frequencies lie inside this
band; the given He--Ne parameters supply the requested count.

.. rubric:: Exercise 15.4-1 — Four-level population equation

Fast emptying makes :math:`N_1\simeq0`, so one stimulated transition changes
:math:`N=N_2-N_1\simeq N_2` by one atom, not two.  Thus
:math:`\dot N=(N_0-N)/t_{sp}-\sigma c nN`, without the two-level factor 2.

.. rubric:: Exercise 15.4-2 — Q-switched ruby pulse

For :math:`N_i/N_t=6`, read the normalized peak, duration, and extracted
population from Fig. 15.4-8; dimensionalize time by :math:`t_p`, photon
density by :math:`N_t`, power by :math:`h\nu V/t_p`, and energy by
:math:`h\nu V(N_i-N_f)/2`.  Recording the graph-read coordinates avoids false
precision from the scanned plot.

.. rubric:: Exercise 15.4-3 — Mode-locking computation

Evaluate :math:`A(t)=\sum_{q=-5}^{5}A_qe^{j2\pi q\nu_Ft}` on one period.
Equal phases give the squared Dirichlet kernel; Gaussian magnitudes give a
Gaussian-like pulse; random phases give irregular low-contrast fluctuations.
Normalize each case by :math:`\sum|A_q|^2` for a fair power comparison.

End-of-chapter problems
-----------------------

.. rubric:: Problem 15.2-2 — Argon longitudinal modes

:math:`\nu_F=c/(2d)=149.9` MHz.  Half-peak loss permits the Doppler FWHM
:math:`B=3.5` GHz, about :math:`\boxed{23}` longitudinal spacings.  Single
mode requires :math:`c/(2d)>B`, so :math:`d<4.28` cm for Ar+ and
:math:`d<2.50` m for the 60-MHz CO2 line.

.. rubric:: Problem 15.2-3 — Length range for one/two modes

Compute :math:`\alpha_r=-\ln(0.97)/(2d)`, then
:math:`B(d)=\Delta\nu_D\sqrt{\ln(\gamma_0/\alpha_r)/\ln2}`.  The required
lengths satisfy :math:`1\leq B/[c/(2d)]<3`; solve the two equality boundaries
numerically and exclude lengths for which :math:`\gamma_0\leq\alpha_r`.

.. rubric:: Problem 15.2-4 — Etalon selector

Choose etalon FSR :math:`c/(2d_e)>1.5` GHz (for example :math:`d_e<10` cm)
and linewidth :math:`\nu_{F,e}/\mathcal F` narrower than the laser's
300-MHz longitudinal spacing; :math:`d_e=5` cm and :math:`\mathcal F>10` is a
workable pair.  Intracavity placement suppresses unwanted modes before gain
saturation and is therefore superior.

.. rubric:: Problem 15.2-5 — Multimode He--Ne power

At gain/loss ratio two, the permitted Gaussian band is one FWHM; FSR is
:math:`c/(0.6)=499.7` MHz, giving roughly three modes.  Centering one mode
makes its saturated gain competition strongest; a first equal-sharing
estimate is :math:`\boxed{50/3\simeq16.7\ \mathrm{mW}}`, refined by weighting
each mode with its Gaussian excess gain.

.. rubric:: Problem 15.2-6 — Single-mode output

:math:`\alpha_{m1}=-\ln0.99/(2d)`, :math:`\alpha_{m2}=0`, and
:math:`\alpha_r=\alpha_{m1}`.  Then :math:`t_p=n/(c\alpha_r)` and intracavity
steady flux is :math:`\phi_s(\gamma_0/\alpha_r-1)`; multiply by output
transmission, photon energy, and :math:`1\ \mathrm{mm^2}` area for
:math:`P_o`.

.. rubric:: Problem 15.2-7 — Reading a passive cavity trace

Read peak spacing :math:`\nu_F` and FWHM :math:`\delta\nu` from the supplied
plot.  Then :math:`d=c/(2\nu_F)`,
:math:`t_p=1/(2\pi\delta\nu)`, and
:math:`\gamma_t=1/(ct_p)`.  Subthreshold pumping narrows and raises peaks
symmetrically around :math:`5\times10^{14}` Hz but cannot make their width
zero.

.. rubric:: Problem 15.2-8 — Four-level rate equations

Write level equations with pump relaxation and stimulated term
:math:`\sigma cn(N_2-N_1)`; subtraction gives
:math:`\dot N=(N_0-N)/T_s-\sigma cnN` and
:math:`\dot n=\sigma cnN-n/t_p+N_2/t_{sp}`.  Above threshold,
:math:`N\simeq N_t=1/(\sigma ct_p)` and the excess pump fixes steady :math:`n`.

.. rubric:: Problem 15.3-1 — Yb:YAG design

Convert the pump energy by :math:`\lambda=hc/E` and its endpoint energies to
obtain band width in nanometres.  Thermal populations give
:math:`\alpha=-\sigma_0N`; the 6-cm cavity has
:math:`\alpha_r=-\ln0.8/(12\ \mathrm{cm})`,
:math:`t_p=n/(c\alpha_r)`, and :math:`N_t=\alpha_r/\sigma_0`.  A small pump-
laser energy defect improves quantum efficiency; YVO4 changes host index,
cross section, lifetime, thermal conductivity, and hence threshold/output.

.. rubric:: Problem 15.3-2 — Ar+ threshold

:math:`t_p=[c(-\ln0.98/2d)]^{-1}`.  Convert 0.003-nm linewidth to frequency,
use lifetime/lineshape to find :math:`\sigma_0`, then
:math:`\boxed{N_t=1/(\sigma_0ct_p)}`; the mode diameter affects total excited
ion number, not density threshold.

.. rubric:: Problem 15.3-3 — EUV spontaneous lifetime

For equal line strength, Einstein :math:`A\propto\nu^3`, so
:math:`t_{sp}\propto\lambda^3`.  Thus
:math:`\boxed{t_{EUV}=10\ \mathrm{ns}(18.2/500)^3=0.482\ \mathrm{ps}}`, of the
same scale as the tabulated value.

.. rubric:: Problem 15.4-4 — Gain-switch transients

The stated substitutions directly produce
:math:`X'=-X+XY`, :math:`Y'=a(Y_0-Y)-2XY`.  Integrate with an adaptive ODE
solver for the three :math:`a` values and define switching time by 10--90%
photon density.  The :math:`10^{-5}` seed represents spontaneous emission;
small :math:`a` gives relaxation spiking, large :math:`a` follows pump rapidly.

.. rubric:: Problem 15.4-5 — Q-switched ruby energetics

Maintenance pump is :math:`N_2V(hc/450\mathrm{nm})/t_{sp}`; spontaneous power
is :math:`N_2V(hc/694.3\mathrm{nm})/t_{sp}`.  Compute
:math:`N_t=-\ln(R_1R_2)/(2d_r\sigma)` and use Q-switch invariants to solve
:math:`N_f-N_t\ln N_f=N_i-N_t\ln N_i`; extracted pulse energy is
:math:`h\nu V(N_i-N_f)/2`, with peak/duration from the normalized rate
solution.

.. rubric:: Problem 15.4-6 — Cavity dumping timeline

During high-Q storage, threshold is low, :math:`N` clamps, internal photons
rise, and external output is small.  Opening the dump raises threshold
abruptly, empties internal photons as one large external pulse, and lets
:math:`N` recover under pumping; repeat this four-trace sequence for cycle two.

.. rubric:: Problem 15.4-7 — Lorentzian mode locking

The Fourier series of Lorentzian modal amplitudes is a periodic exponential
pulse.  Parseval gives mean power :math:`\sum|A_q|^2`; coherent summation gives
peak :math:`|\sum A_q|^2`; solving the exponential intensity at half maximum
gives FWHM proportional to :math:`1/\Delta\nu`.  Evaluating the standard
Lorentzian sums supplies the book's closed constants.

.. rubric:: Problem 15.4-8 — Intracavity second harmonic

Two fundamental photons make one harmonic:
:math:`\dot n=\epsilon n-n/t_p-2\zeta n^2` and
:math:`\dot n_2=\zeta n^2-n_2/t_{p2}`.  The nonzero steady solution is
:math:`\boxed{n=(\epsilon-1/t_p)/(2\zeta)}` and
:math:`\boxed{n_2=\zeta t_{p2}n^2}` above threshold.
