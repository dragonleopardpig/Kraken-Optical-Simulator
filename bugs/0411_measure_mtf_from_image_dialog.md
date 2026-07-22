# 0411 — "Measure MTF from Image" UI (interactive USAF-1951)

**Request:** the user added `KrakenOS/USAFMTF.py` (measure MTF from a captured USAF-1951 bar-target
image, commit `03dfa2ce`) and asked for an **Import Image** UI to load an image and generate the MTF
curve. Chosen ROI-input UX (via AskUserQuestion): **draw ROIs on the image**.

## Code review of `USAFMTF.py` (the user's module)

Sound. Correct USAF-1951 frequency `2^(g + (e-1)/6)`, Rec.709 luminance, NaN-safe rotate/project, and
the key detail — a **joint odd-harmonic (1,3,5) least-squares fit** so a non-integer crop doesn't leak
the square-wave 3rd/5th harmonics into the fundamental — plus the `pi/4` square-wave factor. Verified
end-to-end: unblurred high-contrast bars → MTF ≈ 0.99, blur → 0.66. **MTF = image Michelson contrast ÷
`target_contrast`** (default 1.0, right for a chrome-on-glass USAF chart); the dialog surfaces this. The
module's `tests/test_usaf_mtf.py` use pytest, which isn't in the devenv venv — verified manually instead.

## The dialog

`panels/mtf_from_image_dialog.py` `open_mtf_from_image_dialog(editor)` — File → **"Measure MTF from
Image..."**:

- **Import Image** → the capture is shown scaled-to-fit on a Tk canvas; the full-res grayscale
  (`load_grayscale_image`) is kept for the fit.
- **Draw ROIs** → drag a rubber-band rectangle over each three-bar element. The "Next ROI" fields
  (Group / Element / Bars=orientation / Cycles) stamp it, Element auto-advances 1→6, and the ROI is
  stored in **original image pixels** (`canvas coord / display scale`) so the fit always runs full-res.
  Each ROI is listed in a Treeview (Delete / Clear All).
- **Calibration (optional)**: magnification (for image-space lp/mm), pixel pitch µm, target contrast,
  and the object/image frequency axis.
- **Compute MTF** → `analyze_usaf_image(gray, rois, …)` → the MTF curve is drawn in an embedded
  matplotlib figure and the per-ROI MTF / R² fill the list.
- **Save CSV** → `result.save_csv`.

## Verification (`validate_open3d_mtf_from_image`, penta phase 335)

Display-free — exercises the analysis through the dialog's exact ROI-dict API + getsource wiring:

| check | asserts |
|---|---|
| ANALYZE | synthetic high-contrast bars → MTF ≈ 1 unblurred; blur lowers it; non-empty curve |
| WIRING | File menu "Measure MTF from Image..." → `open_mtf_from_image_dialog`; editor delegates to the dialog |
| CONTRACT | the dialog binds canvas ROI drawing (press/motion/release), stores ROIs in image px, computes, plots, saves CSV |

3/3 pass. Also headless-Tk construction-smoked (Xvfb): the Toplevel + all widgets + the empty plot
build and tear down cleanly.

## Files

- `KrakenOS/UI/panels/mtf_from_image_dialog.py` — the interactive dialog.
- `KrakenOS/UI/services/layout_import_export.py` — `open_mtf_from_image_dialog` editor opener.
- `KrakenOS/UI/panels/main_window.py` — File-menu entry.
- `KrakenOS/UI/validate_open3d_mtf_from_image.py` — guard (penta phase 335).
- (`KrakenOS/USAFMTF.py` + `tests/test_usaf_mtf.py` are the user's, commit `03dfa2ce`.)

## In-app eyeball still owed

File → "Measure MTF from Image..." → Import a USAF-1951 capture → drag rectangles over the three-bar
elements (set Group/Element/Bars first) → Compute → the MTF curve plots; Save CSV writes the points.

## Scope / next

Possible follow-ons: rotation-per-ROI field (the module supports `rotation_deg`); zoom/pan for very
large captures (currently scaled-to-fit); a slanted-edge MTF mode (single-ROI, more automatable) as an
alternative to the bar target.
