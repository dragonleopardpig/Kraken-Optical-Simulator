Active Fiber Alignment: Power, Dither, and Spatial Sensing
==========================================================

Active alignment adjusts the relative position and angle of a beam and a
fiber to maximize useful guided power. A practical starting point is a
calibrated power measurement, a bounded search to find first light, and
small controlled perturbations to optimize coupling. Cameras can accelerate
acquisition when they observe the incident beam relative to the fiber.

The central design question is **which measurement contains a repeatable,
signed signature of the error being corrected?** A clean single-mode fiber
(SMF) output usually retains coupling amplitude but loses the spatial
signature of the launch error. Mechanical dithering supplies direction by
measuring how power responds to known motion; spatial sensing supplies it
only when the optical measurement preserves the relevant information.

.. note::

   This is an engineering design and feasibility guide, developed from the
   supplied active-alignment notes. The control loops and bench arrangements
   are proposals, not an implemented KrakenOS hardware-control feature.
   Numerical examples are analytical illustrations, not measured performance.

.. contents:: On this page
   :local:
   :depth: 2


1. Define the quantity to maximize
----------------------------------

For a scalar field with fixed polarization, the fraction coupled into a
normalized guided spatial mode follows the field-overlap integral:

.. math::
   :label: active-fiber-overlap

   \eta =
   \frac{\left|\iint E_{\rm in}(x,y)u_{01}^{*}(x,y)\,dx\,dy\right|^2}
   {\left(\iint |E_{\rm in}|^2\,dx\,dy\right)
    \left(\iint |u_{01}|^2\,dx\,dy\right)}.

Both fields must be evaluated at the same plane. Position, angle, waist
size, curvature, and aberrations can all reduce overlap. Core diameter and
numerical aperture alone do not determine SMF coupling; Newport's
`Fiber Optic Coupling <https://www.newport.com/n/fiber-optic-coupling>`_
explains this distinction between ray acceptance and mode matching.

For equal circular Gaussian modes with coincident waist planes, common
radius :math:`w`, lateral offset :math:`(\Delta x,\Delta y)`, and small
relative angles :math:`(\theta_x,\theta_y)`, the overlap reduces to

.. math::
   :label: active-fiber-gaussian

   \frac{\eta}{\eta_0} =
   \exp\!\left[-\frac{\Delta x^2+\Delta y^2}{w^2}
   -\frac{(kw)^2}{4}(\theta_x^2+\theta_y^2)\right].

Here :math:`w` is the **intensity** :math:`1/e^2` radius, approximately half
the mode-field diameter, :math:`k=2\pi n/\lambda_0` is the wave number in
the incident medium, and angles are in radians in that medium. The factor
:math:`\eta_0` is unity for the ideal overlap definition above. When
:math:`\eta` denotes measured efficiency instead, :math:`\eta_0` can
include fixed transmission losses at perfect mode matching.
Waist-size mismatch, defocus, polarization mismatch, and clipping require
additional modeling. Mechanical stage angles need not equal optical angles
at the facet; the intervening optics and rotation pivot set that mapping.

For a pure lateral displacement :math:`\delta`, substituting
:math:`u\propto\exp[-(x^2+y^2)/w^2]` in the overlap integral gives a
normalized amplitude overlap :math:`\exp[-\delta^2/(2w^2)]`. Squaring it
gives :math:`\eta/\eta_0=\exp[-\delta^2/w^2]`.

**Example.** With :math:`w=2.5\,\mu\mathrm{m}` and a lateral error of
:math:`1.0\,\mu\mathrm{m}`, the retained coupling is
:math:`\exp[-(1/2.5)^2]=0.852`, or 85.2%. This is an overlap calculation,
not the local intensity sampled at the center of the displaced Gaussian.

For the bench objective, use a dark-corrected, source-normalized signal:

.. math::

   F(\mathbf q)=
   C\frac{V_{\rm out}(\mathbf q)-V_{\rm out,dark}}
          {V_{\rm ref}-V_{\rm ref,dark}},
   \qquad
   \mathbf q=(x,y,z,\theta_x,\theta_y)^T.

The reference detector samples incident power before coupling. The constant
:math:`C` converts detector gains and tap ratios; absolute coupling
efficiency additionally requires a loss budget between the chosen input
and output reference planes. Reject data when the reference signal is too
small, either detector saturates, or a commanded step has not settled.

**A photodiode is authoritative only for the light delivered to it.** If it
collects core, cladding, and stray light, it measures their sum. Validate a
measurement path that suppresses unwanted light without introducing
position-dependent clipping or uncontrolled loss of the desired mode.
Record polarization sensitivity and fixed downstream losses. For
polarization-maintaining fiber, roll and polarization extinction may be
additional alignment requirements beyond the five coordinates above.


2. What a clean SMF output can and cannot reveal
------------------------------------------------

At a wavelength where only the fundamental spatial mode is guided, and
after unwanted light has been removed, write

.. math::

   E_{\rm out}(x,y)=a(\mathbf q)u_{01}(x,y),
   \qquad
   I_{\rm out}(x,y)=|a(\mathbf q)|^2|u_{01}(x,y)|^2.

For fixed output optics and a stable fiber, the normalized image is

.. math::

   I_N(x,y)=\frac{I_{\rm out}(x,y)}{\iint I_{\rm out}\,dx\,dy}
           =\frac{|u_{01}(x,y)|^2}{\iint |u_{01}|^2\,dx\,dy}.

Its spatial shape contains no dependence on :math:`a`. An offset launch
can therefore produce the same Gaussian-looking output at lower power.
Opposite offsets can produce equal power as well as equal normalized
images. An intensity camera cannot identify the sign from that observation.

.. figure:: /_static/knowledge_base/active_fiber_alignment/clean_mode_invariance.svg
   :alt: Misaligned and aligned launches produce the same normalized guided-mode profile, with different output power.
   :width: 100%

   For an ideal clean guided output, launch alignment changes amplitude.
   The normalized spatial profile does not supply a correction direction.

Splitting this clean output between a near-field camera and a far-field
camera does not recover the lost information: both images still scale
with :math:`|a|^2`. Their centroids may reveal motion of the output fixture
or collection optics, which must not be mistaken for input-coupling error.
Polarization changes, cladding modes, and parasitic interference can break
this ideal picture, but are not automatically reliable alignment signals.


3. Choose an observable before choosing an algorithm
----------------------------------------------------

.. list-table:: Measurement choices
   :header-rows: 1
   :widths: 26 34 40

   * - Measurement
     - Useful information
     - Limitation or prerequisite
   * - Clean output power, one sample
     - Value of the coupling objective
     - No unique correction direction from one scalar sample
   * - Output power during known perturbations
     - Local slope along the perturbed coordinates
     - Requires signal, motion, settling or phase calibration, and averaging
   * - Clean output intensity image
     - Power, output-mode quality, output-fixture diagnostics
     - Normalized shape usually carries no launch-error direction
   * - Incident near- and far-field images
     - Beam position and angle relative to calibrated references
     - Reference must represent the receiving fiber, not just the camera
   * - Residual or cladding-light image
     - Possible extra signatures of launch error
     - Experimental channel; information may vanish or change with routing
   * - Input-facet reflection or scatter
     - Possible beam/facet registration or focus cues
     - Depends on return geometry, coating, facet angle, and ghost rejection
   * - Pre-fiber wavefront sensor
     - Phase slope, curvature, and aberrations in a sampled plane
     - Needs amplitude/position information and a fiber-referenced target

A scalar detector does not force an optimizer to take blind random steps.
Finite differences, fitted scans, and synchronous dithering all extract
direction from **multiple measurements under known excitation**. The
appropriate comparison is acquisition time and final coupling under the
same starting errors and noise, rather than sensor dimensionality alone.


4. Obtain a signed gradient by mechanical dithering
---------------------------------------------------

Circular dither
~~~~~~~~~~~~~~~

Around a slowly varying center :math:`(x_0,y_0)`, command a small circle:

.. math::

   x(t)=x_0+a\cos\omega t,\qquad
   y(t)=y_0+a\sin\omega t.

Here :math:`a` is the actual motion amplitude in calibrated alignment
coordinates, not necessarily the commanded actuator amplitude. To first
order, with all other coordinates fixed,

.. math::

   F(t)\simeq F_0+aF_x\cos\omega t+aF_y\sin\omega t,
   \qquad
   F_x=\frac{\partial F}{\partial x},\quad
   F_y=\frac{\partial F}{\partial y}.

Average over an integer number of settled cycles, denoting the average
by :math:`\langle\cdot\rangle`:

.. math::
   :label: active-fiber-lockin

   \widehat F_x=\frac{2}{a}\langle F(t)\cos\omega t\rangle,
   \qquad
   \widehat F_y=\frac{2}{a}\langle F(t)\sin\omega t\rangle.

The signed quadratures estimate the local gradient. Their angle,
:math:`\operatorname{atan2}(\widehat F_y,\widehat F_x)`, gives the
steepest-ascent direction in the calibrated coordinates. Their magnitude
is a slope, not a distance to the optimum. A bounded update such as
:math:`\Delta\mathbf q_{xy}=G\widehat{\nabla F}` needs a gain matrix
:math:`G` with the appropriate units and stable loop dynamics.

PI describes circular probing and gradient-search alignment in
`Practical Examples of Parallel Alignment Automation
<https://www.pi-usa.us/fileadmin/user_upload/pi_us/files/technotes_whitepapers/PI-WP4010E-Practical-Examples-of-Parallel-Alignment-Automation.pdf>`_.
The expansion here makes the small-signal assumptions explicit. It does
not promise an instantaneous estimate, a global optimum, or convergence
in one move.

What happens at twice the dither frequency?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keeping the second-order terms gives

.. math::
   :label: active-fiber-second-harmonic

   F(t)\simeq F_0
   +a(F_x\cos\omega t+F_y\sin\omega t)
   +\frac{a^2}{4}(F_{xx}+F_{yy})
   +\frac{a^2}{4}(F_{xx}-F_{yy})\cos 2\omega t
   +\frac{a^2}{2}F_{xy}\sin 2\omega t.

At the center of a radially symmetric peak,
:math:`F_x=F_y=0`, :math:`F_{xx}=F_{yy}`, and :math:`F_{xy}=0`.
Consequently, an ideal circular dither has **no fundamental or second
harmonic** there. For a radial Gaussian, every point on the circle has
the same power, so this statement is exact for any circle radius within
that model.

In contrast, a **one-axis sinusoidal** dither
:math:`x=x_0+a\cos\omega t` at a stationary point produces
:math:`a^2F_{xx}(1+\cos 2\omega t)/4` to second order. An elliptical
trajectory or unequal transverse curvatures can also produce a second
harmonic. Thus, :math:`2f` is not a universal signature of perfect
two-axis alignment.

A vanishing fundamental alone is insufficient: there may be no light,
detector saturation, a stationary minimum, or an unobserved error in
another axis. Require an adequate DC signal and check that small nearby
perturbations reduce the objective before declaring a maximum.

Amplitude, frequency, and practical limits
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Select amplitude from the measured mode width, signal-to-noise ratio, and
allowed power modulation. At the center of
:math:`F=F_{\max}\exp[-(x^2+y^2)/w^2]`, circular dithering retains

.. math::

   \frac{F_{\rm dither}}{F_{\max}}=\exp[-a^2/w^2].

For :math:`w=2.5\,\mu\mathrm{m}` and :math:`a=50\,\mathrm{nm}`, this
is 99.960%, a 0.040% penalty. A small penalty does not establish that the
modulation is measurable on a particular instrument.

Choose frequency from the **loaded** stage transfer function, detector
bandwidth, sampling rate, and total latency. Measure the actual amplitude
and phase of both axes; compensate phase lag and cross-axis motion before
interpreting the quadratures. Sample well above the frequencies being
demodulated and filter against aliasing. Average long enough to resolve
the signal while keeping the center nearly stationary during estimation.
There is no universal nanometer amplitude or frequency range that fits
all piezo stages, stepper stages, payloads, and detector gains.

When smooth periodic motion is unavailable, use settled central
differences instead:

.. math::

   \widehat F_j =
   \frac{F(\mathbf q+h_j\mathbf e_j)-F(\mathbf q-h_j\mathbf e_j)}{2h_j}.

Here :math:`\mathbf e_j` is a unit vector along stage coordinate
:math:`j`. Pair measurements closely in time, normalize source power,
and account for backlash. Extend to focus and angular coordinates
sequentially, or use separable dither frequencies only after checking
harmonic overlap and mechanical coupling. Dither is a local tracking
method: a bounded coarse scan is still needed when there is no measurable
first light.


5. Place spatial sensors where information survives
---------------------------------------------------

Incident near field and far field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tap the incident beam before the fiber. Relay a plane conjugate to the
input facet onto one camera and a calibrated Fourier plane onto another.
In an ideal uncoupled paraxial arrangement,

.. math::

   \Delta x_{\rm image}=M\Delta x_{\rm facet},\qquad
   \Delta x_{\rm Fourier}\simeq f_{\rm F}\Delta\theta_x,

with analogous equations for :math:`y`. Here :math:`M` is signed
magnification and :math:`f_{\rm F}` is the effective Fourier-plane focal
length. General relays mix position and angle, so calibrate their full
response rather than assuming these two ideal equations.

The reference must be tied to the receiving fiber. Options include an
illuminated facet image, a removable reference target, or a suitable
back-launched guided mode. If the fiber moves while a pre-fiber camera
sees only the stationary incident beam, that camera alone cannot detect
the resulting relative error. Two centroid measurements can constrain
four transverse coordinates; focus generally needs extra information,
such as curvature or a scan. A single waist-size image does not usually
distinguish positive from negative defocus.

Residual and cladding-light imaging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Imaging a wider region of the output facet may reveal light outside the
desired guided mode. For a dark-corrected residual region, possible
features are

.. math::

   S_x=\frac{P_R-P_L}{P_R+P_L},\qquad
   S_y=\frac{P_T-P_B}{P_T+P_B}.

Only use them above a defined denominator/noise threshold. The relations
:math:`S_x\propto\Delta x` and :math:`S_y\propto\Delta y` are hypotheses
to test, not general fiber laws. Radiation can leave near the launch end;
cladding light can be attenuated by coating, bends, length, and stripping.
Interference may scramble an apparent sign when the fiber is rerouted.
The guided fundamental mode itself extends into the cladding; that
ordinary mode tail is not a separate cladding-mode error channel.
Even a camera region centered on the core does not guarantee that only
the guided core mode contributes to its pixels.

Keep this exploratory channel separate from the validated guided-power
objective. Clamp the output fixture and collection optics during input
scans so that image motion does not simply report mechanical motion at
the far end. Repeat calibration after realistic routing and temperature
changes before considering production feedback.

Facet reflection and wavefront sensing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An input-side return path can image the facet, reflected spot, or scatter
when the far end is inaccessible. Its usefulness depends on facet angle,
anti-reflection coating, core visibility, and separation of unwanted
reflections. Specular reflection from a uniform flat facet alone does not
identify the core center. Treat any inferred coupling metric as a proxy
until checked against actual guided transmission on a representative setup.

A Shack--Hartmann sensor measures local wavefront slopes from lenslet-spot
displacements; see Thorlabs' `Adaptive Optics technical whitepaper
<https://media.thorlabs.com/globalassets/family-pages/sharedassets/a/ao/ao_101_white_paper.pdf>`_.
It can help measure tilt, curvature, and aberration of the incident beam.
However, translating a collimated flat-wavefront beam need not tilt its
wavefront. Lateral registration requires an intensity centroid or another
position reference. The target is the field matched to the fiber after
propagation through the coupling optics; making an arbitrary sampled
wavefront flat is not by itself a coupling optimum.


6. Calibrate a multi-axis spatial controller
--------------------------------------------

Let :math:`\mathbf s` contain image features such as registered centroids,
wavefront curvature, or validated residual asymmetries. Record the target
:math:`\mathbf s_*` at an independently verified coupling maximum and
define :math:`\mathbf e=\mathbf s-\mathbf s_*`. Near that point,

.. math::

   \Delta\mathbf s\simeq J\Delta\mathbf q,
   \qquad
   J_{ij}\simeq
   \frac{s_i(\mathbf q_*+h_j\mathbf e_j)
        -s_i(\mathbf q_*-h_j\mathbf e_j)}{2h_j}.

The ideal local correction is :math:`\Delta\mathbf q=-\gamma J^+\mathbf e`,
where :math:`0<\gamma\leq1` damps the step. The minus sign follows from
the stated error convention. More features do not guarantee independent
information: two physically different errors can produce the same image.

Before inverting, scale coordinates and account for feature noise. With
diagonal coordinate scales :math:`Q`, measured feature covariance
:math:`C_s`, and a regularized inverse square root of that covariance,
define

.. math::

   A=C_s^{-1/2}JQ,\qquad
   \mathbf r=C_s^{-1/2}\mathbf e,

   \Delta\mathbf q=
   -\gamma Q(A^TA+\lambda^2 I)^{-1}A^T\mathbf r.

Inspect the singular values of :math:`A`. Recovering all five coordinates
requires five sufficiently strong independent responses; regularization
cannot create a missing measurement. Retain only supported directions,
bound each move to the validated calibration region, remeasure, and
accept a step only when the guided-power check supports it. A calibrated
camera loop can then hand over to fine power optimization.

Image regression or machine learning should face the same observability
test. Split validation by fiber/assembly and session, not just adjacent
frames from one scan. Include unseen combined-axis offsets and routing
conditions, compare against the local Jacobian baseline, and fall back to
power search outside the validated range. A model cannot recover a sign
that ideal single-mode propagation has physically removed.


7. A practical architecture and operating sequence
--------------------------------------------------

.. figure:: /_static/knowledge_base/active_fiber_alignment/architecture.svg
   :alt: Incident-beam sensing and a validated guided-power detector provide separate feedback to an alignment controller; residual imaging is an optional experimental channel.
   :width: 100%

   Proposed measurement architecture. Spatial references must be registered
   to the fiber, and the main power channel must reject unwanted light.

Start with the guided-power channel and add spatial sensing when its
measured acquisition benefit justifies the extra calibration.

1. **Establish references.** Set wavelength, polarization, mode-field size,
   facet plane, detector gains, input-power reference, and stage limits.
   Establish approximate mode matching before a fine position search.
2. **Find first light.** Use facet/beam registration or a bounded raster or
   spiral scan. Set a detection threshold above measured dark/background
   fluctuations. A flat noise floor is not an alignment maximum.
3. **Optimize locally.** Use fitted scans, central differences, or dither
   on the available axes. Revisit lateral alignment after focus or angle
   moves because real mechanisms couple these motions.
4. **Validate the peak.** Check neighboring points, adequate guided power,
   detector linearity, and repeatability. Reduce or stop dither and measure
   the stationary result separately from the modulated average.
5. **Verify the finished assembly.** Recheck after locking, adhesive cure,
   fixture release, and a specified settling interval. Log retained
   coupling and polarization performance where applicable.
6. **Track or reacquire.** For continuous operation, limit tracking motion
   and trigger reacquisition when signal or confidence is lost. Avoid
   integrating noise into unlimited stage travel.


8. Feasibility experiment and acceptance criteria
-------------------------------------------------

Test the sensor before developing a complex controller. Record the fiber
type, wavelength, length, routing, stripping arrangement, optics, stage
pivot, detector bandwidths, camera exposure, and coordinate signs.

1. Find a reproducible power maximum and estimate the coupling width of
   each movable axis. Select perturbations from those widths and the
   actual stage resolution; label all scan ranges and units.
2. Record repeated stationary samples to estimate feature covariance,
   power noise, and drift. Fix exposure and gain, subtract background,
   avoid saturation, and keep raw images as well as normalized images.
3. Scan positive and negative offsets about the optimum. Randomize scan
   order, revisit the center, and repeat in both motion directions to
   expose drift and backlash. Collect settled timestamps, actual stage
   positions, reference power, and validated guided power together.
4. Test combinations of lateral, focus, and angular errors. Estimate the
   scaled response matrix and compare feature changes with their noise.
   Identical images at opposite offsets are an ambiguity, not a training
   problem solved by collecting more copies of the same data.
5. Repeat after remounting or rerouting and across the expected operating
   conditions. Check that a model trained in one session retains its
   direction and scale in another.
6. Compare complete closed-loop runs from held-out starting positions
   against a power-only baseline. Include acquisition, averaging,
   settling, and failed retries in the timing.

.. list-table:: Define pass/fail limits before the comparison
   :header-rows: 1
   :widths: 28 42 30

   * - Quantity
     - What to measure
     - Decision it supports
   * - Capture range and success rate
     - Convergence fraction over a declared starting-position region
     - Whether coarse acquisition is adequate
   * - Final coupling
     - Stationary guided power relative to a verified reference maximum
     - Whether speed sacrifices optical performance
   * - Acquisition time
     - Median and upper-percentile time, including retries
     - Whether the added sensor improves throughput
   * - Observability and direction
     - Scaled singular values and held-out correction-direction errors
     - Which axes may safely use spatial feedback
   * - Dither penalty
     - Mean power reduction and modulation during tracking
     - Whether the tracking signal meets the optical budget
   * - Robustness after assembly
     - Coupling after locking, cure, routing, and thermal settling
     - Whether the alignment survives the real process

If normalized clean-output images remain identical while power changes,
use power-based optimization and reserve the profiler for output-quality
diagnostics. If extra spatial channels reliably predict corrections,
use them within their demonstrated capture region and retain guided
power as the final acceptance measurement.


9. Using KrakenOS and reading further
-------------------------------------

Use KrakenOS to study coupling-optic geometry, stage perturbations,
clearance, and Gaussian-beam propagation. A geometrically small ray spot
or rays landing inside the core does not establish SMF efficiency; a
field-overlap calculation is required. The scalar Gaussian overlap tools
described in :doc:`../manual/gaussian_beams` provide a starting point for
idealized studies. They do not by themselves model cladding-mode
transport, motion dynamics, or a production alignment controller.

* :doc:`worked_exercises/optical_alignment_methods/fiber_and_interferometers`
  gives related bench procedures for fiber injection and interferometers.
* :doc:`worked_exercises/optical_alignment_methods/axis_and_mirror_steering`
  develops the distinction between position and angle alignment.
* `Newport: Fiber Optic Coupling
  <https://www.newport.com/n/fiber-optic-coupling>`_ provides the mode-matching
  basis for the coupling objective.
* `PI: Practical Examples of Parallel Alignment Automation
  <https://www.pi-usa.us/fileadmin/user_upload/pi_us/files/technotes_whitepapers/PI-WP4010E-Practical-Examples-of-Parallel-Alignment-Automation.pdf>`_
  describes practical gradient-search alignment.
* `Thorlabs / Boston Micromachines: Adaptive Optics technical whitepaper
  <https://media.thorlabs.com/globalassets/family-pages/sharedassets/a/ao/ao_101_white_paper.pdf>`_
  explains wavefront-sensor measurements and correction.

The Gaussian overlap example, harmonic expansion, and calibration equations
on this page are worked analytical models with their assumptions stated
alongside them. Residual-light sensing and image regression remain
experimental options to be evaluated with the procedure above.
