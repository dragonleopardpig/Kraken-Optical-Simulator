# 0404 — Replace a promoted optical solid (RA mirror) in place

**Feature (backlog, user-chosen):** "delete/import the RA mirror on the spot." Chosen scope (via
AskUserQuestion): the **promoted optical solid** path first (the RA mirror is a promoted solid, the
harder case), before the STEP-overlay path (camera/BS).

## Why the RA mirror is the hard case

In the AZ85 scene the RA mirror is a **promoted optical solid** — imported STEP → promoted into a
surface row carrying a baked STL cache, a pose (`Desp`/`AxisMove`), and an authored `Mirror` face flag
(`optical_step_path` is empty because promotion consumed the overlay). A fresh promotion does **not**
auto-flag the mirror (only same-part re-import does, via bugs/0214 `_carry_over_same_part_mirror_face`),
so a replacement must **capture and re-apply** the authored face functions.

## Fix

**`replace_promoted_optical_solid_step(row_index, new_step_path)`** (service, with an editor mixin
wrapper) composes the already-tested ops:

1. **Capture** the old solid's authored face functions (`OpticalSolidFaces` metadata) **before**
   unpromote — unpromote deletes the row, so order matters.
2. **Unpromote** → the STEP overlay is restored at the solid's current (possibly slid) pose.
3. **Swap the overlay's STEP path** to the replacement, **preserving** the pose (rotation / axis
   offset / placement offset are left untouched — exactly like Swap Imaging Lens keeps a swapped lens
   where the user aligned it) + mirror the import-time cache invalidation so the new geometry loads.
4. **Re-promote** → the replacement lands at the same pose.
5. **Re-apply** the captured authored functions via the pure planner
   `plan_face_reassignments_for_replace(old_faces, new_faces)`:
   - exact `face_id` (same part re-imported) with an area cross-check;
   - else geometry — the unclaimed new face whose outward normal best aligns (`|dot| ≥ 0.7`, so a
     flipped normal on re-import still matches) tie-broken by area closeness (the RA mirror's
     reflecting hypotenuse). Two authored faces never collapse onto one.
   - No confident target → the function is **reported for a manual re-flag**, never mis-assigned.

**Menu:** right-click a promoted optical solid → **"Replace STEP…"** (next to "Unpromote"), in both
promoted-solid branches of `append_element_context_actions`; the handler prompts for a STEP file and
calls the editor's replace method.

### The mixin-wrapper trap (again)

The method first landed only on `StepOverlayPromotionService`, so `hasattr(editor, ...)` was False and
the right-click would silently no-op through tkinter `__getattr__`. Per
`reference_editor_mixin_service_wrappers`, a service method the UI calls on the editor needs an explicit
editor wrapper that delegates to the service — added next to the `promote_`/`unpromote_` wrappers.

## Verification (`validate_open3d_replace_promoted_solid`, penta phase 331)

Display-free: pure-logic on the planner + getsource wiring/ordering guards.

| check | asserts |
|---|---|
| MATCH | id / geometry / flipped-normal match; no-match reported (not mis-assigned); authored-only; no collapse |
| SERVICE | captures faces BEFORE unpromote, then unpromote→set path→promote→re-apply; pose preserved (no rotation/offset reset) |
| WRAPPER | the editor exposes the method and delegates to the service (mixin-wrapper trap) |
| MENU | "Replace STEP…" in both promoted-solid branches; handler → editor's replace method |

4/4 pass; baseline records phase 331 = pass.

## Files

- `KrakenOS/UI/services/step_overlay_promotion.py` — `plan_face_reassignments_for_replace` (pure) +
  `replace_promoted_optical_solid_step` (service).
- `KrakenOS/UI/services/scene_placement_commands.py` — editor mixin wrapper.
- `KrakenOS/UI/services/open3d_face_assignment.py` — "Replace STEP…" menu entry + handler.
- `KrakenOS/UI/validate_open3d_replace_promoted_solid.py` — guard (phase 331).

## Scope / next

- The **STEP-overlay** replace (camera / BS / optical STEP overlays — swap the path, no promote round
  trip) is the natural follow-on now that the harder promoted path is done.
- Replace is composed from unpromote + promote, so **undo unwinds it in stages** (not one transaction) —
  a single-transaction refinement is possible later.

## In-app eyeball still owed

On the AZ85 folded scene: right-click the RA mirror → "Replace STEP…" → pick another right-angle-mirror
STEP → it should appear at the same pose, still folding as a mirror (status reports the re-applied
Mirror face, or names it for a manual re-flag if geometry differs a lot). The end-to-end mesh round-trip
(unpromote → re-promote on a real STEP) is what the eyeball confirms — the headless guard covers the
face-rematching logic + wiring/ordering.
