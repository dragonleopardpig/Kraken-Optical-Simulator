# 0910 -- phase 147 (navigation cube) failed: my own 0905 moved the construction

bugs/0905 moved the VTK core, the navigation cube included, out of `Kraken3DInspector.__init__`
into `_attach_vtk_core`. Guard `validate_open3d_navigation_cube` check C read `__init__` alone
and failed on all five needles: construct, apply-orientation, apply-step, get-camera and import.
The 0905 gate ran only the phases that change touched, and 147 was not among them. The full run
found it.

Fix:
- `open3d_inspector.inspector_construction_source()` returns the source of the whole
  construction path: `__init__`, `_attach_vtk_core` and `_attach_shell_viewport`.
- A guard asking "does the inspector build X" reads that, so the next split of construction does
  not break it.

Lesson: a change that MOVES code needs a full-suite run, not just the phases that name the file.
