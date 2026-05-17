Sub-Pixel Hot-Spot Detection in IR Imaging
==========================================

The standard objection — *"you need at least 2-3 pixels to detect a feature
(Nyquist, characterization, robustness against hot/dead pixels)"* — is
sound for visible-light imaging. In IR thermography, the physics is
different enough that a sub-pixel hot spot can dominate a pixel's signal by
orders of magnitude over the sensor noise floor.

This note works through *why*, with a worked example and the physical
limits where the claim breaks.

The mixing model
----------------

A pixel does not measure "a temperature." It integrates in-band spectral
radiance over its instantaneous field of view (IFOV). If a fraction

.. math::

   f = \frac{A_{\text{spot}}}{A_{\text{pixel}}}

of that IFOV is at temperature :math:`T_{\text{hot}}` and the remainder
:math:`(1-f)` is at :math:`T_{\text{bg}}`, the radiance reaching the
detector for that pixel is the area-weighted average:

.. math::

   L_{\text{pixel}} = f\, B(T_{\text{hot}}) \;+\; (1-f)\, B(T_{\text{bg}}).

For an emissivity-corrected blackbody, the in-band radiance :math:`B(T)`
rises very steeply with temperature:

* **LWIR (8-14 µm):** :math:`B(T) \propto T^{4}` to a good approximation
  (Stefan-Boltzmann).
* **MWIR (3-5 µm):** :math:`B(T) \propto T^{8}\!\dots T^{12}`, since the
  band sits up the Wien side of the Planck curve. Hot-spot contrast is
  even sharper.

.. figure:: /_static/knowledge_base/fig1_pixel_mixing.svg
   :alt: A 100 × 100 µm hot spot inside a 1 × 1 mm pixel IFOV
   :align: center
   :width: 90%

   A 100 × 100 µm hot spot occupies just 1 % of a 1 × 1 mm pixel IFOV.
   The pixel's signal is the area-weighted average of the hot region and
   the cool background.

A worked numerical example
--------------------------

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Quantity
     - Value
   * - Pixel IFOV :math:`A_{\text{pixel}}`
     - 1 mm × 1 mm = 1 mm²
   * - Hot spot :math:`A_{\text{spot}}`
     - 100 µm × 100 µm = 0.01 mm²
   * - Area fraction :math:`f`
     - 1 %
   * - Background :math:`T_{\text{bg}}`
     - 25 °C = 298 K
   * - Hot spot :math:`T_{\text{hot}}`
     - 200 °C = 473 K
   * - Band
     - LWIR (:math:`B \propto T^{4}`)

Ratio of emissive powers:

.. math::

   \frac{B(T_{\text{hot}})}{B(T_{\text{bg}})}
   = \left(\frac{473}{298}\right)^{4} \approx 6.34.

Pixel-averaged radiance:

.. math::

   \frac{L_{\text{pixel}}}{B(T_{\text{bg}})}
   = 0.01 \cdot 6.34 + 0.99 = 1.053.

Inverting through :math:`T^{4}` to recover an *apparent* pixel temperature:

.. math::

   T_{\text{app}} = T_{\text{bg}} \cdot (1.053)^{1/4} \approx 301.9~\text{K},
   \qquad \Delta T_{\text{app}} \approx 3.9~\text{K}.

Compare to typical sensor noise floors (NETD, noise-equivalent temperature
difference):

.. list-table::
   :header-rows: 1
   :widths: 65 35

   * - Detector
     - NETD
   * - Cooled MWIR / LWIR (HgCdTe, InSb)
     - ~ 20 mK
   * - Uncooled microbolometer LWIR
     - ~ 30-50 mK

.. note::

   :math:`\mathrm{SNR} \approx \dfrac{3.9~\text{K}}{0.030~\text{K}}
   \approx \mathbf{130}.`
   A 1 % sub-pixel hot spot sits two orders of magnitude above the noise
   floor.

In MWIR, with its higher effective exponent, the same scenario pushes the
apparent :math:`\Delta T` to roughly 8-10 K — easier still.

Why visible-light imaging cannot pull this trick
------------------------------------------------

Reflectance imaging mixes the same way,

.. math::

   I_{\text{pixel}} = f\,\rho_{\text{spot}}\,E + (1-f)\,\rho_{\text{bg}}\,E,

but the gain is **linear** in the albedo difference
:math:`\rho_{\text{spot}}-\rho_{\text{bg}}`, not in any power of it. A 1 %
sub-pixel speck with 50 % reflectance contrast lifts the pixel by 0.5 % —
right at the camera noise floor for an 8-bit sensor (~0.3-1 %).

.. figure:: /_static/knowledge_base/fig2_planck_t4.svg
   :alt: Planck radiance B(T) proportional to T^4
   :align: center
   :width: 90%

   LWIR radiance scales as :math:`T^{4}`. The 175 K rise from background
   to defect more than sextuples the emitted power, so even a 1 % area
   share contributes a measurable pixel-level signal.

The PSF assist
--------------

Even if the defect is physically sub-pixel, the optical point-spread
function (Airy disk plus lens aberrations) spreads its photons over
typically 2-4 pixels with FWHM on the same order as the pixel pitch.
So the sensor response is *not* a single hot pixel but a small
Gaussian-ish blob — easy to distinguish from a stuck-pixel artefact,
which is a delta function and is also present in the dark-reference
frame after non-uniformity correction (NUC).

.. figure:: /_static/knowledge_base/fig3_psf_response.svg
   :alt: Sub-pixel point source spreading into a multi-pixel response blob
   :align: center
   :width: 100%

   Optical blur turns even a sub-pixel point source into a small
   Gaussian-shaped response across several pixels. Stuck or hot pixels,
   in contrast, are delta-shaped and stable across frames — they are
   removed by NUC.

What can break the claim
------------------------

Two assumptions hide in the math; raise them when a vendor over-promises
1-pixel detection.

1. **Emissivity uniformity.** The mixing model assumed
   :math:`\varepsilon_{\text{spot}} \approx \varepsilon_{\text{bg}}`.
   A polished metal flake on oxidized steel can have
   :math:`\varepsilon \sim 0.1` versus :math:`\varepsilon \sim 0.8` —
   the contrast can flip sign or vanish entirely at some viewing angles.
   The radiance at a hot, low-:math:`\varepsilon` surface mostly reflects
   the room behind the camera.

2. **Atmospheric and window transmission.** CO₂, H₂O, and ozone bands
   attenuate selectively across LWIR and especially MWIR. A long
   stand-off distance or a viewport (germanium, ZnSe) cuts effective
   :math:`\Delta T`. Always quote the band, path length, and window.

Bottom line: detection vs. characterization
-------------------------------------------

Both views — *"you need 2-3 pixels"* and *"1 pixel is enough"* — are
correct. They are answering different questions, and the disagreement
evaporates once you separate the two.

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - "2-3 pixels" — *Characterization view*
     - "1 pixel" — *Detection view*
   * - Question it answers:
       *"What does the defect look like?"*
     - Question it answers:
       *"Is there a defect here, yes or no?"*
   * - **Nyquist sampling.** To pin down the spatial frequency of a
       feature without aliasing, you need at least 2 samples per cycle —
       so the feature must span :math:`\ge 2` pixels.
     - **Optics spread the light.** A real lens's PSF blurs even a
       sub-pixel hot spot over 2-4 pixels (FWHM :math:`\ge` 1-2 px). So
       the *defect's footprint* can be 1 pixel even when the sensor's
       *response* covers several.
   * - **Morphology needs room.** To measure size, shape, or orientation,
       you need enough pixels to fit a meaningful pattern — typically a
       :math:`3 \times 3` neighbourhood as a minimum.
     - **IR contrast is exponential, not linear.** Thermal radiance
       scales as :math:`T^{4}` (LWIR) or steeper (MWIR), so a tiny hot
       region with a large :math:`\Delta T` dominates the pixel's signal
       far above NETD.
   * - **Single-pixel anomalies are ambiguous.** Without context, one
       bright pixel could be a real defect, a hot/stuck pixel, or shot
       noise. You can't tell from just the pixel itself.
     - **Sensor artefacts are removed first.** Non-uniformity correction
       (NUC) and reference-frame subtraction strip out hot/dead pixels,
       so a remaining 1-pixel anomaly is a real alarm, not a sensor
       quirk.

.. important::

   **Verdict.** If the speaker is making a *detection* claim — "we alarm
   on hot spots smaller than one pixel" — and it is backed by NUC plus
   PSF reasoning on a near-blackbody surface, **1 pixel is honest.**

   If they are claiming *measurement* at the 1-pixel scale — defect size,
   shape, orientation, classification — **the "2-3 pixels theoretically"
   objection is right**, and Nyquist and morphology are the reasons.

   *A point-source siren you can hear is not the same as a face you can
   recognise.*
