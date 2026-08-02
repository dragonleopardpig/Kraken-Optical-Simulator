Appendix A: Aperture Properties of Centered Systems
===================================================

Source: Gerrard and Burch, *Introduction to Matrix Methods in Optics* (1975),
Appendix A.

.. rubric:: Problem A.1 — Stops, pupils, windows, and field in a finder telescope

The finder has a 30-mm-diameter, 100-mm-focal-length objective and a
5-mm-diameter, 10-mm-focal-length eye lens.  The lenses are confocal, with a
6.5-mm diaphragm at their common focus.  Choose reference planes on both
sides of each lens and form cumulative transfer matrices back toward the
objective.

The overall matrix is afocal with angular magnification :math:`-10`.  For each
physical aperture of radius :math:`J_k`, compare
:math:`J_k/|(L_{11})_k|`; the smallest value identifies the aperture stop.
The objective rim wins, so

.. math::

   \boxed{\text{aperture stop = objective}},
   \qquad
   \boxed{\text{entrance pupil = objective}}.

Imaging the objective through the eyepiece puts the exit pupil (Ramsden disc)
11 mm to the right of the eye lens, with diameter 3 mm.  The observer's 4-mm
pupil therefore passes the axial bundle when centered there, although the
lateral tolerance is only about :math:`\pm0.5\ \mathrm{mm}`.

For principal rays, compare the maximum field angle allowed by every stop.
The 5-mm eye-lens rim, rather than the focal-plane diaphragm, limits the
principal field:

.. math::

   \boxed{\text{field stop = eye lens}},
   \qquad
   \boxed{\text{exit window = eye lens}}.

Its conjugate entrance window lies 1.1 m to the left of the objective and has
diameter 50 mm.  Intersecting the stop boundaries in the normalized
:math:`(\phi,\eta)` aperture diagram gives

.. list-table:: Object-space angular field
   :header-rows: 1
   :widths: 42 28 30

   * - Field definition
     - Radius (radians)
     - Diameter (degrees)
   * - Full illumination
     - :math:`0.0091`
     - :math:`1.04^\circ`
   * - Principal-ray field
     - :math:`0.0227`
     - :math:`2.60^\circ`
   * - Total field
     - :math:`0.0325`
     - :math:`3.72^\circ`

The corresponding apparent angles in image space are ten times larger.
Moving the eye 5 mm toward the eye lens (to 6 mm) introduces no additional
limit because the eye lens still dominates.  Moving it 5 mm away (to 16 mm)
clips the opposite side and reduces the total field radius to
:math:`0.0281\ \mathrm{rad}`, or
:math:`\boxed{3.22^\circ}` full diameter.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_matrix_methods_optics/aperture_stop_geometry.svg
   :alt: Finder telescope showing objective aperture stop, focal diaphragm, eye-lens field stop, exit pupil, and marginal rays.
   :align: center
   :width: 100%

   The matrix calculation distinguishes the stop itself from its entrance and
   exit pupil images; the field calculation uses chief-ray rather than
   marginal-ray limits.
