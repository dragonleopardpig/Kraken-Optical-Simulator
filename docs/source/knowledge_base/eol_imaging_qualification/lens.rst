.. _eol-lens-qualification:

Lens Replacement Qualification
==============================

This plan evaluates an industrial imaging lens against an EOL incumbent or
qualifies a lens for a new machine-vision system.  Execute it under the common
controls in :doc:`index`.  Test the lens first on a calibrated reference
camera or optical bench, then on the proposed production camera.

.. contents::
   :local:
   :depth: 2


Objectives and release criteria
-------------------------------

The lens evaluation shall establish:

* mechanical fit, sensor coverage, mount/flange compatibility, retention, and
  production adjustability;
* correct focal length, FOV, magnification, working distance, entrance pupil,
  and image/object-space geometry;
* focus position, field curvature, depth of field (DOF), and stability;
* spatial-frequency response across field, wavelength, aperture, object
  distance, and manufacturing samples;
* lateral and longitudinal chromatic aberration;
* distortion, telecentricity or perspective, principal point, and calibration
  residual;
* relative illumination, vignetting, spectral transmission, colour shading,
  flare, ghosting, and stray-light behaviour;
* environmental, vibration, focus/iris retention, unit-to-unit, and lot
  consistency;
* acceptable application decisions and measurements with the production
  camera, illumination, mechanics, and algorithm.

Unless a test is explicitly marked not applicable in the approved protocol,
lens qualification requires ``PASS`` for L01--L14.  L01--L07, L10, L14, and
every false-accept or measurement-accuracy metric are critical.  The remaining
items are release requirements unless the system owner and quality owner
approve a documented deviation.


Required equipment and fixtures
-------------------------------

In addition to the common bench in :doc:`index`, prepare:

* an optical MTF bench or calibrated reference camera whose sampling,
  cover-glass stack, active area, and noise do not mask the lens behaviour;
* the baseline and proposed production cameras;
* calibrated slanted-edge, Siemens-star or other MTF targets covering the
  full object field, plus a traceable dot/grid target;
* a collimator and reticle for infinity-focus lenses, or a rigid finite-
  conjugate target stage for machine-vision lenses;
* narrow-band sources or filters at every critical production wavelength;
* a characterized uniform source and a spectroradiometer or calibrated
  detector for relative illumination/transmission;
* axial translation with adequate resolution for through-focus MTF, flange
  distance, longitudinal colour, and DOF measurements;
* object-height/depth fixtures and a precision rotary/translation stage for
  telecentricity, chief-ray, and distortion tests;
* an external bright source, black target, masks, and angular stage for flare
  and ghost testing;
* production mounts, adapters, filters, retaining rings, locking screws,
  torque tools, cable routing, and heat sources representative of the machine.

If a camera is used as the MTF detector, keep it and its processing identical
for baseline/candidate lens comparisons.  Its Nyquist frequency and SNR must
exceed the highest required lens frequency with margin.  Report the measured
result as **camera-lens system MTF** unless a validated detector MTF correction
has been applied; never label an undersampled system result as lens-only MTF.


Lens test summary
-----------------

.. list-table::
   :header-rows: 1
   :widths: 8 27 38 27

   * - ID
     - Evaluation
     - Primary data
     - Required result
   * - L01
     - Identity, documentation, compliance, lifecycle
     - Part/revision/lot matrix, supplier and coating evidence
     - Exact identity and all mandatory evidence accepted
   * - L02
     - Mechanical fit, mount, coverage, retention
     - Inspection, tolerance stack, image-circle/CRA checks
     - All fit, coverage, safety, and retention limits pass
   * - L03
     - Focal length, FOV, magnification, working distance
     - Grid fit, scale/FOV versus distance, pupil data
     - All first-order geometry CTQs pass
   * - L04
     - Focus, flange/back focus, field curvature, DOF
     - Through-focus MTF surfaces and best-focus maps
     - Fixed-plane focus and DOF limits pass
   * - L05
     - MTF/resolution across field
     - Tangential/sagittal MTF versus field/frequency
     - Every field/band/direction/application-frequency gate passes
   * - L06
     - Longitudinal/lateral chromatic aberration
     - Best-focus shift and colour-displacement vector fields
     - Chromatic focus, MTF, and registration limits pass
   * - L07
     - Distortion, telecentricity, perspective, calibration
     - Mapping residuals, magnification versus field/depth
     - Raw and calibrated geometry budgets pass
   * - L08
     - Relative illumination, vignetting, chief-ray compatibility
     - Flat-field maps versus aperture/band/focus
     - Coverage and uniformity limits pass
   * - L09
     - Spectral transmission and colour balance
     - Transmission curves and exposure/channel ratios
     - In-band signal and out-of-band rejection pass
   * - L10
     - Flare, ghosting, scatter, and high dynamic range
     - Source-angle maps, veiling glare, ghost catalogue
     - No false feature; contrast/flare limits pass
   * - L11
     - Aperture/focus adjustment and lock repeatability
     - Setting cycles, torque, scale, focus, MTF distributions
     - Every cycle returns within setting and imaging limits
   * - L12
     - Thermal, vibration, shock, and contamination stability
     - Before/during/after optical and physical results
     - CTQs pass throughout environment with no damage
   * - L13
     - Unit/lot consistency and incoming control
     - Per-unit distributions and incoming test specification
     - Variation fits budget; incoming controls accepted
   * - L14
     - Integrated application validation and pilot
     - Blind decisions, measurement-system analysis, pilot log
     - All production decision and measurement gates pass


Detailed experiments and pass/fail rules
----------------------------------------

L01 -- identity, documentation, compliance, and lifecycle
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Confirm that the exact lens configuration is traceable, controlled, and
supportable for the required machine lifetime.

**Procedure and conditions.**
Record manufacturer, order code, serial, manufacturing lot, optical revision,
mount, focal-length designation, aperture type/range, focus range, coating
band, filter or protective window, glass/material declarations, and country of
origin.  Review the full specification, drawing, environmental limits,
cleaning restrictions, regulatory/material declarations, warranty, PCN
policy, lifecycle commitment, repair/calibration support, and whether coating,
glass, cement, mechanics, or supplier may change under the same order code.

**Collect and output.**
Produce a signed identity/compliance matrix, supplier evidence pack, lifecycle
risk assessment, and controlled difference list versus the baseline lens.

**PASS.**
Delivered identity and coating match the order code; every mandatory
compliance and lifecycle requirement has acceptable evidence; serial/lot and
revision are traceable; and optically consequential changes require adequate
notification and requalification.

**FAIL.**
Any mandatory evidence is absent, coating/glass/revision is ambiguous, a
sample differs from its declaration, or uncontrolled material/design changes
can enter production.


L02 -- mechanical fit, mount, sensor coverage, and retention
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Demonstrate that the lens installs safely, covers the sensor, and maintains
alignment without interference or mount-induced variation.

**Procedure and conditions.**
Inspect outside envelope, mass, centre of gravity, mount thread/flange,
flange focal distance, shoulder squareness, thread engagement, locating datum,
rear-element protrusion, sensor-window clearance, filter thread, iris/focus
ring access, lock locations, cable/machine clearance, and required support.
Calculate the tolerance stack over focus travel and production adjustment.

Measure usable image circle and relative illumination on the complete active
sensor, including worst manufacturing decentre and mount tolerance.  Review
exit-pupil/chief-ray angle (CRA) against the sensor microlens and cover-glass
requirements.  Fit the lens in a representative machine using the released
adapter, torque, locking method, and strain relief.  Apply the required
orientation and gravity directions.

**Collect and output.**
Produce dimensional inspection, CAD/envelope overlay, tolerance stack,
image-circle/CRA evidence, mount runout/tilt, fit photographs, torque record,
and any support-bracket calculation.

**PASS.**
All hard dimensions, clearances, thread engagement, loads, flange/datum
limits, active-sensor coverage, CRA, retention, access, and safety margins
pass for every unit and orientation.  No unapproved adapter modification,
rear-element collision, mount sag, vignetting, or adjustment obstruction
exists.

**FAIL.**
Any hard fit/coverage/retention limit fails, the camera mount carries an
unapproved load, or an undocumented assembly selection is needed to obtain
alignment or focus.


L03 -- focal length, FOV, magnification, working distance, and pupils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify the first-order optical geometry across required conjugates.

**Procedure and conditions.**
Image a traceable grid at the nominal and extreme object distances using the
reference camera.  Fit object-to-image mapping and measure effective focal
length where the method supports it, transverse magnification, horizontal and
vertical FOV, working distance from controlled datums, principal point,
entrance/exit pupil location or working f-number where relevant, and focus
travel/margin.  For zoom, liquid, or motorized lenses, test every released
setting and approach each setpoint from both directions.

Report results in physical sensor/object units.  Do not infer focal length
only from the engraving, and do not compensate a wrong FOV by image resizing.

**Collect and output.**
Produce calibrated grid images, scale/FOV versus distance plots, fitted
first-order parameters, focus/adjustment margin, and baseline/candidate
differences.

**PASS.**
Required FOV is covered with margin at every working distance; magnification,
scale, aspect, focal-length-equivalent behaviour, pupil/working-f-number, and
adjustment range meet their guard-banded absolute limits; and no metric
regresses beyond its approved baseline margin.

**FAIL.**
Any required field is cropped, scale or working distance exceeds its budget,
focus cannot be reached with assembly tolerance, or electronic resampling is
needed to conceal a geometry failure.


L04 -- focus position, flange/back focus, field curvature, and DOF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Determine whether the complete field and object-height range remain sharp at
one lockable production focus.

**Procedure and conditions.**
At every required aperture, object distance, wavelength, and temperature,
sweep the detector or target axially through focus using steps fine enough to
resolve the permitted focus error.  At centre, mid-field, corners, and
application-critical points, calculate MTF at the application frequency in
tangential and sagittal directions versus axial position.

Record best-focus position per field, through-focus width at the required MTF,
field curvature, astigmatic focus separation, flange/back-focus margin, focus
sensitivity, and object-side near/far DOF.  Determine the single production
sensor plane/focus setting by the pre-approved optimization rule, then report
all field points at that **common plane**.  Also repeat after remounting and
locking.

**Collect and output.**
Produce through-focus curves, field-versus-focus MTF surface, best-focus and
astigmatism maps, selected common plane, usable DOF interval, remount
repeatability, and mechanical focus margin.

**PASS.**
At the locked common production plane, every required field, direction,
wavelength, object height, and unit meets the guard-banded MTF limit; near/far
DOF contains the entire object range with tolerance margin; flange/focus
travel permits assembly; and remount/refocus variation fits its allocation.

**FAIL.**
Only independently refocusing each field produces a pass, usable DOF misses a
required object height, production focus lies at an adjustment stop, or
field/thermal/remount shift violates the fixed-plane MTF limit.


L05 -- MTF and resolution across field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Measure spatial contrast over the full field and required spectral/aperture
range at the actual production focus.

**Procedure and conditions.**
Using an optical MTF bench or adequately sampled reference camera, measure
tangential and sagittal MTF at centre, multiple mid-field points, four
corners, and application-critical locations.  Test every production
wavelength/band, aperture, conjugate, focus setting, and orientation.  Sample
frequency densely through and beyond the highest application frequency,
within the detector's valid range.  Repeat after independent mounting and on
all qualification units.

Report both:

* **best-focus MTF**, useful for diagnosing intrinsic lens performance; and
* **common-production-plane MTF**, which is the release metric.

When using captured targets, correct for documented target and detector
limits or retain the result as end-to-end system SFR.  Check phase/alias
sensitivity and distinguish lens anisotropy from sensor-row/column response.
The KrakenOS captured USAF workflow is documented in
:doc:`../../manual/captured_usaf_mtf`.

**Collect and output.**
Produce native images or bench data, tangential/sagittal MTF curves, MTF at
application frequencies, MTF50/MTF10 where stable, field heatmaps, azimuth
asymmetry/decentration indicators, repeatability, and baseline/candidate
overlays.

**PASS.**
At the locked production plane, every field, azimuth, direction, band,
aperture, conjugate, and unit meets the absolute MTF requirement at each
application frequency and the approved non-inferiority margin.  Azimuth
asymmetry and remount variation fit their budgets, and no pass depends on
detector sharpening or undersampling.

**FAIL.**
Any required point/direction/band misses its guard-banded limit, only
best-focus rather than common-plane data pass, unit decentre/tilt exceeds its
limit, or the detector/target cannot support the claimed measurement.


L06 -- longitudinal and lateral chromatic aberration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Measure wavelength-dependent focus and magnification/position changes that
can reduce colour contrast or separate channels.

**Procedure and conditions.**
Use narrow-band sources near the short, centre, and long production
wavelengths; add intermediate or out-of-band points when material spectra
require them.  For each wavelength and field point, run a focus sweep and
record best-focus position and through-focus MTF.  At a common production
focus, measure MTF in every band.

Image a high-accuracy dot grid, edge, or pinhole field at the same mechanical
geometry.  Fit a common reference coordinate system, remove only approved
global translation/rotation, and calculate field-dependent lateral
displacement and magnification difference for every wavelength pair.  Report
the vectors in sensor micrometres, pixels of each proposed camera,
object-space units, and normalized field height.

Run valid ``BB/CB/BC/CC`` combinations and the reference lens/camera isolation
experiment in :doc:`index`.  Measure before and after the production colour
correction; do not let a high-order calibration obscure an unstable lens.

**Collect and output.**
Produce longitudinal best-focus-versus-wavelength plots, per-band
common-plane MTF, lateral-colour vector maps, radial/tangential components,
object-space error, correction model/residual, and repeatability across
remounts and units.

**PASS.**
All per-band common-plane MTF limits pass; best-focus spread is no more than
25 % of usable application DOF by default; residual lateral displacement is
no more than 25 % of the smallest positional tolerance and no more than
0.5 production-camera pixel where channel registration is assumed; and no
chromatic metric exceeds its approved baseline regression.  Application-
specific limits replace these defaults when pre-approved.

**FAIL.**
Any required wavelength fails MTF/focus/position limits, correction residual
is unstable across unit/focus/temperature, or chromatic error is reported
only in a unit that hides its impact (for example micrometres without pixels
and object-space error).


L07 -- distortion, telecentricity, perspective, and calibration residual
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Qualify raw image geometry and the residual after a controlled production
calibration.

**Procedure and conditions.**
Image a traceable grid covering the FOV at nominal focus and object depths
spanning the URS.  Measure radial and tangential distortion, local
magnification, aspect/orthogonality, principal point, field-dependent
position error, and decentre.  For object-space telecentric lenses, translate
the target through depth and measure scale, centroid, and perspective change.
For image-space telecentric requirements, assess exit pupil/CRA using an
approved method.

First report uncorrected geometry.  Then fit the exact calibration model and
number of parameters allowed in production on a training capture.  Validate
residuals on independent positions, depths, orientations, remounts,
temperatures, and lens units.  Do not increase model order after viewing the
validation result.

**Collect and output.**
Produce distortion vector/percentage maps, local scale and telecentricity
versus depth, calibration coefficients, independent residual maps and
quantiles, extrapolation mask, and stability results.

**PASS.**
Raw distortion/telecentricity meet any uncorrected limits; guard-banded
independent calibration residual, scale drift, perspective, and principal-
point stability each fit their allocated measurement budget over the entire
qualified volume; all units pass with the released model/order; and relative
regression is within margin.

**FAIL.**
Any usable location/depth exceeds its geometry budget, a pass requires
training/validation leakage or a different model per image, calibration is
unstable after remount/temperature, or uncorrected geometry violates an
algorithm assumption.


L08 -- relative illumination, vignetting, and chief-ray compatibility
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify usable image-circle coverage and stable brightness/colour across the
sensor.

**Procedure and conditions.**
Using a characterized uniform source, acquire dark-subtracted flat fields at
each production aperture, focus/conjugate, wavelength/channel, and camera.
Avoid source clipping and saturation.  Rotate the lens/camera or use a
calibrated source map to separate source, sensor PRNU, and lens shading.
Inspect mechanical and optical vignetting, cat-eye pupil clipping, corner
colour shift, dust sensitivity, and interaction with the candidate sensor's
microlens/CRA.

Measure relative illumination versus field, corner/centre ratio, asymmetry,
colour shading, usable image circle, and stability with focus/aperture.
Validate the proposed flat-field correction on independent captures,
temperatures, and lens units.

**Collect and output.**
Produce per-band raw/corrected illumination maps, radial and azimuth profiles,
corner/centre ratios, image-circle boundary, colour-shading maps, calibration
files, and independent residuals.

**PASS.**
No active or measurement-critical region is mechanically clipped; raw
relative illumination and colour shading meet their absolute/relative limits;
corrected residual meets the application uniformity budget on every unit and
condition; and correction does not create clipping or excessive noise.  In
the absence of an application value, raw corner/centre illumination of at
least 70 % and corrected uniformity within :math:`\pm 5` % are initial
screening gates only, not universal qualification limits.

**FAIL.**
Any required field is clipped, asymmetry indicates excessive decentre,
raw/corrected uniformity or colour shading exceeds its limit, or a unit-
specific correction is unavailable where one is required.


L09 -- spectral transmission and colour balance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Confirm adequate in-band throughput, colour balance, and rejection of
unwanted wavelengths.

**Procedure and conditions.**
Measure lens transmission with a spectrophotometer or compare a calibrated
detector/reference path over the production spectrum.  Include coating-band
edges, illumination lines, sensor-sensitive near-IR/UV, filters, and incidence
angles relevant to the field.  At the production camera, measure exposure
needed to reach the operating signal, per-channel ratios, and SNR on actual
materials at the motion-safe exposure limit.

Account for aperture and effective f-number at finite conjugates.  Separate
spectral transmission from relative illumination and sensor response.

**Collect and output.**
Produce absolute or relative transmission spectra with uncertainty,
in-band/out-of-band integrals, exposure/channel-ratio comparison, SNR by
material/band, and baseline/candidate delta.

**PASS.**
Every required band/material reaches its signal and SNR limit within the
allowed illumination, aperture, gain, and exposure; prohibited out-of-band
response is below its limit; colour/channel balance is calibratable within
range; and transmission does not regress beyond the approved margin.

**FAIL.**
A production band lacks throughput, motion-safe exposure cannot reach SNR,
out-of-band leakage creates a false response, or a result relies on saturated
channels or excessive gain.


L10 -- flare, ghosting, scatter, and high-dynamic-range behaviour
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Ensure bright sources, reflective parts, and off-axis illumination do not hide
defects or create false ones.

**Procedure and conditions.**
Image a dark field containing a controlled bright source at multiple
intensities and angular positions: within the FOV, just outside each edge and
corner, and at every known machine source/reflection direction.  Repeat at
production aperture, focus, filters, wavelengths, sensor, and exposure.
Include glossy, curved, and highly reflective application parts.

Measure veiling-glare level, black-region rise, local contrast loss, ghost
position/area/peak/energy, flare symmetry, saturation bloom/smear, and recovery
after a bright frame.  Compare with the baseline at matched object radiance
and matched useful signal.  Inspect lens barrels, spacers, filter surfaces,
and adapters for responsible paths.

**Collect and output.**
Produce annotated source-angle image sets, veiling-glare and contrast curves,
ghost maps/catalogue, recovery timeline, worst-case application images, and
ray-path hypothesis or KrakenOS model where useful.

**PASS.**
No source angle or intensity produces a false feature, hidden required
feature, saturation path, or unsafe decision; guard-banded veiling glare,
ghost peak/energy, contrast loss, and recovery meet absolute limits; and none
regresses beyond the approved baseline margin.  Where no value exists, use
``no more than baseline`` as the screening gate until the application contrast
budget is approved.

**FAIL.**
Any prohibited false/hidden feature occurs, a flare metric exceeds its limit,
or testing omits a credible production source angle/material.


L11 -- aperture/focus adjustment, lock, and repeatability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify that production assembly and maintenance can set and retain the
qualified optical state.

**Procedure and conditions.**
For manual lenses, cycle focus and iris across their ranges, approach the
production marks from both directions, apply the released setting method and
lock torque, then measure aperture/effective f-number, focus position, FOV,
principal point, and MTF.  Include at least 30 set/lock/release cycles per unit
for engineering screening.  For motorized/tunable lenses, command repeated
positions from both directions and after restart; measure backlash,
repeatability, settling, temperature dependence, and position feedback.

Apply the production cable/hosing loads and camera orientation.  Mark witness
lines or tamper evidence where used.  Check that locking focus or iris does
not shift tilt, decentre, or the other adjustment.

**Collect and output.**
Produce cycle-level settings, torque, focus/FOV/MTF distributions, hysteresis
and backlash plots, lock-induced image shift, settling time, and work-
instruction capability result.

**PASS.**
Every setting/lock cycle returns within allocated focus, aperture, FOV,
principal-point, and MTF limits; no lock-induced shift or cross-coupling
exceeds its budget; motorized settling fits cycle time; and the documented
method is repeatable across operators/units.

**FAIL.**
Any cycle misses an imaging limit, engraved scales or feedback are
insufficient for repeatable setup, lock torque damages/shifts the lens, or
performance depends on unrecorded operator judgement.


L12 -- thermal, vibration, shock, and contamination stability
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Verify optical alignment and materials throughout handling and operation.

**Procedure and conditions.**
Using the production mount/support, test at the qualified temperature and
humidity extremes after soak.  Measure focus, FOV/scale, principal point,
distortion/calibration residual, MTF, relative illumination, and chromatic
metrics at each plateau and during transition if the machine operates then.
Apply required vibration and shock in the relevant orientations, then repeat
optical tests.  Perform approved dust, oil mist, humidity, cleaning-agent,
coating-durability, or ingress tests when credible.

Inspect for focus/iris slip, loose elements, cement/coating change,
condensation, contamination, scratches, fungus risk, thread damage, and
permanent optical shift.  Return to room condition and repeat the baseline
sequence.

**Collect and output.**
Produce environmental profiles, before/during/after optical tables and maps,
focus/scale drift coefficients, physical inspection, photographs, and
failure/event log.

**PASS.**
Every CTQ remains within its guard-banded absolute limit throughout the
claimed operating envelope; no relative regression exceeds its margin;
vibration/shock/cleaning cause no slip, damage, contamination, or permanent
change; and any required refocus/calibration interval is compatible with the
maintenance plan.

**FAIL.**
Any CTQ leaves its limit, the lens changes permanently, a lock slips, optical
surfaces/materials are incompatible with the environment, or a pass depends
on an unplanned manual adjustment.


L13 -- unit/lot consistency and incoming inspection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Ensure evaluated performance is representative of routine supply.

**Procedure and conditions.**
Test at least five candidate lenses from at least two lots where available.
Compare L02--L12 results by serial/lot, emphasizing MTF field asymmetry,
best-focus/field curvature, lateral colour, distortion, relative illumination,
transmission, focus/iris torque, and cosmetic/defect inspection.  Investigate
outliers rather than deleting them.

Define incoming identity/cosmetic inspection plus a short optical test using
the production or reference camera: grid/FOV, fixed-plane centre/corner MTF,
flat field, and an application golden sample.  Define storage, handling,
cleaning, calibration, quarantine, and PCN requalification triggers.

**Collect and output.**
Produce per-unit/lot interval plots, outlier investigations, estimated
variation, approved serial register, incoming-inspection procedure and limits,
golden images/data, and requalification matrix.

**PASS.**
Every unit meets every individual hard limit; observed unit/lot variation fits
inside the guard band; no unexplained asymmetry or bimodal population exists;
and incoming tests can reject wrong, damaged, contaminated, misassembled, or
optically degraded units before production.

**FAIL.**
A unit passes only through group averaging or selected orientation, observed
variation consumes the application margin, an outlier remains unexplained, or
incoming control cannot detect a consequential change.


L14 -- integrated application validation and production pilot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Objective.**
Prove that the candidate lens and camera-lens pair perform the real task.

**Procedure and conditions.**
Lock the production focus, aperture, illumination, camera settings,
calibration, and algorithm before final scoring.  Execute configuration
``BC`` where valid and the proposed ``CC`` configuration.  Use the blinded
representative part set, nuisance variation, measurement-system analysis, and
pilot procedure specified by C15 in :doc:`camera`.

Challenge optical failure modes deliberately: smallest defects at centre and
corners, object height/tilt limits, wavelength/colour extremes, gloss,
reflective edges, flare-source angles, illumination drift, focus/temperature
limits, motion direction, and remount after maintenance.  Preserve native
images and link every decision to a physical sample and condition.

**Collect and output.**
Produce the locked recipe, part/image provenance, confusion matrices or
measurement-system analysis, results by field/height/material/condition,
worst-case images, production-rate pilot log, availability/cycle-time result,
and failure review.

**PASS.**
Every pre-registered class and condition meets its false-accept,
false-reject, detection, measurement bias, repeatability, reproducibility,
calibration residual, cycle-time, and availability limit with the approved
confidence method; no critical pilot event occurs; and the result uses the
same camera-lens-processing configuration intended for release.

**FAIL.**
Any critical application or measurement limit fails, a field/colour/height
stratum is hidden by an aggregate result, the final data influenced tuning,
or the pilot differs from the locked production configuration.


Lens report checklist
---------------------

The lens report is complete only when it includes:

* a one-page L01--L14 result matrix with worst unit and evidence links;
* baseline/candidate identity, serials/lots, camera/detector, aperture, focus,
  conjugates, wavelengths, and exact ``BB/BC/CC`` configurations;
* native target images or bench data and analysis settings sufficient to
  reproduce every derived metric;
* through-focus and fixed-plane MTF, chromatic, geometric, illumination,
  transmission, flare, adjustment, environmental, and application evidence;
* results in image micrometres, production-camera pixels, object-space units,
  and normalized field where relevant;
* explicit separation of lens-only/bench claims from camera-lens system
  measurements;
* every failure, retest, exclusion, deviation, corrective action, and unit/lot
  variation result;
* the production mounting/focus/aperture procedure, calibration, incoming
  test, maintenance limits, and signed G1--G4 decisions from :doc:`index`.
