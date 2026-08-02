Chapter 21: Nonlinear Optics
============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 21.

In-text exercises
-----------------

.. rubric:: Exercise 21.1-1 — Intensity needed for nonlinearity

Since :math:`P_L=\epsilon_0(n^2-1)E`, :math:`P_2=2dE^2`,
:math:`P_3=4\chi^{(3)}E^3`, and :math:`I=E^2/(\eta_0/n)`, setting the requested
ratios to 0.01 gives

.. math::

   \boxed{I_{\rm ADP}=2.64\times10^{13}\ \mathrm{W/cm^2}},\qquad
   \boxed{I_{\rm CS_2}=3.33\times10^{11}\ \mathrm{W/cm^2}}.

The enormous values explain why focused laser fields are normally required.

.. rubric:: Exercise 21.2-1 — Non-collinear type-II SHG

With :math:`n_e(\vartheta)^{-2}=\cos^2\vartheta/n_e^2+
\sin^2\vartheta/n_o^2`, solve

.. math::

   n_o(\omega)\sin\theta_1=n_e(\theta+\theta_2,\omega)\sin\theta_2,
   \quad
   n_o(\omega)\cos\theta_1+n_e(\theta+\theta_2,\omega)\cos\theta_2
   =2n_e(\theta,2\omega).

Sellmeier values for KDP at 1.06 and 0.53 micrometres inserted in these two
equations give the complete one-parameter family; a root finder over
:math:`(\theta,\theta_1,\theta_2)` reproduces it.  The collinear endpoint is
:math:`\boxed{\theta\simeq41^\circ,\ \theta_1=\theta_2=0}`, and continuation
from that root gives the non-collinear branches.

.. rubric:: Exercise 21.3-1 — DC-field-induced Kerr effect

Expanding :math:`4\chi^{(3)}[E(0)+E(\omega)]^3`, the terms at :math:`\omega`
are :math:`12\chi^{(3)}E^2(0)E(\omega)`.  Equating this to
:math:`2n\epsilon_0\Delta nE(\omega)` gives
:math:`\Delta n=6\chi^{(3)}E^2(0)/(n\epsilon_0)=-s n^3E^2(0)/2`, hence
:math:`\boxed{s=-12\chi^{(3)}/(\epsilon_0n^4)}`.

.. rubric:: Exercise 21.3-2 — Optical Kerr lens

Near the beam axis,
:math:`n(I)d\simeq\mathrm{constant}-n_2I_0d(x^2+y^2)/W^2`.  Matching its
phase to :math:`\exp[jk_0(x^2+y^2)/(2f)]` gives
:math:`\boxed{f=W^2/(2n_2I_0d)}`; the sign follows the sign convention for
propagation and :math:`n_2`.

.. rubric:: Exercise 21.3-3 — Self- and cross-phase modulation

Collecting all cubic products at :math:`\omega_1` gives a self term
:math:`|E_1|^2E_1` and two permutations for each other wave.  Converting field
strength to intensity yields
:math:`\boxed{\Delta n_1=n_2(I_1+2I_2+2I_3)}`.  Therefore wave 1 propagates
at :math:`c_0/(n+\Delta n_1)`.

.. rubric:: Exercise 21.4-1 — Degenerate three-wave mixing

Put :math:`E=E_1e^{j\omega t}+E_3e^{j2\omega t}+\mathrm{c.c.}` in
:math:`P_{NL}=2dE^2`.  Terms at :math:`\omega` occur twice, whereas the
:math:`2\omega` product :math:`E_1E_1` occurs once.  Applying
:math:`S=\mu_0\partial_t^2P_{NL}` gives
:math:`\boxed{S_1=2\mu_0\omega^2dE_3E_1^*,\ S_3=4\mu_0\omega^2dE_1^2}`,
equivalent to Eqs. (21.4-14)--(21.4-16).

.. rubric:: Exercise 21.4-2 — Manley--Rowe relation

Multiply each coupled equation by its conjugate amplitude and add the complex
conjugate.  The common interaction term then gives
:math:`\boxed{d|a_1|^2/dz=d|a_2|^2/dz=-d|a_3|^2/dz}`.  These are photon-flux
changes: one photon from each lower-frequency wave makes one sum-frequency
photon.

.. rubric:: Exercise 21.4-3 — Energy conservation

Weight the preceding derivatives by :math:`\hbar\omega_q`.  Because
:math:`\omega_1+\omega_2=\omega_3`, their sum vanishes:
:math:`\boxed{d[\hbar\sum_q\omega_q|a_q|^2]/dz=0}`.

.. rubric:: Exercise 21.4-4 — SHG envelope equations

Substitute :math:`E_q=a_q(z)e^{-jk_qz}` in the two Helmholtz equations and
use :math:`|a_q''|\ll|k_qa_q'|`.  Division by :math:`-2jk_q` gives
:math:`da_1/dz=-j2g a_1^*a_3e^{j\Delta kz}` and
:math:`da_3/dz=-jg a_1^2e^{-j\Delta kz}`, with the chapter normalization of
:math:`g`; the factor two occurs only in the fundamental equation.

.. rubric:: Exercise 21.4-5 — Infrared up-conversion

Frequency addition gives
:math:`\lambda_3^{-1}=\lambda_1^{-1}+\lambda_2^{-1}`, hence
:math:`\boxed{\lambda_3=0.9636\ \mu\mathrm m}`.  With the undepleted-pump
formula and the given :math:`d^2/n^3`, area, power, and 1-cm length,
:math:`\boxed{\eta_{\rm OFC}=5.31\times10^{-3}}` (0.531%).

.. rubric:: Exercise 21.4-6 — KTP parametric amplifier

Difference-frequency conservation gives :math:`\boxed{\lambda_i=1.852\
\mu\mathrm m}`.  From Eq. (21.4-47),
:math:`C=[2\omega_s\omega_i(\eta_0/n)^3d^2]^{1/2}=
\boxed{8.99\times10^{-5}}` in its stated SI normalization.  A 3-dB power gain
requires :math:`\cosh^2(C L\sqrt{P/A})=2`, so
:math:`\boxed{P/A=2.40\times10^{11}\ \mathrm{W/m^2}}`; for example, a
1-W pump focused to :math:`4.16\times10^{-12}\ \mathrm{m^2}` satisfies it.

.. rubric:: Exercise 21.5-1 — Undepleted-pump THG

Retaining the cubic source terms at :math:`\omega` and :math:`3\omega`, then
applying SVEA, gives
:math:`da_3/dz=-jg a_1^3e^{-j\Delta kz}` when :math:`a_1` is undepleted, with
:math:`\boxed{g=3\chi^{(3)}\omega_3(\eta_1^3\eta_3)^{1/2}/2}` under the
chapter's flux-amplitude normalization.  Integration adds the familiar
:math:`L\,\mathrm{sinc}(\Delta kL/2)` phase-matching factor.

.. rubric:: Exercise 21.7-1 — Anharmonic oscillator polarization

Start with :math:`m\ddot x+m\gamma\dot x+Kx+K_2x^2=-eE` and set
:math:`P=-Nex`.  Multiplication by :math:`-Ne/m` gives Eq. (21.7-8), with
:math:`\boxed{\omega_0^2=K/m,\ \chi_0=Ne^2/(\epsilon_0m\omega_0^2),\
b=K_2/(e^3N^2)}`.

.. rubric:: Exercise 21.7-2 — Miller's rule

The first iteration supplies :math:`P_1(\omega)=\epsilon_0\chi(\omega)E(\omega)`.
Driving the linear oscillator at :math:`\omega_3=\omega_1+\omega_2` with
:math:`-bP_1^2` supplies one susceptibility at each of the three frequencies:
:math:`\boxed{d(\omega_3;\omega_1,\omega_2)=C_M
\chi(\omega_3)\chi(\omega_1)\chi(\omega_2)}`, where the material constant
:math:`C_M` follows from :math:`b,\chi_0`, proving Miller's rule.

End-of-chapter problems
-----------------------

.. rubric:: Problem 21.2-2 — Up-conversion power exchange

:math:`1/\lambda_p=1/0.5-1/1.3` gives
:math:`\boxed{\lambda_p=0.8125\ \mu\mathrm m}`.  One lost 1.3-micrometre photon
creates one 0.5-micrometre photon while consuming one pump photon.  Thus a
1-mW signal loss gives :math:`\boxed{2.60\ \mathrm{mW}}` at 0.5 micrometres
and :math:`\boxed{1.60\ \mathrm{mW}}` pump loss.

.. rubric:: Problem 21.2-3 — Collinear type-II KDP matching

For each trial :math:`\theta`, evaluate the extraordinary index and solve
:math:`n_o(\omega)+n_e(\theta,\omega)=2n_o(2\omega)` for o-e-o, or replace
the right side by :math:`2n_e(\theta,2\omega)` for o-e-e.  Bracketing
:math:`0<\theta<90^\circ` with the Table 5.5-1 Sellmeier equations gives the
requested cut angles; substitution back into the equation is the residual
check (a configuration with no sign change has no physical cut angle).

.. rubric:: Problem 21.2-4 — Degenerate KDP down-conversion

Try the allowed type-I condition :math:`n_e(\theta,0.6)=n_o(1.2)`.  The given
indexes bracket 1.490, and
:math:`n_e(\theta)^{-2}=\cos^2\theta/1.468^2+sin^2\theta/1.509^2` gives
:math:`\boxed{\theta=47.2^\circ}`.  The 0.6-micrometre pump is extraordinary;
both collinear 1.2-micrometre daughter waves are ordinary.

.. rubric:: Problem 21.2-5 — Linear-dispersion matching obstruction

With :math:`n(\lambda)=n_0-\beta\lambda` and
:math:`1/\lambda_3=1/\lambda_1+1/\lambda_2`, the :math:`n_0` terms satisfy
energy conservation but the three :math:`-\beta` contributions leave a
nonzero constant in :math:`k_1+k_2-k_3`; co-propagating exact matching is
impossible for :math:`\beta\ne0`.  Reversing one wave changes a wavevector
sign and can supply a root, so counter-propagating matching is possible.

.. rubric:: Problem 21.2-6 — Finite-volume phase mismatch

In the radiation integral use
:math:`|\mathbf r-\mathbf r'|\simeq r-\hat{\mathbf r}\cdot\mathbf r'`.
For a uniform rectangular source the remaining integral factorizes into
:math:`V\prod_i\mathrm{sinc}(\Delta k_iL_i/2)`.  Thus intensity contains
:math:`\prod_i\mathrm{sinc}^2(\Delta k_iL_i/2)` and the longitudinal first
zero is :math:`|\Delta k_z|=2\pi/L_z`, quantifying phase-mismatch tolerance.

.. rubric:: Problem 21.2-7 — Backward quasi-phase-matched SHG

Momentum conservation including grating vector :math:`K=2\pi/\Lambda` is
:math:`-k_{2\omega}=2k_\omega-mK`, so
:math:`\boxed{mK=2k_\omega+k_{2\omega}}`.  If dispersion is neglected,
:math:`k_{2\omega}=2k_\omega`; for :math:`m=7`,
:math:`\boxed{\Lambda/\lambda_\omega=7/4}` where :math:`\lambda_\omega` is
the fundamental wavelength in the crystal.

.. rubric:: Problem 21.3-4 — Four-wave Manley--Rowe invariants

One elementary event destroys photons 1 and 2 and creates photons 3 and 4:
:math:`d\Phi_1=d\Phi_2=-d\Phi_3=-d\Phi_4`.  Therefore
:math:`\Phi_1-\Phi_2`, :math:`\Phi_3-\Phi_4`, and
:math:`\Phi_1+\Phi_3` are invariant; multiplying by photon energies and using
:math:`\omega_1+\omega_2=\omega_3+\omega_4` proves energy conservation.

.. rubric:: Problem 21.3-5 — Spatial-soliton power

For :math:`I(x)=I_0\,\mathrm{sech}^2(x/W_0)`, integration gives
:math:`P'=\int I\,dx=2I_0W_0`.  The soliton condition has
:math:`I_0\propto W_0^{-2}`, so
:math:`\boxed{P'\propto W_0^{-1}}` (power per unit extent in the invariant
transverse direction).

.. rubric:: Problem 21.3-6 — Light-controlled phase modulator

:math:`n_2=3\eta_0\chi^{(3)}/(\epsilon_0n^2)=2.19\times10^{-18}`
:math:`\mathrm{m^2/W}`.  Setting :math:`k_0n_2IL=\pi` gives
:math:`I_\pi=1.24\times10^{12}\ \mathrm{W/m^2}` and, for a square
:math:`0.1`-mm beam, :math:`\boxed{P_\pi\simeq12.4\ \mathrm{kW}}` (multiply
by :math:`\pi/4` instead for a circular diameter convention).

.. rubric:: Problem 21.3-7 — DC-assisted SHG

The cubic product :math:`4\chi^{(3)}[E_0+E_\omega]^3` contains a
:math:`2\omega` term proportional to :math:`E_0E_\omega^2`.  It acts like an
effective quadratic coefficient :math:`d_{\rm eff}\propto\chi^{(3)}E_0`;
conversion therefore scales as :math:`|\chi^{(3)}|^2E_0^2I_\omega L^2`
times the phase-matching sinc-squared factor.

.. rubric:: Problem 21.4-7 — KDP amplifier gain

The idler wavelength is :math:`0.8570` micrometres.  Equation (21.4-47) gives
:math:`C=1.295\times10^{-4}` and
:math:`\gamma=2C\sqrt I=25.90\ \mathrm{m^{-1}}` at
:math:`10^6\ \mathrm{W/cm^2}`.  Thus
:math:`\boxed{G=\cosh^2(\gamma L/2)=1.293=1.12\ \mathrm{dB}}`.

.. rubric:: Problem 21.4-8 — Degenerate down-converter

Degeneracy combines the two signal equations into
:math:`da/dz=-j2ga^*a_pe^{j\Delta kz}` and
:math:`da_p/dz=-jga^2e^{-j\Delta kz}`.  At exact match choose phases so the
amplitudes are real; the invariants give
:math:`\Phi(z)+2\Phi_p(z)=2\Phi_p(0)` and the solution is the standard
:math:`\mathrm{sech}^2/\tanh^2` exchange.  Consequently
:math:`\Phi_p=\Phi_p(0)\mathrm{sech}^2(\kappa z)` and
:math:`\Phi=2\Phi_p(0)\tanh^2(\kappa z)`, proving both energy and photon
conservation and giving :math:`\eta=\tanh^2(\kappa L)`.

.. rubric:: Problem 21.4-9 — OPO threshold

At degeneracy :math:`\lambda_s=\lambda_i=1.064` micrometres.  Requiring the
round-trip power gain to cancel two 0.98 reflectances gives
:math:`\cosh^2(C L\sqrt I)R^2=1`.  With
:math:`C=2.244\times10^{-4}`, the result is
:math:`\boxed{I_{th}=3.23\times10^4\ \mathrm{W/cm^2}}`.

.. rubric:: Problem 21.5-1 — Simultaneous SHG and SFG

For envelopes :math:`A_1,A_2,B_1,B_2,C` at
:math:`\omega_1,\omega_2,2\omega_1,2\omega_2,\omega_1+\omega_2`, write one
SVE equation for every resonant quadratic product:
:math:`A_1^2\leftrightarrow B_1`, :math:`A_2^2\leftrightarrow B_2`, and
:math:`A_1A_2\leftrightarrow C`, plus conjugate back-action terms.  A
Runge--Kutta integration preserving
:math:`\sum\hbar\omega_q|A_q|^2` shows suppression of SHG1 as the SFG channel
draws photons from :math:`A_1`; energy-invariant error is the numerical check.

.. rubric:: Problem 21.5-2 — Degenerate four-wave equations

Keeping resonant cubic products and exact phase matching gives
:math:`dA_1/dz=-j\kappa A_2^*A_3^2`,
:math:`dA_2/dz=-j\kappa A_1^*A_3^2`, and
:math:`dA_3/dz=-j2\kappa^*A_1A_2A_3^*`, together with self/cross-phase terms
if they are not absorbed into propagation constants.  The factor two in the
pump equation accounts for its two degenerate photons.

.. rubric:: Problem 21.6-1 — Type-II coefficient in 3m BBO

Insert the ordinary and extraordinary unit polarization vectors in
:math:`d_{\rm eff}=\hat e_3\boldsymbol d:(\hat e_1\hat e_2)`.  Applying the
3m tensor symmetries cancels the sine terms and leaves
:math:`\boxed{d_{\rm eff}=d_{22}\cos^2\theta\cos3\phi}`.

.. rubric:: Problem 21.6-2 — Electro-optic/nonlinear tensors

For :math:`\boldsymbol\eta=\boldsymbol\epsilon^{-1}\epsilon_0`, variation of
an inverse matrix gives
:math:`\delta\eta=-\epsilon_0\epsilon^{-1}(\delta\epsilon)\epsilon^{-1}`.
Substitute the quadratic and cubic field-dependent polarization terms and
differentiate once or twice with respect to the DC field.  Component matching
gives
:math:`\boxed{r_{ijk}=-4\epsilon_0d_{ijk}/(\epsilon_{ii}\epsilon_{jj})}` and
:math:`\boxed{s_{ijkl}=-12\epsilon_0\chi^{(3)}_{ijkl}/
(\epsilon_{ii}\epsilon_{jj})}`.
