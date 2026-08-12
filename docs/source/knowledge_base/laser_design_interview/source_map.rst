Source Map and Further Reading
==============================

This guide is a concise synthesis, not a substitute for the seven references.
The map below identifies the most useful chapters for checking a derivation,
recovering a book's full assumptions, or preparing a deeper follow-up answer.
Chapter numbers refer to the editions listed on the :doc:`index` page.

.. list-table:: Interview topic to source chapter map
   :header-rows: 1
   :widths: 20 25 28 27

   * - Interview topic
     - *Understanding Lasers*
     - *Laser Resonators and Beam Propagation*
     - *Solid-State Laser Engineering*
   * - Laser action, levels, gain, and threshold
     - Chapters 2--4
     - Chapters 9--10
     - Chapters 1 and 3
   * - Gaussian beams, ABCD matrices, and beam quality
     - Chapters 3--5
     - Chapters 1--2 and 24
     - Chapter 5
   * - Resonator stability, modes, and alignment sensitivity
     - Chapters 3--5
     - Chapters 4--5, 15, and 22
     - Chapter 5
   * - Gain materials and spectroscopy
     - Chapters 6 and 8
     - Chapter 9
     - Chapters 1--2
   * - Pump sources, absorption, and pump geometry
     - Chapters 6 and 8
     - Chapter 9
     - Chapter 6
   * - Output coupling, extraction, and efficiency
     - Chapters 3--4
     - Chapter 10
     - Chapters 3 and 5
   * - Thermal lensing and thermo-mechanical effects
     - Chapters 5 and 8
     - Chapters 13, 15, and 23
     - Chapter 7
   * - Amplifiers, ASE, parasitic oscillation, and self-focusing
     - Chapter 6
     - Chapters 9--10 and 16
     - Chapter 4
   * - Q-switching and mode locking
     - Chapters 4, 6, and 8
     - Chapter 12
     - Chapters 8--9
   * - Nonlinear conversion
     - Chapters 5--6
     - Chapter 16
     - Chapter 10
   * - Optical damage and contamination control
     - Chapter 5 and Appendix A
     - Chapters 4 and 23--24
     - Chapter 11 and Appendix A
   * - Measurement and fault isolation
     - Chapter 5
     - Chapters 23--24
     - Chapters 5 and 7
   * - Laser safety
     - Appendix A
     - Use together with the laboratory chapters
     - Appendix A

How to use the books efficiently
--------------------------------

* Read Hecht first when you need an intuitive explanation that can be delivered
  cleanly at the start of an interview answer.
* Use Hodgson and Weber for resonator calculations, propagation, alignment
  sensitivity, and beam-characterization details.
* Use Koechner to close the solid-state engineering loop: material data, pump
  architecture, heat removal, extraction, pulsed operation, and damage.
* Use Scheps as the short, build-oriented path from diode and gain-element
  selection to an end-pumped oscillator and its pump optics.
* Use Taylor to refresh the explanatory chain from light and amplification to
  stimulated emission, cavities, source descriptions, and safe use.
* Use Ross when a beam metric, analyzer result, or acceptance requirement must
  be defined precisely; use Ristau when exposure margin, coating qualification,
  or damage evidence must withstand design review.

For any real design, confirm material parameters against a current supplier
datasheet and applicable laser-safety requirements.  Values such as lifetime,
cross section, absorption, thermal conductivity, coating limit, and diode
wavelength tolerance depend on material composition, temperature, pulse
duration, spot size, and test method.

Focused-reference chapter map
-----------------------------

.. list-table:: Additional source map
   :header-rows: 1
   :widths: 29 22 49

   * - Reference
     - Highest-value chapters
     - Interview contribution
   * - Scheps, *Introduction to Laser Diode-Pumped Solid State Lasers*
     - Chapters 2--6 and 10
     - Pump-diode spatial/spectral properties, end-pumped TEM00 design, pump optics, cw operation, efficiency, scaling, thermal effects, and intracavity elements; synthesized in :doc:`diode_pumped_lasers`
   * - Taylor, *Introduction to Laser Science and Engineering*
     - Chapters 2--7
     - Amplification, stimulated emission, laser components/rate equations/cavities, laser types, power and beam descriptions, efficiency, measurement, and practical safety; cross-checks :doc:`theory_essentials`, :doc:`hands_on`, and :doc:`beam_quality`
   * - Ross, *Laser Beam Quality Metrics*
     - Chapters 1--4 and 6; Appendix
     - Metric definitions, second-moment :math:`M^2` measurement, application-derived specifications, metric conversion limits, truncation, noise, and reporting traps; synthesized in :doc:`beam_quality`
   * - Ristau, ed., *Laser-Induced Damage in Optical Materials*
     - Chapters 1--8 and 11--16
     - Thermal, defect, nonlinear, and ultrashort-pulse damage; detection, protocols, statistics, transfer/scatter measurement, laser materials, surfaces, coatings, and contamination; synthesized in :doc:`laser_damage`

Scope of this synthesis
-----------------------

The guide emphasizes explanations, first-order calculations, design tradeoffs,
laboratory sequences, and diagnostic reasoning that can be demonstrated in an
interview.  Historical surveys and application catalogues were intentionally
compressed.  Exact book figures, tables, and extended prose were not copied.
