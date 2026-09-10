# 0766 -- the device is named in the machine's terms, not the box's

> "wait, I am now super confused with your definition of W, H and D. Can we clarify this?"
>
> "Can we change the wording to Length x Width x Thickness? Length is parallel to the top
> prism longest dimension. Width is the top prism gap direction. Thickness is the top prism
> short dimension."

The old labels named the BOX's own axes (`local x = W, y = H, z = D, front = +z`). They were
accurate and useless: nothing in them says which way the machine holds the part. In one
conversation the same device was entered three different ways, and I reproduced a flagged bug
against the wrong one twice -- a **depth** change moves the object row and a **width** change
does not, so the wrong guess sends the reproduction down a different code path entirely.

## The mapping

The stored keys do not change -- every saved scene carries them. Only what the user reads does.

| stored key | local axis | the user's name | defined by the machine |
|---|---|---|---|
| `width_mm`  | x | **Length L**    | along the top prism's LONGEST dimension |
| `depth_mm`  | z | **Width W**     | across the top prism GAP (one inspected face to the other) |
| `height_mm` | y | **Thickness T** | the top prism's SHORT dimension |

om05a inspects the FRONT and BACK faces, so `depth_mm` (**W**) is the separation between the
two inspected faces and each face presents `width_mm x height_mm` (**L x T**). The scene's
device -- "two 50 x 1 mm planes, separated 50 mm apart" -- is therefore **L 50 x W 50 x T 1**,
which is exactly the `width_mm 50, height_mm 1, depth_mm 50` already in the file. The data was
right the whole time; only the words were wrong.

Note the ordering trap this closes: **W is not `width_mm`.** The user's Width is the stored
`depth_mm`. A label bound to the wrong key silently rotates the device, which is why the guard
below asserts the pairing and not just the order.

## Changed

- The dialog reads **Length L / Width W / Thickness T**, in that order (the order bugs/0764
  introduced at the user's request -- "W, D then H" -- is the same order, now named properly).
- Its help text states the three directions in the machine's terms.
- The STEP-bounds status line reports `L x W x T` and says which STEP axis each came from.
- `inspection_part.py`'s header carries the key <-> bench mapping, so the next reader of
  `width_mm`/`height_mm`/`depth_mm` is not left to infer it.

## Not changed

The spec keys, the saved scenes, `_FACE_DEFS`, and every geometry helper. This is a naming
change; a data migration would put every existing scene at risk for no gain.

## Guard

`validate_open3d_0764_focus_snap_may_not_make_focus_worse.py` checks E5 (the three labels appear
in L, W, T order) and E6 (each label is bound to the RIGHT stored key -- `Length->w_var`,
`Width->d_var`, `Thickness->h_var`). E6 is the one that matters: getting that pairing wrong
swaps the device's axes without any visible error.

## Also in this commit (partial): the A5+C1 motor rail

> "The A5+C1 is where the motors can travel. The C1 here is up to the Edmund Filter of course."

`_motor_rail_from_lens_block()` reads the rail off the scene instead of hand-typed numbers: A5
is the gap in front of the lens block, C1 the gap behind it (which ends at the Filter, because
the Filter is the next row), so a motor may move by `delta` in `[-A5, +C1]`. On
`om05a_folded_80mm` it derives **rail 148.400 = A5 130.890 + C1 17.510** -- against the 90 mm
and 100 mm ranges I had guessed earlier, which match no feature of the machine.

It is wired but **inert**: `_camera_focus_stage()` fills in only what a scene omits, and the
80 mm scene states every key, so its stage is byte-identical. The production scene has no stage
at all (no `sensor standoff` row, and its A5 is merged into `RA mirror 1`'s 180.47 mm).

Still to do, and why it is not yet switched on:

> "I forgot to put an upper bound to A5+C1 (up to Edmund Filter), while both values can be
> zero, the max cannot exceed the original om05a_26_1_r03_2s_lr_asm.stp imposed."

The ceiling is the vendor STEP's own geometry, not the current gap values. Until that bound is
measured off the assembly, deriving limits from A5 and C1 alone would state a travel the
hardware does not have.

The call is guarded (`try/except` -> `{}`) for the bugs/0758 reason: it is read on every solve,
and a convenience that can raise there would take the whole conjugate solve down with it.
