"""om05a folded scene, both mirrors: mutate -> save -> reload FRESH -> trace."""
import math
import shutil
from pathlib import Path

import numpy as np

STRAIGHT = Path("attachment/om05a_two_side.py")
SCENE = Path("attachment/om05a_folded.py")
COMP = Path("attachment/om05a_components")


def extract_mirror2_s():
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    from OCC.Extend.DataExchange import read_step_file_with_names_colors

    shapes = read_step_file_with_names_colors("attachment/om05a_26_1_r03_2s_lr_asm.stp")
    for shape, (name, _c) in shapes.items():
        if str(name) != "MIRROR_40X40X40":
            continue
        rot = gp_Trsf()
        rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.radians(90.0))
        rotated = shape.Moved(TopLoc_Location(rot))
        box = Bnd_Box()
        brepbndlib.Add(rotated, box)
        x0, y0, z0, x1, y1, z1 = box.Get()
        tr = gp_Trsf()
        tr.SetTranslation(gp_Vec(-(x0 + x1) / 2, -(y0 + y1) / 2, -(z0 + z1) / 2))
        w = STEPControl_Writer()
        w.Transfer(rotated.Moved(TopLoc_Location(tr)), STEPControl_AsIs)
        w.Write(str(COMP / "mirror2_chain_s.step"))
        print("mirror2_chain.step re-extracted (true S: leg3 anti-parallel to leg1)")
        return
    raise SystemExit("mirror2 not found")


def face_at_45(faces, want_sign):
    best = None
    for rec in faces or []:
        n = np.asarray(rec.get("normal") or [0, 0, 0], dtype=float)
        if abs(abs(n[1]) - 0.7071) < 0.06 and abs(abs(n[2]) - 0.7071) < 0.06 and abs(n[0]) < 0.06:
            if want_sign is not None and np.sign(n[1] * n[2]) != want_sign:
                continue
            count = int(rec.get("triangle_count") or 0)
            if best is None or count > int(best.get("triangle_count") or 0):
                best = rec
    return best


def insert_mirror(editor, *, after_name, gap_before, gap_after, step_name, label, want_sign=None):
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    rows = editor.rows
    idx = next(i for i, r in enumerate(rows) if str(r.name) == after_name)
    rows[idx].thickness = gap_before
    mesh_path, cad_source, source_format = _optical_solid_mesh_path_from_source((COMP / step_name).resolve())
    row = editor._optical_stl_solid_row(mesh_path.resolve(), source_path=(COMP / step_name).resolve(),
                                        source_format=source_format)
    row.name = label
    row.thickness = gap_after
    row.diameter = 77.0
    row.glass = "BK7"
    faces = (row.advanced or {}).get("OpticalSolidFaces")
    face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
    hyp = face_at_45(face_list or [], want_sign)
    assert hyp is not None, f"{label}: no 45-degree face"
    # the working Pyrite85 contract: passives are Transmit/Port + Auto; ONLY the
    # mirror face is an Interaction Surface -- with every face an Interaction
    # Surface no output port can be inferred and the fold poses never build.
    for rec in face_list or []:
        if rec is not hyp:
            rec["port_role"] = "Auto"
    hyp["function"] = "Mirror"
    hyp["role"] = "Mirror"
    hyp["port_role"] = "Interaction Surface"
    hyp["assignment_source"] = "manual"
    print(f"  {label}: {hyp.get('face_id')} n={np.round(np.asarray(hyp['normal'], dtype=float), 3)} -> Mirror")
    editor.rows.insert(idx + 1, row)


def build():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    shutil.copyfile(STRAIGHT, SCENE)
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["omf"] = SCENE.resolve()
    editor.load_layout_by_name("omf")
    editor.display_fold_spec = None  # this scene IS folded; the straight scene keeps the view spec
    # mirror 1 between the centre prism and the lens: hypotenuse at chain z=94.93
    insert_mirror(editor, after_name="to lens (unfolded RA mirror 1)", gap_before=33.08,
                  gap_after=180.47, step_name="mirror1_chain.step", label="RA mirror 1 (50 mm)")
    # NB insert_mirror set the PRECEDING row ('to lens') to 33.08 -- but mirror1 must
    # follow the CENTRE PRISM leg; the 'to lens' row IS that leg, correct as is.
    insert_mirror(editor, after_name="to camera (unfolded RA mirror 2)", gap_before=31.11,
                  gap_after=47.40, step_name="mirror2_chain_s.step", label="RA mirror 2 (40 mm)")
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved (no trace in the mutating process)")


def verify():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["omf"] = SCENE.resolve()
    editor.load_layout_by_name("omf")
    rows2 = editor._folded_sequential_trace_rows(editor.rows)
    mirrors = [] if rows2 is None else [(r.name, round(float(r.tilt_x), 1)) for r in rows2 if r.surface == "Mirror"]
    print("sequential fold rows:", mirrors)
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    paths = list(getattr(bundle, "ray_paths", None) or [])
    reached = [rp for rp in paths if bool(getattr(rp, "reaches_image", False))]
    print(f"trace: {len(paths)} paths, {len(reached)} reach image")
    if reached:
        p = np.asarray(getattr(reached[len(reached) // 2], "points_world", None), dtype=float)
        segs = np.diff(p, axis=0)
        lens = np.linalg.norm(segs, axis=1)
        keep = lens > 2.0
        dirs = segs[keep] / lens[keep][:, None]
        seq = []
        for d in np.round(dirs, 2):
            key = tuple(int(round(c)) for c in d) if np.max(np.abs(np.abs(d) - 1.0) < 0.15) else tuple(d)
            if not seq or key != seq[-1]:
                seq.append(key)
        print("chief leg directions:", seq[:8])
        print("image endpoint:", np.round(p[-1], 1).tolist())
    editor.destroy()


if __name__ == "__main__":
    extract_mirror2_s()
    build()
    verify()
