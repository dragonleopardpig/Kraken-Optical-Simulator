Photonics Essentials: Chapter 11 Questions
==========================================

Source
------

Thomas P. Pearsall, *Photonics Essentials: An Introduction with Experiments*
(McGraw-Hill, 2003), Chapter 11, ``Experimental Photonics: Device
Characterization in the Laboratory``, ``Questions to Think About``,
printed page 275.

These are qualitative review questions at the end of the laboratory chapter,
not numbered calculation problems.

Why does laser spectrum depend on current?
-------------------------------------------

Below threshold, the device behaves mainly as an LED: broad spontaneous
emission follows the semiconductor density of states.  As current approaches
threshold, gain becomes large over a narrower spectral interval.  Above
threshold, cavity modes inside that gain interval dominate through stimulated
emission.

Changing current also changes:

* carrier density and band filling, which move the gain peak;
* junction temperature, which changes band gap, refractive index, and cavity
  optical length;
* the number and relative power of longitudinal modes that exceed threshold.

For a Fabry-Perot cavity,

.. math::

   \nu_m=\frac{mc}{2nL}.

Current-induced changes in :math:`n` and :math:`L` shift the resonances, while
changes in gain decide which of those resonances lase.

How does slit width affect mode resolution?
--------------------------------------------

Narrower entrance and exit slits improve a scanning monochromator's spectral
resolution because each slit contributes less geometrical wavelength spread.
The tradeoff is reduced optical throughput and therefore poorer
signal-to-noise ratio.

The entrance slit defines the source width seen by the dispersing element;
the exit slit defines the wavelength interval passed to the single detector.
Neither slit is universally “more important.”  With symmetric optics and
matched slit widths, both make comparable contributions.  In the described
single-detector scan, the exit slit directly selects the detected band, but
opening either slit too far degrades resolution.  A useful lab test is to
narrow one slit at a time while holding the other fixed and plot measured
mode FWHM and signal amplitude.

How would a calibrated detector array help?
--------------------------------------------

Replace the exit slit and scanning single detector with a linear array at the
spectrograph focal plane.  Each pixel corresponds to a calibrated wavelength:

.. math::

   \lambda_i=\lambda_0+
   \left(\frac{d\lambda}{dx}\right)(x_i-x_0)

over a small approximately linear interval.

One exposure then records all resolved modes simultaneously.  This removes
the wavelength scan, reduces sensitivity to laser drift during a scan, and
usually eliminates the exit slit.  The entrance slit is still needed to set
spatial and spectral resolution.

The simplification introduces new calibration tasks: dark subtraction,
pixel-to-pixel responsivity correction, wavelength calibration with known
lines, saturation checks, and deconvolution of the array pixel width from the
instrument line shape.
