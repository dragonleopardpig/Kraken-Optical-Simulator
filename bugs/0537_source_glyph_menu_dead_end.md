# 0537 — "right click seat LED 1 is not working" (the glyph is not a face)

## Flag + recording

flag_20260804_110017 with a full recording: one right-click at the amber emitter plate,
18 s of reading, then the flag. Replaying the click headless produced NO menu at all —
"Right-click a CAD/STL optical face to assign its surface function." The user's natural
gesture (right-click the THING to seat) hits the source GLYPH, which is not a CAD face,
so the 0536 seat entry (which lives on the FACE menu) was unreachable. The LED floor is
also unreachable by face pick from outside — the ray stops at the outer wall.

## Fix

1. `_maybe_show_scene_source_menu` — the context-None branch offers the source's own
   menu before dead-ending: "Seat on the LED floor (auto)" + "Select (raise move gizmo)".
2. `_seat_source_on_led_floor_auto` — resolves the floor geometrically: the LED body's
   bounding face farthest OPPOSITE the object direction, emission aimed back toward the
   object (through the splitter), then the 0536 seat (0.5 mm standoff, toward-splitter
   aim). Verified: origin lands on the housing floor plane (z≈142.7 on AZ85) aiming at
   the object; the gizmo remains for fine adjustment.

Also fixed en route: the 0536 edit had swallowed the `_seat_source_on_face_from_context`
def line (its body was absorbed into the new method); restored.

## Guard

`validate_open3d_0537_source_glyph_menu.py` (penta phase 431): glyph menu wired before
the dead-end (fake-picker drive) + the auto seat's far-plane/aim assertions.
