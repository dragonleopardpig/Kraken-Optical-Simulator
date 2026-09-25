# 0892 -- the last two tail dialogs

The tolerance-solve preset **chooser** and the parametric **beam-splitter resize**. Both small;
both with one decision worth keeping.

## A dialog that skips itself

`open_apply_tolerance_solve_preset_dialog` never opened when the layout held exactly one preset
-- there is nothing to choose. That shortcut is preserved, and it now runs through the **very
same `apply_preset()`** the dialog's Apply calls, so the two cannot drift apart:

```
S: one saved preset applies with NO dialog, through the shared path
   ("Applied tolerance solve preset 'Only'. Click Upd...")
```

The shortcut stays in the panel, because "do I need to ask?" is a view question; *what applying
means* is the model's, and that is what moved.

## Fields that depend on the row

A **cube** beam splitter takes one number (side); a **plate** takes four (width, height,
thickness, tilt). The model reads `beam_splitter_resize_info` and builds the form to match,
rather than a view branching on a kind it would have to understand. A refusal still goes to the
**status line**, as it always did.

Its error wording is the model's, down to the shape:
`side_mm` -> `"side: enter a number."`

## Guard

`KrakenOS/UI/validate_open3d_0892_tail_forms.py` (penta phase 680):

- **A** -- with none saved the chooser refuses; with two it offers both and Apply reports
- **S** -- the one-preset shortcut applies with no dialog
- **R** -- a cube form has 1 field and a plate 4, with "side: enter a number."; a non-parametric
  row refuses
- **T** -- the REAL Tk chooser opened on `'Alpha'` with `['Alpha', 'Beta']`
- **Q** -- the Qt chooser offered both and left the chosen one active

`om05a_folded` has no parametric beam splitter, so the cube/plate branch is driven through
stand-in owners whose `beam_splitter_resize_info` returns each kind -- the branch under test is
the model's, not the scene's.

## Phase 3's dialog tail is done

What remains of phase 3 is `main_atmosphere_panel` (reclassified in 0891 as a live-variable
*panel*, not a dialog) and the LED-edge-distance and system-selection prompts, which are
one-field asks rather than dialogs.
