Chapter 23: Optical Interconnects and Switches
===============================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 23.

In-text exercises
-----------------

.. rubric:: Exercise 23.1-1 — Interconnection capacity

An aperture of width :math:`a` contains :math:`Ba` independent grating
samples in either transverse coordinate, hence :math:`(Ba)^2` independent
space-frequency cells.  Assigning :math:`M` directions to each of :math:`L`
inputs consumes :math:`ML` cells, proving :math:`\boxed{ML\le(Ba)^2}`.  If
every input is connected to every output, the maximum density is therefore
:math:`\boxed{B^2=10^6\ \mathrm{interconnections/mm^2}}` for 1000 lines/mm.

.. rubric:: Exercise 23.1-2 — Separable logarithmic map

Differentiate the proposed phase:

.. math::

   {\partial\phi\over\partial x}={2\pi\over\lambda d}(\ln x-x),\qquad
   {\partial\phi\over\partial y}={2\pi\over\lambda d}(\ln y-y).

Equation (23.1-7) then gives :math:`x'=x+(\lambda d/2\pi)\phi_x=\ln x`
and likewise :math:`y'=\ln y`, which proves the map.

.. rubric:: Exercise 23.4-1 — Bistable nonlinearities

For each candidate plot :math:`y(x)=x/\eta(x)` and locate folds from
:math:`dy/dx=0`; two folds delimit a three-valued output interval.  Working
choices are (a) :math:`a=0.2`, (b) :math:`a=5,\theta=0`, (c)
:math:`\theta=0`, (d) :math:`a=0.5`, and (e) :math:`a=10`.  For example,
case (e) has
:math:`y=x(x+a)^2/(x+1)^2` and its stationary numerator is
:math:`x^2+(3-a)x+a`; at :math:`a=10` the folds are exactly
:math:`\boxed{x=2,5}`.  The same derivative test, rather than visual guesswork,
verifies the other four plots.

End-of-chapter problems
-----------------------

.. rubric:: Problem 23.1-3 — Conformal-map hologram

For a single continuous phase mask, Eq. (23.1-7) would require
:math:`\phi_x\propto\ln r-x` and :math:`\phi_y\propto\tan^{-1}(y/x)-y`.
But

.. math::

   \partial_y(\ln r-x)={y\over r^2},\qquad
   \partial_x[\tan^{-1}(y/x)-y]=-{y\over r^2}.

The mixed derivatives disagree, so :math:`\boxed{\text{no scalar phase
function exists for this map in one thin hologram}}`.  It requires at least a
two-element coordinate transformer (or a segmented/nonlocal implementation);
the curl test is the essential design result.

.. rubric:: Problem 23.2-1 — Four-channel cascaded MZIs

Near :math:`\lambda_0`, :math:`\Delta\nu=c\Delta\lambda/\lambda_0^2=
24.96` GHz.  Adjacent channels must swap ports in the first MZI, so
:math:`\Delta d=c/(2n\Delta\nu)=\boxed{2.612\ \mathrm{mm}}`.  Each second-
stage MZI separates channels spaced by :math:`2\Delta\nu`, so both use
:math:`\boxed{1.306\ \mathrm{mm}}`.

.. rubric:: Problem 23.2-2 — WGR wavelength increment

Adjacent WGR outputs require an optical path increment equal to the channel
spacing: :math:`n\Delta d_b=\Delta\lambda`.  Hence
:math:`\boxed{\Delta d_b=0.2\ \mathrm{nm}/2.3=0.08696\ \mathrm{nm}}` in the
star-coupler material.

.. rubric:: Problem 23.2-3 — Two-by-two wavelength transpose

An :math:`l\to m` path transmits wavelength :math:`\lambda` when
:math:`n\Delta d_{lm}=q_{lm}\lambda` for an integer order, while the rejected
wavelength is not an integer divisor.  Choose
:math:`\Delta d_{11}` resonant for :math:`\lambda_1`,
:math:`\Delta d_{12}` for :math:`\lambda_2`,
:math:`\Delta d_{21}` for :math:`\lambda_3`, and
:math:`\Delta d_{22}` for :math:`\lambda_4`; explicitly
:math:`\boxed{n\Delta d_{11}=q_1\lambda_1,
n\Delta d_{12}=q_2\lambda_2,n\Delta d_{21}=q_3\lambda_3,
n\Delta d_{22}=q_4\lambda_4}`.  Selecting integers that make every unwanted
ratio nonintegral completes the router.

.. rubric:: Problem 23.3-1 — Cascaded-switch loss and crosstalk

The worst route through the five-element 4-by-4 network traverses three
2-by-2 switches, so loss is :math:`\boxed{3(0.5)=1.5\ \mathrm{dB}}`.  Adding
three independent :math:`10^{-3}` leakage powers gives crosstalk
:math:`10\log_{10}(3\times10^{-3})=\boxed{-25.2\ \mathrm{dB}}`; a deliberately
conservative coherent phase alignment would instead bound it at -20.5 dB.

.. rubric:: Problem 23.3-2 — MZI voltage-error crosstalk

The cross state needs :math:`\boxed{V=V_\pi}`.  A 1% error leaves fractional
leakage ratio :math:`\tan^2(0.01\pi/2)=2.468\times10^{-4}`, hence
:math:`\boxed{XT=-36.08\ \mathrm{dB}}`.

.. rubric:: Problem 23.3-3 — TSI with programmable delays

Demultiplex the incoming frame into :math:`N` spatial lanes.  Program lane
:math:`i` with delay :math:`d_i=(\pi(i)-i)\bmod N` slots for the requested
permutation :math:`\pi`; a second bank adds a common frame delay so all values
are causal.  Remultiplex lanes in their fixed order.  This
:math:`\boxed{\text{DEMUX}\to\text{programmable delays}\to\text{MUX}}`
construction absorbs the original fixed-delay/space-switch/fixed-delay stages
into the addressable delay settings.

.. rubric:: Problem 23.4-2 — Threshold optical logic

Sum equal optical inputs and choose a threshold between levels: between one
and two units gives AND, while between zero and one gives OR.  Complement the
threshold device's output (or exchange bright/dark ports) for NAND and NOR.
One scalar threshold cannot implement XOR because its truth set is not
linearly separable; use an OR followed by suppression of the two-input level,
or two threshold stages.  The same sum with threshold :math:`0.5` implements
OR for any :math:`N`.

.. rubric:: Problem 23.4-3 — Kerr-feedback interferometer

The Kerr arm phase is :math:`\Delta\phi=\pi I_o/I_\pi+\phi`, so MZI
interference gives
:math:`\boxed{I_o/I_i=[1+\cos(\pi I_o/I_\pi+\phi)]/2}`.  For :math:`\phi=0`,
write :math:`x=I_o/I_\pi` and
:math:`y=I_i/I_\pi=2x/[1+\cos(\pi x)]`.  Then

.. math::

   {dI_o\over dI_i}=
   \left\{{2\over1+\cos\pi x}+{2\pi x\sin\pi x\over(1+\cos\pi x)^2}\right\}^{-1}.

The ideal differential gain diverges at fold points where the denominator
vanishes; physical loss and finite response time cap that formal maximum.
