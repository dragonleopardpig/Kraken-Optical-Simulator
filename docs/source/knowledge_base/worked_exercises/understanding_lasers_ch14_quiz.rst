Understanding Lasers: Chapter 14 Quiz
=====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 14 quiz, printed pages 540--542.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**c**"
   "2", "**a**"
   "3", "**a**"
   "4", "**d**"
   "5", "**b**"
   "6", "**c**, surface plasmons"
   "7", "**a**, :math:`1\ \mathrm{mJ}`"
   "8", "No listed answer; characteristic size about :math:`1\ \mathrm{\mu m}`"
   "9", "**e**, :math:`0.170\ \mathrm{mrad}`"
   "10", "**a**, about :math:`6\ \mathrm{mm}`"

Worked reasoning
----------------

#. **Doppler-free spectroscopy: c.**  Counterpropagating beams address atoms
   with opposite Doppler shifts.  Selecting the common response cancels
   first-order Doppler broadening without physically stopping every atom.

#. **Frequency-comb source: a.**  A periodic train of phase-coherent short
   pulses has a Fourier spectrum of evenly spaced narrow frequency teeth.

#. **Laser cooling: a.**  Properly detuned light is preferentially absorbed by
   atoms moving toward a beam.  Repeated absorption and random re-emission
   remove net momentum and kinetic energy.

#. **Bose--Einstein condensate: d.**  Below the critical temperature, a
   macroscopic fraction of bosonic atoms occupies the same lowest quantum
   state.

#. **Gravitational-wave detection: b.**  Long laser interferometers compare
   optical path lengths to detect extraordinarily small relative motions of
   suspended end mirrors.

#. **Subwavelength nanolaser: c.**  Surface plasmons are collective electron
   oscillations confined near a metal--dielectric boundary and can support
   optical modes smaller than the free-space diffraction volume.

   .. important:: Answer-key discrepancy

      The printed key selects **b**, but Section 14.8 explains that
      quantum-dot lasers are larger devices whose active layers contain one or
      more dots; they are not made by forcing a single electron to oscillate.
      Section 14.8.3 explicitly identifies surface-plasmon devices as capable
      of operating in less than a cubic wavelength, so **c** is supported by
      the chapter itself.

#. **Petawatt for one attosecond: a.**

   .. math::

      E=P\Delta t=(10^{15}\ \mathrm W)(10^{-18}\ \mathrm s)
      =10^{-3}\ \mathrm J=1\ \mathrm{mJ}.

#. **Spot for :math:`10^{23}\ \mathrm{W/cm^2}`: no listed answer.**  Required
   area is

   .. math::

      A=\frac{P}{I}=\frac{10^{15}\ \mathrm W}
                             {10^{23}\ \mathrm{W/cm^2}}
       =10^{-8}\ \mathrm{cm^2}.

   A square spot would have width
   :math:`\sqrt A=10^{-4}\ \mathrm{cm}=1\ \mathrm{\mu m}`; an equal-area
   circular spot would have diameter :math:`1.13\ \mathrm{\mu m}`.

   .. important:: Answer-key discrepancy

      None of the choices is near :math:`1\ \mathrm{\mu m}`.  The printed key
      selects **e**, :math:`0.03\ \mathrm{mm}`, which would produce only about
      :math:`10^{20}\ \mathrm{W/cm^2}` for a one-petawatt beam.  The key and
      the stated :math:`10^{23}\ \mathrm{W/cm^2}` cannot both be correct.

#. **Mars-to-Earth divergence: e.**  To cover Earth's diameter at distance
   :math:`L`,

   .. math::

      \theta\approx\frac{D_E}{L}
      =\frac{12{,}800\ \mathrm{km}}{75\times10^6\ \mathrm{km}}
      =1.71\times10^{-4}\ \mathrm{rad}=0.171\ \mathrm{mrad}.

#. **Diffraction-limited mirror: a.**

   .. math::

      D\approx\frac{\lambda}{\theta}
       =\frac{1.0\times10^{-6}\ \mathrm m}{1.71\times10^{-4}}
       =5.85\times10^{-3}\ \mathrm m\approx6\ \mathrm{mm}.

   Substitution back into :math:`\theta\approx\lambda/D` returns the required
   :math:`0.17\ \mathrm{mrad}` divergence.
