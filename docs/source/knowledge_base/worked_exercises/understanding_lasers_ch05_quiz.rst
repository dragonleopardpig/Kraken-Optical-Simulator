Understanding Lasers: Chapter 5 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 5 quiz, printed pages 165--167.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**a**, blue focal length is :math:`3.33\ \mathrm{cm}` shorter"
   "2", "**d**, about :math:`30\%`"
   "3", "**d**, about :math:`17.2\%`"
   "4", "**c**, magnesium fluoride"
   "5", "**b**, silicon"
   "6", "**b**, interference filter"
   "7", "**e**, :math:`173.5\ \mathrm{nm}`"
   "8", "**e**, about :math:`1996\ \mathrm{nm}`"
   "9", "**c**"
   "10", "**a**, semiconductor diode"
   "11", "**a**, silicon"
   "12", "**b**"

Worked reasoning
----------------

#. **Chromatic focal shift: a.**  For a symmetric thin biconvex lens,

   .. math::

      \frac1f=(n-1)\left(\frac1R-\frac1{-R}\right)
      =\frac{2(n-1)}R.

   Thus :math:`f_{400}=20/[2(0.60)]=16.67\ \mathrm{cm}` and
   :math:`f_{700}=20/[2(0.50)]=20.00\ \mathrm{cm}`.  The 400-nm focus
   is :math:`3.33\ \mathrm{cm}` shorter.

#. **Bare silicon reflection: d.**  Normal-incidence power reflectance is

   .. math::

      R=\left(\frac{n_2-n_1}{n_2+n_1}\right)^2
       =\left(\frac{3.42-1}{3.42+1}\right)^2=0.300.

#. **Reflection with an index-2 coating: d.**  Ignoring interference and
   multiplying interface transmissions,

   .. math::

      R_{12}=\left(\frac{2-1}{2+1}\right)^2=0.1111,
      \qquad
      R_{23}=\left(\frac{3.42-2}{3.42+2}\right)^2=0.0686,

   .. math::

      R_{\mathrm{total}}=1-(1-R_{12})(1-R_{23})
      =1-(0.8889)(0.9314)=0.172.

#. **Visible-window material: c.**  Magnesium fluoride transmits throughout
   the 0.4--0.7 micrometre band; the semiconductor choices have absorption
   edges that exclude part or all of it.

#. **Unsuitable 0.9--1.0 micrometre material: b.**  Silicon absorbs below its
   roughly :math:`1.1\ \mathrm{\mu m}` band-edge wavelength.  The other listed
   optical materials transmit in this band.

#. **Reject one narrow laser line: b.**  A narrow notch interference filter
   can reject the laser wavelength while passing nearby wavelengths.  A
   neutral-density filter would attenuate the whole band.

#. **Fourth harmonic: e.**  Harmonic frequency is multiplied by four, so
   wavelength is divided by four:

   .. math::

      \lambda_4=\frac{694\ \mathrm{nm}}4=173.5\ \mathrm{nm}.

#. **Difference-frequency wavelength: e.**

   .. math::

      \frac1{\lambda_d}=\left|\frac1{694\ \mathrm{nm}}
      -\frac1{1064\ \mathrm{nm}}\right|,qquad
      \lambda_d=1995.9\ \mathrm{nm}.

#. **Raman shifting: c.**  Raman interaction exchanges a modest vibrational
   energy with the medium, shifting the input frequency and wavelength rather
   than simply doubling or intensity-modulating it.

#. **Direct current modulation: a.**  A diode laser's carrier population and
   optical output respond directly and rapidly to drive current.

#. **Green detector: a.**  A silicon photodiode responds well at
   :math:`525\ \mathrm{nm}`; the other listed compound-semiconductor detectors
   are aimed mainly at longer wavelengths or are unsuitable absorbers there.

#. **Decibels: b.**  A decibel expresses a logarithmic power ratio:

   .. math::

      L_{\mathrm{dB}}=10\log_{10}\left(\frac{P_2}{P_1}\right).
