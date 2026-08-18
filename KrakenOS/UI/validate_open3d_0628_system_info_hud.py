"""Guard for bugs/0628 — the system-info HUD (user feature, 2026-08-18).

Four rows on the 3D canvas: Resolution (delivered FOV / pixel count, um/px),
Magnification (sensor/FOV — the optical |m|, the user's corrected definition),
camera pixel count, pixel size.

Checks (display-free):
  A  FORMATTER — exact numbers on the Apo75+GMAX0505 example (FOV 55 -> 10.74 um/px,
     |m| 0.419); axis merging at 1%; graceful degradation (no camera -> optical rows
     only; no FOV -> pixel rows only; nothing -> hidden).
  B  CONTRACT — the gatherer reads the DELIVERED field via object_fov_dimensions
     (bugs/0602: the same reader as the drawn FOV square) and the scene refresh
     updates the HUD.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0628_system_info_hud
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import system_info_hud as hud

    # ---------------------------------------------------------------- A: formatter
    full = hud.format_system_info_lines((55.0, 55.0), (23.04, 23.04), (5120, 5120), (2.5, 2.5))
    want = [
        "Resolution: 10.74 um/px",
        "Magnification: 0.419x (sensor/FOV)",
        "Pixels: 5120 x 5120",
        "Pixel size: 2.5 um",
    ]
    no_camera = hud.format_system_info_lines((55.0, 55.0), (23.04, 23.04), None, None)
    no_fov = hud.format_system_info_lines(None, (23.04, 23.04), (5120, 5120), (2.5, 2.5))
    nothing = hud.format_system_info_lines(None, None, None, None)
    aniso = hud.format_system_info_lines((55.0, 41.25), (23.04, 23.04), (5120, 5120), (2.5, 2.5))
    if full != want:
        ok = False
        notes.append(f"FAIL: A (bugs/0628): formatter produced {full} != {want}")
    elif no_camera != ["Magnification: 0.419x (sensor/FOV)"]:
        ok = False
        notes.append(f"FAIL: A (bugs/0628): camera-less scene showed {no_camera}")
    elif no_fov != ["Pixels: 5120 x 5120", "Pixel size: 2.5 um"]:
        ok = False
        notes.append(f"FAIL: A (bugs/0628): FOV-less scene showed {no_fov}")
    elif nothing != []:
        ok = False
        notes.append(f"FAIL: A (bugs/0628): empty inputs still showed {nothing} -- HUD never hides")
    elif "/" not in aniso[0] or "/" not in aniso[1]:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0628): anisotropic FOV collapsed to one value ({aniso[:2]}) -- "
            "a non-square field must show both axes"
        )
    else:
        notes.append("PASS: A: exact rows, per-row degradation, anisotropy split")

    # ---------------------------------------------------------------- B: contracts
    gather_src = inspect.getsource(hud.system_info_hud_text)
    from KrakenOS.UI.services import open3d_scene_refresh as refresh_module

    refresh_src = inspect.getsource(refresh_module)
    if "object_fov_dimensions" not in gather_src:
        ok = False
        notes.append(
            "FAIL: B (bugs/0628): the gatherer no longer reads object_fov_dimensions -- "
            "the HUD would disagree with the drawn FOV square (bugs/0602 doctrine)"
        )
    elif "_update_system_info_hud" not in refresh_src:
        ok = False
        notes.append(
            "FAIL: B (bugs/0628): the scene refresh no longer updates the HUD -- it "
            "goes stale across solves/swaps"
        )
    else:
        notes.append("PASS: B: delivered-field source + refresh hook wired")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("System-info-HUD validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
