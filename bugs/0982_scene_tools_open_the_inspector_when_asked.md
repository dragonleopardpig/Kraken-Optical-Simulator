# 0982 -- the 3D scene tools no longer load tkinter when imported

Phase 7d of the Qt migration (docs/design_qt_migration.md), third part: the modules that reach
tkinter through what they import. Phase 738 measured six (bugs/0981); this is the first.

## What was there

`services/three_d_scene_tools.py` imported the 3D inspector class at its top -- a Tk window class
until phase 7e -- so everything that imports the service loaded tkinter. It used the class for three
things:

1. to open the 3D view (`open_3d_view` builds the inspector);
2. for two small helpers that need no window: the classic colour of a surface, and a surface mesh
   as a copy of its own;
3. for five more of its static helpers, fourteen calls, inside the legacy viewer's own picking and
   selection code (actor keys, feature picks, hover outline, selection styling).

## Change

- The two helpers are functions of their own: `open3d_scene_look.surface_color` (with the palette it
  is made of) and `open3d_mesh_basics.mesh_with_transform`. The inspector's two methods stay, as
  one-line calls, so its own callers are untouched. `services/optical_solid_workflow.py` used one of
  them through the inspector class too, and now calls the function.
- The inspector class is reached through one accessor, `_inspector_class()`, which imports it when
  it is needed -- to open the view, or for those fourteen calls -- and not with the module.

**Importing the service no longer loads tkinter: six modules -> five**, by the interpreter.

## What this does not do

The fourteen calls on the inspector class are still made when the legacy viewer picks or selects.
Phase 738 counts them (below), and they go with phase 7e, when the inspector stops being a Tk class.

I first removed the import having seen only three uses; there were seventeen. The file would have
failed at run time in the legacy viewer. Caught before it was committed, by re-reading the file.

## The whole of what is left, now counted

Phase 738 has a further claim, **C**: a service that names a Tk view CLASS at run time uses Tk as
surely as one that imports tkinter. 48 classes count as Tk view classes (those of a `panels/` module
whose import loads tkinter, and the inspector). Services name them **53 times in 8 modules**:

| Module | Uses | What they are |
|---|---|---|
| `three_d_scene_tools` | 16 | opening the 3D view; the legacy viewer's inspector helpers |
| `layout_table_workbench` | 11 | eleven panel factories |
| `layout_shell_controls` | 8 | eight panel factories |
| `analysis_reports` | 6 | six report-panel factories |
| `layout_import_export` | 4 | three panel factories, the Tk missing-assets dialog |
| `legacy_3d_scene` | 4 | the legacy viewer's calls on the inspector class |
| `optical_solid_workflow` | 3 | two panel factories, one inspector call |
| `tolerance_modeling` | 1 | one panel factory |

Most of it is the `_main_*` factories that build the Tk dialog panels. They are view wiring, and
their natural home is the Tk side of the editor when it is split from the model (phase 7f).

## Guard

Phase 738 (`validate_services_import_no_tkinter`): the exact lists I and R go from six to five; new
claim **C** (the table above, exactly); new claim **H** -- the two helpers: a surface's own colour,
black falling through to the glass, mirror, absorber, a surface with nothing; a mesh returned as a
deep copy with its points unmoved; an empty mesh and a non-mesh refused; the inspector's two methods
still giving the same.
