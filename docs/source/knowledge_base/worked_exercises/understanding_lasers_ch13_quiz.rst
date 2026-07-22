Understanding Lasers: Chapter 13 Quiz
=====================================

Source: Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth
edition (2019), Chapter 13 quiz, printed pages 512--514.  The questions are
paraphrased.

Quick answers
-------------

.. csv-table::
   :header: "Question", "Answer"

   "1", "**d**"
   "2", "**c**"
   "3", "**b**, :math:`80\ \mathrm J` under the key's assumption"
   "4", "**a**, diamond drilling"
   "5", "**a**, cutting"
   "6", "**e**, all listed uses"
   "7", "**b**, excimer lasers"
   "8", "**d**, dark hair and light skin"
   "9", "**b**, excimer lasers"
   "10", "**d**, diode-pumped solid-state and fibre lasers"
   "11", "**e**, all listed targets"
   "12", "**e**, the retina"

Worked reasoning
----------------

#. **Not an attraction of high-power lasers: d.**  Lasers can deliver intense,
   localized, noncontact energy under robotic control.  Burning chemical fuel
   is not an intrinsic advantage of the tool.

#. **Baby-bottle nipple drilling: c.**  A mechanical drill would deform the
   soft elastomer.  A laser applies energy without contact force and can make a
   repeatable small opening.

#. **Titanium energy absorption: b only with an unstated assumption.**  Energy
   delivered in one second is

   .. math::

      E_{\mathrm{incident}}=Pt=(1000\ \mathrm W)(1\ \mathrm s)=1000\ \mathrm J.

   The printed key's :math:`80\ \mathrm J` result assumes absorptance
   :math:`A=0.08`:

   .. math::

      E_{\mathrm{absorbed}}=A Pt=(0.08)(1000)(1)=80\ \mathrm J.

   .. important:: Missing data

      The question as printed does not state the titanium absorptance or point
      to a table containing it.  Without :math:`A`, the absorbed energy is
      underdetermined; only the incident :math:`1000\ \mathrm J` is known.

#. **Most concentrated peak power: a.**  Diamond drilling must remove an
   exceptionally hard, high-temperature material in a tiny region, demanding
   higher localized peak intensity than the surface-treatment choices.

#. **Gas-jet-assisted process: a.**  Cutting jets eject molten material from
   the kerf; oxygen can also add exothermic heating for suitable metals.

#. **Additive manufacturing: e.**  It spans hobby parts, rapid prototypes,
   otherwise unmanufacturable geometries, and economical small production
   runs such as replacement aircraft components.

#. **Semiconductor photolithography: b.**  Deep-ultraviolet KrF and ArF excimer
   lasers provide the short wavelengths used by major lithography generations.

#. **Best hair-removal contrast: d.**  Dark melanin-rich hair absorbs strongly
   while light skin absorbs less, maximizing selective follicle heating and
   reducing skin damage.

#. **LASIK source: b.**  An ArF excimer laser near :math:`193\ \mathrm{nm}`
   photoablates corneal tissue with shallow penetration and precise removal.

#. **Current weapon-development source: d.**  Modern programmes emphasize
   electrically powered diode-pumped bulk and fibre lasers rather than the
   large hazardous chemical-laser systems explored historically.

#. **Envisioned targets: e.**  Proposed defensive systems include rockets,
   artillery or mortar projectiles, drones, and small boats.

#. **Most vulnerable target: e.**  The eye focuses incoming light onto the
   retina, multiplying irradiance dramatically; far less incident energy can
   injure it than is needed to disable robust hardware.
