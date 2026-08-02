Chapter 19: Acousto-Optics
===========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 19.

In-text exercises
-----------------

.. rubric:: Exercise 19.2-1 — Modulator parameters

Use the internal optical wavelength :math:`\lambda=\lambda _0/n`,
:math:`\sin\theta_B=\lambda f/(2v_s)`, and :math:`B=v_s\delta\theta/\lambda`
(or :math:`B=v_s/D`).  The two designs give

.. math::

   \boxed{\theta_{B1}=0.1035^\circ,\quad B_1=13.84\ {\rm MHz}},
   \qquad
   \boxed{\theta_{B2}=2.877^\circ,\quad B_2=2.20\ {\rm MHz}}.

.. rubric:: Exercise 19.2-2 — Scanner parameters

Here :math:`N=BT=D B/v_s` and
:math:`\Delta\theta=(\lambda_0/n)B/v_s`.  With :math:`B=20` MHz, fused
quartz therefore needs :math:`\boxed{D=30.0\ \mathrm{mm}}` and scans
:math:`\boxed{1.445\ \mathrm{mrad}=0.0828^\circ}`.  Flint glass needs only
:math:`15.5` mm for the same 100 spots and scans :math:`2.797` mrad; slower
sound gives both a smaller aperture and a larger scan.

.. rubric:: Exercise 19.2-3 — Filter resolving power

Differentiate :math:`\sin\theta=\lambda f/(2v_s)` at fixed angle:
:math:`|\Delta\lambda|/\lambda=|\Delta f|/f`.  A finite interaction time
:math:`T` resolves acoustic frequencies no closer than :math:`1/T`; hence
:math:`\boxed{\lambda/\Delta\lambda=fT}`.

.. rubric:: Exercise 19.3-1 — Transverse strain in a cubic crystal

The shear wave has only :math:`s_{13}=s_{31}=S`.  The impermeability block in
the :math:`x`--:math:`z` plane is
:math:`\bigl[\begin{smallmatrix}n^{-2}&p_{44}S\\p_{44}S&n^{-2}\end{smallmatrix}\bigr]`.
Its eigenvectors are at :math:`\pm45^\circ`, with eigenvalues
:math:`n^{-2}\pm p_{44}S`; the unchanged :math:`y` eigenvalue is
:math:`n^{-2}`.  Thus the crystal is biaxial and, to first order,
:math:`\boxed{n_\pm\simeq n\mp n^3p_{44}S/2,\ n_y=n}`.

End-of-chapter problems
-----------------------

.. rubric:: Problem 19.1-1 — Four periodic structures

A traveling acoustic grating supplies :math:`(\mathbf q,\Omega)`, so the two
Bragg choices have :math:`\mathbf k_r=\mathbf k\pm\mathbf q` and optical
frequency :math:`\omega_r=\omega\pm\Omega`.  A standing acoustic wave is the
sum of both traveling gratings and produces both shifts.  A static sinusoidal
index grating supplies :math:`\pm\mathbf q` but zero frequency, while a static
layered lattice supplies reciprocal vectors :math:`m\mathbf q` and elastic
diffraction orders with no optical frequency shift.

.. rubric:: Problem 19.1-2 — Bragg scattering integral

At exact phase matching the source phase cancels the Green-function phase, so
the far-field amplitude is proportional to source volume :math:`V=AD`.  Dividing
the scattered flux by incident flux gives
:math:`R=\sin^2(\kappa D)` in the coupled-wave solution and
:math:`\boxed{R\simeq(\kappa D)^2}` in the first-Born limit.  With the chapter's
photoelastic perturbation, :math:`\kappa=\pi\Delta n/\lambda`; this is the
small-signal expansion of Eq. (19.1-22).

.. rubric:: Problem 19.1-3 — Raman--Nath width limit

The thin-grating condition is that diffraction separation accumulated across
the sound width remain below one acoustic period.  Using diffraction angle
:math:`\lambda/\Lambda` gives the Klein--Cook parameter
:math:`Q=2\pi\lambda D_s/\Lambda^2`; Raman--Nath operation requires
:math:`Q\lesssim1`, or
:math:`\boxed{D_s\lesssim\Lambda^2/(2\pi\lambda)}` (order-one conventions move
the numerical boundary but not the scaling).

.. rubric:: Problem 19.1-4 — Combined lithium-niobate modulation

:math:`\Lambda=v_s/f=2.467\ \mu\mathrm m` and
:math:`\lambda=633/2.3=275.2` nm, so
:math:`\boxed{\theta_B=3.198^\circ}`.  Electro-optic phase modulation produces
carrier-centered sidebands :math:`\omega+m\Omega`; reflection translates every
one by :math:`\pm\Omega`.  For a short microwave pulse the electro-optic
sidebands appear immediately, whereas the delayed acoustic packet contributes
only after its sound transit time through the illuminated region.

.. rubric:: Problem 19.2-4 — Producing sinusoidal amplitude modulation

Split the input equally and send the branches to oppositely oriented Bragg
cells.  Their first orders are :math:`(A/2)e^{j(\omega+\Omega)t}` and
:math:`(A/2)e^{j(\omega-\Omega)t}`.  Recombine them in phase:
:math:`\boxed{U_o=A\cos(\Omega t)e^{j\omega t}}`.

.. rubric:: Problem 19.2-5 — Deflection without frequency translation

Cascade two equal Bragg cells with acoustic wavevectors chosen so both
deflections add, but drive one on its upshift order and the other on its
downshift order.  The net wavevector changes by the desired two grating
momenta while :math:`(+\Omega)+(-\Omega)=0`; spatially filter the selected
first-order path after each cell.

.. rubric:: Problem 19.3-2 — Front Bragg diffraction

The incident extraordinary and reflected ordinary waves obey
:math:`q=k_o+k_e`; hence
:math:`\boxed{\Lambda=\lambda_0/(n_o+n_e)}` and the reflected wave is polarized
ordinary, perpendicular to the optic-axis plane.  With the stated indexes and
:math:`\lambda_0=633` nm,
:math:`\boxed{\Lambda=141.1\ \mathrm{nm}}`.
