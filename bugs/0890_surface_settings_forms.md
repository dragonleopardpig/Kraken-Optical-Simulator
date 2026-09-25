# 0890 -- two small dialogs that needed nothing new

The galvo scan overlay (the TiltX angles a mirror is *drawn* at) and the grating fields (order,
pitch, line angle) that no longer occupy main-table columns. `main_surface_settings_dialogs.py`
219 -> 76 lines.

These are the first pair in the phase-3 tail that needed **nothing new from the framework** --
which, ten family properties in, is what the tail is supposed to look like.

## What moved into the model

- the overlay is **seeded from the mirror's own displayed angle**: `nominal-5, nominal, nominal+5`;
- **25 angles maximum**, "to keep the plot readable";
- the **middle** value becomes the nominal pose (`tilt_x`, converted from display to local through
  the branch angle) while the whole list goes to the display-only overlay. That rule used to live
  in a Tk callback;
- the two refusals -- no row selected, and a row that is not a Mirror -- still go to the **status
  line**, not a message box, exactly as before. The panel catches `FormRefused` and sets
  `status_var`.

All four pieces of the galvo model reach the Tk shell as **constructor kwargs**
(`galvo_scan_overlay_key`, `format_float_sequence`, `parse_float_sequence_text`,
`short_error_message`), so `model(owner)` falls back to `layout_editor` and
`services/surface_value_parsing` -- the same split every row form has hit.

## Guard

`KrakenOS/UI/validate_open3d_0890_surface_settings_forms.py` (penta phase 678):

- **G** -- seeded `[85, 90, 95]` around the mirror's own 90 deg; 101 angles refuse and so does
  unparseable text
- **N** -- the middle angle became the nominal pose and all three went to the overlay
- **G2** -- Clear emptied it
- **R** -- both refusals carry their own message
- **T** -- "Pitch [um] expects a number.", "Pitch [um] must be non-zero."; apply wrote the pitch
  and the order
- **D** -- the REAL Tk dialogs drew `['Validate', 'Apply', 'Clear', 'Cancel']` over 1 entry and
  `['Validate', 'Apply', 'Cancel']` over 3
- **Q** -- both Qt dialogs the same

`om05a_folded` has no Mirror row -- its folds are promoted solids -- so the guard makes one in
memory rather than pinning itself to a scene that might change.
