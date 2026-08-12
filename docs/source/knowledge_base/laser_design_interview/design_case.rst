Worked Interview Design Case
============================

This is a whiteboard-level first pass, not a production prescription.  Its
purpose is to demonstrate traceable reasoning, estimates, and the tests needed
to retire uncertainty.

Prompt
------

Outline a compact diode-pumped Nd:YAG laser delivering at least 5 W continuous
wave at 1064 nm with :math:`M^2\le1.2` and stable linear polarization.  Explain
the resonator, pump, thermal, coating, measurement, and tolerance decisions.

1. Restate requirements and assumptions
---------------------------------------

State unknowns rather than hiding them.  For a first calculation assume:

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Item
     - First-pass value
     - Must later come from
   * - Pump wavelength and incident power
     - 808 nm, 20 W
     - Qualified diode spectrum over current, temperature, and life
   * - Pump transport efficiency
     - 0.90
     - Coating, fiber, lens, and alignment budget
   * - Absorbed fraction in crystal
     - 0.90
     - Doping, length, spectrum, temperature, and double-pass design
   * - Gain length
     - 10 mm
     - Selected crystal and absorption/thermal model
   * - Cavity length
     - 100 mm optical first pass
     - Package, mode size, FSR, and tolerance trade
   * - Mirrors
     - Plane high reflector and :math:`R=200\,\mathrm{mm}` output coupler
     - Coating availability and thermal-lens sweep
   * - Output-coupler transmission
     - 5%
     - Saturated-gain/output-coupling optimization
   * - Other round-trip power loss
     - 2% represented exponentially
     - Loss measurement and coating/scatter budget

2. Pump and efficiency estimate
-------------------------------

From :eq:`interview-pump-absorption`,

.. math::

   P_{\rm abs}=(0.90)(20\,\mathrm W)(0.90)=16.2\,\mathrm W.

The ideal Stokes efficiency is

.. math::

   \eta_{\rm Stokes}=\frac{808}{1064}=0.759,

so at least :math:`24.1\%` of absorbed pump becomes quantum-defect heat before
other losses.  If a provisional absorbed-power threshold is 3 W and absorbed
slope efficiency is 45%,

.. math::

   P_{\rm out}\simeq0.45(16.2-3.0)=5.94\,\mathrm W.

That passes the paper requirement but has little system margin.  The next model
must split transport, absorption, overlap, internal loss, output coupling, and
thermal roll-over rather than tune the single 45% number.

If the practical heat fraction is provisionally 35%,

.. math::

   P_{\rm heat}\simeq0.35(16.2)=5.67\,\mathrm W.

This number drives the first thermal and mount model.

3. Cold-cavity eigenmode
------------------------

For the plane-concave cavity,

.. math::

   g_1=1,\qquad
   g_2=1-\frac{100}{200}=0.5,\qquad
   g_1g_2=0.5.

The cold cavity is comfortably inside the ideal stability interval.  With the
waist at the plane mirror,

.. math::

   z_R=\sqrt{L(R-L)}=100\,\mathrm{mm},

.. math::

   w_0=\sqrt{\frac{\lambda z_R}{\pi}}
   \simeq184\,\mu\mathrm m,

and at the curved mirror

.. math::

   w(L)=w_0\sqrt{1+(L/z_R)^2}\simeq260\,\mu\mathrm m.

These numbers are not final because the crystal's refractive surfaces and
pump-dependent thermal lens belong in the round-trip matrix.  They do establish
the approximate pump-waist scale and optic clear-aperture requirement.

4. Threshold and circulating-power checks
------------------------------------------

Using :eq:`interview-threshold` with :math:`R_1=0.999`, :math:`R_2=0.95`,
:math:`L_g=0.010\,\mathrm m`, and :math:`\mathcal L_i=0.02`,

.. math::

   g_{\rm th}\simeq
   \frac{\ln[1/(0.999\times0.95)]+0.02}{0.020}
   \simeq3.6\,\mathrm{m^{-1}}.

The spectroscopy and inversion model must demonstrate this gain over the
actual pumped volume.

A 5-W output through :math:`T=0.05` implies roughly

.. math::

   P_{\rm circ}\simeq\frac{P_{\rm out}}{T}=100\,\mathrm W

incident on the output coupler in this simplified travelling-wave power
accounting.  For a Gaussian radius of 260 µm, its on-axis irradiance is

.. math::

   I_{\rm pk}=\frac{2P_{\rm circ}}{\pi w^2}
   \simeq9.4\times10^8\,\mathrm{W/m^2}
   =94\,\mathrm{kW/cm^2}.

Repeat this calculation at every optic and include standing-wave, defect, and
transient enhancement before selecting coatings.

5. Pump overlap and thermal sweep
---------------------------------

Start with an approximately 220-µm pump radius near the gain region so the pump
slightly exceeds the cold TEM00 radius.  Then calculate the full longitudinal
absorbed-pump distribution and overlap integral in :eq:`interview-overlap`.

Insert the gain medium and a variable thermal lens into the cavity matrix.
Sweep from cold through the worst credible hot dioptric power, including
tolerances.  For every point record:

* stability trace and distance to both stability boundaries;
* beam radius through the pumped volume and on every coating;
* pump/mode overlap and expected higher-order-mode discrimination;
* clear-aperture clipping loss;
* waist location and external mode-matching change; and
* mirror-tilt sensitivity.

If the thermal sweep crosses a stability boundary, change resonator geometry;
do not merely plan to align more carefully.

6. Polarization, feedback, and mechanics
----------------------------------------

Use a polarization-selective element only if the gain/crystal geometry does not
provide sufficient stable polarization.  Budget the insertion loss and thermal
depolarization.  Tilt or wedge transmissive intracavity optics so ghosts cannot
form a parasitic cavity, while tracking the astigmatism they introduce.

Mount the crystal with a modeled and repeatable thermal interface, allow
differential expansion, and avoid stress concentrations.  Choose mirror mounts
whose angular drift and resonances fit the alignment-sensitivity budget.  Add
isolation or slight angle to prevent output-path feedback into the resonator and
pump diode where permitted by system requirements.

7. Verification plan
--------------------

.. list-table::
   :header-rows: 1
   :widths: 31 36 33

   * - Requirement or risk
     - Test
     - Pass evidence
   * - Output and efficiency
     - Incident and absorbed pump; output-versus-pump at stabilized temperatures
     - At least 5 W with declared efficiency basis and roll-over margin
   * - TEM00 beam quality
     - Two-axis second-moment caustic fit
     - :math:`M_x^2,M_y^2\le1.2` with residuals and uncertainty
   * - Polarization
     - Analyzer sweep over power and temperature
     - Required extinction ratio without mode or power instability
   * - Thermal robustness
     - Pump steps with waist, mode, power, and coolant logging
     - No stability crossing; model updated from measured thermal lens
   * - Alignment tolerance
     - Controlled mirror perturbation and environmental test
     - Requirement retained within allocated angular/positional range
   * - Coating/damage margin
     - Irradiance budget plus qualified optic data and inspection
     - Required statistical margin at wavelength and exposure condition

The beam-quality row must be converted into the full acceptance statement
described in :doc:`beam_quality`; the coating row must use the local-exposure and
qualification framework in :doc:`laser_damage`.

8. Optional Q-switched extension
--------------------------------

If the same 5-W average output is instead delivered at 20 kHz in 10-ns pulses,

.. math::

   E_p=250\,\mu\mathrm J,
   \qquad
   P_{\rm peak}\simeq25\,\mathrm{kW}.

At a 300-µm :math:`1/e^2` radius, the Gaussian on-axis fluence is

.. math::

   F_{\rm pk}\simeq\frac{2E_p}{\pi w^2}
   \simeq0.177\,\mathrm{J/cm^2},

and peak irradiance is about :math:`17.7\,\mathrm{MW/cm^2}`.  This immediately
changes the Q-switch, coating, bulk-damage, nonlinear, detector, and beam-dump
requirements even though average power is unchanged.

What makes this a strong interview answer
-----------------------------------------

It produces numbers quickly but labels them as assumptions, connects optical
and thermal models, treats the thermal lens as a range, checks intracavity rather
than output power alone, and ends with measurements capable of disproving the
model.
