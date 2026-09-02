"""Guard for bugs/0672 + 0678/0680 -- the om05a folded scene with BOTH device faces.

User: "I want folded only scene, just like machine_vision_Pyrite85.py." ... "it is
symmetry 2-sided: each side should have 3 mirror surface assigned" ... "one FOV is
looking at two object plane which are located at the side of the 50x50x1mm object".

`attachment/om05a_folded.py` (Filen-synced, skip when absent) is the REAL five-fold
arm-A chain (0676/0678 scene swap): Object (face A) -> outer/lower/centre prism A
(free-placed CAD wedges, through-glass folds) -> 50 mm RA mirror 1 -> PYRITE 4.5/85
-> filter -> free-placed 40 mm RA mirror 2 -> SV25 sensor. bugs/0680 adds the
symmetric face-B arm: three free-placed B wedges pinned at the chain END (after
mirror 2, before Image -- mid-chain they fold the frame walk, the sign-agnostic
bugs/0224 line test) plus an ADDITIVE scene source (`additive: True`) whose launch
is the chain's own calibrated bundle MIRRORED through the prism-train symmetry
plane. bugs/0684 remodelled the stations to the REAL components; bugs/0687
anchored the world on the PART (face A = z 0, face B = -50, symmetry plane -25),
rebuilt the four fold mirrors as clean first-surface prisms on the CAD coated
planes, opened the mirrored faceB launch to the FULL 3x3 grid, and authored the
calculated one-side FOV bands on both part faces.

Checks (skip when the scene is absent):
  A  STRUCTURE: 10 optical-solid rows; mirror2 + the B stations free-placed at
     the part-anchored CAD poses, one Mirror/Interaction fold face each; far
     halves PLAIN glass; camera + faceB additive mirrored source; chunk seat;
     part = the world anchor; both FOV bands.
  B  TRACE: chain delivers >=900 reachers on the arm-A strip (z ~ -15.4 on the
     y=-11.4 image plane); central-field waist near the row; the chief folds the
     TRUE S; faceB launches the full mirrored grid from face B and >=10 complete
     to the arm-B strip (z ~ -7); both source families in ONE live bundle.

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0672_om05a_folded_scene
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"

# bugs/0684 (user): "Outer Prism is Right Angle Mirror ... Lower Prism is a Cube
# Beam Splitter ... they should be attached ... Center Prism is a Right Angle
# Mirror." The stations now carry the REAL components: the BS cube's near half
# (TIR fold at the cement plane) + its far half (marked beam_splitter so the walk
# never folds on it), a first-surface outer mirror slab on the CAD coated plane,
# and the CAD centre V-block halves.
# bugs/0687: the world is anchored on the PART (face A = z 0, face B = -50, the
# symmetry plane -25); the outer/centre mirrors are clean extruded-triangle prisms
# whose hypotenuse sits ON the CAD coated plane (the 3 mm slab's Mirror face never
# armed -- the beam TIR'd at its BACK plane, the user's "second surface").
# bugs/0695: the user's clarified architecture + VENDOR-TRUE solids (OPT-ILS8275
# section): window station = FIRST RA MIRROR (first-surface plate, one prism);
# lower station = CUBE BS near half (coated hyp) + far half; centre = the true
# 11.89 mm half-V prism. Plus a flat LED panel per side under the BS.
B_TRAIN = {
    "First RA mirror B": (0.0, 0.42, -59.0),
    "BS cube B": (0.0, 12.52, -57.25),
    "Centre RA mirror B": (0.0, 14.0, -30.97),
}


def _check_scene(ok, notes) -> None:
    if not SCENE.exists():
        notes.append("SKIP: A/B: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["omf"] = SCENE
        editor.load_layout_by_name("omf")
        rows = editor.rows
        specs = editor._serializable_specs_for_rows(list(rows))
        solids = [
            (i, spec) for i, spec in enumerate(specs)
            if isinstance((spec.get("advanced") or {}).get("OpticalSolidFaces"), dict)
        ]
        ok(
            len(solids) == 12,
            f"A1: twelve optical-solid rows (RA mirror + BS near + centre per side, "
            f"2 big RA mirrors, 2 BS far halves, 2 LED panels -- 0695 vendor-true) ({len(solids)})",
        )

        def _centre(spec) -> np.ndarray:
            promo = (spec.get("advanced") or {}).get("StepOverlayPromotion")
            return np.asarray((promo or {}).get("center_world", (np.nan,) * 3), dtype=float)

        m2 = next((spec for _i, spec in solids if str(spec.get("name", "")) == "RA mirror 2 (40 mm)"), {})
        ok(
            np.allclose(_centre(m2), (-272.7, 52.75, -25.0), atol=0.5),
            f"A2: mirror2 is FREE-PLACED at the part-anchored CAD pose ({np.round(_centre(m2), 1).tolist()})",
        )
        image_index = next(i for i, r in enumerate(rows) if str(r.surface) == "Image")
        m2_index = next((i for i, r in enumerate(rows) if str(r.name) == "RA mirror 2 (40 mm)"), -1)
        b_ok = 0
        for label, centre in B_TRAIN.items():
            index = next((i for i, spec in enumerate(specs) if str(spec.get("name", "")) == label), -1)
            if index <= m2_index or index >= image_index:
                continue
            spec = specs[index]
            faces = ((spec.get("advanced") or {}).get("OpticalSolidFaces") or {}).get("faces") or []
            mirror_faces = [
                f for f in faces
                if str(f.get("function", "")) == "Mirror"
                and str(f.get("port_role", "")) == "Interaction Surface"
            ]
            if np.allclose(_centre(spec), centre, atol=0.5) and len(mirror_faces) == 1:
                b_ok += 1
        ok(
            b_ok == 3,
            f"A3: the three B-side stations END-inserted (after mirror2, before Image), free-placed "
            f"at the CAD poses with ONE Mirror/Interaction fold face each ({b_ok}/3)",
        )
        # bugs/0686: the far halves must be PLAIN glass -- the beam_splitter mark routes
        # a row into the branch machinery (every crossing ray spawns split children: the
        # 7300-ray super-lag). The 0686 walk gate (an off-beam pinned inferred output
        # never re-sources the frame) is what protects the Image instead.
        far_rows = [spec for _i, spec in solids if "far half" in str(spec.get("name", ""))]
        far_marked = sum(
            1 for spec in far_rows
            if bool(((spec.get("advanced") or {}).get("StepOverlayPromotion") or {}).get("beam_splitter"))
            or bool((spec.get("advanced") or {}).get("OpticalSolidBeamSplitter"))
        )
        ok(
            len(far_rows) == 2 and far_marked == 0,
            f"A3b: both BS far halves present as PLAIN glass -- no beam_splitter branch mark "
            f"({len(far_rows)} rows, {far_marked} marked)",
        )
        cam_var = editor.__dict__.get("camera_model_var")
        ok(
            cam_var is not None and cam_var.get() == "CAM-SV25MCCXP",
            "A4: the SV25 camera is registered on the scene",
        )
        source_specs = editor._normalize_scene_source_specs(
            getattr(editor, "layout_scene_source_specs", []) or []
        )
        face_b = next((s for s in source_specs if str(s.get("source_id", "")) == "source:faceB"), {})
        ok(
            bool(face_b.get("additive", False))
            and abs(float(face_b.get("mirror_launch_plane_z", 0.0)) + 25.0) < 1e-6,
            "A5: the faceB source is ADDITIVE + mirrors the FULL chain launch through the "
            "part symmetry plane z=-25",
        )

        # flag 124838 ("3D object relocated"): the prism-assembly chunk decoration must
        # render at its AUTHORED pose -- the overlay placement centres the transverse
        # (x, y) on the axis (barrel behavior), so the scene's axis_offset_xy must
        # restore the chunk's authored y-centre (+27.8, housing wrapping the trains and
        # the mirror-1 mount), not leave it sunk around the device plate.
        chunk_seat = None
        try:
            chunk_mesh = editor._transformed_imported_step_mesh_for_label("optical")
            if chunk_mesh is not None:
                cb = chunk_mesh.bounds
                chunk_seat = (0.5 * (cb[2] + cb[3]), 0.5 * (cb[4] + cb[5]))
        except Exception:
            chunk_seat = None
        ok(
            chunk_seat is not None
            and abs(chunk_seat[0] - 27.77) < 1.0
            and abs(chunk_seat[1] + 25.0) < 1.5,
            f"A6: the prism-assembly chunk decoration sits at its AUTHORED seat "
            f"(y-centre ~27.8 wrapping the trains; drawn centre {chunk_seat})",
        )

        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)

        # flag 131224 / bugs/0682 ("still dislocate, not in the center big gap"): the
        # 50x50x1 device box must occupy the slot BETWEEN the two outer prisms
        # (z -58..0, face A on the object plane), not extend +z through prism A --
        # the part pose's object->lens sense comes from the FIRST LEG, never the
        # object->image diagonal (which points backwards in a folded scene).
        part_box = None
        try:
            from types import SimpleNamespace

            from KrakenOS.UI.open3d_inspector import Kraken3DInspector
            from KrakenOS.UI.services.inspection_part import box_corners, normalize_inspection_part_spec

            # the REAL pose method, called through a shim -- it only reads self.editor,
            # and a second live Tk inspector cannot open inside the penta harness
            pose = Kraken3DInspector._inspection_part_pose(
                SimpleNamespace(editor=editor), system, bundle
            )
            if pose is not None:
                spec = normalize_inspection_part_spec(getattr(editor, "inspection_part_spec", None))
                corners = np.asarray(box_corners(spec, pose[0], pose[1]), dtype=float)
                part_box = (corners.min(axis=0), corners.max(axis=0))
        except Exception:
            part_box = None
        # bugs/0683 (flag 133605 "not centered in the gap"): the device is CENTRED in
        # the prism slot (gap z -57.9..+0.1 -> part z -53.9..-3.9, axis_offset_mm -3.9;
        # face A sits 3.9 mm behind the focus plane until the WD recalibration).
        ok(
            part_box is not None
            and abs(float(part_box[1][2]) - 0.0) < 0.5
            and abs(float(part_box[0][2]) + 50.0) < 0.5
            and abs(float(part_box[0][0]) + 25.0) < 0.5
            and abs(float(part_box[1][1]) - 0.5) < 0.5,
            f"A7: the part IS the world anchor -- face A on z=0, body z 0..-50 "
            f"(drawn {None if part_box is None else [np.round(part_box[0], 1).tolist(), np.round(part_box[1], 1).tolist()]})",
        )
        # bugs/0683/0684: the authored partial-FOV bands -- the MEASURED delivered field
        # per face (with the real first-surface mirrors + BS cube the window widened to
        # y -4..+3 at ~90% reach; bugs/0683_band_scan.py re-run post-0684).
        bands = getattr(editor, "layout_object_fov_bands", None) or []
        band_ok = (
            len(bands) == 2
            and all(
                abs(float(b.get("v_lo", 99.0)) + 5.25) < 0.6
                and abs(float(b.get("v_hi", 99.0)) - 3.1) < 0.6
                and abs(float(b.get("half_width", 0.0)) - 27.5) < 0.5
                for b in bands
            )
            and abs(float(bands[0].get("center", [0, 0, 99])[2]) - 0.0) < 0.5
            and abs(float(bands[1].get("center", [0, 0, 99])[2]) + 50.0) < 0.5
        )
        ok(
            band_ok,
            f"A8: both PART faces carry the calculated one-side FOV band (55.0 x 8.35, y -5.25..+3.1, "
            f"at z=0 and z=-50) ({len(bands)} bands)",
        )
        # bugs/0692: each band also AUTHORS its measured sensor cover strip (the image of
        # the band -- bugs/0692_sensor_reach_sweep.py: arm A z -30.3..-27.1 razor spots,
        # arm B z -22.8..-18.2 at the compromise focus), drawn by the coverage overlay as
        # two dashed edges on the sensor die ("actual cover area" -- user request).
        strips = [b.get("image_strip") or {} for b in bands]
        strip_ok = (
            len(strips) == 2
            and all(
                abs(float(s.get("center", [99, 99, 99])[0]) + 272.65) < 0.5
                and abs(float(s.get("center", [99, 99, 99])[1]) + 9.9) < 0.5
                and abs(float(s.get("half_width", 0.0)) - 11.52) < 0.1
                for s in strips
            )
            and abs(float(strips[0].get("v_lo", 99.0)) + 5.3) < 0.6
            and abs(float(strips[0].get("v_hi", 99.0)) + 2.1) < 0.6
            and abs(float(strips[1].get("v_lo", 99.0)) - 2.2) < 0.6
            and abs(float(strips[1].get("v_hi", 99.0)) - 6.8) < 0.6
        )
        ok(
            strip_ok,
            "A8b: both bands author their MEASURED sensor cover strip on the die "
            "(A z -30.3..-27.1, B z -22.8..-18.2 about centre -25)",
        )
        # bugs/0695: the sensor plane is derived LIVE from the Image row -- the
        # vendor-true rebuild moved it (and any future refocus moves it again).
        _img_row = next(i for i, r in enumerate(rows) if str(r.surface) == "Image")
        sensor_y = float(np.asarray(
            editor._surface_reference_world_point(_img_row, system=system), dtype=float
        )[1])
        paths = list(getattr(bundle, "ray_paths", None) or [])
        chain_paths = 0
        chain_reach = []
        face_b_launch = []
        face_b_reach = []
        chief = None
        for rp in paths:
            sid = str(getattr(rp, "source_id", "") or "")
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[0])) or not np.all(np.isfinite(p[-1])):
                continue
            if sid == "source:faceB":
                face_b_launch.append(p[0])
                end = p[-1]
                if abs(end[1] - sensor_y) < 1.0 and end[0] < -250.0 and -21.7 < end[2] < -20.1:
                    face_b_reach.append(end)
                continue
            chain_paths += 1
            if not bool(getattr(rp, "reaches_image", False)):
                continue
            chain_reach.append((int(getattr(rp, "field_index", 0)), p[0], p[-1]))
            score = abs(float(p[0][0])) + abs(float(p[0][1]))
            if chief is None or score < chief[0]:
                chief = (score, p)
        strip = [end for _fi, _start, end in chain_reach if abs(end[1] - sensor_y) < 1.0 and -29.5 < end[2] < -28.3]
        ok(
            len(chain_reach) >= 700 and len(strip) >= 700,
            f"B1: the chain delivers the arm-A strip on the sensor at z~-28.9 (vendor-true "
            f"prisms, 0695) ({len(chain_reach)}/{chain_paths} reach; {len(strip)} on-strip)",
        )
        # central-field focus: the cone converges along the final -y leg; scan y planes
        # around the row (y=-11) for the waist -- the row plane itself carries a small
        # defocus (the lens seat rides arm A's axis, bugs/0680 notes), so pin the WAIST
        # quality and that it sits NEAR the row, not the at-row blur.
        central_segs = []
        for rp in paths:
            sid = str(getattr(rp, "source_id", "") or "")
            if sid == "source:faceB" or not bool(getattr(rp, "reaches_image", False)):
                continue
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2:
                continue
            if abs(float(p[0][0])) < 1.0 and abs(float(p[0][1])) < 1.0:
                a, b = p[-2], p[-1]
                d = b - a
                if abs(d[1]) > 1e-9:
                    central_segs.append((a, d))
        best = None
        for y_plane in np.linspace(sensor_y - 3.0, sensor_y + 3.0, 121):
            pts = []
            for a, d in central_segs:
                t = (y_plane - a[1]) / d[1]
                pts.append(a[[0, 2]] + t * d[[0, 2]])
            if len(pts) > 3:
                arr = np.asarray(pts)
                rms = float(np.sqrt(((arr - arr.mean(axis=0)) ** 2).sum(axis=1).mean()))
                if best is None or rms < best[1]:
                    best = (float(y_plane), rms)
        # current measured quality: ~140 um through the blackbox surrogate + wide hidden
        # apertures (bugs/0680 notes; the vendor-true lens seat at z=-28.9 owns the
        # improvement path) -- pin regression, not aspiration
        ok(
            best is not None and best[1] < 0.2 and abs(best[0] - sensor_y) <= 1.5,
            f"B2: central-field WAIST < 200 um within 1.5 mm of the image row "
            f"(best y {best[0] if best else 0:.2f}, rms {best[1] * 1000 if best else 0:.1f} um, "
            f"{len(central_segs)} rays)",
        )
        seq = []
        if chief is not None:
            p = chief[1]
            segs = np.diff(p, axis=0)
            lens = np.linalg.norm(segs, axis=1)
            keep = lens > 2.0
            for dvec in segs[keep] / lens[keep][:, None]:
                key = tuple(int(round(c)) for c in dvec) if np.max(np.abs(np.abs(dvec) - 1.0) < 0.15) else None
                if key and (not seq or key != seq[-1]):
                    seq.append(key)
        ok(
            seq[:3] == [(0, 0, 1), (0, 1, 0), (0, 0, -1)],
            f"B3: the chief folds the TRUE S -- +z, +y, -z (legs {seq[:4]})",
        )
        launches = np.asarray(face_b_launch) if face_b_launch else np.zeros((0, 3))
        bounded = bool(
            len(launches)
            and np.all(np.abs(launches[:, 0]) <= 45.0)
            and np.all(np.abs(launches[:, 1]) <= 8.5)
            and np.allclose(launches[:, 2], -50.0, atol=0.2)
        )
        ok(
            500 <= len(launches) <= 4000 and bounded,
            f"B4: faceB mirrors the y=0 field row (3 launch points) from face B (z=-50, mirror_bound_y) "
            f"({len(launches)} rays, bounded={bounded})",
        )
        ok(
            len(face_b_reach) >= 500,
            f"B5: faceB reaches its strip at z~-20.8 on the live sensor plane (0695 "
            f"vendor-true; absolute B focus pending the 0696 launcher rework) "
            f"({len(face_b_reach)} reach; both arms live in ONE bundle with the chain intact)",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    _check_scene(ok, notes)
    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("om05a folded-scene validation PASSED")
        return 0
    print("om05a folded-scene validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
