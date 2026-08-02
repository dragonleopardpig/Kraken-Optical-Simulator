Chapter 7: Photonic-Crystal Optics
==================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 7.  The characteristic-matrix convention is the book's.

In-text exercise
----------------

.. rubric:: Exercise 7.1-1 — Quarter-wave antireflection film

Multiplying boundary/propagation matrices makes
:math:`B\propto n_1n_3\sin^2\delta-n_2^2\sin^2\delta` at
:math:`\delta=\pi/2`.  Thus :math:`B=0` and :math:`r=0` when
:math:`\boxed{d=\lambda_0/(4n_2),\ n_2=\sqrt{n_1n_3}}`.

End-of-chapter problems
-----------------------

.. rubric:: Problem 7.1-2 — Slab beamsplitter

Use the Airy result
:math:`T=[1+4R_{s,p}\sin^2\delta/(1-R_{s,p})^2]^{-1}`, :math:`R=1-T`, with
the TE/TM Fresnel :math:`R_{s,p}` at 45 degrees and
:math:`\delta=(2\pi/\lambda_0)nd\cos\theta_t`.  This directly supplies the
periodic spectral curves; TM contrast vanishes when the internal/external
angle is Brewster.

.. rubric:: Problem 7.1-3 — Air-gap tunnelling

At normal incidence insert :math:`n_g,1,n_g` in the slab matrix and
:math:`d=\lambda_0/2`; the round-trip phase gives unity transmission.  Above
critical angle the gap normal wavevector is :math:`j\kappa`; replacing
:math:`\sin\delta,j\cos\delta` by hyperbolic functions gives finite
:math:`T\propto\operatorname{sech}^2(\kappa d)`: frustrated TIR tunnels
through a sufficiently thin gap.

.. rubric:: Problem 7.1-4 — Unmatched incident medium

Composition of the new boundary and old device gives
:math:`\boxed{r=(r_b+r_m)/(1+r_br_m)}`.  It reduces respectively to
:math:`r_m,1,r_b,1` for :math:`r_b=0,1` and :math:`r_m=0,1`.

.. rubric:: Problem 7.1-5 — Oblique quarter-wave coating

Replace admittance by :math:`n\cos\theta` (TE) or
:math:`n/\cos\theta` (TM), and phase by
:math:`\delta=2\pi n_2d\cos\theta_2/\lambda_0`; multiplying the one-film
matrix gives :math:`r=(r_{12}+r_{23}e^{-j2\delta})/
(1+r_{12}r_{23}e^{-j2\delta})`.  Squaring this expression is the requested
angular reflectance.

.. rubric:: Problem 7.1-6 — Quarter/half-wave stacks

At the design wavelength a quarter-wave pair has diagonal matrix
:math:`-\operatorname{diag}(n_2/n_1,n_1/n_2)`; after :math:`N` pairs the
ratio is raised to :math:`N`, yielding
:math:`r=[n_a(n_2/n_1)^{2N}-n_s]/[n_a(n_2/n_1)^{2N}+n_s]` up to layer order.
A half-wave layer is :math:`-I`; every pair is transparent at the design
wavelength apart from phase, so only the unmatched outer boundary remains.

.. rubric:: Problem 7.1-7 — GaAs/AlAs reflector

For a GaAs-matched exterior, evaluate the preceding quarter-wave expression
with :math:`n_1=3.57`, :math:`n_2=2.94`:
:math:`\boxed{R_N=[(1-(n_2/n_1)^{2N})/(1+(n_2/n_1)^{2N})]^2}` and
:math:`T_N=1-R_N`.  Evaluating :math:`N=1,\ldots,10` gives the requested
monotonic plot.

.. rubric:: Problem 7.1-8 — Matrix-program verification

Initialize :math:`M=I`; for each layer multiply
:math:`M_i=\begin{bmatrix}\cos\delta_i&j\sin\delta_i/Y_i\\
jY_i\sin\delta_i&\cos\delta_i\end{bmatrix}`.  Convert total input admittance
to :math:`r` and plot :math:`|r|^2` versus wavelength or angle.  Using the
figure's layer data reproduces its stopband and TE/TM angular splitting.

.. rubric:: Problem 7.2-1 — Gap/midgap estimate

Equal optical thickness gives Bragg frequency
:math:`\boxed{\nu_B=c/[2(n_1d_1+n_2d_2)]}` with
:math:`d_1+d_2=2\ \mathrm{\mu m}`.  The first-order relative gap is
:math:`\Delta\nu/\nu_B\simeq(4/\pi)\sin^{-1}|(n_2-n_1)/(n_2+n_1)|`.
It is large for 1.5/3.5 and small for 3.4/3.6, demonstrating that index
contrast, not mean index, controls the fractional gap.

.. rubric:: Problem 7.2-2 — Off-axis Bloch wave

Keep conserved :math:`k_x`; in every layer replace
:math:`n_i\omega/c` by :math:`k_{zi}=[(n_i\omega/c)^2-k_x^2]^{1/2}` and
admittance by its TE/TM oblique value.  The unit-cell trace then gives
:math:`\boxed{\cos(K\Lambda)=\tfrac12\operatorname{tr}M(k_x,\omega)}`;
:math:`|\operatorname{tr}M/2|>1` is a bandgap.

.. rubric:: Problem 7.2-3 — Propagation normal to periodicity

For :math:`K=0` (wavevector along the layers), tangential phase matching
makes the field sample a translationally uniform direction.  Substitution in
the off-axis dispersion relation leaves real :math:`k_x` for every allowed
frequency; the Bragg coupling term vanishes, so no axial-period bandgap opens.

.. rubric:: Problem 7.2-4 — Omnidirectional reflector

For each conserved air :math:`k_x\leq\omega/c`, evaluate the cell trace with
:math:`n_2=2n_1` and equal optical thickness.  Shade frequencies for which
:math:`|\operatorname{tr}M/2|>1` for every point inside the air light cone;
the intersection of all angular TE/TM stopbands is the omnidirectional range.
This construction, rather than a single normal-incidence gap, is the required
projected dispersion plot.
