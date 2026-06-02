# 0001 — Selecting an analytic lens renders solid red, no slide handle

**Status:** Fixed
**Component:** Open 3D inspector — row selection highlight
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260602_144331_600/`

## Symptom

> "selecting the analytical lens become all RED, and no handle for me to slide"

Selecting a promoted analytic lens (e.g. a biconvex/DCV singlet or achromat
brought in from STEP and promoted to analytic surfaces) paints the whole
body solid red instead of the intended pink translucent fill.

## Root cause

`Kraken3DInspector._set_row_actor_selected` (a `@staticmethod`) decides on
selection whether to draw per-triangle edges. For a dense solid it must NOT
turn edges on — a red wireframe across every triangle smothers the pink
translucent fill and the body reads as solid red.

The edge-suppression branch was gated **only** on
`_kraken_file_backed_row_body` — actors backed by an on-disk STL (Solid 3D /
promoted-STEP solids). A **revolved / analytic lens body** (no STL: a
biconvex drum, a Standard cap, a promoted-STEP body plate) is an equally
dense solid but was never flagged, so it fell into the `else` branch
(`SetEdgeVisibility(1)` + bright-red edges, line width >= 5). That red
wireframe is the "all red".

In `open3d_scene_refresh.py` such bodies are exactly the set where
`glassy_lens = analytic_optic_surface and mesh_opacity > 0.0` — and
`analytic_optic_surface` excludes file-backed rows, so the two flags are
mutually exclusive (no double-flagging).

The "no handle to slide" part is separate and **by design**: slide-along-axis
is a mode (`slide_along_axis_mode_var`), not a per-selection handle actor.
Not addressed by this fix.

## Fix

Flag glassy analytic lens bodies, then broaden the edge-suppression gate to
cover them the same way file-backed solids are covered. Glassy bodies carry
their own separate rim/feature-edge outline actor, so suppressing the body's
own triangle edges still leaves a clean selection outline.

- `KrakenOS/UI/services/open3d_scene_refresh.py:399` — set
  `body_actor._kraken_glassy_lens_body = True` when
  `glassy_lens` (`open3d_scene_refresh.py:374`), right after the existing
  `_kraken_file_backed_row_body` flag (`open3d_scene_refresh.py:387`).
- `KrakenOS/UI/open3d_inspector.py:3312-3314` — read both flags and select on
  `suppress_select_edges = is_file_backed_body or is_glassy_lens_body`; the
  suppressed branch sets `EdgeVisibility(0)` and keeps the pink fill
  `(1.0, 0.45, 0.65)` (`open3d_inspector.py:3322`).

## Tests

- **Unit / display-free** —
  `KrakenOS/UI/validate_open3d_analytic_lens_select_not_all_red.py`. Builds
  real `vtk.vtkActor`s and asserts the contract of `_set_row_actor_selected`:
  glassy + file-backed bodies -> edge visibility 0 + pink fill; a plain
  sparse surface still keeps the red outline; deselect restores the
  baseline. Run:
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analytic_lens_select_not_all_red`
- **Regression / end-to-end** — Phase 10
  (`phase_10_analytic_lens_selection_not_all_red`) in
  `validate_open3d_penta_telescope_comprehensive.py`: promotes a real lens
  fixture onto a clean chain, drives the live recolor path
  (`_set_row_highlights` -> `apply_row_selection` ->
  `_set_row_actor_selected`), and asserts the body stays
  edge-suppressed + pink while selected and restores on deselect.
