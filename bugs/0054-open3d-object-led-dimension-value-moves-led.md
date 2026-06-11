# 0054 — Open 3D: editing the object→LED dimension value moves the LED body

## Motivating bug (user's words)

> changing the thickness to 200 does not move the LED. (Instead it silently
> changed to 275)

(Recording `attachment/recorded_bug_repros/flag_20260611_084621_151/`.) The user
re-anchored the object→LED distance (the `S0` dimension) onto the LED's bottom
face — the magenta arrow read **"S0 measured = 212.593 mm"** — then opened the
inline value editor to set that distance to **200 mm**, expecting the LED to move.
Two things were wrong:

1. The inline editor pre-filled **275** (the model object gap `rows[0].thickness`,
   = the object→lens distance), **not** the 212.6 mm measured distance the user
   clicked. That is the "silently changed to 275".
2. Committing the edit did **not** move the LED. The re-anchored end sits on the
   LED *body*, which is not an optical surface, so the bugs/0053 move path mapped
   it to no row and refused — nothing happened.

This is the LED follow-up flagged at the end of `bugs/0053`: there, editing a
re-anchored value was wired to move the *Next optical element* by editing the
single upstream gap. The object→LED row is different — the LED is the imaged
**object**, a STEP body positioned independently of the sequential surface rows,
so it must be moved by its own placement knob, not by an optical gap.

## Fix

Two changes, both scoped to a re-anchored **object→LED** dimension (`S0` with an
imported LED). Optical thicknesses are never touched.

- **Move the LED, not a gap** — in `scene_placement_commands.apply_reanchored_dimension_value`,
  when the moved endpoint maps to no optical surface *and* it is row 0 with an
  imported LED, route to the new `_move_led_for_reanchored_value`. The LED's
  object-side placement (`led_object_edge_distance_mm`, the same knob the
  "LED Edge Distance" dialog drives) is shifted by the span delta
  `delta_z = (fixed_z ± value) − ref_z`, which rigidly translates the whole STEP
  so the *measured face* lands at the typed object distance. The override's
  `ref_z` follows the body so the arrow stays attached and reads the typed value.
  It refuses (model untouched, status note) when the move would put the LED behind
  the object plane (`led_object_edge_distance_mm < 0`).
- **Prefill the measured value** — in `open3d_thickness_dimensions.edit_dimension`,
  when the row has a re-anchor override, the entry pre-fills the measured distance
  `|ref_z − fixed_z|` (what the magenta arrow shows and what the move targets)
  instead of `rows[row_index].thickness`.

**Semantic:** this moves the LED *body* (its CAD/visual placement) so the measured
face is at the chosen object distance. It does **not** change the optical object
gap `rows[0].thickness` — that conjugate distance stays the plain-S0 quantity,
edited via the non-re-anchored inline-edit path. The two are deliberately separate:
the re-anchored dimension is a measurement to a CAD face, and satisfying it moves
the CAD body, never the optical model.

## Why the LED knob works

`_led_step_z_translation()` returns `led_object_edge_distance_mm − led_step_object_edge_local_z`
(or just `led_object_edge_distance_mm` when no edge is locked), so
`d(translation)/d(led_object_edge_distance_mm) = 1`: adding `delta_z` to the knob
translates the entire LED body by exactly `delta_z` along z, regardless of which
face was picked or whether an object edge was locked. Moving the body by the delta
needed to bring the picked face from `ref_z` to `fixed_z ± value` therefore lands
that face exactly at the typed distance.

## Tests

- `KrakenOS/UI/validate_open3d_dimension_reanchor.py` — display-free, two added
  checks: (a) `_test_object_led_value_edit_moves_led_body` — with an LED imported,
  an `S0` "end" override onto an off-surface z (the LED face) and a value edit
  moves `led_object_edge_distance_mm` by the span delta, leaves every
  `rows[i].thickness` unchanged, follows the measured face, and refuses a move that
  would push the LED behind the object plane; (b)
  `_test_edit_dimension_prefills_measured_value` — `edit_dimension` consults the
  override and prefills the measured value before building the entry.
- Phase 59 in the comprehensive validator
  (`phase_59_object_led_dimension_value_moves_led`) — boots the editor, fakes an
  imported LED, stores an `S0` "end" override, edits the value through the real
  `apply_dimension_value` path, and asserts the LED edge distance moved by the
  delta, no optical thickness changed, the face followed, and the prefill contract
  holds. Added to the baseline (60 phases, 0–59).

## Notes / follow-up

- Detection of "the re-anchored end is on the LED" is row 0 + an imported LED (the
  object→LED row). If the user instead re-anchors `S0`'s end onto a real optical
  surface, the optical-surface mapping catches it first and moves that element
  (bugs/0053), so the LED branch only fires for the genuine LED case.
- The override stores absolute z's (`ref_z`, `fixed_z`); they go stale if an
  upstream gap later changes. For the object→LED row the object plane is the global
  z origin (stable), so this is robust here; a general absolute→relative re-basing
  is a separate follow-up shared with bugs/0053.
