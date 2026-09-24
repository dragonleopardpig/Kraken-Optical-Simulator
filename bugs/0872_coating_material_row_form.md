# 0872 -- the Coating / Material row form: the framework finished

The most tangled of the row dialogs, and the one that completed the row-form framework.

## What it needed that nothing before did

- a **Python literal edited as text**: the coating table, read and written through the editor's
  own `_literal_editor_text` / `_parse_literal_editor_text`. A coating that is not a literal shows
  as `<non-literal coating object>` and refuses to be applied rather than being mangled;
- a choice that **rewrites another field**: picking a preset replaces the whole coating table, and
  picking a metal catalogue sets the metal index it is listed under. `FormField.on_change(form,
  value)` is the framework's answer -- the model decides what changes, and the view refreshes from
  the form afterwards;
- a choice list that **grows**: `Load CSV...` adds a catalogue, so `RowForm.choices` holds live
  overrides and a view reads `choices_for(key)` rather than the frozen field;
- **warnings**, which the shared advanced-surface validator reports alongside errors. A warning is
  shown as a warning; only errors refuse.

## Two rules worth stating

**Zero means default.** Applying `CoatingMet = 0` REMOVES the key, as an empty `[[], [], [], []]`
removes `Coating`. The dialog has always done this; the guard now pins it.

**The catalogue list is not the catalogue specs.** `_metal_catalog_entries` prepends the built-in
metals, so a layout with one loaded CSV shows two entries. The editor keeps the loaded SPECS; the
list shows entries. My first two assertions conflated them and were wrong, not the code.

## Guard

`validate_open3d_0872_coating_material_row_form.py`, penta phase 650. P the preset rewrites the
table. G Load CSV asks the host, grows the list and selects what it loaded. L a catalogue choice
sets the index. W a warning stays a warning. E an unparseable table refuses and a metal index with
no catalogue is the model's error. A1 apply writes Coating and a non-zero CoatingMet and keeps the
loaded specs. A2 an empty table and a zero index remove both keys. T the REAL Tk dialog opens on
the builder's values. Q1-Q4 the Qt form gives each field the widget its kind asks for, rewrites
its table on a preset, grows its list on a load, and applies the same.

## The row-form framework, complete

| piece | added by |
|---|---|
| `FormField` (number/int/choice/text), `RowForm`, `FormRefused` | 0869 Beam Splitter |
| `kind="textarea"`, computed choices | 0870 Diffuse / BRDF |
| `FormAction`, `kind="static"` | 0871 Error Map |
| `on_change`, live `choices`, warnings | 0872 Coating / Material |

What remains is Advanced Surface and the 1 902-line CAD face-roles editor -- larger, but nothing
in them needs a new kind of thing.
