Diode-Pumped Solid-State Laser Engineering
===========================================

Diode pumping is not simply replacing a lamp with a more efficient source.  The
pump's spectrum, étendue, polarization, spatial structure, temperature drift,
and lifetime behavior become inputs to the gain, thermal, resonator, and control
models.  This page turns those couplings into an interview-ready design method.

Characterize the pump before choosing lenses
---------------------------------------------

Ask for measured, tolerance-bounded data rather than one nominal power number:

.. list-table:: Pump-diode information that changes the laser design
   :header-rows: 1
   :widths: 24 36 40

   * - Diode property
     - Design consequence
     - Measurement or supplier evidence
   * - Spectrum versus current and temperature
     - Absorbed fraction, heat distribution, threshold, and power stability
     - Center wavelength, bandwidth, side modes, wavelength-temperature and wavelength-current curves
   * - Fast- and slow-axis divergence
     - Collection NA, collimator choice, astigmatism, and achievable pump waist
     - Near/far-field data using a declared width convention
   * - Emitter or fiber geometry
     - Étendue, image size, homogenization, and alignment tolerance
     - Emitter dimensions, bar smile, fill factor, or fiber core and NA
   * - Polarization
     - Absorption and polarization-combining efficiency
     - Extinction ratio over the qualified operating range
   * - Power and efficiency
     - Optical, electrical, and thermal budgets
     - Calibrated light-current-voltage curves at controlled temperature
   * - Packaging and lifetime drift
     - Focus stability, coupling yield, control authority, and end-of-life margin
     - Mechanical datums, burn-in, accelerated-life, and environmental data

Spectral absorption is an overlap calculation
---------------------------------------------

For pump spectral density :math:`S_p(\lambda)` and absorption coefficient
:math:`\alpha(\lambda,T)`, a useful first-pass absorbed fraction is

.. math::
   :label: interview-spectral-absorption

   \eta_{\rm abs,spec}(T)=
   \frac{\int S_p(\lambda)
   \left[1-\exp\!\left(-\alpha(\lambda,T)L_{\rm eff}\right)\right]d\lambda}
   {\int S_p(\lambda)d\lambda}.

:math:`L_{\rm eff}` includes the intended pump passes.  This exposes why the
answer cannot be ``the diode is at 808 nm``: diode wavelength and width move
with junction temperature and drive current, while the gain-medium absorption
also changes with temperature and composition.

The design loop is to measure the diode spectrum, convolve it with measured or
qualified absorption data, choose diode temperature and crystal length/doping,
and then repeat at cold, nominal, hot, and end-of-life conditions.  A double
pass may improve absorption but changes longitudinal heat deposition and adds
ghost-feedback risks.

Brightness limits pump focusing
-------------------------------

Passive optics conserve radiance and étendue.  In a paraxial single-axis model,

.. math::
   :label: interview-pump-bpp

   \operatorname{BPP}=w_p\theta_p
   \simeq M_p^2\frac{\lambda_p}{\pi}.

A lens can exchange beam radius and divergence, but cannot reduce their product.
For a fiber-coupled pump, core size and NA therefore set a lower bound on the
image/waist trade.  For an emitter or bar, treat fast and slow axes separately;
fast-axis collimation, slow-axis collimation, bar smile, dead space, and fill
factor prevent a circular-Gaussian assumption from being reliable.

Pump geometry trade space
-------------------------

.. list-table:: Architecture selection shorthand
   :header-rows: 1
   :widths: 21 39 40

   * - Architecture
     - Choose it when
     - Close these risks
   * - Direct end pump
     - Brightness supports good fundamental-mode overlap in a compact oscillator
     - Astigmatism, alignment, local heat density, coating loading, and diode feedback
   * - Fiber-coupled end pump
     - Modularity and source/mechanical separation justify coupling loss
     - Fiber-face damage, NA/core tolerances, connector loss, back-reflection, and image stability
   * - Side-pumped rod or slab
     - Pump area and total power must scale beyond one end-pump channel
     - Homogenization, lower TEM00 overlap, asymmetric thermal field, and parasitic paths
   * - Multipass thin disk
     - Short heat flow and large mode area are central to power scaling
     - Pump-imaging sensitivity, low single-pass gain, coating loading, and ASE
   * - Microchip or monolithic
     - Minimum size and short cavity are more important than adjustment freedom
     - Thermal detuning, restricted mode control, coating damage, and fabrication tolerance

End-pumped oscillator workflow
------------------------------

Use this sequence at a whiteboard:

1. Translate output requirements into wavelength, absorbed pump, heat, mode
   size, pulse exposure, polarization, stability, and lifetime budgets.
2. Select the gain material, dopant concentration, and length together.  Check
   absorption, reabsorption, energy storage, concentration quenching, stress,
   and commercially available coatings.
3. Select a diode whose full spectrum overlaps the absorption band over current,
   temperature, tolerance, and ageing—not merely at room-temperature nominal.
4. Propagate the measured pump étendue through the real delivery train.  Include
   collimator aberration, fiber NA, astigmatism, decenter, and focus tolerance.
5. Compare the three-dimensional absorbed-pump volume with the resonator mode
   using :eq:`interview-overlap`; sweep relative waist size and axial position.
6. Calculate threshold, saturated output, and output-coupler sweeps using the
   definitions in :doc:`theory_essentials`.
7. Feed the absorbed-pump distribution into the thermal/stress model, insert the
   resulting lens range into the cavity ABCD model, and iterate.
8. Verify pump leakage, residual absorption, diode feedback, coating exposure,
   ghosts, controls, and fault states before finalizing mechanics.

Hands-on qualification
----------------------

On the bench, record diode current, voltage, package/base temperature, optical
power, spectrum, polarization, near field, far field, and focused caustic.  Do
this at several operating points after thermal equilibrium.  Calibrate pump
power both before the crystal and after the delivery optics; infer absorption
only after accounting for residual pump, fluorescence, windows, multiple passes,
and detector wavelength response.

When output falls as the diode warms, separate four possibilities: electrical
power loss, transport/focus motion, spectral detuning from the absorption band,
and a resonator thermal-lens shift.  Simultaneously log diode spectrum, incident
and residual pump, laser power, beam position/size, and coolant temperatures.
That experiment is far more discriminating than turning the diode temperature
until output improves.

Fast interview checks
---------------------

* A narrower pump spectrum can increase absorption but may raise cost and make
  wavelength control more critical.
* Increasing dopant concentration shortens the absorption length but can
  concentrate heat and introduce concentration-dependent losses.
* A smaller pump spot can lower threshold through overlap, while raising thermal
  gradient, aberration, damage exposure, and sensitivity.
* Fiber coupling improves packaging freedom; it does not erase the source
  étendue represented by core size and NA.
* Maximizing absorbed pump is not identical to maximizing useful output: spatial
  overlap, heat distribution, loss, and extraction still close the balance.
