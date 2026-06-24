# 0127 — LED↔beam-splitter glue unreachable after the BS is promoted (and a confusing second "Glue …")

## Symptom

Two flags on the same machine-vision scene (an LED, an imaging lens, a camera, and
a beam-splitter cube that the user **promoted** to an optical solid, slid +27.5 mm
along the axis):

- `flag_20260624_085546_724`:
  > "the right click menu on LED now show glue to surrogate. I am not sure this is
  > correct term, LED should not glue to lens surrogate, anyway, I glue it. It takes
  > extraordinary long time."
- `flag_20260624_085743_911`:
  > "I notice there is a offset of BS to the LED after glue to surrogate. Then I drag
  > the LED, LED and BS separated, proving that they are not glued."

So: the only glue-looking item on the LED was **"Glue STEP to Surrogate"**, the user
took it for the BS↔LED glue, it ran long, and afterwards the two bodies were *not*
rigidly glued — dragging the LED left the BS behind.

## Root cause

Two distinct, unrelated actions both read as "Glue …":

1. **"Glue STEP to Surrogate"** — `glue_step_overlay_to_surrogate(label)`. It zeroes an
   overlay's drag offsets to snap it back to its auto-station (LED→object station,
   lens→surrogate, camera→Image plane) and `refresh_from_editor(force_retrace=True)`.
   It is **not** a two-body glue. (The "extraordinary long time" was the forced
   retrace — the 0126 launch-pupil explosion, fixed separately.)
2. **"Glue BS to LED (move together)"** — `set_optical_led_glue(True)` / the
   `_optical_led_glued` rigid two-body glue.

The actual BS↔LED glue had become **unreachable** on this scene. Both the glue gate
(`set_optical_led_glue`) and the menu-availability predicate
(`_optical_led_glue_available`) required the **"optical" *and* "led" STEP overlays**.
Promoting the beam splitter **removes** its "optical" overlay (it becomes a promoted
solid *row*), so:

- the "Glue BS to LED" item disappeared from the menu, and
- even if called, `set_optical_led_glue(True)` would refuse ("both STEPs imported").

With the real glue gone, the user fell back to the misnamed surrogate reset, which
moves only the LED and never bonds it to the BS — hence "they are not glued".

## Fix

**Recognise a promoted BS as a glue partner.** A beam-splitter *body* is now either
the "optical" overlay **or** a promoted optical solid row:

```python
def _optical_bs_body_present(self) -> bool:
    if self._step_path_for_label("optical") is not None:
        return True
    return self._promoted_optical_solid_row_index("optical") is not None
```

- `set_optical_led_glue` gates on `_optical_bs_body_present()` (+ the LED), not both
  overlays.
- `_optical_led_glue_available` (menu) returns True for an LED overlay plus a BS body
  (overlay **or** promoted row).
- The promoted-row right-click also offers **"Glue BS to LED (move together)"** (via
  `_row_is_glueable_optical_bs`), so the user can glue where they see the body — the
  mirror of the existing "Unglue BS from LED" on that row (bugs/0103).

**Make the glue HOLD across every drag path.** One re-entrancy-guarded carry,
`_carry_glued_optical_led(moved_label, applied)`, moves the glued partner by the same
world delta. The partner may be an overlay (LED → direct offset) or a promoted row
(BS → `translate_scene_row_pose_vector`). It is wired into all three translate
primitives:

- `translate_step_overlay` (overlay drag — LED, or a still-overlay BS),
- `translate_scene_row_pose_vector` (xyz drag of the promoted BS row),
- `translate_scene_row_pose` (per-axis drag of the promoted BS row).

The two row primitives call it **behind** `_optical_led_carry_active`, so when the LED
move carries the BS row, the row primitive does **not** carry back to the LED (no
double-move). The LED-side carry only sets an overlay offset, so it never re-enters.

**Stop the two-"Glue" confusion.** The surrogate-reset item is relabelled per element
by `_step_surrogate_reset_label`: LED → "Reset LED to Object Station", camera →
"Reset Camera to Image Plane", optical → "Reset BS to Auto Placement" (others keep
"Glue STEP to Surrogate"). It no longer reads as a second "Glue …" beside the real
BS↔LED glue.

## Test

`KrakenOS/UI/validate_open3d_led_bs_glue_promoted.py::run_checks` — display-free; binds
the real `ScenePlacementMixin` glue/carry methods onto a light fake editor:

- **A** a promoted BS (row "optical") + LED overlay → `_optical_bs_body_present` True,
  `set_optical_led_glue(True)` succeeds, and `_optical_led_glue_available` True;
- **B** no BS body at all → glue refused; **C** no LED → glue refused;
- **D** dragging the promoted BS row carries the glued LED overlay by exactly one
  delta (never doubled);
- **E** dragging the LED carries the glued BS row by one delta, and the re-entrancy
  guard stops the row primitive carrying back to the LED;
- **F** an unglued scene carries nothing on either path;
- **source contract** — all three translate primitives route through
  `_carry_glued_optical_led` (the row primitives behind `_optical_led_carry_active`),
  the gate consults `_optical_bs_body_present`, and availability consults
  `_promoted_optical_solid_row_index`.

The label change is also pinned by the two existing menu guards
(`validate_open3d_tree_element_context_menu`, `validate_open3d_glue_unglue_indicator`).

Penta **phase 118** runs this guard. Mutation-tested: reverting the gate to the old
both-overlays form flips A (glue refused) + the gate source check; neutralising the
`translate_scene_row_pose_vector` carry hook flips D (LED no longer follows) + the
re-entrancy source check.

## Note — in-app eyeball owed

Headless can't drive the embedded-VTK right-click pick or the live drag, so the
visible menu wording, the "Glue BS to LED" item appearing on the promoted body, and
the two bodies actually moving together are verified in-app. The guard pins the gate,
availability, the carry math, and the menu-label expectations.
