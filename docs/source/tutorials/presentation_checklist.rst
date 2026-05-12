Presentation Checklist
======================

Purpose
-------

Use this checklist immediately before presenting the UI. It converts the
:doc:`boss_demo_walkthrough` into concrete menu clicks, expected outputs, and
quick validators.

Preflight
---------

Run this command from the repository root:

.. code-block:: bash

   python -m KrakenOS.UI.validate_demo_readiness --full

If time is short, drop ``--full`` for the compact suite, or run only the
validator listed in the case study you will show live and use the stored
screenshots for the rest.

Demo Script
-----------

1. Open the UI.

   .. code-block:: bash

      python -m KrakenOS.UI.layout_editor

2. Sequential lens and optimization.

   Menu path: ``Layouts -> Machine Vision / Finite Imaging -> Machine Vision 150mm Measured``.

   Expected result: a finite multi-element lens appears in the table and the 2D
   plot traces through all elements. Use ``Spot`` or ``MTF`` first, then show
   the optimization controls from :doc:`machine_vision_focus`.

3. Sequential prescription optimization.

   Menu path: ``Layouts -> Starter Lenses -> Cooke Triplet Optimization Case Study``.

   Expected result: a poor three-element Cooke triplet appears with six radii
   and three air gaps already marked as variables. Use ``Spot``/``MTF`` on the
   bad start, then follow :doc:`cooke_triplet_optimization` to apply the final
   prescription and verify the improvement.

4. Sequential analysis breadth.

   Menu path: ``Layouts -> Analysis / Diagnostics -> Double Gauss PSF MTF Wavefront Zernike Case Study``.

   Expected result: the same infinity-object Double Gauss prescription can render
   ``Spot``, ``PSF``, ``MTF``, ``Wavefront``, and ``Zernike`` panels. Use
   :doc:`double_gauss_analysis_suite` to show the exact click order and
   export-ready wavefront/Zernike data.

5. Gaussian laser source.

   Menu path: ``Layouts -> Lasers / Gaussian -> Gaussian Beam Expander``.

   Expected result: the source controls expose beam radius/divergence/waist
   parameters and the plot can show the Gaussian envelope. Show the q-parameter
   report from :doc:`gaussian_beam_expander`.

6. Beam splitter and coherent detector.

   Menu path: ``Layouts -> Beam Splitters / Folds -> Michelson Interferometer (Interferogram)``.

   Expected result: the plot shows branch labels and the analysis toolbar can
   show detector map, coherent detector, and interferogram outputs. Use
   :doc:`michelson_interferometer` as the click-by-click reference.

7. Source/object split.

   Menu path: ``Layouts -> Beam Splitters / Folds -> Right-Angle Beam-Splitter Illumination``.

   Expected result: the physical source is separate from the object/reference
   row, and the useful return path reaches the camera/Image side. Use
   :doc:`right_angle_beam_splitter_illumination`.

8. Imported optical solid.

   Menu path: ``Examples -> Non-Sequential / Advanced Surfaces -> Examp_Phase6_Optical_STL_Prism``.

   Expected result: a ``Solid_3d_stl`` row traces as an optical body, not just a
   decoration. Use ``Actions -> Assign CAD/STL Optical Faces`` and
   ``Actions -> Inspect Optical CAD/STL Solids`` as shown in
   :doc:`optical_stl_prism_faces`.

9. Vendor CAD placement.

   Menu path: ``File -> Import Optical CAD/STL Solid...`` and choose
   ``attachment/prisms/42779/step_42779.step``.

   Expected result: the STEP source is converted to a cached STL, the mesh
   diagnostics pass, and the face-role dialog shows the prism faces. Use
   :doc:`vendor_prism_cad_placement`.

10. Imported camera/lens/LED CAD overlays.

   Menu paths: ``File -> Import LED STEP...``, ``File -> Import Lens STEP...``,
   or ``File -> Import Camera STEP...``.

   Expected result: the 3D viewer shows the imported hardware overlay and a
   long dotted optical-axis guide. Clicking a STEP object opens the ``STEP
   rotation handler`` with persistent ``X/Y/Z +/-90`` buttons for successive
   orientation changes. The old duplicate ``STEP Rotate`` toolbar menu is no
   longer shown. In the 3D toolbar, ``Center STEP Axis`` supports two clicks
   and displays an active-mode badge while armed. Plain left-click selects,
   and left hold-drag rotates the camera around the fixed current view center
   with constant sensitivity:

   * click a planar/circular outer feature on any imported STEP body to move
     that feature center onto the optical axis;
   * select a STEP component first, then click a KrakenOS optical surface to
     center the selected STEP axis on that surface center.
   * click an imported CAD/STL solid row to open the ``CAD/STL placement
     handler``; the old second-row placement toolbar should not be visible.

11. Fabrication output.

   Menu path: ``File -> Lens Drawing Surface Properties...`` followed by
   ``File -> Export Lens Drawing...``.

   Expected result: per-surface drawing metadata is stored in row
   ``DrawingProperties`` and the exporter writes a multi-page PDF. Use
   :doc:`lens_drawing_pdf_export`.

Recovery Checks
---------------

If a live UI action fails during presentation:

* Use the matching Sphinx case-study page and screenshots as the fallback.
* Re-run the specific validator listed in the case study.
* Check the right-side ``Debug`` panel before changing unrelated table rows.
* For CAD overlays, click ``Refresh`` in the 3D viewer after import/axis edits.
