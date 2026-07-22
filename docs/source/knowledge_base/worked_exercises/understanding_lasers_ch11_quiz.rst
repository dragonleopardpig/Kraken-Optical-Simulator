Understanding Lasers: Chapter 11 Quiz
=====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 11 quiz, printed pages 421--423.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**a**"
   "2", "**e**, about 20--40 nm"
   "3", "**e**"
   "4", "**e**, about :math:`5.85\ \mathrm{\mu m}`"
   "5", "**b**, signal wavelength"
   "6", "**c**, optical parametric amplifier"
   "7", "**d**, laser-produced tin plasma"
   "8", "**a**"
   "9", "**d**, all listed bands"
   "10", "**a**"

Worked reasoning
----------------

#. **Dye tunability: a.**  Each electronic state has many closely spaced
   molecular vibrational sublevels, producing a broad gain band from which a
   cavity can select different wavelengths.

#. **Typical single-dye tuning span: e.**  An individual dye commonly covers
   a few tens of nanometres; changing dyes extends the total accessible range.

#. **Dye-laser linewidth: e.**  The broad dye gain does not uniquely set output
   linewidth.  Cavity length, gratings, etalons, and other selection optics do.

#. **OPA idler wavelength: e.**  Parametric energy conservation is

   .. math::

      \nu_p=\nu_s+\nu_i,

   so

   .. math::

      \frac1{\lambda_i}=\frac1{1064\ \mathrm{nm}}
      -\frac1{1300\ \mathrm{nm}},\qquad
      \lambda_i=5.85\times10^3\ \mathrm{nm}\approx5.85\ \mathrm{\mu m}.

#. **OPO tuning reference: b.**  The resonator normally selects and tunes the
   signal wave; the idler then follows from energy conservation with the pump.

#. **Broadest tuning source: c.**  An optical parametric amplifier has no
   resonant signal cavity restricting its range and can cover an exceptionally
   broad span through phase matching.

#. **Shorter-than-193-nm lithography source: d.**  Extreme-ultraviolet systems
   use droplets of tin vaporized into plasma by high-power CO2-laser pulses.

#. **Free-electron-laser emitter: a.**  A relativistic electron beam oscillates
   through the alternating magnetic field of an undulator and radiates.

#. **FEL spectral bands: d.**  By changing electron energy and undulator
   parameters, FELs can operate from infrared through ultraviolet to X-rays.

#. **Energy extraction: a.**  The periodic magnetic field bends the electron
   trajectories.  Their radiation interacts coherently with the bunched beam,
   transferring electron kinetic energy into light.
