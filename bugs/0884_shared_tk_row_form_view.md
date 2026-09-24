# 0884 -- finishing the ports that were only half done

A census of the remaining `tk.Toplevel` builders (50 functions, 7961 lines) turned up something
better than another dialog to port: **five dialogs whose models were already in `row_forms/` were
still drawing their own Tk page.** 0869-0873 moved the data out and left the layout behind.

| panel | before | after |
|---|---|---|
| `main_advanced_surface_dialog.py` | 246 | **87** |
| `main_coating_material_dialog.py` | 200 | **85** |
| `main_beam_splitter_dialog.py` | 154 | **78** |
| `main_error_map_dialog.py` | 154 | **74** |
| `main_diffuse_scatter_dialog.py` | 144 | **75** |

Each is now the read-the-table prologue and one `render_row_form(self, form)`.

## The two kinds the shared renderer lacked

- **`kind="textarea"`** -- a `tk.Text`, which has **no `textvariable`**, so it cannot live in the
  `variables` dict like every other widget. It gets its own `texts` dict and is read and written
  by hand in `current_values()` and `refresh_from_form()`.
- **`form.groups`** -- a `ttk.Notebook` with a **canvas + scrollbar per tab**, which is exactly
  what the hand-written Advanced Surface page did, because 53 fields do not fit a laptop screen.

With these two the Tk and Qt renderers are finally feature-equal: every `FormField` kind and
every `RowForm` property draws in both.

## Two guards had pinned the old pages

- The **interaction contract** (phase 655) went red on four of the five, because
  `"Validation passed:"` is the **renderer's** line now, not each page's. Two of its literals
  (`"Validation passed: no error map."`, `"Advanced Surface Validation"`) existed nowhere at all
  -- they belonged to pages that no longer exist. Re-pointed: each check asserts the panel calls
  its builder and `render_row_form()`, and the shared line is asserted once, against the renderer.
- **Guard 0871** (phase 649) asserted the error-map dialog drew a `tk.Text`. Its fields are all
  `static`, so the shared renderer draws wrapped Labels. The claim -- "the dialog shows what the
  builder put in the form" -- is unchanged, so the guard now reads Labels as well as Texts.

Both are the gate doing its job: every consolidation that moves a string is supposed to trip it.

## Guard

`KrakenOS/UI/validate_open3d_0884_shared_tk_row_form_view.py` (penta phase 672):

- **R** -- the renderer draws textareas and tabs
- **L** -- the five panels build no widgets of their own and are all under 100 lines
- **D** -- each REAL Tk dialog opens on the builder's fields: a textarea for the coating table,
  a notebook with 52 entries and a switch for Advanced Surface, 10 entries for Beam Splitter on a
  real splitter row -- or refuses with the builder's message, as Diffuse / BRDF does on a
  non-diffuse row

## What the census says is left

Of the 50 Toplevel builders, the big ones are the CAD/STL face-roles editor (1903 lines) and the
MTF-from-image dialog (375) -- both **phase 5**, since they embed VTK/matplotlib with picking.
The rest is a long tail of 37-278 line dialogs: the path-component placement dialog (278), the
surface shape builder (375), the inspection *part* dialog (197), the catalog matcher (136), the
scene-source edit popup (136), and a dozen small settings/preset dialogs.
