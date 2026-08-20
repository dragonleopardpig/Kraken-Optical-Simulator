# 0634 — Camera + Lens Catalog Matcher (FEATURE, user request)

User: *"go for the catalog matcher"* -- the follow-on to the bugs/0631 calculator: scan the
registered CAMERAS and the catalog LENSES and list which combinations meet a FOV /
resolution / minimum-WD requirement.

## What shipped

**Actions → Camera + Lens Matcher...** -- enter the requirement (FOV, resolution µm/px,
min WD, λ), click Match, and get a table of every camera × lens combination, PASSING
first (green), each row showing |m|, working distance, image circle, and f/# vs the
diffraction budget. Selecting a row explains a pass or the reasons it fails.

Per combination (pure core, `services/system_matcher.py`, guarded):
- **resolution** -- camera pixel count ≥ FOV/resolution (both axes)
- **magnification** -- m = sensor/FOV; a fixed-mag lens must bracket it (±5%), a
  fixed-focal lens can reach any m (WD then decides)
- **working distance** -- WD = f·(1+1/|m|) ≥ WD_min
- **image circle** -- lens image circle ≥ sensor diagonal
- **f/#** (advisory) -- lens nominal f/# vs the bugs/0633 diffraction budget

Enumeration (data map from the Explore pass):
- Cameras: `camera_database.CAMERA_DATABASE` (built-in + imported folded in).
- Lenses: `attachment/Lens/*` with an optical source, loaded headless via
  `import_lens_folder → SurrogateModel` (effl, image_diameter, aperture_value). Cached.
- Magnification range is NOT a surrogate field -- parsed from the name
  (`parse_magnification_range`: PYRITE compact "05x-20x"→0.5–2.0, "10x"→1.0, literal
  "0.5x-2.0x"; underscores are separators, so "85_05x" reads "05x" not "85.05", and
  "10x_V38" still parses -- both were real bugs caught in verification).

## Verified

- Guard phase 474 (`validate_open3d_0634_catalog_matcher`): the four hard fits + f/#
  advisory + ordering on synthetic catalogs; magnification parse cases; camera
  enumeration + dialog/editor/menu wiring.
- End-to-end on the real catalog (diag_0634_matcher_shot.py): 27 of 72 combinations match
  for FOV 55×55, 12 µm/px, WD 150 (8 cameras × 9 lenses). Screenshot bugs/_0634_matcher.png.

## Next (optional): the lens PDF scrape is ~10–20 s on first Match (cached after) -- a
background-thread enumeration would remove the brief freeze.
