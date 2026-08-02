# 0512 — glue the illumination source to the LED so assembly drags carry it

Flag `flag_20260802_204536_858` ("dragged to BS, LED follows, but the
Illumination source is not followed"), scene `machine_vision_150mm_test.py`,
build `117f75dc` — immediately after 0508 B landed: the BS assembly drag moves
the LED housing, but the first-class parametric emitter (bugs/0283 family) is a
world-anchored spec (`origin` / `source_x..z`) that nothing carried.

## Fix

* Spec key **`glued_to_led`** (persisted; `normalize_scene_source_specs` is a
  passthrough so it survives save/reload untouched). New
  "Add Illumination Source (LED)" emitters default to glued -- they are seeded
  from the housing; a free-placed source (illuminate from another angle) stays
  ungluable by right-click.
* **`_carry_glued_scene_sources(delta)`** (source_modeling.py): shifts every
  glued spec's origin (both storage forms) by the LED's world delta; caller owns
  history + rebuild, mirroring the BS half of `_carry_glued_optical_led`.
* Wired at every LED-motion chokepoint (scene_placement_commands.py): the
  atomic station write's LEG component + the perpendicular carry remainder
  (their sum = the LED body's full delta -- and via the 0508 B delegation this
  covers the BS assembly drag for free), the `_carry_led_glue_over_translation_change`
  distance-dialog movers, and the `_reset_led_to_reference` glue-restore.
  Independent of the BS<->LED glue flag.
* Browser right-click on a source row: **"Glue Source to LED (move together)" /
  "Unglue Source from LED"** via `update_scene_source_spec`
  (`glued_to_led` added to `SCENE_SOURCE_EDITABLE_KEYS`).

## Verification

Headless on the flagged scene: new source glued by default; LED drag (7,0,-4)
carries the origin exactly; after gluing BS<->LED, a USER BS-row drag (+5,0,0)
carries it too (the 0508 B delegation path); unglued source stays put;
normalization round-trip keeps the key. Guard
`validate_open3d_0512_source_glue_rides_led` = penta phase 413 (portable fake
carry checks + the real-scene workflow, skip-if-absent).
