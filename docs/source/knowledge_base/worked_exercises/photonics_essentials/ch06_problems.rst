Photonics Essentials: Chapter 6 Problems
========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 6, ``Light-Emitting Diodes``, Problems 6.1--6.6,
printed pages 139--141.

Problem 6.1: Red LED turn-on
----------------------------

Figure 6.4 peaks at approximately :math:`700\ \mathrm{nm}`.  Therefore,

.. math::

   E_\gamma=\frac{1239.84}{700}
   =\boxed{1.77\ \mathrm{eV}}.

Visible emission begins around :math:`1.4\ \mathrm V`, but the applied
voltage is not a strict per-electron energy ceiling.  Carriers have a thermal
energy distribution, the junction has a built-in potential and band bending,
and recombining electrons and holes already occupy states in the conduction
and valence bands.  The photon energy is set principally by the band-to-band
energy separation, not simply by :math:`qV`.

At :math:`77\ \mathrm K`:

* the thermal tail becomes narrower, so the onset should be sharper;
* the semiconductor band gap normally increases, shifting emission to
  shorter wavelength and requiring a somewhat larger forward voltage;
* nonradiative processes and series resistance may also change.

Problem 6.2: Why forward bias emits efficiently
------------------------------------------------

Forward bias does two essential things before substantial light and current
appear:

1. It narrows the depletion barrier and brings injected electrons and holes
   into the same physical region.
2. It creates large nonequilibrium carrier populations, including occupied
   conduction-band states and empty valence-band states at compatible energy
   and momentum.

These conditions produce a high radiative recombination rate.  Reverse bias
separates and removes carriers, which is why it is useful for photodetection
rather than efficient LED emission.

Problem 6.3: Accepting an LED shipment
--------------------------------------

Values must be read from the printed spectrum, so use appropriate precision:

.. math::

   \lambda_{\mathrm{peak}}\approx480\ \mathrm{nm},\qquad
   P_{\mathrm{peak}}\approx0.095\ \mathrm{mW}.

The half-power crossings are about :math:`442` and :math:`521\ \mathrm{nm}`.
The wavelength FWHM is therefore about :math:`79\ \mathrm{nm}`.  Convert the
two endpoints to energy rather than treating the conversion as exactly
linear:

.. math::

   \begin{aligned}
   \Delta E_{\mathrm{FWHM}}
   &=\frac{1239.84}{442}-\frac{1239.84}{521}\\
   &\approx\boxed{0.42\ \mathrm{eV}}.
   \end{aligned}

For a :math:`20\ \mathrm{mA}` drive, the injected electron rate is
:math:`I/q`.  Treating the graph's peak optical-power value as the emitted
power specified by the exercise,

.. math::

   \eta
   =\frac{P_{\mathrm{opt}}/(hc/\lambda)}{I/q}
   =\frac{P_{\mathrm{opt}}q\lambda}{Ihc}
   \approx1.84\times10^{-3}.

Thus

.. math::

   \boxed{\eta\approx0.184\%>0.1\%},

so the sample passes and the shipment is accepted, subject to a statistically
adequate sampling plan.  One sample cannot establish the defect rate of
500,000 devices.

Problem 6.4: Traffic-light profitability
-----------------------------------------

This problem requires local quotations; the following is a reusable model
and an illustrative calculation, not a claim about current prices in any
particular city.

Let :math:`P_i` and :math:`P_L` be incandescent and LED powers,
:math:`t_y` the energized hours per year, :math:`c_e` the electricity price,
:math:`C_m` the annual maintenance saving, and :math:`C_0` the installed
conversion cost.  Annual saving is

.. math::

   S_y=(P_i-P_L)t_yc_e+C_m.

For an illustrative :math:`70\ \mathrm W` lamp, :math:`10\ \mathrm W` LED
module, one-third duty cycle, :math:`c_e=\$0.25/\mathrm{kWh}`,
:math:`C_m=\$40/\mathrm{yr}`, and :math:`C_0=\$500`,

.. math::

   t_y=\frac{8760}{3}=2920\ \mathrm h,

.. math::

   S_y=(0.070-0.010)(2920)(0.25)+40
      =\$83.80/\mathrm{yr}.

The simple payback is

.. math::

   \boxed{C_0/S_y\approx6.0\ \text{years}}.

For a ten-year life and 5% discount rate,

.. math::

   \mathrm{NPV}_{\mathrm{savings}}
   =S_y\frac{1-(1.05)^{-10}}{0.05}
   \approx\$647.

Since :math:`\$647>\$500`, the illustrative conversion is profitable.  A real
study should replace every assumed value and include failure rate, cleaning,
driver replacement, traffic-control labor, and residual value.  The book's
Example 6.3 obtained an eight-year affordable conversion price of about
:math:`\$480` using its older energy and labor assumptions.

Problem 6.5: LED bandwidth
---------------------------

Equation 6.40 is

.. math::

   \frac{R(f)}{R(0)}
   =\frac{1}{\sqrt{1+(2\pi f\tau)^2}}.

The chapter defines bandwidth at half **amplitude**, not at the conventional
:math:`1/\sqrt2` amplitude point.  Set :math:`R(f)/R(0)=1/2`:

.. math::

   1+(2\pi f\tau)^2=4,

so

.. math::

   \boxed{f_{\mathrm{BW}}=\frac{\sqrt3}{2\pi\tau}}.

For high injection, the chapter gives

.. math::

   \frac1{\tau_{\mathrm{ac}}}
   =\left(\frac{BJ}{3qd}\right)^{1/2}.

Therefore,

.. math::

   \boxed{
   f_{\mathrm{BW,high}}
   =\frac{\sqrt3}{2\pi}
    \left(\frac{BJ}{3qd}\right)^{1/2}
   =\frac{1}{2\pi}\sqrt{\frac{BJ}{qd}}
   }.

For low injection,

.. math::

   \frac1{\tau_{\mathrm{ac}}}=Bn_D+\frac1{\tau_{n-r}},

which gives

.. math::

   \boxed{
   f_{\mathrm{BW,low}}
   =\frac{\sqrt3}{2\pi}
    \left(Bn_D+\frac1{\tau_{n-r}}\right)
   }.

Thus high-injection bandwidth scales as :math:`\sqrt{BJ}`, while the
low-injection result is linear in :math:`B` and independent of drive current
within that approximation.

Problem 6.6: Green and amber traffic signals
---------------------------------------------

This question reflects the economics and LED technology at the time the book
was written.

**Green.**  Efficient wide-band-gap green emitters were historically harder
and more expensive to manufacture than mature red devices.  Because the
green indication often has a substantial duty cycle, its energy and
maintenance savings can still be large.  The original barrier was therefore
mainly device technology and purchase price, rather than an inability to save
operating cost.

**Amber.**  Amber devices also had a cost and efficiency disadvantage, but an
amber traffic phase is usually brief.  Its low duty cycle means fewer saved
kilowatt-hours and fewer avoided lamp-hours, so the payback is weaker.  That
makes the barrier more strongly economic.  Other amber-LED uses include turn
signals, hazard flashers, warning beacons, construction signs, and status
indicators, where visibility, ruggedness, and fast switching can justify the
device even without long daily operating time.

The chapter's own summary notes that efficient red, green, and blue LEDs were
already commercially available, so the problem should be read as a
source-era engineering comparison rather than a timeless statement of market
availability.
