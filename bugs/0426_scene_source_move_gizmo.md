# 0426 — Interactive MOVE gizmo for a scene source (place the LED by dragging)

**Flag `flag_20260723_132119_918`** (chosen via ask → "interactive 3D gizmo"):
> "I need to be able to align this Illumination LED after adding it. Can make it a components which I can
> place and orientate and resize just like optical element?"

The illumination source could already be placed/oriented/resized **numerically** (Edit Source: Origin /
Direction / Width / Height). This adds the **interactive gizmo** for the first, most-asked axis of that:
**move** (place). Rotate + resize handles are follow-ups.

## What it does

Select a scene source in the **Scene Components browser** → XYZ translate arrows appear at the source
origin (the same 6-arrow gizmo as an optical element's placement handles). **Drag an arrow** to slide the
source along that axis; release to commit. A live "Snap mm" quantizes the slide for precise placement,
exactly like the row placement slide.

## How it works (reuses the row placement-slide machinery)

- **State:** `_actor_source_move_map` (handle actor → `(source_id, axis, step)`) + `_selected_source_id`.
- **Selection:** the browser `source:` click routes to `select_scene_source_from_admin`, which sets the
  selected source, enables whole-body handle mode, and rebuilds — so the arrows appear. Mutually
  exclusive with the row gizmo (each clears the other); `_clear_open3d_selection` drops it.
- **Handles:** `_add_one_scene_source_glyph` draws `_add_scene_source_translate_handles` for the selected
  source; the arrows carry `pick_source_move`, recorded in `_actor_source_move_map` by `_add_mesh_actor`.
- **Drag:** `_placement_drag_state_from_current_pick` builds a source drag state (`source_id`);
  `_apply_placement_drag_motion` **cheap-translates** the source glyph + its arrows via `AddPosition`
  (`_translate_source_actors`) so it tracks the cursor with no rebuild; `_finish_placement_drag` commits
  the accumulated slide onto the origin via `_commit_source_move` → `update_scene_source_spec` (rebuild
  re-seats glyph + gizmo). This is the bugs/0012 deferred-commit trick, so the drag is smooth.

## Verification (`validate_open3d_source_move_gizmo`, penta phase 344)

Display-free (the VTK drag itself is headless-untestable):

| check | asserts |
|---|---|
| HANDLES | the selected source draws XYZ arrows tagged into `_actor_source_move_map` |
| DRAG | source arrow → cheap-translate during the drag → commit origin on release |
| SELECT | browser source click raises the gizmo; row/source gizmos are mutually exclusive |
| COMMIT | the commit slides the origin along the unit axis (origin += delta·axis) via `update_scene_source_spec` |

4/4 pass. Baseline phase 344 = pass.

## Files

- `KrakenOS/UI/open3d_inspector.py` — state, `pick_source_move` tag, `_add_scene_source_translate_handles`,
  `_translate_source_actors`, source branches in the drag pick/motion/finish, `_commit_source_move`,
  `select_scene_source_from_admin`, gizmo cleanup.
- `KrakenOS/UI/panels/open3d_step_admin.py` — browser `source:` click → select + gizmo.
- `KrakenOS/UI/validate_open3d_source_move_gizmo.py` — guard (phase 344).

## In-app eyeball still owed

Add a scene source (LED), click it in the Scene Components browser → XYZ arrows at the source → drag one →
the LED slides along that axis and stays. **Next increments:** rotate gizmo (orient) + resize handles
(the emitting rectangle), so it fully matches an optical element's manipulation.
