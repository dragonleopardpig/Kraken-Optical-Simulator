# 0411 — "Measure MTF from Image" UI (slanted-edge + USAF, draw-on-image)

**Request:** the user added `KrakenOS/USAFMTF.py` (MTF from a captured USAF-1951 bar target, commit
`03dfa2ce`) and asked for an **Import Image** UI. Chosen ROI-input UX (AskUserQuestion): **draw ROIs on
the image**.

**Follow-up (the user's first real image):** loading `attachment/1.tif` and selecting the whole image
as one ROI gave a "straight line". Diagnosis: **`1.tif` is a slanted/knife EDGE, not a USAF three-bar
target** — the USAF fit is a periodic square wave, so an edge yields one meaningless point → a line from
the origin. USAF gives ONE point per element (you draw several); an **edge gives a WHOLE curve from one
ROI**, which is what the user expected. So a **slanted-edge (ISO 12233) mode** was added as the DEFAULT
(`KrakenOS/EdgeMTF.py`).

## Code review of `USAFMTF.py` (the user's module)

Sound. Correct USAF-1951 frequency `2^(g + (e-1)/6)`, Rec.709 luminance, NaN-safe rotate/project, and
the key detail — a **joint odd-harmonic (1,3,5) least-squares fit** so a non-integer crop doesn't leak
the square-wave 3rd/5th harmonics into the fundamental — plus the `pi/4` square-wave factor. Verified
end-to-end: unblurred high-contrast bars → MTF ≈ 0.99, blur → 0.66. **MTF = image Michelson contrast ÷
`target_contrast`** (default 1.0, right for a chrome-on-glass USAF chart); the dialog surfaces this. The
module's `tests/test_usaf_mtf.py` use pytest, which isn't in the devenv venv — verified manually instead.

## Slanted-edge module `KrakenOS/EdgeMTF.py`

`measure_slanted_edge_mtf(image, roi=None, *, pixel_pitch_um=None, oversample=4)` → `SlantedEdgeMTFResult`
(`.frequency_cycles_per_px`, `.mtf`, `.mtf50_cycles_per_px()`, `.frequency_lp_mm()`, `.plot`,
`.save_csv`). ISO-12233 style: detect the edge axis (stronger mean |gradient|; transpose if horizontal)
→ per-row sub-pixel edge column (centroid of |d/dx|) → line-fit the slant → project every pixel onto the
edge normal → bin into a ×`oversample` supersampled ESF → LSF = d/dx ESF → Hann window → `|rfft|`
normalised at DC → MTF, capped at the native Nyquist 0.5 cyc/px. Verified on the user's `1.tif` (edge
−0.4°: MTF 1.0→0.47@0.1→0.09@0.25, MTF50 ≈ 0.095 cyc/px) and a synthetic edge (sharp ~1, blur lower).

## The dialog (two modes)

`panels/mtf_from_image_dialog.py` `open_mtf_from_image_dialog(editor)` — File → **"Measure MTF from
Image..."**. A **Target** selector switches modes; the image is shown scaled-to-fit, the full-res
grayscale kept for the fit, and every ROI is stored in **original image pixels** (`canvas coord / scale`).

- **Slanted edge (default)** — drag ONE box over a dark/bright edge → **Compute** →
  `measure_slanted_edge_mtf` → the whole MTF curve (cycles/pixel; lp/mm at the sensor if a pixel pitch is
  set); status reports the edge angle + MTF50.
- **USAF three-bar** — set Group / Element / Bars, drag a box over EACH three-bar element (Element
  auto-advances 1→6) → **Compute** → `analyze_usaf_image` → one point per element (object or image-space
  with a magnification).
- **Calibration** (optional): pixel pitch (both modes); magnification + target contrast (USAF).
- **Save CSV** → `result.save_csv` (both result types implement it).

## Verification (`validate_open3d_mtf_from_image`, penta phase 335)

Display-free — exercises the analysis through the dialog's exact ROI-dict API + getsource wiring:

| check | asserts |
|---|---|
| ANALYZE | USAF: synthetic high-contrast bars → MTF ≈ 1 unblurred; blur lowers it; non-empty curve |
| EDGE | slanted-edge MTF starts at 1 (DC), capped at Nyquist 0.5 cyc/px, blur reduces it |
| WIRING | File menu "Measure MTF from Image..." → `open_mtf_from_image_dialog`; editor delegates to the dialog |
| CONTRACT | the dialog offers edge + USAF modes, binds canvas ROI drawing, stores ROIs in image px, computes, plots, saves CSV |

4/4 pass. Also headless-Tk construction-smoked (Xvfb): the Toplevel + all widgets + the empty plot
build and tear down cleanly.

## Files

- `KrakenOS/EdgeMTF.py` — slanted-edge (ISO 12233) MTF module.
- `KrakenOS/UI/panels/mtf_from_image_dialog.py` — the interactive two-mode dialog.
- `KrakenOS/UI/services/layout_import_export.py` — `open_mtf_from_image_dialog` editor opener.
- `KrakenOS/UI/panels/main_window.py` — File-menu entry.
- `KrakenOS/UI/validate_open3d_mtf_from_image.py` — guard (penta phase 335).
- (`KrakenOS/USAFMTF.py` + `tests/test_usaf_mtf.py` are the user's, commit `03dfa2ce`.)

## In-app eyeball still owed

File → "Measure MTF from Image..." → Import `attachment/1.tif` (default **Slanted edge** mode) → drag ONE
box over the edge → **Compute** → a falling MTF curve (not a straight line); Save CSV. Then try **USAF
three-bar** mode on a bar-target capture (a box per element).

## Scope / next

Possible follow-ons: rotation-per-ROI field for the USAF mode (module supports `rotation_deg`); zoom/pan
for very large captures (currently scaled-to-fit); an averaged multi-edge (SFR) measurement.
