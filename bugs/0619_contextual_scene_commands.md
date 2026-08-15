# 0619 — CAD/Place/Orient commands integrated into element interaction (FEATURE)

flag_20260814 (user): *"for the 3D menu: CAD/target, Place and Orient, I think it is
more useful to integrate the command during user dynamic interaction with the elements
on the scene rather than clicking the menu... Frankly speaking, I don't fully
understand each command."*

## What shipped

All element-targeted commands from the three toolbar menus are now right-click verbs
on the thing they act on (canvas AND Scene Components tree; direct commands, no
cascades — bugs/0320). The full mapping and a plain-language explanation of every
command lives in **docs/open3d_dynamic_interaction.md** (the second half of the ask).

- **Movable rows** (all three classes: file-backed STL, promoted, and plain surface
  rows — plain rows previously fell through with NO element actions): a "Place this
  element" section (Move Row→Axis, Snap Row→Target) and the full 8-command Orient
  family + Preview, with the toolbar Axis/Normal combobox choices baked into the
  labels at build time.
- **STEP bodies**: Move (arms the carry for that body, no checkbox), Rotate (arc
  handles), Center-a-Feature→Axis, Delete, LED reference-edge pick — plus the
  pre-existing replace/swap/flip/glue/promote set.
- **Face→axis in ONE step**: the right-clicked face directly feeds the three
  snap/center variants (a StepFeatureSelection is built from the menu context),
  removing the toolbar flow's separate left-click-the-face-first step.
- **Selection menu** at 2+ selected elements: Snap Selected→Axis, Group as Assembly,
  Snap Assembly→Axis, Clear.
- **Empty-space right-click** (previously a dead-end status hint): Select Elements,
  Select+Snap, Move Elements Axis→Axis.

Toolbar entries stay for muscle memory; scene-level operations (imports, export,
clear, galvo animation, measure) remain toolbar-only by design.

Selection plumbing: context handlers first select the row via
`select_scene_row_from_admin` / set `_picked_row_index` (the resolver every command
prefers), so the command acts on the row under the cursor, never a stale selection.

Guard: phase 466 (`validate_open3d_0619_contextual_scene_commands`) — entry contracts
on all surfaces + a display-free mechanism check (12 entries on a movable row,
refusal on Object/Image, selection menu only at 2+).

## Not in this increment (candidates on user feedback)

- Rubber-band select as the DEFAULT empty-space left-drag (currently orbit; changing
  the primary gesture deserves its own flag).
- A free-rotate trackball gizmo (arcs are click-stepped by design).
- Auto-showing arc handles on selection without the checkbox.
