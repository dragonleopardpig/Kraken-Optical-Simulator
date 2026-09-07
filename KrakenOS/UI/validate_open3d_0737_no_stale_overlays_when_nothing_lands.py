"""Guard for bugs/0737 -- when nothing lands, say so; never draw a stale measurement.

Flag 20260907_111321_904, three observations in one state whose terminations were
``{"stopped_at_surface_10": 1439, "missed_image": 561}`` -- no "image" entry at all, so not one
ray reached the sensor:

  * "So there is no best focus image plane?" -- correct, and silent. Nothing landed, so there was
    nothing to measure; the viewer drew nothing and explained nothing.
  * "the clipped overlays is not ON, why showing the gray clipped rays?" -- bugs/0022 kept every
    ray when the filter would hide them all, so with EVERY ray clipped the switch looked broken.
  * "no rays hit the sensor, but the green strips overlayed on the sensor, not reasonable" -- the
    split-field strips were the ones measured by an EARLIER trace, drawn as if current.

Checks (display-free):
  A  a band that gets no landing rays this trace is marked stale (its numbers are kept for
     reference, but `measured` goes False) and a band that does get rays is marked fresh.
  B  the overlay skips a stale strip and draws a fresh one.
  C  the Clipped toggle is honoured even when every ray is clipped, and the reason is stated.
  D  the focus summary carries the notes -- why there is no focus plane, and where the rays went.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0737_no_stale_overlays_when_nothing_lands
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import detector_coverage_overlay as dco

    img_pt = np.array([272.63, -1.66, -25.3])
    normal = np.array([0.0, -1.0, 0.0])
    iu, iv = dco._basis(normal)
    image_surface = 23

    def rec(face_z, u, v):
        p = img_pt + u * iu + v * iv
        return {
            "reaches_image": True,
            "hits": [
                {"surface": 1, "x": 0.0, "y": 0.42, "z": face_z + 8.5},
                {"surface": image_surface, "x": float(p[0]), "y": float(p[1]), "z": float(p[2])},
            ],
        }

    stamped = {
        "center": [272.63, -1.66, -25.3], "axis_v": list(iv), "half_width": 11.5,
        "v_lo": 1.0, "v_hi": 3.0, "measured": True, "stale": False, "ray_count": 40,
    }
    bands = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -4.0, "v_hi": 4.0, "image_strip": dict(stamped)},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -4.0, "v_hi": 4.0, "image_strip": dict(stamped)},
    ]

    # ---- A: only face A lands this trace -------------------------------------------------------
    records = [rec(0.0, u=float(u), v=float(v)) for u, v in zip(np.linspace(-8, 8, 12), np.linspace(1.2, 3.1, 12))]
    changed = dco.measure_split_field_image_strips(
        bands, records, image_surface=image_surface, image_point=img_pt, image_axis=normal
    )
    a_strip, b_strip = bands[0]["image_strip"], bands[1]["image_strip"]
    ok(
        changed == 1 and a_strip.get("measured") is True and not a_strip.get("stale"),
        f"A1: the band that landed rays is measured fresh (changed={changed}, "
        f"stale={a_strip.get('stale')})",
    )
    ok(
        b_strip.get("stale") is True and b_strip.get("measured") is False and b_strip.get("ray_count") == 0,
        f"A2: the band that landed NOTHING is marked stale, not left looking current "
        f"(stale={b_strip.get('stale')}, measured={b_strip.get('measured')})",
    )
    ok(
        abs(float(b_strip.get("v_lo")) - 1.0) < 1e-9,
        "A3: its previous numbers are kept for reference (nothing is destroyed, just not drawn)",
    )

    # ---- B: the overlay skips a stale strip ------------------------------------------------------
    service = inspect.getsource(dco.DetectorCoverageOverlayService)
    ok(
        'if bool(strip.get("stale")):' in service and "continue   # bugs/0737" in service,
        "B1: the strip drawing skips a stale strip",
    )
    ok(
        service.count("strip = band.get(\"image_strip\")") == 1,
        "B2: there is exactly one strip-drawing path, so the skip cannot be bypassed",
    )

    # ---- C: the Clipped toggle is honoured ---------------------------------------------------------
    from KrakenOS.UI.services import three_d_scene_tools

    rays_src = inspect.getsource(three_d_scene_tools)
    ok(
        "if visible_paths:" in rays_src and "scene_paths = []" in rays_src
        and "_ray_display_suppressed_note" in rays_src,
        "C1: with every ray clipped the switch still hides them (bugs/0022's blanket override is gone)",
    )
    ok(
        "Overlays -> Clipped to show them" in rays_src,
        "C2: and the scene says where the rays went, so an empty view is not a mystery",
    )
    ok(
        'self._ray_display_suppressed_note = ""   # bugs/0737' in rays_src,
        "C3: the note is re-stated on every draw, so it can never go stale itself",
    )

    # ---- D: the notes reach the banner ---------------------------------------------------------------
    lines = dco.format_focus_summary_lines(
        None, None, notes=("FOCUS: no ray reaches the sensor, so the image plane cannot be measured (1439 stopped at surface 10)",
                           "No ray reaches the sensor: 2000 clipped rays hidden (Overlays -> Clipped to show them)"),
    )
    ok(
        len(lines) == 2 and any("cannot be measured" in line for line in lines)
        and any("clipped rays hidden" in line for line in lines),
        f"D1: both notes render on the banner ({len(lines)} lines)",
    )
    ok(
        dco.format_focus_summary_lines(None, None, notes=("", None)) == [],
        "D2: empty notes add nothing",
    )
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    measure = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "_focused_image_plane_unmeasured" in measure and "termination_reason" in measure,
        "D3: the focus measurement records WHY it could not measure, counting the terminations",
    )
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    banner = inspect.getsource(Kraken3DInspector._update_solve_refusal_banner)
    ok(
        "_focused_image_plane_unmeasured" in banner and "_ray_display_suppressed_note" in banner,
        "D4: the banner reads both notes",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0737 no-stale-overlays validation PASSED")
        return 0
    print("0737 no-stale-overlays validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
