Case Study 4b: AZURE ELS-85 mm On A Right-Angle Mirror
======================================================

This page documents the folded variant of the AZURE ELS-85 surrogate,
``Machine Vision Az85 Ra Mirror``.  It is the straight
:doc:`machine_vision_azure_85_surrogate` layout folded by a real **promoted STEP
right-angle mirror solid** (the Edmund 87391 right-angle mirror), so the imaging lens
and the sensor sit on the **reflected** branch of the mirror.

A Promoted STEP Mirror, Not A Sequential Mirror Row
---------------------------------------------------

The mirror here is the vendor right-angle prism imported from STEP and **promoted to a
non-sequential optical solid**.  Its ``S001/F002`` face is assigned ``function =
"Mirror"``, so the traced rays bend on the physical mirror face -- there is only one
path the ray can take according to the geometry of the solid.  The two transmit/port
faces (``S001/F001`` input, ``S001/F003`` output) carry the beam into and out of the
BK7 body.

Because the fold is now done by a real CAD body, the vendor barrel STEP overlay and the
camera STEP overlay are **kept** -- the earlier sequential-``Mirror`` variant had to drop
them because the straight-axis overlay aligner could not fold a mesh.  Here the lens
barrel and the camera body are placed in the scene with the layout, alongside the mirror
solid.

The Conjugate And Prescription
------------------------------

The blackbox prescription is unchanged from the straight surrogate: two ideal KrakenOS
``Thin Lens`` blackbox groups about an F/4.5 stop reproduce **EFL = 85 mm**, and the
front/rear optical vertex datums bracket the ideal lens.  Only the path is bent 90
degrees at the mirror solid; the lens prescription, EFL, F-number, and the 0.5x-2.0x
behaviour are exactly those of the straight surrogate.

What Is In The Layout
---------------------

* **Object** -> **promoted STEP right-angle mirror solid** (BK7, Mirror face) ->
  trailing AIR gap -> **front optical vertex datum** -> **blackbox group 1** ->
  **F/4.5 stop** -> **blackbox group 2** -> **rear optical vertex datum** -> **image**.
* The vendor lens barrel STEP (``ELS-85-4.5V16K.STEP``) and the camera STEP
  (``3D_CAD_HR25xCXP.STEP``) are preloaded so the scene shows the real bodies.
* The camera **model** (Allied Vision ``hr25MCX``) is kept, so the image format stays
  camera- and FOV-driven at runtime.

Everything else (ray display, source, detector, tolerance, atmosphere, optimization
defaults) is inherited from the straight surrogate.

Rendered Layout
---------------

Load ``Machine Vision Az85 Ra Mirror`` from the Machine Vision menu and open it in
Open 3D.  The object beam runs to the right-angle mirror solid; the mirror face reflects
it, and the ELS-85 surrogate plus the sensor receive the folded beam.  The lens barrel
and the camera bodies render with the optics.

Validation
----------

The standalone validation script checks discovery in the Machine Vision menu, the nine
rows, the promoted STEP mirror solid and its assigned Mirror face, the paraxial EFL
(85 mm) of the blackbox chain, and that both the lens STEP and the camera STEP overlays
are preloaded:

.. code-block:: bash

   python -m KrakenOS.UI.validate_machine_vision_azure_85_ra_mirror
