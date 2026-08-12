Beam Quality: Specify, Measure, and Interpret
=============================================

Beam quality is not an intrinsic adjective and no scalar contains the complete
amplitude, phase, polarization, and time dependence of a laser beam.  A strong
interview answer first asks what the beam must accomplish, then chooses a metric
that predicts that outcome and a measurement that is traceable to its definition.

Start with declared moments and widths
--------------------------------------

For an irradiance distribution :math:`I(x,y)`, define the centroid and one
second moment by

.. math::
   :label: interview-beam-moments

   \bar{x}=\frac{\iint xI(x,y)\,dx\,dy}{\iint I(x,y)\,dx\,dy},
   \qquad
   \sigma_x^2=
   \frac{\iint (x-\bar{x})^2I(x,y)\,dx\,dy}{\iint I(x,y)\,dx\,dy}.

The ISO-style second-moment diameter is :math:`d_{\sigma x}=4\sigma_x`.
For an ideal circular Gaussian this equals its :math:`1/e^2` intensity diameter,
but a best-fit Gaussian width, a cutoff width, FWHM, encircled-power diameter,
and second-moment width generally differ for a non-Gaussian beam.

With consistent second-moment radii, the beam-parameter product is

.. math::
   :label: interview-beam-parameter-product

   \operatorname{BPP}_x=w_{0x}\theta_x
   =M_x^2\frac{\lambda}{\pi}.

:math:`M^2` describes propagation/focusability relative to an ideal Gaussian; it
does not uniquely reveal mode content, halo power, focus shape, pointing jitter,
polarization, or temporal behavior.  Report both axes and their waist positions
when the beam is elliptical or astigmatic.

Choose the metric from the task
-------------------------------

.. list-table:: What common beam metrics actually answer
   :header-rows: 1
   :widths: 20 31 29 20

   * - Metric
     - Useful question
     - Required definition/control
     - Important blind spot
   * - :math:`M_x^2,M_y^2`
     - How does the second-moment caustic propagate and focus?
     - Wavelength, second moments, axes, sampling, fit, and uncertainty
     - Target-bucket distribution and short-term jitter
   * - Power in the bucket
     - What fraction reaches a declared target radius or aperture?
     - Bucket plane, center rule, radius, total-power denominator, and time gate
     - Propagation outside the measured plane
   * - Strehl ratio
     - How much is peak focal irradiance reduced relative to a defined ideal beam?
     - Equal-power reference field, pupil/focus, sampling, and aberration state
     - Energy in wings and temporal stability
   * - Wavefront error
     - What phase error should be corrected or allocated?
     - Reference wave, aperture, wavelength, weighting, and removed terms
     - Amplitude nonuniformity
   * - Brightness/radiance
     - How much power occupies the available area-angle phase space?
     - Area, solid angle, polarization, axes, and averaging convention
     - Detailed spot structure
   * - Encircled/central-lobe power
     - How much useful energy lies in the desired core?
     - Center, core boundary, reference, and detector dynamic range
     - Wavefront cause and downstream evolution

An application specification may need several metrics.  For example, a precision
materials process can require :math:`M^2` for delivery design, power-in-bucket for
process effectiveness, ellipticity for scan uniformity, and pointing stability
over a stated bandwidth and warm-up interval.

Traceable :math:`M^2` measurement workflow
------------------------------------------

1. Define wavelength, power/pulse state, polarization, axes, second-moment width,
   temporal averaging, and the applicable measurement standard/version.
2. Sample the beam without clipping or altering its wavefront.  Confirm that
   pickoffs, wedges, attenuation, and focusing optics behave linearly at the
   actual wavelength and exposure.
3. Choose detector pixels and active area that resolve the waist and capture the
   wings at every plane.  Establish spatial calibration and detector linearity.
4. Acquire dark/background frames and prevent saturation.  Use a declared data
   window or noise-equivalent aperture large enough for the beam but not so large
   that distant noise dominates the second moment.
5. Record enough axial planes on both sides of the waist to constrain the near-
   waist curvature and far-field divergence.  Fit :eq:`interview-m2-beam` in both
   principal axes rather than deriving :math:`M^2` from one spot and one angle.
6. Inspect residuals and repeatability.  Report :math:`M_x^2`, :math:`M_y^2`, both
   waist sizes and locations, divergence, wavelength, fit range, sampling,
   attenuation, operating state, and uncertainty.

Why second moments are difficult
--------------------------------

The :math:`(x-\bar{x})^2` weighting in :eq:`interview-beam-moments` magnifies
energy far from the centroid.  Dark offset, stray light, dust scatter, a clipped
halo, and a too-large data window can therefore dominate the result even when
the central spot looks unchanged.  Conversely, a small window can hide real halo
power and make the result look artificially good.

Include these terms in the uncertainty and repeatability study:

* pixel scale, focus-stage position, and lens focal/wavefront uncertainty;
* dark offset, read noise, background gradient, hot pixels, and saturation;
* data-window or noise-equivalent-aperture selection;
* pulse-to-pulse profile change, pointing jitter, and camera exposure timing;
* attenuation-induced wavefront error, etalon fringes, clipping, and polarization
  sensitivity; and
* caustic-model residuals, astigmatism, nonparaxial focusing, and insufficient
  near/far sampling.

Writing a defensible requirement
--------------------------------

``M² < 1.2`` is incomplete.  A better requirement identifies both axes, the
second-moment convention, wavelength, operating power and pulse regime, warm-up
and environmental state, temporal gate/average, measurement plane range,
allowed attenuation method, applicable standard/version, uncertainty rule, and
acceptance statistic across units.

If the application cares about delivered energy, add a target-plane bucket
requirement rather than assuming an :math:`M^2` limit guarantees it.  If it cares
about peak intensity, specify the reference field and Strehl measurement.  The
metric should predict mission performance, not merely match the available beam
analyzer's default screen.

Interview traps
---------------

* A Gaussian fit is not a substitute for a second-moment calculation.
* A circular near field does not rule out far-field ellipticity or astigmatism.
* :math:`M^2` near one does not rule out pointing jitter or a low-power halo.
* Cropping, thresholding, or time-gating can improve a reported metric while
  excluding power that is still included in the advertised output.
* Two instruments can disagree because they use different centering, windows,
  width definitions, sampling, or attenuation—not because one numerical display
  is necessarily broken.
