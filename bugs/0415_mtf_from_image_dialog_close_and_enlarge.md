# 0415 — Measure-MTF-from-Image dialog: close mechanism + click-to-enlarge plot

**User:** "The measure MTF from image pop up, need close mechanism. The MTF image can it be made
clickable, enlarge just like other Analysis curve behaviour?"

Two gaps in the 0411 dialog (`mtf_from_image_dialog.py`):

1. **No reliable close.** It was a plain `Toplevel` relying on the window-manager's title-bar X — which
   the user's tiling WM / the centered-dialog helper don't always provide, so the dialog could get
   stuck open.
2. **The plot was inert.** The main-window Analysis curves open in the system image viewer on click
   (`_open_high_res_plot_in_system_viewer`); the embedded MTF curve had no such affordance.

## Fix

**Close** — an explicit **Close** button (next to Compute / Save CSV), a `WM_DELETE_WINDOW` protocol,
and an `<Escape>` binding all call a `_close()` that clears the standalone `Figure` and destroys the
window.

**Click-to-enlarge** — the plot widget now shows a hand cursor and binds `<Button-1>` to
`_enlarge_plot()`, which renders the current figure to a high-res PNG (`dpi=300`, `bbox_inches="tight"`)
into `SCREENSHOT_DIR` and opens it with the editor's `_open_image_with_system_viewer` — the **same
mechanism the main-window Analysis curves use**, so zoom/pan/save all happen in the system viewer. A
one-line hint under the plot says "Click the plot to enlarge." It works before Compute too (opens the
empty axes), but is most useful once a curve is drawn.

## Verification (`validate_open3d_mtf_from_image_dialog_controls`, penta phase 338)

Display-free (the dialog needs Tk + matplotlib + an editor to instantiate, so the wiring is pinned by
inspection — the same style as the other UI-mechanism guards):

| check | asserts |
|---|---|
| CLOSE | Close button + `WM_DELETE_WINDOW` + `<Escape>` all call `_close`, which destroys the window |
| ENLARGE | the plot binds `<Button-1>` → `_enlarge_plot`, hand cursor, high-res `savefig`, opens via `_open_image_with_system_viewer` |

2/2 pass. Baseline records phase 338 = pass.

## Files

- `KrakenOS/UI/panels/mtf_from_image_dialog.py` — Close button + WM_DELETE + Escape + `_close`; plot click bind + hand cursor + hint + `_enlarge_plot`.
- `KrakenOS/UI/validate_open3d_mtf_from_image_dialog_controls.py` — guard (phase 338).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — register phase 338.
- `tools/penta_validator_baseline.json` — phase 338 = pass.

## In-app eyeball still owed

Open File → "Measure MTF from Image…", load an image, Compute → **click the curve** → it opens enlarged
in the image viewer. **Close** button, the window's X, and **Esc** all shut the dialog.
