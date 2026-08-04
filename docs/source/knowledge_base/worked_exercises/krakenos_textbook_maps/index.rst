.. _krakenos-textbook-maps:

KrakenOS Textbook Cross-References
==================================

These pages connect five optical-engineering references to the equations,
algorithms, and data structures in KrakenOS.  They complement the
:doc:`../fundamentals_of_photonics/krakenos_formula_map`: that page starts from
general photonics, whereas this collection emphasizes practical lens design,
image evaluation, tolerancing, ghost paths, stray light, and MTF measurement.

The maps are reading guides, not claims that KrakenOS implements each book.
They deliberately distinguish a numerical implementation from a nearby
visualization or workflow.

.. list-table:: Match levels used in every map
   :header-rows: 1
   :widths: 16 84

   * - Level
     - Meaning
   * - **Direct**
     - KrakenOS evaluates the stated equation, or an algebraically equivalent
       vector, matrix, sampled, or Monte Carlo form.
   * - **Partial**
     - The named physics is implemented with narrower assumptions or only some
       outputs from the textbook treatment are available.
   * - **Related**
     - KrakenOS can illustrate the topic, but is not a solver for the complete
       mathematical model or measurement procedure.
   * - **Not modelled**
     - No corresponding implementation was found in the reviewed source.

.. important:: Comparison conventions

   Geometry and optical path are normally in millimetres; public trace and
   Gaussian-beam wavelengths are normally in micrometres.  Catalog dispersion
   also expects micrometres.  KrakenOS stores its legacy paraxial ray as
   :math:`(u,y)^T`, while most books use :math:`(y,u)^T`; use
   ``ParaxialMatrixTrace.system_matrix_abcd`` for the conventional order.
   Surface-radius, normal, conic, polarization-phase, and Fourier-transform
   conventions must be checked before comparing signs.  Relative branch power
   is not automatically a calibrated watt, radiance, irradiance, or detector
   signal.

Choose a reference
------------------

.. toctree::
   :maxdepth: 1

   optical_system_design
   modern_optical_engineering
   introduction_to_lens_design
   stray_light_analysis_and_control
   modulation_transfer_function

Best route through the five books
---------------------------------

1. Read Sasián for a compact path from lens geometry through exact tracing,
   evaluation, optimization, tolerancing, and ghosts.
2. Use Smith for deeper paraxial design, aberration interpretation, practical
   engineering, and the prescriptions already shipped with KrakenOS.
3. Use Fischer, Tadic-Galeb, and Yoder for system specification, Gaussian
   beams, sensors, polarization, tolerancing, optomechanics, and stray-light
   context.
4. Use Fest when building non-sequential scatter and ghost studies.  Its
   radiometric bookkeeping also makes clear what KrakenOS does not yet
   calculate absolutely.
5. Use Boreman when converting a simulated or captured image into an MTF and
   when separating optical, detector-footprint, sampling, motion, and
   atmospheric contributions.

Source boundary
---------------

Section, equation, and printed-page references follow the attached editions.
Equations are restated only as needed to explain code correspondence; problem
statements, figures, and tables are not reproduced.  The maps were prepared
from the source tree and these local PDFs:

* Robert E. Fischer, Biljana Tadic-Galeb, and Paul R. Yoder,
  *Optical System Design*, second edition.
* Warren J. Smith, *Modern Optical Engineering*, fourth edition.
* José Sasián, *Introduction to Lens Design* (2019).
* Eric C. Fest, *Stray Light Analysis and Control* (2013).
* Glenn D. Boreman, *Modulation Transfer Function in Optical and
  Electro-Optical Systems*, second edition (2021).
