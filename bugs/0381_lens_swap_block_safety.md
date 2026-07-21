# 0381 — "After lens swap the whole scene is gone" (Import vs Swap footgun + tight block)

**Flags:** `flag_20260721_115241_701` ("before Lens swap.") + `flag_20260721_115330_452` ("After lens
swap.") — before = a full assembly (beam splitter housing, imaging lens, camera, prism); after = ONLY
the new lens on a reoriented vertical axis, everything else gone.

## Root cause — it was an Import, not a Swap

The after-state is a **full layout replacement**: `step_actor_counts {lens:1}` (camera + led overlays
gone), `promoted_solid_rows []` (both promoted solids gone), axis reoriented — exactly what "Import Lens
from Folder" does (`import_machine_vision_lens_from_folder` → `load_layout_by_name` →
`_close_scene_viewers_for_layout_replacement`). The **Swap** flow (bugs/0378) splices the lens in place
and was verified to preserve everything on the real MV-150 scene (9 rows, promoted solids + all overlays
kept). Decisively, the after-state wiped the promoted solid at **row 1**, which sits *before* any datum
row — the swap's splice (`rows[:front] + new_block + rows[rear+1:]`, `front ≥ the first datum row ≥ 2`)
*cannot* remove it. So this was Import, whose two menu entries sit right next to Swap with the opposite
behaviour (replace vs keep) — a footgun.

## Fixes

1. **Import confirmation** — `import_machine_vision_lens_from_folder` now calls
   `_import_would_discard_scene()` (True when a camera/led/optical overlay or a promoted solid is
   present) and, for the interactive path, warns that Import REPLACES the whole scene and points at
   "Swap Imaging Lens" to keep it. A programmatic call (folder passed) is unaffected.
2. **Menu labels** — "Import Lens from Folder **(replaces scene)**…" vs "Swap Imaging Lens from Folder
   **(keeps scene)**…" in both the 2-D right-click menu and the Open-3D CAD menu.
3. **Tight block detector** (a real latent bug found while digging) — `_imaging_lens_block_indices`
   spanned first-front → LAST-rear, so a genuine swap on a two-lens or stray-"rear vertex" scene would
   splice everything between them away. It now returns the TIGHT single block (first front → its FIRST
   rear) and refuses a block that contains a foreign element (promoted solid / Object / Image), so a
   swap can never wipe non-lens content.

## Verification

- `_imaging_lens_block_indices`: lens-datum + optical-vertex naming resolve tight; two blocks → first
  only; a stray later "Camera Rear Vertex" no longer widens the block; a promoted solid inside → refused.
- MV-150 full-swap repro still preserves all 9 rows, both promoted solids, and every overlay.
- `_import_would_discard_scene`: True for camera/led/optical overlay or a promoted solid; False for a
  bare single-lens scene.
- Existing swap guard (phase 318) still green.

Guard `validate_open3d_lens_swap_block_safety`, penta **phase 322**.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — tight `_imaging_lens_block_indices`,
  `_import_would_discard_scene`, Import confirmation.
- `KrakenOS/UI/panels/main_context_menu.py`, `panels/open3d_top_controls.py` — clarified labels.
- `KrakenOS/UI/validate_open3d_lens_swap_block_safety.py` — guard (phase 322).
