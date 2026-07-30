.. _eol-imaging-qualification:

Machine-Vision Camera and Lens EOL Qualification
=================================================

This guideline qualifies a replacement for an end-of-life (EOL) industrial
machine-vision camera, lens, or both.  It is intended for metrology,
inspection, alignment, gauging, OCR, colour classification, and defect
detection systems.  It covers a drop-in comparison with an incumbent model
and the assessment of a new imaging design.

Qualification is an **end-to-end risk decision**, not a datasheet comparison.
A camera and lens can each meet their component specifications and still fail
when combined with the production illumination, mechanics, image processing,
triggering, algorithm, and parts.  Conversely, a candidate need not reproduce
every incumbent parameter if it meets the controlled requirements and
production performance.

Use this page for the common protocol, then execute both component-specific
plans when a camera and lens are changed:

.. toctree::
   :maxdepth: 2

   camera
   lens

.. contents::
   :local:
   :depth: 2


Decision principles
-------------------

The qualification has five non-negotiable principles.

#. **Freeze the intended use before testing.**  Record fields of view (FOVs),
   working distances, smallest relevant features, tolerances, line speed,
   exposure-time limit, spectral bands, environments, interfaces, and
   application error limits.
#. **Retain a golden baseline.**  Preserve at least one known-good incumbent
   camera and lens, their configuration files, firmware, drivers, flat/dark
   calibrations, images, and production performance data.
#. **Compare controlled configurations.**  Change one component at a time
   before testing the proposed camera-lens pair.
#. **Use absolute and relative gates.**  The candidate must meet the
   application requirement and must not regress from the incumbent by more
   than a pre-approved non-inferiority margin.
#. **Qualify the production decision.**  Bench measurements diagnose the
   system; production parts, nuisance variation, and a pilot run decide
   release.

Do not choose acceptance limits after viewing candidate results.  A result
outside a pre-registered limit is a failure until a formal deviation or design
change is approved.  A waiver is not a pass.


Roles and controlled records
----------------------------

Assign these roles before the test starts:

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Role
     - Responsibility
   * - System owner
     - Owns the user requirement specification (URS), production risks, and
       final release decision.
   * - Vision engineer
     - Owns optical setup, camera configuration, algorithms, data reduction,
       and technical conclusions.
   * - Quality or metrology
     - Approves sampling, traceability, measurement-system analysis,
       uncertainty, deviations, and report completeness.
   * - Controls or IT
     - Approves drivers, network load, trigger I/O, timing, operating-system
       image, recovery, and cybersecurity constraints.
   * - Supplier
     - Supplies specifications, change notification, compliance evidence,
       lifecycle status, and traceable samples from representative lots.

The controlled test record shall include the URS revision, protocol revision,
test-script commit, raw-data checksum manifest, operator, date/time, serial and
lot numbers, equipment calibration status, environmental log, wiring diagram,
optical layout, software/firmware versions, every setting, deviations, and
approvals.


Define requirements and budgets
-------------------------------

Convert the production task into measurable critical-to-quality (CTQ)
requirements.  At minimum, record:

* object FOV and allowed coverage error in both axes;
* working-distance range, object-height range, and mechanical envelope;
* smallest defect, edge, code module, or dimensional increment that must be
  detected or measured;
* maximum permitted measurement bias and repeatability;
* required probability of detection, false-reject rate, false-accept rate,
  and confidence level by defect class;
* conveyor speed, motion direction, trigger rate, exposure-time ceiling,
  latency, and jitter limits;
* illumination geometry, wavelength or spectrum, polarization, strobe pulse,
  and allowed intensity drift;
* object colours, materials, gloss, texture, and nuisance variation;
* temperature, humidity, vibration, dust/liquid ingress, EMC, cable length,
  and duty cycle;
* required service life, availability horizon, change notification, and
  acceptable calibration or software changes.

Build an error budget for every reported production measurement.  Allocate
limits to calibration, distortion residual, pixel sampling, focus, part
pose, illumination, segmentation, thermal drift, and repeatability.  A
component limit is defensible only when it fits inside this system budget.

For a sensor pixel pitch :math:`p` and absolute transverse magnification
:math:`|m|`, object-space sampling is

.. math::

   s_{\mathrm{object}} = \frac{p}{|m|}

and object-space sensor Nyquist frequency is

.. math::

   f_{\mathrm{Nyq,object}} = \frac{|m|}{2p}.

Nyquist is an alias boundary, not a robustness target.  A practical
inspection normally needs more than two samples across its smallest feature.
Use the algorithm validation to set that number; three to five pixels across
a critical feature is a reasonable starting range, not a universal rule.


Baseline, samples, and comparison configurations
------------------------------------------------

Baseline selection
~~~~~~~~~~~~~~~~~~

Use a retained, stable production unit near the centre of the accepted
population as the **golden unit**.  Also retain historical distributions or
test representative incumbent units; a single unusually good golden unit can
create false failures, while a degraded unit can hide regression.

Before candidate testing:

#. Verify that the baseline still passes its current calibration and
   production reference set.
#. Export every camera feature and lens setting.
#. Archive unprocessed reference images and the exact application release.
#. Record the baseline mean, variation, and worst observed result for every
   CTQ metric.
#. Mark settings that are allowed to change during optimization.  Maintain
   separate results for ``drop-in`` and ``optimized`` configurations.

Minimum comparison matrix
~~~~~~~~~~~~~~~~~~~~~~~~~

Run all physically valid combinations:

.. list-table::
   :header-rows: 1
   :widths: 22 25 25 28

   * - Configuration
     - Camera
     - Lens
     - Purpose
   * - ``BB``
     - Baseline
     - Baseline
     - Golden end-to-end control.
   * - ``CB``
     - Candidate
     - Baseline
     - Primarily isolates camera and sampling changes.
   * - ``BC``
     - Baseline
     - Candidate
     - Primarily isolates lens changes.
   * - ``CC``
     - Candidate
     - Candidate
     - Qualifies the proposed production pair.

If sensor size, mount, or image circle makes a combination impossible, record
it as ``not physically compatible`` rather than silently omitting it.  Use a
calibrated reference camera or reference lens to preserve component isolation.

For a different pixel pitch or sensor format, perform two comparisons:

* **Drop-in geometry:** unchanged lens, working distance, aperture,
  illumination, exposure time, and camera processing.  This exposes the
  direct replacement effect.
* **Matched application geometry:** adjust only pre-approved parameters to
  restore the required object FOV and sampling.  This qualifies the proposed
  production recipe.

Do not resize candidate images to the baseline raster before component
analysis.  Report results in sensor micrometres, image pixels, object-space
units, and normalized FOV position as applicable.  Resampling is permitted
only as a separately identified application-pipeline test.

Sampling plan
~~~~~~~~~~~~~

Select sample counts from the consequence of failure and expected supplier
variation.  Unless the approved risk assessment specifies more:

* bench-test at least three cameras per model and five lenses per model;
* obtain candidate units from at least two manufacturing lots where possible;
* repeat each controlled acquisition sequence at least three times after
  independent remount/refocus for tests sensitive to alignment;
* randomize baseline/candidate order and re-run the baseline control at the
  end of the session;
* include at least 30 independent parts per important good/defect class for
  engineering screening;
* use the quality-approved sample size for claimed false-accept or
  false-reject rates; 30 images cannot substantiate a parts-per-million
  claim;
* run at least one full production shift or 10,000 cycles, whichever is more
  demanding, for the pilot unless a risk assessment sets a stronger gate.

These are screening minimums, not proof that a supplier population is
capable.  Use a lot-acceptance or tolerance-interval plan when lot-to-lot
variation is a release risk.


Common test setup and conditions
--------------------------------

Controlled optical bench
~~~~~~~~~~~~~~~~~~~~~~~~

Use a rigid rail or fixture with traceable translation and angular
adjustment.  Record distances from defined mechanical datums.  The standard
bench contains:

* a target plane normal to the optical axis, verified in both axes;
* a calibrated dimensional grid or dot target;
* a slanted-edge or appropriate resolution target with contrast and print
  resolution adequate for the test;
* a uniform source or integrating sphere large enough to overfill the FOV;
* a calibrated photodiode, radiometer, spectrometer, or lux meter appropriate
  to the spectral band;
* monochromatic or narrow-band sources spanning every production band;
* a colour target and spectrally characterized production illuminant for
  colour applications;
* a dark cap or light-tight enclosure;
* an oscilloscope or logic analyser for trigger, exposure-active, strobe, and
  data-ready timing;
* a temperature chamber or controlled hot/cold fixture when the environment
  is a CTQ.

The target shall be flatter and more accurate than the allocated measurement
budget.  Its active area must fill the required FOV, including corners.  Do
not infer lens performance from a low-resolution office print.

Default laboratory controls
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unless the URS requires other conditions, use these reproducibility controls:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Variable
     - Control
   * - Ambient
     - :math:`23 \pm 2\,^\circ\mathrm{C}` and 40--60 % RH; record actual
       values continuously for thermal tests.
   * - Warm-up
     - At least 30 minutes powered and acquiring, or until image mean and dark
       level change by less than 0.2 % over 10 minutes.
   * - Power
     - Regulated supply at nominal voltage; record voltage, current, ripple,
       grounding, and power at the camera connector.
   * - Illumination
     - Mechanically fixed; monitor intensity and source temperature.  Correct
       or repeat a sequence if reference intensity changes by more than 1 %.
   * - Alignment
     - Target tilt small enough that induced focus or scale change consumes
       less than 10 % of the relevant tolerance.
   * - Exposure
     - No clipping unless saturation is the test objective.  Use the same
       photon exposure for radiometric comparison and the same motion-safe
       exposure ceiling for application comparison.
   * - Processing
     - First acquire raw or least-processed linear data with auto exposure,
       auto gain, auto white balance, denoise, sharpening, gamma, compression,
       defect correction, lens shading, and geometric correction disabled.
       Test the approved production processing separately.
   * - Focus
     - Determine best focus by a documented sweep, not by visual judgement.
       Lock focus and aperture after setting them.
   * - Data format
     - Prefer lossless native bit depth.  Preserve packing, Bayer pattern,
       black level, channel order, endianness, and metadata.

When baseline and candidate cannot use identical exposure or gain, acquire
both an identical-settings sequence and a matched-signal sequence.  The first
reveals sensitivity differences; the second compares performance at the
production operating point.


Acceptance model
----------------

Pre-register every test in an acceptance matrix with these fields:

``ID``, ``criticality``, ``metric``, ``unit``, ``direction``, ``absolute
limit``, ``baseline value/distribution``, ``allowed regression``, ``method``,
``sample size``, ``uncertainty``, and ``owner``.

For a metric where lower is better, the candidate passes only if

.. math::

   x_C + U_C \leq L_{\mathrm{abs}}

and

.. math::

   (x_C-x_B)+U_\Delta \leq \Delta_{\mathrm{allowed}}.

For a metric where higher is better, it passes only if

.. math::

   x_C-U_C \geq L_{\mathrm{abs}}

and

.. math::

   (x_B-x_C)+U_\Delta \leq \Delta_{\mathrm{allowed}}.

Here :math:`U_C` is the approved guard band for candidate measurement
uncertainty and :math:`U_\Delta` is the guard band for the paired difference.
Use an approved confidence bound or expanded uncertainty consistently; do not
mix a worst-case limit with an unguarded mean.  When a metric has upper and
lower limits, apply both sides.

Recommended default relative gates, used only until risk-based margins are
approved, are:

* no more than 10 % regression for continuous non-critical image-quality
  metrics;
* no regression for safety-, compliance-, timing-, data-integrity-, or
  false-accept-critical metrics;
* every tested unit must meet hard compatibility and safety limits;
* no individual result may exceed an absolute CTQ limit even when the group
  mean passes.

A test item is ``PASS`` only when its setup validity checks, required sample
count, absolute gate, relative gate, repeatability gate, and required outputs
all pass.  Use only ``PASS``, ``FAIL``, ``BLOCKED``, or ``NOT APPLICABLE``.
``NOT APPLICABLE`` requires a written rationale and approval before execution.


Qualification stages and release gates
--------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 13 25 37 25

   * - Gate
     - Objective
     - Required evidence
     - Pass requirement
   * - G0
     - Feasibility and supply
     - URS, risk analysis, supplier lifecycle evidence, interface and
       mechanical review, approved protocol.
     - No unresolved incompatibility; all limits and samples approved before
       candidate measurements.
   * - G1
     - Component metrology
     - Completed :doc:`camera` and/or :doc:`lens` controlled tests, raw data,
       uncertainty, and component report.
     - Every critical item passes; no unresolved major failure.
   * - G2
     - Integrated imaging system
     - ``BB``, ``CB``, ``BC``, and ``CC`` comparisons where valid, calibrated
       system, and locked production recipe.
     - All end-to-end CTQs pass with the proposed pair.
   * - G3
     - Application validation
     - Blinded representative part set, edge cases, nuisance variation,
       measurement-system analysis, and failure review.
     - Pre-approved detection, false decision, bias, repeatability, and
       reproducibility limits all pass.
   * - G4
     - Pilot and release
     - Production-rate pilot, restart and fault recovery, environmental
       evidence, work instructions, spares, rollback plan, and approvals.
     - Zero critical event; all pilot metrics pass; configuration and
       traceability package released.

Qualification fails if any of these occurs:

* a critical item fails on any candidate unit;
* required evidence is missing or raw data cannot be traced to a unit and
  configuration;
* the candidate passes only after unapproved image manipulation or exclusion
  of valid adverse samples;
* the application false-accept, measurement, timing, or data-integrity limit
  fails;
* the production configuration differs from the qualified configuration;
* an unresolved interaction appears when both camera and lens are replaced.


Special diagnostic: apparent colour aberration after pixel-size change
-----------------------------------------------------------------------

A smaller pixel does not by itself create lens chromatic aberration.  It can
make existing lateral or axial chromatic error visible in more pixels, move
the lens-sensor system from undersampled to optically limited, and expose
differences in cover glass, microlenses, colour-filter array (CFA), spectral
response, demosaicing, sharpening, or registration.

For example, a fixed :math:`3\,\mu\mathrm{m}` colour displacement is 0.5 pixel
on a :math:`6\,\mu\mathrm{m}` sensor and 1 pixel on a
:math:`3\,\mu\mathrm{m}` sensor.  Reporting only pixels would make the same
optical error look twice as large; reporting only micrometres could hide an
algorithm-breaking one-pixel error.

Run this isolation experiment whenever pixel pitch, sensor family, cover
glass, CFA, lens, or illumination spectrum changes:

#. Capture the same high-contrast edge, dot grid, or pinhole with narrow-band
   sources near the short, centre, and long wavelengths used in production.
#. Keep lens, aperture, working distance, target, focus reference, and
   geometry fixed for ``BB`` and ``CB``.  Repeat ``BC`` and ``CC`` where
   possible.
#. Acquire raw mosaic or independent monochrome-band images before
   demosaicing and correction; then acquire the approved production pipeline.
#. Sweep focus at each wavelength.  Record best-focus position and
   tangential/sagittal MTF across the FOV.
#. Fit target geometry per band.  Separate global translation/rotation from
   field-dependent radial and tangential colour displacement.
#. Report channel displacement in sensor micrometres, candidate pixels,
   object-space units, and percentage of the local image height.
#. Repeat with a calibrated low-aberration reference lens.  If the candidate
   camera still shows displacement, investigate sensor stack/CFA/processing;
   if displacement follows the lens, investigate lateral or axial lens
   colour.

The default pass gate is **all** of the following:

* per-band MTF at the application frequency meets its absolute and relative
  limits at every qualified field point;
* residual colour displacement after the approved calibration is no greater
  than 25 % of the smallest object-space positional tolerance;
* residual displacement is no greater than 0.5 candidate pixel where the
  algorithm assumes channel registration;
* the best-focus spread across required wavelengths is no greater than 25 %
  of the usable application depth of field;
* production colour/defect decisions meet their application error limits;
* no metric regresses beyond its pre-approved baseline margin.

Replace the 25 % and 0.5-pixel starting limits if the error budget or algorithm
validation justifies different values.  Never accept a change solely because
the displacement in micrometres is unchanged; the new sampling and algorithm
may make it consequential.


Data package and expected outputs
---------------------------------

Store native raw data and derived data separately.  Never overwrite raw
captures.  The final qualification package shall contain:

* approved URS, risk assessment, protocol, acceptance matrix, and deviations;
* bill of materials and serial/lot mapping for every camera, lens, cable,
  filter, source, target, and fixture;
* complete feature-node/configuration exports, firmware, drivers, application
  version, operating-system image, and analysis-script commit;
* setup photographs, dimensioned optical layout, wiring/trigger diagram,
  target certificates, calibration certificates, and environmental logs;
* all dark, flat, spectral, geometric, resolution, timing, stress, and
  production images in native format with checksums;
* tidy tabular results with one row per unit, repeat, condition, FOV point,
  wavelength, and metric;
* uncertainty calculation, repeatability analysis, baseline/candidate paired
  plots, worst-case maps, and confidence or tolerance bounds;
* camera and lens reports, application confusion matrix or measurement-system
  analysis, pilot report, failure log, corrective actions, and signed decision;
* released production recipe, calibration files, work instructions,
  preventive-maintenance limits, incoming-inspection plan, spares strategy,
  and rollback plan.

At minimum, the executive results table shall have one row per test ID and
these columns:

.. code-block:: text

   Test ID | Criticality | Baseline | Candidate | Abs. limit | Rel. limit
   Guard band | Worst unit | Result | Evidence link | Deviation | Owner

The report conclusion shall be one of ``QUALIFIED``, ``NOT QUALIFIED``, or
``QUALIFIED WITH APPROVED DEVIATION``.  It shall identify the exact qualified
camera-lens-processing configuration; qualification does not automatically
transfer to another firmware, sensor revision, lens lot, filter, illumination,
or image-processing recipe.


Reference methods
-----------------

The methods below provide definitions and repeatable measurement procedures;
most do **not** supply application acceptance limits.  Use the currently
approved edition required by the organization:

* `EMVA 1288 Release 4.0
  <https://www.emva.org/standards-technology/emva-1288/>`_ for objective
  industrial camera characterization, including linear and general camera
  models.
* `ISO 12233:2024 <https://www.iso.org/standard/88626.html>`_ for digital
  camera resolution and spatial-frequency response.
* `ISO 9334:2012 <https://www.iso.org/standard/57563.html>`_ and
  `ISO 9335:2025 <https://www.iso.org/standard/85989.html>`_ for OTF
  terminology and measurement principles.
* `ISO 15529:2010
  <https://www.iso.org/standard/56069.html>`_ for MTF measurement of sampled
  imaging systems.
* `ISO 11421:2025 <https://www.iso.org/standard/85988.html>`_ for uncertainty
  evaluation in OTF/MTF measurements.
* `ISO 9039:2008 <https://www.iso.org/standard/50090.html>`_ for optical
  distortion.
* `ISO 13653:2019 <https://www.iso.org/standard/72597.html>`_ for measurement
  of relative irradiance in the image field.
* `ISO 19084:2015 <https://www.iso.org/standard/63894.html>`_ for chromatic
  displacement measurement.
* `ISO 17957:2015 <https://www.iso.org/standard/31974.html>`_ for luminance
  and colour shading measurement.
* `ISO 18844:2017 <https://www.iso.org/standard/63552.html>`_ for digital
  camera image-flare measurement.

Use calibrated equipment, target compensation, and the uncertainty practices
required by the selected method.  Stating that a test is "based on" a
standard is not a claim of compliance with that standard.
