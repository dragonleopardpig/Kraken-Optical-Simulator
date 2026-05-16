from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_plot_controller import (
    active_plot_modes,
    analysis_mode_label,
    arm_ray_label_plan,
    arm_ray_label_targets,
    build_preview_trace_signature,
    distance_to_polyline,
    find_nearest_pick_region,
    find_nearest_ray_region,
    leg_geometry_point_at_fraction,
    leg_label_text,
    max_surface_radius,
    physical_leg_label_plan,
    plot_status_label,
    project_scene_bundle,
    projected_scene_for_layout_render,
    projected_pick_state,
    preview_trace_signature_matches,
    thin_lens_glyph_polyline,
    trace_mode_summary_from_bundle,
    trace_preview_summary,
)
from KrakenOS.UI.scene_builder import _sync_folded_terminal_events, ray_event_to_record
from KrakenOS.UI.scene_geometry import (
    LabelSpec,
    ProjectedRay2D,
    ProjectedScene2D,
    RayEvent3D,
    RayPath3D,
    SceneBundle,
    SurfaceMesh3D,
    projected_ray_hits_detector,
    projected_ray_terminal_status,
)
from KrakenOS.UI.scene_projector import (
    SceneProjector2D,
    auxiliary_projection_planes,
    normalize_projection_plane,
    projection_axis_labels,
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

    class Mesh:
        points = np.asarray(
            [
                [0.0, -1.0, 0.0],
                [2.0, -1.0, 0.0],
                [0.0, 1.0, 10.0],
                [2.0, 1.0, 10.0],
            ],
            dtype=float,
        )

    scene_3d = SceneBundle(
        surface_meshes=[SurfaceMesh3D(row_index=1, kind="solid", mesh=Mesh())],
        ray_paths=[
            RayPath3D(
                ray_index=0,
                points_world=np.asarray([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=float),
            )
        ],
    )
    _require(normalize_projection_plane("Vertical") == "YZ", "legacy Vertical display value did not normalize")
    _require(normalize_projection_plane("Horizontal") == "YZ", "legacy Horizontal display value did not normalize")
    _require(auxiliary_projection_planes("XZ") == ("YZ", "XY"), "auxiliary projection plane ordering changed")
    yz_scene = SceneProjector2D("YZ").project_bundle(scene_3d)
    xz_scene = SceneProjector2D("XZ").project_bundle(scene_3d)
    xy_scene = SceneProjector2D("XY").project_bundle(scene_3d)
    _require(np.allclose(yz_scene.rays[0].points_2d, [[3.0, 2.0], [6.0, 5.0]]), "YZ ray projection changed")
    _require(np.allclose(xz_scene.rays[0].points_2d, [[3.0, 1.0], [6.0, 4.0]]), "XZ ray projection changed")
    _require(np.allclose(xy_scene.rays[0].points_2d, [[1.0, 2.0], [4.0, 5.0]]), "XY ray projection changed")
    _require(xz_scene.curves and xy_scene.curves, "auxiliary projections did not include mesh outlines")
    _require(xz_scene.pick_regions and xz_scene.pick_regions[0].row_index == 1, "XZ projection did not keep row pick regions")
    _require(xy_scene.pick_regions and xy_scene.pick_regions[0].row_index == 1, "XY projection did not keep row pick regions")
    _require(projection_axis_labels("XZ") == ("Z [mm]", "X [mm]", "XZ"), "XZ axis labels changed")
    _require(projection_axis_labels("XY") == ("X [mm]", "Y [mm]", "XY"), "XY axis labels changed")

    labeled_scene = ProjectedScene2D(labels=[LabelSpec(text="surface label")])
    _require(projected_scene_for_layout_render(labeled_scene) is labeled_scene, "unfiltered layout render scene should be reused")
    hidden_label_scene = projected_scene_for_layout_render(labeled_scene, suppress_scene_labels=True)
    _require(hidden_label_scene is not labeled_scene and hidden_label_scene.labels == [], "layout render label suppression changed")
    _require(labeled_scene.labels and labeled_scene.labels[0].text == "surface label", "layout render suppression mutated input scene")

    _require(leg_label_text("michelson", "reflect", "Reflect", "Reference mirror") == "P3 Reflect", "Michelson compact leg label changed")
    _require(leg_label_text("", "custom", "Custom", "short detail") == "Custom: short detail", "custom leg detail label changed")
    _require(leg_label_text("", "custom", "Custom", "this detail is intentionally long") == "Custom", "long custom leg label changed")
    leg = {
        "segments": [
            (np.asarray([0.0, 0.0]), np.asarray([10.0, 0.0])),
            (np.asarray([10.0, 0.0]), np.asarray([10.0, 10.0])),
        ],
        "unit": np.asarray([1.0, 0.0]),
    }
    _require(np.allclose(leg_geometry_point_at_fraction(leg, 0.75), [10.0, 5.0]), "leg fraction point changed")
    plan = physical_leg_label_plan(
        definitions=[("input", "Input", ""), ("reflect", "Reflect", ""), ("detector", "Detector", "")],
        geometry={
            "input": {"segments": [(np.asarray([0.0, 0.0]), np.asarray([100.0, 0.0]))], "unit": np.asarray([1.0, 0.0])},
            "reflect": {"segments": [(np.asarray([0.0, 0.0]), np.asarray([0.0, 100.0]))], "unit": np.asarray([0.0, 1.0])},
        },
        workflow="michelson",
        axis_limits=(0.0, 100.0, -50.0, 50.0),
    )
    _require([item["leg_id"] for item in plan] == ["input", "reflect"], "physical leg label plan did not follow definitions/geometry")
    _require(str(plan[0]["label"]) == "P1 Input" and str(plan[1]["label"]) == "P3 Reflect", "physical leg label text changed")
    _require(np.allclose(plan[0]["point"], [50.0, 0.0]), "Michelson input label marker fraction changed")
    view_plan = physical_leg_label_plan(
        definitions=[("input", "Input", ""), ("reflect", "Reflect", "")],
        geometry={
            "input": {"segments": [(np.asarray([0.0, 0.0]), np.asarray([100.0, 0.0]))], "unit": np.asarray([1.0, 0.0])},
            "reflect": {"segments": [(np.asarray([0.0, 0.0]), np.asarray([0.0, 100.0]))], "unit": np.asarray([0.0, 1.0])},
        },
        workflow="michelson",
        axis_limits=(0.0, 100.0, -50.0, 50.0),
        view_leg_id="reflect",
    )
    _require(len(view_plan) == 1 and view_plan[0]["leg_id"] == "reflect", "physical leg view filter changed")

    branch_scene = ProjectedScene2D(
        rays=[
            ProjectedRay2D(
                ray_index=1,
                points_2d=np.asarray([[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]], dtype=float),
                surface_ids=np.asarray([1, 3], dtype=int),
                branch_path="TR",
            ),
            ProjectedRay2D(
                ray_index=2,
                points_2d=np.asarray([[0.0, 0.2], [10.0, 0.2], [20.0, 0.2]], dtype=float),
                surface_ids=np.asarray([1, 3], dtype=int),
                branch_path="TR",
            ),
        ]
    )
    catalog = [
        {"key": "arm|surface", "short_label": "Surface path", "detail": "through component"},
        {"key": "path|TR", "short_label": "TR", "detail": "Detector output"},
    ]
    targets = arm_ray_label_targets(
        branch_scene,
        catalog,
        indices_for_arm_key=lambda key: {1} if key == "arm|surface" else set(),
        branch_path_for_arm_key=lambda key: "TR" if key == "path|TR" else "",
        ray_matches_arm_key=lambda ray, key: str(getattr(ray, "branch_path", "")) == "TR" if key == "path|TR" else False,
        branch_path_selector_sequence=lambda path: list(str(path)),
    )
    _require(len(targets) == 2, f"arm ray label targets changed: count={len(targets)}")
    _require(np.allclose(targets[0]["point"], [5.0, 0.0]), f"surface arm target tie-break changed: {targets[0]['point']}")
    _require(str(targets[1]["branch_code"]) == "TR", "branch-code target extraction changed")
    label_plans = arm_ray_label_plan(targets, axis_limits=(0.0, 30.0, -10.0, 10.0), palette=("#0f766e", "#b45309"))
    _require(len(label_plans) == 2, f"arm ray label plan count changed: {len(label_plans)}")
    _require(str(label_plans[0]["label"]) == "Surface path: through component", "surface arm label text changed")
    _require(str(label_plans[1]["label"]) == "TR: Detector output", "path arm label text changed")
    _require(str(label_plans[1]["color"]) == "#334155" and str(label_plans[1]["marker_color"]) == "#111827", "path arm colors changed")
    _require(float(np.asarray(label_plans[1]["text_point"])[1]) < float(np.asarray(label_plans[1]["point"])[1]), "TR branch label offset should stay below the ray")

    shared_targets = [
        {
            "entry": {"key": "arm|a", "short_label": "A", "detail": ""},
            "point": np.asarray([4.0, 0.0]),
            "tangent": np.asarray([1.0, 0.0]),
            "arm_index": 0,
            "branch_code": "",
        },
        {
            "entry": {"key": "arm|b", "short_label": "B", "detail": ""},
            "point": np.asarray([4.5, 0.1]),
            "tangent": np.asarray([1.0, 0.0]),
            "arm_index": 1,
            "branch_code": "",
        },
    ]
    shared_plan = arm_ray_label_plan(shared_targets, axis_limits=(0.0, 20.0, -5.0, 5.0), palette=("#111111", "#222222"))
    _require(len(shared_plan) == 1 and "Shared ray" in str(shared_plan[0]["label"]), "shared arm-ray clustering changed")
    _require(set(shared_plan[0]["entry_keys"]) == {"arm|a", "arm|b"}, "shared arm-ray labeled key set changed")

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

    terminal_owned_path = RayPath3D(
        ray_index=0,
        points_world=np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 5.0]], dtype=float),
        surface_ids=np.asarray([2], dtype=int),
        reaches_image=False,
        events=[
            RayEvent3D(
                event_id="ray:0:terminal",
                event_kind="terminal",
                event_type="image",
                ray_index=0,
                step=0,
                surface_id=2,
                point_world=np.asarray([0.0, 0.0, 5.0], dtype=float),
                termination_reason="image",
                metadata={"reaches_detector": True},
            ),
        ],
    )

    class EventTraceBundle:
        extra = {"trace_mode_active": "Non-Sequential"}
        ray_paths = [terminal_owned_path]

    event_trace = trace_preview_summary(
        rays=FakeRays(),
        bundle=EventTraceBundle(),
        trace_state={"requested": "Auto", "active": "Sequential", "note": ""},
        final_surface_index=2,
        scalar_required=False,
        batch_capable=True,
        backend="NsTraceLoop",
    )
    _require(event_trace["image_hits"] == 1, "trace summary should count terminal-event detector reach")
    event_projected = SceneProjector2D("YZ").project_bundle(SceneBundle(ray_paths=[terminal_owned_path]))
    _require(event_projected.rays[0].reaches_image is True, "projected ray should inherit terminal-event detector reach")
    _require(event_projected.rays[0].terminal_status == "hit_detector", "projected ray terminal status changed")
    _require(projected_ray_hits_detector(event_projected.rays[0]), "detector hit helper changed")
    _require(
        projected_ray_terminal_status(ProjectedRay2D(terminal_status="missed_detector")) == "missed_detector",
        "projected terminal status helper changed",
    )

    class FoldedImageRow:
        diameter = 4.0

    folded_path = RayPath3D(
        ray_index=0,
        source_position=np.asarray([0.0, 0.0, 0.0], dtype=float),
        points_world=np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 10.0]], dtype=float),
        surface_ids=np.asarray([1], dtype=int),
        termination_reason="no_next_intersection",
        events=[
            RayEvent3D(
                event_id="ray:0:hit:0",
                event_kind="surface",
                event_type="transmission",
                ray_index=0,
                step=0,
                surface_id=1,
                point_world=np.asarray([0.0, 0.0, 10.0], dtype=float),
                metadata={"event_source": "raykeeper_trace_events"},
            ),
            RayEvent3D(
                event_id="ray:0:terminal",
                event_kind="terminal",
                event_type="no_next_intersection",
                ray_index=0,
                step=1,
                surface_id=1,
                point_world=np.asarray([0.0, 0.0, 10.0], dtype=float),
                termination_reason="no_next_intersection",
                metadata={"event_source": "raykeeper_trace_events"},
            ),
        ],
    )
    _sync_folded_terminal_events(
        [folded_path],
        [np.asarray([[0.0, 0.0], [10.0, 0.0]], dtype=float)],
        [
            ("Mirror", np.asarray([0.0, 0.0], dtype=float), FoldedImageRow(), np.asarray([1.0, 0.0], dtype=float)),
            ("Image", np.asarray([10.0, 0.0], dtype=float), FoldedImageRow(), np.asarray([1.0, 0.0], dtype=float)),
        ],
        {2},
    )
    folded_terminal = [event for event in folded_path.events if event.event_kind == "terminal"][-1]
    folded_record = ray_event_to_record(folded_terminal)
    _require(folded_path.reaches_image is True, "folded reach state should sync from terminal event")
    _require(folded_path.termination_reason == "image", "folded terminal reason should be event-owned")
    _require(folded_record["folded_terminal_source"] == "folded_display_path", "folded terminal provenance missing")
    _require(folded_record["folded_display_status"] == "hit_detector", "folded terminal status missing")
    _require(folded_record["surface"] == 2, "folded terminal surface should be the detector image")

    print("Layout plot controller validation passed.")


if __name__ == "__main__":
    main()
