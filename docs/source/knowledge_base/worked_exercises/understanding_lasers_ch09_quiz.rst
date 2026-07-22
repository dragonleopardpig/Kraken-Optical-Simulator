Understanding Lasers: Chapter 9 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 9 quiz, printed pages 337--339.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**d**"
   "2", "**a**"
   "3", "**b**"
   "4", "**e**, ytterbium"
   "5", "**b**, fibre Bragg gratings"
   "6", "**b**, Nd:YAG"
   "7", "**a**, :math:`7.14\%`"
   "8", "**d**, :math:`2.5\ \mathrm{kW}` saved"
   "9", "**c**"
   "10", "**a**"
   "11", "**b**, erbium"
   "12", "**e**, no added element"

Worked reasoning
----------------

#. **Not a fibre-laser advantage: d.**  The long, small core gives excellent
   cooling and beam quality but nonlinearities and optical damage limit very
   high pulse energy.

#. **Inner cladding: a.**  It accepts pump light from a comparatively large
   area and guides it along the doped core, where repeated overlap allows
   absorption.

#. **Location of active species: b.**  Rare-earth ions are doped into the
   light-guiding core so pump and signal fields overlap them along the fibre.

#. **Highest-power rare-earth fibre laser: e.**  Ytterbium combines efficient
   diode pumping, a small quantum defect, and a useful emission band near one
   micrometre.

#. **Cavity reflectors: b.**  Fibre Bragg gratings written into the fibre
   provide wavelength-selective reflection without free-space alignment.

#. **Same wavelength replacement: b.**  Ytterbium fibre gain includes
   :math:`1064\ \mathrm{nm}`, the main Nd:YAG wavelength.

#. **Thulium-to-holmium quantum defect: a.**

   .. math::

      q=1-\frac{E_l}{E_p}=1-\frac{\lambda_p}{\lambda_l}
      =1-\frac{1950}{2100}=0.07143=7.14\%.

#. **Input-power saving: d.**

   .. math::

      P_{20\%}=\frac{1\ \mathrm{kW}}{0.20}=5\ \mathrm{kW},\qquad
      P_{40\%}=\frac{1\ \mathrm{kW}}{0.40}=2.5\ \mathrm{kW},

   so the more efficient laser saves :math:`2.5\ \mathrm{kW}` of input.

#. **Why 50-fs pulses are possible: c.**  A short transform-limited pulse
   requires many phase-locked frequencies, hence broad emission bandwidth.

#. **Long-wavelength silica limit: a.**  Multiphonon absorption in silica rises
   strongly beyond roughly two micrometres, motivating fluoride and other
   non-silica hosts.

#. **Telecommunications amplifier dopant: b.**  Erbium gain around
   :math:`1550\ \mathrm{nm}` overlaps the low-loss window of silica fibre.

#. **Raman amplifier dopant: e.**  Raman gain comes from the host glass's
   vibrational response and a strong pump; no rare-earth active species is
   required.
