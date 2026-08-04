.. _krakenos-map-boreman-mtf:

Modulation Transfer Function
============================

This map uses Glenn D. Boreman, *Modulation Transfer Function in Optical and
Electro-Optical Systems*, second edition (2021).  KrakenOS has three distinct
connections to the book: diffraction MTF from a modelled wavefront,
slanted-edge MTF from a captured image, and USAF bar-target MTF from selected
regions of an image.

Coverage by chapter
-------------------

.. list-table:: Boreman-to-KrakenOS coverage
   :header-rows: 1
   :widths: 18 14 68

   * - Book section
     - Match
     - KrakenOS implementation
   * - Ch. 1, MTF of optical systems
     - **Direct/partial**
     - ``PSFCalc.py`` computes a sampled diffraction PSF, OTF magnitude, and
       tangential/sagittal cuts.  PTF is discarded by the public MTF result.
   * - Ch. 2, electro-optical systems
     - **Related/not modelled**
     - Pixel pitch converts measured frequency to lp/mm, but detector-footprint,
       sampling, crosstalk, electronics, noise, and alias correction are not a
       general cascaded sensor model.
   * - Ch. 3, PSF/LSF/ESF measurements
     - **Direct for slanted edge**
     - ``EdgeMTF.measure_slanted_edge_mtf`` estimates edge position, builds an
       oversampled ESF, differentiates it, windows the LSF, and FFTs it.
   * - Ch. 4, square-wave and bar targets
     - **Direct/partial**
     - ``USAFMTF.py`` fits the fundamental plus odd harmonics and converts the
       fundamental square-wave modulation to MTF.
   * - Ch. 5, random/noise targets
     - **Not modelled**
     - No noise-target MTF estimator was found.
   * - Ch. 6, measurement and cascade properties
     - **Partial/related**
     - CSV/plots and several validators support measurement workflows; there is
       no general component-MTF cascade or coherence-aware instrument model.
   * - Ch. 7, environmental MTF
     - **Partial/related**
     - Atmospheric modules calculate refraction/seeing-related quantities, but
       motion, vibration, aerosol, and turbulence MTF are not combined into a
       Boreman-style cascade.

Linear systems: Eqs. (1.1), (1.7), and (1.10)--(1.11)
----------------------------------------------------------------

Section 1.2, Eq. (1.1), printed p. 3, writes a shift-invariant image as the
object convolved with the impulse response:

.. math::

   g(x,y)=f(x,y)*h(x,y).

Fourier transformation gives Eq. (1.7),

.. math::

   G(\xi,\eta)=F(\xi,\eta)H(\xi,\eta),

and Sec. 1.3, Eqs. (1.10)--(1.11), separates the optical transfer function:

.. math::

   \operatorname{OTF}=H=|H|e^{-j\Phi},\qquad
   \operatorname{MTF}=|H|,\qquad
   \operatorname{PTF}=\Phi.

``PSFCalc.calculate_mtf`` normalizes its sampled PSF, applies a two-dimensional
FFT, takes the absolute value, and normalizes the DC peak.  This is a **direct
discrete** implementation of the MTF part.  Because the absolute value is
taken, it does not return the phase transfer function.

Diffraction PSF and MTF: Chapters 1 and 3
-----------------------------------------

``PSFCalc.psf4mtf`` builds a circular complex pupil from fitted wavefront error
:math:`W` in waves,

.. math::

   U(x,y)=P(x,y)e^{-j2\pi W(x,y)},\qquad
   \mathrm{PSF}=|\mathcal F\{U\}|^2.

``calculate_mtf`` then applies the preceding OTF equation to that intensity
PSF.  GPU-backed array operations use CuPy when available and NumPy otherwise.
The FFT normalization and sampling are implementation choices; spatial
frequency calibration still depends on wavelength, pupil diameter, focal
length, array size, and pupil sampling.

This calculation assumes a monochromatic scalar pupil unless the caller
combines wavelengths separately.  It is not the MTF of detector integration,
sampling, electronics, motion, or atmosphere.

Detector footprint: Eq. (2.2)
------------------------------

Section 2.1, Eq. (2.2), printed p. 41, gives the one-dimensional footprint MTF
of a rectangular pixel of width :math:`w`:

.. math::

   \operatorname{MTF}_{\rm footprint}(\xi)
   =|\operatorname{sinc}(\xi w)|
   =\left|\frac{\sin(\pi\xi w)}{\pi\xi w}\right|.

KrakenOS accepts pixel pitch when reporting measured slanted-edge or USAF
frequency in line pairs per millimetre, but it does not automatically multiply
the modeled optical MTF by this footprint term.  Pitch and photosensitive
width are also not generally the same.  Apply Eq. (2.2) externally only after
the actual fill factor and direction are known.

Slanted edge: Eqs. (3.13), (3.15), and (3.16)
--------------------------------------------------------

Section 3.3, Eq. (3.13), printed p. 71, relates the edge- and line-spread
functions:

.. math::

   \operatorname{ESF}(x)=\int_{-\infty}^{x}
      \operatorname{LSF}(x')\,dx'.

Equations (3.15)--(3.16), printed p. 72, invert the integral and recover MTF:

.. math::

   \operatorname{LSF}(x)=\frac{d}{dx}\operatorname{ESF}(x),
   \qquad
   \operatorname{MTF}(\xi,0)
   =\left|\mathcal F\left\{\frac{d\operatorname{ESF}}{dx}\right\}\right|.

``EdgeMTF.measure_slanted_edge_mtf`` implements this chain:

1. Detect the stronger gradient direction and orient the edge by rows.
2. Estimate each row's sub-pixel edge position from the centroid of the
   absolute intensity derivative.
3. Fit a straight edge, project every pixel onto its normal, and bin an
   oversampled ESF.
4. Difference the ESF, apply a Hann window, take the real FFT magnitude, and
   normalize at zero frequency.
5. Return through the native image Nyquist frequency, with optional conversion
   from cycles/pixel to line pairs/mm using pixel pitch.

This is a practical implementation of Sec. 3.8's oversampled knife-edge method.
It is not a full ISO 12233 conformance implementation: derivative correction,
camera nonlinearities, sharpening, edge-angle acceptance, uncertainty, and
instrumental MTF corrections require separate control.

USAF bars: Chapter 4
--------------------

For a 50% duty-cycle square wave, the fundamental modulation is
:math:`4/\pi` times the Michelson contrast.  ``USAFMTF.measure_usaf_element``
fits DC and the first, third, and fifth harmonics together so that crop leakage
from odd harmonics does not corrupt the fundamental.  It then calculates

.. math::

   \operatorname{MTF}(\xi)
   =\frac{\pi}{4}\,
    \frac{M_{\rm image,fundamental}}{C_{\rm target}}.

This directly implements the fundamental square-wave conversion used in the
book, while the simultaneous harmonic fit is a robust numerical detail.  It is
not the complete spectral ratio of every harmonic in an arbitrary bar target.
The result is rejected at/above image Nyquist, and optional magnification and
pixel pitch provide independent expected/measured image-frequency checks.

MTF cascades: Eqs. (1.8)--(1.9) and Section 6.2
------------------------------------------------------------

For independent, linear, shift-invariant, incoherent irradiance subsystems,
the cascade rule is

.. math::

   H_{\rm system}(\xi,\eta)=\prod_i H_i(\xi,\eta).

KrakenOS has no general API that combines optical OTF, detector footprint,
sampling, electronics, motion, vibration, turbulence, and display response.
Multiplying MTF magnitudes also loses phase and can be wrong for coherent,
nonlinear, aliased, sharpening, or spatially varying stages.  Keep the complex
OTFs and state the assumptions when building such a cascade externally.

Which KrakenOS result should I use?
-----------------------------------

* Use ``PSFCalc.calculate_mtf`` to predict scalar diffraction MTF from a
  modeled wavefront.
* Use ``EdgeMTF.measure_slanted_edge_mtf`` for a dense camera MTF curve from a
  captured slanted edge.
* Use ``USAFMTF.analyze_usaf_image`` for discrete checks from identified USAF
  elements and for a human-readable test target.
* Use geometrical spot analysis only for geometrical blur; do not label it an
  MTF without an explicit PSF construction and transform.

Important gaps
--------------

Detector active-area integration, fill factor, sampling/alias ensemble MTF,
crosstalk, electronics, noise-target analysis, motion/vibration MTF,
atmospheric MTF cascades, full PTF reporting, ISO 12233 conformance corrections,
and measurement uncertainty are not a unified KrakenOS capability.
