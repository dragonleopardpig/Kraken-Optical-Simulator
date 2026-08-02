Chapter 11: Statistical Optics
==============================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 11.

In-text exercises
-----------------

.. rubric:: Exercise 11.1-1 — Coherence-time definitions

Insert each supplied :math:`g(\tau)` in
:math:`T_c=\int|g|^2d\tau`.  Both integrals return the parameter :math:`T_c`.
At :math:`\tau=T_c`, the exponential magnitude has fallen to
:math:`e^{-1/2}` and the Gaussian to :math:`e^{-\pi/2}`.

.. rubric:: Exercise 11.1-2 — Reciprocal equivalent widths

Parseval applied to the Wiener--Khinchin pair gives
:math:`\int|G|^2d\tau=\int|S|^2d\nu`; dividing by :math:`G(0)^2=[\int S]^2`
shows directly that the power-equivalent widths obey
:math:`\boxed{T_c\Delta\nu_c=1}`.

.. rubric:: Exercise 11.1-3 — Mutual-coherence wave equations

Apply the wave operator to either field inside
:math:`G=\langle U^*(\mathbf r_1,t)U(\mathbf r_2,t+\tau)\rangle`; linearity
lets it pass through the average.  This gives the two Wolf equations, one in
:math:`\mathbf r_1,-\tau` and one in :math:`\mathbf r_2,+\tau`.

.. rubric:: Exercise 11.4-1 — Polarized plus unpolarized decomposition

An unpolarized coherency matrix contributes equal diagonal terms and no cross
term; the rank-one polarized matrix supplies the remaining diagonal imbalance
and correlation.  Adding the stated intensities yields :math:`I_x,I_y` and
:math:`|g_{xy}|`; its rank-one weight is exactly the degree of polarization.

End-of-chapter problems
-----------------------

.. rubric:: Problem 11.1-4 — Lorentzian LED spectrum

:math:`\Delta\lambda\simeq\lambda_0^2\Delta\nu/c=
\boxed{1.634\ \mathrm{nm}}`.  A Lorentzian has
:math:`T_c=1/(\pi\Delta\nu)=\boxed{0.3183\ \mathrm{ps}}` and
:math:`l_c=\boxed{95.4\ \mathrm{\mu m}}`.  Since
:math:`|g|=e^{-\pi\Delta\nu|\tau|}`, the half-coherence delay is 0.2206 ps
(path :math:`\boxed{66.1\ \mathrm{\mu m}}`).

.. rubric:: Problem 11.1-5 — Wiener--Khinchin theorem

Expand :math:`|V_T(\nu)|^2` as a double time integral, set
:math:`\tau=t_2-t_1`, divide by :math:`T`, and take the stationary infinite
window limit.  The remaining inner average is :math:`G(\tau)`, giving
:math:`S=\mathcal F\{G\}`.  Integrating over frequency produces
:math:`\delta(\tau)` and hence :math:`\int S\,d\nu=G(0)=I`.

.. rubric:: Problem 11.1-6 — Gaussian mutual intensity

Setting :math:`x_1=x_2=x` gives
:math:`I(x)=I_0e^{-2x^2/W_0^2}`.  Normalization cancels those intensity
envelopes, leaving :math:`\boxed{g=e^{-(x_1-x_2)^2/\rho_c^2}}`.
:math:`I_0,W_0,\rho_c` are peak intensity, beam radius, and transverse
coherence distance.

.. rubric:: Problem 11.1-7 — Position-dependent colour

Intensity is one, :math:`l_c=cT_c=\boxed{300\ \mathrm m}`, and transverse
coherence distance is :math:`\rho_c=1` mm.  The spectrum is centered at
5e14 Hz when :math:`x_1+x_2>0` and 6e14 Hz when negative; only colour is
position dependent.  Film records two uniform half-planes near 600 and 500 nm.

.. rubric:: Problem 11.1-8 — Coherence length estimates

For a narrow band, :math:`\Delta\nu\simeq c\Delta\lambda/\lambda^2`, so
:math:`l_c=c/\Delta\nu\simeq\lambda^2/\Delta\lambda`.  A uniform spectrum from
:math:`\lambda_{min}` to :math:`2\lambda_{min}` spans frequency
:math:`c/(2\lambda_{min})`; inversion gives
:math:`\boxed{l_c=2\lambda_{min}=\lambda_{max}}`.

.. rubric:: Problem 11.1-9 — Spatial coherence from a point source

The path delay is
:math:`\tau=[\sqrt{d^2+x^2}-d]/c`; a Lorentzian therefore gives
:math:`\boxed{|g(x)|=\exp[-|\sqrt{d^2+x^2}-d|/(2cT_c)]}` when :math:`T_c`
uses the book's power-equivalent convention.  It is even, unity at zero, and
falls approximately as :math:`e^{-x^2/(4dcT_c)}` near the axis.

.. rubric:: Problem 11.1-10 — Gaussian coherence area

Applying either spatial wave operator to :math:`G` gives
:math:`(\nabla^2+k_0^2)J=0`.  The Gaussian solution has transverse coherence
radius :math:`W(z)=W_0\sqrt{1+(z/z_0)^2}`; hence coherence area
:math:`\boxed{A_c=\pi W^2(z)}` up to the selected width convention and it
grows with :math:`|z|`.

.. rubric:: Problem 11.2-1 — Sodium interferogram visibility

:math:`V=|g|=e^{-\pi\Delta\nu|\tau|}`.  Setting :math:`V=1/2` gives maximum
optical path difference
:math:`\boxed{c\ln2/(\pi\Delta\nu)=0.1323\ \mathrm{mm}}`.

.. rubric:: Problem 11.2-2 — Observable Young fringes

For every Table 11.1-2 source, divide coherence length by the Young path
change per fringe (one wavelength):
:math:`\boxed{N\simeq l_c/\lambda_0}`.  This gives the requested values
without mixing temporal coherence with the assumed-perfect spatial coherence.

.. rubric:: Problem 11.2-3 — Can correlation shift a spectrum?

:math:`S=S_1+S_2+2\Re S_{12}` and the spectral Cauchy--Schwarz bound is
:math:`|S_{12}(\nu)|\leq\sqrt{S_1S_2}=S_1`.  Correlation can reshape or cancel
parts of the common Gaussian support, but a stationary linear superposition
cannot translate every frequency to create an exact same-width Gaussian at a
new carrier.  A genuine shift requires time variation/nonlinearity (e.g.
Doppler modulation).

.. rubric:: Problem 11.3-1 — Partially coherent Gaussian beam

Double Fourier propagation of the Gaussian mutual intensity remains Gaussian.
Its far-field width is
:math:`\boxed{W^2(z)=W_0^2+(\lambda z/\pi)^2(1/W_0^2+2/\rho_c^2)}` under the
stated :math:`1/e^2` convention.  Smaller coherence distance increases
angular divergence.

.. rubric:: Problem 11.3-2 — Incoherent Fourier illumination

Each source point forms its own shifted Fourier intensity and mutually
incoherent contributions add.  For spatially uniform incoherent illumination,
the result is the convolution of :math:`|F|^2` with the source angular
intensity; in the ideal infinite-uniform limit it is flat.  Unlike coherent
illumination, complex Fourier amplitudes do not add.

.. rubric:: Problem 11.3-3 — Two incoherent points

Van Cittert--Zernike gives the normalized transform of two delta sources:
:math:`\boxed{g(x_1,x_2)=\cos[2\pi a(x_1-x_2)/(\lambda d)]}` up to a common
phase.  Coherence alternates between magnitude one and zero across separation.

.. rubric:: Problem 11.3-4 — Slit-generated coherence

The normalized transform of a uniform slit of width :math:`2a` is
:math:`\boxed{g(x_1,x_2)=\operatorname{sinc}[2a(x_1-x_2)/(\lambda f)]}`
up to quadratic phase; coherence width is inversely proportional to slit width.

.. rubric:: Problem 11.4-2 — Equal-component partial polarization

Here :math:`P=|g_{xy}|`.  The coherency matrix is
:math:`\boxed{J=\tfrac12\begin{bmatrix}1&-jP\\jP&1\end{bmatrix}}` for
:math:`P=0,0.5,1`: respectively unpolarized, mixed, and circularly polarized
light.  An x polarizer transmits :math:`\boxed{I_x=1/2}` in every case.
