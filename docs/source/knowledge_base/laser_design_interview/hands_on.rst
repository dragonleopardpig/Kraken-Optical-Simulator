Hands-On Alignment, Measurement, and Debugging
==============================================

Interviewers value a safe, causal procedure more than a heroic alignment story.
The recurring pattern is: make safe, establish references, measure a baseline,
change one variable, and preserve evidence.

For the exact job-description emphasis on automated qualification, motion
control, and product transfer, pair this page with :doc:`role_playbook`.  For
wavelength-specific purge, contamination, ageing, and alignment controls, use
:doc:`duv_integration`.

Safety before signal
--------------------

Before enabling a laser or pump:

1. identify every wavelength, accessible beam, pulse regime, and maximum
   credible exposure;
2. apply the site's laser-safety procedure and approved eyewear for all relevant
   wavelengths;
3. terminate the direct beam, pump leakage, harmonic residuals, and likely
   specular reflections with suitable rated stops;
4. remove jewelry and reflective tools, control beam height, close enclosures,
   and verify interlocks;
5. use the lowest practical alignment power and a camera, card, or viewer that
   is appropriate to the wavelength; and
6. confirm cooling, flow, temperature, electrical grounding, high-voltage
   discharge, and emergency-off behavior.

Eyewear is the last layer, not permission to search for a beam by eye.  Near-IR
beams, intracavity power, Q-switched pulses, and generated harmonics deserve
explicit treatment because visibility is a poor hazard indicator.

Resonator alignment sequence
----------------------------

**Passive geometric alignment**

1. Establish a mechanical datum and two irises at the intended cavity height.
2. Send a low-power alignment beam through gain-medium centers, apertures, and
   the nominal pump/laser overlap line.
3. Place each mirror so the incident spot is near its mechanical center and the
   retroreflection returns to the upstream reference.
4. Verify that wedged substrates and ghost reflections cannot be mistaken for
   the desired surface.
5. Check clearance through apertures at both near and far reference planes.

**First light**

1. Start below expected threshold and verify pump position, absorption, cooling,
   fluorescence, and detector range.
2. Raise pump slowly while walking the two cavity mirrors in small paired steps.
3. Watch power, spatial profile, spectrum, and temporal signal—not power alone.
4. Once lasing occurs, optimize overlap and alignment at low or moderate power.
5. Record the mirror settings, pump threshold, output-versus-pump curve, beam
   image, spectrum, and thermal state before further optimization.

**Power scaling**

Increase power in controlled increments.  At each plateau wait for thermal
equilibrium and record output, absorbed pump, coolant temperatures, beam size and
position, polarization, spectrum, and noise.  A slow power roll-over, moving
waist, or changing mode shape is often thermal; an abrupt irreversible change
suggests contamination, coating damage, fracture, or a control fault.

Measurement playbook
--------------------

.. list-table::
   :header-rows: 1
   :widths: 19 29 28 24

   * - Quantity
     - Method
     - Controls
     - Common failure
   * - Incident and absorbed pump
     - Calibrated power measurement before and after the unpumped/pumped medium
     - Account for fluorescence, double passes, window loss, and detector wavelength response
     - Calling incident pump ``absorbed pump``
   * - Threshold and slope
     - Linear fit of output versus the declared pump-power basis above threshold
     - Stabilize temperature and exclude roll-over region
     - Fitting too few points or mixing warm-up states
   * - Beam radius and :math:`M^2`
     - Attenuated caustic scan through a known focus and second-moment fit
     - Multiple planes on both sides of waist, unsaturated detector, background subtraction
     - Inferring :math:`M^2` from one spot or one far-field angle
   * - Pulse energy
     - Energy meter with appropriate aperture, coating, range, and repetition-rate correction
     - Cross-check average power divided by repetition rate
     - Using a slow power meter for unstable pulses
   * - Pulse duration
     - Fast detector/oscilloscope when bandwidth permits; autocorrelation or FROG-class method for ultrashort pulses
     - De-embed detector and cable response; state pulse-shape assumption
     - Reporting autocorrelation width as pulse width without conversion
   * - Spectrum and linewidth
     - Spectrometer, scanning Fabry–Perot, wavemeter, or heterodyne method matched to scale
     - Calibrate resolution and free spectral range
     - Confusing instrument resolution with laser linewidth
   * - Polarization
     - Rotating analyzer; add a retarder for full Stokes/ellipticity information
     - Correct detector normalization and optic wavelength range
     - Calling a large extinction ratio proof of perfect linearity
   * - Thermal lens
     - Probe-beam deflection/focusing or infer from resonator mode/threshold changes
     - Measure versus absorbed pump after thermal equilibrium
     - Forcing an aberrated lens into one focal-length number
   * - Loss and gain
     - Output-coupler sweep/Findlay–Clay-style threshold analysis, delay-time method, or calibrated single-pass measurement
     - Keep pump geometry and thermal state fixed
     - Folding diffraction and parasitic oscillation into unexplained ``loss``

Beam-quality measurement in words
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Attenuate without clipping or distorting the wavefront, focus with a known good
lens, acquire background-corrected second-moment widths at enough axial planes
around the waist, fit the propagation law in :eq:`interview-m2-beam` separately
for both principal axes, and report wavelength, fit quality, waist position,
waist size, divergence, and :math:`M^2`.  Rotate or otherwise diagnose the axes
if astigmatism is present.

For metric selection, second-moment definitions, window/noise sensitivity, and
a defensible acceptance specification, use :doc:`beam_quality`.  For damage
exposure, test protocols, and evidence preservation, use :doc:`laser_damage`.

Do not put an unqualified neutral-density filter near a high-power focus.
Absorption, thermal lensing, nonlinear response, coating damage, and etalon
feedback can corrupt both the laser and the measurement.

Fault-isolation tree
--------------------

No laser output
~~~~~~~~~~~~~~~

.. code-block:: text

   Pump present and at correct wavelength/polarization?
   ├─ no  → driver, diode temperature, transport, interlock, fiber/collimator
   └─ yes → pump reaches and is absorbed in the intended volume?
            ├─ no  → focus, alignment, absorption length, coating, pump pass
            └─ yes → cavity closes geometrically?
                     ├─ no  → datum, irises, mirror curvature/orientation, ghosts
                     └─ yes → gain exceeds total loss?
                              ├─ no  → inversion, output coupling, clipping, contamination
                              └─ yes → detector/spectrum path or parasitic oscillation

Low power or poor slope
~~~~~~~~~~~~~~~~~~~~~~~

Separate pump coupling, absorption, gain overlap, internal loss, extraction,
and thermal roll-over.  Measure the pump basis explicitly, repeat the slope at
several cooling conditions, inspect residual pump and fluorescence, and compare
with a model that includes the actual output coupler.

Poor beam quality
~~~~~~~~~~~~~~~~~

Look for pump/mode mismatch, aperture clipping, higher-order-mode threshold,
thermal aberration, stress birefringence, resonator degeneracy, contaminated or
damaged optics, astigmatism, and measurement saturation.  Check images at more
than one axial plane; a single clean-looking spot is insufficient.

Power instability
~~~~~~~~~~~~~~~~~

Correlate output with pump current, diode temperature, coolant temperature,
mechanical vibration, acoustic noise, cavity length, polarization, and spectrum.
Use time-aligned logs.  A measured transfer function or correlation is stronger
evidence than ``it seems thermal.``

Frequency or mode hopping
~~~~~~~~~~~~~~~~~~~~~~~~~

Check cavity-length drift, gain-medium temperature, etalon temperature/angle,
back-reflection, polarization competition, pump noise, and spatial hole burning.
Observe both spectrum and power while perturbing one control variable.

Alignment is very sensitive
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Compare the as-built cavity with the stability map, including hot thermal lens.
Check mirror pivot position, mount stiffness, beam size on apertures, high-order
mode degeneracy, and whether an internal element acts as an unintended wedge or
lens.  Do not fix a fundamentally marginal design with finer adjustment screws.

How to present an experiment
----------------------------

Use this short structure in an interview:

* **Hypothesis:** the specific mechanism and why it matches the observations.
* **Discriminating test:** one measurement that differs between leading causes.
* **Controls:** calibration, thermal state, detector linearity, and fixed variables.
* **Expected signature:** direction and scale of the change.
* **Decision:** what result triggers the next design or troubleshooting action.

Example: ``I suspect thermal lensing rather than pump noise because beam size and
power drift on the coolant time scale.  I would log absorbed pump, two coolant
temperatures, output power, and caustic position during a pump step.  A monotonic
waist shift at constant pump supports thermal lensing; fast correlated power
noise without waist motion points back to the pump or driver.``
