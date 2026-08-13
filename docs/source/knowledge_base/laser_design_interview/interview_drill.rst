Interview Questions and Answer Frameworks
=========================================

Answer each question aloud before opening the suggested answer.  Lead with the
physical principle, give one governing relation, state assumptions, and finish
with an engineering consequence or test.

Exact-role systems questions
----------------------------

How do you turn a market requirement into subsystem budgets?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clarify the customer use case and measurable system outcome, including operating
conditions, time/population statistic, interfaces, lifetime, and verification
method.  Build a sensitivity model and allocate performance, variation,
measurement uncertainty, and margin to source, delivery optics, mechanics,
motion, controls, and environment.  Assign owners and close every allocation in
a requirements-verification matrix.  Use worst case for hard/safety limits and
the covariance form in :eq:`interview-system-budget` when statistical
contributors are correlated.

How would you prove a risky product concept on the bench?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

State the cause-event-impact risk and competing hypotheses.  Build the minimum
controlled setup that produces different predicted observations, calibrate its
measurement chain, and agree numerical exit criteria before testing.  Preserve
raw data and configuration, compare with the model, and end with a design
decision plus residual risk—not merely ``the prototype worked.``

How would you design an automated laser qualification bench?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start from the requirements-verification matrix.  Define DUT interfaces,
calibrated metrology and uncertainty, a source reference channel, deterministic
fixturing/motion, environmental logging, interlocks and injected faults.  Use a
recoverable state machine that saves raw data and complete provenance before
analysis.  Prove the bench with known-good, known-bad, repeat load/home, drift,
range/linearity, and measurement-repeatability/reproducibility studies before it
makes acceptance decisions.

The motion encoder is stable but the beam still drifts. What next?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The encoder, physical optic pose, and optical output are different observables.
Time-align encoder, beam centroids at two planes, temperatures, purge/airflow and
structural sensors after a repeatable move.  Test approach direction, settling
time, cable force, mount creep, optic heating, Abbe offset and non-common-path
sensor drift.  Change move profile or thermal/purge condition one at a time to
separate servo dynamics from structural or optical drift.

What is different about integrating a DUV laser?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First identify wavelength and architecture: excimer, frequency-converted solid
state, or a supplied source.  Then add the matching gas/high-voltage or nonlinear
conversion risks, invisible-beam controls, DUV-compatible materials/coatings and
detectors, nitrogen purge and contamination control, residual wavelengths, and
accumulated-dose monitoring for absorption, color centers, compaction,
birefringence, thermal wavefront and coating degradation.  Follow the controlled
alignment and qualification plan in :doc:`duv_integration`.

How do you transfer a prototype to operations and field service?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Release the configuration, interfaces, fixtures, software and calibration with
a procedure containing safe state, prerequisites, datums, expected observation
and limit per step, data capture, recovery and escalation.  Validate it with a
trained nonexpert, train concept/execution/diagnostics, and monitor first-pass
yield, retest, adjustment pareto, cycle time and field recurrence.  Feed those
data back into product, fixture, limits and training.

How do you report a serious integration issue to management?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lead with requirement and current result, customer/schedule impact, confidence
and containment.  Show the top evidence-supported hypotheses, next
discriminating test with owner/date, recovery options and the decision or
resource needed.  Put detailed traces in backup.  Separate measured fact,
engineering inference and committed action.

How do you handle a cross-functional technical disagreement?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Restate the shared requirement and decision deadline; make coordinate systems,
interfaces and terms explicit; list each hypothesis and predicted observation;
then agree on a small discriminating analysis or test and its decision rule.
Record the result and owner.  Escalate a decision with evidence and impact when
necessary, rather than escalating personalities.

Core theory
-----------

Why is population inversion necessary?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Net stimulated gain must exceed resonant absorption.  In the cross-section
form :eq:`interview-small-signal-gain`, inversion makes
:math:`\sigma_eN_2-\sigma_aN_1` positive.  A populated upper state alone is not
enough if the lower-state absorption remains larger.

What sets laser threshold?
~~~~~~~~~~~~~~~~~~~~~~~~~~

Threshold is the round-trip balance: stimulated gain equals mirror output
coupling plus absorption, scatter, diffraction, and all other losses.  Write
:eq:`interview-threshold`, explain the double pass for a linear cavity, and say
that above threshold saturation clamps the gain near this value.

Why is a four-level laser easier to operate than a three-level laser?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The lower laser level of an ideal four-level system empties rapidly, so little
pump is needed to make its upper population exceed the lower one.  A three-level
system terminates on the ground state and must deplete a large ground-state
population before net gain appears.

What determines slope efficiency?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is a chain of driver, pump transport, absorption, quantum/Stokes, overlap,
internal-loss, and extraction efficiencies.  State the pump-power basis.  A
high optical slope efficiency can coexist with poor wall-plug efficiency.

Why can a laser oscillate on several longitudinal modes?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The cavity permits frequencies separated by :eq:`interview-fsr`; every mode
lying under adequate net gain can oscillate.  Gain saturation, homogeneous or
inhomogeneous broadening, spatial hole burning, polarization, and mode selectors
determine which survive.

Resonators and beams
--------------------

How do you decide whether a resonator is stable?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multiply the complete round-trip ABCD matrix and require
:math:`|(A+D)/2|<1`.  For an empty two-mirror cavity use
:math:`0<g_1g_2<1`.  Then sweep the thermal lens and tolerances; nominal
stability alone is not robustness.

How do you calculate the intracavity mode size?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Solve the self-consistent complex-beam equation
:math:`q=(Aq+B)/(Cq+D)`, select the physical root, and propagate it with the ABCD
law.  Extract beam radius and wavefront curvature from
:eq:`interview-q-parameter` at every optic and through the gain medium.

What does :math:`M^2=1.5` mean?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The measured second-moment beam parameter product is 1.5 times the ideal
Gaussian value at the same wavelength.  It has 1.5 times the ideal divergence
for a fixed waist, or a larger focused spot for a fixed input geometry.  It does
not identify the mode composition or guarantee the beam is stigmatic.

What is the tradeoff in choosing a small cavity waist?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It can improve pump overlap and lower required gain volume, but raises
intracavity irradiance, divergence, coating/damage risk, nonlinear phase, and
sensitivity to thermal aberration and alignment.  The answer must include both
gain and reliability.

How would you choose an output coupler?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sweep transmission in a saturated-gain model with measured/estimated internal
loss and the intended pump range.  Too little transmission traps power and
raises internal loading; too much raises threshold.  Verify the choice against
thermal-lens, coating, and low-pump requirements.

Solid-state system design
-------------------------

How do you choose a gain medium?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start from wavelength, pulse format, linewidth/tuning, power, beam quality, and
environment.  Compare cross section, lifetime, bandwidth, pump absorption,
quantum defect, thermal conductivity, thermo-optic/stress properties, fracture
limit, available geometry, doping quality, and coatings.  Then close the pump,
gain, thermal, and resonator models together.

How do you select a pump diode and its delivery optics?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start with the gain medium's absorption versus wavelength and temperature, then
compare the diode spectrum over current, junction temperature, tolerance, and
life.  Use measured fast/slow-axis or fiber core/NA data to propagate étendue,
not just total watts.  Model spectral absorption, three-dimensional pump/mode
overlap, residual pump, thermal deposition, and diode feedback.  Finally verify
power, spectrum, focus, absorption, and output together at cold, nominal, and hot
states as described in :doc:`diode_pumped_lasers`.

What causes thermal lensing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Absorbed pump creates a nonuniform temperature and stress field.  Refractive
index changes with temperature, end faces bulge, and photoelastic response
changes optical path; stress also produces birefringence.  Measure lens power
against absorbed pump and model it as a range with aberration, not just one
perfect focal length.

Why can Yb:YAG be efficient yet harder to reach threshold?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Its small quantum defect reduces heat, but the quasi-three-level transition has
significant lower-state population and reabsorption.  Temperature, pump
brightness, inversion density, wavelength, and overlap strongly influence net
gain.

What limits scaling of an end-pumped rod?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Localized heat raises thermal lens, aberration, stress, birefringence, and
fracture risk; brightness and overlap constrain pump scaling.  Larger pump/mode
areas reduce irradiance but demand more gain volume and can support higher modes.
Thin-disk, slab, fiber, or distributed pumping changes the heat-flow geometry.

What are ASE and parasitic lasing?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ASE is spontaneous emission amplified while crossing an inverted medium; it
depletes stored energy and adds background.  Parasitic lasing is oscillation on
an unintended feedback path, often along a long crystal dimension or polished
surface.  Inspect all high-gain paths and suppress them with geometry, absorbing
boundaries, roughening, segmentation, or index matching.

When would you use Q-switching rather than mode locking?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use Q-switching to store inversion and release comparatively high-energy
nanosecond-class pulses at lower repetition rates.  Use mode locking when many
longitudinal modes must phase-lock to produce picosecond or femtosecond pulses.
Quote energy, duration, repetition rate, and peak-power requirements rather than
choosing by pulse duration alone.

Hands-on and troubleshooting
----------------------------

How would you align a laser cavity?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Make the setup safe, establish a mechanical axis with two references, pass a
low-power alignment beam through element centers, retroreflect each cavity
mirror, distinguish desired surfaces from ghosts, verify pump overlap, and then
raise pump slowly while walking the mirrors.  Optimize and characterize at low
power before scaling under thermal monitoring.

The pump is present but the laser will not oscillate. What next?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify pump wavelength/polarization and calibrated power, transport and
absorption, overlap with the intended gain volume, cavity closure and mirror
orientation, output-coupler value, clipping/contamination, and whether gain is
being stolen by fluorescence, ASE, or a parasitic path.  Check the detector and
expected wavelength too.

How do you measure :math:`M^2`?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Attenuate without clipping, focus with a known lens, collect calibrated
background-corrected second-moment widths at multiple planes on both sides of
the waist, fit :eq:`interview-m2-beam` in each principal axis, and report the
fit, wavelength, waist, divergence, and uncertainty.  One near-field and one
far-field image are not a robust caustic measurement.

Why is :math:`M^2` not a complete beam-quality specification?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It compresses the second-moment waist-divergence product into a propagation
metric.  Different beams can share :math:`M^2` while differing in halo energy,
bucket power, focal peak, astigmatism, pointing jitter, polarization, and time
dependence.  Choose additional metrics from the application and state width,
centering, time-gate, operating-state, and uncertainty conventions; see
:doc:`beam_quality`.

Output falls slowly after turn-on. What hypotheses do you test?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Thermal-lens movement, pump-diode wavelength drift, coolant/interface change,
polarization loss, mount drift, absorption saturation, and contamination are
leading hypotheses.  Time-correlate absorbed pump, diode/coolant temperatures,
output, spectrum, beam position, and waist.  Use a pump step to separate fast
electrical response from slower thermal response.

How do you prevent optical damage?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calculate local pulse fluence, peak irradiance, average absorption, and
temperature at every bulk and coating surface; use the proper spatial/temporal
peak factors.  Compare with qualified data at matching wavelength and pulse
conditions, include statistical and contamination margin, avoid ghost foci and
back-reflections, control cleanliness, and inspect while scaling gradually.

How would you qualify an optic's laser-damage margin?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calculate local Gaussian or measured-profile peak exposure at every intended and
ghost path using intracavity power and temporal/spatial factors.  Match it to
damage-probability data for the actual wavelength, pulse shape/duration, rate,
shot count, spot definition, angle, polarization, coating lot, environment, and
test protocol.  Include measurement and lot statistics, contamination/lifetime,
fault transients, and detection criteria.  A catalog's typical LIDT without those
conditions is not acceptance evidence; use the framework in :doc:`laser_damage`.

How would you prove a low-power problem is internal loss rather than weak pump overlap?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Measure incident and absorbed pump, image or map the pumped region and cavity
mode, and vary their relative size/position while holding thermal state fixed.
Independently estimate cavity loss using an output-coupler or delay-time method.
Overlap changes should modify threshold/slope systematically; true passive loss
persists after overlap is optimized.

Whiteboard calculations
-----------------------

**A 100-mm linear air cavity:**
:math:`\Delta\nu=c/(2L)=1.50\,\mathrm{GHz}`.

**A 10-W average, 50-kHz source:**
:math:`E_p=P/f=200\,\mu\mathrm J`.
At 5 ns, :math:`P_{\rm peak}\approx40\,\mathrm{kW}` before pulse-shape factors.

**A 100-µm ideal waist at 1064 nm:**
:math:`z_R=\pi w_0^2/\lambda\approx29.5\,\mathrm{mm}` and
:math:`\theta\approx3.39\,\mathrm{mrad}`.

**A 20-W pump with 85% transport and 90% absorption:**
:math:`P_{\rm abs}=15.3\,\mathrm W`.

**808-nm pump to 1064-nm output:** the Stokes limit is
:math:`808/1064\approx75.9\%`; quantum defect is at least 24.1% of absorbed pump.

Behavioral/project question
---------------------------

For ``Tell me about a laser you designed or debugged,`` use:

1. **Requirement and constraint** — include numerical targets.
2. **Model** — gain, resonator, thermal, tolerance, or measurement relation.
3. **Decision** — the tradeoff you personally made.
4. **Evidence** — calibrated result with uncertainty or before/after comparison.
5. **Failure or surprise** — what disagreed with the model.
6. **Correction** — the discriminating experiment and design update.
7. **Lesson** — a reusable engineering principle, not merely ``communicate more.``
