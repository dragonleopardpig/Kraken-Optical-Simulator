Chapter 3: Pump, Rod, and Resonator Design
===========================================

These worked reading notes expand numerical statements in Sections 3.1 and
3.2.2 of Richard Scheps, *Introduction to Laser Diode-Pumped Solid State
Lasers*, Chapter 3, pp. 26 and 31--32.  They currently cover pump-pulse power,
Nd:YAG rod absorption and dimensions, Brewster-angle trade-offs, threshold
pump power, and slope efficiency.

The energy-to-power conversion
-------------------------------

The required **diode optical power** is not obtained by dividing 1 J by the
efficiency alone.  The pulse energy must first be converted to average power
over the pump pulse:

.. math::
   :label: scheps-31-pump-energy-balance

   E_{\rm out}=\eta_{\rm d\to YAG}P_{\rm d}\tau_p.

Here :math:`E_{\rm out}` is the desired laser pulse energy,
:math:`P_{\rm d}` is the diode optical power during the excitation pulse,
:math:`\tau_p` is the pump-pulse duration, and
:math:`\eta_{\rm d\to YAG}` includes the stated diode-to-Nd:YAG conversion.
Rearranging gives

.. math::
   :label: scheps-31-required-power

   P_{\rm d}=\frac{E_{\rm out}}
   {\eta_{\rm d\to YAG}\tau_p}.

For the values in the book,

.. math::
   :label: scheps-31-19kw-substitution

   \begin{aligned}
   E_{\rm out}&=1\ \mathrm{J},\\
   \eta_{\rm d\to YAG}&=0.35,\\
   \tau_p&=150\ \mu\mathrm{s}=1.50\times10^{-4}\ \mathrm{s},\\
   P_{\rm d}&=\frac{1}{0.35(1.50\times10^{-4})}\ \mathrm{W}
             =1.9048\times10^{4}\ \mathrm{W}
             \approx 19\ \mathrm{kW}.
   \end{aligned}

The inverse pulse duration is the key scale factor: a joule delivered in only
150 microseconds corresponds to 6.667 kW before conversion losses, and the
35-percent conversion requirement multiplies that by :math:`1/0.35`.

Two 40 W end-pump arrays
------------------------

If two fiber-coupled arrays each provide 40 W, their nominal simultaneous pump
power is

.. math::
   :label: scheps-31-two-array-power

   P_{\rm arrays}=2(40\ \mathrm{W})=80\ \mathrm{W}.

Applying exactly the same 35 percent conversion and 150 microsecond pulse used
above predicts

.. math::
   :label: scheps-31-two-array-energy

   E_{\rm out,pred}=0.35(80\ \mathrm{W})(150\times10^{-6}\ \mathrm{s})
                    =4.20\times10^{-3}\ \mathrm{J}
                    =4.2\ \mathrm{mJ}.

This is the direct arithmetic from the stated assumptions.  The book's phrase
“about 3 mJ per pulse” therefore implies an additional unlisted practical
factor.  The effective delivered-pump fraction required to turn the nominal
4.2 mJ into 3 mJ is

.. math::
   :label: scheps-31-utilization

   u=\frac{3.0\ \mathrm{mJ}}{4.2\ \mathrm{mJ}}=0.714.

Equivalently, 3 mJ corresponds to 57.1 W of effective pump at 35 percent, or
to a net conversion of 25 percent when all 80 W reaches the crystal:

.. math::
   :label: scheps-31-three-mj-equivalents

   P_{\rm eff}=\frac{3\ \mathrm{mJ}}{0.35(150\ \mu\mathrm{s})}=57.1\ \mathrm{W},
   \qquad
   \eta_{\rm net}=\frac{3\ \mathrm{mJ}}{80\ \mathrm{W}(150\ \mu\mathrm{s})}=0.25.

Thus 3 mJ is a reasonable engineering estimate if coupling, absorption,
spectral mismatch, and other delivery losses reduce the nominal array power by
about 29 percent.  It should not be presented as the exact result of only the
two stated assumptions; under those assumptions the result is 4.2 mJ.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_laser_diode_pumped_solid_state_lasers/ch03_power_scaling.svg
   :alt: Pump pulse power and energy scaling from diode arrays to Nd:YAG output
   :width: 100%

   **Figure 1.** The 19 kW case requires 1 J in a 150 microsecond pulse.  Two
   40 W arrays produce 4.2 mJ with the idealized 35 percent conversion; the
   book's approximate 3 mJ value corresponds to 71.4 percent effective delivery.

Scheps Section 3.2.2: laser-rod specifications
-----------------------------------------------

Section 3.2.2 chooses the Nd:YAG rod length from the absorption coefficient of
the pump wavelength.  The governing Beer-law relation is

.. math::
   :label: scheps-322-beer-law

   A(L)=1-\exp(-\alpha L),

where :math:`A` is the absorbed fraction, :math:`\alpha` is the absorption
coefficient, and :math:`L` is the pump path length in the crystal.  The
remaining transmitted fraction is :math:`T=\exp(-\alpha L)=1-A`.

Peak-wavelength calculation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the Nd:YAG peak at 808.5 nm, the book uses
:math:`\alpha_{\rm peak}\simeq8\ \mathrm{cm^{-1}}`.  The absorption length is
the distance at which the transmitted fraction falls to :math:`1/e`:

.. math::
   :label: scheps-322-absorption-length

   L_{1/e}=\frac{1}{\alpha_{\rm peak}}
          =\frac{1}{8\ \mathrm{cm^{-1}}}
          =0.125\ \mathrm{cm}=1.25\ \mathrm{mm}.

At integer multiples :math:`mL_{1/e}`, the absorption is
:math:`A_m=1-e^{-m}`.  The numerical values are

.. math::
   :label: scheps-322-multiples

   \begin{array}{c|c|c|c}
   m & L & T=e^{-m} & A=1-e^{-m}\\ \hline
   1 & 1.25\ \mathrm{mm} & 0.3679 & 63.21\%\\
   2 & 2.50\ \mathrm{mm} & 0.1353 & 86.47\%\\
   3 & 3.75\ \mathrm{mm} & 0.0498 & 95.02\%\\
   4 & 5.00\ \mathrm{mm} & 0.0183 & 98.17\%
   \end{array}

Therefore the statement that a 5 mm path absorbs about 98% follows directly
from :math:`\alpha L=8(0.50)=4`:

.. math::
   :label: scheps-322-five-mm

   A(5\ \mathrm{mm})=1-e^{-4}=0.9817=98.17\%.

FWHM-wavelength design constraint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The pump diode has finite spectral bandwidth.  At the two FWHM points of the
Nd:YAG absorption line, the book uses the lower coefficient
:math:`\alpha_{\rm FWHM}\simeq4\ \mathrm{cm^{-1}}`.  Requiring
:math:`\alpha L\ge2` gives

.. math::
   :label: scheps-322-fwhm-minimum

   L\ge\frac{2}{4\ \mathrm{cm^{-1}}}=0.50\ \mathrm{cm}=5\ \mathrm{mm},
   \qquad
   A_{\rm FWHM}(5\ \mathrm{mm})=1-e^{-2}=86.47\%.

The selected rod is twice this minimum length:

.. math::
   :label: scheps-322-selected-length

   L_{\rm rod}=1.0\ \mathrm{cm}=10\ \mathrm{mm}.

At the FWHM coefficient this gives :math:`\alpha L=4` and

.. math::
   :label: scheps-322-fwhm-at-ten-mm

   A_{\rm FWHM}(10\ \mathrm{mm})=1-e^{-4}=98.17\%.

At the peak coefficient the same rod has :math:`\alpha L=8`, so
:math:`A_{\rm peak}=1-e^{-8}=99.966\%`.  The book's statement that more than
90% of the *entire* pump beam is absorbed also includes spectral averaging over
the diode bandwidth; the single-wavelength values above are the limiting-case
calculation, not a substitute for the spectral-overlap integral.

The remaining rod numbers
~~~~~~~~~~~~~~~~~~~~~~~~~

The stated 1.1% Nd doping is the material choice that supplies approximately
:math:`8\ \mathrm{cm^{-1}}` peak absorption in this Nd:YAG grade.  It is not
calculated from Beer law alone; the coefficient must come from measured or
qualified material data.  The selected diameter is

.. math::
   :label: scheps-322-diameter

   d=6.4\ \mathrm{mm}\simeq0.25\ \mathrm{in}.

This diameter is primarily a mechanical decision: a 2--3 mm rod could support
the optical mode, but the 6.4 mm rod is stiffer, less vulnerable to fracture,
and easier to hold in a macroscopic mount.  It does not change the axial Beer
law calculation unless the pump path or illuminated geometry changes.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_laser_diode_pumped_solid_state_lasers/ch03_rod_absorption.svg
   :alt: Nd:YAG pump absorption versus crystal path length at peak and FWHM absorption coefficients
   :width: 100%

   **Figure 2.** Beer-law absorption for :math:`\alpha=8\ \mathrm{cm^{-1}}`
   (peak) and :math:`4\ \mathrm{cm^{-1}}` (FWHM).  The 10 mm selection gives
   99.97% peak absorption and 98.17% absorption at the FWHM coefficient.

Brewster-angle resonator: does the output power fall?
-------------------------------------------------------

A Brewster plate or Brewster-cut gain element is set at

.. math::
   :label: scheps-31-brewster-angle

   \theta_B=\tan^{-1}\!\left(\frac{n_2}{n_1}\right),

where :math:`n_1` and :math:`n_2` are the refractive indices on the incident
and transmitted sides.  At this angle, ideal :math:`p`-polarized light has zero
Fresnel reflection at the interface.  The orthogonal :math:`s` polarization
still reflects, so the Brewster element acts as a polarization-selective loss
inside the resonator.

The effect on output power is therefore not automatically a reduction.  Compare
the two cases using the above-threshold relation

.. math::
   :label: scheps-31-brewster-output

   P_{\rm out}\simeq\eta_s\left(P_{\rm pump}-P_{\rm th}\right),
   \qquad
   P_{\rm th}\ \text{increases with round-trip loss}.

* If the Brewster surface replaces an uncoated or poorly coated interface, it
  can reduce the loss for the desired :math:`p` polarization and preserve or
  increase output.
* If it is added to a cavity that already has low-loss AR coatings, absorption,
  scatter, angle error, and imperfect surface quality add loss.  Output will
  usually be lower unless the polarization selection is needed.
* The rejected :math:`s` polarization does not normally appear as a simple
  50-percent power penalty.  The lower-loss :math:`p` mode reaches threshold
  first and gain saturation suppresses the competing mode.
* Tilting the optic makes the resonator astigmatic: tangential and sagittal
  beam sizes and waist positions differ.  Poor compensation can reduce mode
  overlap, increase diffraction loss, and lower :math:`\eta_s` even when the
  Brewster Fresnel loss is small.

For example, an air-to-glass surface with :math:`n_2=1.5` has
:math:`\theta_B\approx56.3^\circ`.  The ideal :math:`p` reflection is zero,
whereas the :math:`s` reflection is about 15 percent per interface.  Real
performance must also include both surfaces, propagation through the plate,
thermal birefringence, alignment tolerance, and any change to the output
coupler.  A fair power comparison therefore re-optimizes the output coupling
for the changed round-trip loss.

Local references for this design choice
---------------------------------------

The following supplied references discuss Brewster surfaces in laser
resonators:

* *Understanding Lasers*, Sec. 4.7, pp. 120--121: Brewster-window
  polarization selection and the different :math:`p`/:math:`s` losses.
* *Laser Resonators and Beam Propagation*, Secs. 3.3--3.4, pp. 168--170:
  Brewster-plate Jones matrices and the lowest-loss resonator polarization
  eigenmode.
* *Solid-State Laser Engineering*, pp. 250--252: Brewster-ended rods,
  astigmatism, and compensation in folded resonators.
* *Introduction to Laser Diode-Pumped Solid State Lasers*, Sec. 5.3.2,
  pp. 63--64: a Brewster-angle Nd:YAG ring resonator used to maintain the
  polarization needed for unidirectional operation.

For a polarization-insensitive Nd:YAG oscillator, a normal-incidence,
AR-coated interface is usually simpler and can provide higher total power.  A
Brewster design is justified when polarization, frequency doubling, Q-switching,
or a Brewster-cut gain element provides a stronger system-level benefit than
the added astigmatism and alignment complexity.

Meaning of low threshold and high slope efficiency
---------------------------------------------------

The sentence in Section 3.1 is describing two different parts of the laser
input-output curve.  The relevant pump quantity is the absorbed pump power
density,

.. math::
   :label: scheps-31-pump-density

   I_p=\frac{P_{\rm abs}}{A_p},

where :math:`P_{\rm abs}` is the pump power absorbed in the crystal and
:math:`A_p` is the illuminated cross-sectional area.  End pumping focuses the
pump into approximately the same small volume occupied by the resonator mode,
so a given total pump power produces a larger inversion where it is useful.

**Threshold pump power** :math:`P_{\rm th}` is the minimum absorbed pump power
at which the round-trip gain equals the resonator loss.  Below threshold,
spontaneous emission and fluorescence dominate and there is no sustained laser
output.  A simple above-threshold model is

.. math::
   :label: scheps-31-laser-input-output

   P_{\rm out}=\begin{cases}
   0, & P_{\rm abs}\le P_{\rm th},\\
   \eta_s\left(P_{\rm abs}-P_{\rm th}\right),
      & P_{\rm abs}>P_{\rm th}.
   \end{cases}

“Low threshold” means that :math:`P_{\rm th}` is small.  High pump density can
lower it when the pump distribution overlaps the fundamental mode well: less
total pump is wasted outside the active mode, and the required inversion is
reached with less incident power.  It does **not** mean that the material has
zero loss or that arbitrarily high intensity is safe.

**Slope efficiency** :math:`\eta_s` is the slope of the straight part of the
output curve above threshold,

.. math::
   :label: scheps-31-slope-efficiency

   \eta_s=\frac{dP_{\rm out}}{dP_{\rm abs}}.

It is dimensionless when both powers use the same units.  For example,
:math:`\eta_s=0.50` means that each additional watt of absorbed pump produces
about 0.5 W of extracted laser power after threshold.  This is different from
the earlier :math:`\eta_{\rm d\to YAG}`: the latter is the overall diode-pump
to laser-output factor used for the pulse-energy estimate, while slope
efficiency is a local derivative and is normally measured from a power sweep.

The two benefits are related but not identical.  Good overlap can reduce
:math:`P_{\rm th}` and increase :math:`\eta_s`; output coupling, quantum
defect, reabsorption, excited-state absorption, parasitic loss, and thermal
lensing also affect the slope.  Increasing pump density too far can reverse
the benefit through thermal lensing, birefringence, fracture, coating damage,
or gain saturation.  Thus “high density” means high useful density in the
mode volume, not simply the highest possible irradiance.

Scaling rules
-------------

For any desired pulse energy and pulse duration, use

.. math::
   :label: scheps-31-general-scaling

   P_{\rm d}[\mathrm{W}]
   =\frac{E_{\rm out}[\mathrm{J}]}
   {\eta\,\tau_p[\mathrm{s}]},
   \qquad
   E_{\rm out}[\mathrm{J}]=\eta P_{\rm d}[\mathrm{W}]\tau_p[\mathrm{s}].

These are pulse-average optical quantities.  Electrical wall-plug power,
thermal duty factor, pump absorption, and resonator extraction efficiency must
be added separately when sizing the complete laser system.
