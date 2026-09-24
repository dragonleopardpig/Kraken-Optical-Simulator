# 0882 -- the Glass Catalog Browser and the Stock Lens Importer

Two catalogue browsers: a list you search and pick from. `RecordList` (bugs/0881) absorbed both
with **one addition** -- an `on_change` on a **text** field, so a filter is live, after which the
view re-asks the model for its rows. Choices already had `on_change`; now `text`, `number` and
`int` do too (Tk `<KeyRelease>`, Qt `textEdited`).

| dialog | before | after |
|---|---|---|
| `main_glass_catalog_browser_dialog.py` | 182 | **54** |
| `main_stock_lens_importer_dialog.py` | 337 | **56** |

## Glass Catalog Browser -- a record-list form with nothing to edit

3473 catalogue glasses, a live filter, and an Apply that writes the picked glass onto the
selected surface row. Two behaviours kept exactly as they were: applying a glass to a `Mirror`
row turns it back into `Standard` (the Tk browser did this silently), and with no row selected it
refuses with "Select a surface row first, then apply the glass."

**One trap:** `Setup().NAMES` and `.NM` are numpy arrays, so `list(getattr(setup, "NAMES", []) or [])`
raises `ValueError: The truth value of an array with more than one element is ambiguous`. The Tk
browser tested `is not None` for exactly that reason; the builder does the same, with the reason
written down this time.

## Stock Lens Importer -- a record list that inserts rows

A catalogue choice whose `on_change` **loads** the .ZMF (the expensive step, so it reports what it
loaded: `"Edmund Optics 2019 (attachment): 9495 parts from ..."`), a live search, and an Apply
that turns the catalogue item into a rigid block of surface rows. The 500-row display cap the Tk
tree had is preserved and named (`SHOWN_LIMIT`), so a search that matches 936 parts still says
so: `"936 match(es) showing first 500."`

Path mode -- opened from a path-component command -- adds the path distance and the five local
decenter/tilt fields, titles itself "Add Stock Lens to Path", and inserts the block on that path
instead of after the selected row. It refuses a non-positive distance and a non-numeric offset.

## Guard

`KrakenOS/UI/validate_open3d_0882_catalog_record_forms.py` (penta phase 670):

- **G** -- 3473 glasses, the live filter cut it to 21, apply wrote `'N-BK7'` onto row 2, and with
  no row selected it refuses
- **S** -- 4 catalogs, the loaded one drew 500 rows, the search matched, apply inserted 4 rows
- **P** -- path mode is titled "Add Stock Lens to Path", adds 6 placement fields, and refuses
  "Path distance must be positive." / "Local offset and tilt values must be numeric."
- **T** -- the REAL Tk browser drew 3473 glasses and the REAL Tk importer 500 parts
- **Q** -- both Qt dialogs listed the same rows, the live filter working through `textEdited`

## The contract caught it again

Penta phase 655 went red on both dialogs the moment their strings moved into the builders --
the second time in two bugs that gating `validate_3d_interaction_contract` (0877) has paid off
within the hour. Re-pointed, and it now also asserts each panel calls its builder and
`render_row_form()`.
