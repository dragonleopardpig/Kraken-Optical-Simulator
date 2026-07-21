"""Display-free guard for bugs/0062 — the 3D "Show clipped rays" filter must hide
non-folded vignetting just like 2D does (detector hits + folds only when OFF).

Regression context
------------------
After bugs/0061 synced the *toggle state* between 2D and 3D, the two views still
disagreed on *which* rays the toggle hid. With clipping OFF:

- **2D** (``scene_renderer_2d._draw_rays`` -> ``projected_ray_hits_detector``)
  kept only rays whose terminal status is ``hit_detector``.
- **3D** (``ray_path_visible_without_clipping_from_events``) hid only *escaped,
  non-folded* rays — so rays that vignetted and ``stopped`` at an aperture stop
  / lens rim, or that ``missed_detector``, still rendered in 3D.

The user's machine-vision LED layout fans rays past the optics; ~38% ``stopped``
on the aperture. Turning clipping OFF cleared them in 2D but left them in 3D
("disable clipped rays still show up"). Bug 0062 tightened the 3D predicate to
the 2D rule: visible-when-OFF iff the ray hit the detector **or** underwent a
deliberate fold (reflect / mirror / TIR / split / grating, per bugs/0018). A
fold is a real authored branch the user asked for (a beam-splitter 2nd path),
so it survives even with no detector to land on — **except** when a downstream
aperture then *vignetted* it (``stopped``): bugs/0389 found that folded field-
edge rays on the RA-mirror scene fold at the mirror then clip the F/4.5 aperture
stop, and were drawn as "broken" stubs terminating mid-air at the stop. A
vignetted folded ray is a blocked stray, not an authored branch, and hides with
clipping OFF; ``absorbed`` / ``missed`` / escaped folds still survive (a real
beam-splitter 2nd path is ``hit_detector`` / ``absorbed`` / escaped, never
``stopped``, as the MV-150 scene confirms). The 2D filter has no fold exception.

Checks
------
1. Predicate semantics (synthetic ``RayPath3D``): clipped-OFF keeps the detector
   hit and folded branches that were NOT vignetted (folded escape); it hides the
   non-folded stop/miss/escape AND the folded-then-``stopped`` vignetted stray
   (bugs/0389).
2. Real-layout parity (``machine_vision_150mm_datasheet_1x.py`` — a fold-free
   LED -> lens -> camera scene with genuine aperture vignetting):
   - the 3D ray filter renders every traced path with clipping ON;
   - with clipping OFF it keeps exactly the detector-hit paths (drops the
     vignetted strays);
   - that OFF count equals the number of rays the 2D filter keeps
     (``projected_ray_hits_detector``) — the two views now agree.
   Skipped if the layout is unavailable on this machine.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clipped_vignetting_parity

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import os
from pathlib import Path

# Headless rendering — never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
_PARITY_LAYOUT = "machine_vision_150mm_datasheet_1x.py"


def _synthetic_paths():
    """One RayPath3D per (terminal class x folded?) case the predicate gates."""
    from KrakenOS.UI.scene_geometry import RayEvent3D, RayPath3D

    def _terminal(reason: str) -> RayEvent3D:
        return RayEvent3D(event_kind="terminal", termination_reason=reason)

    def _fold() -> RayEvent3D:
        return RayEvent3D(event_kind="surface", event_type="reflect", surface_name="beam_splitter")

    pts = np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 10.0]], dtype=float)

    def _path(index: int, events) -> RayPath3D:
        return RayPath3D(ray_index=index, wavelength=0.55, color="#39FF14",
                         points_world=pts.copy(), events=list(events))

    # (label, events, visible-when-clipped-OFF)
    return [
        ("hit_detector", _path(0, [_terminal("detector")]), True),
        ("stopped_nofold", _path(1, [_terminal("aperture_stop")]), False),
        ("missed_nofold", _path(2, [_terminal("missed_detector")]), False),
        ("escaped_nofold", _path(3, [_terminal("no_hit")]), False),
        # A folded ray that then FAILED at a real downstream element -- ``stopped`` (vignetted
        # at an aperture, bugs/0389) or ``missed_detector`` (missed an existing detector's
        # clear aperture, bugs/0390) -- is a blocked/missed stray, NOT an authored branch, so
        # it hides with clipping OFF. Two folded RA-mirror cases proved it: field-edge rays
        # fold at the mirror then clip the F/4.5 aperture stop (drawn as "broken" stubs at the
        # stop), and illumination rays that fold at mirror 1, skip the wider-than-aperture
        # mirror 2, and spray past it (folded display scores them ``missed_detector``). A real
        # beam-splitter 2nd path never lands here -- it hits its detector (``hit_detector``),
        # is ``absorbed``, or escapes with no detector to land on (``escaped_folded``), all
        # still kept visible.
        ("stopped_folded", _path(4, [_fold(), _terminal("aperture_stop")]), False),
        ("missed_folded", _path(6, [_fold(), _terminal("missed_detector")]), False),
        ("escaped_folded", _path(5, [_fold(), _terminal("no_hit")]), True),
    ]


def _traced_layout(fname: str):
    """Build editor + system + rays + bundle for a SURFACES/SETTINGS layout."""
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import (
        _build_system_from_specs,
        _load_python_data,
        _rows_from_layout_info,
        _snapshot_editor,
    )

    path = LAYOUT_DIR / fname
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = str(path)
    editor._normalize_special_rows()
    row_specs = [
        {
            "surface": r.surface, "name": r.name, "rc": r.rc, "k": r.k, "axicon": r.axicon,
            "diff_ord": r.diff_ord, "grating_d": r.grating_d, "grating_angle": r.grating_angle,
            "thickness": r.thickness, "diameter": r.diameter, "in_diameter": r.in_diameter,
            "drawing": r.drawing, "extra_data": r.extra_data, "uda": r.uda, "advanced": r.advanced,
            "tilt_x": r.tilt_x, "tilt_y": r.tilt_y, "tilt_z": r.tilt_z,
            "desp_x": r.desp_x, "desp_y": r.desp_y, "desp_z": r.desp_z,
            "axis_move": r.axis_move, "glass": r.glass,
        }
        for r in rows
    ]
    if row_specs and editor.metal_catalogs:
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(
        system, rays, wavelength, max_radius,
        allow_full_pupil=True, sampling_mode=editor._preview_2d_sampling_mode(),
    )
    editor.last_system = system
    editor.last_rays = rays
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return editor, rays, bundle


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    from KrakenOS.UI.scene_geometry import (
        ray_path_has_non_refractive_steering,
        ray_path_terminal_status_from_events,
        ray_path_visible_without_clipping_from_events,
    )

    notes: list[str] = []
    passed = True

    def _check(ok: bool, message: str) -> None:
        nonlocal passed
        notes.append(("PASS " if ok else "FAIL ") + message)
        if not ok:
            passed = False

    # --- 1. Predicate semantics (synthetic, no trace) --------------------
    for label, path, expected in _synthetic_paths():
        visible = ray_path_visible_without_clipping_from_events(path)
        _check(
            visible is expected,
            f"{label}: visible-when-clipped-OFF == {expected} (got {visible})",
        )

    # --- 2. Real-layout 2D/3D parity -------------------------------------
    if not (LAYOUT_DIR / _PARITY_LAYOUT).exists():
        notes.append(f"SKIP: {_PARITY_LAYOUT} missing -- parity not exercised on a real trace")
    else:
        from KrakenOS.UI.layout_plot_controller import project_scene_bundle
        from KrakenOS.UI.scene_geometry import projected_ray_hits_detector

        editor, rays, bundle = _traced_layout(_PARITY_LAYOUT)
        paths = list(getattr(bundle, "ray_paths", []) or [])
        total = len(paths)
        hit = sum(1 for p in paths if ray_path_terminal_status_from_events(p) == "hit_detector")
        folded = sum(1 for p in paths if ray_path_has_non_refractive_steering(p))

        # This datasheet scene is fold-free with genuine aperture vignetting, so
        # the 2D/3D keep-sets must be identical (both == the detector hits).
        _check(folded == 0, f"parity layout is fold-free (folded={folded})")
        _check(total > hit > 0, f"parity layout produces vignetted strays to hide (total={total} hit={hit})")

        editor.show_clipped_rays_var.set(True)
        on = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
        editor.show_clipped_rays_var.set(False)
        off = len(editor._iter_3d_scene_ray_records(rays=rays, scene_bundle=bundle))
        _check(on == total, f"3D clipped ON renders every traced path (on={on} total={total})")
        _check(off == hit, f"3D clipped OFF keeps only detector hits (off={off} hit={hit})")

        proj = project_scene_bundle(bundle, editor._current_display_orientation())
        prays = list(getattr(proj, "rays", []) or [])
        twod_kept = sum(1 for r in prays if projected_ray_hits_detector(r))
        _check(twod_kept == hit, f"2D filter keeps only detector hits (kept={twod_kept} hit={hit})")
        _check(off == twod_kept, f"3D clipped-OFF count matches 2D kept-ray count (off={off} 2D={twod_kept})")

    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
