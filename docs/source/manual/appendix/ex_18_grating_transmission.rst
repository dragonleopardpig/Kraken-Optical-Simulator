7.18 Example — Diffraction Grating in Transmission
==================================================

PDF section 7.18. Source script: ``KrakenOS/Examples/Examp_Diffraction_Grating_Transmission.py``.

Sets ``Diff_Ord``, ``Grating_D`` and ``Grating_Angle`` on a planar surface
to make it a transmission grating. Tracing a fan of three wavelengths
shows the dispersion: each wavelength leaves the grating at a different
angle for the same diffraction order.

.. figure:: ../../_static/manual/examples/18_grating_transmission_a.png
   :align: center
   :alt: Transmission grating dispersion (view 1)

   Figure 25a. Transmission grating — multi-wavelength fan.

.. figure:: ../../_static/manual/examples/18_grating_transmission_b.png
   :align: center
   :alt: Transmission grating dispersion (view 2)

   Figure 25b. Alternate view.

.. literalinclude:: ../../../../KrakenOS/Examples/Examp_Diffraction_Grating_Transmission.py
   :language: python
