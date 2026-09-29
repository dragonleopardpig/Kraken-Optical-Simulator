Future Plan
===========

Work that is designed but not built. These pages exist so that a direction can be
reviewed, argued with, and costed *before* code lands — and so that a reader can tell
at a glance what KrakenOS does today from what it is intended to do next.

Each page states its own status in the first line. Nothing here describes shipped
behaviour; for that, see the Manual and the Knowledge Base.

The corresponding design documents live outside the Sphinx tree, alongside the code
they govern:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - design document
     - what it governs
   * - ``docs/design_wave_domains.md``
     - the three-domain wave-optics architecture summarised in :doc:`wave_optics_roadmap`
   * - ``docs/design_scene_ir.md``
     - the materialized Scene IR, a prerequisite for the wave work from Stage 4 on
   * - ``docs/design_qt_migration.md``
     - the Tk → Qt migration, which the wave work deliberately does not touch
   * - ``docs/design_row_placement_space.md``
     - placement-space analysis that the Scene IR design builds on

.. toctree::
   :maxdepth: 1

   wave_optics_roadmap
