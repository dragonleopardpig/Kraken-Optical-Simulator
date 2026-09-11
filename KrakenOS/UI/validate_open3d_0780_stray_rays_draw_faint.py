"""Guard for bugs/0780 -- stray light that reached the sensor by another route draws FAINT.

Flag `20260911_160208_046`, on build 40d35e2f (the bugs/0779 fix): *"I still see many stray rays
flying around."* The measurement was already right -- the banner read "Landed: the blur on the
sensor (2.27 um) is inside one pixel" and "STRAY LIGHT: 6 ray(s) reach the sensor by another optical
route" -- but the scene still drew those cross-arm rays exactly like image light: same colour, same
opacity, same width.

They are real traced light, so the bugs/0530 doctrine applies: never hide true light, weight it.
bugs/0604 set that precedent for beam-splitter ghost forests (opacity follows power, floor 0.15).
The same rule the focus measurement uses (bugs/0779 split_stray_routes) now classifies each draw's
landing rays, and the draw loops multiply a stray ray's opacity by 0.15. The Normal-to-Sensor view
(bugs/0606), which shows only the light that forms the image, leaves them out.

Checks (display-free; the REAL ThreeDSceneToolsMixin._iter_3d_scene_ray_records and
_ray_stray_route_display_weight are driven by a stub on the bugs/0779 synthetic split field):
  A  exactly the stray-route rays are classified, over the whole bundle before the draw budget thins
     it; clean bundles classify nothing; a new draw clears the previous draw's classification;
  B  their terminal status is untouched, so their drawn geometry is too;
  C  the weight is 0.15 -- bugs/0604's floor -- and 1.0 for image light or no path;
  D  both scene draw loops apply the weight and drop stray rays in the Normal-to-Sensor view;
  E  the banner's STRAY LIGHT line says they are drawn faint.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0780_stray_rays_draw_faint
"""

from __future__ import annotations

import inspect
import types

import numpy as np


def _stub(show_clipped: bool = False):
    import KrakenOS.UI.services.three_d_scene_tools as tds

    tds.__dict__.setdefault("np", np)

    class Stub(tds.ThreeDSceneToolsMixin):
        def __init__(self):
            self.show_clipped_rays_var = types.SimpleNamespace(get=lambda: show_clipped)
            self.last_rays = None
            self._last_scene_bundle = None

    return Stub()


def _landing(paths):
    for path in paths:
        path.reaches_image = str(getattr(path, "termination_reason", "")) in ("image", "target_termination")
    return paths


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines
    from KrakenOS.UI.validate_open3d_0779_stray_routes_are_not_the_image import (
        GHOST_ROUTE,
        detector_bundle,
        split_field_paths,
    )

    ghost_paths = _landing(split_field_paths(ghosts=True))
    ghosts = [p for p in ghost_paths if tuple(p.surface_ids) == GHOST_ROUTE]
    image = [p for p in ghost_paths if tuple(p.surface_ids) != GHOST_ROUTE]
    bundle = detector_bundle(ghost_paths)

    # ---- A: classification ---------------------------------------------------------------------
    stub = _stub()
    records = stub._iter_3d_scene_ray_records(None, bundle)
    ids = set(stub.__dict__.get("_stray_route_path_ids") or ())
    ok(len(ghosts) == 8 and ids == {id(p) for p in ghosts},
       f"A1: exactly the 8 stray-route rays are classified ({len(ids)} of {len(ghost_paths)} paths)")
    ok(0 < len(records) < len(ghost_paths) and len(ids) == 8,
       f"A2: the classification covers the whole bundle even though the draw budget drew only "
       f"{len(records)} of {len(ghost_paths)} rays")
    clean_paths = _landing(split_field_paths())
    stub._iter_3d_scene_ray_records(None, detector_bundle(clean_paths))
    ok(not (stub.__dict__.get("_stray_route_path_ids") or ()),
       "A3: a bundle with no stray light classifies nothing")
    ok(stub._ray_stray_route_display_weight(ghosts[0]) == 1.0,
       "A4: and a new draw clears the previous draw's classification -- no stale fading")
    shown = _stub(show_clipped=True)
    shown._iter_3d_scene_ray_records(None, bundle)
    ok(len(shown.__dict__.get("_stray_route_path_ids") or ()) == 8,
       "A5: with clipped rays shown the stray rays are still classified -- faint either way")

    # ---- B: status and geometry untouched --------------------------------------------------------
    stub = _stub()
    all_records = _stub(show_clipped=True)._iter_3d_scene_ray_records(None, detector_bundle(ghost_paths[-8:] + image[:40]))
    statuses = {str(status) for _i, _c, _p, status in all_records}
    ok(statuses == {"hit_detector"},
       f"B1: a stray ray keeps its terminal status ({statuses}) -- the fade is an opacity weight, so "
       f"the bounding and clipping that key on status draw its path exactly as before")

    # ---- C: the weight -------------------------------------------------------------------------------
    stub._iter_3d_scene_ray_records(None, bundle)
    ok(stub._ray_stray_route_display_weight(ghosts[0]) == 0.15, "C1: a stray ray draws at weight 0.15")
    ok(stub._ray_stray_route_display_weight(image[0]) == 1.0, "C2: image light keeps full weight")
    ok(stub._ray_stray_route_display_weight(None) == 1.0, "C3: no path (a legacy ray) keeps full weight")
    import KrakenOS.UI.services.three_d_scene_tools as tds

    floor = tds.ThreeDSceneToolsMixin._ray_branch_power_display_weight("s->a->b", 0.0)
    ok(float(tds.ThreeDSceneToolsMixin._STRAY_ROUTE_DISPLAY_WEIGHT) == float(floor) == 0.15,
       "C4: the weight IS bugs/0604's ghost floor -- one faint level for stray light, not a new one")

    # ---- D: both draw loops --------------------------------------------------------------------------
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    src = inspect.getsource(Open3DSceneRefreshService)
    ok(src.count("self.editor._ray_stray_route_display_weight(ray_path)") == 2,
       "D1: both scene draw loops (_refresh_rays_only and refresh_scene) ask for the stray weight")
    ok(src.count("* power_weight * stray_weight") == 2,
       "D2: and both multiply it into the ray's opacity")
    ok(src.count("stray_weight < 1.0") == 2,
       "D3: and both drop stray rays in the Normal-to-Sensor view, which shows the image")

    # ---- E: the banner -------------------------------------------------------------------------------
    info = {"offset_mm": 0.0, "stray_light": {"rays": 6, "outside": 6, "share": 0.009, "worst_outside_mm": 1.9}}
    text = "\n".join(format_focus_summary_lines(info, None))
    ok("drawn faint in the 3D scene" in text, f"E1: the banner says the stray light is drawn faint ({text!r})")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0780 stray-rays-draw-faint validation PASSED")
        return 0
    print("0780 stray-rays-draw-faint validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
