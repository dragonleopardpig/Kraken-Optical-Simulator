Boss Demo Walkthrough
=====================

Goal
----

Use this page as a short presentation path through the UI. It is ordered so a
reviewer can start from a conventional sequential lens, then see optimization,
tolerancing, non-sequential source/beam-splitter work, imported CAD, and final
fabrication drawing export.

Recommended Demo Order
----------------------

1. :doc:`machine_vision_focus`

   Start with a finite machine-vision lens. Show that the table is an optical
   prescription, not just a drawing. Run a basic analysis, then show how a
   merit operand and optimization improve the design.

2. :doc:`gaussian_beam_expander`

   Switch from image-forming optics to laser source work. Show source radius,
   divergence, waist calculation, q-parameter reporting, and the Gaussian beam
   overlay.

3. :doc:`michelson_interferometer`

   Demonstrate active beam-splitter branch tracing, coherent path handling, and
   interferogram analysis.

4. :doc:`mach_zehnder_interferometer`

   Show separated arms, recombination, and path-aware analysis on a second
   interferometer geometry.

5. :doc:`right_angle_beam_splitter_illumination`

   Show the source/object split workflow. This is useful when explaining why
   illumination sources and object fields are separate concepts.

6. :doc:`multi_source_illumination`

   Show multi-source non-sequential tracing and detector/source illumination
   maps.

7. :doc:`tolerance_monte_carlo`

   Move from nominal design to manufacturing robustness: tolerance variables,
   compensators, coupling groups, worst-sample comparison, and stack-up plots.

8. :doc:`optical_stl_prism_faces`

   Demonstrate arbitrary closed STL solids, face-role metadata, and hit
   sequence diagnostics.

9. :doc:`cube_virtual_plane_workflow`

   Explain the CAD/body-versus-physics distinction for cube beam splitters.
   Use this to make clear that mechanical CAD alone does not encode split
   ratio, phase, or coating physics.

10. :doc:`vendor_prism_cad_placement`

    Show real vendor STEP/IGES/PDF assets, mesh diagnostics, face assignment,
    and CAD face-fit placement.

11. :doc:`lens_drawing_pdf_export`

    Show engineering output: a multi-element lens prescription, per-surface
    drawing properties, a JSON sidecar, and a multi-page PDF fabrication
    drawing.

12. :doc:`3d_hardware_alignment`

    Show the embedded 3D inspector controls: optical-axis guide, CAD/STL
    placement handler, active-mode badges, and imported STEP rotation handler.

13. :doc:`cooke_triplet_optimization`

    Move from focus recovery to true prescription design. Show a bad
    three-element Cooke triplet, the six radii and three air gaps marked as
    variables, then apply the deterministic optimized prescription and verify
    Spot/MTF improvement.

14. :doc:`double_gauss_analysis_suite`

    Stay with a conventional sequential lens and show analysis breadth from one
    state: Spot, PSF, MTF, Wavefront Function, Zernike coefficients, and CSV
    export readiness.

What To Emphasize
-----------------

The strongest message is not that every workflow is already final. The
important message is that the UI exposes the core KrakenOS model end-to-end:

* editable surface and element prescriptions;
* sequential and non-sequential tracing;
* source/object separation;
* beam-splitter branch paths and coherent detector analysis;
* Gaussian beam/q-parameter workflows;
* tolerance and compensator reporting;
* imported CAD/STL optical solids with diagnostics;
* fabrication metadata and PDF drawing export.

Suggested Live Checks
---------------------

Run these before a presentation:

.. code-block:: bash

   python -m KrakenOS.UI.validate_menu_smoke
   python -m KrakenOS.UI.validate_branch_analysis
   python -m KrakenOS.UI.validate_lens_drawing_pdf_case_study
   python -m KrakenOS.UI.validate_cooke_triplet_case_study
   python -m KrakenOS.UI.validate_double_gauss_analysis_case_study
   python -m KrakenOS.UI.validate_gaussian_beam_expander_case_study
   python -m KrakenOS.UI.validate_michelson_case_study
   python -m KrakenOS.UI.validate_mach_zehnder_case_study
   python -m KrakenOS.UI.validate_vendor_prism_42779
   python -m KrakenOS.UI.validate_3d_hardware_alignment_case_study
   python -m sphinx -b html docs/source docs/build/html

If time is limited, run the specific validator for the case study being shown
and open the prebuilt screenshots in the Sphinx docs.
