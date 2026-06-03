# 0006 — promoted analytic-lens row: the big Move/Rotate translate arrows shrink back to short grid stubs

**Status:** Fixed. The row-placement Move/Rotate gizmo now sizes its translate
arrows (and rotation arcs) to the *visible body* of the row, using the same
length formula as the STEP overlay. A STEP promoted to an analytic-lens row
keeps the same big arrows it had as a STEP overlay instead of reverting to the
short, scene-grid-scaled stubs.
**Component:** Open 3D inspector — scene-placement (row) transform gizmo vs the
STEP-overlay transform gizmo.
**Reported via:** in-app recorder, flag `flag_20260603_113147_592`
("After converted to analytical lens, when select again the element, the
previous big sliding arrow handles become the old short one.").

## Symptoms (user's words)

> After converted to analytical lens, when select again the element, the
> previous big sliding arrow handles become the old short one.

State (`state.json`): `picked_row_index: 1`, `picked_step_label: null`
(the lens is now a *row*, not a STEP overlay), `placement_translate_handle_count:
6`, `placement_rotate_handle_count: 9`. The selected row's body bounds were
`[-12.5, 12.5, -12.56, 12.48, 54.56, 66.18]` ⇒ body extent ≈ 25 mm.

## Behaviour before

Two parallel gizmos draw the "same" Move/Rotate handles:

* **STEP overlay** (`Open3DStepRotationHandleService.add_handles`) — used while a
  STEP is imported as a transient overlay. bugs/0004 made its translate arrows
  long: `translate_len = max(extent*1.05, radius*1.55)` where `extent` is the
  STEP body's bounding-box extent and `radius = max(extent*0.62, 3.0)`. For a
  25 mm lens that is ≈ 26 mm — arrows that clear the rotation arcs.
* **Row placement** (`_add_scene_placement_translate_handles` /
  `_add_scene_placement_rotate_handles`) — used once a row is selected (a
  promoted analytic lens, or a file-backed STL row). Its arrow length was
  `max(min(max(extent*0.18, spacing*1.5), max(extent*0.35, 1.0)), 1.0)` where
  `extent` is the **scene grid** extent (`grid_extent_mm`, default **100 mm**),
  *not* the body. For the default grid that caps at ≈ 18 mm regardless of how
  big the lens is, and the rotation arcs were likewise grid-scaled
  (`radius ≈ min(grid*0.48, …)` ≈ 28 mm).

Promotion (STEP → analytic-lens row) switches the lens from the STEP-overlay
gizmo to the row-placement gizmo, so a 25 mm lens's translate arrows dropped
from ≈ 26 mm (clearing the arcs) to ≈ 18 mm (buried inside the 28 mm arcs) —
the "big sliding arrow handles become the old short one".

## Root cause

The row-placement gizmo was sized off the **scene grid** (a fixed 100 mm), while
the STEP overlay was sized off the **body**. They are the same gizmo on the same
object; only the size source differed, so the gizmo visibly changed shape when
the object crossed from one code path to the other on promotion.

A second wrinkle: a promoted analytic lens body is **not** file-backed — it
carries `_kraken_glassy_lens_body` / `_kraken_round_lens_like_step_body`, not
`_kraken_file_backed_row_body`. So keying the body bounds off the file-backed
marker alone (as `_row_display_actor_center`'s body branch does) misses a
promoted lens and silently falls back to the grid extent. Verified off-screen:
for the Ball Lens fixture the STEP-overlay arrow measured 10.39 mm and the
row-placement arrow 10.39 mm *after* the fix (body extent 9.525 mm), versus the
≈ 18 mm grid stub before.

## Fix

`KrakenOS/UI/open3d_inspector.py`:

* New `Kraken3DInspector._transform_translate_arrow_length(extent)` staticmethod
  — the single source of truth for a Move-gizmo translate-arrow length,
  `max(extent*1.05, max(extent*0.62, 3.0)*1.55)` (byte-identical to the STEP
  service's old inline formula). Both gizmos now call it.
* New `Kraken3DInspector._row_display_body_extent(row_index)` — the largest
  world bounding-box dimension of a row's **visible solid body**, accepting any
  of the three body markers (`_kraken_file_backed_row_body`,
  `_kraken_glassy_lens_body`, `_kraken_round_lens_like_step_body`) and excluding
  gizmo / overlay / label actors. Returns `None` for an abstract placement with
  no rendered body.
* `_add_scene_placement_translate_handles` now uses
  `_transform_translate_arrow_length(body_extent)` when the row has a body,
  falling back to the old grid-scaled stub only for bodiless abstract
  placements.
* `_add_scene_placement_rotate_handles` now sizes its arcs off the body extent
  when available (grid extent otherwise), so the arcs fit the object and the
  body-scaled translate arrows clear them.

`KrakenOS/UI/services/open3d_step_rotation_handles.py`:

* `add_handles` now calls `inspector._transform_translate_arrow_length(extent)`
  instead of the inline `max(extent*1.05, radius*1.55)` — behaviour-preserving,
  and guarantees the two gizmos can never drift apart again.

## Tests

* **`validate_open3d_promoted_row_translate_arrow_length`** (display-free) —
  pins `_transform_translate_arrow_length` (monotonic, ≥ extent*1.05, equals the
  STEP service's historical formula) and source-couples both gizmos: the STEP
  service and `_add_scene_placement_translate_handles` must call the shared
  length seam, and the row translate/rotate handlers must size off
  `_row_display_body_extent` — so a future edit can't silently revert either to
  grid-only sizing.
* **`validate_open3d_promoted_row_translate_arrow_length_snapshot`**
  (image-snapshot, boots its own Xvfb) — imports a lens STEP, measures the
  STEP-overlay translate-arrow length, promotes to analytic, builds the
  row-placement gizmo, and asserts (a) the row arrow length matches the STEP
  overlay within tolerance (the gizmo doesn't shrink on promotion) and (b) the
  arrows are actually rendered (changed pixels over a no-gizmo baseline), then
  the fixer opens the PNG and confirms the arrows clear the body. SKIP when no
  lens fixture is checked out.
* **Regression / end-to-end** — `Phase 13` in
  `validate_open3d_penta_telescope_comprehensive.py`: on a real imported lens,
  measures the STEP-overlay translate-arrow length, promotes, builds the
  row-placement gizmo, and asserts the row arrow length equals the STEP overlay
  length within tolerance and is ≥ the body extent. SKIP-passes when no lens
  fixture is checked out under `attachment/Lens/`.
