# 0631 — System Selection Calculator (FEATURE, user request)

User: *"practical situation: I am given FOV and system resolution requirement, need to
determine a matching lens and camera with minimum WD given as well."*

This superseded the reverted bugs/0630 (which solved the current lens's thickness for a
target magnification/resolution -- the wrong question). The real task is SELECTION/SIZING
from requirements.

## What shipped

**Actions → System Selection Calculator...** -- a modeless dialog. Enter FOV (w×h),
object-space resolution (µm/px), minimum working distance, and a candidate sensor size
(prefilled from the current scene + registered camera); it live-computes:

- **Camera:** ≥ N×N px  (`N = FOV·1000 / r`, rounded up -- the sampling requirement)
- **Magnification:** `m = sensor / FOV`  (the bugs/0628 HUD definition)
- **Lens image circle:** ≥ sensor diagonal
- **Lens EFL:** ≥ `WD_min·m/(m+1)` mm, with the WD it yields (thin-lens
  `WD = f(m+1)/m`; longer EFL → longer WD)
- **Pixel pitch** at that sensor, and whether the **registered camera** meets the pixel
  requirement.

Pure first-order optics in `services/system_selection.py` (`compute_system_selection`
+ helpers) -- display-free and guardable; the dialog only renders it. Without a sensor
size it returns the pixel-count requirement alone. A FOV/sensor aspect mismatch is noted.

## Verified

- Guard phase 473 (`validate_open3d_0631_system_selection`): the pixel/mag/WD relations
  are exact and round-trip (EFL≥22.7 → WD 200), the worked example, no-sensor degrade,
  aspect flag, bad-input rejection, and the editor + Actions-menu wiring.
- Headless dialog drive + screenshot: bugs/_0631_system_selection_calculator.png
  (FOV 100, r 50 µm/px, WD 200, sensor 12.8 → 2000px, 0.128×, EFL≥22.7, pitch 6.4µm).

## Next (on request): the catalog MATCHER -- scan registered cameras + lens catalogs and
list the combinations that meet all three requirements.
