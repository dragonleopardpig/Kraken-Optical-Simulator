Resonators and Gaussian Beams
=============================

This is the highest-value calculation page for a laser-design interview.  Draw
the cavity, define the sign convention, multiply the matrices, check stability,
solve the eigenmode, and then test apertures, gain overlap, thermal-lens range,
and alignment sensitivity.

ABCD method
-----------

For paraxial propagation in air and a thin lens,

.. math::

   T(d)=\begin{bmatrix}1&d\\0&1\end{bmatrix},
   \qquad
   L(f)=\begin{bmatrix}1&0\\-1/f&1\end{bmatrix}.

A spherical mirror of radius :math:`R` acts like a thin lens of focal length
:math:`R/2` on reflection,

.. math::

   M_R=\begin{bmatrix}1&0\\-2/R&1\end{bmatrix}.

Use the convention of the chosen ray vector consistently.  Reduced-angle
vectors change the translation and refraction matrices inside a dielectric.

For a round-trip matrix

.. math::

   M_{\rm rt}=\begin{bmatrix}A&B\\C&D\end{bmatrix},

the paraxial stability condition is

.. math::
   :label: interview-abcd-stability

   \left|\frac{A+D}{2}\right|<1.

Equality is a stability boundary, not a comfortable design point.  Manufacturing
tolerances, thermal lensing, mirror motion, and refractive-index drift can push a
nominally marginal cavity unstable.

Two-mirror shortcut
-------------------

For two mirrors separated by :math:`L`, define

.. math::
   :label: interview-g-parameters

   g_1=1-\frac{L}{R_1},
   \qquad
   g_2=1-\frac{L}{R_2}.

The cavity is stable when

.. math::

   0<g_1g_2<1.

This shortcut is excellent for intuition but does not replace the full ABCD
model when a gain rod, thermal lens, Brewster plate, telescope, nonlinear
crystal, or nonuniform index lies inside the resonator.

Complex beam parameter
----------------------

Define

.. math::
   :label: interview-q-parameter

   \frac1{q(z)}=\frac1{R(z)}-i\frac{\lambda}{\pi w^2(z)},
   \qquad
   q_2=\frac{Aq_1+B}{Cq_1+D}.

The resonator eigenmode reproduces itself after a round trip:

.. math::

   q=\frac{Aq+B}{Cq+D},

so

.. math::

   Cq^2+(D-A)q-B=0.

Choose the root with a physically positive beam-radius solution.  Once :math:`q`
is known at one plane, propagate it to every optic and record :math:`w`,
:math:`R`, and Gouy phase.

For an ideal Gaussian beam,

.. math::
   :label: interview-gaussian-beam

   z_R=\frac{\pi w_0^2}{\lambda},
   \qquad
   w(z)=w_0\sqrt{1+(z/z_R)^2},
   \qquad
   \theta=\frac{\lambda}{\pi w_0}.

For a real beam, a convenient second-moment model is

.. math::
   :label: interview-m2-beam

   w^2(z)=w_0^2+
   \left[\frac{M^2\lambda(z-z_0)}{\pi w_0}\right]^2,
   \qquad
   \theta=\frac{M^2\lambda}{\pi w_0}.

State the beam-radius convention.  A :math:`1/e^2` intensity radius, a D4σ
second-moment diameter, and a camera threshold diameter are not interchangeable.

Mode spacing and transverse modes
---------------------------------

For an empty two-mirror cavity, one useful mode-frequency form is

.. math::
   :label: interview-transverse-modes

   \nu_{qmn}=\frac{c}{2L}
   \left[
     q+\frac{m+n+1}{\pi}\cos^{-1}\!\left(\sqrt{g_1g_2}\right)
   \right].

The first term is the longitudinal comb; the Gouy-phase term separates
transverse families.  Degeneracies become likely in symmetric or special
geometries and can make transverse-mode control harder.

Design margins that matter
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 23 30 47

   * - Check
     - Calculation
     - Engineering interpretation
   * - Thermal stability
     - Sweep the thermal-lens dioptric power through cold, nominal, and hot states
     - The entire operating range should remain stable with useful mode-size margins
   * - Aperture clearance
     - Compare every clear radius with local :math:`w` or measured second-moment radius
     - A common first pass is several beam radii, then refine from permitted clipping loss
   * - Gain overlap
     - Compare cavity intensity with absorbed-pump distribution throughout the medium
     - Oversized cavity modes waste inversion; undersized modes raise intensity and thermal sensitivity
   * - Coating loading
     - Convert circulating power to peak irradiance on each optic
     - Account for angle, polarization, standing-wave enhancement, pulse shape, and hot spots
   * - Alignment
     - Perturb each mirror in the ray/misalignment model
     - Near-boundary and high-magnification cavities can be extremely sensitive
   * - Tolerance
     - Monte Carlo radii, spacing, focal power, decenter, tilt, and index
     - Report yield or worst credible margin, not only the nominal solution

Thermal lens as a design variable
---------------------------------

Model the pumped gain element initially as a thin lens :math:`f_{\rm th}` at its
principal plane, but treat that as a range, not a fixed catalog value:

.. math::

   \Phi_{\rm th}=\frac1{f_{\rm th}}
   =\Phi_{dn/dT}+\Phi_{\rm bulge}+\Phi_{\rm photoelastic}+\cdots.

Its power depends on absorbed pump, pump radius and distribution, cooling
boundary conditions, geometry, material properties, and polarization.  Higher
order aberration and stress birefringence are not captured by a perfect thin
lens.

A credible resonator answer therefore says:

1. how the cold cavity was chosen;
2. what thermal-lens interval is expected;
3. how eigenmode radii move over that interval;
4. where stability boundaries lie;
5. which optic or aperture becomes limiting; and
6. how the prediction will be measured and updated.

Common interview traps
----------------------

* ``Stable`` does not mean robust; it only passes the ideal eigenmode criterion.
* A small waist improves nominal focusability but raises divergence and local
  irradiance.
* :math:`M^2` is not a fixed spot-size multiplier at every plane; propagate the
  second-moment beam consistently.
* Cavity mode matching concerns a resonator eigenmode; external pump focusing is
  a separate overlap problem.
* A beam that looks circular on one camera plane may still be astigmatic.
* Clipping can make a camera fit look deceptively clean while power and
  diffraction loss degrade.
