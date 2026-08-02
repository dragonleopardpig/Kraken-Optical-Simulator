# 0504 — the LED was the last label on the destructive glue path

bugs/0497's closing note, now closed: *"the LED takes the same destructive zeroing path and wants
the same treatment."* No flag yet — fixed pre-emptively because the user's active scene is a loaded
landmine: on `machine_vision_AZ85_RA_Mirror_BS.py` the LED's seated placement offset is
`[-8.93, 0, -29.15]`, so one right-click glue would have zeroed it, thrown the housing ~30 mm off
its seat, and stranded it there (`already_glued` meant "offset is zero", refusing every retry) —
the identical failure bugs/0475 fixed for the camera and bugs/0497+0503 for the lens.

## Fix

`glue_step_overlay_to_surrogate("led")` now routes through `_reset_led_to_reference()`:

* restore the recorded reference placement (`step_glue_reference_offset_xyz`, seeded from the
  saved layout like every other label since 0497) instead of zeroing;
* "already glued" is expressed against the reference, so a seated LED reports no move and a
  displaced one can always be recovered;
* a body with NO recorded reference falls through to the legacy zeroing, where zero genuinely IS
  the unfolded auto station.

Unlike the lens, no datum anchor is needed: the LED's placement offset rides ON a base transform
that already tracks the object-distance machinery (`_led_step_z_translation`), so the recorded
offset stays meaningful when that base moves.

**The restore carries the glued BS back.** The drag that displaced the LED carried the beam
splitter along (asymmetric parent/child glue, bugs/0437: LED move carries BS, BS move never drags
the LED) — so a glue that moved only the LED would tear the assembly the drag kept together. The
restore hands `_carry_glued_optical_led("led", delta)` the same delta, and sets
`_fold_carry_pending_rebuild` since the carry may move a PROMOTED BS row (the bugs/0503 lesson;
the menu path's `_apply_model_change` consumes the marker anyway).

## Guard

`validate_open3d_0504_led_glue_restores_reference.py`, penta phase 406: seeded non-zero reference;
glue on the seated scene is a no-op (the old path moved it ~30 mm); LED drag carries the BS; glue
restores LED **and** BS exactly (residual 0.000000 mm); second glue no-ops; the reference survives
the settings round trip.

## Related still open

bugs/0500 (lens STEP orientation at import) — a flip must also update the 0497/0503
reference+anchor pair, or glue will restore the pre-flip pose.
