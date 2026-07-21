# 0378 — "Swap Imaging Lens" flow (replace the lens in place)

**Flag:** 20260721_085648 (build 35f27e24) — "After replacing Imaging Lens. I think we need proper
flow to replace imaging lens." The screenshot showed a single lens STEP floating alone, off the
optical axis, with no scene. User later clarified: this is a **Swap Lens** flow (replace the existing
imaging lens in place), distinct from a separate **Add Imaging Lens** flow (a second lens on another /
the same axis). Chosen scope: swap the surrogate rows AND the STEP, keep the rest of the scene, new
lens on-axis at the same datum. **Status:** SHIPPED 2026-07-21 (guard
`validate_open3d_swap_imaging_lens`, penta phase 318).

## Why it happened

The only way to bring in a lens was **Import Lens from Folder**, which generates a
`machine_vision_<slug>.py` and `load_layout_by_name`s it — i.e. it **replaces the entire working
layout**. On a full coaxial assembly (Object + beam splitter + LED + imaging lens + camera + FOV) that
throws the whole scene away and shows only the freshly-imported single-lens surrogate, off-axis. There
was no way to swap *just* the imaging lens.

## The fix — swap the imaging-lens block in place

`swap_imaging_lens_from_folder` (`layout_table_workbench`):

1. **Locate** the imaging-lens block — `_imaging_lens_block_indices` finds the Front..Rear
   vertex/lens-datum pair that brackets the ideal Blackbox groups + aperture stop (not the beam
   splitter or any other component between Object and Image). No block → clear error, "use Add Imaging
   Lens".
2. **Import** the replacement folder → build + write the surrogate → extract *its* vertex-datum block.
3. **Splice** `rows[:front] + new_block + rows[rear+1:]` — everything before (Object, BS, gap) and
   after (Image, camera-facing rows) is kept; only the lens block is replaced, at the same front-datum
   position (new lens on-axis where the old one was). The image side follows the new lens's back focal
   distance (a different lens genuinely images at a different plane; the glued camera tracks it).
4. **Rewire only the lens STEP overlay** — `_apply_swapped_lens_step_settings` sets the lens
   path/flip/largest-component/offsets/rotations from the new surrogate; the scene's own camera / LED /
   optical STEP overlays and all source/field/pupil settings are untouched.

UI: **Overlays/CAD menu → "Swap Imaging Lens from Folder..."** (3D top-controls) and the main-window
Insert → Machine Vision cascade. The inspector handler delegates then rebuilds via `_apply_model_change`
— it does NOT replace the working layout, so the inspector is never torn down (no bugs/0294 path).

Verified headless on the real MV-150 scene: swapping the 15056 lens for PYRITE 5.6/80 replaced the
five lens-block rows + the STEP path (15056 → 1097785), and Object / beam splitter / LED source / Image
all survived.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_imaging_lens_block_indices`,
  `swap_imaging_lens_from_folder`, `_apply_swapped_lens_step_settings`.
- `KrakenOS/UI/open3d_inspector.py` — inspector delegation (in-place rebuild).
- `KrakenOS/UI/panels/open3d_top_controls.py`, `panels/main_context_menu.py` — the menu commands.
- `KrakenOS/UI/validate_open3d_swap_imaging_lens.py` — display-free guard (penta phase 318).

## Not in scope (separate)

**Add Imaging Lens** — adding a SECOND imaging lens on another / the same optical axis — is a distinct
flow the user called out; not built here.
