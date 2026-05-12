from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_plot_controller import (
    active_plot_modes,
    analysis_mode_label,
    build_preview_trace_signature,
    distance_to_polyline,
    find_nearest_pick_region,
    find_nearest_ray_region,
    max_surface_radius,
    plot_status_label,
    project_scene_bundle,
    projected_pick_state,
    preview_trace_signature_matches,
    thin_lens_glyph_polyline,
    trace_mode_summary_from_bundle,
    trace_preview_summary,
)
from KrakenOS.UI.surface_table_model import SurfaceRow


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _signature(**overrides):
    values = {
        "row_specs_signature": ("rows", (("Object",), ("Image",))),
        "object_mode": "Finite",
        "field_type": "Angle",
        "field_value": "14.0",
        "field_count": "3",
        "requested_trace_mode": "Auto",
        "aperture_type_label": "EPD",
        "aperture_value": "25",
        "wavelength": "0.5876",
        "ray_count": "9",
        "ray_height_factor": "1.0",
        "source_model": "Gaussian Beam",
        "pupil_pattern_label": "Hexapolar",
        "source_radius": "5",
        "source_cone_angle": "0",
        "gaussian_input_mode": "Manufacturer diameter/divergence",
        "gaussian_waist_radius": "0.5",
        "gaussian_waist_offset": "12.5",
        "gaussian_beam_diameter": "1.2",
        "gaussian_full_divergence": "0.8",
        "gaussian_waist_after_input": False,
        "gaussian_m2": "1.1",
        "pupil_rad": "0",
        "pupil_theta": "0",
        "source_power": "2",
        "source_seed": "42",
        "source_origin": ("1", "2", "3"),
        "source_direction": ("0", "0", "1"),
        "source_angular_weight": "Uniform solid angle",
        "nonseq_energy_probability": True,
        "nonseq_ns_limit": "200",
        "nonseq_target_surface_index": None,
        "full_pupil_mode": False,
    }
    values.update(overrides)
    return build_preview_trace_signature(**values)


def main() -> None:
    rows = [
        SurfaceRow(surface="Object", diameter=10.0),
        SurfaceRow(surface="Standard", diameter=80.0),
        SurfaceRow(surface="Image", diameter=4.0),
    ]
    _require(max_surface_radius(rows) == 40.0, "max surface radius did not use largest diameter")
    _require(max_surface_radius([], default=2.5) == 2.5, "max surface radius did not honor default")
    _require(max_surface_radius([object()]) == 1.0, "max surface radius did not tolerate missing diameter")

    sig = _signature()
    same_sig = _signature(field_value=14.0, source_origin=(1.0, 2.0, 3.0))
    changed_sig = _signature(field_value=15.0)
    _require(preview_trace_signature_matches(sig, same_sig), "equivalent signatures did not compare equal")
    _require(not preview_trace_signature_matches(sig, changed_sig), "changed field value did not invalidate signature")

    _require(sig[3] == 14.0 and isinstance(sig[3], float), "field value was not normalized to float")
    _require(sig[4] == 3 and isinstance(sig[4], int), "field count was not normalized to int")
    _require(sig[26] == (1.0, 2.0, 3.0), "source origin was not normalized to float tuple")
    _require(sig[29] is True and sig[-1] is False, "boolean signature fields were not normalized")

    _require(active_plot_modes(["spot", "", "mtf"]) == ["spot", "mtf"], "active analysis modes were not filtered")
    _require(active_plot_modes(["spot"], suppress_analysis=True) == [], "suppressed analysis modes were not cleared")
    _require(analysis_mode_label("coherent_detector") == "CohDet", "analysis label lookup changed")
    _require(plot_status_label(["spot", "mtf"]) == "Spot + MTF", "active analysis status label changed")
    _require(plot_status_label([], "none") == "2D", "preview status label changed")

    class FakeBundle:
        extra = {
            "trace_mode_requested": "Auto",
            "trace_mode_active": "Non-Sequential",
            "trace_mode_note": "branched",
        }

    trace_summary = trace_mode_summary_from_bundle(FakeBundle())
    _require(trace_summary == {"requested": "Auto", "active": "Non-Sequential", "note": "branched"}, "trace summary extraction changed")

    calls: list[str] = []

    class FakeProjector:
        def __init__(self, orientation: str) -> None:
            calls.append(f"projector:{orientation}")

        def project_bundle(self, bundle: object) -> str:
            calls.append(f"project:{bundle}")
            return "raw"

    def refresh_auto(projected: object) -> None:
        calls.append(f"auto:{projected}")

    def refresh_choices() -> None:
        calls.append("choices")

    def filter_arm(projected: object) -> str:
        calls.append(f"arm:{projected}")
        return f"{projected}:arm"

    def filter_ray(projected: object) -> str:
        calls.append(f"ray:{projected}")
        return f"{projected}:ray"

    projected = project_scene_bundle(
        "bundle",
        "YZ",
        projector_factory=FakeProjector,
        refresh_auto_leg_graph=refresh_auto,
        refresh_arm_view_choices=refresh_choices,
        filter_arm_view=filter_arm,
        filter_ray_display=filter_ray,
    )
    _require(projected == "raw:arm:ray", "projection filters did not chain")
    _require(
        calls == ["projector:YZ", "project:bundle", "auto:raw", "choices", "arm:raw", "ray:raw:arm"],
        f"projection orchestration order changed: {calls}",
    )

    positive_lens = SurfaceRow(surface="Thin Lens", rc=50.0, diameter=20.0)
    positive_glyph = thin_lens_glyph_polyline(positive_lens, 80.0)
    _require(positive_glyph is not None and positive_glyph.shape[0] >= 18, "positive thin-lens glyph was not built")
    _require(float(np.ptp(positive_glyph[:, 0])) > 3.0, "positive thin-lens glyph collapsed to a vertical line")
    _require(abs(float(np.ptp(positive_glyph[:, 1])) - 20.0) < 1e-9, "positive thin-lens glyph height changed")

    negative_lens = SurfaceRow(surface="Thin Lens", rc=-50.0, diameter=20.0)
    negative_glyph = thin_lens_glyph_polyline(negative_lens, 80.0)
    _require(negative_glyph is not None and float(np.ptp(negative_glyph[:, 0])) > 3.0, "negative thin-lens glyph collapsed")

    transform = np.eye(4)
    transform[2, 3] = 125.0
    transform[1, 3] = 3.0
    shifted_glyph = thin_lens_glyph_polyline(positive_lens, 0.0, transform=transform)
    _require(shifted_glyph is not None, "transformed thin-lens glyph was not built")
    shifted_center_z = 0.5 * (float(np.min(shifted_glyph[:, 0])) + float(np.max(shifted_glyph[:, 0])))
    _require(abs(shifted_center_z - 125.0) < 0.2, "thin-lens glyph did not honor transform z")

    class FakePickRegion:
        row_index = 4
        polylines = [np.asarray([[0.0, 0.0], [2.0, 0.0]])]

    class FakeRay:
        ray_index = 9
        points_2d = np.asarray([[0.0, 1.0], [2.0, 1.0]])

    class DegenerateRay:
        ray_index = 10
        points_2d = np.asarray([[0.0, 2.0]])

    class FakeProjected:
        pick_regions = [FakePickRegion()]
        rays = [FakeRay(), DegenerateRay()]

    row_regions, ray_regions = projected_pick_state(FakeProjected())
    _require(list(row_regions) == [4], "projected row pick regions were not grouped by row")
    _require(len(row_regions[4]) == 1 and np.allclose(row_regions[4][0], [[0.0, 0.0], [2.0, 0.0]]), "row pick polyline changed")
    _require(len(ray_regions) == 1 and ray_regions[0][0] == 9, "ray pick regions did not filter degenerate rays")
    _require(distance_to_polyline((1.0, 0.25), row_regions[4][0]) == 0.25, "polyline distance changed")
    scale_to_display = lambda points: np.asarray(points, dtype=float) * 10.0
    _require(
        find_nearest_pick_region((10.0, 2.0), row_regions, transform_points=scale_to_display, threshold=3.0) == 4,
        "nearest row pick region changed",
    )
    _require(
        find_nearest_pick_region((10.0, 8.0), row_regions, transform_points=scale_to_display, threshold=3.0) is None,
        "far row pick should not select",
    )
    _require(
        find_nearest_ray_region((10.0, 12.0), ray_regions, transform_points=scale_to_display, threshold=3.0) == 9,
        "nearest ray pick region changed",
    )

    class FakeRays:
        SURFACE = [[0, 1, 2], [0, 1]]

        def batch_push(self) -> None:
            pass

    trace = trace_preview_summary(
        rays=FakeRays(),
        bundle=None,
        trace_state={"requested": "Auto", "active": "Sequential", "note": ""},
        final_surface_index=2,
        scalar_required=False,
        batch_capable=True,
        backend="",
    )
    _require(trace["family"] == "Sequential preview", "trace preview family changed")
    _require(trace["backend"] == "Batch preview", "trace preview backend fallback changed")
    _require(trace["total_rays"] == 2 and trace["image_hits"] == 1 and trace["stopped_rays"] == 1, "trace preview ray accounting changed")

    class FakePath:
        def __init__(self, reaches_image: bool) -> None:
            self.reaches_image = reaches_image

    class FakeTraceBundle:
        extra = {"folded_ray_display_paths": [np.zeros((2, 2))], "trace_mode_active": "Folded"}
        ray_paths = [FakePath(True), FakePath(False), FakePath(True)]

    folded_trace = trace_preview_summary(
        rays=FakeRays(),
        bundle=FakeTraceBundle(),
        trace_state={"requested": "Auto", "active": "Sequential", "note": "state note"},
        final_surface_index=2,
        scalar_required=True,
        batch_capable=False,
        backend="none",
    )
    _require(folded_trace["family"] == "Folded sequential preview", "folded trace family changed")
    _require(folded_trace["active"] == "Folded", "bundle trace mode did not override trace state")
    _require(folded_trace["image_hits"] == 2 and folded_trace["stopped_rays"] == 0, "bundle ray-path accounting changed")
    _require(folded_trace["scalar_required"] is True, "scalar trace flag was not preserved")

    print("Layout plot controller validation passed.")


if __name__ == "__main__":
    main()
