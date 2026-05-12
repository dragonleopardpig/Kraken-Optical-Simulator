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
* Gaussian source and q propagation: :doc:`gaussian_beam_expander`;
* PSF/MTF-style detector and field diagnostics: :doc:`machine_vision_focus`,
  :doc:`michelson_interferometer`, and :doc:`mach_zehnder_interferometer`;
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
   * - 1
     - ``Tutorial_4b_PSF_&_MTF_Calculation.ipynb`` and
       ``Tutorial_4c_Zernike_Decomposition.ipynb``
     - One lens, one page: spot, PSF, MTF, wavefront, Zernike, and export
     - Demonstrates analysis breadth from one stable prescription.
   * - 2
     - ``Tutorial_6a`` through ``Tutorial_6f`` coating/polarization notebooks
     - Coating table, Jones polarization, AR stack, and beam-splitter coating
       examples
     - Strengthens the current coating/polarization UI and prevents physics
       regressions.
   * - 3
     - ``Tutorial_9a_Edmund_Optics_Catalogue.ipynb`` and
       ``Tutorial_9b_Thorlabs_Catalogue.ipynb``
     - Off-the-shelf catalogue import, table expansion, and detector analysis
     - Matches the UI goal of importing real vendor optics from the dropdown
       or Import menu.
   * - 4
     - ``Tutorial_2d_Raytracing_Aspheres.ipynb`` and
       ``Tutorial_7c_Freeform_Surfaces.ipynb``
     - Asphere/freeform surface editing with sag and wavefront checks
     - Exposes advanced surface gems in KrakenOS core.
   * - 5
     - ``Tutorial_7d_Three_Mirror_Anastigmat.ipynb``
     - Off-axis reflective TMA with 2D/3D alignment and wavefront diagnostics
     - Builds on the non-sequential and 3D alignment work already present.
   * - 6
     - ``Tutorial_11a_Extended_Source_Modeling.ipynb``
     - Extended LED/fiber/source examples with source-illumination maps
     - Complements the existing multi-source and Zemax LED diffuse case
       studies.
   * - 7
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

The Cooke-triplet optimization port has landed as
:doc:`cooke_triplet_optimization`. The next high-value port should be the
one-lens analysis breadth page inspired by Optiland
``Tutorial_4b_PSF_&_MTF_Calculation.ipynb`` and
``Tutorial_4c_Zernike_Decomposition.ipynb``: one stable prescription with
Spot, PSF, MTF, wavefront, Zernike, and export checks from the same UI state.
