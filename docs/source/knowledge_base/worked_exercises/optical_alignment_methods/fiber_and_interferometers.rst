Fiber Coupling and Interferometer Alignment
===========================================

Fiber injection and interferometers both demand simultaneous position and
angle matching.  A bright spot on a detector is not sufficient evidence: fiber
coupling requires spatial-mode overlap, while interference requires the two
fields to overlap with compatible propagation directions and optical path
lengths.

Method 8: focus into a fiber
----------------------------

Start from the focused-spot requirement.  For a circular collimated beam of
diameter :math:`D` focused by a lens of focal length :math:`f`, the Airy diameter
is

.. math::
   :label: align-fiber-airy

   d_{\rm Airy}=2.44\frac{\lambda f}{D}.

The focusing numerical aperture must also fit the fiber acceptance:

.. math::
   :label: align-fiber-na

   \mathrm{NA}_{\rm focus}\simeq\frac{D}{2f},
   \qquad
   \mathrm{NA}_{\rm focus}\lesssim\mathrm{NA}_{\rm fiber}.

**Worked example.**  For :math:`\lambda=633\ \mathrm{nm}`,
:math:`D=4.0\ \mathrm{mm}`, and :math:`f=11\ \mathrm{mm}`,
:math:`d_{\rm Airy}=4.25\ \mu\mathrm{m}` and
:math:`\mathrm{NA}_{\rm focus}\simeq0.182`.  This is geometrically compatible
with a 9 micrometre core only if the fiber NA is at least about 0.18; otherwise
increase :math:`f` or reduce the filled lens diameter.

For matched Gaussian modes with radius :math:`w`, lateral offset alone reduces
power coupling approximately as

.. math::
   :label: align-fiber-lateral-coupling

   \eta_x=\exp\!\left[-2\left(\frac{\delta}{w}\right)^2\right].

If :math:`w=2.5\ \mu\mathrm{m}` and :math:`\delta=1.0\ \mu\mathrm{m}`, only
72.6% remains before angular, focus, Fresnel, and mode-shape losses.

.. figure:: /_static/knowledge_base/worked_exercises/optical_alignment_methods/fiber_coupling.svg
   :alt: Raster search and fine optimization of focus into an optical fiber
   :width: 100%

   **Figure 1.** Establish the fiber-face plane, raster :math:`x,y` until any
   transmitted signal is found, then optimize :math:`z`, :math:`x`, :math:`y`,
   tip, and tilt with progressively smaller excursions.

Use a power meter at the far end, normalize to power immediately before the
coupling lens, and record

.. math::
   :label: align-fiber-measured-efficiency

   \eta_{\rm measured}=\frac{P_{\rm fiber,out}}
   {P_{\rm before\ lens}\,T_{\rm known}}.

After every focus adjustment, repeat the local :math:`x,y` optimization because
thread runout can move the spot in a circle.  Tighten the lock, wait for settling,
and remeasure; the locked result is the accepted result.

Method 9: align a Michelson interferometer
------------------------------------------

First align each arm independently.  Block arm 2, retroreflect arm 1 through
the beamsplitter to near and far targets; then exchange the blocks.  Near-plane
coincidence controls position and far-plane coincidence controls angle.  Only
then unblock both arms.

For equal-frequency plane waves crossing at small angle
:math:`\Delta\theta`, the fringe spacing is

.. math::
   :label: align-fringe-angle

   p\simeq\frac{\lambda}{\Delta\theta}.

At 632.8 nm, 5.0 mm fringes correspond to
:math:`\Delta\theta=126.6\ \mu\mathrm{rad}`.  As mirror tilt is corrected, the
fringes widen; the limit is a nearly uniform field when the wavefront
curvatures also match.

The Michelson optical-path difference is

.. math::
   :label: align-michelson-opd

   \mathrm{OPD}=2n_1L_1-2n_2L_2,

and interference visibility requires its magnitude to lie within the source
coherence length.  Matching spots without matching OPD can therefore produce
no visible fringes.

.. figure:: /_static/knowledge_base/worked_exercises/optical_alignment_methods/michelson_alignment.svg
   :alt: Michelson arm-by-arm alignment and near-far overlap test
   :width: 100%

   **Figure 2.** Align each return separately, compare both beams at two planes,
   then use fringe spacing as the angular residual.  A large-area detector can
   hide non-overlapping spots, so view the field before integrating it.

If both output ports are accessible, their interference terms have opposite
sign.  Balanced detection subtracts the photocurrents, doubling the modulated
term while rejecting common intensity noise, subject to detector matching.

Method 10: align a Mach--Zehnder interferometer
-----------------------------------------------

A Mach--Zehnder has two separate forward paths, so it lacks the automatic
return-path overlap of a Michelson.  Define the input axis, align the first
beamsplitter, and propagate each arm to the second beamsplitter while the other
is blocked.  Use one mirror per arm to place both output spots at a near target
and a second steering degree of freedom to overlap them at a far target.

.. math::
   :label: align-mach-zehnder-opd

   \mathrm{OPD}=n_1L_1-n_2L_2,
   \qquad
   I=I_1+I_2+2\sqrt{I_1I_2}\,V\cos\Delta\phi.

The ideal intensity-balance contribution to visibility is

.. math::
   :label: align-visibility-balance

   V_{\rm balance}=\frac{2\sqrt{I_1I_2}}{I_1+I_2}.

For an arm-power ratio of 4:1, even perfect spatial and temporal coherence gives
only :math:`V_{\rm balance}=0.80`.  Do not misdiagnose that contrast limit as
angular misalignment.

.. figure:: /_static/knowledge_base/worked_exercises/optical_alignment_methods/mach_zehnder_alignment.svg
   :alt: Mach-Zehnder alignment using blocked arms and two-plane overlap
   :width: 100%

   **Figure 3.** Position overlap at one screen is insufficient.  Near and far
   coincidence closes the two transverse positions and two propagation angles;
   path length and polarization are then optimized separately.

Final acceptance is quantitative: record near/far centroid differences, fringe
spacing or fitted relative angle, arm powers, visibility, and OPD margin to the
measured or specified coherence length.
