Captured USAF-1951 MTF
======================

KrakenOS has two different MTF paths:

* ``PSFCalc.calculate_mtf`` and the layout editor's MTF analysis transform a
  simulated or ray-traced point-spread function.
* ``USAFMTF.analyze_usaf_image`` measures a real camera/lens capture of a
  USAF-1951 three-bar target.

The vector file ``attachment/USAF-1951.svg`` is target artwork, not a captured
system response.  Print or display it at a known physical scale, capture it
through the machine-vision system without clipping highlights or shadows, and
analyze the resulting raster image.  Perspective-correct the chart first if it
is not normal to the optical axis.  This particular legacy SVG has unitless
``width``/``height`` values and declares its document units as pixels, so do not
assume a printer or browser preserved its intended millimetre scale.  Verify a
bar with a microscope or calibrated ruler: its physical width should be
``1 / (2 * f)`` mm for element frequency ``f`` in line-pairs/mm.

Method
------

For every selected USAF element, KrakenOS averages along the bars to obtain a
one-dimensional intensity profile.  It jointly fits the fundamental, third,
and fifth square-wave harmonics while allowing a linear illumination trend.
The fundamental image modulation is converted to MTF by

.. math::

   \mathrm{MTF}(f) = \frac{\pi}{4}\,
   \frac{M_{\mathrm{fundamental,image}}(f)}{C_{\mathrm{target}}}.

This Fourier-domain method is preferable to applying an infinite-square-wave
series directly to the finite three-bar element.  The result is a set of MTF
samples at the USAF frequencies

.. math::

   f(g,e) = 2^{g + (e-1)/6}\quad\text{line-pairs/mm}.

Vertical bars measure x response and horizontal bars measure y response.  The
CSV retains both directions, the fitted cycles/pixel, pixels/cycle, fit
:math:`R^2`, and an optional calibration consistency error.  Inspect these
diagnostics: fewer than roughly four pixels/cycle is undersampled, and a low
:math:`R^2` usually means the ROI contains a label, the orthogonal bars, severe
noise, or incorrect rotation.

Python API
----------

ROIs use ``(x0, y0, x1, y1)`` pixel bounds and should contain one complete
three-bar element without its number or the adjacent orthogonal element.

.. code-block:: python

   import KrakenOS as Kos

   rois = [
       Kos.USAFElementROI(0, 1, (120, 80, 240, 130), "vertical"),
       Kos.USAFElementROI(0, 1, (250, 70, 305, 190), "horizontal"),
       Kos.USAFElementROI(0, 2, (330, 90, 430, 132), "vertical"),
   ]

   result = Kos.analyze_usaf_image(
       "capture.tif",
       rois,
       magnification=0.5,   # absolute image size / object size
       pixel_pitch_um=3.45,
       target_contrast=1.0,
   )
   result.save_csv("capture_mtf.csv")
   figure, axes = result.plot(frequency_space="object")
   figure.savefig("capture_mtf.png", dpi=160)

Object-space frequency comes directly from the USAF group and element.  With
``magnification``, image-space frequency is ``object frequency / abs(m)``.
With ``pixel_pitch_um``, KrakenOS also converts the fitted cycles/pixel to a
measured image-space frequency.  A large discrepancy between those two values
indicates incorrect magnification, pixel pitch, ROI extent, or element labels.

Command line
------------

Create a JSON file describing the same ROIs:

.. code-block:: json

   {
     "magnification": 0.5,
     "pixel_pitch_um": 3.45,
     "target_contrast": 1.0,
     "rois": [
       {"group": 0, "element": 1, "roi": [120, 80, 240, 130], "orientation": "vertical"},
       {"group": 0, "element": 1, "roi": [250, 70, 305, 190], "orientation": "horizontal"}
     ]
   }

Then generate both outputs:

.. code-block:: bash

   python -m KrakenOS.USAFMTFCLI capture.tif rois.json

The default files are ``capture_mtf.csv`` and ``capture_mtf.png``.  Use
``--csv``, ``--plot``, and ``--frequency-space image`` to override them.

Measurement limits
------------------

This is an end-to-end system MTF: lens, focus, motion, sensor aperture,
demosaicing, sharpening, and compression can all affect it.  Use linear raw or
linearized image intensity where possible; gamma-encoded JPEG values bias
contrast.  The estimator does not automatically recognize the chart or remove
perspective distortion.  An SVG rasterization only tests the artwork/rendering
chain and cannot measure the machine-vision system.

The Fourier treatment follows the finite three-/four-bar method described by
G. D. Boreman and S. Yang, *Applied Optics* 34, 8050-8052 (1995), DOI
``10.1364/AO.34.008050``.  The general bar-to-OTF correction is discussed by
R. L. Lucke, *Applied Optics* 37, 7248-7252 (1998), DOI
``10.1364/AO.37.007248``.
