# 0058 — Open 3D: wire the new attachment/Cameras into camera selection

## Reported (direct request)

> There are a few cameras added in attachment/Cameras, can you wire them into
> camera selection option?

`attachment/Cameras/` had gained two new camera bundles (STEP + datasheet) that
were not represented in `CAMERA_DATABASE`, so the camera-selection dropdown still
listed only the single "Allied Vision hr25MCX".

## Root cause

Not a defect — the catalogue (`KrakenOS/UI/camera_database.py`) is hand-authored.
The dropdown is populated from `camera_names()` (sorted `CAMERA_DATABASE` keys),
fed to `MainFieldControlsPanel` (`values=[None, *camera_names()]`), so adding the
new files to disk does nothing until a record is added to the dict.

## Fix

Added two records to `CAMERA_DATABASE`, spec'd from the datasheets in
`attachment/Cameras/`; both resolve their `step_path`/`datasheet` via
`_preferred_existing_path` so they stay attachment-relative and portable:

- **Allied Vision shr661MCX12** (`shr661MCX12_Datasheet.pdf`,
  `3D_CAD_shr661MCX.STEP`) — Sony IMX661 CMOS global shutter, 13392 × 9528
  (127.6 MP), sensor 46.2 × 32.87 mm (diagonal 56.7 mm), pixel 3.45 µm, code
  F004141, M72×0.75 mount, body 83 × 80 × 80 mm. `camera_front_to_sensor_mm`
  19.88 (datasheet optical backfocus).
- **Japan Bopixel BC-GM65M12X4-F** (`BC-Gx65M12X4_Spec_ver04_EN.pdf`,
  `BC-GM(C)65M12X4-F.STEP.step`) — Gpixel GMAX3265 mono CMOS global shutter,
  9344 × 7000 (65 MP), pixel 3.2 µm → sensor 29.90 × 22.40 mm (diagonal
  37.36 mm), F-mount straight, body 92 × 80 × 80 mm. `camera_front_to_sensor_mm`
  46.5 (Nikon-F flange focal distance; the STEP is the F-mount variant).

The computed diagonals match the datasheet values (56.7 / 37.36 mm), so
`camera_image_coverage_mm` / `camera_sensor_active_mm` and the detector-overlay
footprint read the real sensor. No UI wiring change was needed — the combobox
already enumerates `camera_names()`.

## Tests

`validate_attachment_paths.py` gains an **every camera resolves attachment
files** check: for every name in `camera_names()`, both `step_path` and
`datasheet` must be under `attachment/` *and* exist on disk. PASS for all three
cameras (previously the path check only covered hr25MCX).
