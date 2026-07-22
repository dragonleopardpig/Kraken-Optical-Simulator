# 0397 — add-BS plate STILL re-aims the camera (0396's coating check misses the real plate)

**Flag:** `flag_20260722_100739_675` — "quit Kitty, fresh restart, right click add BS plate
causes camera to re-orientate." Build bf974dab (= 0396), **fresh restart** (not stale).

## Why 0396 didn't fire on the real plate

0396 skips the follower repositioning when the solid has a **"Beam Splitter" interaction face**
(`_solid_has_beam_splitter_interaction_face`). That worked on synthetic plates, but the REAL
`add_beam_splitter_to_led("plate")` promotes an 85 mm plate that is first **rotated to match the
LED windows**, and that rotation is **baked into the promoted mesh**. So the coating's local
normal is no longer ~45° off the local +Z axis, and `_flag_beam_splitter_coating_face` (which
looks for the largest face ~45° off +Z) **never flags it** — the solid ends up with no "Beam
Splitter" face for the geometric check to find. The camera then folds onto the plate's tilted
output-face frame (verified from the flag: camera actor moved from `x[200,270]` onto the BS at
`x[-29,41]`).

## Fix — an explicit, coating-agnostic mark

A solid the user added *as a beam splitter* is definitionally a beam splitter — don't infer it
from fragile face geometry. `add_beam_splitter_to_led` now stamps the promoted row:

- `advanced["StepOverlayPromotion"]["beam_splitter"] = True` — stored inside
  `StepOverlayPromotion`, an advanced dict that IS preserved through save/reload (a bare
  top-level `advanced` key is whitelisted away by `_advanced_surface_attrs_from_spec`), so the
  mark survives a round-trip. A top-level `OpticalSolidBeamSplitter` key is also set as a
  live-session fallback.

`build_optical_solid_output_port_pose_overrides`'s non-folding guard now fires when the exit is
codirectional **or** the solid has a BS interaction face (0396) **or** the row is explicitly
marked (`_row_is_marked_beam_splitter`). So the camera never folds onto a BS the user added,
cube or plate, any tilt, flagged coating or not.

## Verification

- **Penta phase 26**, extended: an unflagged tilted plate WITHOUT the mark folds the chain
  (`[2,3]`, the bug); WITH the `StepOverlayPromotion.beam_splitter` mark it skips (`[]`), even
  with no coating. The mark survives `_row_from_layout_item` (save/reload). 0396's coating check
  still covers a manually-flagged BS; a MIRROR plate still folds; the real MV-150 BS-cube scene
  passes.
- **Note:** the full live `add_beam_splitter_to_led("plate")` can't run headless (the LED
  clear-aperture opening isn't detectable offscreen), so the mark's *end-to-end* effect owes an
  in-app eyeball; the mechanism (marked plate → no follower override) is proven.

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — stamp the BS mark on the promoted row.
- `KrakenOS/UI/nonseq_output_ports.py` — `_row_is_marked_beam_splitter` + the guard.
- `KrakenOS/UI/validate_open3d_beam_splitter_transmit_and_second_axis.py` — marker checks.

## In-app eyeball still owed

Add a BS plate to the LED — the camera should stay put (and stay put after save + reload).
