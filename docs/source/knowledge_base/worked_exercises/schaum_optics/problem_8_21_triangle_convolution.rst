.. _schaum-problem-8-21:

Problem 8.21 — from Fig. 8-29 to Fig. 8-30
==========================================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of Optics*
(1975), Chapter 8, Solved Problem 8.21, printed page 222 (PDF page 228).
This explanation supplements the :doc:`Chapter 8 supplementary solutions
<ch08_introduction_to_fourier_optics>`.

**Paraphrased task.** Construct the two-dimensional convolution of the two
three-hole masks in Fig. 8-29 and explain the positions and relative weights
of the spots in Fig. 8-30.

**Answer.** Put a complete copy of the downward-pointing triangle
:math:`h(x,y)` at each of the three hole centres of :math:`f(x,y)`, then
add the contributions at coincident positions.  The nine contributions
occupy seven positions: six outer spots of weight 1 and a central spot of
weight 3.  The crosses and dashed triangles in Fig. 8-30 show how these
copies were placed.

Step 1: Label the two masks
---------------------------

Treat each small, equally weighted hole as a unit point impulse.  Choose
the centroid of each triangle as its local origin, with :math:`x` pointing
right and :math:`y` pointing up.  The second mask is the first triangle
turned through :math:`180^\circ` about that origin.

For a convenient equilateral construction, let :math:`a>0` be half the
horizontal separation of the lower holes of :math:`f`, and set
:math:`b=a/\sqrt{3}`.  Label the first triangle's holes

.. math::

   \mathbf r_A=(0,2b),\qquad
   \mathbf r_B=(-a,-b),\qquad
   \mathbf r_C=(a,-b).

The holes of :math:`h` are at the opposite coordinates:

.. math::

   \mathbf s_{A'}=-\mathbf r_A=(0,-2b),\qquad
   \mathbf s_{B'}=-\mathbf r_B=(a,b),\qquad
   \mathbf s_{C'}=-\mathbf r_C=(-a,b).

The book's drawing is schematic.  The equilateral choice makes the outer
hexagon regular; the three central overlaps follow from the opposite
coordinates regardless of the triangle's aspect ratio.

.. figure:: /_static/knowledge_base/worked_exercises/schaum_optics/problem_8_21/masks.svg
   :alt: An upward triangle with holes A, B, C and a downward triangle with holes A prime, B prime, C prime, each centred on its own origin.
   :width: 100%
   :align: center

   Original coordinate diagrams of the two masks in Fig. 8-29.  A cross
   marks each local origin; it is not a fourth hole.

Step 2: Use the impulse-shift rule
----------------------------------

The convolution is

.. math::
   :label: schaum-8-21-convolution

   g(x,y)=(f*h)(x,y)
   =\int_{-\infty}^{\infty}\int_{-\infty}^{\infty}
   f(\xi,\eta)\,h(x-\xi,y-\eta)\,d\xi\,d\eta.

Writing :math:`\delta^{(2)}` for a two-dimensional impulse, the first mask is
:math:`f(\mathbf r)=\sum_{i\in\{A,B,C\}}\delta^{(2)}(\mathbf r-\mathbf r_i)`.
Substitution into :eq:`schaum-8-21-convolution` gives

.. math::

   g(x,y)
   =h(x,y-2b)+h(x+a,y+b)+h(x-a,y+b).

Each term is the **same downward-pointing triangle**, translated so that
its centroid lies at one of the three holes of :math:`f`:

* :math:`h(x,y-2b)` is centred at :math:`A=(0,2b)`;
* :math:`h(x+a,y+b)` is centred at :math:`B=(-a,-b)`;
* :math:`h(x-a,y+b)` is centred at :math:`C=(a,-b)`.

This is what the three small crosses in Fig. 8-30 indicate.  They mark
the original :math:`f` hole positions and the centroids of the translated
copies.  A cross is a construction mark, not an additional output spot.

**Why is there no extra flip?** In the graphical overlap method,
:math:`h(x-\xi,y-\eta)` is reflected as a function of the integration
coordinates :math:`(\xi,\eta)`.  After an impulse selects
:math:`(\xi,\eta)=\mathbf r_i`, the output is
:math:`h(\mathbf r-\mathbf r_i)`: a translated copy of the original
:math:`h`, with its orientation preserved in the output coordinates.
Rotating that copy again would construct a different convolution.

Step 3: Add the nine pairs of hole coordinates
----------------------------------------------

A hole at :math:`\mathbf r_i` in :math:`f` and a hole at
:math:`\mathbf s_{j'}` in :math:`h` contribute at their **sum**:

.. math::

   \delta^{(2)}(\mathbf r-\mathbf r_i)
   *\delta^{(2)}(\mathbf r-\mathbf s_{j'})
   =\delta^{(2)}\bigl(\mathbf r-(\mathbf r_i+\mathbf s_{j'})\bigr).

There are :math:`3\times3=9` pairs.  List all of them before combining
coincident positions:

.. list-table:: Output position for each pair
   :header-rows: 1
   :widths: 25 25 25 25

   * - First-mask hole
     - Add :math:`A'=(0,-2b)`
     - Add :math:`B'=(a,b)`
     - Add :math:`C'=(-a,b)`
   * - :math:`A=(0,2b)`
     - :math:`(0,0)`
     - :math:`(a,3b)`
     - :math:`(-a,3b)`
   * - :math:`B=(-a,-b)`
     - :math:`(-a,-3b)`
     - :math:`(0,0)`
     - :math:`(-2a,0)`
   * - :math:`C=(a,-b)`
     - :math:`(a,-3b)`
     - :math:`(2a,0)`
     - :math:`(0,0)`

The first row draws the upper downward-pointing triangle in Fig. 8-30:
its top two spots are at :math:`(\pm a,3b)`, and its bottom spot is at
the origin.  The second row draws the lower-left triangle, and the third
row draws the lower-right triangle.  Their dashed outlines meet at the
origin, where :math:`A+A'`, :math:`B+B'`, and :math:`C+C'` all coincide.

.. figure:: /_static/knowledge_base/worked_exercises/schaum_optics/problem_8_21/construction.svg
   :alt: Three coloured downward triangles centred at A, B, C overlap at the origin. The combined pattern has six outer positions labelled 1 and one central position labelled 3.
   :width: 100%
   :align: center

   Left: the three translated copies of :math:`h`; crosses locate their
   centroids.  Right: combine coincident contributions to obtain the
   pattern in Fig. 8-30.  Numbers indicate weights, not hole diameters.

Step 4: State and check the result
----------------------------------

Let :math:`\mathcal V` be the six outer positions:

.. math::

   \mathcal V=\{(-2a,0),(2a,0),(-a,3b),(a,3b),
   (-a,-3b),(a,-3b)\}.

Then the convolution is

.. math::
   :label: schaum-8-21-result

   \boxed{g(\mathbf r)=3\delta^{(2)}(\mathbf r)
   +\sum_{\mathbf v\in\mathcal V}\delta^{(2)}(\mathbf r-\mathbf v).}

Every outer spot receives one contribution and the centre receives three.
For :math:`b=a/\sqrt{3}`, all six outer spots lie at radius :math:`2a`,
with angular spacing :math:`60^\circ`.

**Check.** The total weight is :math:`6\times1+3=9`, equal to the product
of the input weights :math:`3\times3`.  All off-diagonal coordinate sums
occur in opposite pairs, so the result is symmetric about its centre.

Physical placement: do the masks need to move?
----------------------------------------------

**They can stay fixed.** The translated triangles in Fig. 8-30 are
contributions to the output, not successive physical positions of the
second mask.  The book specifies the mathematical convolution but gives
no optical layout or mask separation for Problem 8.21.  A distance must
therefore be chosen for a particular implementation.

Putting the masks in contact under uniform illumination gives the
pointwise product :math:`f(x,y)h(x,y)`.  To obtain the convolution pattern
simultaneously, each first-mask hole must illuminate all three holes of
the second mask and project its own shifted three-spot pattern onto a
screen.

A fixed-mask shadow-projection arrangement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use three parallel planes with their triangle centroids on a common axis:

1. Place a uniformly illuminated diffuser immediately behind a source
   mask.  Its three holes act as small, mutually incoherent emitters
   radiating toward the second mask.
2. Place the aperture mask a distance :math:`d` downstream.
3. Place a screen a further distance :math:`D` downstream.

For an emitter at transverse position :math:`\mathbf u` and an aperture
at :math:`\mathbf v`, a straight ray reaches the screen at

.. math::
   :label: schaum-8-21-shadow-ray

   \mathbf R
   =\mathbf v+\frac{D}{d}(\mathbf v-\mathbf u)
   =\left(1+\frac{D}{d}\right)\mathbf v-\frac{D}{d}\mathbf u.

Thus each source projects an enlarged copy of the second mask, with
magnification :math:`1+D/d`, and its centre shifts in the opposite
direction to the source.  This reversal and magnification must be
included when preparing the masks.  The general principle of adding
shifted, scaled shadows under incoherent illumination is described in
`Wu et al., Single-shot lensless imaging with fresnel zone aperture and
incoherent illumination (2020), Materials and methods: Imaging model
<https://www.nature.com/articles/s41377-020-0289-9>`_.  The construction
below is derived from the straight-ray geometry for this three-hole
example; it is not an apparatus specified by Hecht.

To obtain a scaled version of :math:`f*h`, use aperture positions
:math:`\mathbf v_j=\mathbf s_{j'}` and source positions

.. math::

   \mathbf u_i=-\frac{d+D}{D}\mathbf r_i.

In other words, rotate the :math:`f` pattern through :math:`180^\circ`
about its centroid and enlarge its **hole-centre spacing** by
:math:`(d+D)/D`.  The individual hole diameters can remain small.
Equation :eq:`schaum-8-21-shadow-ray` then becomes

.. math::

   \mathbf R_{ij}=\left(1+\frac{D}{d}\right)
   (\mathbf r_i+\mathbf s_{j'}).

All nine ray paths therefore land at the positions in the coordinate
table, multiplied by a common scale factor.

**A concrete starting layout.** Set :math:`d=D=100\,\mathrm{mm}`.
Use an equilateral aperture mask with 8 mm between hole centres, and a
source mask with 16 mm between centres.  The source pattern is the
rotated :math:`f`, so both physical triangles point downward when viewed
in the same transverse coordinates.  Use roughly 1 mm diameter holes,
uniform diffuse LED illumination, and a screen large enough to capture
the output.  The screen receives a pattern twice the scale of the
mathematical construction, with six outer spot centres at radius 16 mm
and three contributions meeting at the centre.

.. figure:: /_static/knowledge_base/worked_exercises/schaum_optics/problem_8_21/bench.svg
   :alt: Front views of a downward source triangle with twice the spacing of the downward aperture triangle, followed by a screen with seven spots; the two axial gaps are each 100 mm.
   :width: 100%
   :align: center

   A fixed-mask implementation derived for :math:`d=D`.  All front views
   use the same transverse scale.  The source mask compensates the
   reversal and magnification of shadow projection.

These distances are illustrative, not unique.  Changing :math:`D/d`
changes both the necessary source-mask spacing and the output scale.
Keeping two equal-size masks in the orientations of Fig. 8-29 and
choosing an arbitrary gap does not ensure the three central overlaps.
Finite source size and diffraction broaden the spots; the simple ray
model assumes small angles and well-separated spots.

When moving a mask is useful
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Another way to measure the convolution is to scan overlap.  Illuminate
:math:`f` uniformly, rotate the :math:`h` mask through :math:`180^\circ`,
and translate it by :math:`(x,y)` in a plane coincident with :math:`f`,
or optically imaged onto it.  At each shift, a detector collects the
**total transmitted power** over the overlap:

.. math::

   P(x,y)\propto\iint f(\xi,\eta)h(x-\xi,y-\eta)\,d\xi\,d\eta.

Here the masks can be nearly in contact, with a small mechanical clearance;
there is no special propagation distance.  Record one number per shift
and plot those numbers against :math:`(x,y)` to reconstruct Fig. 8-30.
Sliding without the rotation measures correlation instead.  The fixed
shadow-projection setup produces all seven spots at once, while scanning
measures their weights one position at a time.

Finite holes and the meaning of brightness
------------------------------------------

For finite identical holes with aperture profile :math:`p(\mathbf r)`,
replace each point impulse in the inputs by a translated copy of
:math:`p`.  Each output spot then has profile :math:`p*p`, so the complete
output is :math:`(p*p)*g`, with :math:`g` from :eq:`schaum-8-21-result`.
The positions and multiplicities remain the same.  The holes must be small
enough for the seven output spots to remain separate.

The central weight 3 describes the addition of three equal contributions
in the function being convolved.  If these functions represent intensities
in an incoherent optical implementation, the central spot is three times
as bright as one outer spot.  If they represent coherent field amplitudes,
equal contributions arriving in phase give three times the field and nine
times the intensity; other phases can change that intensity.  The geometry
in Fig. 8-30 establishes the overlap count without specifying those phases.
