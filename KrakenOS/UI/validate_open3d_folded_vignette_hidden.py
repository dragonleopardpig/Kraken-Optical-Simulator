"""Display-free guard for bugs/0389 + 0390 -- on the REAL folded RA-mirror scene, rays that
fold at the mirror then FAIL at a real downstream element (vignette at the aperture stop =
``stopped`` [0389], or miss the detector = ``missed_detector`` [0390]) must HIDE with
clipping OFF; the folded image-forming beam stays visible.

The synthetic predicate is guarded by validate_open3d_clipped_vignetting_parity; this guard
proves the fix fires on the actual traced AZ85 folded scene and is NOT vacuous:

  - there IS a population of folded-AND-``stopped`` rays (field-edge rays that fold at the RA
    mirror then clip the F/4.5 aperture stop -- correct physics, the beam is wider than the
    stop). Before the fix these rendered as "broken" stubs terminating mid-air at the stop.
  - every one of them is now HIDDEN by ray_path_visible_without_clipping_from_events
    (clipping OFF), exactly like a non-folded vignetted stray.
  - the imaging rays that fold at the mirror and reach the sensor (``hit_detector``) stay
    VISIBLE -- the fix hides only the vignetted folds, not the real image-forming beam.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_vignette_hidden
Exit: 0 = pass, 1 = regression. (Traces a folded scene -- ~30s.)
"""

from __future__ import annotations

import contextlib
import io


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import (
                _build_editor,
                _AZ85,
            )
            from KrakenOS.UI.scene_geometry import (
                ray_path_visible_without_clipping_from_events as VIS,
                ray_path_terminal_status_from_events as STATUS,
                ray_path_has_non_refractive_steering as STEER,
            )

            editor = _build_editor(_AZ85)
            _system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
            paths = None
            for attr in ("paths", "ray_paths", "scene_paths"):
                v = getattr(bundle, attr, None)
                if v:
                    paths = list(v)
                    break
    except Exception as exc:  # pragma: no cover - environment/trace failure
        return False, [f"folded trace failed: {exc!r}"]

    if not paths:
        return False, ["no traced ray paths on the AZ85 folded scene (guard precondition gone)"]

    folded_stopped_visible = folded_stopped_total = 0
    imaging_visible = imaging_total = 0
    for p in paths:
        status = STATUS(p)
        folded = bool(STEER(p))
        visible = bool(VIS(p))
        if folded and status == "stopped":
            folded_stopped_total += 1
            if visible:
                folded_stopped_visible += 1
        if status == "hit_detector":
            imaging_total += 1
            if visible:
                imaging_visible += 1

    notes.append(
        f"AZ85 folded scene: {len(paths)} paths; folded+stopped={folded_stopped_total}; "
        f"hit_detector={imaging_total}"
    )

    # (1) non-vacuous: the scene must actually produce folded-then-vignetted strays (0389)
    if folded_stopped_total == 0:
        failures.append(
            "vacuous: no folded+stopped rays on AZ85 -- the FOV/aperture that clips the field "
            "edges is gone, so this guard proves nothing"
        )
    # (2) every folded-stopped ray hides with clipping OFF (bugs/0389)
    if folded_stopped_visible != 0:
        failures.append(
            f"{folded_stopped_visible}/{folded_stopped_total} folded+vignetted rays still "
            "VISIBLE with clipping OFF (drawn as 'broken' stubs) -- 0389 regressed"
        )
    # (3) the image-forming beam stays visible (fix must not blank real rays)
    if imaging_total == 0:
        failures.append("no hit_detector imaging rays on AZ85 (precondition gone)")
    elif imaging_visible != imaging_total:
        failures.append(
            f"only {imaging_visible}/{imaging_total} imaging rays visible -- the fix wrongly "
            "hid image-forming rays"
        )

    # (4) bugs/0390: folded rays that MISS the detector must also hide. Manufacture them
    # non-vacuously by shrinking the sensor so folded imaging rays fall outside it (the same
    # class as rays that fold at mirror 1, skip the wider-than-aperture mirror 2, and spray
    # past it -- the folded display scores those missed_detector).
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor2 = _build_editor(_AZ85)
            editor2.rows[-1].diameter = 2.0
            _s2, _r2, bundle2 = editor2._build_preview_system_rays_bundle(update_state=True)
            paths2 = None
            for attr in ("paths", "ray_paths", "scene_paths"):
                v = getattr(bundle2, attr, None)
                if v:
                    paths2 = list(v)
                    break
    except Exception as exc:  # pragma: no cover
        return False, [f"shrunk-detector trace failed: {exc!r}"]
    fm_total = fm_visible = 0
    for p in (paths2 or []):
        if bool(STEER(p)) and STATUS(p) == "missed_detector":
            fm_total += 1
            if bool(VIS(p)):
                fm_visible += 1
    notes.append(f"AZ85 tiny-sensor: folded+missed_detector={fm_total}")
    if fm_total == 0:
        failures.append(
            "vacuous: shrinking the sensor produced no folded+missed_detector rays -- 0390 "
            "path unexercised"
        )
    if fm_visible != 0:
        failures.append(
            f"{fm_visible}/{fm_total} folded+missed_detector rays still VISIBLE with clipping "
            "OFF (spray-past-the-mirror strays) -- 0390 regressed"
        )

    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    if not passed:
        print("Folded-vignette-hidden validation FAILED:")
        for m in messages:
            print(f"- {m}")
        return 1
    print("Folded-vignette-hidden validation passed:")
    for m in messages:
        print(f"  {m}")
    print(
        "  folded+vignetted rays hide with clipping OFF; the folded image-forming beam stays "
        "visible."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
