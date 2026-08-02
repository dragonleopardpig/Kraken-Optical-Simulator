Chapter 23: Optical Interconnects and Switches
===============================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 23.

In-text exercises
-----------------

Exercise 23.1-1 — Interconnection capacity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-23-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_23_01_01.svg
   :alt: Illustrated calculation map for Exercise 23.1-1, Interconnection capacity
   :align: center
   :width: 95%

   **Figure 129 — Exercise 23.1-1: Interconnection capacity.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

An aperture of width :math:`a` contains :math:`Ba` independent grating
samples in either transverse coordinate, hence :math:`(Ba)^2` independent
space-frequency cells.  Assigning :math:`M` directions to each of :math:`L`
inputs consumes :math:`ML` cells, proving :math:`\boxed{ML\le(Ba)^2}`.  If
every input is connected to every output, the maximum density is therefore
:math:`\boxed{B^2=10^6\ \mathrm{interconnections/mm^2}}` for 1000 lines/mm.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-23-1-1-result

   \boxed{B^2=10^6\ \mathrm{interconnections/mm^2}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-23-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 23.1-2 — Separable logarithmic map
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-23-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_23_01_02.svg
   :alt: Illustrated calculation map for Exercise 23.1-2, Separable logarithmic map
   :align: center
   :width: 95%

   **Figure 130 — Exercise 23.1-2: Separable logarithmic map.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiate the proposed phase:

.. math::
   :label: fop-exercise-23-1-2-eq-1

   {\partial\phi\over\partial x}={2\pi\over\lambda d}(\ln x-x),\qquad
   {\partial\phi\over\partial y}={2\pi\over\lambda d}(\ln y-y).

Equation (23.1-7) then gives :math:`x'=x+(\lambda d/2\pi)\phi_x=\ln x`
and likewise :math:`y'=\ln y`, which proves the map.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Equation :eq:`fop-exercise-23-1-2-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Exercise 23.4-1 — Bistable nonlinearities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-23-4-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_23_04_01.svg
   :alt: Illustrated calculation map for Exercise 23.4-1, Bistable nonlinearities
   :align: center
   :width: 95%

   **Figure 131 — Exercise 23.4-1: Bistable nonlinearities.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each candidate plot :math:`y(x)=x/\eta(x)` and locate folds from
:math:`dy/dx=0`; two folds delimit a three-valued output interval.  Working
choices are (a) :math:`a=0.2`, (b) :math:`a=5,\theta=0`, (c)
:math:`\theta=0`, (d) :math:`a=0.5`, and (e) :math:`a=10`.  For example,
case (e) has
:math:`y=x(x+a)^2/(x+1)^2` and its stationary numerator is
:math:`x^2+(3-a)x+a`; at :math:`a=10` the folds are exactly
:math:`\boxed{x=2,5}`.  The same derivative test, rather than visual guesswork,
verifies the other four plots.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-23-4-1-result

   \boxed{x=2,5}


**Step 5 — Check.**  Equation :eq:`fop-exercise-23-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 23.1-3 — Conformal-map hologram
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For a single continuous phase mask, Eq. (23.1-7) would require
:math:`\phi_x\propto\ln r-x` and :math:`\phi_y\propto\tan^{-1}(y/x)-y`.
But

.. math::
   :label: fop-problem-23-1-3-eq-1

   \partial_y(\ln r-x)={y\over r^2},\qquad
   \partial_x[\tan^{-1}(y/x)-y]=-{y\over r^2}.

The mixed derivatives disagree, so :math:`\boxed{\text{no scalar phase
function exists for this map in one thin hologram}}`.  It requires at least a
two-element coordinate transformer (or a segmented/nonlocal implementation);
the curl test is the essential design result.

**Check.**  Equation :eq:`fop-problem-23-1-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 23.2-1 — Four-channel cascaded MZIs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Near :math:`\lambda_0`, :math:`\Delta\nu=c\Delta\lambda/\lambda_0^2=
24.96` GHz.  Adjacent channels must swap ports in the first MZI, so
:math:`\Delta d=c/(2n\Delta\nu)=\boxed{2.612\ \mathrm{mm}}`.  Each second-
stage MZI separates channels spaced by :math:`2\Delta\nu`, so both use
:math:`\boxed{1.306\ \mathrm{mm}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-2-1-result

   \boxed{1.306\ \mathrm{mm}}


**Check.**  Equation :eq:`fop-problem-23-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 23.2-2 — WGR wavelength increment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`optical path and Fermat's principle <fop-formula-fermat>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Adjacent WGR outputs require an optical path increment equal to the channel
spacing: :math:`n\Delta d_b=\Delta\lambda`.  Hence
:math:`\boxed{\Delta d_b=0.2\ \mathrm{nm}/2.3=0.08696\ \mathrm{nm}}` in the
star-coupler material.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-2-2-result

   \boxed{\Delta d_b=0.2\ \mathrm{nm}/2.3=0.08696\ \mathrm{nm}}


**Check.**  Equation :eq:`fop-problem-23-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 23.2-3 — Two-by-two wavelength transpose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

An :math:`l\to m` path transmits wavelength :math:`\lambda` when
:math:`n\Delta d_{lm}=q_{lm}\lambda` for an integer order, while the rejected
wavelength is not an integer divisor.  Choose
:math:`\Delta d_{11}` resonant for :math:`\lambda_1`,
:math:`\Delta d_{12}` for :math:`\lambda_2`,
:math:`\Delta d_{21}` for :math:`\lambda_3`, and
:math:`\Delta d_{22}` for :math:`\lambda_4`; explicitly
:math:`\boxed{n\Delta d_{11}=q_1\lambda_1,
n\Delta d_{12}=q_2\lambda_2,n\Delta d_{21}=q_3\lambda_3,
n\Delta d_{22}=q_4\lambda_4}`.  Selecting integers that make every unwanted
ratio nonintegral completes the router.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-2-3-result

   \boxed{n\Delta d_{11}=q_1\lambda_1,
   n\Delta d_{12}=q_2\lambda_2,n\Delta d_{21}=q_3\lambda_3,
   n\Delta d_{22}=q_4\lambda_4}


**Check.**  Equation :eq:`fop-problem-23-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 23.3-1 — Cascaded-switch loss and crosstalk
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The worst route through the five-element 4-by-4 network traverses three
2-by-2 switches, so loss is :math:`\boxed{3(0.5)=1.5\ \mathrm{dB}}`.  Adding
three independent :math:`10^{-3}` leakage powers gives crosstalk
:math:`10\log_{10}(3\times10^{-3})=\boxed{-25.2\ \mathrm{dB}}`; a deliberately
conservative coherent phase alignment would instead bound it at -20.5 dB.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-3-1-result

   10\log_{10}(3\times10^{-3})=\boxed{-25.2\ \mathrm{dB}}


**Check.**  Equation :eq:`fop-problem-23-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 23.3-2 — MZI voltage-error crosstalk
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The cross state needs :math:`\boxed{V=V_\pi}`.  A 1% error leaves fractional
leakage ratio :math:`\tan^2(0.01\pi/2)=2.468\times10^{-4}`, hence
:math:`\boxed{XT=-36.08\ \mathrm{dB}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-3-2-result

   \boxed{XT=-36.08\ \mathrm{dB}}


**Check.**  Equation :eq:`fop-problem-23-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 23.3-3 — TSI with programmable delays
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Demultiplex the incoming frame into :math:`N` spatial lanes.  Program lane
:math:`i` with delay :math:`d_i=(\pi(i)-i)\bmod N` slots for the requested
permutation :math:`\pi`; a second bank adds a common frame delay so all values
are causal.  Remultiplex lanes in their fixed order.  This
:math:`\boxed{\text{DEMUX}\to\text{programmable delays}\to\text{MUX}}`
construction absorbs the original fixed-delay/space-switch/fixed-delay stages
into the addressable delay settings.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-23-3-3-result

   \boxed{\text{DEMUX}\to\text{programmable delays}\to\text{MUX}}


**Check.**  Equation :eq:`fop-problem-23-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 23.4-2 — Threshold optical logic
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Sum equal optical inputs and choose a threshold between levels: between one
and two units gives AND, while between zero and one gives OR.  Complement the
threshold device's output (or exchange bright/dark ports) for NAND and NOR.
One scalar threshold cannot implement XOR because its truth set is not
linearly separable; use an OR followed by suppression of the two-input level,
or two threshold stages.  The same sum with threshold :math:`0.5` implements
OR for any :math:`N`.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

Problem 23.4-3 — Kerr-feedback interferometer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The Kerr arm phase is :math:`\Delta\phi=\pi I_o/I_\pi+\phi`, so MZI
interference gives
:math:`\boxed{I_o/I_i=[1+\cos(\pi I_o/I_\pi+\phi)]/2}`.  For :math:`\phi=0`,
write :math:`x=I_o/I_\pi` and
:math:`y=I_i/I_\pi=2x/[1+\cos(\pi x)]`.  Then

.. math::
   :label: fop-problem-23-4-3-eq-1

   {dI_o\over dI_i}=
   \left\{{2\over1+\cos\pi x}+{2\pi x\sin\pi x\over(1+\cos\pi x)^2}\right\}^{-1}.

The ideal differential gain diverges at fold points where the denominator
vanishes; physical loss and finite response time cap that formal maximum.

**Check.**  Equation :eq:`fop-problem-23-4-3-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.
