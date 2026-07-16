# 0326 — LED clear-aperture opening edge is a deterministic plain-hover target

## Flag / redirect
After the 0323/0324 Alt-hover work the user re-recorded two flags
(`flag_20260716_113333_847` "default selection still edge. Still have phantom highlight." and
`flag_20260716_113415_401` "mouse hover while pressing Alt does not show any differnece at all.")
and then **stopped the general chase**:

> we have been circling around this multiple times already. Let's break it down and do one task at a
> time: 1. The imported LED STEP, can you "see" the Clear Aperture opening? 2. If yes, can you make the
> edge selectable first?

Then: **"OK, plain first, if it works, we plan next step."**

So the scope is deliberately narrowed: forget the fuzzy per-cell face/edge pick for a moment and make the
**one edge that matters** — the clear-aperture opening rim — reliably selectable on **plain** hover.

## Task 1 — yes, the opening is visible (deterministically)
`led_clear_aperture_detect.detect_clear_aperture_openings_from_analytic_faces` already exists (bugs/0319
C2). Run on the actual imported LED (`attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP`) it returns the opening
as the top candidate:

| Rank | face_index / id | centroid | normal | span | bbox_fill | score |
|------|-----------------|----------|--------|------|-----------|-------|
| **1** | **266 / F267** | (0, 116, 0) | +y | 85×85 | 0.10 | **0.955** |
| 2 | 306 / F307 | (0, 117, 0) | +y | 84×84 | 0.31 | 0.860 |
| 3–5 | 100/8/185 | side/ring | ±z/+y | ~75–85 | 0.50–0.52 | 0.77 |

F267 is the object-facing square window: a thin rim (fill 0.10) around the hole. On the display mesh
`kraken_step_face_index == 266` (== `kraken_step_selection_face_index == 266`) is exactly those 1196 rim
cells → 1172 boundary segments (`attachment/_ca_edge_hover_style.png` shows it as a gold rim on the body).

Telling detail: the flag the user actually hovered resolved `F012`, a **back housing** face — never the
opening. That is *why* "select any edge" kept fighting noise; targeting the detected opening is robust.

## Task 2 — make the opening's edge selectable on plain hover
The insight (per "guard the invariant, not the instance"): the opening is a **deterministic** feature, so
we don't need the pixel-varying per-cell pick for it. When the hovered cell lands on the detected opening
face, **substitute the opening's rim EDGE as the hover feature**. It flows through the existing shared
pick path, so the hover highlight and the click both use it (WYSIWYG) — no new interaction plumbing, no
Alt, no modifier-stream race (the 0324 gremlin is sidestepped entirely).

### Wiring
- **`Kraken3DInspector._clear_aperture_opening_face_index(label)`** (new) — the opening face index:
  a manually recorded clear aperture (bugs/0134) wins; else the auto-detect top candidate. The
  auto-detect result is geometry-stable, cached per STEP source path
  (`self._ca_opening_face_index_cache`); the analytic document itself is already cached by
  `_load_step_analytic_document`, so plain hover stays cheap.
- **`Kraken3DInspector._clear_aperture_opening_edge_feature(label, face_index)`** (new) — returns the
  hover feature `(centroid, overlay, normal)` where `overlay = _hover_overlay_for_feature(centroid,
  _clear_aperture_outline(...))`. The outline is `face_outline_from_face_indices` — a **lines-only**
  polydata, so `_set_step_hover_outline_impl` renders it as gold EDGE tubes (its
  `GetNumberOfPolys() > 0` fill/edge switch), i.e. the rim EDGE, not a face fill. Centroid/normal come
  from `_step_overlay_fine_face_centroid_normal` (world frame, aligned to the drawn body).
- **`step_feature_pick_for_display_xy`** (`services/open3d_round_lens_pick.py`) — a short-circuit at the
  TOP: if the picked cell's `clear_aperture_face_index_for_display_cell` equals the opening face index,
  return the opening edge feature. Guarded on `getattr(inspector, "_clear_aperture_opening_face_index")`
  and `cell_id >= 0`, so test doubles / right-click (cell_id −1) fall through unchanged. Non-opening
  cells are untouched → the metadata/raw paths still run for the rest of the body.

The manual "Set Clear Aperture" pick mode (`_update_clear_aperture_hover_highlight`) is a **different**
path and is not affected.

## Verified (display-free + offscreen)
`KrakenOS/UI/validate_open3d_led_ca_edge_hover.py` — **PASS** (drives the real methods against the cached
analytic mesh with a light fake editor; no OCC, no GLX):
- **A** `_clear_aperture_opening_edge_feature("led", 266)` → face_id `F266`, overlay is a LINE loop
  (`GetNumberOfLines()=1172`, `GetNumberOfPolys()=0`), finite centroid/normal.
- **B** `step_feature_pick_for_display_xy` on an opening cell short-circuits to that rim-edge feature.
- **C** a non-opening cell does NOT return the CA edge (got `F435`) — the short-circuit is selective.

Offscreen render `attachment/_ca_edge_hover_style.png` shows the rim in the live gold-tube hover style.

Penta **phase 289** (`phase_289_led_ca_edge_hover`) delegates to the guard; baseline updated (`"289":
"pass"`). Phases 287/288 still pass.

## Notes / remaining (the "plan next step" after the user confirms live)
- **In-app eyeball owed** (needs a GLX display this box lacks): import the LED, hover the front window,
  confirm the rim edge highlights on plain hover and a click selects it.
- The general fuzzy per-cell face/edge pick + the phantom whole-face fill (bugs/0325) are still open;
  this bug intentionally does NOT touch them — it delivers the one reliable edge first.
- Next candidates once confirmed: hover the opening's inner hole edge vs the whole rim; a second opening
  when a BS is glued (LED-with-BS has two openings); face selection built on the same deterministic route.

## Files
- `KrakenOS/UI/open3d_inspector.py` — `_ca_opening_face_index_cache` init;
  `_clear_aperture_opening_face_index`, `_clear_aperture_opening_edge_feature`.
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — opening-edge short-circuit in
  `step_feature_pick_for_display_xy`.
- `KrakenOS/UI/validate_open3d_led_ca_edge_hover.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_289_led_ca_edge_hover`.
- `tools/penta_validator_baseline.json` — phase 289 baseline + title.
