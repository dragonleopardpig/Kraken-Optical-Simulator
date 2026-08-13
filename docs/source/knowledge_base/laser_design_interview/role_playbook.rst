Role-Specific Interview Playbook
================================

The job description is for a **laser systems, integration, and productization
engineer**.  It needs optical depth, but success is measured by whether a product
meets its requirements repeatedly—not by whether one heroic bench setup once
reached maximum power.  Prepare evidence that you can move from an ambiguous
market need to a controlled design, qualified test result, and transferable
operating procedure.

What the interview panel is likely to score
-------------------------------------------

.. list-table:: Job-description evidence map
   :header-rows: 1
   :widths: 23 28 30 19

   * - Hiring signal
     - Likely probe
     - Strong evidence
     - Prepare this
   * - Requirements and budgets
     - ``How did you convert a customer need into subsystem specifications?``
     - Traceable, measurable requirements; sensitivity/error budgets; margin; verification ownership
     - One numerical allocation example
   * - Bench feasibility
     - ``How did you retire the largest technical risk cheaply and early?``
     - Hypothesis, minimal experiment, controls, calibrated data, exit criterion, design decision
     - One prototype that changed the design
   * - Laser integration
     - ``Walk me through first light, alignment, and power scaling.``
     - Safe sequence, datums, known-good references, causal optimization, recorded baselines
     - One alignment/debug story
   * - Diagnostics
     - ``Output is low or unstable—what do you do?``
     - Fault tree, time-correlated channels, discriminating tests, one-variable changes
     - One difficult root-cause analysis
   * - Opto-mechanics and motion
     - ``Is this drift optical, thermal, mechanical, or control-related?``
     - Repeatability/backlash/settling tests, modal or thermal evidence, interface ownership
     - One motion or stability investigation
   * - Qualification and code
     - ``How would you build an automated acceptance bench?``
     - Measurement uncertainty, state machine, metadata, raw-data retention, analysis review
     - One Python/MATLAB/LabVIEW example
   * - Development execution
     - ``How did you keep a project accurate and on schedule?``
     - Risk register, interface control, review gates, decision log, verification matrix
     - One end-to-end project
   * - Product introduction
     - ``How did you transfer a design to operations or field service?``
     - Validated work instructions, training, fault isolation, configuration control, yield feedback
     - One transfer/training example
   * - Communication
     - ``Explain the same issue to management and to a supplier.``
     - Decision-ready summary for management; reproducible evidence and acceptance language for vendors
     - One concise status slide/story

Requirements allocation that survives verification
---------------------------------------------------

Start with the use case and define critical-to-quality outcomes.  Convert each
into a requirement with a metric, operating conditions, limit, population or
time statistic, measurement method, and uncertainty/guard-band rule.  Then
allocate it to the physical contributors and owners.

A reusable hierarchy is:

.. code-block:: text

   Market need
   └─ system performance requirement and use conditions
      ├─ laser source allocation
      ├─ beam delivery / opto-mechanical allocation
      ├─ motion and control allocation
      ├─ environment / utility allocation
      └─ measurement uncertainty and product margin

For a response :math:`y=f(\mathbf{x})`, first-order uncertainty or variation is

.. math::
   :label: interview-system-budget

   \sigma_y^2 \simeq
   \mathbf{J}\,\boldsymbol{\Sigma}_x\,\mathbf{J}^{\mathsf T},
   \qquad
   J_i=\left.\frac{\partial f}{\partial x_i}\right|_{\mathbf{x}_0}.

Use root-sum-square only when the contributors and distribution assumptions
justify it.  Retain covariance when drivers are correlated; use worst-case
limits for safety or hard-stop interfaces; use Monte Carlo or a higher-fidelity
model when the response is nonlinear or bounded.  Separate predicted product
variation from measurement uncertainty so a weak gauge is not mistaken for a
weak product.

As a whiteboard example, suppose delivered pointing must be no greater than
30 µrad RMS over a declared time band and operating condition.  Illustrative
independent allocations of 15 µrad to the source, 10 µrad to opto-mechanics,
8 µrad to motion, 6 µrad to environment, and 5 µrad to controls give

.. math::

   \sigma_{\rm product}=\sqrt{15^2+10^2+8^2+6^2+5^2}
   \simeq21.2\ \mu\mathrm{rad}.

That leaves model/product margin, but acceptance also needs a separate decision
rule for measurement uncertainty.  The useful interview move is not the
particular allocation; it is asking about time bandwidth, axes, operating state,
correlation, tails, measurement uncertainty, and how each contributor will be
verified.

Example allocation questions for a DUV laser product include:

* Which source terms set dose stability: pulse energy, repetition rate, pulse
  width, spectrum, pointing, profile, polarization, trigger jitter, and warm-up?
* How much beam-position error belongs to source pointing, mount drift, motion
  repeatability, sensor noise, calibration, and environment?
* Which losses and ageing terms set delivered power at end of life rather than
  on the first day?
* What is the permitted recovery time after startup, service, interruption, or
  fault?
* Which subsystem verifies each allocation, at what interface and configuration?

End with a requirements-verification matrix.  Every requirement needs an owner,
method (test, analysis, inspection, or demonstration), configuration, procedure,
instrument, data product, acceptance rule, and closure status.

Bench concepts should retire a named risk
-----------------------------------------

A feasibility bench should answer a decision, not become an undocumented early
product.  Present your prototype work with this structure:

1. **Risk statement:** cause, uncertain event, and performance/schedule impact.
2. **Hypotheses:** leading mechanisms and observations each predicts.
3. **Minimum bench:** only the hardware and controls needed to distinguish them.
4. **Measurement model:** calibration, references, uncertainty, nuisance
   variables, and sample size.
5. **Exit criterion:** numerical pass/fail or decision boundary agreed before
   seeing the result.
6. **Result:** raw evidence, uncertainty, mismatch with prediction, and anomaly
   disposition.
7. **Design action:** architecture, tolerance, supplier, control, or test change.
8. **Reusable artifacts:** data, code, schematic, bill of materials, procedure,
   risks closed/opened, and recommended next experiment.

When schedule is tight, reduce experimental scope rather than removing controls.
A fast test with no stable reference, configuration record, or decision rule can
create false confidence and cost more time later.

Designing a laser qualification bench
-------------------------------------

A credible bench contains these layers:

.. list-table:: Qualification-bench architecture
   :header-rows: 1
   :widths: 22 39 39

   * - Layer
     - Design questions
     - Evidence before release
   * - Device interface
     - Are mechanical datums, purge/cooling, electrical, timing, software, and beam boundaries controlled?
     - Interface drawing, mating check, safe connect/disconnect sequence
   * - Metrology
     - Do instruments cover wavelength, bandwidth, dynamic range, aperture, sampling rate, and exposure?
     - Calibration status, traceability, uncertainty budget, linearity/range check
   * - Reference channel
     - Can source drift be separated from DUT or measurement drift?
     - Stable pickoff/reference ratio and drift study
   * - Fixturing and motion
     - Is seating deterministic? Are homing, backlash, settling, and cable forces acceptable?
     - Repeatability study after unload/reload, home, and representative moves
   * - Environment
     - Are temperature, humidity, vibration, airflow, purge chemistry, and cleanliness measured?
     - Limits, logged sensors, alarms, and correlation with output
   * - Safety and faults
     - What happens on lost cooling, purge, communication, motion limit, or interlock?
     - Safe-state verification and controlled fault injection
   * - Automation and data
     - Can interrupted tests recover without losing configuration or provenance?
     - Versioned recipe/code, raw data, metadata, audit trail, deterministic report
   * - Measurement-system analysis
     - Is observed variation product, operator, fixture, day, or gauge?
     - Repeatability/reproducibility, golden artifact, correlation or round-robin study

Perform a dry run, known-good-unit run, known-bad or injected-fault run, repeated
load/unload run, and an independent review of the analysis before the bench makes
product decisions.  A test should fail safely and explain why it failed.

Automation that sounds like product engineering
-----------------------------------------------

In a programming discussion, describe architecture and data integrity before
plot aesthetics.  A useful acquisition flow is a state machine:

.. code-block:: text

   SAFE → INITIALIZE → VERIFY UTILITIES → HOME → BASELINE
        → APPLY TEST POINT → WAIT FOR SETTLE → ACQUIRE
        → VALIDATE RANGE → SAVE RAW + METADATA → ANALYZE
        → PASS / FAIL / RETRY-UNDER-RULE → SAFE

The implementation should always return the hardware to a safe state, enforce
limits independently of the analysis, timestamp channels from a common clock,
retain raw data, and record unit/fixture/instrument IDs, calibration versions,
software commit, recipe, environment, operator, and exceptions.

Be ready to explain where each tool fits:

* **Python:** instrument orchestration, image/time-series processing, automated
  reports, regression tests, and reproducible analysis with NumPy/SciPy/pandas.
* **MATLAB:** modeling, signal/image analysis, controls, rapid engineering
  algorithms, and comparison with Python production implementations.
* **LabVIEW:** deterministic equipment integration, hardware timing, interlocks,
  and operator-facing test applications.
* **JMP:** designed experiments, regression, capability, measurement-system
  studies, yield/lot analysis, and communicating statistical evidence.

For images, retain unsaturated raw frames and background/reference frames; state
the centroid, width, window, threshold, and bad-pixel rules.  For time series,
look beyond mean and standard deviation: warm-up, drift, steps, periodic content,
cross-correlation, outliers, missing samples, and state-dependent behavior often
contain the root cause.

Opto-mechanics and motion-control diagnostics
---------------------------------------------

.. list-table:: Motion symptom to discriminating test
   :header-rows: 1
   :widths: 26 37 37

   * - Symptom
     - Leading causes
     - Discriminating test
   * - Position depends on approach direction
     - Backlash, hysteresis, preload or cable force
     - Command identical targets from both directions; compare encoder and optical result
   * - Home is not repeatable
     - Sensor threshold/noise, index logic, hard-stop compliance, thermal drift
     - Repeat home cycles from varied starting points and temperatures
   * - Encoder settles but beam continues moving
     - Structural creep, mount relaxation, optic temperature, adhesive or cable load
     - Log encoder, beam centroid, temperatures, and time after a common move
   * - Oscillation follows a move
     - Servo tuning, structural resonance, loose interface, floor/acoustic excitation
     - Compare command/encoder/error and optical signal; vary move profile and measure frequency
   * - Good open-loop alignment, poor closed-loop stability
     - Sensor noise, loop bandwidth, latency, quantization, cross-axis coupling
     - Inject small disturbances and measure transfer/step response by axis
   * - Unit changes after transport or service
     - Datum/seating error, fastener preload, contamination, connector or cable routing
     - Controlled remove/reinstall study using independent mechanical and optical references

Always distinguish commanded position, encoder position, physical optic pose,
and optical beam result.  They are different observables.  Check Abbe offset,
cosine error, axis orthogonality, pivot location, bearing runout, limit behavior,
settling criterion, thermal expansion, vibration modes, and cable management.

Development-cycle and risk evidence
-----------------------------------

Show how your deliverables changed at each gate:

.. list-table:: Development gate and completion evidence
   :header-rows: 1
   :widths: 21 44 35

   * - Gate
     - Core work product
     - Exit evidence
   * - Concept
     - Use cases, measurable requirements, architecture options, feasibility risks
     - Selected concept and risk-retirement plan
   * - Design
     - Budgets, models, interfaces, tolerances, safety, FMEA, verification plan
     - Review actions closed; margins and owners visible
   * - Prototype
     - Controlled build, bring-up, baseline, model correlation, anomaly log
     - Critical risks retired or quantified
   * - Integration
     - Interface verification, configuration control, fault isolation, regression tests
     - System requirements demonstrated in representative configuration
   * - Qualification
     - Environmental/lifetime test, uncertainty, statistics, nonconformance disposition
     - Approved objective evidence, not a hand-selected trace
   * - Product introduction
     - Released drawings/BOM/code, work instructions, fixtures, training, service diagnostics
     - Repeatable build/test yield and owned feedback loop

Use a live risk register with cause-event-impact statements, likelihood/severity,
mitigation, owner, due date, retirement evidence, and residual risk.  FMEA helps
enumerate failures; a fault tree helps reason backward from a top event; neither
replaces a physical test of the dominant uncertainty.

Product introduction is part of the design
------------------------------------------

A transferable procedure should contain purpose/scope, hazards and safe state,
prerequisites, controlled tools and calibrations, configuration, datums, numbered
actions, expected observation and limit at each step, hold points, data capture,
fault recovery, escalation, sign-off, and revision history.  Validate it with a
trained but nonexpert user.  If the author must stand beside every operator, the
procedure is not yet complete.

Train operations and field teams at three levels:

* **concept:** what the subsystem does and which variables matter;
* **execution:** safe setup, normal sequence, acceptance limits, and evidence;
* **diagnostics:** symptom tree, known-good checks, replace/adjust boundaries,
  configuration capture, and escalation package.

Track first-pass yield, retest and adjustment frequency, failure pareto, cycle
time, false-fail/escape evidence, field recurrence, and procedure deviations.
Use those data to change the product, fixture, limits, training, or supplier
control rather than treating every deviation as operator error.

Communication at three altitudes
--------------------------------

**Executive update:** requirement/status in one line, performance versus target,
top risks with evidence/owner/date, schedule or customer impact, recovery plan,
and the decision or resource needed.  Lead with outcome and uncertainty.

**Cross-functional technical review:** interface, model and assumptions, test
configuration, data and uncertainty, anomaly hypotheses, action owners, and
decision log.  Define terms so optical, mechanical, electrical, controls, and
operations teams use the same observable and coordinate system.

**Vendor discussion:** drawing/spec revision, lot and configuration, exact test
method and raw evidence, observed versus required result, containment, requested
root-cause/corrective-action response, and acceptance of the next lot.  Separate
facts, inference, and requested action.

Prepare six evidence stories
----------------------------

Have a two-minute and a five-minute version of each:

1. turning a vague need into a numerical requirement and budget;
2. using a small bench experiment to retire or expose a major risk;
3. aligning or integrating an optical system safely and repeatably;
4. isolating a difficult optical/mechanical/control root cause with data;
5. automating a measurement and proving the result was trustworthy; and
6. transferring a design/procedure to another team or resolving a supplier issue.

For each, state your individual decision, a number before and after, the failed
hypothesis or surprise, and what artifact prevented recurrence.  Do not invent
direct DUV experience.  If your closest example is another wavelength or optical
system, name the gap and explain the transferable method plus the DUV-specific
controls in :doc:`duv_integration`.

Questions worth asking the interviewers
---------------------------------------

* Which DUV architecture and wavelength are in scope: excimer, frequency-
  converted solid state, or integration of a supplied source?
* What are the dominant current gaps: performance, stability, lifetime, yield,
  test capacity, supplier variation, or field recovery?
* Where does this role own architecture versus integration, qualification, and
  product sustaining?
* Which system metrics drive customer value, and which subsystem budgets are
  currently hardest to close?
* What does a successful first six months deliver—prototype evidence, a released
  design, a qualification bench, or an operations/field transfer?
* How are raw test data, software versions, calibration, and product
  configuration linked today?

Last 24-hour preparation checklist
----------------------------------

* Write a 90-second introduction that connects your engineering/physics
  foundation, hands-on optical work, system ownership, data/code capability, and
  reason for wanting this integration/product role.
* Put one numerical result, one surprise, and one recurrence-prevention artifact
  into each of the six evidence stories above.
* Draw the requirement hierarchy, 30-µrad pointing budget, qualification-bench
  block diagram, automation state machine, and DUV architecture fork without
  notes.
* Rehearse the first-light/power-scaling sequence and three diagnostic answers:
  low output, slow drift, and motion-dependent pointing.
* Prepare an honest statement of your direct DUV experience and the transferable
  evidence behind it; do not memorize experience you do not have.
* Choose four questions from the list above based on who is interviewing you:
  optical specialist, systems lead, operations/NPI partner, or manager.
