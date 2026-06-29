Case Study 4b: AZURE ELS-85 mm On A 45-Degree Fold
==================================================

This page documents the folded variant of the AZURE ELS-85 surrogate,
``Machine Vision 85 mm Azure Folded (Datasheet 0.5X-2.0X)``.  It is the straight
:doc:`machine_vision_azure_85_surrogate` layout with one 45-degree fold mirror added
ahead of the lens, so the imaging lens and the sensor sit on the **reflected** branch
of the mirror.

Why A Sequential Mirror, Not A Promoted Prism
--------------------------------------------

If you import a right-angle prism/mirror and promote it to a non-sequential optical
solid, it folds the traced **rays** in 3D -- but the sequential table rows stay on the
original straight axis.  The lens rows do not move onto the reflected path, so the lens
stops receiving the beam.  To fold the lens itself you fold the optical **axis**, and in
a sequential layout that is done with a ``Mirror`` surface (``glass = "MIRROR"``):

* KrakenOS re-orients **every row after the mirror** onto the reflected path
  automatically (the editor forces ``AxisMove = 2.0`` on any ``Mirror`` row).
* This is the canonical pattern used by the ``Double Mirror Fold`` and
  ``Flat Mirror 45 Deg`` examples, where the lens follows immediately after the mirror.

Here ``tilt_x = -45`` folds the ``+Z`` object axis up into ``+Y`` (the same direction the
user's imported Edmund 87391 right-angle mirror reflects), so the front/rear optical
vertex datums, the two ideal blackbox groups, the F/4.5 stop, and the image plane all
land on the ``+Y`` branch.

The Conjugate Is Preserved
-------------------------

At 1x the object-to-front-vertex working distance is 141.85 mm.  The fold splits that
distance across the bend:

.. code-block:: text

   object -> mirror        = 100.00 mm
   mirror -> front vertex  =  41.85 mm
   -----------------------------------
   total                   = 141.85 mm   (unchanged 1X conjugate)

so only the path is bent 90 degrees; the lens prescription, EFL (85 mm), F-number
(F/4.5), and the 0.5x-2.0x behaviour are exactly those of the straight surrogate.

What Is Different From The Straight Layout
-----------------------------------------

* A ``Right Angle Fold Mirror`` row (``glass = "MIRROR"``, ``tilt_x = -45``, Ø50 mm) sits
  between the object and the lens.
* The object thickness is the object-to-mirror distance (100 mm) instead of the full
  141.85 mm.
* The vendor barrel STEP overlay and the camera STEP overlay are **omitted**.  The CAD
  overlay aligner seats a STEP mesh along the straight cumulative-thickness ``+Z`` axis
  (``layout_polyline_display`` ends its alignment with ``aligned[:, 2] += target_front_z``);
  it does not follow a folded polyline, so on the reflected branch the barrel/camera
  bodies would render detached on the straight axis.  The sequential rows -- the datums,
  the blackbox groups, the stop, and the fold mirror -- already show the folded imaging
  path.  To inspect the barrel STEP, open the straight
  ``Machine Vision 85 mm Azure (Datasheet 0.5X-2.0X)`` layout.
* The camera **model** (Allied Vision ``hr25MCX``) is kept, so the image format stays
  camera- and FOV-driven at runtime.

Everything else (ray display, source, detector, tolerance, atmosphere, optimization
defaults) is inherited from the straight surrogate.

Rendered Layout
---------------

Load ``Machine Vision 85 mm Azure Folded (Datasheet 0.5X-2.0X)`` from the Machine Vision
menu and open it in Open 3D.  The object axis runs along ``+Z`` to the fold mirror; from
there the whole ELS-85 surrogate and the sensor run along ``+Y``.  An on-axis ray
launched from the object reaches the sensor on the reflected branch.

Validation
----------

The standalone validation script checks discovery in the Machine Vision menu, the eight
rows, the fold mirror, the preserved 1X conjugate split, the paraxial EFL (85 mm) of the
post-mirror chain, and -- with a real build=0 sequential trace -- that the axis folds so
the on-axis ray lands on the reflected branch:

.. code-block:: bash

   python -m KrakenOS.UI.validate_machine_vision_azure_85_folded
