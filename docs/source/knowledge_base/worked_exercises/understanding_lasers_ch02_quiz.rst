Understanding Lasers: Chapter 2 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 2 quiz, printed pages 55--57.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**b**, :math:`2.83\times10^{13}\ \mathrm{Hz}`"
   "2", "**c**, :math:`6.63\times10^{-20}\ \mathrm{J}`"
   "3", "**b**, :math:`3.00\ \mathrm{\mu m}`"
   "4", "**a**, destructive"
   "5", "**c**, :math:`656\ \mathrm{nm}`"
   "6", "**d**, :math:`333\ \mathrm{nm}`"
   "7", "**d**, :math:`17.5^\circ`"
   "8", "**e**, none; :math:`T=0.0625`"
   "9", "**d**, :math:`20\ \mathrm{cm}`"
   "10", "**c**, magnitude :math:`1`"

Worked reasoning
----------------

#. **Frequency from wavelength: b.**  Use :math:`c=f\lambda`:

   .. math::

      f=\frac{2.998\times10^8\ \mathrm{m/s}}
              {10.6\times10^{-6}\ \mathrm m}
       =2.83\times10^{13}\ \mathrm{Hz}.

#. **Photon energy: c.**  Planck's relation gives

   .. math::

      E=hf=(6.626\times10^{-34}\ \mathrm{J\,s})(10^{14}\ \mathrm{Hz})
       =6.63\times10^{-20}\ \mathrm J.

#. **Wavelength from frequency: b.**

   .. math::

      \lambda=\frac{c}{f}=\frac{2.998\times10^8}{10^{14}}
      =2.998\times10^{-6}\ \mathrm m\approx3\ \mathrm{\mu m}.

#. **Equal waves separated by 180 degrees: a.**  One field is the negative of
   the other at every instant, so their amplitudes cancel: destructive
   interference.

#. **Hydrogen transition: c.**  The Rydberg relation for the magnitude of the
   :math:`n=2\leftrightarrow3` transition is

   .. math::

      \frac{1}{\lambda}=R_H\left(\frac{1}{2^2}-\frac{1}{3^2}\right)
      =R_H\frac{5}{36}, \qquad \lambda\approx656\ \mathrm{nm}.

#. **Two absorbed photons followed by one emitted photon: d.**  Energies add,
   and :math:`E=hc/\lambda`:

   .. math::

      \frac{1}{\lambda_e}=\frac{1}{500\ \mathrm{nm}}
      +\frac{1}{1000\ \mathrm{nm}}, \qquad
      \lambda_e=333\ \mathrm{nm}.

#. **Refraction: d.**  Snell's law gives

   .. math::

      n_1\sin\theta_1=n_2\sin\theta_2,qquad
      \theta_2=\sin^{-1}\!\left(\frac{1.2\sin30^\circ}{2.0}\right)
      =17.46^\circ.

#. **Transmission through four half-transmission layers: e.**  A
   :math:`2\ \mathrm{cm}` sample contains four :math:`0.5\ \mathrm{cm}`
   layers, so Beer--Lambert multiplication gives

   .. math::

      T=(0.5)^4=0.0625=6.25\%.

   No listed numerical choice equals this result.

   .. important:: Answer-key discrepancy

      The printed key selects **c**, :math:`0.018`.  That would follow from
      treating :math:`0.5\ \mathrm{cm}` as a :math:`1/e` absorption length,
      not from the stated fact that it transmits one half.  For the wording as
      printed, **e (none of the above)** is correct.

#. **Thin-lens image distance: d.**

   .. math::

      \frac1f=\frac1{d_o}+\frac1{d_i},\qquad
      \frac1{d_i}=\frac1{10}-\frac1{20}=\frac1{20}\ \mathrm{cm^{-1}},

   hence :math:`d_i=20\ \mathrm{cm}`.

#. **Image-to-object size ratio: c.**  The transverse magnification is
   :math:`m=-d_i/d_o=-1`; the minus sign means inverted, while the requested
   size ratio is :math:`|m|=1`.
