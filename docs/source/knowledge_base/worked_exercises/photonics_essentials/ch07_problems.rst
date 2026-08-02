Photonics Essentials: Chapter 7 Problems
========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 7, ``Lasers``, Problems 7.1--7.3,
printed page 173.

Worked solutions
----------------

Problem 7.1: Phase-shift oscillator experiment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a measurement exercise.  The result depends on transistor gain,
component tolerances, potentiometer range, supply voltage, wiring
capacitance, and temperature, so no honest solution can supply the measured
frequency range in advance.

Prediction
~~~~~~~~~~

Figure 7.2 uses three :math:`0.047\ \mu\mathrm F` capacitors and nominal
:math:`4.7\ \mathrm{k\Omega}` feedback resistances.  For an ideal
three-section RC phase-shift network with equal :math:`R` and :math:`C`,

.. math::

   f_0\approx\frac{1}{2\pi RC\sqrt6}
   =\frac{1}{2\pi(4.7\times10^3)(47\times10^{-9})\sqrt6}
   \approx\boxed{294\ \mathrm{Hz}}.

The real circuit is loaded by the transistor and its :math:`470\ \mathrm{k
\Omega}` bias path, so this is a starting estimate rather than a guaranteed
frequency.

Procedure and record
~~~~~~~~~~~~~~~~~~~~

1. Verify component values and transistor pinout with power disconnected.
2. Start with a current-limited low-voltage supply and view the collector on
   the oscilloscope with DC coupling.
3. Sweep the potentiometer slowly.  At each stable setting record frequency,
   peak-to-peak amplitude, and DC collector voltage.
4. Plot amplitude against frequency.  Mark the two points where oscillation
   starts or stops.
5. Repeat at several supply voltages without exceeding transistor ratings.
6. Warm one feedback resistor indirectly and record frequency versus time.

.. csv-table::
   :header: "Pot setting", ":math:`V_+` (V)", "Frequency (Hz)", ":math:`V_{pp}` (V)", "Waveform/notes"

   "", "", "", "", ""
   "", "", "", "", ""
   "", "", "", "", ""

Expected observations
~~~~~~~~~~~~~~~~~~~~~

Increasing a feedback resistance increases its RC delay and normally lowers
the frequency.  Bias voltage mainly changes transistor gain and operating
point; the oscillation frequency should change less than the amplitude, until
the loop gain falls below unity and oscillation stops.  Heating a conventional
resistor changes its resistance according to its temperature coefficient:

.. math::

   \frac{\Delta f}{f}\approx-\frac{\Delta R}{R}.

A positive-temperature-coefficient resistor therefore makes the frequency
fall.  The sign must be reversed for a negative-temperature-coefficient part.

Problem 7.2: Can spontaneous emission be zero?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No.  Setting the spontaneous-emission source term to zero does not produce a
thresholdless laser.  It removes the photons that seed the resonant modes:

.. math::

   \text{no spontaneous seed}
   \Longrightarrow S(0)=0
   \Longrightarrow S(t)=0

in the deterministic rate-equation model, even if material gain exceeds
loss.  A real device always has vacuum fluctuations and some spontaneous
emission, so an exactly zero rate is not physical.

The threshold condition itself remains

.. math::

   \Gamma g_{\mathrm{th}}
   =\alpha_i+\alpha_m.

Reducing spontaneous emission into unwanted modes can improve efficiency and
noise, but it neither removes cavity loss nor the population inversion needed
to overcome it.

Problem 7.3: GaAs laser threshold current density
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For an uncoated semiconductor-air facet,

.. math::

   R=\left(\frac{n-1}{n+1}\right)^2
   =\left(\frac{3.5-1}{3.5+1}\right)^2
   =0.3086.

With equal facets, :math:`L=400\ \mu\mathrm m=0.040\ \mathrm{cm}`, and
internal loss :math:`\alpha_i=30\ \mathrm{cm^{-1}}`,

.. math::

   \begin{aligned}
   k_{\mathrm{th}}
   &=\alpha_i+\frac1L\ln\left(\frac1R\right)\\
   &=30+\frac1{0.040}\ln\left(\frac1{0.3086}\right)\\
   &=\boxed{59.4\ \mathrm{cm^{-1}}}.
   \end{aligned}

Combining the book's Equations 7.19--7.23 gives

.. math::

   J_{\mathrm{th}}
   \approx 8\pi qt
   \frac{\tau_{21}}{\tau_r}
   \frac{k_{\mathrm{th}}n^2\Delta f}{\lambda^2}.

The printed form of Equation 7.23 is easy to misread; the :math:`8\pi` comes
from Equation 7.19 and must remain.  Following the chapter's estimate
:math:`\tau_{21}/\tau_r\approx1`, and using
:math:`t=200\ \mathrm{nm}=2.00\times10^{-5}\ \mathrm{cm}` and
:math:`\lambda=850\ \mathrm{nm}=8.50\times10^{-5}\ \mathrm{cm}`,

.. math::

   \begin{aligned}
   J_{\mathrm{th}}
   &\approx8\pi(1.602\times10^{-19})(2.00\times10^{-5})
   \frac{(59.4)(3.5)^2(1.5\times10^{13})}
        {(8.50\times10^{-5})^2}\\
   &=\boxed{1.22\times10^2\ \mathrm{A/cm^2}}.
   \end{aligned}

This is a model estimate.  Optical confinement, nonradiative recombination,
current spreading, and a lifetime ratio different from unity raise the
measured threshold.
