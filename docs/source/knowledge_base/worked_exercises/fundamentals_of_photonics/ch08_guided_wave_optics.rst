Chapter 8: Guided-Wave Optics
=============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 8.  These solutions retain the intermediate algebra so that every
boundary condition, mode count, and numerical result can be checked.

Shared notation and conventions
-------------------------------

The phasor convention is :math:`e^{j\omega t}` with guided-wave factor
:math:`e^{-j\beta z}`.  The vacuum quantities are :math:`\lambda_0` and
:math:`k_0=2\pi/\lambda_0`; in a core of index :math:`n_1`,
:math:`\lambda=\lambda_0/n_1`.  The bounce angle :math:`\theta` is measured
from the guide axis, so

.. math::
   :label: fop-ch08-critical-complement

   \bar\theta_c=\cos^{-1}\!\left(\frac{n_2}{n_1}\right),
   \qquad \mathrm{NA}=n_1\sin\bar\theta_c
   =\sqrt{n_1^2-n_2^2}.

For a symmetric slab of full width :math:`d`, define

.. math::
   :label: fop-ch08-normalized-variables

   k_y=n_1k_0\sin\theta,\quad
   \gamma=\sqrt{\beta^2-n_2^2k_0^2},\quad
   u=\frac{k_yd}{2},\quad w=\frac{\gamma d}{2},\quad
   V=\frac{k_0d}{2}\mathrm{NA},\qquad u^2+w^2=V^2.

Here scalar :math:`u` is a dimensionless transverse phase, whereas
:math:`u_m(y)` is the book's normalized mode function,
:math:`\int|u_m(y)|^2dy=1`.

In-text exercises
-----------------

Exercise 8.1-1 — Modal power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  The TE modal field is

.. math::
   :label: fop-exercise-8-1-1-field

   \boldsymbol E_m=\hat{\boldsymbol x}\,a_mu_m(y)e^{-j\beta_mz},
   \qquad \int|u_m(y)|^2dy=1,

where :math:`\beta_m=n(\omega/c_0)\cos\theta_m` and
:math:`\eta=\sqrt{\mu/\epsilon}=\eta_0/n`.  Power is per unit length in the
invariant :math:`x` direction.

.. _fop-exercise-8-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_01_01.svg
   :alt: Illustrated calculation map for Exercise 8.1-1, Modal power
   :align: center
   :width: 95%

   **Figure 56 — Exercise 8.1-1: Modal power.**  The normalized transverse
   field and axial propagation constant determine the integrated Poynting
   flux.

**Step 2 — Mathematical formulas used.**  We use
:ref:`vector-calculus identities <fop-formula-vector-calculus>`,
:ref:`complex phasors <fop-formula-exponentials>`, and
:ref:`integration identities <fop-formula-integration>`.

**Step 3 — Derive the associated magnetic field.**  From
:math:`\nabla\times\boldsymbol E=-j\omega\mu\boldsymbol H`,

.. math::
   :label: fop-exercise-8-1-1-hy

   H_{y,m}=\frac{\beta_m}{\omega\mu}
   a_mu_m(y)e^{-j\beta_mz}.

The sign gives positive axial flux because
:math:`\hat{\boldsymbol x}\times\hat{\boldsymbol y}
=\hat{\boldsymbol z}`.

**Step 4 — Integrate the time-averaged Poynting vector.**

.. math::
   :label: fop-exercise-8-1-1-poynting

   \begin{aligned}
   P_{z,m}
   &=\frac12\operatorname{Re}\int E_{x,m}H_{y,m}^*dy\\
   &=\frac12\frac{\beta_m}{\omega\mu}|a_m|^2
     \int|u_m(y)|^2dy\\
   &=\frac{|a_m|^2}{2}\frac{n/c_0}{\mu}\cos\theta_m.
   \end{aligned}

Since :math:`(n/c_0)/\mu=\sqrt{\epsilon/\mu}=1/\eta`,

.. math::
   :label: fop-exercise-8-1-1-result

   \boxed{P_{z,m}=\frac{|a_m|^2}{2\eta}\cos\theta_m}.

**Step 5 — Check.**  At :math:`\theta_m=0` this is the plane-wave value;
as :math:`\theta_m\to90^\circ`, the axial power tends to zero.  The result
has units :math:`|a_m|^2/\eta=\mathrm W` under the modal normalization.

Exercise 8.1-2 — Multimode power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**

.. math::
   :label: fop-exercise-8-1-2-fields

   E_x=\sum_m a_mu_m(y)e^{-j\beta_mz},\qquad
   H_y=\sum_n\frac{\beta_n}{\omega\mu}
   a_nu_n(y)e^{-j\beta_nz},

and the real mirror-guide modes obey
:math:`\int u_m(y)u_n(y)dy=\delta_{mn}`.

.. _fop-exercise-8-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_01_02.svg
   :alt: Illustrated calculation map for Exercise 8.1-2, Multimode power
   :align: center
   :width: 95%

   **Figure 57 — Exercise 8.1-2: Multimode power.**  Orthogonal modes add in
   field amplitude, while their integrated powers add without cross terms.

**Step 2 — Mathematical formulas used.**  We use
:ref:`integration identities <fop-formula-integration>` and
:ref:`complex phasors <fop-formula-exponentials>`.

**Step 3 — Expand before using orthogonality.**

.. math::
   :label: fop-exercise-8-1-2-double-sum

   \begin{aligned}
   P_z&=\frac12\operatorname{Re}\int E_xH_y^*dy\\
   &=\frac12\operatorname{Re}\sum_m\sum_n
     \frac{\beta_n}{\omega\mu}a_ma_n^*
     e^{-j(\beta_m-\beta_n)z}\int u_m(y)u_n(y)dy.
   \end{aligned}

The Kronecker delta removes every :math:`m\ne n` cross term, and the phase
of each surviving diagonal term is unity:

.. math::
   :label: fop-exercise-8-1-2-diagonal

   P_z=\frac12\sum_m\frac{\beta_m}{\omega\mu}|a_m|^2.

**Step 4 — Substitute the single-mode result.**

.. math::
   :label: fop-exercise-8-1-2-result

   \boxed{P_z=\sum_m\frac{|a_m|^2}{2\eta}\cos\theta_m}.

**Step 5 — Check.**  With only :math:`a_q\ne0`, this reduces to Exercise
8.1-1.  It is independent of :math:`z`, as required in a lossless guide.

Exercise 8.2-1 — Slab confinement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Use the unnormalized symmetric-slab
profile

.. math::
   :label: fop-exercise-8-2-1-profile

   f_m(y)=
   \begin{cases}
   \cos(k_yy),&|y|\le d/2,\ m\ \text{even},\\
   \sin(k_yy),&|y|\le d/2,\ m\ \text{odd},\\
   f_m(d/2)e^{-\gamma(y-d/2)},&y>d/2,
   \end{cases}

with even or odd continuation below.  Normalization cancels from
:math:`\Gamma_m=P_{\rm core}/P_{\rm total}`.

.. _fop-exercise-8-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_02_01.svg
   :alt: Illustrated calculation map for Exercise 8.2-1, Slab confinement
   :align: center
   :width: 95%

   **Figure 58 — Exercise 8.2-1: Slab confinement.**  The harmonic core
   power is compared with both evanescent tails.

**Step 2 — Mathematical formulas used.**  We use
:ref:`integration identities <fop-formula-integration>`,
:ref:`trigonometric identities <fop-formula-trigonometry>`, and
:ref:`exponential identities <fop-formula-exponentials>`.

**Step 3 — Integrate the core.**  Let :math:`\sigma_m=(-1)^m` and
:math:`Q=k_yd`.  The even and odd cases combine as

.. math::
   :label: fop-exercise-8-2-1-core-integral

   I_{\rm core}=\frac d2+\sigma_m\frac{\sin Q}{2k_y}
   =\frac d2\left(1+\sigma_m\frac{\sin Q}{Q}\right),

while the boundary intensity is

.. math::
   :label: fop-exercise-8-2-1-boundary-field

   |f_m(d/2)|^2=\frac{1+\sigma_m\cos Q}{2}.

**Step 4 — Integrate both tails.**

.. math::
   :label: fop-exercise-8-2-1-cladding-integral

   I_{\rm clad}=2|f_m(d/2)|^2\int_0^\infty e^{-2\gamma s}ds
   =\frac{|f_m(d/2)|^2}{\gamma}.

Express the transverse phase and decay only through the requested variables:

.. math::
   :label: fop-exercise-8-2-1-angle-variables

   Q=2\pi\frac d\lambda\sin\theta_m,\qquad
   G=\gamma d=2\pi\frac d\lambda
   \sqrt{\sin^2\bar\theta_c-\sin^2\theta_m}.

Therefore

.. math::
   :label: fop-exercise-8-2-1-result

   \boxed{\Gamma_m=\left[
   1+\frac{1+\sigma_m\cos Q}
   {G(1+\sigma_m\sin Q/Q)}\right]^{-1}},
   \qquad \sigma_m=(-1)^m.

**Step 5 — Check.**  Increasing :math:`m` increases
:math:`\theta_m`, decreases :math:`\gamma`, and increases the tail length
:math:`1/\gamma`, which diverges at cutoff.  Thus the nodeless
:math:`m=0` mode has the greatest confinement.  The limit
:math:`\gamma\to0^+` correctly gives :math:`\Gamma_m\to0` near cutoff.

Exercise 8.2-2 — Asymmetric slab
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  The core, substrate, and cover indices
are :math:`n_1`, :math:`n_2`, and :math:`n_3`, with
:math:`n_3<n_2<n_1`.

.. _fop-exercise-8-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_08_02_02.svg
   :alt: Illustrated calculation map for Exercise 8.2-2, Asymmetric slab
   :align: center
   :width: 95%

   **Figure 59 — Exercise 8.2-2: Asymmetric slab.**  The higher-index
   substrate sets the stricter ray limit; the two boundaries contribute
   unequal reflection phases.

**Step 2 — Mathematical formulas used.**  We use
:ref:`trigonometric identities <fop-formula-trigonometry>` and
:ref:`algebraic rearrangement <fop-formula-algebra>`.

**Step 3 — Part (a): maximum angle and NA.**  Since
:math:`\cos\bar\theta_{cj}=n_j/n_1` and :math:`n_2>n_3`, the substrate has
the smaller complementary critical angle:

.. math::
   :label: fop-exercise-8-2-2-part-a

   \boxed{\theta_{\max}=\cos^{-1}(n_2/n_1)},
   \qquad
   \boxed{\mathrm{NA}=n_1\sin\theta_{\max}
   =\sqrt{n_1^2-n_2^2}}.

**Step 4 — Part (b): self-consistency.**  For TE polarization define

.. math::
   :label: fop-exercise-8-2-2-reflection-phases

   \tan\frac{\phi_{1j}}2
   =\sqrt{\frac{\sin^2\bar\theta_{cj}}{\sin^2\theta}-1},
   \qquad j=2,3.

One round trip contains one reflection at each boundary, so

.. math::
   :label: fop-exercise-8-2-2-result

   \boxed{2k_yd-\phi_{12}-\phi_{13}=2\pi m},
   \qquad k_y=\frac{2\pi}{\lambda}\sin\theta.

When :math:`n_3=n_2`, the two phases become equal and the symmetric-slab
condition is recovered.

**Step 5 — Part (c): many-mode limit.**  Reflection phase changes shift the
endpoints only by order unity.  With approximate spacing
:math:`\Delta(\sin\theta)=\lambda/(2d)`,

.. math::
   :label: fop-exercise-8-2-2-mode-count

   \boxed{M\simeq\frac{2d}{\lambda}\sin\theta_{\max}
   =\frac{2d}{\lambda_0}\sqrt{n_1^2-n_2^2}},\qquad M\gg1.

The cover still changes individual propagation constants, but the
higher-index substrate controls the leading mode count.

**Check.**  Setting :math:`n_3=n_2` recovers both the symmetric phase
condition and its symmetric large-mode count.

End-of-chapter problems
-----------------------

Problem 8.1-3 — Mirror-guide field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The perfect mirrors are at
:math:`y=\pm d/2`; both boundary values must vanish for every :math:`z`.

**Mathematical formulas used.**  We use
:ref:`complex-exponential identities <fop-formula-exponentials>` and
:ref:`algebraic rearrangement <fop-formula-algebra>`.

**Worked derivation.**

**Part (a): test one plane wave.**  At the upper mirror,

.. math::
   :label: fop-problem-8-1-3-single-boundary

   E_x(d/2,z)=Ae^{-jk_yd/2}e^{-j\beta z}=0.

The exponentials never vanish, so :math:`A=0`.  A nonzero single traveling
wave cannot form nodes at both mirrors.

**Part (b): impose both boundaries on two waves.**  Set
:math:`k_{y1}=q`, :math:`k_{y2}=-q`, and
:math:`\beta_1=\beta_2=\beta`.  Using
:ref:`complex-exponential identities <fop-formula-exponentials>`,

.. math::
   :label: fop-problem-8-1-3-two-wave-field

   E_x=e^{-j\beta z}\left(A_1e^{-jqy}+A_2e^{jqy}\right).

The equations at :math:`y=+d/2` and :math:`y=-d/2` are

.. math::
   :label: fop-problem-8-1-3-boundary-system

   A_1e^{-jqd/2}+A_2e^{jqd/2}=0,\qquad
   A_1e^{jqd/2}+A_2e^{-jqd/2}=0.

A nonzero solution requires the determinant to vanish:

.. math::
   :label: fop-problem-8-1-3-determinant

   e^{-jqd}-e^{jqd}=-2j\sin(qd)=0
   \quad\Longrightarrow\quad
   \boxed{q=k_y=\frac{m\pi}{d}},\quad m=1,2,\ldots.

The first boundary equation then fixes the relative sign:

.. math::
   :label: fop-problem-8-1-3-result

   \boxed{\frac{A_2}{A_1}=-e^{-jqd}=(-1)^{m+1}}.

Odd :math:`m` therefore gives :math:`A_2=A_1` and a cosine mode; even
:math:`m` gives :math:`A_2=-A_1` and a sine mode.

.. note::

   The printed problem says the sum “does not satisfy” the boundaries under
   these conditions.  Direct substitution shows that an arbitrary
   :math:`\pm` sign fails, but the parity-matched sign above satisfies both
   mirrors.  This appears to be a wording error in the printed question.

**Check.**  :math:`\cos(m\pi y/d)` vanishes at both mirrors for odd
:math:`m`, while :math:`\sin(m\pi y/d)` vanishes there for even :math:`m`.

Problem 8.1-4 — Mirror-guide dispersion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  :math:`\lambda_0=0.633\ \mu\mathrm m`,
:math:`d=10\ \mu\mathrm m`, and :math:`n=1`, hence
:math:`\lambda=\lambda_0/n=0.633\ \mu\mathrm m`.

**Mathematical formulas used.**  We use the
:ref:`chain rule <fop-formula-product-chain>` and
:ref:`algebraic and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**

**Mode count.**  The guide permits :math:`m=1,\ldots,M` with
:math:`m\lambda/(2d)<1`.  Thus

.. math::
   :label: fop-problem-8-1-4-count

   \frac{2d}{\lambda}=\frac{20}{0.633}=31.5956
   \quad\Longrightarrow\quad
   \boxed{M_{\rm TE}=31,\qquad M_{\rm TM}=31}.

There are 62 polarization-resolved modes.  The book's mirror-guide sequence
starts at :math:`m=1`, not at a TEM :math:`m=0` endpoint.

**Derive the group velocity.**  With nondispersive :math:`n`,

.. math::
   :label: fop-problem-8-1-4-dispersion

   \beta_m^2=\left(\frac{n\omega}{c_0}\right)^2
             -\left(\frac{m\pi}{d}\right)^2.

Differentiate using the :ref:`chain rule <fop-formula-product-chain>`:

.. math::
   :label: fop-problem-8-1-4-group-velocity

   v_{g,m}=\left(\frac{d\beta_m}{d\omega}\right)^{-1}
   =\frac{c_0}{n}\sqrt{1-\left(\frac{m\lambda}{2d}\right)^2}.

The fastest and slowest modes are :math:`m=1` and :math:`m=31`:

.. math::
   :label: fop-problem-8-1-4-velocities

   \begin{aligned}
   v_{g,1}&=c_0\sqrt{1-(0.633/20)^2}
      =\boxed{2.99642\times10^8\ \mathrm{m\,s^{-1}}},\\
   v_{g,31}&=c_0\sqrt{1-(31\times0.633/20)^2}
      =\boxed{5.79342\times10^7\ \mathrm{m\,s^{-1}}}.
   \end{aligned}

**Pulse spread over 1 m.**

.. math::
   :label: fop-problem-8-1-4-result

   \begin{aligned}
   \Delta t
   &=L\left(\frac1{v_{g,31}}-\frac1{v_{g,1}}\right)\\
   &=1.726096\times10^{-8}-3.337313\times10^{-9}\ \mathrm s\\
   &=\boxed{13.924\ \mathrm{ns}}.
   \end{aligned}

The high-order zigzag ray follows the longer path, so the positive delay is
also the expected physical sign.

**Check.**  Both velocities lie between zero and :math:`c_0`, and direct
substitution of them in :math:`L/v_g` reproduces the stated delay.

Problem 8.2-3 — Film in index-1.4 cladding
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  :math:`\lambda_0=0.87\ \mu\mathrm m`,
:math:`d=2.00\ \mu\mathrm m`, :math:`n_1=1.60`, and :math:`n_2=1.40`.

**Mathematical formulas used.**  We use
:ref:`trigonometric identities <fop-formula-trigonometry>`, the
:ref:`chain rule <fop-formula-product-chain>`, and
:ref:`algebraic rearrangement <fop-formula-algebra>`.

**Worked derivation.**

**Part (a): angles and aperture.**

.. math::
   :label: fop-problem-8-2-3-part-a

   \begin{aligned}
   \theta_c&=\sin^{-1}(1.4/1.6)=\boxed{61.045^\circ},\\
   \bar\theta_c&=90^\circ-\theta_c=\boxed{28.955^\circ},\\
   \mathrm{NA}&=\sqrt{1.6^2-1.4^2}=\boxed{0.774597}.
   \end{aligned}

At an air entrance face, Snell's law gives
:math:`\sin\theta_{a,\max}=\mathrm{NA}`, hence

.. math::
   :label: fop-problem-8-2-3-acceptance

   \boxed{\theta_{a,\max}=\sin^{-1}(0.774597)=50.768^\circ}.

**Part (b): TE mode count.**  The chapter uses the smallest integer greater
than :math:`2d\,\mathrm{NA}/\lambda_0`:

.. math::
   :label: fop-problem-8-2-3-count

   \frac{2d\,\mathrm{NA}}{\lambda_0}=3.56136
   \quad\Longrightarrow\quad \boxed{M_{\rm TE}=4}.

**Part (c): TE0 eigenvalue and angle.**

.. math::
   :label: fop-problem-8-2-3-root

   V=\frac{\pi d}{\lambda_0}\mathrm{NA}=5.594177,\qquad
   u\tan u=\sqrt{V^2-u^2}.

Solving on :math:`0<u<\pi/2` gives
:math:`u=1.3306338`, :math:`w=5.4336208`, and

.. math::
   :label: fop-problem-8-2-3-angle

   \boxed{\theta_0=\sin^{-1}\!\left(
   \frac{u\lambda_0}{\pi n_1d}\right)=6.61249^\circ}.

**Group velocity including waveguide dispersion.**  Let
:math:`F(u,V)=u\tan u-\sqrt{V^2-u^2}=0`.  Implicit differentiation gives

.. math::
   :label: fop-problem-8-2-3-du-dv

   \frac{du}{dV}=
   \frac{V/w}{\tan u+u\sec^2u+u/w}=0.0369715.

Using :math:`\beta=[n_1^2k_0^2-(2u/d)^2]^{1/2}` and
:math:`du/dk_0=(d\,\mathrm{NA}/2)(du/dV)`, the
:ref:`chain rule <fop-formula-product-chain>` gives

.. math::
   :label: fop-problem-8-2-3-beta-derivative

   \frac{d\beta}{dk_0}=
   \frac{n_1^2k_0-(2u\,\mathrm{NA}/d)(du/dV)}{\beta}.

Since :math:`\omega=c_0k_0`,

.. math::
   :label: fop-problem-8-2-3-result

   \boxed{v_g=\frac{c_0}{d\beta/dk_0}
   =1.86508\times10^8\ \mathrm{m\,s^{-1}}}.

The simpler ray estimate :math:`(c_0/n_1)\cos\theta_0
=1.86124\times10^8\ \mathrm{m/s}` differs by 0.21%; the exact derivative
includes the frequency-dependent reflection-phase delay.

**Check.**  The root obeys :math:`u\tan u=w` to the shown precision and
:math:`\theta_0<\bar\theta_c`.  The exact group velocity is close to the
ray estimate and may lie slightly below :math:`c_0/n_1`, as expected from
the chapter's waveguide-dispersion curve.

Problem 8.2-4 — Film suspended in air
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Keep the preceding
:math:`\lambda_0,d,n_1`, but set :math:`n_2=1`.

**Mathematical formulas used.**  We use
:ref:`trigonometric identities <fop-formula-trigonometry>`, the implicit
:ref:`chain rule <fop-formula-product-chain>`, and
:ref:`algebraic rearrangement <fop-formula-algebra>`.

**Worked derivation.**

**Part (a).**

.. math::
   :label: fop-problem-8-2-4-part-a

   \theta_c=\boxed{38.682^\circ},\qquad
   \bar\theta_c=\boxed{51.318^\circ},\qquad
   \mathrm{NA}=\boxed{1.24900}.

The formal entrance relation :math:`\sin\theta_a=1.249>1` means the guide
accepts the entire propagating angular range available in air:
:math:`\boxed{\theta_{a,\max}=90^\circ}` in the ideal end-face model.

**Part (b).**

.. math::
   :label: fop-problem-8-2-4-count

   \frac{2d\,\mathrm{NA}}{\lambda_0}=5.74253
   \quad\Longrightarrow\quad \boxed{M_{\rm TE}=6}.

**Part (c).**  The even-mode equation gives

.. math::
   :label: fop-problem-8-2-4-root

   V=9.020340,\qquad u=1.4134518,\qquad w=8.9089107,\qquad
   \boxed{\theta_0=7.02606^\circ}.

Repeating :eq:`fop-problem-8-2-3-du-dv`--
:eq:`fop-problem-8-2-3-beta-derivative` with
:math:`du/dV=0.0158137` yields

.. math::
   :label: fop-problem-8-2-4-result

   \boxed{v_g=1.86244\times10^8\ \mathrm{m\,s^{-1}}}.

The ray estimate is :math:`1.85963\times10^8\ \mathrm{m/s}`.  Relative to
Problem 8.2-3, air cladding increases the mode count from 4 to 6 and raises
the TE0 confinement from 99.12% to 99.75%, while changing its angle and
group velocity only slightly.

**Check.**  The lower cladding index increases NA and therefore cannot
decrease the mode count; all calculated angles remain within the TIR limit.

Problem 8.2-5 — TE0 field and confinement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  :math:`n_1=1.48`, :math:`n_2=1.46`,
:math:`d=0.500\ \mu\mathrm m`, and
:math:`\lambda_0=0.850\ \mu\mathrm m`.

**Mathematical formulas used.**  We use
:ref:`integration identities <fop-formula-integration>`,
:ref:`exponential identities <fop-formula-exponentials>`, and
:ref:`trigonometric identities <fop-formula-trigonometry>`.

**Worked derivation.**

**Ratio of proportionality constants.**  Matching the book's
:math:`A\cos(k_yy+\varphi)` core field to :math:`Be^{-\gamma y}` at
:math:`y=d/2` gives

.. math::
   :label: fop-problem-8-2-5-ratio-general

   A\cos(k_yd/2+\varphi)=Be^{-\gamma d/2}
   \quad\Longrightarrow\quad
   \boxed{\frac BA=e^{\gamma d/2}\cos(k_yd/2+\varphi)}.

For even TE0, :math:`\varphi=0`, so :math:`B/A=e^w\cos u`.

**Solve the eigenvalue.**

.. math::
   :label: fop-problem-8-2-5-root

   \mathrm{NA}=0.242487,\quad V=0.448115,\quad
   u\tan u=\sqrt{V^2-u^2}
   \Longrightarrow u=0.4108277,\ w=0.1789630.

Thus :math:`k_y=1.643311\ \mu\mathrm m^{-1}`,
:math:`\gamma=0.715852\ \mu\mathrm m^{-1}`, and
:math:`B/A=1.096460`.  A continuous normalized profile is

.. math::
   :label: fop-problem-8-2-5-normalized-profile

   u_0(y)=N\begin{cases}
   \cos(k_yy),&|y|\le d/2,\\
   \cos u\,e^{-\gamma(|y|-d/2)},&|y|>d/2.
   \end{cases}

Using :ref:`integration identities <fop-formula-integration>`,

.. math::
   :label: fop-problem-8-2-5-normalization

   \begin{aligned}
   N^{-2}&=\left[\frac d2+\frac{\sin(2u)}{2k_y}\right]
            +\frac{\cos^2u}{\gamma}\\
   &=0.4728045+1.1741324=1.6469369\ \mu\mathrm m,
   \end{aligned}

so :math:`\boxed{N=0.779223\ \mu\mathrm m^{-1/2}}`.

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/ch08/problem_08_02_05_te0_field.svg
   :alt: Normalized TE0 field and evanescent cladding tails
   :align: center
   :width: 88%

   **Figure 60 — Problem 8.2-5: normalized TE0 field.**  The shaded core is
   :math:`-0.25\le y\le0.25\ \mu\mathrm m`; field and slope are continuous
   at both interfaces.

**Confinement.**  The factor :math:`N^2` cancels, so

.. math::
   :label: fop-problem-8-2-5-result

   \boxed{\Gamma_0=\frac{0.4728045}{0.4728045+1.1741324}
   =0.287081=28.71\%}.

This is plausible because :math:`V=0.448\ll1` and the intensity decay
length :math:`1/(2\gamma)=0.6985\ \mu\mathrm m` exceeds the core half-width.

**Check.**  Substitution of :math:`N` makes the total field integral unity,
and the core and cladding fractions sum to one.

Problem 8.2-6 — Maxwell derivation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The TE field has one electric-field component;
the media are nonmagnetic and the interfaces are parallel to the guide axis.

**Mathematical formulas used.**  The curl, Helmholtz equation, exponential
derivative, and electromagnetic boundary conditions are used below.

**Worked derivation.**

Let :math:`\boldsymbol E=\hat{\boldsymbol x}u(y)e^{-j\beta z}`.  With the
:math:`e^{j\omega t}` convention and
:ref:`vector-calculus identities <fop-formula-vector-calculus>`,

.. math::
   :label: fop-problem-8-2-6-curl

   \nabla\times\boldsymbol E
   =(0,-j\beta u,-u')e^{-j\beta z}
   =-j\omega\mu\boldsymbol H.

Therefore

.. math::
   :label: fop-problem-8-2-6-h-fields

   \boxed{H_y=\frac{\beta}{\omega\mu}u(y)e^{-j\beta z}},
   \qquad
   \boxed{H_z=-\frac{j}{\omega\mu}u'(y)e^{-j\beta z}}.

The :ref:`constant-coefficient ODE solutions <fop-formula-odes>` applied to
the Helmholtz equation require

.. math::
   :label: fop-problem-8-2-6-dispersion-pieces

   k_y^2+\beta^2=n_1^2k_0^2,\qquad
   -\gamma^2+\beta^2=n_2^2k_0^2.

Subtracting them and multiplying by :math:`d^2/4` verifies
:math:`u^2+w^2=V^2`.

**Apply both boundary conditions.**  Equal permeabilities make continuity
of tangential :math:`E_x,H_z` equivalent to continuity of :math:`u,u'`.
For an even core field at :math:`y=d/2`,

.. math::
   :label: fop-problem-8-2-6-even-boundary

   A\cos(k_yd/2)=Be^{-\gamma d/2},\qquad
   -Ak_y\sin(k_yd/2)=-\gamma Be^{-\gamma d/2}.

Dividing the equations gives

.. math::
   :label: fop-problem-8-2-6-even-eigenvalue

   \boxed{k_y\tan(k_yd/2)=\gamma}
   \quad\Longleftrightarrow\quad \boxed{u\tan u=w}.

For odd :math:`A\sin(k_yy)`, the same operation yields

.. math::
   :label: fop-problem-8-2-6-odd-eigenvalue

   \boxed{-k_y\cot(k_yd/2)=\gamma}
   \quad\Longleftrightarrow\quad \boxed{-u\cot u=w}.

Combine the parity cases and substitute the angle definitions:

.. math::
   :label: fop-problem-8-2-6-unified

   \tan\left(\frac{k_yd}{2}-\frac{m\pi}{2}\right)=\frac{\gamma}{k_y},
   \qquad
   \frac{\gamma}{k_y}=\sqrt{
   \frac{\sin^2\bar\theta_c}{\sin^2\theta}-1}.

Because :math:`k_yd/2=\pi(d/\lambda)\sin\theta`, this becomes

.. math::
   :label: fop-problem-8-2-6-result

   \boxed{\tan\left(\pi\frac d\lambda\sin\theta_m-\frac{m\pi}{2}\right)
   =\sqrt{\frac{\sin^2\bar\theta_c}{\sin^2\theta_m}-1}},

which is Eq. (8.2-4).  Derivative continuity is the step that turns a merely
continuous trial field into a permitted eigenmode.

**Check.**  Either parity profile recovers the two regional dispersion
relations, and both tangential field components are continuous.

Problem 8.2-7 — Single-mode thickness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The guide is symmetric and material dispersion
is not included.

**Mathematical formulas used.**  The mode-count inequality and algebraic
rearrangement are used below.

**Worked derivation.**

For :math:`n_1=1.50` and :math:`n_2=1.46`,

.. math::
   :label: fop-problem-8-2-7-na

   \mathrm{NA}=\sqrt{1.50^2-1.46^2}=0.344093.

The :math:`m=1` branch reaches cutoff at
:math:`2d\,\mathrm{NA}/\lambda_0=1`.  At equality it is marginal and not
evanescent outside, so the largest thickness retaining only confined TE0 is

.. math::
   :label: fop-problem-8-2-7-thickness

   \boxed{d_{\max}=\frac{1.30}{2(0.344093)}
   =1.88902\ \mu\mathrm m}.

At :math:`\lambda_0'=0.85\ \mu\mathrm m`, keeping this thickness,

.. math::
   :label: fop-problem-8-2-7-result

   \frac{2d_{\max}\mathrm{NA}}{\lambda_0'}
   =\frac{1.30}{0.85}=1.52941
   \quad\Longrightarrow\quad \boxed{M_{\rm TE}=2}.

The inverse-wavelength scaling confirms that the shorter wavelength must
support more modes.

**Check.**  Substitution of the limiting thickness returns the first
higher-order-mode cutoff, with dimensions of length.

Problem 8.2-8 — Cutoff approximation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The index difference is small and the mode is a
higher-order TE mode.

**Mathematical formulas used.**  The cutoff phase condition, difference of
squares, and weak-guidance approximation are used below.

**Worked derivation.**

Let :math:`\Delta n=n_1-n_2` and :math:`m>0`.  At cutoff,
:math:`\gamma\to0`, the reflection phase tends to zero, and
:math:`\theta_m\to\bar\theta_c`.  The phase condition reduces to

.. math::
   :label: fop-problem-8-2-8-cutoff-phase

   \frac{2\pi}{\lambda}(2d\sin\bar\theta_c)=2\pi m
   \quad\Longrightarrow\quad
   \frac{2d}{\lambda_0}\sqrt{n_1^2-n_2^2}=m.

Solving and factoring the difference of squares gives

.. math::
   :label: fop-problem-8-2-8-exact

   \lambda_{0,c}^2
   =\frac{4d^2}{m^2}(n_1-n_2)(n_1+n_2).

For weak guidance :math:`n_2\simeq n_1`, hence
:math:`n_1+n_2\simeq2n_1` and

.. math::
   :label: fop-problem-8-2-8-result

   \boxed{\lambda_{0,c}^2\simeq
   \frac{8n_1\Delta n\,d^2}{m^2}}.

Dimensions are length squared on both sides.  Increasing :math:`d` or index
contrast correctly moves cutoff to a longer wavelength.

**Check.**  Replacing the index sum by twice the core index in the exact
result reproduces the approximation without changing dimensions.

Problem 8.2-9 — TM modes
^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The bounce angle is measured from the guide
axis; the requested plot uses the sine of that angle.

**Mathematical formulas used.**  The TM total-internal-reflection phase,
trigonometric identities, and algebraic rearrangement are used below.

**Worked derivation.**

For total internal reflection of a TM wave,

.. math::
   :label: fop-problem-8-2-9-tm-phase

   \tan\frac{\phi_{\rm TM}}2
   =\frac{n_1^2}{n_2^2}
   \sqrt{\frac{\sin^2\bar\theta_c}{\sin^2\theta}-1}.

Substitute this in :math:`2k_yd-2\phi_{\rm TM}=2\pi m` and take the tangent
of the half-phase equation:

.. math::
   :label: fop-problem-8-2-9-result

   \boxed{\tan\left(\pi\frac d\lambda\sin\theta_m-\frac{m\pi}{2}\right)
   =\frac{n_1^2}{n_2^2}
   \sqrt{\frac{\sin^2\bar\theta_c}{\sin^2\theta_m}-1}}.

The index-squared factor is the difference from TE polarization.  For
:math:`s=\sin\theta`, :math:`s_c=0.3`, and
:math:`\lambda/(2d)=0.1`, one has :math:`d/\lambda=5` and
:math:`n_1^2/n_2^2=1/(1-s_c^2)=1.098901`.  The numerical equation is

.. math::
   :label: fop-problem-8-2-9-numeric-equation

   \tan(5\pi s-m\pi/2)=1.098901\sqrt{0.09/s^2-1}.

.. list-table:: TM branch intersections
   :header-rows: 1
   :widths: 15 28 28 29

   * - :math:`m`
     - :math:`\sin\theta_m`
     - :math:`\theta_m`
     - status
   * - 0
     - 0.0835713
     - :math:`4.79387^\circ`
     - guided
   * - 1
     - 0.165506
     - :math:`9.52662^\circ`
     - guided
   * - 2
     - 0.242842
     - :math:`14.0544^\circ`
     - guided
   * - 3
     - 0.300000
     - :math:`17.4576^\circ`
     - cutoff boundary

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/ch08/problem_08_02_09_tm_modes.svg
   :alt: Graphical solution for the TM slab modes
   :align: center
   :width: 88%

   **Figure 61 — Problem 8.2-9: graphical TM-mode solution.**  Positive
   branches of the left side intersect the reflection-phase curve at the
   listed roots; the fourth point lies exactly at cutoff.

The book's count is the smallest integer strictly greater than
:math:`s_c/[\lambda/(2d)]=3`, so

.. math::
   :label: fop-problem-8-2-9-count

   \boxed{M_{\rm TM}=4}.

Only the first three have :math:`\gamma>0`; :math:`m=3` is marginal at the
specified exact cutoff.  A plot that omits its endpoint will appear to show
only three intersections.

**Check.**  Removing the TM index-squared factor recovers the TE equation;
every listed root is on its proper branch and does not exceed cutoff.

Problem 8.3-1 — Rectangular-guide mode count
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The guide is square, and the requested result
counts only the TE polarization family.

**Mathematical formulas used.**  The area mode-count approximation,
wavelength-frequency relation, and dimensional checks are used below.

**Worked derivation.**

The square area is
:math:`A=d^2=10^{-2}\ \mathrm{mm^2}=10^{-8}\ \mathrm{m^2}`, so
:math:`d=10^{-4}\ \mathrm m`; :math:`\mathrm{NA}=0.1`.  For one
polarization, Eq. (8.3-3) is

.. math::
   :label: fop-problem-8-3-1-start

   M_{\rm TE}\simeq\frac\pi4
   \left(\frac{2d}{\lambda_0}\right)^2\mathrm{NA}^2,
   \qquad \lambda_0=\frac{c_0}{\nu}.

Substitution gives

.. math::
   :label: fop-problem-8-3-1-result

   \boxed{M_{\rm TE}(\nu)=
   \pi A\left(\frac{\mathrm{NA}\,\nu}{c_0}\right)^2
   =(3.49549\times10^{-27}\ \mathrm{Hz^{-2}})\nu^2}.

.. list-table:: Approximate TE mode count
   :header-rows: 1
   :widths: 50 50

   * - :math:`\nu` (THz)
     - :math:`M_{\rm TE}`
   * - 50
     - 8.739
   * - 100
     - 34.955
   * - 200
     - 139.820
   * - 300
     - 314.594
   * - 400
     - 559.279

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/ch08/problem_08_03_01_mode_count.svg
   :alt: Rectangular dielectric guide mode count versus frequency
   :align: center
   :width: 88%

   **Figure 62 — Problem 8.3-1: TE count versus frequency.**  A square guide
   has quadratic growth; the same-width slab comparison is linear.  Exact
   counts would be staircases around these large-mode approximations.

Indeed, :math:`M_{\rm slab}\simeq2d\,\mathrm{NA}\,\nu/c_0`, so

.. math::
   :label: fop-problem-8-3-1-comparison

   M_{\rm rectangular}\simeq\frac\pi4M_{\rm slab}^2.

This is the two-dimensional analogue of Fig. 8.2-4.  The area estimate is
not an exact integer count at small :math:`M`.

**Check.**  The coefficient of frequency squared has inverse-hertz-squared
units, and substitution at 100 THz gives the tabulated value 34.955.

Problem 8.4-1 — Two-slab coupler
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  The identical isolated TE0 fields are normalized
to unity and weakly overlap across the gap, so they are phase matched.

**Mathematical formulas used.**  Field normalization, exponential and
trigonometric integration, and coupled-mode power exchange are used below.

**Worked derivation.**

Each slab has :math:`d=0.500\ \mu\mathrm m`, :math:`n_s=1.48`; the medium
has :math:`n=1.46`; the inner-edge gap is :math:`2a=1.00\ \mu\mathrm m`, so
:math:`a=0.500\ \mu\mathrm m`; and
:math:`\lambda_0=0.850\ \mu\mathrm m`.  Put guide 1 in
:math:`[-a-d,-a]` and guide 2 in :math:`[a,a+d]`.

**Part (a): evaluate Eq. (8.5-6).**  Problem 8.2-5 supplies

.. math::
   :label: fop-problem-8-4-1-mode-data

   u=0.4108277,\ k_y=1.643311\ \mu\mathrm m^{-1},\quad
   \gamma=0.715852\ \mu\mathrm m^{-1},\quad
   \beta=10.816010\ \mu\mathrm m^{-1},\quad
   N=0.779223\ \mu\mathrm m^{-1/2}.

For a guide centered at :math:`y_c`, use

.. math::
   :label: fop-problem-8-4-1-shifted-profile

   U(y-y_c)=N\begin{cases}
   \cos[k_y(y-y_c)],&|y-y_c|\le d/2,\\
   \cos u\,e^{-\gamma(|y-y_c|-d/2)},&|y-y_c|>d/2.
   \end{cases}

Then :math:`u_1(y)=U[y+(a+d/2)]` and
:math:`u_2(y)=U[y-(a+d/2)]`.  For identical guides,

.. math::
   :label: fop-problem-8-4-1-coupling-equation

   \kappa=\frac12(n_s^2-n^2)\frac{k_0^2}{\beta}
   \int_a^{a+d}u_1(y)u_2(y)dy.

Inside guide 2, guide 1 supplies its exponential tail.  With :math:`x=y-a`,

.. math::
   :label: fop-problem-8-4-1-overlap

   \begin{aligned}
   I&=N^2\cos u\,e^{-2\gamma a}
   \int_0^d e^{-\gamma x}\cos[k_y(x-d/2)]dx\\
   &=0.1111544.
   \end{aligned}

Now :math:`k_0=2\pi/0.85=7.391983\ \mu\mathrm m^{-1}` and
:math:`n_s^2-n^2=0.0588000`, so

.. math::
   :label: fop-problem-8-4-1-result-a

   \boxed{\kappa=\tfrac12(0.0588)
   \frac{(7.391983)^2}{10.816010}(0.1111544)
   =0.0165093\ \mu\mathrm m^{-1}
   =1.65093\times10^4\ \mathrm m^{-1}}.

The normalized overlap is dimensionless, leaving the correct inverse-length
unit from :math:`k_0^2/\beta`.

**Part (b): 3-dB length.**  Identical, phase-matched guides obey

.. math::
   :label: fop-problem-8-4-1-power-transfer

   P_1(z)=P_1(0)\cos^2(\kappa z),\qquad
   P_2(z)=P_1(0)\sin^2(\kappa z).

Equal powers require :math:`\kappa L_{3\rm dB}=\pi/4`, hence

.. math::
   :label: fop-problem-8-4-1-result

   \boxed{L_{3\rm dB}=\frac{\pi}{4\kappa}=47.573\ \mu\mathrm m}.

Complete transfer occurs at twice this length,
:math:`L_0=95.146\ \mu\mathrm m`.  Increasing the gap decreases the
overlap as :math:`e^{-2\gamma a}` and must increase both lengths, providing
an independent trend check.

**Check.**  At the 3-dB length both squared trigonometric factors are one
half; at twice that length all power transfers to guide 2.
