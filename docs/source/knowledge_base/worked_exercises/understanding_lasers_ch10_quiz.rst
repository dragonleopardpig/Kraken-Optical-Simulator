Understanding Lasers: Chapter 10 Quiz
=====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 10 quiz, printed pages 395--398.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**b**, direct-bandgap semiconductor"
   "2", "**a**, InGaAsP"
   "3", "**c**, 40% Ga, 10% Al, 50% As"
   "4", "**d**"
   "5", "**b**"
   "6", "**e**, all listed structures"
   "7", "**d**, VCSEL"
   "8", "**a**, InGaN diode"
   "9", "**c**, :math:`827\ \mathrm{nm}`"
   "10", "**d**, distributed feedback"
   "11", "**e**, AlGaN"
   "12", "**b**, AlGaInP"
   "13", "**e**, VCSEL"
   "14", "**d**, stacked arrays"
   "15", "**e**, :math:`3.1\ \mathrm{eV}`"

Worked reasoning
----------------

#. **Efficient diode-laser material: b.**  A direct bandgap lets an electron
   and hole recombine while conserving crystal momentum and emitting a photon.
   Indirect-gap materials usually lose energy nonradiatively through phonons.

#. **Quaternary III--V compound: a.**  InGaAsP contains four elements, all
   drawn from periodic-table groups III and V.  GaAlAs is ternary and GaAs is
   binary.

#. **Atomic fractions in Ga0.8Al0.2As: c.**  One formula unit contains
   :math:`0.8+0.2+1=2` atoms in normalized proportions.  Therefore

   .. math::

      x_{\mathrm{Ga}}=\frac{0.8}{2}=40\%,\quad
      x_{\mathrm{Al}}=\frac{0.2}{2}=10\%,\quad
      x_{\mathrm{As}}=\frac{1}{2}=50\%.

#. **Exciton: d.**  It is a bound electron--hole pair: the electron is excited
   relative to the filled valence band but has not recombined with the hole.

#. **Double-heterostructure advantage: b.**  Higher-bandgap layers confine
   injected carriers to the thin active layer, increasing the probability of
   radiative recombination.  They also help confine the optical mode.

#. **Structures possible in GaAlAs: e.**  The material system supports
   Fabry--Perot and distributed-feedback edge emitters, VCSELs, and gain chips
   used in external cavities.

#. **Shortest cavity: d.**  A VCSEL cavity runs vertically through only a few
   micrometres of epitaxial material, much shorter than edge-emitter or
   free-space cavities.

#. **High-definition optical-disc source: a.**  InGaN diodes emit violet-blue
   light, whose shorter wavelength focuses to the small spot required for
   high-density Blu-ray data.

#. **Bandgap wavelength: c.**  Using
   :math:`E(\mathrm{eV})\lambda(\mathrm{nm})\approx1240`,

   .. math::

      \lambda=\frac{1240\ \mathrm{eV\,nm}}{1.5\ \mathrm{eV}}
      =827\ \mathrm{nm}.

#. **Single-longitudinal-mode diode: d.**  A distributed-feedback grating
   selects one cavity mode across the gain region.

#. **Shortest-wavelength family: e.**  Wide-bandgap AlGaN reaches farther into
   the ultraviolet than GaInN, AlGaInP, GaAlAs, or InGaAsP.

#. **Red pointer diode: b.**  AlGaInP is the standard material family for
   efficient visible-red diode emission.

#. **Low-threshold, efficient, good-beam source: e.**  VCSELs combine a tiny
   active volume with strong mirrors and a circular, low-divergence output
   mode.

#. **Maximum efficient power without beam-quality priority: d.**  Stacking
   multiple diode arrays combines many broad emitting stripes and scales total
   power, at the cost of poorer spatial quality.

#. **Energy of a 400-nm photon: e.**

   .. math::

      E=\frac{1240\ \mathrm{eV\,nm}}{400\ \mathrm{nm}}
      =3.10\ \mathrm{eV}.

   Check: a shorter wavelength than :math:`1240\ \mathrm{nm}` must have more
   than :math:`1\ \mathrm{eV}` of energy.
