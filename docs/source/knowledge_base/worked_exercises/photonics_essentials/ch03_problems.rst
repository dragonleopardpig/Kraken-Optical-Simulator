Photonics Essentials: Chapter 3 Problems
========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 3, ``Photodiodes``, Problems 3.1--3.5,
printed pages 58--60.

.. seealso::

   :doc:`ch03_diffusion_equation` explains how the diffusion current on
   printed page 38 leads to the second-order spatial derivative in Equation
   3.5.

Values read from the book's plots are estimates.  The calculations use

.. math::

   E_\gamma(\mathrm{eV})=\frac{1239.84}{\lambda(\mathrm{nm})},
   \qquad
   \mathcal R=\eta\frac{q\lambda}{hc}.

Quick results
-------------

.. csv-table::
   :header: "Problem", "Result"

   "3.1", "Detection starts near :math:`0.67\ \mathrm{eV}` and is suppressed above about :math:`1.13\ \mathrm{eV}`; the detector is Ge"
   "3.2", ":math:`\mathcal R_{1000}=0.65\ \mathrm{A/W}`, :math:`\eta\approx0.806`, :math:`I_{600}\approx0.390\ \mu\mathrm A`"
   "3.3", "Graph estimate: :math:`I_d\approx1.5\ \mu\mathrm A`"
   "3.4", "The straight semilog segment implies an exponential law; the printed voltage scale gives an unphysical :math:`n\approx0.19`"
   "3.5", ":math:`P_D\approx9.21\ \mathrm{nW}`, :math:`\mathcal R=0.375\ \mathrm{A/W}`, :math:`I(1\ \mathrm m)=3.46\ \mathrm{nA}`"

Worked solutions
----------------

Problem 3.1: Filtered photodiode spectrum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrase.**  Interpret a measured spectrum made with an incandescent
source, a silicon filter, a monochromator, and an unknown Ge or Si detector.

The response first rises at about :math:`1850\ \mathrm{nm}`.  Its photon
energy is

.. math::

   E_{\min}\approx\frac{1239.84}{1850}
   =\boxed{0.67\ \mathrm{eV}}.

That long-wavelength edge agrees with the room-temperature Ge band gap.  A
silicon detector would stop responding near :math:`1100\ \mathrm{nm}`, so
the detector must be

.. math::

   \boxed{\text{germanium}}.

The short-wavelength edge is near :math:`1100\ \mathrm{nm}`, or

.. math::

   E_{\max}\approx\frac{1239.84}{1100}
   =\boxed{1.13\ \mathrm{eV}}.

This edge is caused by the **silicon filter**, not by the Ge detector.
Silicon absorbs photons above its band gap and therefore blocks wavelengths
shorter than roughly :math:`1.1\ \mu\mathrm m`.

A monochromator set to :math:`\lambda` can also transmit its second order at
:math:`\lambda/2`.  Without the silicon filter, visible second-order light
could produce a false infrared response.  The silicon filter absorbs most of
that visible light, strongly suppressing the artifact.

Problem 3.2: Responsivity and quantum efficiency
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

At :math:`1000\ \mathrm{nm}`, divide the measured current by incident power:

.. math::

   \mathcal R_{1000}
   =\frac{0.65\ \mu\mathrm A}{1.00\ \mu\mathrm W}
   =\boxed{0.65\ \mathrm{A/W}}.

Since

.. math::

   \mathcal R=\eta\frac{\lambda(\mathrm{nm})}{1239.84},

the quantum efficiency is

.. math::

   \eta
   =\mathcal R\frac{1239.84}{\lambda}
   =(0.65)\frac{1239.84}{1000}
   =\boxed{0.806}.

Assuming this internal efficiency remains constant at :math:`600\ \mathrm{nm}`,

.. math::

   \mathcal R_{600}
   =(0.806)\frac{600}{1239.84}
   =0.390\ \mathrm{A/W},

and a :math:`1\ \mu\mathrm W` signal produces

.. math::

   \boxed{I_{600}=0.390\ \mu\mathrm A}.

The trial curve requested in part (d) is therefore

.. math::

   \mathcal R(\lambda)\approx
   \begin{cases}
   0.806\,\lambda/1239.84\ \mathrm{A/W},
      &400\leq\lambda\lesssim1100\ \mathrm{nm},\\
   0,&\lambda\gtrsim1100\ \mathrm{nm}.
   \end{cases}

.. csv-table::
   :header: ":math:`\lambda` (nm)", "400", "600", "800", "1000", "1100", "1200", "1400"

   ":math:`\mathcal R` (A/W)", "0.260", "0.390", "0.520", "0.650", "0.715", "0", "0"

The abrupt cutoff is an idealization.  A measured silicon response rolls off
as absorption becomes weak near the indirect band edge.

Problem 3.3: Germanium dark current
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In reverse bias the curve is nearly horizontal about three vertical
divisions below zero.  With :math:`5\times10^{-7}\ \mathrm{A/div}`,

.. math::

   |I_d|\approx3(5\times10^{-7})
   =\boxed{1.5\times10^{-6}\ \mathrm A}.

The reading is only accurate to roughly half a graph division.  It is larger
than the dark current normally measured from a comparable silicon diode.
Three features increase it:

* Ge has a smaller band gap, so thermal generation is much stronger.
* The area, :math:`8\times10^{-3}\ \mathrm{cm^2}`, provides appreciable bulk
  and junction volume.
* Surface leakage, defects, and the measurement temperature add to the
  generation current.

Problem 3.4: Forward characteristic and ideality factor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A straight line on a plot of :math:`\log_{10}I` against :math:`V` means

.. math::

   I=I_s\exp\left(\frac{qV}{nk_BT}\right).

For one decade of current,

.. math::

   \Delta V_{\mathrm{dec}}
   =n\frac{k_BT}{q}\ln 10
   \approx n(59.6\ \mathrm{mV})

at :math:`300\ \mathrm K`.

The dashed segment in the printed graph rises by about 4.5 decades over
:math:`0.050\ \mathrm V`, giving

.. math::

   \Delta V_{\mathrm{dec}}\approx11\ \mathrm{mV},
   \qquad
   n\approx\frac{11}{59.6}=\boxed{0.19}.

This is not physically credible for an ordinary p-n diode, whose ideality
factor is normally at least one in this model.  The likely explanation is a
factor-of-ten error in the printed voltage axis.  If the intended interval
were :math:`0.50\ \mathrm V`, the same construction would give
:math:`n\approx1.9`.  The defensible result is therefore to report both the
literal graph result and the apparent scale error.

Problem 3.5: Free-space LED link
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The drawing labels the **full** cone angle as :math:`20^\circ`; its half-angle
is :math:`\theta=10^\circ`.  At distance :math:`L`,

.. math::

   A_{\mathrm{beam}}=\pi(L\tan\theta)^2.

At :math:`L=1\ \mathrm m`,

.. math::

   A_{\mathrm{beam}}
   =\pi(\tan10^\circ)^2
   =0.09768\ \mathrm{m^2}.

The detector area is

.. math::

   A_D=(0.003\ \mathrm m)^2=9.0\times10^{-6}\ \mathrm{m^2}.

Assuming uniform power across the cone,

.. math::

   P_D=(10^{-4})
       \frac{9.0\times10^{-6}}{0.09768}
   =\boxed{9.21\times10^{-9}\ \mathrm W}.

The photodiode responsivity is

.. math::

   \mathcal R
   =\eta\frac{\lambda}{1239.84}
   =(0.75)\frac{620}{1239.84}
   =\boxed{0.375\ \mathrm{A/W}}.

Thus

.. math::

   I_{\mathrm{ph}}=\mathcal R P_D
   =(0.375)(9.21\ \mathrm{nW})
   =\boxed{3.46\ \mathrm{nA}}.

The stated :math:`100\ \Omega` load does not change the ideal photocurrent;
it gives :math:`V_{\mathrm{out}}\approx0.346\ \mu\mathrm V`.  Beam area grows
as :math:`L^2`, so at :math:`10\ \mathrm m`,

.. math::

   \boxed{I_{\mathrm{ph}}(10\ \mathrm m)
   =\frac{3.46\ \mathrm{nA}}{10^2}
   =34.6\ \mathrm{pA}}.
