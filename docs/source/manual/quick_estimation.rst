Quick Estimation (object / image / FOV)
=======================================

Quick Estimation is a live **finite-conjugate imaging** aid in the Open 3D
viewer, built for machine-vision setups where the camera (sensor) is fixed and
you trade object distance, image distance, magnification, and field of view
(FOV) against one another.

It is driven by the conjugate relationship of the fixed lens:

.. math::

   \frac{1}{s_o} + \frac{1}{s_i} = \frac{1}{f}, \qquad
   |m| = \frac{s_i}{s_o}, \qquad
   \mathrm{FOV} = \frac{\text{sensor semi-height}}{|m|}

where :math:`s_o` and :math:`s_i` are the object and image distances measured
from the lens principal planes and :math:`f` is the focal length.

The design flow
---------------

#. **Pin the sensor in the left panel.** Set ``Field Type`` to
   ``Real Image Semi-Height`` with the sensor half-height as the ``Field value``.
   This is the fixed camera; Quick Estimation never changes it.
#. **Turn on Quick Estimation** in the Live Controls panel, and enable physical
   distances so the thickness arrows are visible and hoverable.
#. **Drive a conjugate gap.** Drag a thickness arrow, click it to type a value,
   or right-click it for a role. Whichever gap you touch becomes the
   *independent* variable; its conjugate partner re-solves for **focus**, so the
   image stays sharp, and the FOV readout follows the new magnification.

Two readings of the same move
-----------------------------

Dragging always keeps the image **in focus** (the other distance auto-solves).
What you read off depends on what you are holding fixed:

* **Fixed object size → fill factor.** Set a *target Object Height* (the real
  object you want to image). As you drag, the image grows or shrinks on the
  fixed sensor; the readout shows the fill percentage. Above 100 % the object
  overfills and is cropped; below 100 % it underfills.
* **Fixed sensor fill → FOV.** With no target set, the FOV that exactly fills
  the sensor is reported and changes as you drag.

There is exactly **one** focused conjugate pair per FOV: for a fixed lens and
sensor, the target FOV fixes the magnification :math:`|m| = \text{sensor}/\text{FOV}`,
and a given magnification has a unique pair
:math:`s_o = f(1 + 1/|m|)`, :math:`s_i = f(1 + |m|)`. **Snap to FOV** jumps both
gaps straight to that pair. The **Configuration table** sweeps the object
distance and lists the focused conjugate combinations (object/image distance,
magnification, FOV, working distance, real-image validity).

Right-click actions
-------------------

* **Object plane / object-distance arrow** — set the target Object Height (FOV),
  snap both gaps to that FOV, open the configuration table, or set the gap role
  (Independent / Dependent / Constant).
* **Image plane / image-distance arrow** — set the sensor semi-height
  (the same left-panel ``Field value``) or set the role.

Graphical FOV solve (double-click a plane)
------------------------------------------

For a direct, graphical alternative to the menu, **double-click** the Object or
Image plane in the 3D canvas. A small popup opens, pre-filled with that plane's
field **Width × Height** — the Object field that exactly fills the current
sensor, or the sensor's own active dimensions. Both planes hover-highlight and
accept the double-click, including the green detector-coverage FOV square when
the *Det* overlay is on.

Two buttons decide what the solver changes:

* **Solve for Thickness** — move the object↔image conjugate pair so the typed
  field maps onto the sensor, in focus. The sensor is left untouched.
* **Solve for Image/Sensor Size** — keep the current magnification and resize the
  terminal sensor so the typed field maps onto it. No thickness changes.

Height is optional: leave it blank and the vertical extent follows the 4:3
working aspect, giving exactly the original single-width solve.

Variable-thickness solve (Best Focus / Best Collimation)
--------------------------------------------------------

The Live Controls panel has a **Solve (Variable thickness)** section that mirrors
the 2D editor's 1-D solve. Tick one or more thickness gaps **Variable** — this is
the same ``optimize_thickness`` flag the 2D optimizer reads, so a gap flagged in
either view is flagged in both — then press:

* **Solve Best Focus** — minimise the image spot RMS. The terminal Image gap is
  the axial reference and is never a variable; the object gap is excluded, since
  moving the object is not a focus knob.
* **Solve Best Collimation** — drive the paraxial output vergence
  :math:`|1/s'|` to zero, i.e. send the exit beam to infinity. This objective
  *includes* the object gap, because moving the source toward the front focal
  point is the canonical way to parallelise the output. On the 150 mm 1× layout
  the collimated object distance lands at the front focal distance
  (:math:`\mathrm{EFL} - \mathrm{ppa} \approx 125` mm).

With several gaps Variable the solver runs a few coordinate-descent passes until
every gap settles. Each solve is one undoable step and retraces the scene.

Sensor coverage and recommended sensor
--------------------------------------

When Quick Estimation is on, the 3D scene draws coverage overlays:

* **Object plane** — a solid circle at the current object FOV and a dashed
  *ghost* circle at the previous FOV, so a change reads as bigger or smaller.
* **Image plane** — a solid circle at the image footprint, the recommended
  rectangular sensor inscribed in it (so you see the image circle covering the
  sensor), and a dashed ghost of the previous image circle.

The panel reports a **recommended sensor**: the rectangle whose diagonal matches
the image footprint of the object being imaged, with width × height (4:3), the
image-circle diameter, and the nearest standard format (``1/4"`` …
``Full-frame``) — so you can size or source a camera the image circle perfectly
covers. Overfilling the current sensor recommends a larger format; underfilling
recommends a smaller one.

Forbidden values
----------------

If you drag the object inside the front focal point — the working distance falls
below the focal length — no real image can form. The thickness arrow **flashes
red** with a warning and the live commit is suppressed until you back off.

Validation
----------

The behaviour is guarded across all five machine-vision layouts (150 mm 1×/0.5×,
120 mm, 85 mm, 150 mm measured) by
``KrakenOS/UI/validate_open3d_quick_estimation_conjugate.py`` (comprehensive
harness Phase 34): focus is held, ``FOV = sensor / |m|``, FOV is monotonic with
object distance, both solve directions work, ``snap_to_fov`` reproduces the
unique conjugate pair, the forbidden region is detected, and the live drag
preview does not mutate committed thicknesses.

The graphical FOV solve is guarded by
``KrakenOS/UI/validate_open3d_fov_plane_solve.py`` (harness Phase 60, with the
Object/Image plane pickability checked live in Phase 61), and the
Variable-thickness Best Focus / Best Collimation solve by
``KrakenOS/UI/validate_open3d_thickness_solve.py`` (harness Phase 62).
