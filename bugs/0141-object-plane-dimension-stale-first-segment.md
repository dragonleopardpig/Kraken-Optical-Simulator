# 0141 — Object-plane thickness arrow's first segment reads the BS's pre-move spot

## Symptom

`flag_20260625_091108_573`:

> *"the thickness measurement blue arrow starting from the object plane, there are
> two segments, the first one measure the old location of the BS before move, which is
> not updated."*

In the BS-cube + imaging-lens + camera scene, the blue (physical-distance) dimension
running from the Object plane is drawn as **two** segments. The user reads the second
as correct (`gap to solid = 201.5 mm`, the live Object→beam-splitter-entry distance)
but the **first** segment ends at the beam splitter's **pre-move** position (~z = 81,
the promotion-time nominal station) and did not follow the cube when it was moved
downstream.

## State evidence (`state.json`, post-move)

- `row_actor_bounds["1"]` (the promoted BK7 cube) = z **201.49 .. 257.35**
  (center ≈ 229.4, thickness ≈ 55.86 — matches the `S1 Thickness = 55.86 mm` label).
- `promoted_solid_rows[0]`: `promotion_center_world.z = 108.5172`, `desp = [0, 0, 148.4]`.
  So the cube's **nominal** station (desp = 0) is center ≈ 229.4 − 148.4 = **81.0**,
  and the live body sits at 229.4 after the `+148.4 mm` move.
- The blue arrow's first-segment break sits at ≈ 40 % of the Object→cube run
  (81 / 201.5 ≈ 0.40) — i.e. exactly the cube's **pre-move nominal station**.
- `step_actor_counts = {lens, led, camera}` — **no** beam-splitter overlay remains
  (promotion removed it).

## What the current code does (thorough dig — does NOT reproduce)

The Object→cube dimension is one row→row span (`Open3DThicknessDimensionService.
add_overlays`, `open3d_thickness_dimensions.py`). Walking it against the current code
with this exact state, it draws a **single, fresh** arrow:

1. `p1 = editor._surface_reference_world_point(row 1)`. Row 1 is a **file-backed STL**
   solid, so this goes through `transformed_stl_bounds(path, tilts, desp, z_station)`
   (`scene_placement_commands.py:489`) — which **includes** `desp_z = 148.4`, giving
   the **live** center 229.4, not the nominal 81. (The committed `desp_z` in the state
   proves the move was written back, so the reference point is not stale.)
2. bugs/0093 override: the next row is an optical solid, so `entry =
   _optical_solid_entry_point(row 1)` reads the **rendered actor's** near face (201.5)
   and **replaces** `p1` → the label becomes `gap to solid = 201.5 mm`. A single span.
3. The split (`_overlay_axial_spans_within` → `split_span_at_overlays`) only carves at
   **STEP overlays** in `_step_actor_map`. The cube overlay is gone (promoted); the LED
   overlay is a **decoration** (`is_step_overlay_decoration`, bugs/0122) and is skipped;
   the imaging-lens overlay (z 275..331) is downstream of 201.5. So **nothing splits**
   the Object→cube span.

So current code produces ONE fresh `gap to solid = 201.5 mm` arrow — it cannot emit a
**second** segment frozen at the cube's old nominal station. A fresh `201.5` reading
coexisting with a stale `~81` break is not a frozen overlay (bugs/0011, where the
*whole* overlay froze) and not a phantom overlay span (none remains): it is the
signature of a **partial refresh in a long-running app** — the cube was moved and the
live `gap to solid` recomputed, but the app retained a pre-move Object→cube arrow that
a clean scene rebuild would have cleared.

## Status — needs a re-record (suspected stale app)

Not reproduced on current code after the dig above; same pattern as bugs/0093
(`repro_0093.py`: "does NOT reproduce on current code => suspect a stale app at record
time"). **Owed:** the user restarts the app, re-loads the scene, moves the beam
splitter again, and re-flags **if** the stale first segment persists. If it does, the
fresh recording will show whether the move took a fast path that skipped the dimension
rebuild — at which point this gets a root-cause fix + display-free guard + penta phase
like the other bugs. No code changed and no guard added yet, because there is nothing
real to pin until it reproduces.
