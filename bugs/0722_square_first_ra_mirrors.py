"""0722: the first RA mirrors must fold EXACTLY 90 deg (user: "the ray should bend 90
degree for whatever mirror or BS in this design, so there shouldn't be 45.29 degree").

bugs/0695_build_vendor_prisms.py read the first RA mirror off the vendor section as
9.8 x 9.9 legs -> hypotenuse 45.29 deg -> the follower walk's first reflection dips the
whole imaging chain by 0.58 deg (1.09 mm at the sensor, the two strips not mirror images).

  --build : regenerate ONLY ra_mirror_A/B_0695v.step with square 9.85 x 9.85 legs
            (same bbox centre -> manifest / desp unchanged; backups *.pre-0722.bak).
  --seat  : re-seat the lens chain (row 'Front Optical Vertex Datum' frame-desp, the 0689
            mechanism) onto the fold prism's centre plane -- the old seat embedded the dip.
  --apply : re-promote rows 'First RA mirror A/B' in the given scenes through the editor's
            own STEP -> mesh -> analytic-solid path (new Solid_3d_stl + OpticalSolidFaces),
            copying every non-geometric face attribute from the existing records (matched
            by normal) so the Mirror flag / coatings survive; then save the layout.

Run (one heavy job at a time):
  .devenv/state/venv/bin/python bugs/0722_square_first_ra_mirrors.py --build
  taskset -c 0-5 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u \
      bugs/0722_square_first_ra_mirrors.py --apply attachment/om05a_folded_80mm.py
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

COMP = Path("attachment/om05a_components")
LOG = os.environ.get("KRAKEN_0722_LOG", "bugs/0722_square_first_ra_mirrors.log")
_t0 = time.perf_counter()
ROWS = {"First RA mirror A": "ra_mirror_A_0695v", "First RA mirror B": "ra_mirror_B_0695v"}
GEOMETRIC = {"normal", "centroid", "area_mm2", "triangle_count", "triangle_indices", "plane_offset_mm",
             "component_face_id", "source_face_id", "source_solid_index", "source_face_index",
             "surface_type", "analytic_parameters", "interior_duplicate", "duplicate_group", "face_id"}


def step(msg):
    line = f"[{time.perf_counter() - _t0:6.1f}s] {msg}\n"
    fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.write(fd, line.encode()); os.fsync(fd); os.close(fd)
    print(line, end="", flush=True)


def _builder():
    spec = importlib.util.spec_from_file_location("build0695", "bugs/0695_build_vendor_prisms.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def build():
    b = _builder()
    ra = [b.scene_pt(29.075, 30.775), b.scene_pt(38.925, 20.925), b.scene_pt(38.925, 30.775)]
    manifest = json.loads((COMP / "manifest_0695v.json").read_text())
    for side in ("A", "B"):
        prof = ra if side == "A" else b.mirror_profile(ra)
        shape, (cx, cy, cz) = b.extruded_solid(prof)
        path = b.save_step(shape, f"ra_mirror_{side}_0695v.step")
        old = manifest[f"ra_mirror_{side}_0695v"]
        step(f"built {path} centre ({cx:.4f}, {cy:.4f}, {cz:.4f}) manifest {old} "
             f"profile {[(round(z, 3), round(y, 3)) for z, y in prof]}")
        assert abs(cy - old[1]) < 1e-6 and abs(cz - old[2]) < 1e-6, "bbox centre moved -- desp would be stale"


def _hyp_normal(faces):
    for rec in faces:
        n = np.asarray(rec.get("normal"), float)
        if abs(abs(n[1]) - abs(n[2])) < 0.05 and abs(n[0]) < 0.05 and float(rec.get("area_mm2") or 0) > 100:
            return n
    return None


def apply(scene_paths):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    for scene in scene_paths:
        scene = Path(scene)
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor._preview_trace_deferred_until_requested = True
        editor.layout_files["p"] = scene.resolve()
        editor.load_layout_by_name("p")
        step(f"{scene}: loaded {len(editor.rows)} rows")
        for row in editor.rows:
            mesh_name = ROWS.get(str(row.name))
            if mesh_name is None:
                continue
            old_faces = ((row.advanced or {}).get("OpticalSolidFaces") or {}).get("faces") or []
            src = (COMP / f"{mesh_name}.step").resolve()
            mesh_path, _s, fmt = _optical_solid_mesh_path_from_source(src)
            fresh = editor._optical_stl_solid_row(Path(mesh_path).resolve(), source_path=src, source_format=fmt)
            fresh_adv = dict(fresh.advanced or {})
            new_faces = (fresh_adv.get("OpticalSolidFaces") or {}).get("faces") or []
            assert new_faces and len(new_faces) == len(old_faces), (row.name, len(new_faces), len(old_faces))
            used = set()
            for rec in new_faces:
                n = np.asarray(rec.get("normal"), float)
                best, best_d = None, 9e9
                for j, o in enumerate(old_faces):
                    if j in used:
                        continue
                    d = float(np.linalg.norm(np.asarray(o.get("normal"), float) - n))
                    if d < best_d:
                        best, best_d = j, d
                assert best is not None and best_d < 0.05, (row.name, rec.get("face_id"), best_d)
                used.add(best)
                for key, value in old_faces[best].items():
                    if key not in GEOMETRIC:
                        rec[key] = value
            adv = dict(row.advanced or {})
            for key in ("Solid_3d_stl", "OpticalSolidSourcePath", "OpticalSolidSourceFormat", "OpticalSolidFaces", "Note"):
                if key in fresh_adv:
                    adv[key] = fresh_adv[key]
            row.advanced = adv
            row.element = fresh.element
            n_old, n_new = _hyp_normal(old_faces), _hyp_normal(new_faces)
            ang_old = np.degrees(np.arctan2(abs(n_old[1]), abs(n_old[2]))) if n_old is not None else float("nan")
            ang_new = np.degrees(np.arctan2(abs(n_new[1]), abs(n_new[2]))) if n_new is not None else float("nan")
            roles = [(r.get("face_id"), r.get("role")) for r in new_faces]
            step(f"  {row.name}: hyp normal {np.round(n_old, 5).tolist()} ({ang_old:.2f} deg) -> "
                 f"{np.round(n_new, 5).tolist()} ({ang_new:.2f} deg); stl {adv['Solid_3d_stl']}; roles {roles}")
            assert abs(ang_new - 45.0) < 0.01, ang_new
        editor._sync_table()
        editor._write_layout_file(scene.resolve())
        editor.destroy()
        step(f"{scene}: saved")


def seat(scene_paths):
    """Re-seat the lens chain on the fold prism's symmetry plane with the 0689 mechanism
    (ONE frame-desp on the first follower row): the old seat was computed against the
    dipped frame and is stale once the first fold is exactly 90 deg."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

    for scene in scene_paths:
        scene = Path(scene)
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor._preview_trace_deferred_until_requested = True
        editor.layout_files["p"] = scene.resolve()
        editor.load_layout_by_name("p")
        rows = list(editor.rows)
        prism = next(i for i, r in enumerate(rows) if str(r.name).startswith("RA mirror 1"))
        first = next(i for i, r in enumerate(rows) if str(r.name) == "Front Optical Vertex Datum")
        sensor = next(i for i, r in enumerate(rows) if str(r.surface) == "Image")
        ov = optical_solid_output_port_pose_overrides(None, rows)
        axis_z = float(np.asarray(ov[prism]["center"], float)[2])
        p8 = ov[first]
        centre = np.asarray(p8["center"], float).reshape(3)
        R = np.asarray(p8["rotation"], float).reshape(3, 3)
        row = rows[first]
        desp_old = np.array([float(row.desp_x or 0), float(row.desp_y or 0), float(row.desp_z or 0)])
        shift = np.array([0.0, 0.0, axis_z - centre[2]])
        desp_new = desp_old + R.T @ shift
        step(f"{scene}: prism axis z {axis_z:+.4f}; row {first} centre {np.round(centre, 4).tolist()} -> world shift "
             f"{np.round(shift, 4).tolist()}; desp {np.round(desp_old, 4).tolist()} -> {np.round(desp_new, 4).tolist()}")
        row.desp_x, row.desp_y, row.desp_z = (float(v) for v in desp_new)
        ov2 = optical_solid_output_port_pose_overrides(None, editor.rows)
        for i in (first, sensor):
            c = np.asarray(ov2[i]["center"], float); Rr = np.asarray(ov2[i]["rotation"], float).reshape(3, 3)
            step(f"  after: row {i} '{rows[i].name}' centre {np.round(c, 4).tolist()} axis {np.round(Rr[:, 2], 5).tolist()}")
        assert abs(float(np.asarray(ov2[first]["center"], float)[2]) - axis_z) < 1e-6
        editor._sync_table()
        editor._write_layout_file(scene.resolve())
        editor.destroy()
        step(f"{scene}: saved (re-seated)")


def main(argv):
    if "--build" in argv:
        build()
    scenes = [a for a in argv if a.endswith(".py")]
    if "--apply" in argv:
        apply(scenes)
    if "--seat" in argv:
        seat(scenes)
    step("DONE " + " ".join(argv))


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        import traceback
        step("EXCEPTION " + traceback.format_exc()[-1500:])
        raise
