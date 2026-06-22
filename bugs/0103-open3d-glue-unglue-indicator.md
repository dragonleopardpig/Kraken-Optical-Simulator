# 0103 — BS↔LED glue stays unglueable + shows a browser indicator

**Flagged:** 2026-06-22 (recorded `flag_20260622_115043_698`).
Reported symptom: *"No glue/unglue indicator. After glue, no unglue option."*

## What the glue is
There are two unrelated "Glue" commands on a STEP element's right-click menu; only
the second one is involved here:

1. **"Glue STEP to Surrogate"** — a one-shot placement reset
   (`glue_step_overlay_to_surrogate`). No persistent state, no Unglue. Not this bug.
2. **"Glue BS to LED" / "Unglue BS from LED"** — a *persistent rigid glue* toggle
   (`set_optical_led_glue` / `optical_led_glued`, editor flag `_optical_led_glued`).
   It is **saved to disk** (`layout_settings.py`) and makes the beam-splitter and
   the LED move together (the carry-drag mirrors one overlay's placement delta onto
   its partner).

## Root cause
The Glue/Unglue pair was gated behind `_optical_led_glue_available()`, which is True
only when **both** the `"optical"` (beam splitter) and `"led"` overlays are still
imported *as overlays* (`_step_path_for_label(label)` non-None for both).

Promoting the beam splitter ("optical" overlay → optical-solid row) removes the
"optical" overlay, so `_step_path_for_label("optical")` becomes None →
`_optical_led_glue_available()` is False → **the Unglue command disappeared from
every menu** while the glue flag stayed ON and survived save/reload. Result: a glue
that is stuck on, with no way to release it and no indication it is even active.

The carry-drag that the glue drives (`scene_placement_commands.py`) only operates on
two *overlays*, so once the BS is a row the glue is also mechanically inert — all the
more reason the user must be able to see it and turn it off.

## Fix
Unglue must be reachable for as long as the glue is active, and the active state must
be visible. Two anchors and one indicator:

- **LED overlay is the stable anchor.** The LED is a decoration — never promoted
  (bugs/0101) — so its overlay is always present while the scene has an LED. When
  `optical_led_glued()` is True, the LED overlay's menu offers **"Unglue BS from
  LED"** regardless of whether the "optical" overlay still exists. Only the *Glue*
  direction stays gated on `_optical_led_glue_available()` (you can only glue two
  live overlays together).
  - `KrakenOS/UI/services/open3d_face_assignment.py::append_element_context_actions`
    overlay block: `if step_label in ("optical","led"):` → when glued, add Unglue;
    elif available, add Glue.
- **The promoted BS row also offers Unglue.** New
  `Open3DFaceAssignmentService._row_is_glued_optical_bs(row_index)` is True only for a
  promoted "optical" optical-solid row while glued; both promoted-row branches
  (file-backed and promoted-analytic) emit "Unglue BS from LED" behind that guard.
- **Browser indicator.** New `Open3DStepAdminPanel._glue_partner_suffix(label)` returns
  `"  — glued to BS"` for the `led` element and `"  — glued to LED"` for the `optical`
  element while glued (else `""`). `refresh()` appends it to **both** the overlay label
  and the promoted-row label, so the Scene Components tree shows the glue at a glance.

## Repro / test
`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_glue_unglue_indicator`
— display-free. Checks: (A) glued + "optical" promoted away → LED overlay still offers
Unglue (and keeps the unrelated "Glue STEP to Surrogate" reset); (B) not glued + both
overlays → offers Glue, not Unglue; (B') a lone overlay offers no BS↔LED item but keeps
"Glue STEP to Surrogate"; (C) `_row_is_glued_optical_bs` is True only for a glued
promoted "optical" row (False when not glued / for a "lens" row), plus a source check
that both promoted-row branches gate Unglue on it and that the overlay Unglue is gated
on `optical_led_glued()` not availability; (D) `_glue_partner_suffix` returns the exact
suffix strings (and `""` when not glued / for an unrelated element), plus a source check
that `refresh()` applies it to overlays AND promoted rows. Penta phase 89.

## Owed
In-app eyeball: headless can't drive a real right-click pick or render the tree, so the
visible "— glued to …" suffix and the live Unglue command still want a user confirm.
