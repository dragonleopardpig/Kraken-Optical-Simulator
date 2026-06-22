# 0108 — Absorbed reflect arm still shows a detector; arrow-less / manual measurement overlays can't be hidden; no measure hover highlight

**Flag:** `attachment/recorded_bug_repros/flag_20260622_154023_980` (2026-06-22)

> *"set absorbing surface to the BS stop the ray, but the image plane is still
> shown in the reflecting arm. Some thickness measurment overlay without arrow,
> can't hide them. The manual measurement, can't delete or hide by selection."*

Plus one follow-up from the same session:

> *"Also, manual measurement, mouse hover over edge or surface is not
> highlighting."*

Four independent display-layer issues, bundled into one fix.

---

## Issue 1 — an absorbed reflect arm still draws a branch detector / Image plane

Assigning an **Absorber/Mechanical** face to the beam splitter stops the reflect
ray. The reflected rays are still present in `ray_paths` (they terminate by
absorption), so `derive_branch_detectors` still grouped them into a terminal
leaf and placed a converging "detector" (and the superseded sequential Image)
in the reflect arm — a focus for a beam that never gets there.

**Root cause:** `derive_branch_detectors` keyed only on the ray-tree topology
(which leaves exist), not on whether a leaf's rays actually *reach* anything. An
all-absorbed leaf has no exit beam, so it must not produce a detector.

**Fix** (`services/branch_detectors.py`): a leaf whose every ray dies by
absorption is dropped before detectors are derived. The terminal status comes
from `ray_path_terminal_status_from_events(path) == "absorbed"` (falls back to a
`termination_reason` substring). The test is conservative — a single
non-absorbed ray keeps the detector — so it can't suppress a live arm.

```python
leaves = [bp for bp in leaves if not _leaf_fully_absorbed(groups[bp])]
```

Guard: `validate_open3d_beam_splitter_branch_detectors` test 3b — an absorbed
reflect arm yields **no** reflect detector (0 branch detectors total). Penta
phase 82.

---

## Issue 2 — a thin / arrow-less Thickness overlay can't be hidden

The 0107 per-row hide works by right-clicking the blue arrow. But a thin element
(or a branch exit→detector distance overlay) draws only a **leader line +
billboard label**, no arrow. The `vtkCellPicker` can't hit billboard text or a
hairline leader, so the right-click never resolved a row and the menu never
opened ("can't hide them").

**Fix:**
- `open3d_inspector.py` `_thickness_dimension_row_under_cursor` now falls back, on
  a direct-pick miss, to a **screen-space proximity search**
  `_thickness_dimension_row_near_display_xy(x, y)` — the nearest registered
  arrow segment **or** label center within `tolerance_px`. So a right-click near
  any overlay (arrow or label) resolves its row.
- `services/open3d_thickness_dimensions.py` `_branch_distance_overlays` now also
  honours `_thickness_dimension_is_hidden` so the per-branch exit→detector
  distance overlays can be turned off too.

Guard: `validate_open3d_thickness_dimension_visibility` check F. Penta phase 93.

---

## Issue 3 — manual measurements can't be deleted or hidden by selection

The Measure tool's `clear_measurements` was all-or-nothing; there was no
per-measurement control.

**Fix** (`open3d_inspector.py`):
- Each recorded segment carries a stable `seg["id"]`; `_hidden_measure_segments`
  is a set of those **ids** (not list indices, so a hide survives a delete that
  shifts indices). `_refresh_measure_overlays` skips hidden ids.
- A shared `_measure_segment_offset_endpoints(seg)` resolves a segment to its
  drawn dimension-line geometry; both the draw loop and the new proximity finder
  `_measure_segment_index_near_display_xy(x, y)` use it, so a right-click lands
  on exactly what is drawn (the overlays are `PickableOff`, so this resolves by
  screen-space proximity).
- Right-click menu `_maybe_show_measure_menu` / `_show_measure_menu` offers
  **Delete this measurement** / **Hide this measurement** / **Show all
  measurements**, backed by `delete_measure_segment` /
  `toggle_measure_segment_hidden` / `show_all_measure_segments`.
- Wired into `services/open3d_face_assignment.py`
  `_show_surface_function_context_menu` (claimed before the thickness/QE menus).

---

## Issue 4 — no hover highlight while measuring

`_on_mouse_move` (interaction service) had branches that highlight the
edge/surface under the cursor for the re-anchor and center-to-ray picks, but
none for the Measure tool — so measuring gave no feedback about what the next
click would pick.

**Fix:** a `_measure_pick_mode` branch in
`services/open3d_interaction.py` `_on_mouse_move` (and added to `hover_critical`
so it isn't throttled) calls `_update_measure_hover_highlight`, which picks under
the cursor and reuses the existing gold STEP-face outline / row highlight
(`_set_dimension_anchor_snap_highlight`). The highlight is cleared when the
measurement completes or is cleared.

---

## Tests

- `python -m KrakenOS.UI.validate_open3d_beam_splitter_branch_detectors` (issue 1)
- `python -m KrakenOS.UI.validate_open3d_thickness_dimension_visibility` (issue 2)
- `python -m KrakenOS.UI.validate_open3d_measure_overlay_visibility` (issues 3 & 4) — penta **phase 94** (new; baseline → 95 phases)

In-app eyeball owed for all four (headless can't drive the absorbing-trace
render, the right-click hide menus, or the live hover highlight).
