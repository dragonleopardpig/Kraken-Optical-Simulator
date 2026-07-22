Understanding Lasers: Chapter 6 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 6 quiz, printed pages 213--216.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**d** in the printed key; **b** under the book's taxonomy"
   "2", "**c**"
   "3", "**d**"
   "4", "**e**"
   "5", "**d**"
   "6", "**b**"
   "7", "**e**"
   "8", "**a**"
   "9", "**d**, mode locking"
   "10", "**b**, about :math:`24\ \mathrm{fs}`"
   "11", "**e**, :math:`441\ \mathrm{ns}`"
   "12", "**a**, :math:`532\ \mathrm{nm}`"

Worked reasoning
----------------

#. **Excluded from the book's solid-state-laser category: d.**  The
   neodymium-doped glass slab is actually a solid-state laser material, so the
   printed key's selection of **d** appears inconsistent with both the chapter
   and standard terminology.  A gallium-arsenide diode, **b**, is normally put
   in the separate *semiconductor laser* category used by this book.

   .. important:: Answer-key discrepancy

      The printed key says **d**, but **b** is the defensible answer under the
      book's classification.  The slab, fibre, ruby, and Nd:YVO4 choices are
      all solid-state gain media.

#. **Dielectric: c.**  In this context it is a transparent, electrically
   insulating crystal.  Dielectrics polarize in an electric field but do not
   conduct current like metals.

#. **Not a diode-pump advantage: d.**  Diodes are efficient, wavelength
   matched, and easy to couple to fibres, but flashlamps can deliver much
   higher single-pulse energy.

#. **Requirement for electrical pumping: e.**  Current must pass through the
   gain material, so electrical conductivity is essential.

#. **Laser oscillator condition: d.**  A resonant cavity must have enough
   round-trip gain to replace internal loss and useful output coupling:

   .. math::

      G_{\mathrm{rt}}\ge L_{\mathrm{internal}}+L_{\mathrm{output}}.

#. **Optical amplifier: b.**  Stimulated emission amplifies a signal in one or
   more passes without requiring resonant feedback.

#. **Wavelength-multiplexed capacity: e.**  Every channel lying within the
   amplifier gain band can be amplified simultaneously, subject to saturation
   and gain-flatness limits.

#. **Q switching: a.**  A low-cavity-Q state suppresses oscillation while the
   pump stores energy in the upper level.  Switching to high Q releases that
   stored energy as a short, energetic pulse.

#. **Shortest pulses: d.**  Mode locking fixes the phase relationship among
   many longitudinal modes, so they add into ultrashort pulses.

#. **Transform-limited 40-nm-bandwidth pulse: b.**  First convert wavelength
   bandwidth near :math:`800\ \mathrm{nm}` to frequency bandwidth:

   .. math::

      \Delta\nu\approx\frac{c\,\Delta\lambda}{\lambda^2}
      =\frac{(2.998\times10^8)(40\times10^{-9})}
             {(800\times10^{-9})^2}
      =1.87\times10^{13}\ \mathrm{Hz}.

   For a transform-limited Gaussian pulse,

   .. math::

      \Delta t\approx\frac{0.441}{\Delta\nu}
      =2.35\times10^{-14}\ \mathrm s\approx24\ \mathrm{fs}.

#. **One-megahertz bandwidth pulse: e.**  The same time-bandwidth product gives

   .. math::

      \Delta t\approx\frac{0.441}{10^6\ \mathrm{Hz}}
      =4.41\times10^{-7}\ \mathrm s=441\ \mathrm{ns}.

#. **Frequency-doubled Nd:YAG: a.**  Doubling frequency halves wavelength:
   :math:`1064/2=532\ \mathrm{nm}`.
