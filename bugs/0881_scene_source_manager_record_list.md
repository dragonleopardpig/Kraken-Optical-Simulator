# 0881 -- the Scene Source Manager, and the seventh dialog family

The largest remaining phase-3 dialog (770 lines) and the first that edits a **collection** rather
than one row. A scene source is a source *record*, not a KrakenOS surface row, and the manager
owns the whole list: add one, add one from the Source panel, duplicate, delete, apply them all,
or throw them away and fall back to the panel.

## `RecordList` -- the master list is model data

```python
@dataclass(frozen=True)
class RecordList:
    columns: tuple[str, ...]
    rows: Callable[[Any], tuple]        # form -> one display tuple per record
    select: Callable[[Any, int], str]   # form, index -> message; rewrites form.values
    selected_key: str = "index"
```

`RowForm.records` carries it, `form.state["specs"]` the working list, `form.state["index"]` the
selection. **The selection is model state, not view state**: a view reports a pick by calling
`records.select(form, index)` and the form rewrites itself, so Tk and Qt get identical behaviour
from one place -- including the part that is easy to get wrong, loading a record as
*model defaults, then the record over them*.

One small convention came with it: a row form's action is terminal and closes the dialog, while a
record-list action edits the collection and stays open -- unless it sets
`form.state["close_after"]`, which is how "Use Source Panel Only" leaves.

## Everything else was already in the framework

33 fields; two choices that rewrite others (`Pupil / field` forces a nonphysical reference with
role `pupil_field_reference`; a direction preset rewrites L/M/N); an editable choice for the aim
target; and two actions that **ask the model** where to point --
`scene_source_direction_to_row` and `scene_source_place_at_row_standoff`.

## One renderer for all five Tk row dialogs

The Tk view moved out to `KrakenOS/UI/panels/row_form_view.py`, now shared with the four
scene-element dialogs. It grew the record list, a two-column field layout past 14 fields, and a
hint-on-hover line.

| file | before | after |
|---|---|---|
| `main_scene_source_manager_dialog.py` | 770 | **108** |
| `main_scene_element_dialogs.py` | 616 (originally) | **103** |

Both are now just the factory's kwargs and one call.

## A papercut fixed on the way

`_default_scene_source_spec` carries **no wavelength**, so a freshly added source loaded with the
field blank and refused its own first save (`"Wavelength expects a number."`). The Tk dialog
initialised its variable to the scene wavelength and only lost it on load; the builder keeps that
intent -- a new source starts at the wavelength the scene is using.

## The contract caught the refactor

Penta phase 655 (`validate_3d_interaction_contract`, gated by 0877) went red the moment
"Add From Source Panel" and "Use Source Panel Only" moved into the builder. That is exactly what
gating it was for; the check is re-pointed at `row_forms/scene_sources.py` and additionally
asserts the panel now calls `build_scene_source_manager_form(` and `render_row_form(`.

## Guard

`KrakenOS/UI/validate_open3d_0881_scene_source_manager_form.py` (penta phase 669):

- **B** -- 33 fields, a 6-column record list, the 8 collection verbs, editing record 0
- **V** -- "Source ID cannot be empty.", "Direction vector cannot be zero.", "Choose a valid
  source model."
- **C** -- Add / Duplicate / Add From Source Panel grew 1 -> 4 (the duplicate is
  `source:1_copy`), Delete took one back
- **M** -- the preset rewrote LMN, and `Pupil / field` made the record nonphysical
- **A** -- apply wrote the whole list through `_set_scene_source_specs`
- **T** -- the REAL Tk manager drew its 6-column tree of 2 rows beside 8 combos / 23 entries /
  2 checkbuttons
- **Q** -- the Qt manager listed the same rows, Add grew it, picking row 0 loaded that record
  back, and Apply wrote both
