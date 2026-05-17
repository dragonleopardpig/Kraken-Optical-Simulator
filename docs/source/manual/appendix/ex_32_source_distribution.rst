7.32 Example — Source Distribution Function
===========================================

PDF section 7.32. Source script: ``KrakenOS/Examples/Examp_Source_Distribution_Function.py``.

Final example of the appendix: defines a custom source-distribution
function that produces ray origins and directions according to a
user-specified spatial/angular probability distribution. Useful for
modelling extended sources, LED emitters or speckle distributions.

The script ends with several 3D viewer panels showing the source samples,
the rays as they leave the source, and the resulting irradiance on the
detector.

.. figure:: ../../_static/manual/examples/32_source_distribution_a.png
   :align: center
   :alt: Source-distribution example — panel a

   Figure 39a.

.. figure:: ../../_static/manual/examples/32_source_distribution_b.png
   :align: center
   :alt: Source-distribution example — panel b

   Figure 39b.

.. figure:: ../../_static/manual/examples/32_source_distribution_c.png
   :align: center
   :alt: Source-distribution example — panel c

   Figure 39c.

.. figure:: ../../_static/manual/examples/32_source_distribution_d.png
   :align: center
   :alt: Source-distribution example — panel d

   Figure 39d.

.. figure:: ../../_static/manual/examples/32_source_distribution_e.png
   :align: center
   :alt: Source-distribution example — panel e

   Figure 39e.

.. figure:: ../../_static/manual/examples/32_source_distribution_f.png
   :align: center
   :alt: Source-distribution example — panel f

   Figure 39f.

.. literalinclude:: ../../../../KrakenOS/Examples/Examp_Source_Distribution_Function.py
   :language: python
