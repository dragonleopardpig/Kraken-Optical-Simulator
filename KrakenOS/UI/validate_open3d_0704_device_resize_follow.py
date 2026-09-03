"""Guard for bugs/0704 -- flag 110804: "add device size (length, width,
thickness) changing option. The green object plane should attach automatically
to new device side location. Let user to input required FOV as usual."

The size option is the existing Inspection Part dialog (W/H/D); what was
missing is the SPLIT-FIELD follow-through, now in
`set_inspection_part_spec` -> `_retarget_split_field_to_part`:

  * the far (face B) band's centre moves to the new back face;
  * the mirrored faceB launch follows (launch plane, symmetry plane at half
    depth, aperture = the new face size);
  * the near band (face A, the object-plane anchor) never moves;
  * hardware is never moved -- re-seating the vendor train is the user's call;
  * a successful object-FOV solve writes the delivered width into both bands
    (`QuickEstimationService._update_split_field_band_widths`).

Checks (display-free, unbound mixin methods on stubs):
  A  depth 50 -> 15: far band z -50 -> -15, faceB spec follows (z, mirror
     plane, radius_x/radius_y), near band byte-identical.
  B  a scene whose bands do not sit on the part's faces is left untouched.
  C  a single-band (non-split) scene is left untouched.
  D  the FOV-solve band-width follow writes width/2 into both bands.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0704_device_resize_follow
"""

from __future__ import annotations

import copy

from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin


def _bands(depth: float) -> list[dict]:
    return [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1},
        {"name": "Face B field", "center": [0.0, 0.0, -depth], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1},
    ]


def _specs(depth: float, width: float) -> list[dict]:
    return [{
        "source_id": "source:faceB", "mirror_launch_plane_z": -0.5 * depth,
        "source_z": -depth, "radius_x": 0.5 * width, "radius_y": 0.5,
        "radius": 0.5 * width,
    }]


def _solid_row(name, z, tilt=(0.0, 0.0, 0.0), solid=True):
    from types import SimpleNamespace

    return SimpleNamespace(
        name=name, advanced=({"Solid_3d_stl": "/x.stl"} if solid else {}),
        desp_x=0.0, desp_y=0.0, desp_z=float(z),
        tilt_x=float(tilt[0]), tilt_y=float(tilt[1]), tilt_z=float(tilt[2]),
        thickness=0.0,
    )


def _tower_rows():
    # the om05a shape: symmetric tower pairs about -25, an unpaired far solid,
    # and a tilted far fold mirror -- only the PAIRED, UNTILTED far rows slide.
    return [
        _solid_row("First RA mirror A", 9.0),
        _solid_row("BS cube A", 7.25),
        _solid_row("Centre RA mirror A", -19.03),
        _solid_row("First RA mirror B", -59.0),
        _solid_row("BS cube B", -57.25),
        _solid_row("Centre RA mirror B", -30.97),
        _solid_row("RA mirror 2", -26.4, tilt=(0.0, 90.0, 180.0)),
        _solid_row("stray far solid", -45.0),
    ]


class _Stub:
    def __init__(self, bands, specs, rows=None):
        self.layout_object_fov_bands = bands
        self.layout_scene_source_specs = specs
        self.inspection_part_spec = {"axis_offset_mm": 0.0}
        self.rows = list(rows or [])
        self.debug = []

    def _row_z_positions(self):
        return [0.0] * len(self.rows)

    def _slide_far_tower_rows(self, *a, **k):
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

        return LayoutTableWorkbenchMixin._slide_far_tower_rows(self, *a, **k)

    def append_debug(self, msg):
        self.debug.append(str(msg))


def _old(depth=50.0, width=50.0, height=1.0):
    return {"depth_mm": depth, "width_mm": width, "height_mm": height}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # A (bugs/0708, superseding the 0706 display-offset scheme): FACE A stays on
    # the walk origin -- where the imaging launch physically starts (flag 133247
    # "the ray is no launching from the Object Plane") -- and the FAR TOWER
    # slides with the far face, so the device stays in the middle of the gap
    # (the 0706 ask) the physical way, keeping the mirrored launch exact.
    stub = _Stub(_bands(50.0), _specs(50.0, 50.0), rows=_tower_rows())
    moved = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub, _old(), {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0}
    )
    far = stub.layout_object_fov_bands[1]
    near = stub.layout_object_fov_bands[0]
    spec = stub.layout_scene_source_specs[0]
    ok(
        bool(moved)
        and abs(near["center"][2] - 0.0) < 1e-9
        and abs(far["center"][2] + 15.0) < 1e-9,
        f"A1: face A stays on the launch plane, far face -> z=-15 "
        f"(near {near['center']}, far {far['center']})",
    )
    ok(
        abs(spec["source_z"] + 15.0) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 7.5) < 1e-9
        and abs(spec["radius_x"] - 7.5) < 1e-9
        and abs(spec["radius_y"] - 0.5) < 1e-9,
        f"A2: faceB launch on the new face, mirror plane at -7.5 "
        f"(z {spec['source_z']}, mirror {spec['mirror_launch_plane_z']}, "
        f"rx {spec['radius_x']}, ry {spec['radius_y']})",
    )
    zs = {str(r.name): float(r.desp_z) for r in stub.rows}
    ok(
        abs(zs["First RA mirror B"] + 24.0) < 1e-9
        and abs(zs["BS cube B"] + 22.25) < 1e-9
        and abs(zs["Centre RA mirror B"] - 4.03) < 1e-6,
        f"A3a: the PAIRED far-tower solids slide +35 with the far face "
        f"({zs['First RA mirror B']}, {zs['BS cube B']}, {zs['Centre RA mirror B']})",
    )
    ok(
        abs(zs["First RA mirror A"] - 9.0) < 1e-9
        and abs(zs["RA mirror 2"] + 26.4) < 1e-9
        and abs(zs["stray far solid"] + 45.0) < 1e-9,
        "A3b: the near tower, the tilted leg fold and an unpaired far solid never move",
    )
    # A4: a SECOND resize (15 -> 30) is consistent from the new state.
    moved2 = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub, {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0},
        {"depth_mm": 30.0, "width_mm": 30.0, "height_mm": 1.0},
    )
    ok(
        bool(moved2)
        and abs(near["center"][2] - 0.0) < 1e-9
        and abs(far["center"][2] + 30.0) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 15.0) < 1e-9,
        f"A4: a second resize stays face-A-anchored (far {far['center'][2]}, "
        f"mirror {spec['mirror_launch_plane_z']})",
    )

    # B: bands not on the part's faces -> hands off
    foreign = _bands(42.0)
    before = copy.deepcopy(foreign)
    stub_b = _Stub(foreign, _specs(42.0, 50.0))
    moved_b = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub_b, _old(), {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0}
    )
    ok(
        not moved_b and stub_b.layout_object_fov_bands == before,
        "B: bands that do not sit on the part's faces are left byte-identical",
    )

    # C: single band -> untouched
    single = [copy.deepcopy(_bands(50.0)[0])]
    stub_c = _Stub(single, _specs(50.0, 50.0))
    moved_c = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub_c, _old(), {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0}
    )
    ok(not moved_c, "C: a non-split (single band) scene is untouched")

    # D: the FOV solve writes the delivered width into both bands
    from types import SimpleNamespace

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = _Stub(_bands(15.0), _specs(15.0, 15.0))
    qe = QuickEstimationService.__new__(QuickEstimationService)
    qe.editor = editor
    QuickEstimationService._update_split_field_band_widths(qe, 20.0)
    halves = [band["half_width"] for band in editor.layout_object_fov_bands]
    ok(
        halves == [10.0, 10.0],
        f"D: a solved FOV of 20 writes half_width 10 into BOTH bands ({halves})",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0704 device-resize follow validation PASSED")
        return 0
    print("0704 device-resize follow validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
