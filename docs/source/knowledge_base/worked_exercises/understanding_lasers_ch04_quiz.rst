Understanding Lasers: Chapter 4 Quiz
====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 4 quiz, printed pages 123--126.  Approximations below
follow the conventions used by the book.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**b**, :math:`168\ \mathrm{\mu m}`"
   "2", "**e**, :math:`1.5\ \mathrm{km}`"
   "3", "**a**"
   "4", "**e**"
   "5", "**c**, :math:`1.58\ \mathrm m`"
   "6", "**e**, :math:`76\ \mathrm{km}`"
   "7", "**b**, :math:`48\ \mathrm m`"
   "8", "**d**, :math:`1.46\ \mathrm m`"
   "9", "**c**, :math:`1.3\ \mathrm{mm}`"
   "10", "**b**, :math:`5.25\%`"
   "11", "**d**, :math:`90.7\%`"
   "12", "**a**, :math:`1\ \mathrm W`"

Worked reasoning
----------------

#. **Coherence length from wavelength spread: b.**  Using the chapter's
   convention,

   .. math::

      L_c\approx\frac{\lambda^2}{2\Delta\lambda}
      =\frac{(820\ \mathrm{nm})^2}{2(2\ \mathrm{nm})}
      =168\ \mathrm{\mu m}.

#. **Coherence length from frequency spread: e.**

   .. math::

      L_c\approx\frac{c}{2\Delta f}
      =\frac{2.998\times10^8}{2\times10^5}
      =1.50\times10^3\ \mathrm m.

#. **Doppler broadening: a.**  Different line-of-sight atomic velocities
   produce different Doppler shifts and widen the observed line.

#. **Number of longitudinal modes: e.**  It is roughly gain bandwidth divided
   by cavity-mode spacing, so there is no universal fixed count.

#. **Near-field distance: c.**  The chapter uses the order-of-magnitude
   Rayleigh-range estimate

   .. math::

      z_R\approx\frac{D^2}{\lambda}
      =\frac{(10^{-3}\ \mathrm m)^2}{632.8\times10^{-9}\ \mathrm m}
      =1.58\ \mathrm m.

   A Gaussian-beam definition using waist radius instead of beam diameter has
   a different numerical factor, so the convention must be stated.

#. **Unexpanded beam at geosynchronous distance: e.**  Taking
   :math:`1\ \mathrm{mrad}` as the half-angle,

   .. math::

      d\approx2L\theta=2(38\times10^6\ \mathrm m)(10^{-3})
      =76\ \mathrm{km}.

#. **One-metre diffraction-limited transmitter: b.**

   .. math::

      \theta\approx\frac{\lambda}{D}=6.328\times10^{-7}\ \mathrm{rad},
      \qquad d\approx2L\theta\approx48\ \mathrm m.

#. **Bare diode spot: d.**  With a 20-degree half-angle,

   .. math::

      d=2L\tan20^\circ=2(2\ \mathrm m)\tan20^\circ=1.46\ \mathrm m.

#. **Lens aperture for a 1-mm spot: c.**  The quiz uses
   :math:`s\approx\lambda L/D`, hence

   .. math::

      D\approx\frac{\lambda L}{s}
      =\frac{(650\times10^{-9}\ \mathrm m)(2\ \mathrm m)}{10^{-3}\ \mathrm m}
      =1.3\ \mathrm{mm}.

   Exact Airy-disk or Gaussian-beam definitions introduce order-one factors.

#. **Maximum wall-plug efficiency: b.**

   .. math::

      \eta=(0.70)(0.25)(0.60)(0.50)=0.0525=5.25\%.

#. **Ideal pump conversion: d.**  One pump photon produces at most one laser
   photon, so the energy ratio is

   .. math::

      \eta_{\max}=\frac{E_l}{E_p}=\frac{\lambda_p}{\lambda_l}
      =\frac{980}{1080}=0.907=90.7\%.

#. **Average pulsed power: a.**  First find pulse energy and then multiply by
   repetition rate:

   .. math::

      E_p=(500\times10^3\ \mathrm W)(10\times10^{-9}\ \mathrm s)
      =5\times10^{-3}\ \mathrm J,

   .. math::

      P_{\mathrm{avg}}=E_p f_r=(5\times10^{-3})(200)=1\ \mathrm W.
