# 0307 — "Could not extract a sensor size from this folder" (BC-OM25M camera import)

`attachment/error.png`, importing **`attachment/Cameras/BC-OM25M/`** (a Bopixel BC-OM25M12X2 camera folder:
mechanical `.STEP` + `BC-OM25M12X2 EN.pdf` datasheet):

> *Could not extract a sensor size from this folder.*

## Two compounding causes
1. **The datasheet PDF is unreadable to the shared stdlib text extractor.** BC-OM25M12X2's spec text is set in
   **CID fonts with no ToUnicode CMap** (plus rasterised image tables), so `extract_pdf_text` /
   `_decode_content` (the per-font CMap decoder shared by the camera *and* the datasheet lens Path-C importers)
   came back with ~8 garbage characters — the English spec table was never seen.
2. **Even when readable, there is no "Sensor size … mm" row.** The sheet gives the sensor only as
   **Active Pixel** `5120 (H) x 5120 (V)` and **Pixel Size** `4.5 (H) x 4.5 (V) µm`. `parse_camera_datasheet`
   only matched an explicit `Sensor size W×H mm` row, so `has_sensor_size` stayed false and the import bailed.

## The fix (both parts pure stdlib, general — no per-camera hardcoding)
**Part A — recover the text.** `datasheet_prescription_import.py` gains a **literal-harvest fallback**: when
the per-font ToUnicode decode comes back essentially empty (`_ascii_letter_count < 64`), harvest the raw
`(..)` show-string literals directly from the content streams, resolving PDF escapes (`\n \( \) \\` and
`\ddd` octal, decoded Latin-1 so the `µ` micro-sign / `\265` survive). This recovers any English spec text set
in *simple* (directly Latin-1) fonts. It is **gated** on the near-empty CMap decode, so a normal text-based
datasheet early-returns its CMap text unchanged — zero regression, and it still helps the lens Path-C importer
that shares this extractor.

**Part B — read the sensor as pixels × pitch.** `camera_folder_import.parse_camera_datasheet` now also:
* matches `Active Pixel` and the `5120 (H) x 5120 (V)` spec-table form for resolution (a `≥3-digit` guard keeps
  it off the pixel-pitch row's own `(H) x (V)`);
* matches the `4.5 (H) x 4.5 (V) µm` pixel-pitch form (anchored on the micro-sign);
* when there is **no** explicit sensor-size row, derives the active-area size = resolution × pixel pitch
  (µm → mm), with the diagonal via `math.hypot`.

## Result
BC-OM25M now scrapes to **23.04 × 23.04 mm**, diagonal **32.583**, **5120 × 5120**, **4.5 µm**, and builds a
record `BC-OM25M` with `image_diameter_mm = 23.04` — the same PYTHON 25K sensor as the Allied Vision hr25MCX,
which is why the delete-bug flag (0306) showed its ±16.29 mm half-diagonal. Importing the folder now succeeds
and couples the surrogate to the sensor exactly like picking the camera from the dropdown. A side benefit:
`BC-Gx65M` now also resolves (29.9 × 22.4). `BC-Gx25M` still returns None (a *scrambled* partial-CMap decode —
a different, harder failure; not a regression and not flagged).

## Files
- `KrakenOS/UI/services/datasheet_prescription_import.py` — `_LITERAL_SHOW_RE`, `_PDF_ESCAPE_SIMPLE`,
  `_MIN_DECODED_LETTERS`, `_ascii_letter_count`, `_unescape_pdf_literal`, `_harvest_literal_text`;
  `extract_pdf_text` falls back to the harvest when the CMap decode is near-empty.
- `KrakenOS/UI/services/camera_folder_import.py` — `parse_camera_datasheet` matches Active-Pixel / `(H) x (V)`
  resolution + `(H) x (V) µm` pixel pitch and computes the sensor size from resolution × pitch when no explicit
  size row exists.

## Verified (display-free)
- `parse_camera_datasheet(BC-OM25M12X2 EN.pdf)` → 23.04×23.04, 5120×5120, 4.5 µm; `build_camera_record_from_assets`
  → record `BC-OM25M`, image diameter 23.04.
- `KrakenOS/UI/validate_camera_folder_import.py` — **PASS**, with a new BC-OM25M real-asset assertion (skips
  cleanly when the Filen-synced folder is absent). Penta **phase 265** delegates to this guard.
- No regression on the shared extractor: the hr25MCX scrape still asserts 23.04/5120/4.5, and the datasheet
  **lens** Path-C cardinal scrape is unchanged — `validate_datasheet_lens_import`'s cardinal checks pass; its
  only failure is a **pre-existing, unrelated** wiring assertion (`self.editor.import_machine_vision_lens_from_folder(dialog_parent=self)`
  vs. the inspector's local-var `editor.…` at open3d_inspector.py:6344), untouched by this work.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): Open 3D → Import Camera from Folder → `attachment/Cameras/BC-OM25M`,
  and confirm the sensor couples (the object-plane FOV follows the 23.04 mm square sensor).
- `BC-Gx25M` scrambled-CMap decode is a separate, deferred parse gap (not user-flagged).
