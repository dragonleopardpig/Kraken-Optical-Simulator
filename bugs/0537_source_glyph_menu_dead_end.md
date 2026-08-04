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

## Round 2 (flag_20260804_115107 "right click seat still not functioning", build a1ee867e)

The matched-window replay of the recorded right-click (LED STEP F006, the housing wall)
shows the menu WITH "Seat Illumination LED 1 on This Face", and invoking it seats the
source correctly — the machinery works end-to-end headless; the live failure left no
forensics (menu-entry clicks are not recorded, the logs rotate on inspector init, and a
menu-command exception dies as a silent Tk callback error).

Hardening + discoverability so the next attempt cannot be silent or missed:
- both seat handlers wrap their bodies: any failure now prints "Seat ... failed: <reason>"
  in the status bar AND the debug log, and `_debug_trace` records every invoke;
- "Seat {name} on the LED floor (auto)" now appears in ALL THREE menus: the source
  glyph's menu, every LED face menu, and the browser's source right-click (next to
  "Edit Source…" — the place the user demonstrably works).
