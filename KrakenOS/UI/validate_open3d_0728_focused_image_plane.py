"""Guard for bugs/0728 -- show WHERE the image forms instead of only a defocused sensor.

User: "instead of showing ray defocusing at the sensor, show the perfect focus image detached
from the sensor and give a message focused image is located at XX.XX mm from the sensor" --
generalised to every scene, not just the om05a split field.

The image plane is MEASURED from the traced bundle after every trace: rays are grouped by field
(a pooled least-squares waist would minimise the IMAGE HEIGHT, not the blur), each field's waist
is solved analytically, and the best-sampled field decides the plane. It is drawn as a
sensor-sized magenta rectangle at that plane with a dashed connector to the sensor, and
summarised on the in-scene banner.

Checks (display-free, synthetic rays):
  A  focus_waist_from_rays: a perfect cone gives the exact offset and a ~zero waist; the side
     ("in front of" / "behind") follows the direction of travel, not the sign alone; too few
     rays, degenerate directions and collimated bundles return None.
  B  focus_waist_from_grouped_rays: grouping by field recovers the true waist where pooling is
     contaminated by image height; a field that does not converge is not allowed to vote; with
     no usable group it falls back to the pooled bundle and says so.
  C  focused_image_plane_specs: rectangle + dashed connector at centre + normal*offset, and
     NOTHING when the image already sits on the sensor.
  D  format_focus_summary_lines: the SOLVE line distinguishes a no-op from a move; the FOCUS
     line carries the distance, the side and both spot sizes; silence when in focus.
  E  wiring pins: measured after every real trace (2D refresh and 3D rebuild), drawn from the
     stash by the coverage overlay, and shown on the banner.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0728_focused_image_plane
"""

from __future__ import annotations

import inspect

import numpy as np


def _cone(centre, normal, waist_offset, *, field_shift=None, n_rays=24, radius=8.0, back=60.0):
    """Rays that pass through a point ``waist_offset`` along ``normal`` from ``centre`` and are
    reported where they cross the ``centre`` plane."""
    centre = np.asarray(centre, dtype=float)
    normal = np.asarray(normal, dtype=float)
    normal = normal / np.linalg.norm(normal)
    u, v = np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
    if abs(normal[0]) > 0.9:
        u, v = np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    waist = centre + normal * float(waist_offset)
    if field_shift is not None:
        waist = waist + np.asarray(field_shift, dtype=float)
    ends, dirs = [], []
    for k in range(int(n_rays)):
        ang = 2.0 * np.pi * k / int(n_rays)
        start = waist + (np.cos(ang) * u + np.sin(ang) * v) * float(radius) - normal * float(back)
        d = waist - start
        d = d / np.linalg.norm(d)
        t = float((centre - start) @ normal / (d @ normal))
        ends.append(start + d * t)
        dirs.append(d)
    return ends, dirs


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import (
        focus_waist_from_grouped_rays,
        focus_waist_from_rays,
        focused_image_plane_label_specs,
        focused_image_plane_specs,
        format_focus_summary_lines,
    )

    centre = np.array([272.63, -1.76, -25.0])
    normal = np.array([0.0, -1.0, 0.0])  # om05a: the sensor faces -y, light travels -y

    # ---- A: the single-bundle waist ---------------------------------------------------------
    ends, dirs = _cone(centre, normal, -20.0)
    info = focus_waist_from_rays(ends, dirs, image_point=centre, image_axis=normal)
    ok(
        info is not None and abs(info["offset_mm"] + 20.0) < 1e-6 and info["rms_waist_mm"] < 1e-6,
        f"A1: a perfect cone gives the exact waist offset and a ~zero spot there "
        f"({info['offset_mm']:.6f} mm, {info['rms_waist_mm']:.2e} mm)",
    )
    ok(
        info["side"] == "in front of" and info["rms_plane_mm"] > 1.0,
        f"A2: the side follows the direction of travel -- upstream reads 'in front of' "
        f"(side={info['side']}, spot at the sensor {info['rms_plane_mm']:.3f} mm)",
    )
    behind = focus_waist_from_rays(*_cone(centre, normal, +30.0), image_point=centre, image_axis=normal)
    ok(
        behind is not None and abs(behind["offset_mm"] - 30.0) < 1e-6 and behind["side"] == "behind",
        f"A3: a waist downstream of the sensor reads 'behind' ({behind['offset_mm']:.3f} mm)",
    )
    ok(
        focus_waist_from_rays(ends[:2], dirs[:2], image_point=centre, image_axis=normal) is None
        and focus_waist_from_rays([], [], image_point=centre, image_axis=normal) is None,
        "A4: too few rays -> no claim",
    )
    collimated_ends = [centre + np.array([x, 0.0, 0.0]) for x in np.linspace(-5, 5, 12)]
    collimated_dirs = [normal.copy() for _ in collimated_ends]
    ok(
        focus_waist_from_rays(collimated_ends, collimated_dirs, image_point=centre, image_axis=normal) is None,
        "A5: a collimated bundle has no waist to report (degenerate -> None, never a fabricated plane)",
    )

    # ---- B: grouping by field ----------------------------------------------------------------
    groups = [
        _cone(centre, normal, -20.0, field_shift=(0.0, 0.0, -6.0)),
        _cone(centre, normal, -20.0, field_shift=(0.0, 0.0, 0.0)),
        _cone(centre, normal, -20.0, field_shift=(0.0, 0.0, +6.0)),
    ]
    grouped = focus_waist_from_grouped_rays(groups, image_point=centre, image_axis=normal)
    pooled = focus_waist_from_rays(
        sum([list(g[0]) for g in groups], []), sum([list(g[1]) for g in groups], []),
        image_point=centre, image_axis=normal,
    )
    ok(
        grouped is not None and abs(grouped["offset_mm"] + 20.0) < 1e-6 and grouped["rms_waist_mm"] < 1e-6,
        f"B1: grouping by field recovers the true waist and a real spot "
        f"({grouped['offset_mm']:.4f} mm, {grouped['rms_waist_mm']:.2e} mm)",
    )
    ok(
        pooled is not None and pooled["rms_waist_mm"] > 1.0 and grouped["rms_waist_mm"] < pooled["rms_waist_mm"],
        f"B2: pooling every field reports the IMAGE HEIGHT as a 'spot' ({pooled['rms_waist_mm']:.3f} mm) -- "
        f"which is why the grouped measure exists",
    )
    ok(
        grouped["field_count"] == 3 and grouped["offset_spread_mm"] < 1e-6 and not grouped["pooled"],
        f"B3: every field votes and their spread is reported ({grouped['field_count']} fields, "
        f"spread {grouped['offset_spread_mm']:.2e} mm)",
    )
    noise = ([centre + np.array([0.1 * i, 0.0, 0.0]) for i in range(8)], [normal + np.array([1e-7 * i, 0.0, 0.0]) for i in range(8)])
    ok(
        focus_waist_from_grouped_rays([noise], image_point=centre, image_axis=normal) is None,
        "B4: a field that never converges is not allowed to invent a plane",
    )
    # four fields of 3 rays each: no single field reaches min_rays=8, but pooled there are 12
    mixed = focus_waist_from_grouped_rays(
        [_cone(centre, normal, -20.0, n_rays=3, field_shift=(0.0, 0.0, 0.0)) for _ in range(4)],
        image_point=centre, image_axis=normal, min_rays=8,
    )
    ok(
        mixed is not None and bool(mixed.get("pooled")) and abs(mixed["offset_mm"] + 20.0) < 1e-6,
        "B5: when no group is large enough it falls back to the pooled bundle and flags it",
    )

    # ---- C: the drawn plane --------------------------------------------------------------------
    specs = focused_image_plane_specs(centre, normal, grouped, 11.52, 11.52)
    kinds = [s["kind"] for s in specs]
    ok(
        kinds == ["focused_image_plane", "focus_defocus_gap"],
        f"C1: a detached focus draws the plane and a dashed connector to the sensor ({kinds})",
    )
    rect = np.asarray(specs[0]["points"], dtype=float)
    expected = centre + normal * grouped["offset_mm"]
    # _rect_points returns a CLOSED loop (the first corner repeated), so average the 4 corners
    corners = rect[:4]
    in_plane = float(np.max(np.abs((rect - expected) @ (normal / np.linalg.norm(normal)))))
    ok(
        np.allclose(corners.mean(axis=0), expected, atol=1e-6) and in_plane < 1e-9,
        f"C2: the rectangle is centred on centre + normal*offset and lies IN that plane "
        f"(centre {np.round(corners.mean(axis=0), 3).tolist()}, out-of-plane {in_plane:.2e} mm)",
    )
    in_focus = dict(grouped, offset_mm=0.001)
    ok(
        focused_image_plane_specs(centre, normal, in_focus, 11.52, 11.52) == []
        and focused_image_plane_label_specs(centre, normal, in_focus, 11.52) == [],
        "C3: an image already on the sensor draws nothing (no clutter when it is in focus)",
    )
    label = focused_image_plane_label_specs(centre, normal, grouped, 11.52)
    ok(
        label and "20" in label[0]["text"] and "in front of" in label[0]["text"],
        f"C4: the label states the distance and the side ({label[0]['text'] if label else None!r})",
    )

    # ---- D: the banner text ----------------------------------------------------------------------
    noop = format_focus_summary_lines(grouped, {"delivered_fov_wh": (20.0, 20.0), "delivered_m": 1.152, "lens_move_mm": None})
    moved = format_focus_summary_lines(grouped, {"delivered_fov_wh": (20.0, 20.0), "delivered_m": 1.152, "lens_move_mm": -138.6})
    ok(
        any("did not move" in line for line in noop) and any("-138.6 mm" in line for line in moved),
        "D1: the SOLVE line distinguishes a no-op from a real lens move",
    )
    ok(
        any("20 mm in front of the sensor" in line for line in noop)
        and any("spot" in line and "on the sensor" in line for line in noop),
        f"D2: the FOCUS line carries the distance, the side and both spot sizes ({noop[1] if len(noop) > 1 else None!r})",
    )
    ok(
        format_focus_summary_lines(in_focus, None) == [] and format_focus_summary_lines(None, None) == [],
        "D3: nothing to say when the image is on the sensor and no solve ran",
    )

    # ---- E: wiring pins ---------------------------------------------------------------------------
    from KrakenOS.UI.services import detector_coverage_overlay, plot_refresh, three_d_scene_tools
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    ok(
        "_measure_focused_image_plane(bundle)" in inspect.getsource(plot_refresh)
        and "_measure_focused_image_plane(scene_bundle)" in inspect.getsource(three_d_scene_tools),
        "E1: the plane is re-measured after EVERY real trace (2D refresh and 3D rebuild)",
    )
    measure = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "focus_waist_from_grouped_rays" in measure
        and '"image", "target_termination"' in measure
        and "field_index" in measure,
        "E2: the measurement groups by field and only uses rays that reached the detector",
    )
    ok(
        "focused_image_plane_specs(img_pt, image_axis, focus_info" in inspect.getsource(detector_coverage_overlay)
        and "_focused_image_plane_info" in inspect.getsource(detector_coverage_overlay),
        "E3: the coverage overlay draws it from the stash, for any scene with a detector",
    )
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    ok(
        "format_focus_summary_lines" in inspect.getsource(Kraken3DInspector._update_solve_refusal_banner),
        "E4: the in-scene banner carries the focus summary",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0728 focused-image-plane validation PASSED")
        return 0
    print("0728 focused-image-plane validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
