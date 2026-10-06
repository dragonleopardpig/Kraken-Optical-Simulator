# 0975 -- Insert > Common Component keeps the scene's file, as an appended layout does

Decided by the user 2026-10-07: "Insert --> Common Component should append layout."

## What it did

bugs/0973 made a layout appended from the Layouts menu leave the scene its own file. The other way
to add the same rows, **Insert > Common Component**, still ended with
`self.current_layout_file = None` and put the three selector names back to their placeholders: it
untitled the scene, even one opened from a file. A Save straight after an insert then asked for a
file name, and the title bar lost the file.

## Change

`insert_layout_component_by_name` no longer touches the scene's file, its transient-import mark or
its selector names. Inserting a component and appending a layout now leave the scene the same way.
The same function serves "insert a machine-vision lens" and the fold-mirror helper, so they follow.

A component inserted into the empty starter still gives an untitled scene: the starter has no file.

## Guard

- `validate_appended_layout_keeps_scene_file` (phase 741), new claim **N**: a scene opened from the
  user's file takes in Doublet Lens through Insert -- 4 to 7 rows, file, title and selectors as they
  were; Save asks nothing, rewrites the user's file (opened again it is the merged scene) and leaves
  `doublet_lens.py` byte for byte; and a scene opened from the Layouts menu keeps its name.
- `validate_selector_menus` (phase 740) told an insert from a load by "the scene is untitled
  afterwards". Over an open scene the two can no longer be told apart -- which is the point -- so it
  now inserts from the empty starter (an insert makes rows and no file; a load there would take the
  layout's file) and then loads a layout that is not insertable.
