# 0916 -- ungated sweep, batch 1: my own broken import, and test doubles behind the code

The 2026-09-27 sweep ran all 175 ungated validators, each in its own process inside
`devenv shell`: 139 pass and 36 fail. None of them modified a tracked file. This batch is the
failures whose cause is in the TEST.

- **`validate_five_penta_prism_cascade`: I broke it in 0914.** It imports `PENTA_ENTRANCE_FACE`
  and `PENTA_MIRROR_FACES` from `validate_penta_mirror_3d_cascade`, and 0914 deleted them.
  - They are restored, documented as the old clustering's names. On this promoted-row path the
    faces keep bare IDs, and those names are right.
  - Once running, it expected one exit-axis record per prism. b987840d (2026-05-27, after the
    guard) deliberately draws no separate guide for a leg parallel to global z, because the
    dotted optical axis already is that guide; prism 3 exits along +z. It now expects one per
    non-z leg: 2, 2, 3 and 4 as the beam folds.
- **`validate_open3d_coaxial_imaging_launch`.**
  - The stub lacked `_source_spec_aim_point` (bugs/0680).
  - The live-vs-saved comparison set the live INTERACTIVE preview (capped at 200 rays by design,
    bugs/0540) against the full-count saved bundle. It now compares the live ANALYSIS launch
    (`full_count=True`, bugs/0590): byte-identical, spanning 74 x 55 mm.
- **`validate_open3d_ra_mirror_fold_follows_reflection`:** the stub lacked
  `_lens_datum_row_index` (bugs/0384).
- **`validate_open3d_step_reselect_single_gizmo`:** the fake lacked
  `_remove_actor_from_renderers` (the gizmo layer, bugs/0112). The real method is bound.
- **`validate_open3d_step_translate_gap`.** The fake thickness service lacked `arrow_mesh`'s
  `thickness_scale` argument and `DIMENSION_LEADER_LINE_WIDTH` (the thicker live gap, #65). The
  inspector swallows drawing errors into `append_debug`; surfacing them named both. The fake
  editor also gains `history_transaction` (bugs/0449). Now 29 checks pass.
- **`validate_table_component_workflow`:** its `__new__`-built editor lacked
  `_active_cell_border_after_id`.

No product change.
