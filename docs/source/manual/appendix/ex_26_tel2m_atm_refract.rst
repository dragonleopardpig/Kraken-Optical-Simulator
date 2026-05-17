7.26 Example — Tel 2M Atmospheric-Refraction Corrector
======================================================

PDF section 7.26. Source script:
``KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Static.py``.

End-to-end demonstration of the AstroAtmosphere integration in
:doc:`../pupilcalc_tool`: three wavelength groups are traced through the
telescope; their spot centroids drift apart by tens of micrometres at the
focal plane because of atmospheric dispersion, and a corrector element is
added to compensate.

The 2021 manual referred to a single
*Examp-Tel_2M_Atmospheric_Refraction.py*; the current repo splits it into
``..._Corrector_Static.py`` and ``..._Corrector_Adaptable.py``.

.. figure:: ../../_static/manual/examples/26_tel2m_atm_refract_a.png
   :align: center
   :alt: Atmospheric refraction corrector (panel 1)

   Figure 33a.

.. figure:: ../../_static/manual/examples/26_tel2m_atm_refract_b.png
   :align: center
   :alt: Atmospheric refraction corrector (panel 2)

   Figure 33b.

.. figure:: ../../_static/manual/examples/26_tel2m_atm_refract_c.png
   :align: center
   :alt: Atmospheric refraction corrector (panel 3)

   Figure 33c.

.. figure:: ../../_static/manual/examples/26_tel2m_atm_refract_d.png
   :align: center
   :alt: Atmospheric refraction corrector (panel 4)

   Figure 33d.

.. literalinclude:: ../../../../KrakenOS/Examples/Examp_Tel_2M_Atmospheric_Refraction_Corrector_Static.py
   :language: python
