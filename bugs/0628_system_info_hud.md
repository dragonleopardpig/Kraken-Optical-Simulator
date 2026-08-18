# 0628 — system-info HUD on the 3D canvas (FEATURE, user request 2026-08-18)

Four rows, top-left of the Open 3D canvas, refreshed with every scene refresh:

    Resolution:    <delivered FOV / camera pixel count>  um/px
    Magnification: <sensor size / delivered FOV>  (the optical |m| -- the user's
                   corrected definition)
    Pixels:        N1 x N2         (camera record)
    Pixel size:    w um            (camera record)

- FOV source: `object_fov_dimensions()` -- the SAME delivered-field reader as the
  drawn green FOV square (bugs/0602 doctrine), so the two can never disagree.
- Pure formatter `format_system_info_lines` + gatherer `system_info_hud_text` in
  `services/system_info_hud.py`; actor in `_update_system_info_hud` (normalized-
  viewport anchor, top-justified); hook after the coverage overlays in the refresh.
- Rows degrade per-source: no camera -> optical rows only; no finite FOV -> pixel
  rows only; nothing -> the HUD hides. Axis values merge when within 1%, else both.
- TRAP fixed during verification: the refresh's RemoveAllViewProps DETACHES a kept
  actor -- the updater re-attaches via HasViewProp every refresh (probe v1: actor
  "present" but invisible).

Verified: bugs/_0628_system_info_hud.png (Apo75 + hr25MCX: 5.502 um/px, 0.818x,
5120 x 5120, 4.5 um). Guard: phase 472 (`validate_open3d_0628_system_info_hud`).
