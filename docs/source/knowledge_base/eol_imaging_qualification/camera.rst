.. _eol-camera-qualification:

Camera Replacement Qualification
================================

This plan evaluates an industrial machine-vision camera against an incumbent
model or qualifies a camera for a new system.  Execute it under the common
controls in :doc:`index`.  The camera shall be tested first with the retained
baseline lens or a calibrated reference lens, then with the proposed
production lens.

.. contents::
   :local:
   :depth: 2


Objectives and release criteria
-------------------------------

The camera evaluation shall establish:

* physical, electrical, protocol, driver, and configuration compatibility;
* correct FOV, sampling, pixel geometry, bit depth, and image orientation;
* sensitivity, linearity, noise, dynamic range, uniformity, and defect
  behaviour at production operating points;
* spatial, spectral, colour, and channel-registration performance;
* exposure, trigger, shutter, latency, frame-rate, and data-integrity
  performance;
* stability over warm-up, temperature, power, restart, and production duty;
* equivalent or better application decisions on representative parts;
* acceptable unit-to-unit variation and supplier lifecycle controls.

Unless a test is explicitly marked not applicable in the approved protocol,
camera qualification requires ``PASS`` for C01--C16.  C01--C04, C10--C12,
C15, and every application safety or false-accept metric are critical: one
failing unit fails the item.  C05--C09, C13--C14, and C16 are also release
requirements unless the system owner and quality owner approve a documented
deviation.


Required equipment and fixtures
-------------------------------

In addition to the common bench in :doc:`index`, prepare:

* a calibrated low-aberration reference lens that covers both sensors;
* the baseline production lens and the proposed lens;
* an integrating sphere or uniform flat-field source with stable current
  drive and monitored radiance;
* traceable neutral-density filters or a controlled source covering dark to
  saturation;
* narrow-band sources or filters spanning the production spectrum;
* a calibrated slanted-edge, grid/dot, colour, and application-specific
  target;
* a light-tight cap, temperature sensor on the camera body, and chamber if
  required;
* the production power supply, I/O module, cables, network interface card,
  switches, frame grabber, host, and storage path;
* an oscilloscope or logic analyser with sufficient bandwidth for trigger,
  strobe, exposure-active, and output timing;
* a moving stage, encoder, rotating disc, or actual conveyor for shutter and
  motion testing.

Mount the camera from its production datums with production-intent cables and
strain relief.  Record camera-to-target distance, lens focus/aperture, filter,
adapter, sensor temperature where available, illumination spectrum, and all
feature-node values.


Camera test summary
-------------------

.. list-table::
   :header-rows: 1
   :widths: 8 27 38 27

   * - ID
     - Evaluation
     - Primary data
     - Required result
   * - C01
     - Identity, documentation, compliance, lifecycle
     - Part/revision matrix, declarations, lifecycle and change-control record
     - Exact identity and all mandatory evidence accepted
   * - C02
     - Mechanical, optical, electrical compatibility
     - Inspection report, CAD overlay, pinout, power/inrush
     - All hard interface and safety limits pass
   * - C03
     - Software, API, format, and configuration
     - Feature map, native frames, save/load and restart results
     - Required features and deterministic configuration pass
   * - C04
     - Sensor geometry, FOV, and sampling
     - Pixel pitch, active area, scale, FOV, orientation, coverage
     - Every FOV/sampling/geometry CTQ passes
   * - C05
     - Response, gain, exposure linearity, sensitivity
     - Photon-transfer and response curves, fit residuals
     - Absolute and non-inferiority radiometric gates pass
   * - C06
     - Noise, SNR, saturation, dynamic range
     - Temporal statistics and derived noise/dynamic-range metrics
     - Required operating-point and range limits pass
   * - C07
     - Dark signal and dark-current stability
     - Dark maps versus exposure and temperature
     - Dark, drift, warm/hot-pixel limits pass
   * - C08
     - DSNU, PRNU, blemishes, and correction
     - Dark/flat maps, defect catalogue, correction residual
     - Uniformity and defect rules pass on every unit
   * - C09
     - Spatial response and aliasing
     - SFR/MTF curves and field maps
     - MTF/alias/application sampling limits pass
   * - C10
     - Spectrum, colour, channel registration
     - Spectral response, colour error, chromatic displacement
     - Spectral/classification/registration gates pass
   * - C11
     - Exposure, shutter, trigger, latency, motion
     - Timing distributions, skew and moving-target error
     - Worst-case timing and image-position limits pass
   * - C12
     - Throughput and data integrity
     - Frame/event logs, counters, resource and bandwidth traces
     - No prohibited loss/corruption; sustainable rate passes
   * - C13
     - Warm-up and environmental stability
     - Metrics versus time, temperature, humidity, and vibration
     - All CTQs pass throughout the qualified envelope
   * - C14
     - Power, disconnect, fault, and recovery robustness
     - Cycle/fault logs and configuration checksums
     - Safe deterministic recovery within the allowed time
   * - C15
     - Application validation and production pilot
     - Blind decisions, measurement-system analysis, pilot log
     - All production decision and measurement limits pass
   * - C16
     - Unit/lot consistency and incoming control
     - Per-unit distributions and incoming test specification
     - Population evidence and incoming limits accepted


Detailed experiments and pass/fail rules
----------------------------------------

C01 -- identity, documentation, compliance, and lifecycle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Confirm that the purchasable item is stable, traceable, supportable, and
approved for the installation environment.

**Procedure and conditions.**
Record manufacturer, order code, sensor, colour/mono variant, shutter type,
mount, interface, hardware revision, firmware, country of origin, and serial
number.  Review the datasheet, dimensional drawing, pinout, protocol
conformance, environmental ratings, regulatory declarations, mean time
between failures if claimed, warranty, product-change notification (PCN)
policy, last-time-buy status, minimum longevity commitment, and approved
alternates.  Resolve whether the manufacturer may substitute a sensor or
firmware under the same order code.

**Collect and output.**
Produce a signed identity/compliance matrix, supplier evidence pack, lifecycle
risk rating, and list of differences from the baseline.

**PASS.**
The delivered identity matches the controlled order code; all mandatory
regulatory, material, cybersecurity, environmental, and supplier requirements
have current evidence; the PCN and traceability process is acceptable; and no
unresolved lifecycle risk violates the sourcing plan.

**FAIL.**
Any mandatory evidence is missing, the model can change without acceptable
notification, a sample differs from its declared revision, or a lifecycle or
compliance requirement is not met.


C02 -- mechanical, optical, and electrical compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Demonstrate safe physical replacement without hidden changes in datum,
clearance, optical stack, or power.

**Procedure and conditions.**
Inspect or measure body envelope, mounting-hole location and thread, sensor
datum, mount flange distance, mount tilt/play, connector locations, cable bend
radius, heat-sink contact, mass, centre of gravity, filter/cover-glass stack,
protective window, and ingress sealing.  Check lens image circle against the
active sensor diagonal and chief-ray requirements.  Verify pinout, I/O voltage
thresholds, isolation, polarity, grounding, nominal power, inrush, ripple
sensitivity, heat dissipation, and behaviour at voltage limits.

Perform a controlled fit trial in a representative machine.  Do not force an
adapter, leave a lens supported only by the camera mount, or count a CAD
clearance smaller than the approved manufacturing and assembly tolerance.

**Collect and output.**
Produce a dimensioned inspection sheet, CAD/envelope overlay, tolerance-stack
calculation, optical-stack comparison, pinout review, and power/inrush traces.

**PASS.**
All dimensions, loads, image-circle margins, flange/datum limits, connector
clearances, thermal limits, voltage/current limits, grounding, and I/O safety
requirements pass with tolerance margin.  No unintended vignetting, sensor
tilt, interference, cable load, or unsafe state is observed.

**FAIL.**
Any hard mechanical/electrical limit fails, an undocumented adapter or wiring
change is required, the production lens is inadequately supported, or the
sensor/cover-glass stack prevents qualified imaging.


C03 -- software, API, pixel format, and configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify that the camera can be controlled, reproduced, and diagnosed in the
production software stack.

**Procedure and conditions.**
Use the production host, operating-system image, driver, transport layer,
frame grabber or network interface, and SDK.  Enumerate feature nodes and test
the required exposure, gain, ROI, binning/decimation, pixel formats, trigger,
strobe, chunk data, timestamp, counters, temperature, status, and user-set
functions.  Verify Bayer order or channel order with a physical colour
target.  Decode native packed formats and maximum values independently.

Save the qualified configuration, power-cycle the camera, reload it, restart
the service, disconnect/reconnect the cable, and replace the camera with
another qualified sample.  Repeat with any identifier or IP-address
provisioning used in production.

**Collect and output.**
Archive the feature-node export, readable/writable feature comparison, native
test frames, metadata decode, configuration checksum, logs, and automated
configuration verification.

**PASS.**
Every required feature is available with adequate range and increment; image
format and metadata decode correctly; prohibited automatic processing is
disabled; configuration load is deterministic across all units and restarts;
and unsupported differences are absent from the production code path.

**FAIL.**
A required feature is missing, silently coerced, incorrectly decoded, reset
after restart, unit-dependent, or requires an unapproved driver/application
change.


C04 -- sensor geometry, FOV, orientation, and sampling
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Confirm that the active sensor and production geometry cover and sample the
required object region.

**Procedure and conditions.**
Image a traceable dot/grid target at each required working distance.  Verify
active width/height, pixel pitch, ROI origin/increments, aspect ratio,
horizontal/vertical orientation, mirroring, rotation, principal point,
effective magnification, FOV, object-space pixel scale, and corner coverage.
Measure rather than relying only on datasheet pitch.  Test full frame and each
production ROI/binning mode.

For a different sensor size or pixel pitch, report both unchanged drop-in
geometry and optimized application geometry.  Keep native pixels during
measurement.  Evaluate the smallest critical feature at its worst field and
pose, not just at the centre.

**Collect and output.**
Produce calibrated grid images, fitted mapping, scale/FOV residuals,
object-space sampling, pixels per critical feature, and coverage/margin maps.

**PASS.**
Every required object point is inside the usable FOV with approved margin;
scale, aspect, orientation, principal-point, and ROI limits meet the URS;
the smallest feature has the pre-approved number of effective samples after
MTF and motion are considered; and lens image-circle/CRA compatibility passes.

**FAIL.**
Any required area is cropped or vignetted, axes or Bayer order are wrong,
geometry exceeds its error budget, or the candidate relies on interpolation
to claim missing physical sampling.


C05 -- response, gain, exposure linearity, and sensitivity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Measure the conversion from incident exposure to digital signal and verify
that production operating points are controllable and stable.

**Procedure and conditions.**
With the reference lens or an integrating sphere, acquire bias/dark frames and
uniform illuminated frames from near black through saturation at each
production pixel format, analogue gain, and relevant wavelength.  Use at least
ten exposure levels with denser sampling near black and saturation; acquire
enough frames at each level to separate temporal and spatial variation.
Monitor source intensity.  Perform a photon-transfer/EMVA 1288 analysis where
the camera permits it.

Measure response curve, black offset, conversion gain where valid,
responsivity, usable saturation, linear fit range, residual non-linearity,
exposure-time accuracy, gain-step accuracy, channel balance, and hysteresis
when increasing/decreasing exposure or gain.

**Collect and output.**
Produce raw mean/variance tables, response and photon-transfer curves,
fit range/residual plots, per-gain metrics, source-monitor log, and machine
readable results.

**PASS.**
At every qualified operating point, signal reaches the required level without
clipping; exposure/gain accuracy and response non-linearity meet their
absolute limits; no unapproved knee, auto function, or quantization plateau
exists; and sensitivity/linearity do not regress beyond the approved baseline
margin.  A 1 % non-linearity and 2 % exposure/gain repeatability are reasonable
initial limits only when the application budget has not set stricter values.

**FAIL.**
Any operating point clips or falls below required signal, response is
unstable or unmodelled, controls are inaccurate beyond limits, or the absolute
or non-inferiority gate fails.


C06 -- temporal noise, SNR, saturation, and dynamic range
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Determine whether the candidate can separate required signals over the full
production intensity range.

**Procedure and conditions.**
Use C05 sequences to calculate temporal dark noise, shot/noise behaviour,
signal-to-noise ratio (SNR), saturation signal, dynamic range, and
signal-to-noise ratio at the production operating points.  Measure each
colour plane separately for colour sensors.  Include low-signal conditions,
shortest and longest production exposures, and all production gains.  Do not
compare digital counts without accounting for bit depth and gain.

Where possible follow EMVA 1288 definitions.  If on-camera processing makes
that model invalid, use the general model and state the processing.

**Collect and output.**
Produce noise histograms, variance-versus-signal curves, SNR curves, saturation
and dynamic-range table, quantiles, confidence/uncertainty bounds, and
baseline/candidate deltas.

**PASS.**
Guard-banded SNR at every CTQ signal level, saturation headroom, temporal
noise, and dynamic range meet the absolute limits and approved relative
margin on every unit.  No clipped, banded, or quantization-limited region
overlaps the production range.

**FAIL.**
Any CTQ signal falls below its SNR/dynamic-range requirement, a noise mode
violates the error budget, or a reported improvement depends on hidden
denoising or clipping.


C07 -- dark signal, dark current, and warm/hot pixels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Characterize exposure- and temperature-dependent dark behaviour that can
create false features or consume dynamic range.

**Procedure and conditions.**
Cap the sensor light-tight and acquire repeated frames at the minimum,
nominal, and maximum production exposure/gain at room temperature and each
qualified temperature extreme after stabilization.  Add several exposure
times to estimate dark-current slope.  Repeat after warm-up and after the
longest production duty cycle.

Measure mean black level, temporal drift, dark-signal non-uniformity (DSNU),
dark-current distribution, row/column structure, random-telegraph pixels,
warm/hot-pixel count and location, and black-level clamp behaviour.  Run once
with defect correction disabled and once with the released correction.

**Collect and output.**
Produce dark maps, histograms, exposure/temperature curves, defect-coordinate
list, temporal traces, and corrected/uncorrected comparison.

**PASS.**
Dark offset, drift, DSNU, dark current, structured noise, and defect counts
meet their application-derived absolute limits at every condition and do not
regress beyond the baseline margin.  No unstable defect enters a protected
measurement region or creates a false application decision.

**FAIL.**
Any dark metric or application result exceeds its limit, defects are unstable
or uncorrectable under the released process, or correction hides rather than
controls the risk.


C08 -- PRNU, DSNU, blemishes, and flat-field correction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Measure spatial non-uniformity and verify correction validity across signal,
gain, wavelength, and temperature.

**Procedure and conditions.**
Acquire dark frames and spatially uniform fields at approximately 10 %, 50 %,
and 80 % of usable range for every production band/channel.  Remove measured
source/lens non-uniformity using a calibrated reference or rotate/translate
the camera to separate fixed sensor structure.  Calculate photo-response
non-uniformity (PRNU), DSNU, row/column banding, dust/blemish maps, cluster
defects, and low-frequency colour/luminance shading.

Create the proposed dark/flat correction using only its calibration set and
validate it on independent frames, another temperature, and all units.  Check
that correction does not amplify noise, clip, or conceal new defects.

**Collect and output.**
Produce raw/corrected flat maps, row and column profiles, PRNU/DSNU statistics,
defect catalogue by category, low-frequency shading maps, calibration files,
and independent-validation residuals.

**PASS.**
Every uncorrected metric satisfies the sensor acceptance limit, every
corrected residual satisfies the application uniformity limit, no prohibited
cluster/line defect exists, and calibration remains valid across the
qualified range.  Each unit must pass; averaging units is prohibited.

**FAIL.**
Any prohibited defect exists, corrected residual or drift exceeds its limit,
or a unit requires undocumented hand editing of its defect map.


C09 -- spatial-frequency response, resolution, and aliasing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify useful spatial contrast, not merely pixel count.

**Procedure and conditions.**
At best focus, acquire a calibrated slanted edge or other approved target at
centre, four corners, and any application-critical field point.  Test
horizontal, vertical, and, where relevant, diagonal/motion directions at each
production colour band, aperture, ROI/binning mode, and processing state.
Use linear raw data first.  Repeat after independent remount/refocus.

Calculate SFR/MTF versus cycles/pixel, cycles/mm at the sensor, and
cycles/mm in object space; report MTF at the application frequency, MTF50,
MTF10 where stable, anisotropy, overshoot, and response near/above Nyquist.
Inspect moire, colour aliasing, false resolution, sharpening halos, and phase
sensitivity.  KrakenOS's captured-image workflow is described in
:doc:`../../manual/captured_usaf_mtf`; use its USAF method where appropriate,
while a slanted edge is preferred for a continuous SFR.

**Collect and output.**
Produce native captures, focus sweep, SFR/MTF curves, field/wavelength maps,
repeatability, alias/overshoot images, and baseline/candidate plots on common
physical and object-space axes.

**PASS.**
Guard-banded MTF at every pre-registered application frequency and field point
meets the absolute limit and relative margin in both axes; focus repeatability
passes; aliasing/overshoot does not create a false application feature; and
the end-to-end application sampling requirement passes.

**FAIL.**
Any required field/band/direction misses its MTF limit, an apparent result is
created by sharpening or aliasing, or only a visually selected best unit or
best repeat passes.


C10 -- spectral response, colour accuracy, and channel registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Qualify wavelength sensitivity, colour separation, and spatial registration,
including apparent colour aberration exposed by a sensor change.

**Procedure and conditions.**
Measure each raw channel under narrow-band or monochromator illumination
across the production spectrum, including out-of-band sources that can reach
the machine.  Record quantum-efficiency data from the supplier but verify the
system response at critical wavelengths.  Test production filters and
illuminants.

Under the characterized production illuminant, capture a traceable colour
target and actual coloured materials at several intensities.  Derive colour
matrix/white balance only from a training set and validate it on independent
patches and parts.  Report a defined colour difference such as
:math:`\Delta E_{00}` only if the workflow is colorimetric; classification
applications shall also report the actual class confusion matrix.

Execute the narrow-band focus and displacement isolation experiment in
:doc:`index`.  Measure channel edge/centroid positions before and after
demosaicing and correction across the FOV.  Include the reference lens and
all valid ``BB/CB/BC/CC`` combinations.

**Collect and output.**
Produce spectral response curves, channel crosstalk and SNR, colour-target
predicted/measured values, colour-difference distribution, class confusion
matrix, wavelength focus curves, and chromatic-displacement vector maps in
micrometres, pixels, object-space units, and normalized field height.

**PASS.**
All required materials/bands meet minimum channel signal and SNR; prohibited
out-of-band response is below its limit; all colour classes meet the
false-accept/false-reject gate; and the chromatic MTF, focus spread, and
registration gates in :doc:`index` pass on independent validation data.  For
a general colorimetric application, mean
:math:`\Delta E_{00}\leq 3` and 95th percentile
:math:`\Delta E_{00}\leq 5` may be used as initial limits, but production
class separation and the URS take precedence.

**FAIL.**
Any critical wavelength/material has inadequate SNR, a colour class or
registration limit fails, calibration is fitted and judged on the same data,
or acceptable-looking rendered colour hides a raw-channel or spatial failure.


C11 -- exposure timing, shutter, trigger, latency, and motion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify that the image represents the required place and time on a moving
machine.

**Procedure and conditions.**
Measure electrical trigger threshold and pulse width, trigger-to-exposure
latency, exposure duration, exposure-active/strobe timing, frame/data-ready
latency, timestamp accuracy, and jitter using an oscilloscope/logic analyser.
Test minimum, nominal, and maximum exposure; minimum and maximum trigger rate;
free-run and every production trigger mode; burst start/stop; encoder input;
and any multi-camera synchronization.

Image a calibrated moving target in both directions at maximum line speed and
acceleration.  For rolling shutters, measure line time, full-frame readout,
skew, illumination-band interaction, and partial exposure.  Measure motion
blur rather than calculating it only from the requested exposure value.

**Collect and output.**
Produce timing diagrams and distributions, event/frame correlation, missing
or duplicate trigger list, rolling-shutter skew, moving-target position/scale
error, motion-blur MTF, and multi-camera phase error.

**PASS.**
Every trigger produces exactly the required frame/event; worst-case
guard-banded latency and jitter fit the control budget; measured exposure is
within its limit; skew, position error, and motion blur consume no more than
their allocated measurement/imaging budgets; and synchronization passes at
all production rates.  No relative regression is allowed for a
false-accept-critical timing metric.

**FAIL.**
Any missing/duplicate/misassociated frame occurs, a timing bound is exceeded,
motion creates an out-of-tolerance image, or a rolling/global shutter
difference is not controlled by the released design.


C12 -- throughput, transport, and data integrity
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Demonstrate sustainable acquisition without silent loss, corruption, backlog,
or resource exhaustion.

**Procedure and conditions.**
Run the full production path at maximum ROI size, bit depth, frame/trigger
rate, cable length, camera count, and expected competing network/host load.
Include acquisition, processing, decision, image retention, and deletion.
Run at least :math:`10^6` frames or the risk-approved endurance count.  Stress
packet size/delay, switch ports, frame-grabber buffers, disk limits, and
application restart.  Correlate trigger IDs, camera frame IDs, timestamps,
payload sizes, checksums, decisions, and PLC acknowledgements.

Monitor camera/transport error counters, dropped/incomplete frames, resend,
buffer occupancy, queue latency, CPU/GPU/RAM, network utilization, disk
latency/capacity, temperature, and clock synchronization.

**Collect and output.**
Produce a frame-level audit log, error/counter summary, throughput and latency
percentiles, resource traces, checksum failures, and bottleneck analysis.

**PASS.**
Default gate: zero corrupted, incomplete, duplicate, unexplained dropped, or
misassociated frame in :math:`10^6` events; no buffer overflow or unbounded
backlog; sustained rate is at least the URS rate with approved margin; and all
latency/resource limits pass.  If the URS permits loss, its explicit rate and
safe reaction replace the zero-loss default.

**FAIL.**
Any prohibited data-integrity event occurs, performance depends on an
unqualified host/network condition, resources grow without bound, or the
system cannot identify and enter a safe state after an allowed loss.


C13 -- warm-up and environmental stability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify image and timing performance throughout the actual operating envelope.

**Procedure and conditions.**
From cold power-on, record dark level, flat-field mean, noise, scale, focus,
selected MTF, timing, body/sensor temperature, and power until stable.  Repeat
at minimum and maximum qualified ambient temperature and humidity with
appropriate soak.  If required by the URS, test temperature cycling,
condensation prevention, vibration while operating, shock survival, dust or
water exposure, and external light leakage using approved safety procedures.

Use the production mounting and heat path.  At each environmental plateau,
run dark/flat, grid, resolution, timing, and representative application
checks.  Repeat after return to room conditions to detect permanent shift.

**Collect and output.**
Produce time/temperature traces, drift coefficients, before/during/after
metric tables, images, fault logs, and physical-inspection results.

**PASS.**
Every CTQ remains inside its guard-banded absolute limit at all qualified
conditions, no metric regresses beyond its relative margin, warm-up reaches
the defined stable state within the permitted time, and no permanent change,
condensation, fault, or unsafe temperature occurs.

**FAIL.**
Any CTQ leaves its limit during the claimed envelope, stabilization is too
slow, environmental exposure causes damage/configuration loss, or production
heat sinking differs from the tested setup.


C14 -- power, disconnect, fault, and recovery robustness
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Ensure deterministic and safe behaviour during foreseeable machine faults
and maintenance actions.

**Procedure and conditions.**
Perform the risk-approved number of cold starts, warm restarts, rapid
power cycles, brownout/overvoltage-limit trials, trigger present during boot,
cable disconnect/reconnect, network/switch restart, host-service restart,
storage-full event, lost time synchronization, and camera replacement.
Inject one fault at a time, then the credible combinations defined by the risk
analysis.  Verify alarm visibility to the PLC/operator and safe decision
handling.

One hundred successful power/reconnect cycles is a useful engineering
screening default; reliability claims require a separately justified sample
size and duration.

**Collect and output.**
Produce cycle-by-cycle result logs, boot/recovery-time distributions,
configuration checksums, alarm/PLC traces, failed-state images, and residual
fault list.

**PASS.**
All cycles recover within the URS time to the exact qualified configuration;
no stale image or false good decision is issued; every injected fault is
detected and produces the approved safe response; and no configuration,
calibration, or device identity is lost.

**FAIL.**
Any unsafe decision, undetected fault, manual undocumented recovery,
configuration drift, intermittent enumeration, or recovery-time violation
occurs.


C15 -- application validation and production pilot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Prove that the candidate performs the production task under representative
normal and adverse variation.

**Procedure and conditions.**
Lock the ``CC`` production recipe before scoring.  Use a blinded, randomized,
traceable set containing known-good parts, every important defect/class,
near-limit samples, supplier/lot/material/colour variation, pose and height
limits, dirty/worn conditions, illumination drift, speed extremes, and other
credible nuisance factors.  Do not tune on the final validation set.

For inspection, report true/false positive/negative results by class and
condition with confidence bounds.  For metrology, perform a measurement
system analysis against a traceable reference: bias, linearity, repeatability,
reproducibility, stability, and part variation.  Then run the production pilot
at rate with operators, PLC, reject mechanism, image retention, and alarms.

**Collect and output.**
Produce the frozen recipe, data split and provenance, image/part-level result
table, confusion matrices, receiver-operating or precision-recall analysis
where useful, measurement-system analysis, worst-case images, pilot log, and
failure review.

**PASS.**
Every pre-registered defect/class and nuisance stratum meets its detection,
false-accept, false-reject, bias, repeatability, reproducibility, cycle-time,
and availability limit with the approved confidence method; there is no
critical pilot event; and results do not depend on sample leakage or
post-hoc threshold selection.

**FAIL.**
Any safety/quality critical false accept occurs beyond its stated rule, any
stratum or measurement CTQ fails, the validation set influenced tuning, or the
pilot configuration differs from the frozen recipe.


C16 -- unit/lot consistency and incoming inspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Control candidate variation after the evaluated samples enter routine supply.

**Procedure and conditions.**
Compare all unit-level C04--C13 metrics, calibration constants, defect maps,
firmware/hardware revisions, and environmental results.  Estimate within-unit,
unit-to-unit, and lot-to-lot variation where the sample supports it.  Define
incoming identity checks, a short dark/flat/grid/application reference test,
control limits, golden images, calibration frequency, quarantine rules, and
PCN requalification triggers.

At minimum, incoming checks shall catch the wrong mono/colour model, pixel
format/Bayer order, sensor revision, firmware/configuration, excessive
defects, scale/orientation error, and gross sensitivity or timing change.

**Collect and output.**
Produce per-unit/lot control charts or interval plots, outlier investigation,
incoming-inspection procedure and limits, approved-unit register, golden
dataset, and requalification matrix.

**PASS.**
Every qualification unit passes every individual hard limit; observed
variation fits inside the allocated guard band; incoming inspection can detect
specified wrong or degraded units; and supplier changes that require partial
or full requalification are contractually and procedurally controlled.

**FAIL.**
Any unit is accepted only through averaging, variation consumes the
application margin, an outlier is unexplained, or revision/lot changes can
enter production without adequate detection and requalification.


Camera report checklist
-----------------------

The camera report is complete only when it includes:

* a one-page C01--C16 result matrix with worst unit and evidence links;
* baseline and candidate identities, samples/lots, settings, and exact
  ``BB/CB/CC`` configurations;
* native raw examples and configuration exports sufficient to reproduce each
  analysis;
* radiometric, noise, uniformity, spatial, colour, timing, throughput,
  environmental, and application results with uncertainty;
* explicit accounting for changed pixel pitch, sensor format, CFA, shutter,
  bit depth, cover glass, processing, and driver;
* every failure, retest, exclusion, deviation, and corrective action;
* the locked production recipe, incoming test, calibration files, and signed
  G1--G4 decisions defined in :doc:`index`.
