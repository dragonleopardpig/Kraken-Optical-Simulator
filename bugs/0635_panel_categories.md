# 0635 — left panel solvers grouped under "Given → Solve for" categories (user request)

User: *"for all the calculator or solver on the left panel, can properly categorize them?
Under some big titles like Given xxx, Solve for yyy, or similar."*

## What shipped

The Open 3D left "Live Controls" panel now groups its sections under three bold category
headers (each with a gray one-line subtitle + separator), built by `_category()`/`_section()`
helpers in `Open3DLiveControlsPanel.build`:

- **Set up** — "The field to image and how the scene is drawn." → Field, Trace / Display.
- **Solve the current system** — "Given the loaded optics → object / image / FOV, or a
  thickness." → Object / Image / FOV (Quick Estimation), Variable thickness.
- **Size a new system** — "Given FOV + resolution + working distance → the camera + lens
  to buy." → Camera + lens (System Selection).

Section CONTENT is unchanged (same builder methods); only the grouping/headers are new.

Verified: guard phase 475 (`validate_open3d_0635_panel_categories`) pins the three headers,
the section titles, and their order. Screenshot bugs/_0635_categorized_panel.png (rendered
with a stub inspector — placeholders stand in for each section's real controls).
