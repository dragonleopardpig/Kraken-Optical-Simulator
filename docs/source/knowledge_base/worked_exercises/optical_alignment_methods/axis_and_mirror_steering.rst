Reference Axis and Mirror Steering
==================================

The first alignment task is to establish a line in space independently of the
optics that will later be installed.  Two separated irises constrain both the
beam position and direction; two steering mirrors then transfer a source beam
onto that reference line without moving the source body.

Method 1: define the axis with two irises
-----------------------------------------

Place irises :math:`A_1` and :math:`A_2` at the required beam height and
separate them by :math:`L`.  With transverse beam coordinates :math:`x_1` and
:math:`x_2` at the two planes, the small angular error is

.. math::
   :label: align-axis-angle

   \theta_x\simeq\frac{x_2-x_1}{L},
   \qquad
   \theta_y\simeq\frac{y_2-y_1}{L}.

This is why two irises are necessary: one iris constrains position but leaves
angle undetermined.  Separate the irises only after setting both centers to the
same height beside a common mechanical datum.

**Worked example.**  Let :math:`L=0.500\ \mathrm{m}`.  The beam is centered at
:math:`A_1` but is :math:`0.50\ \mathrm{mm}` high at :math:`A_2`:

.. math::
   :label: align-axis-example

   \theta_y=\frac{0.50\times10^{-3}}{0.500}
           =1.0\times10^{-3}\ \mathrm{rad}=1.0\ \mathrm{mrad}.

If left uncorrected, that error becomes 5 mm after another 5 m.  Close
:math:`A_1`, correct the source or upstream steering so the beam remains on
:math:`A_1`, then remove the :math:`A_2` error.  Repeat in horizontal and
vertical axes with successively smaller apertures.

.. figure:: /_static/knowledge_base/worked_exercises/optical_alignment_methods/two_iris_axis.svg
   :alt: Two separated irises distinguish beam position error from angular error
   :width: 100%

   **Figure 1.** One aperture fixes a point; two apertures fix a line.  The
   measured displacement at :math:`A_2` divided by the separation gives the
   paraxial angular error.

**Acceptance check.**  Translate a viewing card just after each iris without
touching the steering controls.  The spot must remain centered at both planes
when each aperture is reopened to its working diameter.  Record the residual
:math:`|x_2-x_1|/L` and :math:`|y_2-y_1|/L`, not merely “beam passes.”

Method 2: walk a dog-leg onto the axis
--------------------------------------

A dog leg uses mirrors :math:`M_1` and :math:`M_2`.  The first mirror changes
where the beam reaches the second mirror; the second predominantly changes the
outgoing angle.  For a ray

.. math::
   :label: align-ray-line

   x(z)=x_0+\theta z,

the desired ray through two reference coordinates is

.. math::
   :label: align-two-point-ray

   \theta=\frac{x_2-x_1}{z_2-z_1},
   \qquad
   x_0=x_1-\theta z_1.

The mirror response has a factor of two:

.. math::
   :label: align-mirror-double-angle

   \Delta\theta_{\rm beam}=2\Delta\phi_{\rm mirror}.

**Worked example.**  After centering :math:`A_1`, the spot is 2.0 mm right at
:math:`A_2`, 0.50 m downstream.  The outgoing ray error is 4.0 mrad, so the
ideal small correction at :math:`M_2` is 2.0 mrad.  That correction usually
disturbs :math:`A_1`; use :math:`M_1` to restore the near-plane position, then
:math:`M_2` to halve the far-plane error.  Alternate until both errors fall
inside tolerance.

.. figure:: /_static/knowledge_base/worked_exercises/optical_alignment_methods/dog_leg_walk.svg
   :alt: Two mirror dog-leg beam walk through near and far irises
   :width: 100%

   **Figure 2.** Use :math:`M_1` mainly to restore the near target and
   :math:`M_2` mainly to correct the far target.  Repetition decouples position
   and angle.

Do not chase both targets with one mirror.  Do not translate an already defined
iris to meet the beam.  When convergence is complete, lock mounts gently and
repeat the measurement because locking torque can shift the spot.
