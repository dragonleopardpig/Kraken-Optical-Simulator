Solid-State Laser Design
========================

A strong system answer begins with requirements and closes four coupled loops:
spectroscopy, pump/gain overlap, resonator extraction, and heat removal.  Pulse
format, nonlinear conversion, mechanics, controls, safety, and lifetime sit on
top of those loops.

Translate requirements before choosing hardware
------------------------------------------------

Write down at least:

* wavelength and linewidth;
* continuous-wave or pulse energy, duration, repetition rate, and allowed jitter;
* beam quality, polarization, pointing, and waist location;
* wall-plug power, size, mass, cooling, and warm-up constraints;
* operating temperature, shock/vibration, contamination, and lifetime;
* optical interfaces, control interfaces, safety class, and validation method.

Then form derived quantities with :eq:`interview-pulse-relations`: peak power,
fluence, peak irradiance, duty cycle, and stored energy.  These often eliminate
architectures before detailed optical design begins.

Gain-medium selection
---------------------

.. list-table::
   :header-rows: 1
   :widths: 19 25 28 28

   * - Property
     - It controls
     - Favorable direction
     - Coupled penalty
   * - Emission cross section :math:`\sigma_e`
     - Gain and saturation intensity
     - Large for low threshold and compact cavities
     - Often shorter energy-storage time or narrower tuning range
   * - Upper-state lifetime :math:`\tau_f`
     - Stored energy and pump dynamics
     - Long for Q-switching and low pump intensity
     - Slow transients and possible energy-transfer losses
   * - Emission bandwidth
     - Tunability and transform-limited pulse duration
     - Broad for ultrashort pulses
     - Lower peak cross section and more dispersion management
   * - Thermal conductivity
     - Temperature rise and thermal lens
     - High
     - Host availability, growth, or doping may constrain it
   * - Thermo-optic coefficient
     - Optical-path distortion
     - Small magnitude
     - Stress-optic and end-face bulging can still dominate
   * - Fracture strength
     - Maximum thermal loading
     - High
     - Mounting stress and inclusions reduce practical margin
   * - Pump absorption
     - Required length and pump geometry
     - Adequate at available diode wavelength
     - Strong absorption can concentrate heat near an entrance face

Material shorthand for interviews
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Nd:YAG:** mature, mechanically robust, strong 1064-nm transition, suitable
  for cw and Q-switched systems; narrower bandwidth than ultrafast hosts.
* **Nd:YVO4:** strong pump absorption and gain, useful in compact low-to-medium
  power oscillators; more anisotropic and thermally demanding.
* **Yb:YAG:** small quantum defect and simple level structure, attractive for
  efficient high power; quasi-three-level reabsorption makes temperature and
  inversion important.
* **Ti:sapphire:** extremely broad gain for tunable and femtosecond operation;
  demands a suitable high-brightness pump and careful dispersion management.
* **Er- and Tm-based media:** access eye-safer and mid-infrared bands; level
  dynamics, reabsorption, cross relaxation, and pump availability are central.

These are starting points, not a selection table.  Compare actual spectroscopy,
doping, geometry, thermal conditions, and supplier quality for the application.

Pump design
-----------

For a simple end-pumped pass,

.. math::
   :label: interview-pump-absorption

   P_{\rm abs}=\eta_c P_p
   \left[1-\exp(-\alpha_pL_g)\right],

where :math:`\eta_c` contains transport and coupling losses.  Double-pass pump
optics can raise absorption but also change the longitudinal heat distribution.

Brightness and étendue cannot be improved by passive optics.  A pump train must
therefore be designed from the diode's measured emitter size, divergence,
astigmatism, smile, spectrum, polarization, and wavelength shift with current
and temperature—not from optical power alone.

End pumping versus side pumping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Geometry
     - Advantages
     - Risks
   * - End pumped
     - High TEM00 overlap, compact cavity, efficient at moderate power
     - Intense localized heat, longitudinal absorption gradient, tight alignment
   * - Side pumped
     - Scales pump area and rod length; multiple diode packages can be distributed
     - Weaker fundamental-mode overlap, more complex homogenization, often multimode
   * - Thin disk / face pumped
     - Short heat-flow distance and power scaling with large mode area
     - Low single-pass gain, complex multipass pump optics, coating and mounting demands
   * - Slab / zigzag
     - Averages one-dimensional thermal gradients and supports large apertures
     - Astigmatism, edge effects, parasitic paths, and more complex resonator geometry

Mode and pump overlap
~~~~~~~~~~~~~~~~~~~~~

For transverse distributions :math:`I_l(x,y,z)` and absorbed pump density
:math:`Q_p(x,y,z)`, reason from an overlap integral rather than two quoted spot
diameters:

.. math::
   :label: interview-overlap

   \eta_{\rm ov}\propto
   \frac{\iiint I_l Q_p\,dV}
   {\sqrt{\iiint I_l^2\,dV\;\iiint Q_p^2\,dV}}.

Exact oscillator models use inversion and saturation, but this normalized form
exposes the design trade.  A pump waist slightly larger than the laser mode can
improve alignment tolerance and avoid hot spots, while too much oversizing wastes
pump and encourages higher-order modes.

Output coupling and parasitic loss
----------------------------------

Output-coupler transmission :math:`T` is intentional round-trip loss that
becomes useful power.  If :math:`T` is too small, circulating power and coating
loading rise while little power leaves.  If too large, threshold rises and gain
may not sustain oscillation.  The optimum moves with pump level and saturated
gain; it is not a universal reflectivity.

A practical first study sweeps :math:`T` together with uncertain parasitic loss,
pump power, and thermal lens.  At modest gain, :math:`T` being of the same order
as internal loss is a useful starting intuition; a high-gain system can support
larger output coupling.  Final selection requires a saturated-gain model and
measured coating, scatter, absorption, and diffraction losses.

Thermal engineering
-------------------

Start with absorbed pump and an explicit heat fraction:

.. math::
   :label: interview-heat-load

   P_{\rm heat}=\eta_hP_{\rm abs},
   \qquad
   \eta_h\ge 1-\frac{\lambda_p}{\lambda_l}.

Then solve or estimate the temperature field using the true pump distribution
and boundary conductance.  Convert it to:

* refractive-index gradient;
* end-face bulging;
* photoelastic lens and stress birefringence;
* stress and fracture margin; and
* temperature-dependent absorption, lifetime, and wavelength shifts.

Mounting is part of the thermal model.  Excess clamp force, uneven indium foil,
poor interface flatness, adhesive shrinkage, and coolant gradients can dominate
a material-only prediction.

Amplifiers, ASE, and parasitic oscillation
------------------------------------------

For a short pulse through a homogeneously broadened saturated amplifier, the
Frantz–Nodvik relation is a useful design model:

.. math::
   :label: interview-frantz-nodvik

   F_{\rm out}=F_{\rm sat}
   \ln\!\left[1+G_0\left(\exp(F_{\rm in}/F_{\rm sat})-1\right)\right].

It shows how small-signal gain :math:`G_0`, input fluence, and saturation fluence
set extraction.  It does not include transverse nonuniformity, ASE depletion,
damage, bandwidth, or nonlinear phase.

ASE and parasitic lasing grow along high-gain paths that may not coincide with
the intended beam.  Inspect the longest dimensions, polished barrel paths,
specular mount surfaces, end-face reflections, and multi-pass ghost loops.  Use
absorbing claddings, roughened or angled edges, index matching, spatial isolation,
and gain segmentation where appropriate.

Pulse and nonlinear subsystems
------------------------------

**Q-switch choice.** Electro-optic switches are fast and support precise timing
but need high-voltage drivers and careful polarization control.  Acousto-optic
switches are convenient for repetitive moderate-power systems but switch more
slowly and add diffraction/thermal constraints.  Passive absorbers are compact
but offer less timing control and can suffer bleaching nonuniformity or damage.

**Mode-lock choice.** Active modulation is controllable but generally produces
longer pulses.  SESAMs aid self-starting but have saturation-fluence and damage
limits.  Kerr-lens mode locking supports very short pulses but depends strongly
on cavity alignment, nonlinear focus, aperture action, and dispersion.

**Frequency conversion.** Specify polarization, phase-matching method, crystal
temperature/angle, focusing parameter, walk-off, acceptance bandwidth, coatings,
absorption, and separation of residual wavelengths.  For pulsed systems evaluate
peak fluence and peak irradiance at every crystal and coating surface.

Reliability and damage
----------------------

Damage threshold is a test condition, not a single material constant.  Record
wavelength, pulse duration, repetition rate, spot definition, incidence angle,
polarization, number of shots, defect statistics, cleanliness, and test protocol.
Design below the applicable lower-confidence threshold with margin for hot spots,
back-reflections, coating variation, contamination growth, and focus drift.

A design review should include at least these unintended paths: first-surface
reflections, uncoated wedges, ghost foci, rejected polarization, undiffracted
Q-switch order, residual fundamental after harmonic conversion, amplifier ASE,
and retroreflections into pump diodes or seed lasers.
