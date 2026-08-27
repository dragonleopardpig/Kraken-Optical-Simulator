# 0655 — Camera folder import: Edmund stock page + only-the-first-PDF veto

**User (2026-08-27 13:48, error.png):** "Could not import a camera from this folder:
.../Cameras/Basler_Ace — Could not extract a sensor size from this folder."

The folder held the Basler MECHANICAL DRAWING PDF (2012, 664 chars of title block),
the STP, a DXF, and `spec_35917.pdf` — the Edmund stock page for the acA2440-20gm the
user dropped in at 12:58 precisely to feed the import.

## Two independent causes

1. **Primary-PDF veto:** `build_camera_record_from_assets` parsed ONLY
   `assets.primary_pdf` — the alphabetically-first PDF, i.e. the drawing. The spec
   sheet beside it was never opened. Fix: try EVERY PDF in scan order (a proper
   vendor datasheet still sorts first and keeps precedence); the first that yields a
   sensor size feeds the record, and `record["datasheet"]` is re-pointed at the PDF
   that actually fed it.
2. **Edmund camera stock-page labels:** all label-glued rows the parser had no
   patterns for — `Sensing Area, H x V (mm):8.45 x 7.07` (the sensor size stated
   DIRECTLY), `Pixels (H x V):2,448 x 2,048`, `Pixel Size, H x V (μm):3.45 x 3.45`,
   `Model Number:acA2440-20gm`, `Mount:C-Mount` (a named-mount token match, so
   "Tripod Mount Adapter" cannot false-positive). Also latent: `_scrape_flange`
   keyed "C-MOUNT" against a table keyed "C" — every "-Mount"-suffixed spelling
   silently missed the standard FFD; the suffix now strips.

## Verified

Basler_Ace imports end-to-end: sensor 8.45 × 7.07 mm (resolution × pitch cross-checks
it exactly), 2448 × 2048 @ 3.45 µm, C-Mount → front→sensor 17.526, datasheet pointer
= spec_35917.pdf, name "Basler acA2440-20gm". Existing camera-import guard untouched
and green. Guard `validate_open3d_0655_edmund_camera_stock_page` (penta phase 491):
parser rows + pitch corroboration, builder iterates all PDFs + datasheet re-point +
flange suffix strip, real-folder import.
