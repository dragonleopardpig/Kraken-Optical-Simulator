"""Guard for bugs/0723 -- split field: the optical-axis guides draw BOTH imaging beams at
their own offsets (traced chief rays), and the lens-axis guide has no 0692 jog.

User (flag 135342_027 + design truth): "Beam A and B ... reaching the big inverted RA mirror
are independent, both offset from the center"; the dotted guide showed an "unknown 90 degree
bending of optical axis at the big inverted RA mirror" -- the 0692 jog bridging the arm's leg
onto the seated lens axis. Under split-field bands that skew IS the design.

Checks (display-free, synthetic fold chain -- a 45 deg fold mirror at z +9 (arm A) / -59
(arm B) onto +x, stop plane x=100 (surface 10, r 7.35 about (100, 3, -25)), image x=200
(surface 23)):
  A  split_field_beam_axis_records: one record per band, ids/labels from the band name,
     the launch sign is the NEARER arm (A -> +z, B -> -z), the face-normal ray is drawn
     when there is no stop (it dies on the stop: reached False, nothing fabricated).
  B  with the stop: the launch is AIMED through the stop centre (chief ray) -- the stop
     vertex is the stop centre, the ray reaches the image, aimed/reached flags True; a
     band that cannot be traced gets no record; no bands -> [].
  C  aim_launch_through_stop converges on a skew (non-axis-aligned) stop and reports
     converged False when the stop is never reached.
  D  _multifold_guide_segments (the lens-axis guide): without bands a skew junction is
     bridged by the jog (0692, byte-identical); with bands there is NO jog and the guide
     starts at the last skew junction's foot on the seated leg.
  E  wiring pins: the inspector extends the axis records with the beam records; the
     multifold builder passes split_field from layout_object_fov_bands; the trace picks
     the best NS branch.
  F  the 0357 coverage block exempts ADDITIVE sources: om05a's 'Device face B' (the
     device's second face, additive to the imaging launch, 0680) sat 0.5 mm from BS cube
     B's +z leg face and was booked as an opaque LED plate, force-absorbing every
     imaging-role ray leaving BS cube B -- the face-B chief ray died there. The same
     panel WITHOUT `additive` still blocks (0357 preserved).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0723_split_field_beam_axes
"""

from __future__ import annotations

import inspect

import numpy as np


def make_synthetic_trace(stop_center=(100.0, 3.0, -25.0), stop_radius=7.35):
    sc = np.asarray(stop_center, dtype=float)

    def trace(origin, direction):
        o = np.asarray(origin, dtype=float)
        d = np.asarray(direction, dtype=float)
        d = d / np.linalg.norm(d)
        if abs(d[2]) < 1e-9:
            return np.array([o]), []
        s = 1.0 if d[2] > 0 else -1.0
        z_m = 9.0 if s > 0 else -59.0
        t = (z_m - o[2]) / d[2]
        if t <= 0:
            return np.array([o]), []
        p1 = o + d * t
        n = np.array([1.0, 0.0, -s]) / np.sqrt(2.0)
        d1 = d - 2.0 * (d @ n) * n
        pts, surfs = [o], []
        if t > 20.0:
            # the wrong-way launch crosses the device body: a chain row's AIR plane 3.5 mm in
            # is a trace vertex too (om05a row 4) -- the nearer-arm rule must look past it
            pts.append(o + d * 3.5)
            surfs.append(4)
        pts.append(p1)
        surfs.append(1)
        if d1[0] <= 1e-9:
            return np.array(pts), surfs
        p_stop = p1 + d1 * ((100.0 - p1[0]) / d1[0])
        pts.append(p_stop)
        surfs.append(10)
        if np.hypot(p_stop[1] - sc[1], p_stop[2] - sc[2]) > stop_radius:
            return np.array(pts), surfs
        pts.append(p1 + d1 * ((200.0 - p1[0]) / d1[0]))
        surfs.append(23)
        return np.array(pts), surfs

    return trace


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import detector_coverage_overlay as dco

    trace = make_synthetic_trace()
    bands = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0]},
        "not a band",
        {"name": "bad", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 0.0]},
    ]

    # ---- A: no stop -> face-normal launch, nearer arm -----------------------------------
    recs = dco.split_field_beam_axis_records(bands, trace, image_surface=23)
    ok(
        len(recs) == 2
        and [r["axis_id"] for r in recs] == ["axis:beam:face-a", "axis:beam:face-b"]
        and [r["axis_label"] for r in recs] == ["Face A beam axis", "Face B beam axis"]
        and all(r["axis_kind"] == "dotted_global_guide" for r in recs),
        f"A1: one record per band with ids/labels from the band name ({[r['axis_id'] for r in recs]})",
    )
    ok(
        len(recs) == 2 and recs[0]["launch_sign"] == 1.0 and recs[1]["launch_sign"] == -1.0
        and abs(recs[0]["points"][1][2] - 9.0) < 1e-9 and abs(recs[1]["points"][1][2] + 59.0) < 1e-9,
        "A2: each face launches into the NEARER arm (A -> +z to the z=9 mirror, B -> -z to the z=-59 mirror) -- "
        "measured to the first FOLD, past the air-plane vertex 3.5 mm into the device body",
    )
    ok(
        abs(dco._first_fold_distance([[0, 0, 0], [0, 0, -3.5], [0, 0, -58.58], [0, 5.77, -58.58]]) - 58.58) < 1e-9
        and abs(dco._first_fold_distance([[0, 0, 0], [0, 0, 8.58], [0, 5.77, 8.58]]) - 8.58) < 1e-9
        and abs(dco._first_fold_distance([[0, 0, 0], [0, 0, 5.0], [0, 0, 12.0]]) - 12.0) < 1e-9,
        "A4: _first_fold_distance = path length to the first direction change (whole path when straight)",
    )
    ok(
        len(recs) == 2 and not recs[0]["reached_image"] and not recs[0]["aimed_through_stop"] and len(recs[0]["points"]) == 3 and len(recs[1]["points"]) == 3,
        "A3: without a stop the face-normal ray is drawn as traced -- it dies on the stop (reached False), nothing fabricated",
    )

    # ---- B: with the stop -> chief ray ---------------------------------------------------
    recs = dco.split_field_beam_axis_records(
        bands, trace, image_surface=23, stop_surface=10, stop_center=[100.0, 3.0, -25.0], stop_axis=[1.0, 0.0, 0.0]
    )
    stop_hits = [np.asarray(r["points"][2], dtype=float) for r in recs] if len(recs) == 2 else []
    ok(
        len(recs) == 2 and all(r["aimed_through_stop"] and r["reached_image"] for r in recs)
        and all(np.linalg.norm(h - np.array([100.0, 3.0, -25.0])) < 1e-3 for h in stop_hits),
        f"B1: with a stop each beam is AIMED through the stop centre and reaches the image "
        f"(stop hits {[np.round(h, 3).tolist() for h in stop_hits]})",
    )
    ok(
        len(recs) == 2 and recs[0]["launch_sign"] == 1.0 and recs[1]["launch_sign"] == -1.0
        and recs[0]["points"][-1][2] < -25.0 < recs[1]["points"][-1][2],
        "B2: the aimed beams keep their arms and land on OPPOSITE sides of the sensor centre (mirror-image strips)",
    )
    ok(
        dco.split_field_beam_axis_records([], trace, image_surface=23) == []
        and dco.split_field_beam_axis_records(bands, lambda o, d: (np.array([o]), []), image_surface=23) == [],
        "B3: no bands, or a trace that returns nothing, -> no records",
    )

    # ---- C: the aimer ----------------------------------------------------------------------
    skew_axis = np.array([1.0, 0.3, -0.2])
    skew_axis /= np.linalg.norm(skew_axis)
    d, converged = dco.aim_launch_through_stop(
        trace, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], stop_surface=10, stop_center=[100.0, 3.0, -25.0], stop_axis=skew_axis
    )
    pts, surfs = trace([0.0, 0.0, 0.0], d)
    ok(
        converged and len(pts) >= 3 and np.linalg.norm(pts[2] - np.array([100.0, 3.0, -25.0])) < 1e-3,
        f"C1: aim_launch_through_stop converges on a skew stop frame (miss {np.linalg.norm(pts[2] - np.array([100.0, 3.0, -25.0])) if len(pts) >= 3 else float('nan'):.2e})",
    )
    d2, converged2 = dco.aim_launch_through_stop(
        trace, [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], stop_surface=99, stop_center=[100.0, 3.0, -25.0], stop_axis=[1.0, 0.0, 0.0]
    )
    ok(
        not converged2 and np.allclose(d2, [0.0, 0.0, 1.0]),
        "C2: a stop the ray never reaches -> converged False and the launch is left as given",
    )

    # ---- D: the lens-axis guide segments --------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    seg = Kraken3DInspector._multifold_guide_segments
    # om05a-like branches: arm A (+z, +y, -z, +y at z -16) then the seated lens leg (+x at z -25) and the sensor drop (-y)
    branches = [
        [np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), []],
        [np.array([0.0, 5.0, 9.0]), np.array([0.0, 1.0, 0.0]), []],
        [np.array([0.0, 11.0, 0.0]), np.array([0.0, 0.0, -1.0]), []],
        [np.array([0.0, 30.0, -16.0]), np.array([0.0, 1.0, 0.0]), []],
        [np.array([100.0, 52.8, -25.0]), np.array([1.0, 0.0, 0.0]), []],
        [np.array([272.0, 20.0, -25.0]), np.array([0.0, -1.0, 0.0]), []],
    ]
    junctions = []
    for j in range(len(branches) - 1):
        junctions.append(Kraken3DInspector._axis_branch_junction_feet(branches[j][0], branches[j][1], branches[j + 1][0], branches[j + 1][1]))
    corners = np.array([(x, y, z) for x in (-50.0, 400.0) for y in (-100.0, 150.0) for z in (-120.0, 60.0)])
    plain = seg(branches, junctions, corners, split_field=False)
    split = seg(branches, junctions, corners, split_field=True)
    ids_plain = [r["axis_id"] for r in plain]
    ids_split = [r["axis_id"] for r in split]
    ok(
        "axis:global:reflected:jog4" in ids_plain and len(plain) == 6,
        f"D1: without bands the skew junction keeps the 0692 jog ({ids_plain})",
    )
    ok(
        not any(":jog" in i for i in ids_split) and ids_split == ["axis:global:reflected:4", "axis:global:reflected"],
        f"D2: with bands there is NO jog and the guide is the seated chain only ({ids_split})",
    )
    ok(
        len(split) == 2 and np.allclose(split[0]["points"][0], [0.0, 52.8, -25.0]) and np.allclose(split[0]["points"][1], [272.0, 52.8, -25.0])
        and np.allclose(split[1]["points"][0], [272.0, 52.8, -25.0]) and split[1]["points"][1][1] < -90.0,
        "D3: the lens-axis guide starts at the fold prism's centre on the split line (0, 52.8, -25), runs to RA2's corner and drops through the sensor to the bounds",
    )
    ok(
        [r["points"].tolist() for r in plain] == [r["points"].tolist() for r in seg(branches, junctions, corners)],
        "D4: split_field defaults to False (byte-identical segments for every non-band scene)",
    )

    # ---- E: wiring pins ----------------------------------------------------------------------
    src_records = inspect.getsource(Kraken3DInspector._optical_axis_records_for_3d)
    src_multi = inspect.getsource(Kraken3DInspector._folded_multifold_axis_guide_records)
    src_beam = inspect.getsource(Kraken3DInspector._split_field_beam_axis_records)
    ok(
        "_split_field_beam_axis_records(scene_bundle)" in src_records
        and "layout_object_fov_bands" in src_multi and "split_field=split_field" in src_multi,
        "E1: the 3D axis records include the beam records; the multifold guide passes split_field from the bands",
    )
    ok(
        "NS_BRANCH_RESULTS" in src_beam and "_runtime_transform_for_row" in src_beam and "NsTrace(" in src_beam
        and "energy_probability" in src_beam and "aperture" in src_beam,
        "E2: the inspector traces on the live system, picks the best NS branch, and aims at the FIRST Aperture row's live pose",
    )

    # ---- F: the additive-source exemption from the 0357 coverage block ---------------------
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    class _Fake:
        _coverage_illumination_block_face_ids = KrakenLayoutEditor._coverage_illumination_block_face_ids
        _illumination_block_face_ids_by_row = KrakenLayoutEditor._illumination_block_face_ids_by_row

        @staticmethod
        def _is_open3d_promoted_optical_solid_row(row):
            return bool(getattr(row, "promoted", False))

        def __init__(self, sources, faces_by_row, rows):
            self._sources = list(sources)
            self._faces_by_row = dict(faces_by_row)
            self.rows = list(rows)
            self.layout_scene_source_specs = []

        def _drawable_scene_source_descriptors(self):
            return self._sources

        def _scene_source_face_anchor_records(self, row_index):
            return self._faces_by_row.get(int(row_index), [])

    # om05a BS cube B (row 17): its +z leg face at z -50.5 facing +z; the device face-B source is a
    # 50 x 1 mm strip at z -50 emitting -z (into the arm) -- plane-parallel, 0.5 mm off, on-board.
    faces = [
        {"face_id": "S001/F002", "centroid_world": (0.0, 12.52, -50.5), "normal_world": (0.0, 0.0, 1.0)},
        {"face_id": "S001/F001", "centroid_world": (0.0, 5.77, -57.25), "normal_world": (0.0, -1.0, 0.0)},
    ]
    rows = [SimpleNamespace(promoted=False)] * 17 + [SimpleNamespace(promoted=True)]

    def _src(additive):
        settings = {"radius_x": 25.0, "radius_y": 0.5, "radius": 25.0, "physical": True, "enabled": True}
        if additive:
            settings["additive"] = True
        return SimpleNamespace(origin=(0.0, 0.0, -50.0), direction=(0.0, 0.0, -1.0), settings=settings)

    device_face = _Fake([_src(True)], {17: faces}, rows)._coverage_illumination_block_face_ids()
    led_plate = _Fake([_src(False)], {17: faces}, rows)._coverage_illumination_block_face_ids()
    ok(
        device_face == {} and led_plate.get(17) == {"S001/F002"},
        f"F1: an ADDITIVE source seated on a promoted face blocks nothing (got {device_face!r}); the same panel "
        f"without `additive` still blocks that face (0357: {led_plate!r})",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0723 split-field beam-axes validation PASSED")
        return 0
    print("0723 split-field beam-axes validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
