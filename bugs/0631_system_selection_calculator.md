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

## 0632 follow-up: self-fitting dialog + left-panel embedding (user request)

flag/attachment popup.png: the fixed-size dialog clipped its result text when the output
grew (e.g. the "camera UNDER the pixel requirement" line appears once you type). And the
user asked for the calculator in the 3D view's left panel too.

- The form is refactored into a shared `build_system_selection_form(parent, editor,
  compact=...)` used by BOTH the dialog and the panel (short labels + narrow entries in
  compact mode). Same bugs/0631 first-order core.
- The dialog is now `resizable(True, True)` and self-fits: a trace on the result grows the
  window to `winfo_reqheight` (never shrinking below the user's size), so the output never
  clips (bugs/_0632_dialog_selffit.png — the exact popup.png case now shows every line).
- 3D left panel: a "System Selection" LabelFrame section (Open3DLiveControlsPanel), with a
  "↺ From scene" button to re-pull FOV/sensor/pixels from the current scene
  (bugs/_0632_left_panel_section.png). It sits in the panel's scroll stack, so it never
  clips.

Guard phase 473 extended (check D): shared form, left-panel section, self-fitting dialog.

## 0633 follow-up: lens PERFORMANCE targets (user request)

After sizing the pixel, the lens must actually RESOLVE to it. Added (when a sensor size +
wavelength are given), from the required pixel pitch p and λ:

- **Sensor Nyquist** = `500/p` lp/mm — the spatial frequency the lens MTF must hold
  contrast at (the direct "can this lens feed the pixel" test).
- **Max working f/#** (diffraction Airy ≈ 2 px) = `p/(1.22·λ)`, with the **nominal**
  (infinity) f/# = working/(1+|m|) that lenses are specced by. Slower → diffraction blurs
  past a pixel; faster → aberrations usually dominate.
- **Target lens spot** ≤ `2·p` µm diameter (≈ 2 px geometric blur — the Nyquist match).

New **Wavelength (µm)** input (default 0.55) drives these. Verified: guard phase 473
check E (Nyquist = 1/(2·pitch); working f/# = p/(1.22λ); nominal = working/(1+m); λ=0
drops the diffraction f/# but keeps Nyquist). Screenshot bugs/_0633_dialog_perf_targets.png.
