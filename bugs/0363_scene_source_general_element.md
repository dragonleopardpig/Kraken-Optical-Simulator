# 0363 — The LED Illumination Source as a general 3D source element

**Ask (user, 2026-07-20):** "About the LED Illumination Source, I see it is added to
machine_vision_150mm_test.py, not as a general 3D source element that I can add it to other files.
Can make it a 3D source element so that I can import it? After import I can change the dimension,
orientate and place it to whatever location manually, can also glue to the BS cube or LED STEP?"

**Status:** SHIPPED 2026-07-20 (guard `validate_open3d_scene_source_edit`, penta phase 312).

## Already true (worth knowing)

The source was never baked into that file: it lives in the layout's `scene_sources` spec, and
**right-click "Scene Sources" in the Scene Components browser → "Add Illumination Source (LED)"**
(0284) adds one to ANY scene; it persists with the layout. What was missing was editing and glue.

## What ships

- **Edit Source… dialog** (right-click the source row in the browser): name, origin X/Y/Z,
  direction L/M/N, emitting width/height (mm), cone half-angle, ray count, power. Writes through
  the new `update_scene_source_spec` (editable-key filter — role/physical/coaxial keys stay as
  authored; both the `origin`/`direction` and `source_x..n` spec forms are overridden; `radius`
  refreshes to max(radius_x, radius_y)), applied via the standard row-action path so the glyph,
  Illum volume and trace follow immediately.
- **Seat on face (one-shot glue)**: right-click a face of the BS cube / LED STEP in 3D → "Seat
  \<source\> on This Face" — origin lands on the picked face centroid, aim turns INTO the solid
  (the coaxial case). One entry per physical source. Size stays as authored (use Edit Source…).

## Deferred (documented, not built)

Follow-on-move glue (the seat is a pose copy; moving the BS later does not drag the source) — the
two-body glue arcs (0103/0319 class) are the pattern when this is asked for. A drag gizmo for
sources remains the older open ask (project_open3d_scene_source_object).
