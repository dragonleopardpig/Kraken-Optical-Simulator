# 0768 -- the part dialog specifies the geometry and the required FOV, nothing else

> "can we remove the offset text input box? Uneccessary for user to input."
> "and the Axis reach, what is that?" ... "user need to input?"
> "even the Inspected Face (on the object plane) dropdown, I don't think we need this as well.
> We need to specify the geometry and the required FOV."

Three of the six inputs were not the user's to set, and one of them was actively causing the
"device decentered" reports.

## Face offset along axis -- was a bug source, not just clutter

`axis_offset_mm` is **derived**: it is what keeps the part centred in the prism gap as its Width
changes. The gap centre is hardware (`mirror_launch_plane_z = -25`, fixed for the life of the
scene), so the offset must satisfy

```
offset = Width/2 - 25          W 50 -> 0,  W 30 -> -10,  W 20 -> -15,  W 25 -> -12.5
```

and the app maintains it by adding `(near_z - near_z_old)` on every Width change. That telescopes
correctly **only if every step starts from the current value**. The widget did not: it was
initialised when the dialog was *opened* and re-submitted that same number on every Apply, so
after the first change the arithmetic was fed a stale offset and the device drifted off the gap
centre. Measured, feeding the live value at each step centres the box at z = -25.000 for
W = 30 -> 20 -> 25 -> 50 -> 30; re-submitting a stale one does not.

Removing the widget removes the conflict at the root: the app owns the value, and `_read()` takes
it from the live spec.

## Axis reach -- no optical effect at all

`axis_reach_mm` sets how far the six dashed blow-out guide axes are **drawn**
(`0 = auto = max(80, 2.5 x the largest dimension)`). Nothing else reads it.

## Inspected face -- never a choice here

The split field images the FRONT face and its mirror image on the BACK. `active_face` stays in
the spec (scenes carry it, and the six blow-out axes need it) but it is not a control.

## The dialog now

`Show the 3D part` | **Length L** | **Width W** | **Thickness T** | **Required FOV** | Part STEP

Verified by building it: five input widgets, and `active_face`, `axis_offset_mm` and
`axis_reach_mm` all preserved in the spec and read from the live spec -- which is exactly what
lets the auto-centring keep telescoping.

## Guard

`validate_open3d_0764_...` E5/E6: the three dimension labels appear in L, W, T order, and each is
bound to the RIGHT stored key (`Length->width_mm`, `Width->depth_mm`, `Thickness->height_mm`).
E6 is the one that matters -- a label bound to the wrong key silently rotates the device, with no
visible error (bugs/0766).
