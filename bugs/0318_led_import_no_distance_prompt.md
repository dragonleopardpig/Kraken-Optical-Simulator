# 0318 — Importing an LED STEP should not prompt for a working distance

## Request
Follow-up to the 0317 LED work, from the user:

> *"we can remove the LED working distance prompt. Let user align themselves, the thickness overlay can
> be click --> change value --> physical change."*

Importing an LED STEP popped a modal (`_ask_led_edge_distance`, *"Distance from object plane to the
object-side LED box edge [mm]"*) **before** the body appeared, forcing the user to type a number they
would rather set by eye once they can see the scene. Everything the modal did is already reachable after
import — the LED drags freely along the axis, and the live Object→LED dimension is click→edit→physical.

## Fix — drop the import prompt, land at the auto default
`KrakenOS/UI/services/step_overlay_import.py` `import_led_step`:

- Removed the `_ask_led_edge_distance(...)` call and its *"LED STEP import cancelled"* early-out.
- The edge distance is now taken from the current `led_object_edge_distance_mm` (so a re-import keeps a
  distance already dialled in), falling back to the existing `_default_led_object_edge_distance()` (25% of
  the lens front datum, clamped; `0.0` for an LED-only scene) when none is set. Same knob, same default —
  just no modal in the way.
- The status line now reads *"...landed at N mm. Drag it along the axis or click the Object→LED dimension
  to change the distance."* so the alignment affordance is discoverable.

The **explicit** `set_led_edge_distance()` action (`scene_placement_commands.py`, invoked from the
menu/overlay) **keeps** its prompt — that is a user asking to type a number, not an import getting in the
way. The distance knob, its persistence (`layout_settings`), the live Object→LED dimension, and the
thickness-overlay click→edit path are all untouched, so nothing downstream regresses.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_led_import_no_distance_prompt.py` — **PASS**:
- **A** source wiring: `import_led_step` no longer references `_ask_led_edge_distance` and has no
  modal-cancel early-out, while `set_led_edge_distance` still prompts.
- **B** a stub-driven fresh import whose `_ask_led_edge_distance` **raises** returns the chosen path
  (never `None`), lands `led_object_edge_distance_mm` at the auto default, records the path, selects the
  LED, resets the pose knobs, and calls the modal **0** times.
- **C** re-import with an existing 42 mm distance preserves it (no surprise reset to default).
- **D** the default distance is finite and non-negative (LED-only scene → `0.0`).

Penta **phase 280** (`phase_280_led_import_no_distance_prompt`) delegates to the guard; baseline updated
(`"280": "pass"`).

## Files
- `KrakenOS/UI/services/step_overlay_import.py` — `import_led_step` drops the modal + cancel path, lands
  at the auto default, and updates the status line.
- `KrakenOS/UI/validate_open3d_led_import_no_distance_prompt.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_280`.
- `tools/penta_validator_baseline.json` — phase 280 baseline + title.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): Import LED STEP → the body appears immediately with no
  dialog; confirm the Object→LED dimension is click-to-edit and dragging the LED along the axis moves it.
- Sets up 0319 (one-click parametric BS overlay centered on the LED clear-aperture opening): with the
  import no longer blocking, the LED lands ready to overlay and glue a beam-splitter template onto.
