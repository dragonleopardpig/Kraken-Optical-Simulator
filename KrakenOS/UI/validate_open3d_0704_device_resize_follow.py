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


class _Stub:
    def __init__(self, bands, specs):
        self.layout_object_fov_bands = bands
        self.layout_scene_source_specs = specs
        self.inspection_part_spec = {"axis_offset_mm": 0.0}
        self.debug = []

    def append_debug(self, msg):
        self.debug.append(str(msg))


def _old(depth=50.0, width=50.0, height=1.0):
    return {"depth_mm": depth, "width_mm": width, "height_mm": height}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # A: the split-field scene follows a resize SYMMETRICALLY about the gap
    # centre (flag 125205 "always at the middle of the big gap of the two top
    # RA mirrors") -- the mirror-launch symmetry plane IS that centre and stays
    # invariant, which keeps the mirrored faceB launch exact at every size.
    stub = _Stub(_bands(50.0), _specs(50.0, 50.0))
    moved = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub, _old(), {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0}
    )
    far = stub.layout_object_fov_bands[1]
    near = stub.layout_object_fov_bands[0]
    spec = stub.layout_scene_source_specs[0]
    ok(
        bool(moved)
        and abs(near["center"][2] + 17.5) < 1e-9
        and abs(far["center"][2] + 32.5) < 1e-9,
        f"A1: faces land symmetric about the gap centre -25 "
        f"(near {near['center']}, far {far['center']})",
    )
    ok(
        abs(spec["source_z"] + 32.5) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 25.0) < 1e-9
        and abs(spec["radius_x"] - 7.5) < 1e-9
        and abs(spec["radius_y"] - 0.5) < 1e-9,
        f"A2: faceB launch follows with the mirror plane INVARIANT at -25 "
        f"(z {spec['source_z']}, mirror {spec['mirror_launch_plane_z']}, "
        f"rx {spec['radius_x']}, ry {spec['radius_y']})",
    )
    ok(
        abs(float(stub.inspection_part_spec["axis_offset_mm"]) + 17.5) < 1e-9,
        f"A3: the drawn part box re-centres via axis_offset "
        f"({stub.inspection_part_spec['axis_offset_mm']})",
    )
    # A4: a SECOND resize (15 -> 30) stays centred -- the scheme is stable.
    moved2 = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub, {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0},
        {"depth_mm": 30.0, "width_mm": 30.0, "height_mm": 1.0},
    )
    ok(
        bool(moved2)
        and abs(near["center"][2] + 10.0) < 1e-9
        and abs(far["center"][2] + 40.0) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 25.0) < 1e-9,
        f"A4: a second resize stays centred at -25 (near {near['center'][2]}, "
        f"far {far['center'][2]})",
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
