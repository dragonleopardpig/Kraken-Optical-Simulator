# 0617 — A camera re-import wipes the user's flange-to-sensor distance (FIXED)

User (after flag_20260812_140652 follow-up): *"I did entered 12mm after import. Then I
noticed the camera is flipped, so I flipped it. Not sure it is the flip that causes
the None?"*

## What actually happened — the flip is innocent

Timeline reconstruction: the user imported BC-OM25M interactively and entered 12 mm at
the bugs/0309 flange prompt → persisted to `imported_cameras.json`. The flip
(`camera_step_reverse_direction`) touches no record. Then a **headless verification
re-import** (my probe for the previous flag) ran `import_vendor_camera_from_folder`
programmatically — and the import flow rebuilds the camera record by RE-SCRAPING the
folder. The flange distance is a mechanical-drawing dimension the scrape can never
recover, so the fresh record carried `None`, and `write_imported_camera` overwrote the
catalog — erasing the user's 12 mm. Any real re-import with a cancelled prompt (or any
programmatic re-import, per the bugs/0586 non-interactive rule) does the same.

An "already scraped — do not overwrite" guard existed in the prompt helper, but it read
the FRESH record, not the persisted catalog — so it never engaged on re-imports.

## Fix

`import_vendor_camera_from_folder` carries the persisted value forward: when the fresh
scrape lacks `camera_front_to_sensor_mm`, adopt it from the existing catalog entry
(by camera name) BEFORE the prompt/persist. The prompt now fires only for a genuinely
new camera; a cancelled prompt or headless re-import can no longer destroy earlier
work. The user's 12 mm was restored to the catalog (user-confirmed value).

Guard: phase 464's B legs assert the flange value survives both same-camera flows
(re-import and replace) unchanged.

## Process note

The wipe was caused by my own verification probe — a probe that exercises an
IMPORT flow mutates the user's persistent catalog, not just the in-memory scene.
Probes that run import/replace flows must either restore the catalog afterward or
run against a copy; "the scene is discarded on destroy()" does not cover
`attachment/`-persisted state.
