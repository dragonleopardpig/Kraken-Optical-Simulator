Photonics Essentials: Chapter 9 Problems
========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 9, ``Optical Fibers and Optical Fiber
Amplifiers``, Problems 9.1--9.4, printed pages 222--224.

The calculations follow the chapter's simple step-index and transform-limited
pulse models.  Catalog values are rounded measurements and need not be
mutually exact inputs to those models.

Worked solutions
----------------

Problem 9.1: Corning SMF-28 estimates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The normalized frequency is

.. math::

   V=\frac{2\pi a}{\lambda}\mathrm{NA}.

Using :math:`a=8.2/2=4.1\ \mu\mathrm m` and the NA quoted at
:math:`1310\ \mathrm{nm}`,

.. math::

   V_{1310}
   =\frac{2\pi(4.1)(0.14)}{1.310}
   =\boxed{2.75}.

For weak guidance,

.. math::

   \Delta=\frac{n_1-n_2}{n_1}
   \approx\frac{\mathrm{NA}^2}{2n_1^2}.

Taking the stated effective group index as the requested estimate for
:math:`n_1`,

.. math::

   \boxed{\Delta\approx
   \frac{0.14^2}{2(1.4677)^2}
   =4.55\times10^{-3}=0.455\%}.

Equivalently, :math:`n_1-n_2\approx0.00668`.

An ideal step-index fiber becomes single mode at :math:`V=2.405`, giving

.. math::

   \lambda_c
   =\frac{2\pi a\,\mathrm{NA}}{2.405}
   =\boxed{1.50\ \mu\mathrm m}.

This literal result conflicts with the data sheet's identification of the
fiber as single-mode at :math:`1310\ \mathrm{nm}`.  It also predicts
:math:`V_{1310}>2.405`.  The reason is that nominal core diameter, measured
NA, mode-field diameter, and effective group index cannot be combined as
exact parameters of a single ideal step-index profile.  The calculation is a
useful consistency check, not a replacement for the manufacturer's measured
cable cutoff.

Problem 9.2: Material-dispersion distance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Bit periods
~~~~~~~~~~~

.. math::

   T_b=\frac1B.

.. csv-table::
   :header: "Bit rate", "2.5 Gbit/s", "10 Gbit/s", "40 Gbit/s"

   ":math:`T_b`", "400 ps", "100 ps", "25 ps"
   "Allowed 50% broadening", "200 ps", "50 ps", "12.5 ps"

Dispersion near 1550 nm
~~~~~~~~~~~~~~~~~~~~~~~

A visual linear fit to Figure 9.10 near :math:`1550\ \mathrm{nm}` gives
approximately

.. math::

   \boxed{
   M(\lambda)\approx
   17+0.07[\lambda(\mathrm{nm})-1550]
   \ \mathrm{\frac{ps}{nm\,km}}
   }.

The values are graph estimates; using a different pair of well-read points
can change the intercept by about :math:`1\ \mathrm{ps/(nm\,km)}`.

Modulation linewidth
~~~~~~~~~~~~~~~~~~~~

The chapter uses :math:`\Delta f\approx2/T_b=2B`.  Since
:math:`f_0=c/\lambda_0`,

.. math::

   \Delta\lambda_{\mathrm{mod}}
   \approx\lambda_0\frac{\Delta f}{f_0}
   =\frac{2\lambda_0^2B}{c}.

Following the book, add this linearly to the zero-modulation linewidth
:math:`0.3\ \mathrm{nm}`:

.. csv-table::
   :header: "Bit rate", ":math:`\Delta\lambda_{\mathrm{mod}}`", ":math:`\Delta\lambda_{\mathrm{total}}`"

   "2.5 Gbit/s", "0.0401 nm", "0.340 nm"
   "10 Gbit/s", "0.160 nm", "0.460 nm"
   "40 Gbit/s", "0.641 nm", "0.941 nm"

Distance limit
~~~~~~~~~~~~~~

Material-dispersion broadening is

.. math::

   \Delta t_M=L\,M\,\Delta\lambda.

Overlap begins under the problem's criterion when
:math:`\Delta t_M=0.5T_b`.  Therefore,

.. math::

   L_{\max}=\frac{0.5T_b}{M\Delta\lambda}.

Using :math:`M=17\ \mathrm{ps/(nm\,km)}`:

.. csv-table::
   :header: "Bit rate", "Allowed :math:`\Delta t_M`", ":math:`L_{\max}`"

   "2.5 Gbit/s", "200 ps", "34.6 km"
   "10 Gbit/s", "50 ps", "6.39 km"
   "40 Gbit/s", "12.5 ps", "0.781 km"

The result isolates **material** dispersion as requested; actual SMF-28 total
chromatic dispersion also includes waveguide dispersion.

Problem 9.3: Inferring Samsung fiber geometry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Numerical aperture
~~~~~~~~~~~~~~~~~~

The specified relative index difference is
:math:`\Delta=0.0034`.  With :math:`n_1=1.4690`,

.. math::

   n_2=n_1(1-\Delta)=1.4640,

.. math::

   \mathrm{NA}=\sqrt{n_1^2-n_2^2}
   =\boxed{0.121}.

Core-diameter trials
~~~~~~~~~~~~~~~~~~~~

For the mode-field diameter, use the chapter's Gaussian approximation

.. math::

   \frac{\mathrm{MFD}}{d}
   =0.65+\frac{1.619}{V^{3/2}}+\frac{2.879}{V^6},
   \qquad
   V=\frac{\pi d\,\mathrm{NA}}{\lambda}.

.. csv-table::
   :header: "Assumed :math:`d`", ":math:`V_{1310}`", "MFD at 1310 nm", ":math:`V_{1550}`", "MFD at 1550 nm"

   "8.5 um", "2.47", "9.18 um", "2.09", "10.39 um"
   "9.0 um", "2.61", "9.38 um", "2.21", "10.52 um"
   "Specified", "", "9.3 um", "", "10.5 um"

Both guesses are reasonable, but :math:`9.0\ \mu\mathrm m` has the smaller
combined error.  A least-squares match to both MFD values gives approximately
:math:`d=8.84\ \mu\mathrm m`.

The corresponding ideal step-index cutoff wavelengths are

.. math::

   \lambda_c=\frac{\pi d\,\mathrm{NA}}{2.405}
   =1.34\ \mu\mathrm m\quad(d=8.5\ \mu\mathrm m)

and :math:`1.42\ \mu\mathrm m` for :math:`d=9.0\ \mu\mathrm m`.  The book asks
for the “longest” single-mode wavelength, but the model has no such upper
limit: :math:`V` falls as wavelength rises.  These are the **shortest**
single-mode wavelengths predicted by the model.

Simple fitting routine
~~~~~~~~~~~~~~~~~~~~~~

This dependency-free Python routine searches for the diameter that best
matches both catalog MFD values:

.. code-block:: python

   import math

   na = 0.1210338
   samples = ((1.310, 9.3), (1.550, 10.5))  # wavelength, MFD in um

   def predicted_mfd(diameter, wavelength):
       v = math.pi * diameter * na / wavelength
       ratio = 0.65 + 1.619 / v**1.5 + 2.879 / v**6
       return diameter * ratio

   best = None
   for step in range(50_001):
       d = 6.0 + step * 0.0001
       error = sum(
           (predicted_mfd(d, wavelength) - measured) ** 2
           for wavelength, measured in samples
       )
       if best is None or error < best[0]:
           best = (error, d)

   print(best[1])  # approximately 8.84 um

Dispersion distance
~~~~~~~~~~~~~~~~~~~

Use the same linewidth model as Problem 9.2, now with the specified
:math:`M=18\ \mathrm{ps/(nm\,km)}` at :math:`1550\ \mathrm{nm}`:

.. csv-table::
   :header: "Bit rate", "Allowed broadening", "Distance"

   "2.5 Gbit/s", "200 ps", "32.7 km"
   "10 Gbit/s", "50 ps", "6.04 km"
   "40 Gbit/s", "12.5 ps", "0.738 km"

Problem 9.4: WDM information bandwidth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The frequency width of the 1530--1560 nm window is more accurate than treating
all 30 nm as one constant wavelength conversion:

.. math::

   \Delta f_{\mathrm{window}}
   =c\left(\frac1{1530\ \mathrm{nm}}-\frac1{1560\ \mathrm{nm}}\right)
   =3.768\ \mathrm{THz}.

Using the chapter's transform-limited convention, a bit rate :math:`B`
requires optical bandwidth :math:`2B`.  Channel centers are separated by
:math:`1.5(2B)=3B`.

.. csv-table::
   :header: "Bit rate/channel", "Optical bandwidth", "Equivalent width near 1550 nm", "Spacing", "Whole channels", "Aggregate rate"

   "10 Gbit/s", "20 GHz", "0.160 nm", "30 GHz", "125", "1.25 Tbit/s"
   "40 Gbit/s", "80 GHz", "0.641 nm", "120 GHz", "31", "1.24 Tbit/s"

The nearly equal totals are expected:

.. math::

   N_{\mathrm{ch}}B
   \approx\frac{\Delta f_{\mathrm{window}}}{3B}B
   =\frac{\Delta f_{\mathrm{window}}}{3}.

ITU-T comparison
~~~~~~~~~~~~~~~~

ITU-T G.694.1 defines a **frequency grid**, not one mandatory bit rate per
channel.  Its fixed-grid examples include 12.5, 25, 50, and 100 GHz spacings,
anchored at 193.1 THz; its flexible grid uses 6.25 GHz center-frequency
granularity and 12.5 GHz slot-width granularity.  See the `official ITU-T
G.694.1 summary <https://www.itu.int/dms_pubrec/itu-t/rec/g/T-REC-G.694.1-202010-I!!SUM-HTM-E.htm>`_.

The ideal 30 GHz spacing is not on the listed fixed examples and the 120 GHz
requirement is not a 12.5 GHz slot multiple.  On the flexible grid they would
round up to 37.5 and 125 GHz.  Guard bands, filter shape, laser drift,
dispersion, modulation format, and forward-error correction determine the
deployable capacity, so the simple result is an upper-level engineering
estimate rather than an ITU-compliant network design.
