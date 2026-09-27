# 0911 -- row-form tabs lost wheel scrolling in the 0884 port (a real regression)

Penta phase 171 ("Advanced Surface dialog fits the screen + scrolls its tabs") failed 10 checks.
It still read `MainAdvancedSurfaceDialog.open`, which since bugs/0873 and 0884 only renders a row
form through the shared `render_row_form`.

## Claim by claim

- **Tabs are Canvas + Scrollbar scroll regions:** still true.
- **The footer stays outside the scrolled area:** still true.
- **Every Advanced Surface field sits in a tab:** still true. Every `FormField` there has a
  `group=`.
- **The mouse wheel and touchpad scroll a tab from over any field: FALSE.** The hand-written
  dialog bound `<MouseWheel>` and `<Button-4>`/`<Button-5>` recursively on every widget of each
  tab. The port dropped it, so a 30-row tab scrolled only by dragging its scrollbar. The port
  also dropped the auto-hiding scrollbar and the fill-to-height behaviour.

## Fix, in the SHARED renderer, so every grouped row form gets it back

- `bind_tab_wheel(canvas, inner)`: recursive, and lets the event through when the tab has
  nothing to scroll. This is the old dialog's tested behaviour, not the global `bind_all` helper,
  which never unbinds.
- `_update_tab_scroll`: the scrollbar shows only while the tab overflows.
- `_on_tab_canvas_configure`: the fields fill the canvas width and at least its height.

## Guard

The guard now reads the renderer and the form, and B is measured live:
- a tall tab built the renderer's way scrolls on a real Button-5 sent to a FIELD;
- mutation check: with `bind_tab_wheel` disabled, the live check fails ("yview 0.0 -> 0.0").
