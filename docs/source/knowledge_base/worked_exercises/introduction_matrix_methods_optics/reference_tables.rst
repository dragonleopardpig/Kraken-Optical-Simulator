Matrix-Optics Reference Tables
==============================

This page recreates the four principal summary tables in Gerrard and Burch as
Sphinx-native tables.  Notation has been regularized and short verification
notes have been added.  The diagrams are original SVG companions rather than
scans of the printed pages.

Ray-transfer matrices
---------------------

Use the reduced ray vector :math:`\mathbf r=(y,V)^T=(y,nv)^T`, surface power
:math:`P=(n_2-n_1)/r`, and translation
:math:`T(t,n)=(1,t/n;0,1)`.  For a mirror the outgoing index changes sign, so
:math:`P=-2n/r`.

.. list-table:: Recreated Table 1 — common ray-transfer matrices
   :header-rows: 1
   :widths: 8 35 37 20

   * - No.
     - Situation
     - Matrix
     - Quick check
   * - 1
     - Translation through thickness :math:`t` in index :math:`n`
     - :math:`\begin{bmatrix}1&t/n\\0&1\end{bmatrix}`
     - Heights shear; :math:`V` is unchanged.
   * - 2
     - Refraction at one spherical surface
     - :math:`\begin{bmatrix}1&0\\-P&1\end{bmatrix}`,
       :math:`P=(n_2-n_1)/r`
     - Height is continuous.
   * - 3
     - Reflection at one spherical surface
     - :math:`\begin{bmatrix}1&0\\2n/r&1\end{bmatrix}`
     - Plane mirror: :math:`r\to\infty` gives :math:`I`.
   * - 4
     - Thin lens in air, focal length :math:`f`
     - :math:`\begin{bmatrix}1&0\\-1/f&1\end{bmatrix}`
     - Parallel ray crosses axis after :math:`f`.
   * - 5
     - Between the principal planes of a lens system
     - :math:`\begin{bmatrix}1&0\\-1/f&1\end{bmatrix}`
     - Same reduced action as a thin lens.
   * - 6
     - Between the two focal planes
     - :math:`\begin{bmatrix}0&f\\-1/f&0\end{bmatrix}`
     - Height and angle exchange roles.
   * - 7
     - Imaging between conjugate planes with lateral magnification :math:`m`
     - :math:`\begin{bmatrix}m&0\\-1/f&1/m\end{bmatrix}`
     - :math:`B=0`; object height alone fixes image height.
   * - 8
     - Afocal system with lateral magnification :math:`m`
     - :math:`\begin{bmatrix}m&0\\0&1/m\end{bmatrix}`
     - :math:`C=0`; parallel input remains parallel.

Every matrix has determinant one.  For a compound system, multiply in reverse
order of encounter so the rightmost factor acts first.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_matrix_methods_optics/ray_matrix_elements.svg
   :alt: Eight panels illustrating translation, refraction, reflection, thin lens, principal planes, focal planes, conjugate imaging, and an afocal telescope.
   :align: center
   :width: 100%

   Optical meaning of the eight matrices in the recreated ray-transfer table.

Resonator and Gaussian-beam relations
--------------------------------------

Let :math:`M=(A,B;C,D)` be a real unimodular round-trip matrix and define
:math:`s=(A+D)/2`.

.. list-table:: Recreated Table 2a — eigenvalue and stability summary
   :header-rows: 1
   :widths: 22 26 28 24

   * - Regime
     - Criterion
     - Eigenvalues
     - Interpretation
   * - Positive unstable branch
     - :math:`s>1`
     - :math:`\lambda_\pm=e^{\pm\tau}`,
       :math:`\cosh\tau=s`
     - One eigenray expands while its reciprocal contracts.
   * - Negative unstable branch
     - :math:`s<-1`
     - :math:`\lambda_\pm=-e^{\pm\tau}`,
       :math:`\cosh\tau=-s`
     - Expansion/contraction plus parity reversal.
   * - Stable
     - :math:`|s|<1`
     - :math:`\lambda_\pm=e^{\pm i\theta}`,
       :math:`\cos\theta=s`
     - Bounded ray orbit and confined Gaussian eigenmode.
   * - Marginal
     - :math:`|s|=1`
     - Repeated :math:`+1` or :math:`-1`
     - Stability boundary; diffraction/apertures decide behavior.

For the unstable branches, the real eigenvector curvature may be written

.. math::

   R=\frac{\lambda-D}{C},
   \qquad
   \frac1R=\frac{\lambda-A}{B}.

For the stable branch, choose the fixed point with the physical imaginary
sign:

.. math::

   q=\frac{A-D}{2C}+i\frac{\sin\theta}{C},
   \qquad
   \frac1q=\frac{D-A}{2B}+i\frac{\sin\theta}{B}.

With the book's convention :math:`1/q=1/R+i\lambda/(\pi w^2)`, the associated
beam data are:

.. list-table:: Recreated Table 2b — Gaussian eigenbeam parameters
   :header-rows: 1
   :widths: 34 38 28

   * - Parameter
     - Formula at the reference plane
     - Interpretation
   * - Wavefront curvature
     - :math:`R=2B/(D-A)`
     - Infinite when :math:`A=D`.
   * - Spot radius
     - :math:`w^2=\lambda B/(\pi\sin\theta)`
     - Select the eigenvalue branch giving :math:`w^2>0`.
   * - Neck location
     - :math:`z=(A-D)/(2C)`
     - Signed distance from the reference plane.
   * - Neck radius
     - :math:`w_0^2=-\lambda\sin\theta/(\pi C)`
     - Physical branch again requires positivity.
   * - Confocal parameter
     - :math:`z_0=-\sin\theta/C=\pi w_0^2/\lambda`
     - Half the usual confocal length under this notation.
   * - Mode discrimination warning
     - Geometrical stability alone is insufficient.
     - Aperture loss and gain profile select transverse modes.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_matrix_methods_optics/resonator_stability.svg
   :alt: Trace axis with stable region between minus one and one and Gaussian mode between two curved mirrors.
   :align: center
   :width: 100%

   The half-trace classifies the matrix; the physical fixed point supplies the
   Gaussian eigenmode.

Mueller matrices
----------------

Use Stokes order :math:`(I,Q,U,V)^T`,
:math:`C_2=\cos2\theta`, :math:`S_2=\sin2\theta`,
:math:`\beta=\cos\delta`, and :math:`\mu=\sin\delta`.

.. list-table:: Recreated Table 3 — ideal Mueller elements
   :header-rows: 1
   :widths: 24 56 20

   * - Device
     - Mueller matrix
     - Special cases
   * - Linear polarizer at :math:`\theta`
     - :math:`\dfrac12\begin{bmatrix}
       1&C_2&S_2&0\\C_2&C_2^2&C_2S_2&0\\
       S_2&C_2S_2&S_2^2&0\\0&0&0&0
       \end{bmatrix}`
     - :math:`\theta=0` passes :math:`+Q`; :math:`\theta=\pi/2` passes
       :math:`-Q`.
   * - Linear retarder, retardance :math:`\delta`, fast axis :math:`\theta`
     - :math:`\begin{bmatrix}
       1&0&0&0\\
       0&C_2^2+S_2^2\beta&C_2S_2(1-\beta)&-S_2\mu\\
       0&C_2S_2(1-\beta)&S_2^2+C_2^2\beta&C_2\mu\\
       0&S_2\mu&-C_2\mu&\beta
       \end{bmatrix}`
     - Quarter wave: :math:`\delta=\pi/2`; half wave:
       :math:`\delta=\pi`.
   * - Quarter-wave retarder, fast axis horizontal
     - :math:`\begin{bmatrix}1&0&0&0\\0&1&0&0\\0&0&0&1\\0&0&-1&0\end{bmatrix}`
     - Interchanges :math:`U` and :math:`V` with the convention's signs.
   * - Half-wave retarder, fast axis horizontal
     - :math:`\operatorname{diag}(1,1,-1,-1)`
     - Reverses the :math:`U,V` components.
   * - Rotation of axes through :math:`\theta`
     - :math:`R_M(\theta)=\begin{bmatrix}
       1&0&0&0\\0&C_2&S_2&0\\0&-S_2&C_2&0\\0&0&0&1
       \end{bmatrix}`
     - Rotates the linear Stokes pair by :math:`2\theta`.

A device rotated from its tabulated zero-angle form transforms as

.. math::

   \boxed{M(\theta+\phi)=R_M(-\theta)M(\phi)R_M(\theta)}.

Jones matrices
--------------

Use :math:`c=\cos\theta`, :math:`s=\sin\theta`.  Overall nonzero complex
scalars are physically irrelevant unless absolute transmission or phase is
being compared.

.. list-table:: Recreated Table 4 — ideal Jones elements
   :header-rows: 1
   :widths: 25 55 20

   * - Device
     - Jones matrix
     - Special cases
   * - Linear polarizer at :math:`\theta`
     - :math:`\begin{bmatrix}c^2&cs\\cs&s^2\end{bmatrix}`
     - :math:`\theta=0`: :math:`\operatorname{diag}(1,0)`;
       :math:`\theta=\pi/2`: :math:`\operatorname{diag}(0,1)`.
   * - Linear retarder, retardance :math:`\delta`, fast axis :math:`\theta`
     - :math:`\begin{bmatrix}
       c^2+s^2e^{-i\delta}&cs(1-e^{-i\delta})\\
       cs(1-e^{-i\delta})&s^2+c^2e^{-i\delta}
       \end{bmatrix}`
     - At :math:`\theta=0`: :math:`\operatorname{diag}(1,e^{-i\delta})`.
   * - Quarter-wave retarder
     - Set :math:`\delta=\pi/2` in the general retarder.
     - Converts suitable linear states to circular states and conversely.
   * - Half-wave retarder
     - :math:`\begin{bmatrix}\cos2\theta&\sin2\theta\\
       \sin2\theta&-\cos2\theta\end{bmatrix}` up to common phase
     - Rotates a linear polarization direction through twice the plate angle.
   * - Rotation of axes through :math:`\theta`
     - :math:`R_J(\theta)=\begin{bmatrix}c&s\\-s&c\end{bmatrix}`
     - Also represents an ideal circular retarder with the associated angle.

The rotation rule is

.. math::

   \boxed{J(\theta+\phi)=R_J(-\theta)J(\phi)R_J(\theta)}.

Jones calculus retains complex field phase but applies only to fully
polarized light.  Mueller calculus propagates measurable Stokes data and also
handles partial or unpolarized states.

.. figure:: /_static/knowledge_base/worked_exercises/introduction_matrix_methods_optics/polarization_matrix_pipeline.svg
   :alt: Parallel Jones and Mueller calculation pipelines through a rotated retarder and polarizer, ending in field or Stokes output.
   :align: center
   :width: 100%

   Jones and Mueller products use the same rightmost-first composition rule,
   but operate on different state spaces.
