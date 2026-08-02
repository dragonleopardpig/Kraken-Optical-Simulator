Chapter 5: Electromagnetic Optics
=================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 5.

In-text exercise
----------------

.. rubric:: Exercise 5.5-1 — Dilute absorbing impurities

The host has :math:`\epsilon_r=n_0^2`; adding dilute susceptibility gives
:math:`\epsilon_r=n_0^2+\chi'+j\chi''`.  Expanding
:math:`\tilde n=\sqrt{\epsilon_r}` to first order gives
:math:`n\simeq n_0+\chi'/(2n_0)` and extinction part
:math:`\kappa\simeq\chi''/(2n_0)`.  Therefore
:math:`\boxed{\alpha=2k_0\kappa=k_0\chi''/n_0}`.

End-of-chapter problems
-----------------------

.. rubric:: Problem 5.1-1 — Gaussian electromagnetic pulse

This is an :math:`x`-polarized Gaussian-envelope carrier traveling in
:math:`+z` at :math:`c_0`.  Maxwell's plane-wave relation gives
:math:`\boxed{\mathbf H=\hat{\mathbf y},f(t-z/c_0)/\eta_0}`; the Poynting
vector points along :math:`+z`.

.. rubric:: Problem 5.2-1 — Constitutive-law classification

(a) The spatial derivative makes the medium linear, homogeneous, temporally
nondispersive but spatially dispersive.  (b) :math:`P+aP^2=\epsilon_0\chi E`
is nonlinear, instantaneous, homogeneous, and local.  (c) time derivatives
make it linear, homogeneous, local, and temporally dispersive.  (d) the
position-dependent coefficient is linear, instantaneous, local, and
inhomogeneous.

.. rubric:: Problem 5.3-1 — Traveling standing wave

The Helmholtz equation requires :math:`2\beta^2=k_0^2`, so
:math:`\boxed{\beta=k_0/\sqrt2}`.  From
:math:`\mathbf H=(j\omega\mu_0)^{-1}\nabla\times\mathbf E`, obtain the
:math:`y` and :math:`z` magnetic components.  Expanding
:math:`\sin\beta y` into exponentials shows two equal TEM waves with
:math:`\mathbf k_\pm=(0,\pm\beta,\beta)`, i.e. at :math:`\pm45^\circ` in the
:math:`y-z` plane.  Their transverse power cancels and mean power flows in
:math:`+z`.

.. rubric:: Problem 5.4-1 — Focused electric-field strength

For uniform area :math:`10^{-8}\ \mathrm{m^2}`, :math:`I=10^8`
:math:`\mathrm{W,m^{-2}}` and
:math:`E_0=\sqrt{2\eta_0I}=\boxed{2.75\times10^5\ \mathrm{V/m}}`.
For the Gaussian, :math:`I(0)=2P/(\pi W_0^2)=6.37\times10^7`
:math:`\mathrm{W,m^{-2}}`, hence
:math:`\boxed{E_0=2.19\times10^5\ \mathrm{V/m}}`.

.. rubric:: Problem 5.5-2 — Modulation in dispersion

Resolve the input into carrier and two sidebands.  After distance :math:`z`,

.. math::

   A_z=e^{j2\pi\nu_0t-j\beta_0z}
   \left[1+\frac m2e^{j2\pi f_mt-j(\beta_2-\beta_0)z}
   +\frac m2e^{-j2\pi f_mt-j(\beta_1-\beta_0)z}\right].

The bracket is purely real apart from a common phase when
:math:`(\beta_2+\beta_1-2\beta_0)z=2\pi q`; at those distances the wave is
again pure AM (with a dispersion-dependent RF phase delay).

.. rubric:: Problem 5.6-1 — Sellmeier dispersion

For :math:`n^2=1+\sum_i A_i\lambda^2/(\lambda^2-\lambda_i^2)`, differentiate
analytically and use
:math:`\boxed{N=n-\lambda,dn/d\lambda}` and
:math:`\boxed{D_\lambda=-(\lambda/c_0)d^2n/d\lambda^2}`.  Evaluating these
expressions with the table coefficients reproduces the silica curves and,
with the three listed GaAs terms, the GaAs curves.  GaAs has much larger
index and stronger, resonance-proximate dispersion; silica has a broad
low-dispersion telecommunications region.

.. rubric:: Problem 5.6-2 — Air dispersion from three measurements

With :math:`\lambda` in micrometres, the exact quadratic through the data is
:math:`n-1=-2.0000\times10^{-5}\lambda^2+2.5400\times10^{-5}\lambda
+2.59448\times10^{-4}`.  Then
:math:`v_g=c_0/[n-\lambda n']`; at 0.76, 0.81, and 0.86 micrometres it is
:math:`2.9971124`, :math:`2.9971077`, and :math:`2.9971027`
:math:`\times10^8\ \mathrm{m/s}`.  The constant curvature gives
:math:`D_\lambda=0.1014`, 0.1081, and 0.1147
:math:`\mathrm{ps/(km,nm)}`, hundreds of times smaller than ordinary silica
fibre dispersion.

.. rubric:: Problem 5.6-3 — Drude phase/group velocities

For the lossless Drude law :math:`k^2=(\omega^2-\omega_p^2)/c_0^2`,
:math:`v_p=\omega/k` and
:math:`v_g=d\omega/dk=c_0^2k/\omega`.  Therefore
:math:`\boxed{v_pv_g=c_0^2}`.
