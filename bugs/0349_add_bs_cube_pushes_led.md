# 0349 — "Add BS Cube" pushes the LED away; BS must seat at the crossing of the two CA-window axes

## Flags

- `flag_20260717_212643_040` — *"right click snap successfully."* (bugs/0348 confirmed in-app;
  the LED's CA snapped to (0,0,70.8936), normal −Z, `feature_normal_axis_snap` anchor recorded.)
- `flag_20260717_212714_748` — *"Unfortunately, right click add BS cube push the LED STEP away.
  Misplacement of the 2 elements. BS cube should respect both sides of CA and orientate the BS
  automatically accordingly."* Recording `recording_20260717_212904.json`: exactly ONE action
  between the flags — right-click → **Add Beam Splitter to LED (Cube)**.

User clarification (mid-fix): *"given optical axis, CA opening on both sides, perpendicular to
each other, I believe the BS cube or plate should be able to orientate and align properly,
overlapping and glued to the LED."* The coaxial LED (OPT-CO90) has TWO clear-aperture windows,
perpendicular; the BS belongs INSIDE the housing where the two window axes cross — overlap with
the LED is the vendor cavity, not a collision.

## What the recording shows (decoded arithmetically)

- Auto-detect ranked the **side window** (face 266, centroid (0, 45.5, 28.39), normal +Y) first —
  NOT the through window the user had just snapped on-axis at (0,0,70.89).
- `add_beam_splitter_to_led` then `set_step_clear_aperture("led", 266)` +
  `center_clear_aperture_on_optical_axis("led")` → translate Δ = (0−0, 0−45.5, 0) = **(0, −45.5, 0)**
  — exactly the recorded LED placement change (−20.9095 → −66.4095 in Y). The "push" was the flow
  re-centering the WRONG window, un-doing the user's alignment.
- The cube (side 85, from the side window's span) was placed with
  `_set_step_placement_offset_xyz("optical", (0,0,opening_z=28.39))` under a comment claiming the
  template is origin-centred. It is not, in overlay space: the STEP overlay import re-bases every
  body to front = min-z at z = 0, so placement z is the cube's BASE → recorded promoted bounds
  z 28.39..113.39, center 70.89. No orientation from the window normals at all.

## Fix (`KrakenOS/UI/services/scene_placement_commands.py`)

- `_led_beam_splitter_openings()` (replaces `_led_beam_splitter_opening_plan`): gathers ALL
  openings (auto-detect + persisted manual record), outward-signed normals, ordered by
  (distance from the global optical axis, normal-parallel-to-axis, detect rank) — the user's
  aligned THROUGH window sorts first, its perpendicular partner second.
- The orchestration additionally trusts the **CA-snap axis anchor** (`_step_overlay_axis_anchor`,
  written by `feature_normal_axis_snap`): an anchor matching a detected opening selects it; an
  anchor with NO detected match becomes a **synthetic through window** (centroid = anchor target,
  normal = anchor direction) — no CA persist, no centering, so the LED cannot move (it is on-axis
  by construction). This covers the flag exactly: only the side window survived auto-detect.
- Seat + orient: through-axis (template +Z) aligned along −n̂_through; diagonal fold axis
  (template +X) aimed at the side window's normal — light entering from the side window exits
  along the through window's outward normal. Seated **by measurement** (transformed-mesh centre →
  target), never by the origin-centred assumption:
  - two perpendicular windows → target = `_line_line_meet_point` of the two window axes (the
    vendor BS cavity centre; overlapping the housing, then glued);
  - single window → the 0319 semantics (BS centred on the opening).
- Sized to the larger of the two window spans (clamped 8..90 mm).
- Return payload now carries `side_opening_face_index`, `bs_center`, `bs_rotation_deg`;
  `opening_face_index` is None for a synthetic anchor window.

For the recorded scene this seats an 85 mm cube at (0,0,28.39) — its top face flush at the
through window (28.39 + 42.5 = 70.89), folded toward the +Y side window, LED untouched.

## Guards

`validate_open3d_led_beam_splitter_orchestration.py` (penta **phase 283** gates it) extended:

- A: pipeline order now includes the rotation step; the seat is asserted on the MEASURED
  transformed-mesh centre (single-window: BS centred on the on-axis opening).
- **A2**: two perpendicular windows with auto-detect ranking the SIDE window first (the flag's
  condition): the through window must win, the aligned LED must NOT move, side 85 sizing,
  R·Ẑ = +Z and R·X̂ = +Y (fold to the side window), seat at the crossing (0,0,28.39), glued.
- **A3**: the flag's exact live condition — axis anchor + ONLY the side window detected: the
  synthetic through window is used, NO `set_step_clear_aperture` / centering fires, LED shift
  stays (0,0,0), seat at the crossing.

Repro probe: `bugs/probe_0349_add_bs_cube_seat.py` (oblique CO90 → CA snap → add cube; asserts
the LED pose is unchanged by the add and prints the seated cube pose/overlap).

In-app eyeball owed: cube/plate on the real CO90 after restart.
