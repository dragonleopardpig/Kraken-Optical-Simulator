Chapter 24: Optical Fiber Communications
=========================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 24.

This chapter contains end-of-chapter problems but no boxed in-text exercises.

End-of-chapter problems
-----------------------

Problem 24.1-1 — Assessing fiber-system claims
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.

(a) 1300 nm usually beats 870 nm for silica loss and modal bandwidth, but cheap
short plastic/multimode links can favor 870 nm.  (b) 1550 nm has the lowest
silica loss and supports EDFAs, while 1300 nm can have lower dispersion in
ordinary fiber and cheaper components.  (c) Single-mode fiber removes modal
dispersion; its advantage is not inherently a lower material attenuation.
(d) Material and waveguide dispersion may cancel near 1312 nm, but source
linewidth, polarization-mode dispersion, and higher-order dispersion remain.
(e) Compound semiconductors are needed for efficient 1.3/1.55-micrometre
sources, not for passive fiber, and silicon detectors work near 870 nm.
(f) APDs add excess multiplication noise, yet their internal gain can overcome
receiver circuit noise and improve sensitivity.  Thus none of the six absolute
claims is universally true.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 24.1-2 — Choosing compatible components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.


**Definitions and setup.**  No new mathematical symbols are introduced.  Technical terms retain their chapter definitions, and each comparison is conditional on the wavelength, material, geometry, and operating assumptions stated below.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  Evaluate each claim or design choice against the applicable physical definition, then state the assumption that controls the conclusion.

(a) Use a narrow-linewidth 1550-nm InGaAsP laser, single-mode low-loss (often
dispersion-managed) silica fiber, EDFAs, and an InGaAs p-i-n or APD receiver.
(b) A visible/870-nm LED, plastic or large-core multimode fiber, and silicon
p-i-n diode minimize cost; no amplifier is needed.  (c) A common 500-Mb/s LAN
choice is an 850-nm VCSEL, graded-index multimode fiber, and silicon p-i-n
receiver.  (d) For temperature margin over 1 km, choose a stabilized 1310-nm
InGaAsP laser, silica fiber operated near its zero-dispersion band, and an
InGaAs p-i-n receiver; the laser's narrow spectrum avoids temperature-driven
LED linewidth penalties.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

**Check.**  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 24.2-1 — Plastic-fiber distance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The 1-mW source is 0 dBm.  After two 3-dB couplers, the fiber may consume
:math:`0-6-(-20)=14` dB.  At 0.5 dB/m,
:math:`\boxed{L_{max}=28\ \mathrm m}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-2-1-result

   \boxed{L_{max}=28\ \mathrm m}


**Check.**  Equation :eq:`fop-problem-24-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.2-2 — LED-link distance with two receivers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Photon-per-bit sensitivity converts through
:math:`P_r=N_ph(hc/\lambda)R_b`.  At 10 Mb/s the p-i-n value is
:math:`\boxed{-49.42\ \mathrm{dBm}}`; its loss budget after 4-dB couplers and
6-dB margin permits six whole 1-km segments (21 dB fiber plus five dB of
connectors), so :math:`\boxed{L=6\ \mathrm{km}}`.  The APD value is
:math:`\boxed{-65.45\ \mathrm{dBm}}` and similarly permits
:math:`\boxed{L=10\ \mathrm{km}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-2-2-result

   \boxed{L=10\ \mathrm{km}}


**Check.**  Equation :eq:`fop-problem-24-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.2-3 — Attenuation-limited bit rate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`power and decibel conversions <fop-formula-power-decibels>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The 50-km fiber, fixed losses, and margin consume
:math:`10+8+6=24` dB, leaving :math:`7.962\ \mu\mathrm W`.  Dividing by 1000
photon energies per bit at 1550 nm gives
:math:`\boxed{R_b=62.1\ \mathrm{Gb/s}}` at BER :math:`10^{-9}`.  Under the
ideal Poisson scaling, changing BER to :math:`10^{-11}` multiplies the photon
requirement by
:math:`\ln(1/2\times10^{-11})/\ln(1/2\times10^{-9})=1.230`, giving
:math:`\boxed{50.5\ \mathrm{Gb/s}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-2-3-result

   \boxed{50.5\ \mathrm{Gb/s}}


**Check.**  Equation :eq:`fop-problem-24-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.2-4 — Analog APD link
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`power and decibel conversions <fop-formula-power-decibels>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The sinusoidal signal mean square is
:math:`(G\mathcal RmP)^2/2`; APD shot-noise variance is
:math:`2eBG^2F\mathcal RP`.  Their ratio gives

.. math::
   :label: fop-problem-24-2-4-eq-1

   P_{min}={4eBF\,\mathrm{SNR}\over m^2\mathcal R}
   =\boxed{2.563\ \mu\mathrm W}=-25.91\ \mathrm{dBm}.

Internal gain cancels in this photon-noise-limited case.  The 100-microwatt
source supplies 15.91 dB of fiber loss, hence
:math:`\boxed{L=6.36\ \mathrm{km}}`.

**Check.**  Equation :eq:`fop-problem-24-2-4-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.2-5 — Dispersion time budget
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Ordinary fiber broadens by
:math:`t_f=D_\lambda L\Delta\lambda=340` ps.  The fiber-only criterion gives
:math:`R_b\le0.25/t_f=\boxed{0.735\ \mathrm{Gb/s}}`.  Root-sum-square with
20-ps source and 100-ps receiver gives :math:`t_s=355.0` ps and the system
criterion :math:`R_b\le0.70/t_s=\boxed{1.97\ \mathrm{Gb/s}}`.  With
:math:`D_\lambda=1`, :math:`t_f=20` ps and :math:`t_s=103.9` ps, giving
:math:`\boxed{12.5\ \mathrm{Gb/s}}` and :math:`\boxed{6.74\ \mathrm{Gb/s}}`,
respectively.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-2-5-result

   \boxed{6.74\ \mathrm{Gb/s}}


**Check.**  Equation :eq:`fop-problem-24-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.3-1 — WDM channels in C and O bands
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use frequency, not wavelength, span:
:math:`\Delta\nu=c(1/\lambda_{min}-1/\lambda_{max})`.  The C band spans
4.382 THz and the O band 17.495 THz.  Counting both endpoint slots gives
:math:`\boxed{\lfloor\Delta\nu/75\ \mathrm{GHz}\rfloor+1=59}` C-band and
:math:`\boxed{234}` O-band carriers (58 and 233 are the corresponding numbers
of 75-GHz intervals).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-3-1-result

   \boxed{234}


**Check.**  Equation :eq:`fop-problem-24-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.3-2 — Broadcast-star node limit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

A source-to-receiver route traverses two 2-km fiber legs (1.2 dB), two 1-dB
connector losses, 3-dB star excess loss, and a 5-dB margin.  From a 0-dBm
source to a -35-dBm receiver,
:math:`10\log_{10}N\le35-1.2-2-3-5=23.8` dB.  Therefore
:math:`N\le239.9` and :math:`\boxed{N_{max}=239}` whole nodes.  If the stated
1-dB connector loss is intended for the entire end-to-end route rather than
per star leg, the same budget gives 301 nodes.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-24-3-2-result

   \boxed{N_{max}=239}


**Check.**  Equation :eq:`fop-problem-24-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 24.3-3 — Six-channel four-node ring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Regard the six wavelengths as the six edges of a complete graph on four
nodes; each node drops its three incident edges.  With node 1 assigned
:math:`\{\lambda_1,\lambda_2,\lambda_3\}`, a valid allocation is

.. math::
   :label: fop-problem-24-3-3-eq-1

   \boxed{N_2=\{\lambda_1,\lambda_4,\lambda_5\},\quad
   N_3=\{\lambda_2,\lambda_4,\lambda_6\},\quad
   N_4=\{\lambda_3,\lambda_5,\lambda_6\}}.

Every node pair shares exactly one channel and no third node drops that
channel, so intermediate nodes pass it through.

**Check.**  Equation :eq:`fop-problem-24-3-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.
