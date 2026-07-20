# 0373 — Imported lens is reversed in direction; add a persistent flip

**Flag:** 20260720_142700_586 (build 7e3fd67c) — "The imaging lens imported is reversed in direction.
How to prevent this in future?" (The 0372 fix put the Apo-Rodagon on-axis; its front/rear then read
reversed.) **Status:** SHIPPED 2026-07-20 (guard `validate_open3d_lens_step_flip_direction`, penta
phase 314).

## Why it happens (and why it can't be fully auto-prevented)

A **mechanical** lens STEP carries no optical metadata — nothing says which end is the FRONT (object
side). The importer's alignment pins `front_face="max"` (the axial-max barrel end) at the front datum;
that is a *guess*. When the CAD's optical front is the other end, the barrel imports reversed. The
Apo-Rodagon is also optically **symmetric** (datasheet SF = −44.2, S'F' = +44.2), so even the optics
don't disambiguate direction. There is no reliable geometric signal, so full auto-prevention isn't
honest — the robust answer is a one-click flip that STICKS.

## The fix — a persistent flip

`lens_step_reverse_direction` (bool, persisted with the layout via `layout_settings` save/load,
initialised in `layout_editor`). The lens overlay builder maps it to
`front_face = "min" if reverse else "max"` — which **re-pins the OPPOSITE end at the front datum**,
so the lens faces the other way while staying correctly placed axially (verified: the front-datum
element radius swaps 15.8 ↔ 21.9 mm, both keep the front at the datum z — unlike a 180° rotation,
which would move it). The reverse flag is in the transformed-mesh cache signature, so the flip is a
render-only re-mesh (no retrace).

UI: right-click the imported lens overlay (3D canvas or the Scene Components tree) →
**"Flip Lens Direction (front/rear)"** — a direct command (no cascade, per the bugs/0320 VTK-menu
lesson) that toggles the flag and re-renders. `toggle_imported_lens_step_direction()` guards the
no-lens case with a status line.

**Prevention going forward:** flip it once; the setting is saved with the layout, so it never reverts.
