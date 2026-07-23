# 0423 — Resize a parametric beam splitter numerically, in place

**Flag `flag_20260723_115239_954`** (follow-up to 0422):
> "Can we have a way to resize optical component by direct extrude a surface and/or input the numerical
> value to the particular dimension?"

Chosen scope (via ask): the **numerical-input resize for the parametric beam splitter** — the tractable
first step, since the one-click BS ("Add Beam Splitter to LED") is already a parametric solid. (A general
drag-to-extrude on arbitrary imported solids is a separate, much larger CAD-editing project.)

## What it does

Right-click a beam splitter added via "Add Beam Splitter to LED" → **"Resize Beam Splitter…"** → a small
dialog with the current dimensions (cube: **side**; plate: **width / height / thickness / tilt**). Enter
new values, click **Resize**, and the solid is regenerated at those dimensions and replaced **in place**.

## How it stays in place

- **Recipe persistence** — `add_beam_splitter_to_led` now stores `beam_splitter_kind` +
  `beam_splitter_params` in the promotion dict (survives save/reload), so the resize reads and pre-fills
  the current dimensions.
- **Replace in place** — `resize_beam_splitter` regenerates via `generate_beam_splitter(kind, **params)`
  and swaps it with `replace_promoted_optical_solid_step` (bugs/0404), which **preserves the pose**
  (rotation + placement + transverse decenter) — so the resized BS keeps wherever the user put it
  (including a manual orientation). The parametric solid is origin-centred, so the same placement offset
  re-centres it. The authored coating face is re-applied by the replace; the non-face beam-splitter mark +
  recipe are re-stored, and the coating is re-flagged belt-and-suspenders.

Gating: the "Resize Beam Splitter…" item appears only when `beam_splitter_resize_info(row)` finds a
parametric BS recipe on the row — never on a plain STEP/mirror/lens.

## Verification (`validate_open3d_bs_resize`, penta phase 341)

Display-free:

| check | asserts |
|---|---|
| PERSIST | `add_beam_splitter_to_led` stores `beam_splitter_kind` + `beam_splitter_params` in the promotion |
| RESIZE-INFO | `beam_splitter_resize_info` returns `(kind, params)` for cube/plate BS rows, `None` for non-BS / plain / out-of-range; the params fit the factory's kwargs |
| RESIZE-WIRING | `resize_beam_splitter` regenerates + replaces in place + re-marks the beam splitter |
| MENU | the element menu offers "Resize Beam Splitter…" gated on `beam_splitter_resize_info`, wired to the dialog |

4/4 pass. Baseline phase 341 = pass.

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — persist the recipe; `beam_splitter_resize_info`,
  `resize_beam_splitter`, `open_resize_beam_splitter_dialog`.
- `KrakenOS/UI/services/open3d_face_assignment.py` — "Resize Beam Splitter…" element-menu item.
- `KrakenOS/UI/validate_open3d_bs_resize.py` — guard (phase 341).

## In-app eyeball still owed

Add a BS to the LED → right-click it → **"Resize Beam Splitter…"** → change the thickness (or side) → it
regenerates in place at the new size, keeping its position/orientation and the coating. (A pre-existing
BS added before 0423 has no stored recipe, so it won't show the item — re-add it once to get a
resizable one.)
