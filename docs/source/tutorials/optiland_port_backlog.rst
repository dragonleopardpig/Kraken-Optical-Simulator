Optiland-Inspired Case Study Port Backlog
=========================================

Purpose
-------

The local ``~/Projects/optiland/docs`` tree has a large Sphinx/Jupyter
learning guide. KrakenOS UI should not copy those notebooks line-by-line.
Instead, each useful Optiland tutorial should be translated into a
clickable KrakenOS UI case study with:

* a menu-loadable layout or example;
* step-by-step UI instructions;
* generated screenshots;
* at least one validator that checks the optical result, not only that files
  exist.

Already Covered In Current KrakenOS UI Docs
-------------------------------------------

The current KrakenOS UI tutorials already cover several Optiland-style
learning objectives:

* beginner layout/table editing: :doc:`pcx_from_plate`;
* finite lens analysis and optimization: :doc:`machine_vision_focus`;
* poor-to-optimized Cooke triplet prescription design:
  :doc:`cooke_triplet_optimization`;
* one-lens Spot/PSF/MTF/Wavefront/Zernike analysis breadth:
  :doc:`double_gauss_analysis_suite`;
* Gaussian source and q propagation: :doc:`gaussian_beam_expander`;
* additional PSF/MTF-style detector and field diagnostics:
  :doc:`machine_vision_focus`, :doc:`michelson_interferometer`, and
  :doc:`mach_zehnder_interferometer`;
* beam splitters and coherent recombination: :doc:`michelson_interferometer`
  and :doc:`mach_zehnder_interferometer`;
* tolerance sensitivity and Monte Carlo: :doc:`tolerance_monte_carlo`;
* catalogue/CAD-oriented workflows: :doc:`right_angle_beam_splitter_illumination`,
  :doc:`vendor_prism_cad_placement`, and :doc:`lens_drawing_pdf_export`.

High-Value Ports
----------------

These Optiland notebooks are good candidates for future KrakenOS UI case
studies because they show a workflow a user can follow and verify:

.. list-table::
   :header-rows: 1

   * - Priority
     - Optiland source
     - KrakenOS UI port target
     - Why it matters
   * - Landed
     - ``Tutorial_5c_Optimization_Case_Study.ipynb``
     - :doc:`cooke_triplet_optimization`
     - Shows a complete design loop beyond the current machine-vision focus
       solve: six radii, three air gaps, Spot/MTF before/after screenshots,
       and a primary-wavelength spot-improvement validator.
   * - Landed
     - ``Tutorial_4b_PSF_&_MTF_Calculation.ipynb`` and
       ``Tutorial_4c_Zernike_Decomposition.ipynb``
     - :doc:`double_gauss_analysis_suite`
     - Demonstrates analysis breadth from one stable prescription: Spot, PSF,
       MTF, Wavefront Function, Zernike fit, and export-ready data.
   * - 1
     - ``Tutorial_6a`` through ``Tutorial_6f`` coating/polarization notebooks
     - Coating table, Jones polarization, AR stack, and beam-splitter coating
       examples
     - Strengthens the current coating/polarization UI and prevents physics
       regressions.
   * - 2
     - ``Tutorial_9a_Edmund_Optics_Catalogue.ipynb`` and
       ``Tutorial_9b_Thorlabs_Catalogue.ipynb``
     - Off-the-shelf catalogue import, table expansion, and detector analysis
     - Matches the UI goal of importing real vendor optics from the dropdown
       or Import menu.
   * - 3
     - ``Tutorial_2d_Raytracing_Aspheres.ipynb`` and
       ``Tutorial_7c_Freeform_Surfaces.ipynb``
     - Asphere/freeform surface editing with sag and wavefront checks
     - Exposes advanced surface gems in KrakenOS core.
   * - 4
     - ``Tutorial_7d_Three_Mirror_Anastigmat.ipynb``
     - Off-axis reflective TMA with 2D/3D alignment and wavefront diagnostics
     - Builds on the non-sequential and 3D alignment work already present.
   * - 5
     - ``Tutorial_11a_Extended_Source_Modeling.ipynb``
     - Extended LED/fiber/source examples with source-illumination maps
     - Complements the existing multi-source and Zemax LED diffuse case
       studies.
   * - 6
     - ``Tutorial_7f_Multi_Configuration_Zoom_Lenses.ipynb``
     - Multi-configuration zoom or focus workflow
     - Useful, but should wait until KrakenOS UI has a stronger
       multi-configuration table model.

Deferred Or Research-Oriented Ports
-----------------------------------

The Optiland machine-learning notebooks are valuable references, but they
should not become boss-demo UI case studies until the KrakenOS UI has a stable
ML/differentiable backend story:

* ``Singlet_RF_Model_RMS_Spot_Size.ipynb``;
* ``Double_Gauss_Surrogate_Model.ipynb``;
* ``Ray_Path_Failure_Classification_Model.ipynb``;
* ``Misalignment_Prediction_Cooke_Triplet.ipynb``;
* ``RL_aspheric_singlet.ipynb``;
* ``SR_GAN_for_wavefront_data.ipynb``.

Recommended Next Port
---------------------

The Cooke-triplet optimization port and the one-lens analysis breadth port
have landed as :doc:`cooke_triplet_optimization` and
:doc:`double_gauss_analysis_suite`. The next high-value Optiland-inspired port
should be the coating/polarization group, especially the AR-stack and
beam-splitter coating examples, because that area is physics-sensitive and
already has UI controls that benefit from regression screenshots.
