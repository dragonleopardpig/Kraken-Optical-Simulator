Understanding Lasers: Chapter 3 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 3 quiz, printed pages 91--93.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**b**"
   "2", "**a**"
   "3", "**c**"
   "4", "**e**, :math:`1.221`"
   "5", "**c**, :math:`3\%`"
   "6", "**e**, :math:`1.36\times10^6` wavelengths"
   "7", "**a**, about :math:`0.0013\ \mathrm{nm}`"
   "8", "**b**, one nodal minimum"
   "9", "**c**"
   "10", "**a**"
   "11", "**b**, :math:`28.5\%`"
   "12", "**b**, about :math:`9.7\%`"

Worked reasoning
----------------

#. **Four-level advantage: b.**  Its lower laser level is above the ground
   state and empties rapidly.  A population inversion therefore needs far
   fewer excited particles than in a three-level system.

#. **Metastable state: a.**  Its long lifetime lets excited particles
   accumulate, making it suitable as an upper laser level.

#. **Growth by stimulated emission: c.**  Existing photons stimulate more
   matching photons, which can stimulate still more; unsaturated gain is
   exponential rather than merely additive.

#. **Amplification over 20 cm: e.**  For small-signal gain coefficient
   :math:`g=0.01\ \mathrm{cm^{-1}}`,

   .. math::

      G=e^{gL}=e^{(0.01)(20)}=e^{0.2}=1.221.

#. **Steady-state round-trip gain: c.**  Gain must replace the 2% internal loss
   and the 1% useful output coupling, or approximately :math:`3\%` total.

#. **Round-trip length in wavelengths: e.**

   .. math::

      N=\frac{2L}{\lambda}
       =\frac{0.60\ \mathrm m}{442\times10^{-9}\ \mathrm m}
       =1.36\times10^6.

#. **Adjacent longitudinal wavelengths: a.**  Near wavelength :math:`\lambda`,
   cavity resonances are separated by

   .. math::

      \Delta\lambda\approx\frac{\lambda^2}{2L}
      =\frac{(632.8\times10^{-9}\ \mathrm m)^2}{0.30\ \mathrm m}
      =1.34\times10^{-12}\ \mathrm m=0.00134\ \mathrm{nm}.

#. **TEM01 minimum: b.**  This first-order transverse mode has one internal
   nodal line separating its two bright lobes.

#. **Heating cannot create the inversion: c.**  Thermal equilibrium follows a
   Boltzmann distribution with fewer particles at higher energy.  Selective
   optical or electrical pumping can drive a nonequilibrium inversion.

#. **Atmospheric absorption: a.**  It reduces power after the beam leaves the
   laser, not the laser's electrical-to-optical conversion efficiency.  The
   other choices waste excitation inside the conversion chain.

#. **Cascaded wall-plug efficiency: b.**  Successive efficiencies multiply:

   .. math::

      \eta_{\mathrm{wall}}=(0.95)(0.50)(0.60)=0.285=28.5\%.

#. **Quantum defect: b.**  With :math:`E=hc/\lambda`, the useful energy ratio
   is :math:`E_l/E_p=\lambda_p/\lambda_l`.  Thus

   .. math::

      q=1-\frac{E_l}{E_p}
       =1-\frac{975}{1080}=0.0972\approx9.7\%,

   which rounds to the listed :math:`9.75\%`.
