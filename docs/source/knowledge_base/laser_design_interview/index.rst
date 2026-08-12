Laser Design Engineer Interview Guide
=====================================

This collection distills the interview-relevant theory and engineering practice
from three local references:

* Jeff Hecht, *Understanding Lasers: An Entry-Level Guide*, fourth edition
  (2019);
* Norman Hodgson and Horst Weber, *Laser Resonators and Beam Propagation*,
  second edition (2005); and
* Walter Koechner, *Solid-State Laser Engineering*, sixth revised edition
  (2006).

The text is an independent technical synthesis.  It paraphrases concepts rather
than reproducing the books.  Use the :doc:`source_map` to return to the relevant
chapters when a topic needs deeper study.

.. figure:: ../../_static/knowledge_base/laser_design_interview/design_loop.svg
   :alt: Laser design reasoning from requirements through modelling and measurement
   :width: 100%

   **Figure 1.** A strong design answer closes the loop between requirements,
   coupled models, and measured evidence.

What an interviewer is testing
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 19 29 28 24

   * - Dimension
     - Strong evidence
     - Weak answer pattern
     - Best page here
   * - Physics
     - Derives threshold, mode size, or pulse relations and states assumptions
     - Recites a laser definition without closing the energy or loss balance
     - :doc:`theory_essentials`
   * - Optical design
     - Uses ABCD matrices, checks stability over thermal-lens range, and reserves apertures
     - Designs only at one nominal focal power
     - :doc:`resonators_and_beams`
   * - System engineering
     - Connects gain medium, pump, cooling, coatings, extraction, safety, and controls
     - Optimizes one component in isolation
     - :doc:`solid_state_design`
   * - Laboratory judgment
     - Aligns at low power, measures with calibrated tools, and changes one variable at a time
     - Chases maximum power without a baseline or damage controls
     - :doc:`hands_on`
   * - Communication
     - Starts from requirements, names assumptions, estimates, verifies, then discusses risk
     - Gives a number without units, tolerance, or validation plan
     - :doc:`design_case` and :doc:`interview_drill`

Recommended preparation order
-----------------------------

1. Memorize the governing equations and verbal explanations in
   :doc:`theory_essentials`.
2. Work the cavity and Gaussian-beam calculations in
   :doc:`resonators_and_beams` without notes.
3. Practice turning requirements into a solid-state architecture with
   :doc:`solid_state_design` and :doc:`design_case`.
4. Rehearse the alignment, measurement, and fault-isolation sequences in
   :doc:`hands_on`.
5. Answer :doc:`interview_drill` aloud.  Keep the first answer under 90 seconds,
   then expand only when asked.

.. toctree::
   :maxdepth: 1

   theory_essentials
   resonators_and_beams
   solid_state_design
   hands_on
   design_case
   interview_drill
   source_map
