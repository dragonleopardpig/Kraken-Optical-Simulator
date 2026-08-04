# 0536 — the source gizmo trio: 1 FPS drag, un-hoverable arrows, no way to seat on the floor

## Reports

flag_20260804_102722 + live messages: (a) "the drag gizmo for LED is very lag, not smooth
at all"; (b) "hover the gizmo not highlighting the arrow, background STEP got highlighted
instead"; (c) "the created LED illuminator is slanted at unknown angle, there is no
rotation gizmo — better way to (1) resize (2) snap it to the LED floor?"

## (a) The lag was the DISPLAY STACK, not the drag path

The 0426 arrow drag already used the cheap deferred-commit path — but the LIVE app's
every VTK render measured a constant ~1013 ms while the identical scene renders in
~125 ms headless. That constant is Mesa blocking its full 1 s frame-callback timeout:
under Hyprland/XWayland the compositor withholds frame callbacks from the (partially
occluded — the browser panel overlaps it) 3D surface. Fix: the app entry sets
`vblank_mode=0` (Mesa) and `__GL_SYNC_TO_VBLANK=0` (NVIDIA) — a CAD viewport renders on
demand and must never wait on vblank. Diagnosed with `sudo py-spy dump` on the live PID.

## (b) The arrows were missing from the hover pick set — the 0019 lesson again

`_passive_hover_pick_rotation_handle` gained `_actor_source_move_map`, and
`_on_mouse_move` gained the source-arrow branch: gold affordance on the arrow, no face
highlight underneath, hint in the status bar.

## (c) Seat on the LED floor

The 0363 "Seat {source} on This Face" glue existed ONLY on promoted-solid faces; the LED
housing floor is a decoration STEP face, so the one place the emitter belongs never
offered it. The decoration face menu now lists every scene source, and the handler aims
the emission TOWARD the splitter (fallback: the object row) instead of 0363's blind
−normal, so either side of the floor face works; origin gets a 0.5 mm standoff off the
PCB. The slant itself is the 0290 seeding (aimed at the imaged FOV) — one seat gesture
replaces it. Resize remains the browser's per-source "Edit Source…" (radius_x/radius_y);
a rotation gizmo stays a follow-up (the seat covers orientation).

## Guard

`validate_open3d_0536_source_gizmo_usability.py` (penta phase 430): vblank guards in the
entry, arrows in the hover set + hover branch, decoration-face seat menu, and the REAL
seat drive (origin standoff, toward-splitter aim, bogus-id not-found).
