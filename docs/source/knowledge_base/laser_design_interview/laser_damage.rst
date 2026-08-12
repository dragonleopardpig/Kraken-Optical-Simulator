Laser-Induced Damage Engineering
================================

Laser-induced damage is a system reliability problem, not a single catalog
number.  The relevant exposure is local and statistical; it depends on the
source, material, surface, coating, defect population, environment, history,
measurement protocol, and definition of damage.

Calculate local exposure before comparing thresholds
----------------------------------------------------

For an elliptical spatial Gaussian with :math:`1/e^2` intensity radii
:math:`w_x,w_y`,

.. math::
   :label: interview-gaussian-exposure

   I_{\rm pk}=\frac{2P}{\pi w_xw_y},
   \qquad
   F_{\rm pk}=\frac{2E_p}{\pi w_xw_y}.

The second expression is peak fluence for one pulse.  Peak irradiance also
depends on temporal shape.  Define the effective duration

.. math::
   :label: interview-effective-pulse-duration

   \tau_{\rm eff}=\frac{\int P(t)\,dt}{P_{\rm pk}},
   \qquad
   I_{\rm pk}=\frac{F_{\rm pk}}{\tau_{\rm eff}}.

This avoids silently treating FWHM duration as :math:`E/P_{\rm pk}` for every
pulse shape.  Repeat the calculation at every coating and bulk path using local
beam radii, incidence angle, polarization, wavelength, pulse duration, repetition
rate, burst structure, and credible hot spots.  Inside a resonator, use
circulating rather than output power and include counter-propagating/standing-wave
field enhancement where applicable.

Damage mechanisms by operating regime
-------------------------------------

.. list-table:: First mechanisms to investigate—not universal boundaries
   :header-rows: 1
   :widths: 21 34 45

   * - Exposure regime
     - Leading mechanisms
     - Engineering evidence to seek
   * - Continuous wave or long pulse
     - Linear absorption, temperature rise, stress, coating delamination, melting, or fracture
     - Absorption map, thermal boundary condition, temperature/stress model, time to equilibrium
   * - Nanosecond-class pulse
     - Defect absorption, multiphoton seed generation, avalanche, plasma, and thermal/mechanical aftermath
     - Defect statistics, pulse shape, local fluence, number of sites, morphology, and conditioning history
   * - Picosecond/femtosecond pulse
     - Strong-field/multiphoton ionization, avalanche during the pulse, nonlinear propagation, and incubation
     - Peak field/intensity, bandwidth, dispersion, nonlinear focus, pulse contrast, repetition and environment
   * - High-average repetitive pulse
     - Single-pulse mechanisms combined with cumulative heating, incubation, contamination growth, and fatigue
     - Burst duty, cooling time, S-on-1 behavior, long-duration exposure, and in-situ monitoring

These regimes overlap.  Defects, coating field distribution, material band gap,
absorption, pulse contrast, and environment can move the dominant mechanism.
Self-focusing can also move the peak exposure away from the geometrical focus;
a B-integral or nonlinear propagation check belongs in intense-pulse designs.

Understand what an LIDT result means
------------------------------------

A usable laser-induced-damage-threshold statement includes at least:

* optic material, coating design/process, substrate preparation, lot, and surface;
* wavelength and spectral bandwidth;
* pulse temporal shape and duration, repetition rate, burst pattern, and shot count;
* spatial profile, radius definition, incidence angle, and polarization;
* test environment, cleanliness, conditioning, and sample area/site count;
* exposure protocol, damage-detection method, damage criterion, and inspection
  resolution; and
* threshold estimator, damage-probability curve, sample size, and confidence or
  uncertainty.

Do not scale a threshold from one pulse duration or wavelength with a universal
square-root law and call it qualified.  Scaling laws are mechanism-dependent
estimates; procure or test data under representative conditions.

Test protocols answer different questions
-----------------------------------------

.. list-table:: Common laser-damage test logic
   :header-rows: 1
   :widths: 20 31 28 21

   * - Protocol
     - Exposure
     - Useful result
     - Limitation
   * - 1-on-1
     - One pulse per fresh site at assigned fluence
     - Single-shot damage probability versus fluence
     - Does not expose incubation from repeated pulses
   * - S-on-1
     - A fixed number of equal-fluence pulses at each fresh site
     - Multiple-pulse threshold/probability and incubation behavior
     - Result depends on :math:`S`, rate, burst timing, and environment
   * - R-on-1 or N-on-1 ramp
     - Fluence increases on the same site until damage or the sequence ends
     - Conditioning/ramp behavior and efficient screening
     - Exposure history differs from fixed-fluence service
   * - Raster scan
     - Beam scans a larger surface at defined overlap and speed
     - Defect discovery, conditioning, or area qualification
     - Scan geometry and detection sensitivity govern coverage

Damage is commonly defect-driven and probabilistic.  A small-spot test samples a
limited area and precursor population; a larger production beam may encounter
more rare defects.  ``Zero damage observed`` is evidence tied to a tested site
count and detection limit, not proof of zero probability.

Build a damage budget
---------------------

For every intended and unintended path, tabulate optic/surface, wavelength,
local :math:`w_x,w_y`, power or pulse energy, temporal factor, angle,
polarization, exposure time/shot count, calculated peak exposure, qualified
threshold distribution, uncertainty, and margin.  Include:

* intracavity mirrors, gain-medium faces, Q-switches, polarizers, etalons, and
  nonlinear crystals;
* ghost foci, rejected polarization, undiffracted orders, residual pump and
  fundamental/harmonic wavelengths;
* startup, misalignment, failed cooling, lost seed, Q-switch mistiming, and
  control overshoot;
* coating nonuniformity, beam modulation/hot spots, contamination, focus drift,
  and back-reflection; and
* bulk, entrance surface, exit surface, coating electric-field maxima, adhesive,
  mount, sensor, aperture, window, and beam dump.

Do not use one arbitrary safety factor for unrelated uncertainties.  Allocate
margin separately for source variation, beam-size measurement, coating-lot
statistics, contamination/lifetime drift, fault transients, and model error.

Procurement and acceptance
--------------------------

A defensible optic specification declares operating and test conditions, test
protocol, number of sites/samples, damage definition/detection, probability or
survival criterion, reporting format, witness-sample relation, and handling
requirements.  Ask whether the threshold applies to the coated surface, bulk,
or complete component and whether the reported value is a guaranteed minimum,
typical result, or best-site observation.

At incoming inspection, preserve lot identity and cleanliness history.  Verify
surface/coating documentation, dimensional and wavefront requirements, and the
agreed damage evidence.  Witness coupons are useful only when their substrate,
preparation, coating run/location, handling, and test exposure represent the
delivered optic closely enough for the decision.

Safe power scaling and failure analysis
---------------------------------------

Scale in controlled steps while monitoring power, near/far-field profile,
scatter, spectrum, pulse shape/energy, pointing, coolant state, and optic images.
Allow thermal equilibrium at each plateau.  A new scatter site, transmission
change, acoustic event, plume, mode distortion, or irreversible power loss is a
stop condition—not a prompt to optimize alignment at higher power.

After suspected damage, make the system safe and preserve evidence.  Record the
last known exposure and time history before moving optics.  Use appropriate
microscopy/scatter inspection, locate the site relative to the beam and coating
surface, and distinguish contamination, coating failure, surface pit, bulk track,
fracture, and mount/thermal damage.  Check upstream causes and downstream debris;
replacing the visibly damaged optic without closing the initiating mechanism can
destroy the replacement.

Fast interview checks
---------------------

* Average power alone is inadequate for pulsed-damage qualification.
* The smallest nominal waist may not be the highest actual exposure if aberration,
  self-focusing, hot spots, or ghosts are present.
* A high LIDT coating can still fail from absorption-driven heating or a defect.
* Cleaning can help contamination risk but can also add scratches, residue, or
  handling damage; use qualified processes and inspection.
* Threshold is not a sharp universal material constant, and survival in one
  short test does not establish service lifetime.
