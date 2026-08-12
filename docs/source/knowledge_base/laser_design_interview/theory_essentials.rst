Laser Theory Essentials
=======================

Be able to explain every relation on this page physically, derive its leading
dependence, and state where it stops being valid.

The laser in one sentence
-------------------------

A laser stores pump energy in a population inversion, converts it into coherent
light by stimulated emission, selects self-consistent spatial and longitudinal
modes with a resonator, and reaches steady state when saturated round-trip gain
equals round-trip loss.

Absorption, spontaneous emission, and stimulated emission
----------------------------------------------------------

For a transition between levels 1 and 2:

* **absorption** removes a resonant photon and raises an ion;
* **spontaneous emission** produces a photon with random emission time,
  direction, phase, and often polarization; and
* **stimulated emission** produces a photon in the stimulating optical mode,
  with the same frequency, phase, propagation direction, and polarization.

The small-signal gain coefficient is usefully written

.. math::
   :label: interview-small-signal-gain

   g_0(\nu)=\sigma_e(\nu)N_2-\sigma_a(\nu)N_1,

where :math:`\sigma_e` and :math:`\sigma_a` are emission and absorption cross
sections.  ``Population inversion`` means enough population is placed in the
upper laser level that :math:`g_0>0`; it does not merely mean that the upper
level is occupied.

Three- versus four-level media
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In a three-level laser the lower laser level is the ground state.  More than
half of the active ions must be transferred before net gain appears, so
threshold is high.  In a four-level laser the lower laser level empties rapidly;
even a modest upper-level population can produce inversion.  Ruby is the
standard three-level example, while Nd:YAG at 1064 nm is approximately
four-level.

Threshold: close the round-trip balance
---------------------------------------

Let :math:`R_1` and :math:`R_2` be mirror power reflectivities, :math:`L_g` the
gain length, :math:`g` the gain coefficient, and :math:`\mathcal L_i` the
remaining fractional round-trip power loss represented exponentially.  At
threshold,

.. math::
   :label: interview-threshold

   R_1R_2\exp(2g_{\rm th}L_g-\mathcal L_i)=1,

and therefore

.. math::

   g_{\rm th}=\frac{1}{2L_g}
   \left[\ln\!\left(\frac{1}{R_1R_2}\right)+\mathcal L_i\right].

The factor of two is the double pass through the gain medium in a linear
cavity.  If loss is instead defined per pass or per unit length, rewrite the
balance explicitly rather than carrying this formula unchanged.

Above threshold, gain saturation clamps the round-trip gain near the loss:

.. math::
   :label: interview-gain-saturation

   g(I)\simeq\frac{g_0}{1+I/I_{\rm sat}},
   \qquad
   I_{\rm sat}\simeq\frac{h\nu_l}{\sigma_e\tau_f}.

The precise saturation factor depends on level scheme, standing versus
travelling wave, and temporal regime.  The design insight is robust: increasing
intracavity intensity depletes inversion and reduces available gain.

Efficiency bookkeeping
----------------------

Separate efficiencies so a disappointing result can be diagnosed:

.. math::
   :label: interview-efficiency-chain

   \eta_{\rm wall}
   =\eta_{\rm driver}\eta_{\rm coupling}\eta_{\rm absorption}
    \eta_{\rm quantum}\eta_{\rm overlap}\eta_{\rm extraction}.

The ideal Stokes limit for one pump photon producing one laser photon is

.. math::

   \eta_{\rm Stokes}=\frac{h\nu_l}{h\nu_p}
   =\frac{\lambda_p}{\lambda_l}.

The quantum-defect fraction :math:`1-\lambda_p/\lambda_l` is an unavoidable
heat contribution even in an otherwise ideal system.  Nonradiative decay,
unabsorbed pump, fluorescence, parasitic oscillation, imperfect overlap, and
intracavity loss add further penalties.

Near and above threshold, many cw lasers are summarized by

.. math::
   :label: interview-slope-efficiency

   P_{\rm out}\simeq\eta_s(P_{\rm pump}-P_{\rm th}).

Do not report :math:`\eta_s` without specifying whether pump power is electrical,
incident optical, or absorbed optical power.

Longitudinal modes and linewidth
--------------------------------

For a linear cavity with round-trip optical length :math:`2L_{\rm opt}`,

.. math::
   :label: interview-fsr

   \Delta\nu_{\rm FSR}=\frac{c}{2L_{\rm opt}},
   \qquad
   L_{\rm opt}=\sum_j n_{g,j}L_j.

The group index belongs in a precise free-spectral-range calculation.  The
number of longitudinal modes is roughly gain bandwidth divided by FSR, but
actual oscillation also depends on spatial and spectral hole burning,
polarization, intracavity etalons, and mode competition.

A narrow gain curve does not by itself guarantee single-frequency operation.
Common controls are a short cavity, unidirectional ring geometry, intracavity
etalons, birefringent filters, injection seeding, and active frequency locking.

Continuous wave, Q-switching, and mode locking
----------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 18 26 27 29

   * - Regime
     - Stored quantity
     - Release mechanism
     - Dominant engineering issue
   * - Continuous wave
     - Nearly steady inversion and photon population
     - Gain balances loss continuously
     - Thermal lens, efficiency, noise, and mode stability
   * - Q-switched
     - Inversion accumulates while cavity loss is high
     - Cavity Q rises rapidly
     - Prelasing, switching speed, damage fluence, timing jitter
   * - Mode locked
     - Fixed phase relation among many longitudinal modes
     - Intracavity modulation or saturable absorption
     - Dispersion, nonlinearity, self-starting, pulse stability

Always connect pulse energy, duration, repetition rate, average power, and peak
power:

.. math::
   :label: interview-pulse-relations

   E_p=\frac{P_{\rm avg}}{f_{\rm rep}},
   \qquad
   P_{\rm peak}\simeq\frac{E_p}{\tau_p},
   \qquad
   F=\frac{E_p}{A_{\rm eff}},
   \qquad
   I_{\rm peak}\simeq\frac{P_{\rm peak}}{A_{\rm eff}}.

Use fluence for pulse-energy-driven damage and peak irradiance for nonlinear or
instantaneous effects.  The temporal and spatial beam shapes change the exact
peak factors.

Nonlinear conversion
--------------------

For second-harmonic generation, energy conservation fixes
:math:`\omega_{2}=2\omega_1` while efficient build-up requires phase matching,

.. math::
   :label: interview-phase-matching

   \Delta k=k_{2\omega}-2k_\omega=0.

At low depletion, converted power grows approximately as the square of
fundamental power and as :math:`\operatorname{sinc}^2(\Delta kL/2)`.  A real
design balances intensity, crystal length, walk-off, absorption, temperature or
angle acceptance, focusing, coating limits, and damage.  ``Focus as tightly as
possible`` is therefore not a good design rule.

Fast oral checks
----------------

* More output coupling raises threshold but can improve useful extraction.
* A shorter cavity increases longitudinal-mode spacing.
* A longer upper-state lifetime helps energy storage but can constrain fast
  modulation.
* Pump/laser wavelength separation creates heat through quantum defect.
* Increasing intracavity power improves nonlinear conversion but tightens
  coating, contamination, and damage margins.
