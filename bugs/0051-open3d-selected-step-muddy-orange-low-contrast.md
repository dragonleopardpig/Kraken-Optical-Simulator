# 0051 — Open 3D: a selected STEP reads as a muddy, low-contrast orange blob

## Symptom (user's words)

> highlight edge color does not have contrast. And why this STEP color is
> orange? different from the rest.

Flag `flag_20260610_192640_648` (2026-06-10T19:26:40), `machine_vision_150mm`
layout, `cad_axis_pick` mode. The selected LED STEP body was rendered a flat,
saturated orange — visually unlike the other (unselected) solids — and the
selection edge had no contrast against it.

## Root cause

`Kraken3DInspector._set_step_actor_selected` (open3d_inspector.py) styled a
selected STEP overlay by turning on **per-triangle edges** in orange
(`SetEdgeColor(1.0, 0.48, 0.0)`) and bumping ambient, with **no body-fill
change**. But an imported STEP overlay is a *dense CAD tessellation*: drawing
every triangle edge paints a wireframe that fills the body, and in orange over
the warm glass palette that reads as a flat orange shape — the edge "outline"
is lost in the wireframe (no contrast), and the body looks like it changed
material ("why is this orange?").

Meanwhile promoted rows / optical solids already had a clear, high-contrast
selection idiom (`_set_row_actor_selected`, bugs/0001-0003): a **pink
translucent body fill** with the dense triangle edges suppressed. STEP overlays
just never adopted it.

## Fix

`_set_step_actor_selected` now uses the same idiom: suppress the per-triangle
edges (the body's own glass-edge rim actor — also tagged with the label, so it
gets styled too — keeps the silhouette) and fill the body pink
(`1.0, 0.45, 0.65`) with a bumped opacity. A selected STEP now reads as the
same pink translucent highlight used everywhere else, high-contrast against the
cool/neutral resting glass and unambiguous as "selected" rather than a material
change.

Files:

- `KrakenOS/UI/open3d_inspector.py` — `_set_step_actor_selected` selected
  branch rewritten (pink fill + edges off, mirroring `_set_row_actor_selected`).

No validator pinned the old orange `(1.0, 0.48, 0.0)`; the deselect/restore path
is unchanged (it still restores the captured base style).

## Tests

- `KrakenOS/UI/validate_open3d_step_selection_pink_snapshot.py` — image
  snapshot (needs an X server, like the analytic-lens snapshot). Renders the
  STEP overlay unselected then selected and asserts the selection introduces a
  body-sized region of **pink** that was absent unselected (selected ≈ 194 pink
  px vs unselected ≈ 4). A regression back to the orange edge-only style leaves
  the pink count at the unselected baseline and fails. Run:
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_selection_pink_snapshot`.
- Phase 56 in `validate_open3d_penta_telescope_comprehensive.py` — folds the
  same pink-selection assertion into the comprehensive harness.

Visually verified by rendering the selected vs unselected prism overlay: the
selection flips from cool teal glass to a clean pink translucent body with a
crisp rim, no orange wireframe.
