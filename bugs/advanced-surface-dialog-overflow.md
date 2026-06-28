# Advanced Surface dialog overflows the screen (no scrollbar, title under the AGS bar)

## Flag

User (2D layout, the **"Advanced..."** button → Native KrakenOS attributes): *"the pop up window
vertical side overflow the screen (and without scroll bar). The text even hide beneath the AGS
bar."*

## Root cause

The dialog (`MainAdvancedSurfaceDialog.open`) is a `ttk.Notebook` whose **Diagnostics/Native**
tab alone is **~30 rows** (each a label + entry + a wrapped "Default: …" line) — well over
2000 px, taller than any screen. The tabs were plain `ttk.Frame`s added straight to the
notebook, so the notebook's *requested* height was that of its tallest tab.

The shared `LayoutTableWorkbenchMixin._show_centered_dialog` then sized the window to
`max(winfo_reqheight(), winfo_height())` — i.e. it **grew the window to the content height**,
ignoring the screen. With the content taller than the screen, `pos_y = (screen − height) // 2`
clamped to 0, so the title tucked under the top/AGS bar and the bottom (the Apply/Cancel footer)
fell off the screen, with no way to scroll.

## Fix

Two parts:

1. **Scrollable tabs** (`main_advanced_surface_dialog.py`): a `make_scroll_tab(title)` helper
   wraps each tab body in a `tk.Canvas` + auto-hiding `ttk.Scrollbar` (inner frame via
   `create_window`, width synced to the canvas, vertical scroll only), with the mouse +
   touchpad wheel (`<MouseWheel>`/`<Button-4>`/`<Button-5>`) bound recursively on every field —
   the same idiom as the scrollable Face Editor (phase 100). All three content tabs (Shape
   Params, the field groups, Custom Surface) go through it; the footer stays gridded on the
   window (row 2), so the buttons are always reachable. Because the canvas bounds the notebook's
   requested height, the window no longer grows to the content height.
2. **Screen cap** (`layout_table_workbench.py::_show_centered_dialog`, shared by all dialogs):
   cap the placed size to the usable screen (`min(reqsize, screen − margin)`; `margin_y = 120`,
   `margin_x = 80`) and keep `pos_y ≥ 40` so a tall dialog never grows past the edges or tucks
   its title under a top bar. A dialog whose content exceeds the cap must scroll its own body.

## Guard

`validate_advanced_surface_dialog_scrollable` (display-free source check, like the Face Editor's
— the harness has no display to render the Tk dialog): the tabs are Canvas+Scrollbar
scroll regions via `make_scroll_tab`; the wheel binds mouse + touchpad recursively; all three
content tabs are scrollable (no raw `notebook.add(frame)`); the footer is on the window; and
`_show_centered_dialog` caps to the screen. **Penta phase 171**, baseline 172.

In-app eyeball owed (the dialog should open screen-sized with a scrollbar on the long
Diagnostics/Native tab, title clear of the AGS bar).
