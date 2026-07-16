# 0327 — LED clear-aperture opening is selected by screen-proximity to its closed loop

## Flag / redirect
After 0326 shipped (snap to the opening rim when the picked **cell** lands on the opening face) the
user re-recorded `flag_20260716_125803_837`:

> still the same, can't highlight the CA opening.

Then challenged the whole framing:

> Is there any discrepancy in your edge detection algorithm? by right, all closed edges should be
> detected if your algorithm is right.

That reframing is the fix. The edge detection is **not** broken; the *selection trigger* was.

## Root cause — the opening is a see-through hole, so the cell gate never fires
`kraken_step_selection_face_index == 266` (F267) is the object-facing window: a **wide** frame
(measured radius **46.9 → 59.8 mm ≈ 13 mm across**, not the ~2 mm I first mis-stated) with a
**see-through hole** punched through its centre and 13 screw holes in the frame. Its boundary is a
clean set of **14 closed loops** — one big aperture loop (396 verts, ~83 mm, closed, **0 dangling
ends**) plus 13 screw-hole loops. So detection is complete; the loop is right there.

The failure is geometric: 0326 gated the snap on the picked **cell** having face index 266. But the
window centre is empty, so a ray under the cursor passes **through** the opening and hits whatever is
recessed behind it. The flagged hover resolved `hover_step_cell_key = ('step','led','F005')` — a
3×2×5 mm sliver ~17 mm **behind** the opening — never face 266. No opening cell ⇒ the 0326 gate
correctly did nothing ⇒ "still can't highlight the CA opening." (The earlier "phantom highlight"
complaints are the same thing seen from the other side: a recessed face *did* light up because that is
what the ray hit.)

A 3D distance metric would be fooled the same way — F005 is the nearest **3D** hit, but it is not what
the user is pointing at.

## Fix — select the rim by SCREEN proximity to its closed loop
The opening rim is one **deterministic closed loop**, so make it a big forgiving target: on every STEP
hover, project that loop to the screen and snap to it when the cursor is within a pixel tolerance of
**any** rim segment — regardless of `cell_id` / whatever the ray hits behind the hole. Proximity is
measured in **screen space** (`depth_reference=None`): the recessed face is far in 3D but the rim it
hides behind projects **near** the cursor in 2D, which is exactly the edge being pointed at. On a hit
we still return the **whole-rim** edge feature (the gold ring from 0326's
`_clear_aperture_opening_edge_feature`), so the rendered highlight is unchanged — only *when* it fires
changed. The click inherits it (WYSIWYG) because it re-picks through the same path.

### Wiring
- **`_clear_aperture_opening_edge_pick(inspector, label, display_xy, tolerance_px=28.0)`** (new,
  `services/open3d_round_lens_pick.py`) — looks up the opening face index
  (`_clear_aperture_opening_face_index`, cached; manual pick wins else auto-detect top candidate),
  builds the rim outline (`_clear_aperture_outline` → `face_outline_from_face_indices`, cached
  topology), projects it with `inspector._world_to_display_2d`, and runs the existing
  `nearest_display_edge` (`depth_reference=None`) purely as a **hit test**. On a hit it returns the
  whole-rim `_clear_aperture_opening_edge_feature`. Guarded on both `_clear_aperture_opening_face_index`
  and `_world_to_display_2d` being callable, so test doubles fall through.
- **`step_feature_pick_for_display_xy`** — the 0326 face-cell block (which read
  `clear_aperture_face_index_for_display_cell` and required `cell_id >= 0`) is replaced by a single
  `_clear_aperture_opening_edge_pick(...)` call at the TOP. The `cell_id >= 0` gate is **dropped** —
  proximity works for right-click (cell −1) and wherever the ray falls through. Non-near cells return
  `None` and fall through to the normal per-cell pick for the rest of the body (still selective).

Reuses machinery already built for the Alt edge-refine (bugs/0317/0323): `line_segment_pairs`,
`nearest_display_edge` (per-vertex projection memoised → one projection per outline vertex per hover,
not per segment). `_clear_aperture_opening_face_index` / `_clear_aperture_outline` /
`_clear_aperture_opening_edge_feature` are unchanged from 0326.

The manual "Set Clear Aperture" pick mode (`_update_clear_aperture_hover_highlight`) is a different
path and is not affected.

## Verified (display-free + offscreen)
`KrakenOS/UI/validate_open3d_led_ca_edge_hover.py` — **PASS** (drives the real methods against the
cached analytic mesh with a light fake editor + a synthetic drop-`y` camera; no OCC, no GLX):
- **A** `_clear_aperture_opening_edge_feature("led", 266)` → face_id `F266`, overlay is a LINE loop
  (`n_lines=1172`, `n_polys=0`), finite centroid/normal (unchanged from 0326).
- **B** a cursor a few px off an actual rim vertex, with **no `cell_id`**, snaps to the rim edge —
  proving the snap is proximity-driven, not cell-driven.
- **C** selective: the projected **hole centre** (inside the see-through opening) and a far off-body
  cursor do **not** return the CA edge.

Offscreen proof `attachment/_ca_proximity_pick.png` draws the projected rim loop + the 28 px tolerance
band with a near-rim cursor (snaps, `d=0.0 px`) and a hole-centre cursor (no snap) — the "big
forgiving target vs falls-through" contrast.

Penta **phase 289** (`phase_289_led_ca_edge_hover`) delegates to the guard; baseline unchanged
(`"289": "pass"`, title updated for proximity). Phases 287/288 still pass.

## Notes / remaining
- **In-app eyeball owed** (needs a GLX display this box lacks): import the LED, move the cursor near
  the front-window rim from any angle — including over the see-through centre — and confirm the rim
  edge highlights and a click selects it.
- Tolerance is 28 px (vs 14 px for the Alt per-edge refine): the CA opening is meant to be a *large*
  forgiving target, not a per-pixel edge pick.
- Generalises for free to any STEP body with a detected CA opening (e.g. an LED-with-BS has **two**
  openings — bugs/0319); the per-loop nearest-of-many selection is a later step once this is confirmed
  live.
- Still paused (not touched here): the general fuzzy per-cell face/edge pick and the phantom whole-face
  fill (bugs/0325), and the Alt-live gremlin (bugs/0324).

## Files
- `KrakenOS/UI/services/open3d_round_lens_pick.py` — new `_clear_aperture_opening_edge_pick`;
  `step_feature_pick_for_display_xy` trigger replaced (proximity, no `cell_id` gate).
- `KrakenOS/UI/validate_open3d_led_ca_edge_hover.py` — guard reworked to test screen proximity
  (fake `_world_to_display_2d`; near-rim snaps with no `cell_id`, hole-centre / off-body do not).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_289_led_ca_edge_hover`
  wording.
- `tools/penta_validator_baseline.json` — phase 289 title (status still `pass`).
- `attachment/_ca_proximity_pick.png` — offscreen proof (gitignored cache).
