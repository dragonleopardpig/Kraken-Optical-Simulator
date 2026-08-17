Optical Alignment Methods
=========================

This collection develops worked alignment procedures from two supplied
references:

* David M. Benton, *Alignment of Optical Systems Using Lasers: A Guide for the
  Uninitiated* (SPIE Spotlight SL61, 2021); and
* Rainer Heintzmann, "Practical Guide to Optical Alignment," Appendix B in
  *Fluorescence Microscopy: From Principles to Biological Applications*, second
  edition (2017).

The figures are original diagrams.  The text paraphrases the references and
adds error equations, numerical examples, convergence logic, and acceptance
checks so that each method can be performed and diagnosed at the bench.

.. warning::

   Alignment is not an exemption from laser-safety controls.  Enclose the beam
   where practical, remove specular hazards, use the lowest usable power, set
   beam blocks before steering, and follow the laboratory's approved wavelength-
   and power-specific procedure.  A card, ceiling, or distant wall is not an
   acceptable target for a hazardous open beam.

Method map
----------

.. list-table::
   :header-rows: 1
   :widths: 31 33 36

   * - Page
     - Methods
     - Primary residuals
   * - :doc:`axis_and_mirror_steering`
     - Two irises; dog-leg beam walk
     - Position error and angular error
   * - :doc:`collimation_lenses_and_focus`
     - Beam expander; shear plate; aperture pair; lens centering;
       autocollimation; focal plane and objective BFP
     - Beam curvature, decenter, tilt, defocus, aberration
   * - :doc:`fiber_and_interferometers`
     - Fiber injection; Michelson; Mach--Zehnder
     - Coupled power, near/far overlap, fringe spacing, path mismatch
   * - :doc:`nir_and_retroreflection`
     - Visible proxy for NIR; plane mirror; corner cube; return coupling
     - Chromatic focus shift, return displacement, angular closure

Reference coverage
------------------

* Axis definition and dog-leg walking expand Benton Secs. 4 and 4.1 and
  Heintzmann Sec. B.2.
* Expansion, collimation, lenses, and focus expand Benton Secs. 3.2--3.5, 7,
  and 8 and Heintzmann Secs. B.1 and B.3--B.7.
* Fiber and interferometer procedures expand Benton Secs. 5, 6.1, and 6.2.
* NIR and retroreflection procedures expand Benton Secs. 9, 10, and 10.1.

.. toctree::
   :maxdepth: 1

   axis_and_mirror_steering
   collimation_lenses_and_focus
   fiber_and_interferometers
   nir_and_retroreflection
