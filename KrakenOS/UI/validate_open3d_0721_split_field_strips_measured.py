"""Guard for bugs/0721 -- om05a split field: the device-face bands are symmetric and the
sensor strips are MEASURED from the trace, not authored.

User (flags 135342_027 / 140518_465): "what is eventually shown in the sensor is one thin
dark edge at the center of the sensor caused by the edge of the center RA mirror ...
symmetry rectangular strip on both sides of the center dark edge corresponds to the two
symmetrical object side FOV." The scene carried authored bands v -5.25..+3.1 (centre -1.08)
and authored sensor strips (A +0.85..+3.85, B -6.22..-3.11) that cannot follow
magnification and were not mirror images.

Checks (display-free):
  A  symmetrize_face_bands: an authored asymmetric band becomes +-span/2; a symmetric
     one is untouched; bad/missing values are skipped.
  B  measure_split_field_image_strips: synthetic records from two faces (first hit near
     z=0 vs z=-50) landing at mirror-image v on the sensor -> two symmetric strips, the
     centre gap (the dark edge) between them, half_width from u, trim + min_rays honoured,
     the detector frame is the overlay's own _basis.
  C  wiring pins: the loader and the solve symmetrize; the 2D and 3D trace paths call the
     measurement after a real trace; the editor method reads the detector target.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0721_split_field_strips_measured
"""

from __future__ import annotations

import inspect

import numpy as np


def _records(face_z: float, v_values, u_values, image_surface: int, reaches: bool = True):
    out = []
    for v, u in zip(v_values, u_values):
        # first hit on the face's arm (z near the face), last hit on the image row at
        # world = img_pt + u*iu + v*iv (frame built by the test below)
        out.append({"face_z": face_z, "v": float(v), "u": float(u), "reaches": bool(reaches)})
    return out


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import detector_coverage_overlay as dco

    # ---- A: band symmetrization ---------------------------------------------------------
    bands = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0], "half_width": 27.5, "v_lo": -4.0, "v_hi": 4.0},
        {"name": "bad", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "half_width": 1.0, "v_lo": 2.0, "v_hi": 2.0},
        "not a band",
    ]
    changed = dco.symmetrize_face_bands(bands)
    ok(
        changed == 1
        and abs(bands[0]["v_lo"] + 4.175) < 1e-9
        and abs(bands[0]["v_hi"] - 4.175) < 1e-9
        and bands[1]["v_lo"] == -4.0
        and bands[2]["v_lo"] == 2.0,
        f"A1: the authored asymmetric band becomes +-span/2 (centre 0), symmetric/degenerate ones untouched "
        f"(changed={changed}, A v {bands[0]['v_lo']:+.3f}..{bands[0]['v_hi']:+.3f})",
    )
    ok(dco.symmetrize_face_bands(bands) == 0, "A2: idempotent -- a second pass changes nothing")

    # ---- B: measured strips ------------------------------------------------------------
    img_pt = np.array([272.66, -1.66, -25.3])
    normal = np.array([0.0, -1.0, 0.0])  # the om05a sensor faces -y (the fold-down leg)
    iu, iv = dco._basis(normal)
    image_surface = 23

    def rec(face_z, u, v, reaches=True):
        p = img_pt + u * iu + v * iv
        return {
            "reaches_image": reaches,
            "hits": [
                {"surface": 1, "x": 0.0, "y": 0.42, "z": face_z + 8.5},  # first hit on that face's arm
                {"surface": 7, "x": 0.0, "y": 52.8, "z": face_z - 16.8},
                {"surface": image_surface, "x": float(p[0]), "y": float(p[1]), "z": float(p[2])},
            ],
        }

    recs = []
    # face A lands at v +1.0..+3.4 (plus two outliers), face B at the mirror image -3.4..-1.0
    for v in np.linspace(1.0, 3.4, 20):
        recs.append(rec(0.0, u=np.random.default_rng(int(v * 100)).uniform(-11.0, 11.0), v=v))
    recs.append(rec(0.0, u=0.0, v=9.0))  # outlier (trimmed)
    for v in np.linspace(-3.4, -1.0, 20):
        recs.append(rec(-50.0, u=np.random.default_rng(int(-v * 100)).uniform(-11.0, 11.0), v=v))
    recs.append(rec(-50.0, u=0.0, v=-9.0))  # outlier (trimmed)
    recs.append(rec(0.0, u=0.0, v=0.0, reaches=False))  # a vignetted ray must be ignored
    bands2 = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0], "half_width": 27.5, "v_lo": -4.175, "v_hi": 4.175,
         "image_strip": {"center": [-272.65, -1.65, -26.4], "axis_v": [0, 0, 1], "half_width": 11.52, "v_lo": 0.845, "v_hi": 3.845}},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0], "half_width": 27.5, "v_lo": -4.175, "v_hi": 4.175,
         "image_strip": {"center": [-272.65, -1.65, -26.4], "axis_v": [0, 0, 1], "half_width": 11.52, "v_lo": -6.224, "v_hi": -3.114}},
    ]
    n = dco.measure_split_field_image_strips(bands2, recs, image_surface=image_surface, image_point=img_pt, image_axis=normal, trim=0.05)
    sa, sb = bands2[0]["image_strip"], bands2[1]["image_strip"]
    ok(
        n == 2 and sa.get("measured") and sb.get("measured"),
        f"B1: both bands re-measured from the trace (n={n}, rays A {sa.get('ray_count')} / B {sb.get('ray_count')})",
    )
    ok(
        abs(sa["v_lo"] - 1.0) < 0.2 and abs(sa["v_hi"] - 3.4) < 0.2 and abs(sb["v_lo"] + 3.4) < 0.2 and abs(sb["v_hi"] + 1.0) < 0.2,
        f"B2: the strips are the landing v-ranges with outliers trimmed: A {sa['v_lo']:+.2f}..{sa['v_hi']:+.2f}, "
        f"B {sb['v_lo']:+.2f}..{sb['v_hi']:+.2f}",
    )
    ok(
        abs((sa["v_lo"] + sa["v_hi"]) + (sb["v_lo"] + sb["v_hi"])) < 0.4 and sa["v_lo"] > 0.5 > -0.5 > sb["v_hi"],
        "B3: the two strips are mirror images about the sensor centre with a gap between them (the dark edge)",
    )
    ok(
        abs(float(sa["half_width"]) - 11.0) < 1.0 and np.allclose(sa["center"], img_pt) and np.allclose(sa["axis_v"], iv),
        f"B4: half_width from the u spread ({sa['half_width']:.2f}); the strip frame is the overlay's own "
        f"(centre = detector centre, axis_v = _basis(normal)[1])",
    )
    few = [rec(0.0, u=0.0, v=2.0), rec(0.0, u=0.0, v=2.5)]
    keep = [dict(bands2[0], image_strip=dict(bands2[0]["image_strip"]))]
    ok(
        dco.measure_split_field_image_strips(keep, few, image_surface=image_surface, image_point=img_pt, image_axis=normal) == 0
        and keep[0]["image_strip"]["v_lo"] == sa["v_lo"],
        "B5: fewer than min_rays landing rays keeps the previous strip (no fabricated strip)",
    )
    ok(
        dco.measure_split_field_image_strips(bands2, [], image_surface=image_surface, image_point=img_pt, image_axis=normal) == 0
        and dco.measure_split_field_image_strips([], recs, image_surface=image_surface, image_point=img_pt, image_axis=normal) == 0,
        "B6: no records / no bands -> nothing changes",
    )

    # ---- C: wiring pins ------------------------------------------------------------------
    from KrakenOS.UI.services import layout_settings, plot_refresh, three_d_scene_tools
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    ok(
        "symmetrize_face_bands" in inspect.getsource(layout_settings)
        and "symmetrize_face_bands" in inspect.getsource(QuickEstimationService._update_split_field_band_widths),
        "C1: the loader and the FOV solve both symmetrize the face bands",
    )
    ok(
        "_measure_split_field_image_strips(system, rays, bundle)" in inspect.getsource(plot_refresh)
        and "_measure_split_field_image_strips(system, rays, scene_bundle)" in inspect.getsource(three_d_scene_tools),
        "C2: both the 2D refresh and the 3D rebuild re-measure the strips after a real trace",
    )
    src = inspect.getsource(LayoutTableWorkbenchMixin._measure_split_field_image_strips)
    from KrakenOS.UI.scene_geometry import SceneTarget3D

    target_fields = set(getattr(SceneTarget3D, "__dataclass_fields__", {}).keys())
    ok(
        "is_detector" in src and "_ray_analysis_records_for_trace" in src and "measure_split_field_image_strips(" in src
        and "center_world" in src and "normal_world" in src and "trace_surface" in src
        and {"center_world", "normal_world", "trace_surface", "is_detector"} <= target_fields,
        "C3: the editor method reads the REAL SceneTarget3D fields (center_world / normal_world / "
        "trace_surface) -- the first cut used center/normal, raised, and was silently skipped",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0721 split-field measured-strips validation PASSED")
        return 0
    print("0721 split-field measured-strips validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
