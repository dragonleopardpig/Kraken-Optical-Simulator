Chapter 4: Fourier Optics
=========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 4.  Fourier frequency is in cycles per unit length.

In-text exercises
-----------------

.. rubric:: Exercise 4.1-1 — Binary Fresnel plate

Expand the binary radial phase in a Fourier series of its quadratic-phase
coordinate.  Its constant term is an unfocused order; harmonics
:math:`e^{-jqk x^2/(2f)}` are cylindrical-lens phases.  Thus the orders focus
at :math:`\boxed{\infty,\ \pm f,\ \pm f/2,\ldots}`; Fourier coefficients set
their amplitudes.

.. rubric:: Exercise 4.1-2 — Gaussian propagation

Fourier transforming :math:`e^{-\rho^2/W_0^2}`, multiplying by the paraxial
free-space transfer function, and transforming back gives
:math:`U=A_0(q_0/q)e^{-jkz}e^{-jk\rho^2/(2q)}` with
:math:`q=z+j\pi W_0^2/\lambda`.  Convolution with the Fresnel kernel gives the
same Gaussian integral and therefore the Chapter 3 beam.

.. rubric:: Exercise 4.2-1 — Fresnel versus Fraunhofer range

For :math:`a=0.02` m, :math:`b=0.01` m, and
:math:`\lambda=0.5\ \mathrm{\mu m}`, the Fresnel equality estimate is
:math:`d=[(a+b)^4/(4\lambda)]^{1/3}=0.740` m, so use
:math:`\boxed{d\gg0.740\ \mathrm m}`.  Fraunhofer requires both
:math:`a^2/(\lambda d)\ll1` and :math:`b^2/(\lambda d)\ll1`; the stricter is
:math:`\boxed{d\gg800\ \mathrm m}`.

.. rubric:: Exercise 4.2-2 — Inverse transform

The focal-plane relation samples :math:`F(\nu_x,\nu_y)` at
:math:`(x,y)/(\lambda f)`.  Reversing focal-plane coordinates changes the
kernel from :math:`e^{-j2\pi\boldsymbol\nu\cdot\mathbf r}` to
:math:`e^{+j2\pi\boldsymbol\nu\cdot\mathbf r}`, which is exactly the inverse
Fourier transform.

.. rubric:: Exercise 4.3-1 — Rectangular aperture

The transform of :math:`\operatorname{rect}(x/D_x)
\operatorname{rect}(y/D_y)` is
:math:`D_xD_y\operatorname{sinc}(D_x\nu_x)
\operatorname{sinc}(D_y\nu_y)`.  Squaring at
:math:`\nu_{x,y}=(x,y)/(\lambda d)` gives Eq. (4.3-6), with first zeros
:math:`x=\pm\lambda d/D_x`, :math:`y=\pm\lambda d/D_y`.

.. rubric:: Exercise 4.3-2 — Circular aperture

The polar Fourier integral gives
:math:`2J_1(\pi D\rho/\lambda d)/(\pi D\rho/\lambda d)`.  Its first numerator
zero is 3.8317, hence
:math:`\boxed{\rho_s=1.22\lambda d/D}` and
:math:`\boxed{\theta_s=1.22\lambda/D}`.

.. rubric:: Exercise 4.3-3 — Focused spot

Replace propagation distance by focal length in the preceding result:
:math:`\rho_s=1.22\lambda f/D`.  A Gaussian filling a clear diameter near
:math:`D\simeq2W` has :math:`W'_0=\lambda f/(\pi W)\simeq0.637\lambda f/D`;
the differing radius definitions explain the numerical factor.

End-of-chapter problems
-----------------------

.. rubric:: Problem 4.1-3 — Harmonic propagation

Decompose each input into terms :math:`c_m e^{j2\pi(\nu_{xm}x+\nu_{ym}y)}`
and multiply by
:math:`H_m=e^{-j2\pi d\sqrt{\lambda^{-2}-\nu_{xm}^2-\nu_{ym}^2}}`.
This leaves (a) one axial plane wave; (b) one oblique wave with
:math:`(\nu_x,\nu_y)=(-1/2\lambda,-1/2\lambda)`; (c) two waves at
:math:`\nu_x=\pm1/(4\lambda)`; (d) an axial term plus two at
:math:`\nu_y=\pm1/(2\lambda)`; and (e) grating orders
:math:`\nu_x=m/(20\lambda)` weighted by the 50%-duty rectangular-cell
coefficients.

.. rubric:: Problem 4.1-4 — Direction cone

:math:`\sin\theta_{max}=\lambda\nu_{max}=(0.000633)(200)=0.1266`, so
:math:`\boxed{\theta_{max}=7.27^\circ}`.

.. rubric:: Problem 4.1-5 — Logarithmic map

A phase :math:`t=e^{-j2\pi\phi}` deflects by
:math:`\theta=-\lambda\phi'`.  With a lens,
:math:`\phi'=-(\ln x)/(\lambda f)`, hence
:math:`\boxed{\phi=-(x\ln x-x)/(\lambda f)+C}`.  If light instead propagates
distance :math:`f` without the lens, require
:math:`x+f\theta=\ln x`; replace the derivative by
:math:`\phi'=-(\ln x-x)/(\lambda f)` and integrate.

.. rubric:: Problem 4.2-3 — Lens Fourier-transform proof

Expand :math:`(x-x')^2=x^2+x'^2-2xx'` in the Fresnel convolution.  The two
quadratic factors surround the Fourier kernel.  In the propagation--lens--
propagation cascade the lens cancels both inner quadratic phases, leaving
:math:`g(x)=e^{-j2kf}F[x/(\lambda f)]/(j\lambda f)` up to convention phase.

.. rubric:: Problem 4.2-4 — Line-function transforms

(a) :math:`\delta(x-y)` is a bright diagonal in both planes, rotated to its
orthogonal Fourier line.  (b) Two lines at :math:`x=\pm a` transform to
:math:`2\cos(2\pi a\nu_x)`, giving cosine-squared fringes.  (c) Relative phase
:math:`j` changes this to :math:`e^{j2\pi a\nu_x}+j e^{-j2\pi a\nu_x}` and
shifts the fringes by one quarter period.  Use
:math:`x_f=\lambda f\nu_x`; here :math:`\lambda f=1\ \mathrm{mm^2}`.

.. rubric:: Problem 4.2-5 — Fourier-plane scale

:math:`\Delta x=\lambda f(200-20)` lines/mm.  Therefore
:math:`\boxed{f=0.09/[488\times10^{-9}(180\times10^3)]
=1.025\ \mathrm m}`.

.. rubric:: Problem 4.3-4 — Multi-slit grating

The field is
:math:`\sum_{m=-L}^{L}e^{-j2\pi ma\theta/\lambda}` and the intensity is

.. math:: \boxed{I\propto\left[
   \frac{\sin(M\pi a\theta/\lambda)}
   {\sin(\pi a\theta/\lambda)}\right]^2}.

Principal orders occur at :math:`\theta_q\simeq q\lambda/a=q/10`; adjacent
zeros are :math:`1/M` of that separation away.

.. rubric:: Problem 4.3-5 — Oblique Fraunhofer illumination

The aperture field gains :math:`e^{-j2\pi\nu_{0x}x}` with
:math:`\nu_{0x}\simeq\theta_x/\lambda`.  The shift theorem gives
:math:`\boxed{I(x,y)\propto|P(x/\lambda d-\nu_{0x},y/\lambda d)|^2}`: the
entire pattern shifts by :math:`d\theta_x`.

.. rubric:: Problem 4.3-6 — Two-pinhole Fresnel pattern

Adding the two Fresnel kernels cancels their common phase and leaves
:math:`2\cos(2\pi ax/\lambda d)`.  Squaring gives
:math:`\boxed{I=(2/\lambda d)^2\cos^2(2\pi ax/\lambda d)}`.

.. rubric:: Problem 4.3-7 — Fresnel/Fraunhofer relation

Expanding the Fresnel kernel shows that its integral is the Fourier transform
of :math:`p(x',y')e^{-j\pi(x'^2+y'^2)/(\lambda d)}` evaluated at
:math:`(x,y)/(\lambda d)`, times an output quadratic phase.  Its magnitude is
therefore the requested Fraunhofer pattern.

.. rubric:: Problem 4.4-1 — Blurred sinusoidal grating

Convolving :math:`[1+\cos(4\pi x/a)]/2` with a width-:math:`D` square gives
:math:`g(x,0)=D[1+\operatorname{sinc}(2D/a)\cos(4\pi x/a)]/2` (apart from the
constant y factor).  Thus
:math:`\boxed{C=|\operatorname{sinc}(2D/a)|}`.

.. rubric:: Problem 4.4-2 — Phase-edge image

Because :math:`h=\operatorname{rect}(x)\delta(y)`, the output is the running
unit-width average
:math:`g(x,y)=\int_{x-1/2}^{x+1/2}f(u,y)du`.  Far from the phase edge its
magnitude is one; while the window straddles :math:`x=0`, the two constant
phasors add in proportions :math:`1/2\pm x`.  Squaring this piecewise linear
phasor gives the nonuniform transition intensity.

.. rubric:: Problem 4.4-3 — Spatial filtering

With :math:`\lambda f=1\ \mathrm{mm^2}`,
:math:`g=\mathcal F^{-1}\{F(\nu)p(\nu)\}`.  Hence (a)
:math:`g(x,0)=\operatorname{sinc}(x-5)`; (b)
:math:`g(x,0)=\operatorname{tri}(x)`.  A Laplacian filter uses
:math:`\boxed{p(x_f,y_f)=-4\pi^2(x_f^2+y_f^2)/(\lambda f)^2}` within the
available pupil.

.. rubric:: Problem 4.4-4 — Optical cross-correlation

Place :math:`f_1` at the input and
:math:`F_2^*(\nu_x,\nu_y)` in the Fourier plane.  The inverse-transform plane
then contains :math:`f_1\star f_2`.  All masks can be real only when the needed
spectra have zero/constant phase (for example, real even functions); a general
real image still has a complex Fourier transform.

.. rubric:: Problem 4.4-5 — Severe defocus

In the diffraction integral the rapidly varying phase has stationary point
:math:`(x',y')=(x/(\epsilon d_2),y/(\epsilon d_2))`.  Stationary-phase
evaluation makes all slowly varying factors constant there and gives
:math:`\boxed{h(x,y)\propto p(x/(\epsilon d_2),y/(\epsilon d_2))}` up to the
book's normalization and phase, the same geometrical pupil image.

.. rubric:: Problem 4.4-6 — Resolving two points

For a square pupil,
:math:`h\propto\operatorname{sinc}(Dx/\lambda d_2)
\operatorname{sinc}(Dy/\lambda d_2)`.  Two points give
:math:`g=h(x,y)+h(x-b,y)`.  With :math:`\lambda d_2/D=0.1` mm, all three
listed separations (0.5, 1, 2 mm) show two clear peaks.  Solving
:math:`g''(b/2)=0` gives the equal-phase two-peak threshold
:math:`\boxed{b\simeq0.1325\ \mathrm{mm}}`.

.. rubric:: Problem 4.4-7 — Annular pupil

At unit magnification :math:`d_1=d_2=2f=2` m.  The coherent transfer function
is an annulus with spatial-frequency radii
:math:`a/(\lambda d_2)=2.5` and :math:`b/(\lambda d_2)=3.0` lines/mm.  Moving
the image plane to 0.25 m maps the physical pupil by ray scale
:math:`1+d_2(1/d_1-1/f)=0.875`; the impulse response is therefore an annulus
of radii :math:`\boxed{4.375,5.250\ \mathrm{mm}}` (apart from phase and scale).

.. rubric:: Problem 4.5-1 — Spherical-reference holography

Record :math:`|O+R|^2=|O|^2+|R|^2+OR^*+O^*R`, using
:math:`R\propto e^{-jk\rho^2/(2d)}`.  On replay with :math:`R`, the
:math:`OR^*` term reconstructs :math:`O`; the conjugate term creates the
twin image.  A tilted plane object makes an off-axis Fresnel-zone pattern; a
displaced spherical object makes the difference of two quadratic phases and
therefore shifted zone plates whose curvature encodes :math:`d_1^{-1}-d^{-1}`.

.. rubric:: Problem 4.5-2 — Joint-transform correlation

For separated inputs the recorded spectrum contains
:math:`F_1F_2^*e^{-j4\pi a\nu_x}` and its conjugate besides the two
autocorrelation terms.  A second Fourier transform produces separated peaks
:math:`f_1\star f_2` and :math:`f_2\star f_1` at :math:`x=\pm2a`; reading
either off-axis term yields the desired cross-correlation without overlap.
