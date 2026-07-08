"""Display-free guard for the coaxial-LED illumination-RAYS overlay (Feature B2).

Feature A drapes the dark edges on the sensor as a heatmap; THIS overlay draws the mechanism behind
them -- the REAL traced LED->beam-splitter->object rays, coloured by fate. Green rays reach the
FOV/detector; red rays terminate early at the foreshortened BS-exit stop (the 55*cos45~39 clip that
darkens the two fold-axis FOV edges in production). Rays killed at the LED's own source aperture
collapse to a dot and are dropped.

This guard is display-free (pure numpy + a headless trace, no VTK). It pins:

  * PURE GEOMETRY (``build_source_illumination_rays_overlay``): synthetic records split into reaching
    (green) vs clipped (red) by the reach flags; degenerate source-plane dots are dropped; a foreign
    ``source_role`` is filtered out WHEN illumination rays exist; the merged VTK line cell-arrays are
    well formed; the clip plane
    is the clipped-terminal median z; and -- the load-bearing one -- the FOLD AXIS is named by
    comparing the clipped terminals against the SURVIVOR aperture envelope, NOT by raw spread. The
    fixture deliberately makes the clipped rays spread WIDER on the perpendicular axis (they fill it)
    than on the fold axis they are cut on, so a naive "widest-spread" heuristic would name the wrong
    axis; the survivor-envelope test must still return the fold axis. The limiting BS-exit-stop clear
    aperture (Feature B1), read off the survivors, is a well-formed rectangle outline at the clip
    plane, NARROWER on the fold axis than across, and the clipped rays reach BEYOND it on the fold axis.
  * ROLE FALLBACK: a scene whose LED ``source_role`` did NOT round-trip to the literal "illumination"
    (blank / None / a different tag) must STILL draw the rays -- fall back to every traced ray rather
    than collapse to None -- while staying dormant when the role DOES match. This is the live-app bug
    (flags 20260708_1516..1519) where the heatmap rendered but this overlay drew nothing.
  * INTEGRATION on the real coaxial-LED BS scene: ``source_illumination_rays_overlay_spec`` returns
    BOTH reaching and clipped rays, the clip plane sits at the BS-exit stop (~75, clearly upstream of
    the ~130 detector), the fold axis is X (the foreshortened 55->39 axis), the stop aperture is
    foreshortened on the fold axis with the clipped rays overhanging it, and it is CACHED (a second
    call returns the same object -- bugs/0166).
  * RENDER-ONLY / TOGGLE contract: ``refresh_scene`` reads ``show_source_illumination_rays_var`` and
    calls ``_add_source_illumination_ray_overlays``; that renderer never rebuilds the system; and the
    Overlays menu exposes the toggle.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_source_illumination_rays

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

from KrakenOS.UI.services import source_illumination_rays_overlay as sir
from KrakenOS.UI.validate_open3d_source_illumination_overlay import _build_coaxial_overlay

# Deterministic trace budget for the integration check. 8000 rays already give a stable
# reaching/clipped split and an unambiguous fold-axis (X) signal on the coaxial-LED scene.
_TRACE_RAYS = int(os.environ.get("COAXIAL_RAYS_OVERLAY_RAYS", "8000"))


def _synthetic_records(seed=7, n_reach=48, n_clip=48, aperture_x=14.0, aperture_y=37.0, stick_x=27.0):
    """Records that mimic the coaxial trace: survivors cross the stop aperture (narrow on the fold/x
    axis) and land on the detector; clipped rays die AT the stop, sticking OUT past the fold aperture
    on x while spreading across the FULL perpendicular y -- so their raw y-spread is WIDER than their
    x-spread even though x is the axis they are cut on. Plus source-plane dots (dropped) and a foreign
    imaging ray (filtered by role)."""
    rng = np.random.default_rng(seed)
    records: list[dict] = []
    for i in range(n_reach):
        x75 = float(rng.uniform(-aperture_x, aperture_x))
        y75 = float(rng.uniform(-aperture_y, aperture_y))
        # Exercise both reach flags: half via reaches_image, half via reaches_detector.
        flag = {"reaches_image": True} if i % 2 == 0 else {"reaches_detector": True}
        records.append({
            "source_role": "illumination",
            "source_x": x75 * 0.4, "source_y": y75 * 0.4, "source_z": 0.0,
            "hits": [{"x": x75, "y": y75, "z": 75.0}, {"x": x75 * 1.1, "y": y75 * 1.1, "z": 130.0}],
            **flag,
        })
    for _ in range(n_clip):
        sign = 1.0 if rng.random() < 0.5 else -1.0
        x75 = float(sign * rng.uniform(aperture_x + 1.0, stick_x))
        y75 = float(rng.uniform(-aperture_y, aperture_y))
        records.append({
            "source_role": "illumination",
            "source_x": x75 * 0.4, "source_y": y75 * 0.4, "source_z": 0.0,
            "hits": [{"x": x75, "y": y75, "z": 75.0}],
            "reaches_image": False,
        })
    for _ in range(6):  # killed at the LED source aperture -> a dot at z=0, no story -> dropped
        records.append({
            "source_role": "illumination",
            "source_x": 0.0, "source_y": 0.0, "source_z": 0.0,
            "hits": [{"x": 0.0, "y": 0.0, "z": 0.0}],
            "reaches_image": False,
        })
    records.append({  # a non-illumination ray must be filtered out by role
        "source_role": "imaging",
        "source_x": 0.0, "source_y": 0.0, "source_z": 0.0,
        "hits": [{"x": 0.0, "y": 0.0, "z": 75.0}, {"x": 0.0, "y": 0.0, "z": 130.0}],
        "reaches_image": True,
    })
    return records, n_reach, n_clip


def _validate_line_cells(points: np.ndarray, lines: np.ndarray) -> str | None:
    """Walk a VTK poly-line cell array [n0, i0.., n1, j0.., ...]; return an error string or None."""
    n_points = int(points.shape[0])
    idx = 0
    cells = 0
    lines = np.asarray(lines, dtype=np.int64)
    while idx < lines.size:
        count = int(lines[idx])
        if count < 2:
            return f"cell {cells} has {count} vertices (< 2)"
        seg = lines[idx + 1: idx + 1 + count]
        if seg.size != count:
            return f"cell {cells} truncated (want {count} indices, got {seg.size})"
        if seg.min() < 0 or seg.max() >= n_points:
            return f"cell {cells} index out of range [0,{n_points})"
        idx += count + 1
        cells += 1
    if idx != lines.size:
        return "cell array did not consume exactly"
    return None


def _check_pure_geometry(failures: list[str]) -> None:
    records, n_reach, n_clip = _synthetic_records()

    spec = sir.build_source_illumination_rays_overlay(records)
    if spec is None:
        failures.append("PURE: build_source_illumination_rays_overlay returned None for valid records")
        return

    if spec.get("kind") != "source_illumination_rays":
        failures.append(f"PURE: kind {spec.get('kind')!r} != 'source_illumination_rays'")
    # Classification: the source-plane dots (6) and the imaging ray (1) are dropped/filtered.
    if int(spec["reaching_total"]) != n_reach:
        failures.append(f"PURE: reaching_total {spec['reaching_total']} != {n_reach}")
    if int(spec["clipped_total"]) != n_clip:
        failures.append(f"PURE: clipped_total {spec['clipped_total']} != {n_clip}")

    # Well-formed VTK cell arrays for both classes.
    for name in ("reaching", "clipped"):
        pts = np.asarray(spec[f"{name}_points"], dtype=float)
        lines = np.asarray(spec[f"{name}_lines"], dtype=np.int64)
        if pts.ndim != 2 or pts.shape[1] != 3:
            failures.append(f"PURE: {name}_points shape {pts.shape} is not (N, 3)")
            continue
        err = _validate_line_cells(pts, lines)
        if err is not None:
            failures.append(f"PURE: {name}_lines malformed -- {err}")

    # Clip plane = median terminal z of the clipped rays (the stop at z=75 in the fixture).
    z = spec.get("clip_plane_z")
    if z is None or not np.isclose(z, 75.0, atol=1e-6):
        failures.append(f"PURE: clip_plane_z {z} != 75.0 (clipped-terminal median)")

    # THE load-bearing check: the clipped rays spread WIDER on y (perp) than x (fold) here, so a raw
    # "widest spread" heuristic would answer 'Y'. The survivor-envelope test must answer 'X' (fold).
    clipped_term = np.asarray([
        (r["hits"][-1]["x"], r["hits"][-1]["y"]) for r in records
        if r.get("source_role") == "illumination" and not r.get("reaches_image")
        and not r.get("reaches_detector") and r["hits"][-1]["z"] > 1.0
    ], dtype=float)
    if clipped_term.size:
        raw_wider = "Y" if np.ptp(clipped_term[:, 1]) > np.ptp(clipped_term[:, 0]) else "X"
        if raw_wider != "Y":
            failures.append("PURE: fixture is miscalibrated -- clipped rays should spread wider on Y")
    if spec.get("clip_axis") != "X":
        failures.append(
            f"PURE: fold/clip axis {spec.get('clip_axis')!r} != 'X' -- the survivor-envelope test "
            "regressed to naming the widest-spread axis (Y) instead of the foreshortened fold axis"
        )

    # Limiting BS-exit-stop aperture (Feature B1): a well-formed rectangle outline at the clip plane,
    # read off the survivors, NARROWER on the fold axis (x) than across (y), with the clipped rays
    # reaching BEYOND it on the fold axis (that is what "clipped" means here).
    ap_pts = np.asarray(spec.get("aperture_points"), dtype=float)
    ap_lines = np.asarray(spec.get("aperture_lines"), dtype=np.int64)
    if ap_pts.shape != (5, 3):
        failures.append(f"PURE: aperture_points shape {ap_pts.shape} != (5, 3) closed rectangle loop")
    else:
        if not np.allclose(ap_pts[:, 2], 75.0, atol=1e-6):
            failures.append("PURE: aperture rectangle is not on the clip plane z=75")
        if not np.allclose(ap_pts[0], ap_pts[-1]):
            failures.append("PURE: aperture rectangle loop is not closed (first != last vertex)")
        err = _validate_line_cells(ap_pts, ap_lines)
        if err is not None:
            failures.append(f"PURE: aperture_lines malformed -- {err}")
    aperture_half = spec.get("aperture_half")
    clipped_half = spec.get("clipped_half")
    if not aperture_half or not clipped_half:
        failures.append("PURE: aperture_half / clipped_half missing (survivor aperture not measured)")
    else:
        if not (aperture_half[0] < aperture_half[1] - 1.0):
            failures.append(
                f"PURE: aperture not foreshortened on the fold axis "
                f"(x half {aperture_half[0]:.1f} !< y half {aperture_half[1]:.1f})"
            )
        if not (clipped_half[0] > aperture_half[0] + 1.0):
            failures.append(
                f"PURE: clipped rays do not reach past the aperture on the fold axis "
                f"(clipped x {clipped_half[0]:.1f} !> aperture x {aperture_half[0]:.1f})"
            )

    # Subsample cap: totals stay full, drawn is capped, and the cap is deterministic.
    capped = sir.build_source_illumination_rays_overlay(records, max_per_class=10, seed=7)
    if capped is None:
        failures.append("PURE: capped overlay returned None")
    else:
        if int(capped["reaching_total"]) != n_reach or int(capped["clipped_total"]) != n_clip:
            failures.append("PURE: subsampling changed the totals (should cap only the DRAWN count)")
        if int(capped["reaching_drawn"]) != 10 or int(capped["clipped_drawn"]) != 10:
            failures.append(
                f"PURE: drawn not capped to 10 (reaching {capped['reaching_drawn']}, "
                f"clipped {capped['clipped_drawn']})"
            )
        again = sir.build_source_illumination_rays_overlay(records, max_per_class=10, seed=7)
        if not np.array_equal(np.asarray(again["clipped_points"]), np.asarray(capped["clipped_points"])):
            failures.append("PURE: subsampling is not deterministic for a fixed seed")

    # Degenerate inputs -> None (nothing to draw).
    if sir.build_source_illumination_rays_overlay([]) is not None:
        failures.append("PURE: empty records did not return None")
    dots = [r for r in records if r["hits"][-1]["z"] <= 1.0]  # the source-plane dots only
    if sir.build_source_illumination_rays_overlay(dots) is not None:
        failures.append("PURE: an all-degenerate record set did not return None")


def _check_role_fallback(failures: list[str]) -> None:
    """A user-built scene whose LED source role did NOT round-trip to the literal 'illumination' must
    STILL draw the rays -- fall back to every traced ray rather than silently collapsing to None. This
    is the live-app bug behind flags 20260708_1516..1519: the heatmap (Feature A, role-agnostic)
    rendered while THIS overlay drew nothing, because the strict role gate matched no record. The
    fallback must also stay DORMANT whenever some record DOES match the role -- the foreign imaging ray
    in the fixture stays filtered -- so a normal tagged scene is unchanged."""
    records, n_reach, n_clip = _synthetic_records()

    # Dormancy: with the role present, the fallback must NOT fire -- the foreign 'imaging' ray stays
    # out, so the tagged counts are exactly the illumination split (48/48), never 49/48.
    tagged = sir.build_source_illumination_rays_overlay(records)
    if tagged is None:
        failures.append("FALLBACK: baseline (tagged) overlay is None -- fixture broken")
        return
    if int(tagged["reaching_total"]) != n_reach or int(tagged["clipped_total"]) != n_clip:
        failures.append(
            "FALLBACK: the fallback is NOT dormant when the role matches -- the foreign imaging ray "
            f"leaked in (reaching {tagged['reaching_total']}!={n_reach} / clipped "
            f"{tagged['clipped_total']}!={n_clip})"
        )

    # The bug: blank/foreign the role on every record. Each variant must still draw BOTH classes, not
    # None, and never fewer rays than the role-gated path (the fallback sees >= as many records).
    for blanker, label in ((lambda r: "", "''"), (lambda r: None, "None"), (lambda r: "led", "'led'")):
        mangled = [dict(r) for r in records]
        for r in mangled:
            r["source_role"] = blanker(r)
        spec = sir.build_source_illumination_rays_overlay(mangled)
        if spec is None:
            failures.append(
                f"FALLBACK: role={label} collapsed the overlay to None instead of falling back to "
                "all traced rays (the live-app 'Illum rays draws nothing' bug)"
            )
            continue
        if not (int(spec["reaching_total"]) > 0 and int(spec["clipped_total"]) > 0):
            failures.append(
                f"FALLBACK: role={label} fell back but lost a class "
                f"(reaching {spec['reaching_total']}, clipped {spec['clipped_total']})"
            )
        if (int(spec["reaching_total"]) < int(tagged["reaching_total"])
                or int(spec["clipped_total"]) < int(tagged["clipped_total"])):
            failures.append(
                f"FALLBACK: role={label} drew FEWER rays than the tagged path "
                f"({spec['reaching_total']}/{spec['clipped_total']} < "
                f"{tagged['reaching_total']}/{tagged['clipped_total']})"
            )


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_coaxial_overlay(_TRACE_RAYS)
    if editor is None:
        notes.append("SKIP integration: coaxial-LED layout/bundle unavailable")
        return
    try:
        spec = editor.source_illumination_rays_overlay_spec(system, bundle)
    except Exception as exc:
        failures.append(f"INTEGRATION: source_illumination_rays_overlay_spec raised {exc!r}")
        return
    if not spec:
        failures.append("INTEGRATION: rays overlay spec is None on the coaxial-LED BS scene")
        return

    if spec.get("kind") != "source_illumination_rays":
        failures.append(f"INTEGRATION: kind {spec.get('kind')!r} != 'source_illumination_rays'")
    if not (int(spec["reaching_total"]) > 0 and int(spec["clipped_total"]) > 0):
        failures.append(
            f"INTEGRATION: expected BOTH reaching and clipped rays "
            f"(reaching {spec['reaching_total']}, clipped {spec['clipped_total']})"
        )
    z = spec.get("clip_plane_z")
    det_z = spec.get("detector_z")
    if z is None or not (50.0 <= float(z) <= 100.0):
        failures.append(f"INTEGRATION: clip plane z={z} is not the BS-exit stop (~75)")
    if det_z is not None and z is not None and not (float(z) < float(det_z) - 20.0):
        failures.append(
            f"INTEGRATION: clip plane z={z} is not clearly upstream of the detector z={det_z}"
        )
    if spec.get("clip_axis") != "X":
        failures.append(
            f"INTEGRATION: fold/clip axis {spec.get('clip_axis')!r} != 'X' (foreshortened 55->39 axis)"
        )
    aperture_half = spec.get("aperture_half")
    clipped_half = spec.get("clipped_half")
    if not aperture_half or not clipped_half:
        failures.append("INTEGRATION: limiting-aperture half-extents not measured on the real scene")
    else:
        if not (aperture_half[0] < aperture_half[1]):
            failures.append(
                f"INTEGRATION: BS-exit-stop aperture not foreshortened on the fold axis "
                f"(x half {aperture_half[0]:.1f} !< y half {aperture_half[1]:.1f})"
            )
        if not (clipped_half[0] > aperture_half[0]):
            failures.append("INTEGRATION: clipped rays do not overhang the aperture on the fold axis")
    if editor.source_illumination_rays_overlay_spec(system, bundle) is not spec:
        failures.append("INTEGRATION: rays overlay is not cached (re-traces every call) -- breaks bugs/0166")
    ap = spec.get("aperture_half")
    ap_text = ""
    if ap:
        ap_text = f", stop aperture ~{2 * ap[0]:.0f}x{2 * ap[1]:.0f} mm (fold x perp)"
    notes.append(
        f"integration: {_TRACE_RAYS} rays -> reaching {spec['reaching_total']} / clipped "
        f"{spec['clipped_total']} at z={float(z):.1f}, fold axis {spec.get('clip_axis')}{ap_text}"
    )


def _check_source_contracts(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import Kraken3DInspector
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_source_illumination_rays_var" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not read show_source_illumination_rays_var")
    if "_add_source_illumination_ray_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not call _add_source_illumination_ray_overlays")

    add_src = inspect.getsource(Kraken3DInspector._add_source_illumination_ray_overlays)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(
                f"CONTRACT: _add_source_illumination_ray_overlays references {forbidden!r} -- not render-only"
            )

    from KrakenOS.UI.panels import open3d_top_controls
    controls_src = inspect.getsource(open3d_top_controls)
    if "show_source_illumination_rays_var" not in controls_src:
        failures.append("CONTRACT: the Overlays menu does not offer the illumination-rays toggle")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure_geometry(failures)
    _check_role_fallback(failures)
    _check_integration(failures, notes)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] coaxial-LED illumination-rays overlay")
        return 1
    print("[PASS] coaxial-LED LED->BS->object rays split green=reaches / red=clipped at the BS-exit stop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
