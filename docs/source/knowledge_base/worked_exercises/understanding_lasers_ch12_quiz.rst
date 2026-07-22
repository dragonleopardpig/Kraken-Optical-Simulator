Understanding Lasers: Chapter 12 Quiz
=====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 12 quiz, printed pages 470--473.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**b**"
   "2", "**c**"
   "3", "**a**"
   "4", "**b**, :math:`1.008\ \mathrm{GB}`"
   "5", "**d**"
   "6", "**a**, :math:`5.0\times10^5` points/s"
   "7", "**d** in the printed key; see convention note"
   "8", "**c**"
   "9", "No listed answer; :math:`156{,}250` channels"
   "10", "**e**, :math:`2.56\ \mathrm s`"

Worked reasoning
----------------

#. **Long-life vent monitor: b.**  A rarely serviced diode laser can last much
   longer than an incandescent bulb.  Its directionality is also useful, but
   the reliability advantage is the book's intended reason.

#. **Scanner rejection of room light: c.**  A narrow optical filter passes the
   scanner's laser line while rejecting most broadband fluorescent light,
   greatly improving signal-to-background ratio.

#. **Why Blu-ray uses violet: a.**  Diffraction-limited spot size scales with
   wavelength, so a shorter wavelength reads smaller marks and closer tracks.

#. **Capacity from wavelength alone: b.**  Linear feature size scales as
   :math:`\lambda`, so areal density scales approximately as
   :math:`1/\lambda^2`:

   .. math::

      C_{DVD}=700\ \mathrm{MB}\left(\frac{780}{650}\right)^2
      =1008\ \mathrm{MB}=1.008\ \mathrm{GB}.

#. **Other DVD improvements: d.**  Higher-numerical-aperture optics reduce the
   spot further, while improved coding and compression store useful content
   more efficiently.

#. **Maximum lidar point rate: a.**  The farthest target requires a
   :math:`600\ \mathrm{m}` round trip:

   .. math::

      t_{rt}=\frac{2R}{c}=\frac{600}{3.00\times10^8}
      =2.00\ \mathrm{\mu s},

   .. math::

      f_{\max}=\frac1{t_{rt}}=5.00\times10^5\ \mathrm{s^{-1}}.

   The 1-ns pulse duration is negligible compared with this wait time.

#. **Distance scale of a 1-ns pulse: d in the key.**  Its free-space spatial
   length is

   .. math::

      \ell=c\tau=(3.00\times10^8)(10^{-9})=0.30\ \mathrm m.

   This matches choice d and the printed key.  In a two-way time-of-flight
   range calculation, however, :math:`R=ct/2`, so the pulse-duration-limited
   *range resolution* is often quoted as :math:`c\tau/2=0.15\ \mathrm m`.
   The choices do not include that value.

#. **Single-drum colour printing: c.**  The photoconductor is written and
   developed successively with different toner colours, transferring the
   colour separations during multiple passes.

#. **Voice channels in 10 Gbit/s: no listed answer.**  Direct division gives

   .. math::

      N=\frac{10\times10^9\ \mathrm{bit/s}}
              {64\times10^3\ \mathrm{bit/s}}
       =156{,}250.

   .. important:: Answer-key discrepancy

      The printed key selects **d**, :math:`178{,}000`, but that value does not
      follow from the two rates stated in the question.  Protocol overhead
      would reduce, not increase, the number of payload channels.

#. **Earth--Moon round trip: e.**

   .. math::

      t=\frac{2R}{c}
       =\frac{2(384{,}000\ \mathrm{km})}{299{,}792\ \mathrm{km/s}}
       =2.56\ \mathrm s.
