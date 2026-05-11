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

3. Gaussian laser source.

   Menu path: ``Layouts -> Lasers / Gaussian -> Gaussian Beam Expander``.

   Expected result: the source controls expose beam radius/divergence/waist
   parameters and the plot can show the Gaussian envelope. Show the q-parameter
   report from :doc:`gaussian_beam_expander`.

4. Beam splitter and coherent detector.

   Menu path: ``Layouts -> Beam Splitters / Folds -> Michelson Interferometer (Interferogram)``.

   Expected result: the plot shows branch labels and the analysis toolbar can
   show detector map, coherent detector, and interferogram outputs. Use
   :doc:`michelson_interferometer` as the click-by-click reference.

5. Source/object split.

   Menu path: ``Layouts -> Beam Splitters / Folds -> Right-Angle Beam-Splitter Illumination``.

   Expected result: the physical source is separate from the object/reference
   row, and the useful return path reaches the camera/Image side. Use
   :doc:`right_angle_beam_splitter_illumination`.

6. Imported optical solid.

   Menu path: ``Examples -> Non-Sequential / Advanced Surfaces -> Examp_Phase6_Optical_STL_Prism``.

   Expected result: a ``Solid_3d_stl`` row traces as an optical body, not just a
   decoration. Use ``Actions -> Assign CAD/STL Optical Faces`` and
   ``Actions -> Inspect Optical CAD/STL Solids`` as shown in
   :doc:`optical_stl_prism_faces`.

7. Vendor CAD placement.

   Menu path: ``File -> Import Optical CAD/STL Solid...`` and choose
   ``attachment/prisms/42779/step_42779.step``.

   Expected result: the STEP source is converted to a cached STL, the mesh
   diagnostics pass, and the face-role dialog shows the prism faces. Use
   :doc:`vendor_prism_cad_placement`.

8. Imported camera/lens/LED CAD overlays.

   Menu paths: ``File -> Import LED STEP...``, ``File -> Import Lens STEP...``,
   or ``File -> Import Camera STEP...``.

   Expected result: the 3D viewer shows the imported hardware overlay. In the
   3D toolbar, ``Axis LED``/``Axis Cam``/``Axis Lens`` supports two clicks.
   Plain left-click selects, and left hold-drag rotates the camera around the
   fixed current view center with constant sensitivity:

   * click a planar/circular feature on the STEP body to define its local
     optical axis;
   * click a KrakenOS optical surface to center the current STEP axis on that
     surface axis.

9. Fabrication output.

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
