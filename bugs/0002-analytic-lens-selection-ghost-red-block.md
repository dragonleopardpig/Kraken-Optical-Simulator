# 0002 — Selected analytic lens leaves a "ghost red block"; slide has no handle

**Status:** Fixed (ghost red block). Slide-along-axis "no handle" is a UX gap, not a code bug — see below.
**Component:** Open 3D inspector — row selection highlight
**Reported via:** in-app recorder, `attachment/recorded_bug_repros/flag_20260602_153241_516/`

## Symptom

Two issues in one recording, both after the 0001 all-red fix:

> 1. "still a ghost red block" trailing the selected lens.
> 2. "Checked 'Slide along axis', still no handle pop up for sliding."

## Issue 1 — ghost red block (FIXED)

### Root cause

A promoted analytic lens maps **two** surface bodies to its row, not one:

- the **visible glassy drum** — `_kraken_glassy_lens_body`, opacity ~0.35,
  the thing you actually see; and
- a **second, baseline-invisible companion surface** — a pick-only / duplicate
  body representation flagged `_kraken_round_lens_like_step_body` (set in
  `open3d_inspector.py` `_add_mesh_actor` when the mesh is round-lens-like and a
  pick/track label is set) with **baseline opacity 0.0**. It is never meant to
  be drawn; it exists for hit-testing.

`_set_row_actor_selected` recolors *every* actor mapped to the selected row.
The all-red fix (0001) only suppressed triangle edges for glassy / file-backed
bodies; the invisible companion still fell through to the sparse-surface branch,
which on selection bumped its opacity (0.0 → 0.75) **and** turned on bright-red
triangle edges (line width 5). That resurrected the undrawn body as a solid red
block sitting behind / around the pink drum — the "ghost red block".

The 0001 Phase-10 check missed it because it inspected only the actors it knew
about (the glassy body) by **vtkProperty**; it never rendered pixels, so a
*second* actor painting red was invisible to it. (This is exactly why visual
bugs now require an image-snapshot test — see `bugs/README.md`.)

### Fix

`KrakenOS/UI/open3d_inspector.py` — in `_set_row_actor_selected`, right after the
baseline-style dict is captured, early-out when the captured baseline opacity is
≈ 0:

```python
if float(base.get("opacity", 1.0)) <= 1e-3:
    return
```

A baseline-invisible actor is a pick-only / hidden companion surface; selection
must leave it untouched. It can show no meaningful selection feedback anyway
(it is not drawn), and the visible glassy drum + its separate rim/feature-edge
actor already provide the pink fill and clean outline. This is root-cause: the
hidden actor is simply excluded from the recolor instead of patching the red
back out after the fact.

## Issue 2 — "no handle to slide" (UX gap, not fixed here)

Slide-along-axis is **drag-based by design**: it is a *mode*
(`slide_along_axis_mode_var`), not a pop-up handle actor. When the mode is on
and an eligible promoted optical body is selected, the user clicks the body and
**drags along Z**; the status line reads "click an optical element body and drag
along Z". Eligibility requires a promoted optical solid with preceding/trailing
rows. There is no handle actor to "pop up", so the user's expectation of a
visible slider is a UX-affordance gap, not a regression. Deliberately **not**
changed here without product sign-off; flagged to the user separately.

## Tests

- **Image-snapshot (display-required)** —
  `KrakenOS/UI/validate_open3d_analytic_lens_selection_snapshot.py`. Promotes
  the DCV fixture onto a clean Object+Image chain, selects row 1 via the live
  recolor path, renders the scene to a PNG (boots its own Xvfb if `DISPLAY` is
  unset), and asserts the selected lens is dominated by pink fill
  (`pink > 500`) with only negligible red (`red < 80`; the constant ~9 red
  pixels are the axis-origin marker, not the lens). A pre-fix ghost red block
  is ~1000+ red pixels. Run:
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot`
- **Regression / end-to-end** — Phase 10
  (`phase_10_analytic_lens_selection_not_all_red`) in
  `validate_open3d_penta_telescope_comprehensive.py` was upgraded: in addition
  to the property assertions it now renders the selected lens and runs the same
  red/pink pixel check, so the ghost red block is machine-detectable on the full
  penta-cascade gate.
