Chapter 20: Electro-Optics
==========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 20.

In-text exercises
-----------------

.. rubric:: Exercise 20.1-1 — Directional-coupler spectral response

Since :math:`V_0(\lambda)=V_0(\lambda_r)\lambda/\lambda_r`, holding
:math:`V=V_0(\lambda_r)` gives coupling phase
:math:`(\pi/2)(\lambda_r/\lambda)`.  Therefore

.. math::

   \boxed{\eta(\lambda)=\cos^2\!\left({\pi\lambda_r\over2\lambda}\right)}.

It has a quadratic null at :math:`\lambda_r`; this expression directly
generates the requested wavelength-detuning plot.

.. rubric:: Exercise 20.2-1 — Longitudinal Kerr modulation

For eigenpolarization :math:`i`,
:math:`n_i(E)\simeq n_i-s_i n_i^3E^2/2`.  With :math:`E=V/L`,

.. math::

   \phi_i=\phi_{i0}-{\pi s_i n_i^3\over\lambda_0 L}V^2,
   \qquad
   \Gamma=\Gamma_0-{\pi(s_xn_x^3-s_yn_y^3)\over\lambda_0L}V^2.

Setting the voltage-induced phase or retardation magnitude to :math:`\pi`
gives :math:`\boxed{V_\pi=\sqrt{\lambda_0L/(|s|n^3)}}`, with :math:`s n^3`
replaced by the eigenpolarization difference for a retarder.

End-of-chapter problems
-----------------------

.. rubric:: Problem 20.1-2 — GaAs phase-modulator speed

For a longitudinal cell,
:math:`V_\pi=\lambda_0/(2rn^3)=\boxed{8.71\ \mathrm{kV}}` and the optical
transit time is :math:`nL/c=\boxed{0.360\ \mathrm{ns}}`.  The parallel-plate
capacitance is :math:`\epsilon A/L=\boxed{0.398\ \mathrm{pF}}`, so the
50-ohm time constant is only :math:`19.9` ps.  Optical transit, not the RC
circuit, is the limiting scale.

.. rubric:: Problem 20.1-3 — Mach--Zehnder sensitivity

Bias at quadrature, where
:math:`\eta=[1+\cos(\pi V/V_\pi)]/2` has maximum slope.  Thus
:math:`\boxed{|d\eta/dV|_{max}=\pi/(2V_\pi)=0.1571\ \mathrm{V^{-1}}}` for
:math:`V_\pi=10` V.

.. rubric:: Problem 20.1-4 — Integrated strain sensor

Put the sensing and reference waveguides in a Mach--Zehnder and bias it at
quadrature.  Strain produces :math:`\Delta\phi_s=k_0L(\partial n/\partial
\epsilon)\epsilon`.  Apply a feedback voltage giving
:math:`\Delta\phi_E=-k_0Ln^3rV/(2d)` and servo the detector back to its null;
then
:math:`\boxed{\epsilon=n^3rV/[2d(\partial n/\partial\epsilon)]}`.  The null
measurement removes source-power drift.

.. rubric:: Problem 20.1-5 — Faraday intensity modulation

Place the rotator between linear polarizers.  If their relative angle is
:math:`\alpha`, Malus' law gives
:math:`\boxed{I_o/I_i=\cos^2[\alpha+V_B B(t)L]}`.  Biasing at 45 degrees makes
small field changes linear in output intensity; crossed polarizers instead
make an on/off switch.

.. rubric:: Problem 20.2-2 — Poled-silica phase shift

For the stated axes and :math:`y` polarization, :math:`r_{13}` applies.
Substitution in :math:`\Delta\phi=-\pi r n^3(V/d)L/\lambda` gives
:math:`\boxed{\Delta\phi=-0.3058\ \mathrm{rad}}` (magnitude 17.5 degrees).

.. rubric:: Problem 20.2-3 — Cascaded KDP cells

The longitudinal KDP geometry uses :math:`r_{63}` and ordinary index, giving
:math:`\boxed{V_\pi=\lambda_0/(r_{63}n_o^3)=16.8\ \mathrm{kV}}` for one
plate.  Rotate alternate plates by 90 degrees about the beam (or reverse their
crystal axes when electrode polarity reverses) so every retardation has the
same sign.  Nine equal stages add phase, so
:math:`\boxed{V_{\pi,9}=V_\pi/9=1.87\ \mathrm{kV}}`.

.. rubric:: Problem 20.2-4 — Push--pull reflective modulator

Each arm makes two passes.  Equal and opposite voltages therefore give
relative phase :math:`\Delta\phi=4\pi V/V_\pi`, where for a transverse cell
:math:`V_\pi=\lambda_0d/(r n^3L)`.  The 3-dB recombiner yields
:math:`\boxed{\eta=\cos^2(\Delta\phi/2)=\cos^2(2\pi V/V_\pi)}` (the other port
has the complementary sine-squared response).

.. rubric:: Problem 20.2-5 — Low-voltage LiNbO3 modulator

Choose extraordinary polarization and field parallel to the optic axis to use
the largest product :math:`r_{33}n_e^3`.  A push--pull Mach--Zehnder has
:math:`V_\pi=\lambda_0d/[2r_{33}n_e^3L]`, hence
:math:`\boxed{V_\pi=6.73\ \mathrm V}` for the specified active region.

.. rubric:: Problem 20.2-6 — Electrically controlled walk-off

Without voltage, use the uniaxial extraordinary-index formula at 45 degrees;
Snell-wavevector continuity gives the ordinary/extraordinary ray directions.
The lateral separation is :math:`d(\tan\rho_e-\tan\rho_o)` and retardation is
:math:`k_0d[n_e(45^\circ)-n_o]`.  A field along the optic axis changes
:math:`n_o` and :math:`n_e` by :math:`-n_o^3r_{13}E/2` and
:math:`-n_e^3r_{33}E/2`; recomputing those two expressions gives the voltage
shift.  The resulting controllable beam separation/retardation supports
polarization switching, sensing, and beam steering.  (At the printed 30 V/m,
the effect is extremely small; 30 V/micrometre would be device-scale.)
