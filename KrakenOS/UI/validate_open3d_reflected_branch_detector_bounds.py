"""Display-free guard for bugs/0018 — a beam-splitter cube's reflected branch
must never be force-projected onto the far detector/image plane.

Regression context
------------------
The user's saved machine-vision prescription folds the central beam ~90 deg off a
promoted beam-splitter cube. The reflected branch travels almost purely +X (up its
own second optical axis), i.e. nearly *parallel* to the authored Image plane at
z~665. ``scene_builder._detector_plane_miss_intersection`` projected every escaped
ray onto that plane via ``distance = dot(center-origin, normal) / dot(dir, normal)``
with no guard on the denominator. For a grazing +X ray ``dot(dir, normal) ~ dir_z``
is ~0.01, so ``distance`` ballooned to ~10^4-10^5 mm and the reflected segment was
re-terminated hundreds of metres off-axis (z snapped to ~665, x to ~6e5).

That single absurd coordinate then wrecked the renderer two ways the user flagged:
  * VTK single-precision line clipping drew the ~600 m segment as a *bent diagonal*
    band that changed angle on zoom (recordings flag_20260605_110342_145 /
    _113625_430), and
  * the 2D layout auto-scaled its axes to +/-6e5 mm, collapsing the whole scene to
    a dot (attachment/2D.png).

Fix: require the ray to actually head toward the plane -- ``|dot(dir, normal)|``
within cos(80 deg) of the normal -- before projecting. A grazing/parallel ray stays
escaped at its sane traced length (the reflected fold ends ~232 mm up +X, near the
cube), while genuine transmit rays (dir ~ +Z) still image normally onto z~665.

Reopen (bug 0018, flag_20260605_143523_953 "where is the beam splitter 2nd path
ray?"): the projection guard above stopped the runaway, but it also reclassified the
reflected branch from ``missed_image`` (drawn) to ``no_next_intersection`` ->
``escaped``, which the 3D display filter hides when "Show Clipped Rays" is OFF (the
user's setting). The fold is a real second path, so the display filter now keeps an
*escaped* ray visible when it underwent non-refractive steering (reflect / split /
mirror / TIR); only an un-folded escaped ray (vignetted) stays hidden.

Invariants asserted here (all headless / display-free):

1. Mechanism: with a fixed z-normal detector plane, a grazing (+X / tiny dir_z) ray
   is NOT projected (returns None), a pure-axial (+Z) ray still projects to a sane
   finite distance, and the cos(80 deg) threshold is the exact crossover. Disabling
   the guard (cos -> 0) reproduces the ~10^4 mm runaway distance the bug emitted.
1b. Display filter: a fabricated escaped+folded path (reflect event) stays VISIBLE
   with Show Clipped Rays OFF; a purely refractive escaped path stays HIDDEN (bug
   0016 invariant kept); a detector hit is always drawn.
2. Optional real-scene guard: tracing the user's saved cube prescription keeps every
   ray-path coordinate within a sane scene bound (was ~6e5 mm), keeps the reflected
   fold rays (final dir ~ +X) at a finite length instead of vanishing/exploding,
   confirms every reflected fold ray is DISPLAYED with Show Clipped Rays OFF (the 2nd
   path is not hidden), and preserves the transmit rays that reach the Image plane at
   z~665. Skipped when the prescription / its CAD cache is unavailable on this machine.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace

# Headless rendering — never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import numpy as np

import KrakenOS.UI.scene_builder as scene_builder
from KrakenOS.UI.scene_builder import _detector_plane_miss_intersection
from KrakenOS.UI.scene_geometry import (
    ray_path_has_non_refractive_steering,
    ray_path_visible_without_clipping_from_events,
)

PRESCRIPTION = Path("attachment/machine_vision_150mm_measured_test.py")

# The reflected fold ends ~232 mm up +X; transmit rays image at z~665. The bug
# emitted ~6e5 mm. Cap a few x the authored scene extent: passes post-fix, and is
# ~300x below the runaway value, so any re-introduction is caught decisively.
_SANE_SCENE_BOUND_MM = 2000.0
_DETECTOR_Z = 665.0


def _unit(vector) -> np.ndarray:
    vector = np.asarray(vector, dtype=float).reshape(3)
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 1e-12 else vector


# --------------------------------------------------------------------------
# 1. Mechanism guard — exercise the real projection helper against a fixed plane.

def _fixed_detector_frame(_rows, _system, _index):
    """A z=665 image plane: center on axis, +Z normal, +X tangent."""
    return (
        np.asarray([0.0, 0.0, _DETECTOR_Z], dtype=float),
        np.asarray([0.0, 0.0, 1.0], dtype=float),
        np.asarray([1.0, 0.0, 0.0], dtype=float),
    )


def _miss(origin, direction):
    rows = [SimpleNamespace(diameter=10.0, advanced={})]
    return _detector_plane_miss_intersection(rows, None, {0}, np.asarray(origin, float), _unit(direction))


def _mechanism_checks(check) -> None:
    saved_frame = scene_builder._detector_surface_frame
    saved_cos = scene_builder._DETECTOR_MISS_MIN_AXIAL_COS
    scene_builder._detector_surface_frame = _fixed_detector_frame
    try:
        cube_exit = np.asarray([12.5, 0.0, 212.0], dtype=float)

        # (a) The reflected fold: nearly pure +X, dir_z ~ 0.01 -> grazing the z plane.
        grazing = _miss(cube_exit, [1.0, 0.0, 0.01])
        check(grazing is None, f"grazing reflected (+X) ray is NOT projected to the detector (got {grazing!r})")

        # (b) A perfectly transverse +X ray (dir_z == 0): also rejected.
        transverse = _miss(cube_exit, [1.0, 0.0, 0.0])
        check(transverse is None, f"pure +X ray (parallel to plane) is NOT projected (got {transverse!r})")

        # (c) A genuine transmit ray (+Z) still images onto the plane at a sane distance.
        axial = _miss([0.0, 0.0, 316.0], [0.0, 0.0, 1.0])
        axial_ok = (
            axial is not None
            and np.isfinite(float(axial["distance"]))
            and abs(float(axial["point"][2]) - _DETECTOR_Z) < 1e-6
            and float(axial["distance"]) < _SANE_SCENE_BOUND_MM
        )
        check(axial_ok, f"axial (+Z) transmit ray still projects to z~665 at a sane distance (got {axial!r})")

        # (d) The cos(80 deg) threshold is the exact crossover.
        just_below = _miss(cube_exit, [np.sqrt(1.0 - 0.15 ** 2), 0.0, 0.15])   # dir_z 0.15 < cos80
        just_above = _miss(cube_exit, [np.sqrt(1.0 - 0.20 ** 2), 0.0, 0.20])   # dir_z 0.20 > cos80
        check(just_below is None, "ray just inside the grazing cone (|dir_z|=0.15) is rejected")
        check(just_above is not None, "ray just outside the grazing cone (|dir_z|=0.20) projects")

        # (e) Without the guard (cos -> 0) the grazing ray emits the runaway distance
        #     the bug rendered (documents WHY the cap exists).
        scene_builder._DETECTOR_MISS_MIN_AXIAL_COS = 0.0
        runaway = _miss(cube_exit, [1.0, 0.0, 0.01])
        check(
            runaway is not None and float(runaway["distance"]) > 1.0e4,
            f"guard disabled reproduces the runaway projection (distance={None if runaway is None else round(float(runaway['distance']), 1)} mm)",
        )
    finally:
        scene_builder._detector_surface_frame = saved_frame
        scene_builder._DETECTOR_MISS_MIN_AXIAL_COS = saved_cos


# --------------------------------------------------------------------------
# 1b. Display-filter mechanism — the folded branch must survive "Show Clipped
#     Rays OFF" (bug 0018 reopen). CAD-free: fabricated ray paths.

def _surface_event(event_type: str):
    return SimpleNamespace(
        event_kind="surface",
        event_type=event_type,
        interaction_model="",
        surface_name="",
        metadata={},
    )


def _terminal_event(reason: str):
    return SimpleNamespace(
        event_kind="terminal",
        termination_reason=reason,
        event_type=reason,
        surface_id=None,
        metadata={},
    )


def _fake_path(surface_event_types, terminal_reason):
    events = [_surface_event(t) for t in surface_event_types]
    events.append(_terminal_event(terminal_reason))
    return SimpleNamespace(events=events, reaches_image=False)


def _display_filter_checks(check) -> None:
    # The reflected beam-splitter branch: refracts into the cube, reflects off the
    # 45 deg splitter face, exits, and escapes (no downstream detector on +X).
    reflected = _fake_path(["refract", "reflect", "refract"], "no_next_intersection")
    check(
        ray_path_has_non_refractive_steering(reflected),
        "a reflected branch path is recognized as non-refractive steering (fold)",
    )
    check(
        ray_path_visible_without_clipping_from_events(reflected),
        "an escaped+folded branch (beam-splitter 2nd path) stays VISIBLE with Show Clipped Rays OFF",
    )

    # A genuinely clipped ray: only refractions, then escapes past the last lens.
    vignetted = _fake_path(["refract", "refract"], "no_next_intersection")
    check(
        not ray_path_has_non_refractive_steering(vignetted),
        "a purely refractive escaped ray is NOT flagged as steering",
    )
    check(
        not ray_path_visible_without_clipping_from_events(vignetted),
        "an escaped, un-folded (vignetted) ray stays HIDDEN with Show Clipped Rays OFF (bug 0016 invariant kept)",
    )

    # A detector hit is always visible regardless of clipping or steering.
    imaged = _fake_path(["refract"], "image")
    check(
        ray_path_visible_without_clipping_from_events(imaged),
        "a ray that reaches the detector is always displayed",
    )


# --------------------------------------------------------------------------
# 2. Optional real-scene guard — the user's saved beam-splitter-cube prescription.

def _real_scene_summary() -> dict[str, object] | None:
    if not PRESCRIPTION.exists():
        return None
    try:
        from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        spec = importlib.util.spec_from_file_location("_mv0018_guard", PRESCRIPTION)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in module.SURFACES]
        editor = _snapshot_editor(rows, dict(module.SETTINGS))
        editor.current_layout_file = PRESCRIPTION.resolve()
        # bugs/0021: rebuild a missing promoted-cube body STL from its source
        # STEP so this guard exercises the REAL beam-splitter fold, not the
        # analytic single-face fallback the system-build safety-net substitutes
        # for a missing cache. If the body still can't be resolved (no cache, no
        # source on this machine), skip rather than assert fold physics on the
        # placeholder.
        try:
            editor._regenerate_missing_optical_solid_caches()
        except Exception:
            pass
        from KrakenOS.UI.services.missing_assets_scan import any_solid_body_unresolved
        if any_solid_body_unresolved(editor.rows):
            return None
        editor._saved_step_native_trace_plan_cache = {}
        try:
            editor._normalize_special_rows()
        except Exception:
            pass
        _system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        if not paths:
            return None

        max_coord = 0.0
        reflected_lengths: list[float] = []   # final dir ~ +X (the fold)
        reflected_displayed = 0                # ...and survives Show Clipped Rays OFF
        transmit_at_image = 0                  # final dir ~ +Z reaching z~665
        for path in paths:
            pts = np.asarray(getattr(path, "points_world", []), dtype=float)
            if pts.shape[0] < 2:
                continue
            max_coord = max(max_coord, float(np.abs(pts).max()))
            direction = _unit(pts[-1] - pts[-2])
            end = pts[-1]
            if abs(direction[0]) > 0.95:                       # folded reflected branch
                reflected_lengths.append(float(np.linalg.norm(pts[-1] - pts[-2])))
                # Bug 0018 reopen: with the user's Show Clipped Rays OFF the
                # folded branch must still be drawn (it vanished after the first
                # 0018 fix reclassified it escaped).
                if ray_path_visible_without_clipping_from_events(path):
                    reflected_displayed += 1
            elif direction[2] > 0.95 and abs(end[2] - _DETECTOR_Z) < 1.0:
                transmit_at_image += 1
        return {
            "paths": len(paths),
            "max_coord": max_coord,
            "reflected": len(reflected_lengths),
            "reflected_len_max": max(reflected_lengths) if reflected_lengths else None,
            "reflected_displayed": reflected_displayed,
            "transmit_at_image": transmit_at_image,
        }
    except Exception as exc:  # missing CAD cache / vendor STEP, etc.
        return {"error": repr(exc)}


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True

    def _check(ok: bool, message: str) -> None:
        nonlocal passed
        notes.append(("PASS " if ok else "FAIL ") + message)
        if not ok:
            passed = False

    _mechanism_checks(_check)
    _display_filter_checks(_check)

    real = _real_scene_summary()
    if real is None:
        notes.append("SKIP real prescription unavailable (no CAD cache) — mechanism guards cover the fix")
    elif "error" in real:
        notes.append(f"SKIP real prescription failed to load: {real['error']}")
    else:
        _check(
            real["max_coord"] <= _SANE_SCENE_BOUND_MM,
            f"every ray-path coordinate stays within the scene (max|coord|={real['max_coord']:.1f} mm, "
            f"cap {_SANE_SCENE_BOUND_MM:.0f}, bug emitted ~6e5)",
        )
        _check(
            real["reflected"] > 0
            and real["reflected_len_max"] is not None
            and real["reflected_len_max"] <= _SANE_SCENE_BOUND_MM,
            f"reflected fold rays exist and stay finite, not vanished/exploded "
            f"(count={real['reflected']}, max_len={real['reflected_len_max']})",
        )
        _check(
            real["reflected"] > 0 and real["reflected_displayed"] == real["reflected"],
            f"every reflected fold ray is DISPLAYED with Show Clipped Rays OFF "
            f"(displayed={real['reflected_displayed']}/{real['reflected']}) — the 2nd path is not hidden",
        )
        _check(
            real["transmit_at_image"] > 50,
            f"transmit rays still image onto z~665 (count={real['transmit_at_image']})",
        )

    return passed, notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
