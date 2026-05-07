Provisional Manual
==================

These pages are a Sphinx conversion of
``KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf``. The original manual is
from 2021 and describes the core library model: ``surf`` objects collected into
a ``system``, exact sequential and non-sequential tracing, ``raykeeper`` data
collection, paraxial tools, pupil generation, atmospheric refraction, display
tools, STL solids, and examples.

The conversion keeps the technical content but normalizes wording, fixes obvious
legacy spelling issues, and points readers toward the current UI where Phase 5
now exposes the same core features.

Focused UI screenshots in these pages are generated from the live Tk editor:

.. code-block:: bash

   python -m KrakenOS.UI.capture_manual_ui_screenshots

.. toctree::
   :maxdepth: 2

   installation
   core_model
   editable_table
   nonsequential_first_design
   tracing_and_ray_data
   zemax_rayfile_sources
   pupil_paraxial_analysis
   gaussian_beams
   beam_splitters
   diffuse_scattering
   lens_fabrication_drawings
   viewers
   examples
