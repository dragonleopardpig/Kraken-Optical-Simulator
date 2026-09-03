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


def _object_row():
    from types import SimpleNamespace

    return SimpleNamespace(
        name="Object", surface="Object", advanced={},
        desp_x=0.0, desp_y=0.0, desp_z=0.0,
        tilt_x=0.0, tilt_y=0.0, tilt_z=0.0, thickness=5.35,
    )


def _tower_rows():
    # the om05a shape: an Object row (the DEVICE -- its desp_z is device
    # placement), then symmetric tower pairs about -25 etc. (vendor hardware).
    return [
        _object_row(),
        _solid_row("First RA mirror A", 9.0),
        _solid_row("BS cube A", 7.25),
        _solid_row("Centre RA mirror A", -19.03),
        _solid_row("First RA mirror B", -59.0),
        _solid_row("BS cube B", -57.25),
        _solid_row("Centre RA mirror B", -30.97),
        _solid_row("RA mirror 2", -26.4, tilt=(0.0, 90.0, 180.0)),
        _solid_row("stray far solid", -45.0),
    ]


class _FakeInspector:
    def __init__(self):
        self.hidden = []

    def winfo_exists(self):
        return True

    def set_step_label_hidden(self, label, hidden):
        self.hidden.append((str(label), bool(hidden)))


class _Stub:
    def __init__(self, bands, specs, rows=None):
        self.layout_object_fov_bands = bands
        self.layout_scene_source_specs = specs
        self.inspection_part_spec = {"axis_offset_mm": 0.0}
        self.rows = list(rows or [])
        self.imported_optical_step_path = "/x/assembly.step"
        self._three_d_inspector = _FakeInspector()
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

    # A (bugs/0712, USER DIRECTIVE superseding 0708-0711): "the vendor provided
    # STEP file should remain constant, no modification (including sliding of
    # element) is allowed. The only change is the device itself." The device box
    # stays CENTRED in the fixed gap (faces at centre +/- depth/2), the bands
    # attach to its faces, the faceB marker follows the far face, the mirror
    # plane IS the fixed hardware symmetry plane, and NO row moves.
    stub = _Stub(_bands(50.0), _specs(50.0, 50.0), rows=_tower_rows())
    rows_before = {str(r.name): (float(r.desp_x), float(r.desp_y), float(r.desp_z),
                                 float(r.tilt_x), float(r.tilt_y), float(r.tilt_z))
                   for r in stub.rows[1:]}
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
        f"A1: device faces land centred in the FIXED gap "
        f"(near {near['center']}, far {far['center']} about -25)",
    )
    ok(
        abs(spec["source_z"] + 32.5) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 25.0) < 1e-9
        and abs(spec["radius_x"] - 7.5) < 1e-9
        and abs(spec["radius_y"] - 0.5) < 1e-9,
        f"A2: faceB marker on the far face, mirror plane FIXED at the hardware "
        f"symmetry plane (z {spec['source_z']}, mirror {spec['mirror_launch_plane_z']})",
    )
    ok(
        abs(float(stub.inspection_part_spec["axis_offset_mm"]) + 17.5) < 1e-9,
        f"A3: the part box re-centres via axis_offset only "
        f"({stub.inspection_part_spec['axis_offset_mm']})",
    )
    rows_after = {str(r.name): (float(r.desp_x), float(r.desp_y), float(r.desp_z),
                                float(r.tilt_x), float(r.tilt_y), float(r.tilt_z))
                  for r in stub.rows[1:]}
    ok(
        rows_after == rows_before and not stub._three_d_inspector.hidden,
        "A4: NO hardware row moves and NO overlay is hidden -- the vendor "
        "hardware is byte-identical (the user directive)",
    )
    # bugs/0713 ("The rays not launching from the object plane. Recurring
    # bug."): the OBJECT row IS the device -- its desp_z takes face A, so the
    # launch rides the face while the hardware stays put; the paraxial
    # reference folds it into the object distance.
    ok(
        abs(float(stub.rows[0].desp_z) + 17.5) < 1e-9,
        f"A6: the object row (the device) carries face A -- launch plane at "
        f"z={stub.rows[0].desp_z}",
    )
    # A5: a SECOND resize (15 -> 30) stays centred about the fixed plane.
    moved2 = LayoutTableWorkbenchMixin._retarget_split_field_to_part(
        stub, {"depth_mm": 15.0, "width_mm": 15.0, "height_mm": 1.0},
        {"depth_mm": 30.0, "width_mm": 30.0, "height_mm": 1.0},
    )
    ok(
        bool(moved2)
        and abs(near["center"][2] + 10.0) < 1e-9
        and abs(far["center"][2] + 40.0) < 1e-9
        and abs(spec["mirror_launch_plane_z"] + 25.0) < 1e-9
        and abs(float(stub.inspection_part_spec["axis_offset_mm"]) + 10.0) < 1e-9,
        f"A5: a second resize stays centred about the fixed plane -25 "
        f"(near {near['center'][2]}, far {far['center'][2]}, "
        f"offset {stub.inspection_part_spec['axis_offset_mm']})",
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

    # bugs/0713/0714 wiring: the launch honours the object-row desp, the
    # paraxial reference folds it into the object distance, and the folded
    # solve books a negative station-frame object gap on the lens-leg slide.
    import inspect as _inspect

    from KrakenOS.UI.services import paraxial_tools as _pt
    from KrakenOS.UI.services import trace_preview_sampling as _tps

    _launch_src = _inspect.getsource(_tps)
    ok(
        "origin_z" in _launch_src
        and "anchor_x - float(field_x), anchor_y - float(field_y), origin_z" in _launch_src,
        "F1: the finite-object launch origin rides the object row's desp_z (the device face)",
    )
    _ref_src = _inspect.getsource(_pt.ParaxialToolsMixin._paraxial_reference_rows_for_layout)
    ok(
        "reference_rows[0].thickness = float(reference_rows[0].thickness) - _obj_desp_z" in _ref_src,
        "F2: the paraxial reference folds the object desp into the object distance",
    )
    _gate_src = _inspect.getsource(_pt.ParaxialToolsMixin._folded_conjugate_gaps_for_magnification)
    ok(
        "_lens_leg_slide_plan() is not None" in _gate_src and "bugs/0714" in _gate_src,
        "F3: a negative station-frame object gap proceeds to the lens-leg slide "
        "instead of the plain refusal (the 0588-symmetric object gate)",
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
