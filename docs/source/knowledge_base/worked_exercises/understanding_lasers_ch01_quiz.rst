Understanding Lasers: Chapter 1 Quiz
====================================

Source
------

Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth edition
(Wiley/IEEE Press, 2019), ``Quiz for Chapter 1``, printed pages 18--20.

The questions below are paraphrased rather than reproduced.  The goal is to
explain why each answer follows from the chapter, including the calculation
steps for the efficiency questions.

Quick answers
-------------

.. list-table::
   :header-rows: 1
   :widths: 12 18 70

   * - Question
     - Answer
     - Main idea
   * - 1
     - **c**
     - ``LASER`` began as an acronym.
   * - 2
     - **b**
     - Photon behaviour is not unique to laser light.
   * - 3
     - **a**
     - Semiconductor lasers dominate by unit count.
   * - 4
     - **c**
     - Laser amplification is based on stimulated emission.
   * - 5
     - **d**
     - Chromium ions are the active emitters in ruby.
   * - 6
     - **b** (intended)
     - A semiconductor laser is an electrically driven diode device.
   * - 7
     - **e**, :math:`99\ \mathrm{W}`
     - A 1%-efficient device needs :math:`100\ \mathrm{W}` input.
   * - 8
     - **b**, :math:`3\ \mathrm{W}`
     - A 25%-efficient device needs :math:`4\ \mathrm{W}` input.
   * - 9
     - **b**
     - Waves with a stable phase relationship are coherent.
   * - 10
     - Personal result
     - Count lasers hidden in devices as well as standalone lasers.

1. Where the word ``laser`` came from
-------------------------------------

**Answer: c.**  The name was formed from the initial letters of *Light
Amplification by Stimulated Emission of Radiation*.  It is therefore an
acronym, not a trade name or a translation of a foreign word.

The phrase is also a compact description of the process: stimulated emission
adds photons to the optical field, thereby amplifying light.

2. The incorrect statement about light
----------------------------------------

**Answer: b.**  All light can display wave-like and photon-like behaviour.
Laser light is special because of properties such as high coherence,
directionality, and brightness, not because its energy alone comes in
photons.

The other statements are consistent with the electromagnetic spectrum.
Radio, visible, and ultraviolet radiation are all electromagnetic waves;
their wavelength and frequency ranges differ.

3. The most common lasers
--------------------------

**Answer: a.**  Most lasers counted as individual devices are semiconductor
laser diodes embedded in electronic and communications equipment.  Familiar
examples include optical-disc drives and fibre-optic transmitters.

This question concerns the **number of devices**, not which laser type has the
highest power or occupies the most space.  Large scientific and industrial
lasers are much less numerous.

4. The emission process used by a laser
----------------------------------------

**Answer: c.**  A photon whose energy matches an excited-state transition can
stimulate the excited atom, molecule, or semiconductor carrier to emit
another photon.  This is **stimulated emission**.

Spontaneous emission can help start the process, and mirrors can provide
optical feedback, but neither one is the defining amplification mechanism.

5. The active emitter in ruby
------------------------------

**Answer: d.**  Ruby is sapphire, :math:`\mathrm{Al_2O_3}`, containing a small
concentration of chromium ions.  The sapphire forms the host crystal, while
the chromium ions supply the energy levels responsible for the red laser
transition.

It is useful to keep these two roles separate:

.. math::

   \text{ruby laser material}
   = \underbrace{\mathrm{Al_2O_3}}_{\text{host}}
   + \underbrace{\mathrm{Cr^{3+}}}_{\text{active ion}}.

6. Why the name ``diode laser`` is used
----------------------------------------

**Answer: b is the intended choice.**  A semiconductor laser is based on a
diode junction with two electrical terminals.  An applied current injects
electrons and holes; their recombination can produce stimulated emission.

The wording of choice b in the book says that the device conducts *light*
between terminals.  That is imprecise: electrical current passes between the
terminals, while light is generated in and guided out of the active region.
Nevertheless, b is the only choice describing the diode structure and is also
the choice in the book's answer key.

7. Heat from a 1%-efficient laser
---------------------------------

**Answer: e,** :math:`99\ \mathrm{W}`.

We are given optical output power :math:`P_{\mathrm{out}}=1\ \mathrm{W}` and
efficiency :math:`\eta=1\%=0.01`.  Efficiency is

.. math::
   :label: laser-efficiency-ch1

   \eta = \frac{P_{\mathrm{out}}}{P_{\mathrm{in}}}.

Rearrange Equation :eq:`laser-efficiency-ch1` for input power:

.. math::

   P_{\mathrm{in}} = \frac{P_{\mathrm{out}}}{\eta}
   = \frac{1\ \mathrm{W}}{0.01}
   = 100\ \mathrm{W}.

If the non-optical output is treated as heat, conservation of energy gives

.. math::

   \begin{aligned}
   P_{\mathrm{heat}}
   &= P_{\mathrm{in}}-P_{\mathrm{out}} \\
   &= 100\ \mathrm{W}-1\ \mathrm{W} \\
   &= \boxed{99\ \mathrm{W}}.
   \end{aligned}

Check: one percent of :math:`100\ \mathrm{W}` is the stated
:math:`1\ \mathrm{W}` optical output.

8. Heat from a 25%-efficient laser
----------------------------------

**Answer: b,** :math:`3\ \mathrm{W}`.

Now :math:`P_{\mathrm{out}}=1\ \mathrm{W}` and
:math:`\eta=25\%=0.25`.  Apply the same equation:

.. math::

   P_{\mathrm{in}}
   = \frac{P_{\mathrm{out}}}{\eta}
   = \frac{1\ \mathrm{W}}{0.25}
   = 4\ \mathrm{W}.

Therefore,

.. math::

   P_{\mathrm{heat}}
   = 4\ \mathrm{W}-1\ \mathrm{W}
   = \boxed{3\ \mathrm{W}}.

Check: :math:`1\ \mathrm{W}` of light plus :math:`3\ \mathrm{W}` of heat
accounts for the full :math:`4\ \mathrm{W}` input.

9. The result of a stable phase relationship
------------------------------------------------

**Answer: b, coherent.**  Waves are coherent when their relative phase is
stable.  Stimulated emission produces a new photon matched to the stimulating
field, which supports the coherent field in a laser cavity.

.. important:: Answer-key discrepancy

   The answer key on printed page 543 gives **c** for question 9, which would
   mean ``pulsed``.  That conflicts with the question and with the definition
   of coherence: being in phase does not require a laser to be pulsed.  Choice
   **b** is the physically correct answer, so the printed key appears to
   contain an error.

10. Personal laser inventory
-----------------------------

There is no single correct answer.  Count only devices you actually own and
distinguish lasers from ordinary light-emitting diodes.  Places worth checking
include:

* CD, DVD, and Blu-ray drives or players, which may contain more than one
  wavelength of laser;
* laser printers;
* fibre-optic networking equipment;
* laser distance meters, levels, barcode scanners, and pointers;
* computer mice specifically labelled as laser mice.

For a repeatable answer, make a table with columns for the device, number of
lasers, purpose, and confidence.  Devices whose documentation is unclear can
be marked ``unknown`` rather than guessed.

What this quiz established
---------------------------

The chapter's central chain of ideas is:

.. math::

   \text{excited laser medium}
   \xrightarrow{\text{stimulated emission}}
   \text{optical amplification}
   \xrightarrow{\text{feedback and selection}}
   \text{coherent laser output}.

Practical lasers differ in their active material and efficiency, but the
stimulated-emission principle is common to them.
