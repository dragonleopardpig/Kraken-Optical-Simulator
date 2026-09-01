"""0684 stage 2: swap the six fold rows of attachment/om05a_folded.py to the REAL
CAD optics (extracted by bugs/0684_extract_real_optics.py):

  station z ~ +5.3/-63.2 ("Lower"):  BS CUBE -- near half traced (through-glass,
      TIR fold at the cement diagonal = Mirror/Interaction), far half added as a
      plain glass solid so the cube reads ATTACHED;
  station y 11.65 ("Outer"):         first-surface RA MIRROR (real CAD solid);
  station z -22.9/-34.9 ("Centre"):  first-surface RA MIRROR (V-block half).

All meshes are authored world-aligned about their own bbox centre: tilts 0,
desp = center_world - station. Old wedge rows keep their station/thickness; only
solid, faces, name, pose change. Verify with bugs/0680_symmetric_b.py-style stats.
"""
import json
import os
from pathlib import Path

import numpy as np

SCENE = Path(os.environ.get("KRAKEN_0684_SCENE", "attachment/om05a_folded.py"))
ONLY = {name for name in os.environ.get("KRAKEN_0684_ONLY", "").split(",") if name}
COMP = Path("attachment/om05a_components")
MANIFEST = json.loads((COMP / "manifest_0684r.json").read_text())

# old row name -> (new name, mesh, beam fold point on the station axis).
# The mirror solids carry TWO nearly-parallel 45-degree faces (coated front +
# back, ~0.2 mm apart, areas within 0.5%) -- an area-based hyp pick is a coin
# flip that lands on the BACK face and turns a first-surface mirror into a
# through-glass Fresnel splitter (3249 split paths, 0 reach). Pick the 45-degree
# face whose PLANE passes closest to the station's beam fold point instead.
SWAPS = {
    "Outer prism A": ("BS cube A", "bs_near_half_A_0684r", (0.0, 0.0, 4.88)),
    "Lower prism A": ("Outer RA mirror A", "outer_mirror_A_0684r", (0.0, 9.4, 4.88)),
    "Centre prism A": ("Centre RA mirror A", "centre_mirror_A_0684r", (0.0, 9.4, -20.0)),
    "Outer prism B": ("BS cube B", "bs_near_half_B_0684r", (0.0, 0.0, -62.68)),
    "Lower prism B": ("Outer RA mirror B", "outer_mirror_B_0684r", (0.0, 9.4, -62.68)),
    "Centre prism B": ("Centre RA mirror B", "centre_mirror_B_0684r", (0.0, 9.4, -37.8)),
}
FAR_HALVES = [
    ("BS cube A (far half)", "bs_far_half_A_0684r"),
    ("BS cube B (far half)", "bs_far_half_B_0684r"),
]


def flag_faces(row, fold_point, center_world):
    """Flag the coated fold face: the 45-degree face whose plane passes closest to
    the station's beam fold point (world). `fold_point=None` -> no mirror face."""
    faces = (row.advanced or {}).get("OpticalSolidFaces")
    face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
    assert face_list, row.name
    for rec in face_list:
        rec["port_role"] = "Auto"
    if fold_point is None:
        return
    target = np.asarray(fold_point, dtype=float)
    centre = np.asarray(center_world, dtype=float)
    hyp = None
    hyp_dist = None
    for rec in face_list:
        n = np.asarray(rec.get("normal") or (0, 0, 0), dtype=float)
        if not (abs(abs(n[1]) - 0.7071) < 0.05 and abs(abs(n[2]) - 0.7071) < 0.05):
            continue
        if float(rec.get("area_mm2") or 0.0) < 100.0:
            continue
        c_world = np.asarray(rec.get("centroid") or (0, 0, 0), dtype=float) + centre
        norm = n / max(float(np.linalg.norm(n)), 1e-12)
        dist = abs(float(norm @ (target - c_world)))
        if hyp is None or dist < hyp_dist:
            hyp, hyp_dist = rec, dist
    assert hyp is not None, f"{row.name}: no 45-degree face"
    print(f"    {row.name}: fold face plane {hyp_dist:.2f} mm from the beam point, "
          f"n={[round(v, 2) for v in hyp.get('normal')]}")
    hyp["function"] = "Mirror"
    hyp["role"] = "Mirror"
    hyp["port_role"] = "Interaction Surface"
    hyp["assignment_source"] = "manual"


def new_solid_row(editor, mesh_name):
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    mesh_path, _src, source_format = _optical_solid_mesh_path_from_source((COMP / f"{mesh_name}.step").resolve())
    return editor._optical_stl_solid_row(
        mesh_path.resolve(), source_path=(COMP / f"{mesh_name}.step").resolve(), source_format=source_format
    )


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import row_z_positions

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    for index, row in enumerate(list(editor.rows)):
        name = str(row.name)
        if name not in SWAPS:
            continue
        if ONLY and name not in ONLY:
            continue
        new_name, mesh_name, fold_point = SWAPS[name]
        centre = np.asarray(MANIFEST[mesh_name], dtype=float)
        fresh = new_solid_row(editor, mesh_name)
        row.name = new_name
        row.element = fresh.element
        row.glass = "BK7"
        row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        adv = dict(row.advanced or {})
        fresh_adv = dict(fresh.advanced or {})
        for key in ("Solid_3d_stl", "OpticalSolidSourcePath", "OpticalSolidSourceFormat",
                    "OpticalSolidFaces", "Note"):
            if key in fresh_adv:
                adv[key] = fresh_adv[key]
        adv["StepOverlayPromotion"] = {"center_world": centre.tolist()}
        row.advanced = adv
        flag_faces(row, fold_point, centre)
        zs = row_z_positions(editor.rows)
        z_station = float(zs[index]) if index < len(zs) else 0.0
        row.desp_x, row.desp_y = float(centre[0]), float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        print(f"  {name} -> {new_name} at {np.round(centre, 2).tolist()} (station z {z_station:.2f})")

    image_index = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image")
    for name, mesh_name in FAR_HALVES:
        if any(str(r.name) == name for r in editor.rows):
            continue
        if ONLY and name not in ONLY:
            continue
        centre = np.asarray(MANIFEST[mesh_name], dtype=float)
        row = new_solid_row(editor, mesh_name)
        row.name = name
        row.thickness = 0.0
        row.glass = "BK7"
        row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        flag_faces(row, None, centre)
        adv = dict(row.advanced or {})
        # bugs/0686: NO beam_splitter mark -- the mark routes the row into the branch
        # machinery (every crossing ray spawns split children: the user's 7300-ray lag).
        # The 0686 walk gate (an off-beam pinned inferred output never re-sources the
        # frame) is what keeps the far half's cement face from folding the Image.
        adv["StepOverlayPromotion"] = {"center_world": centre.tolist()}
        row.advanced = adv
        insert_at = image_index
        editor.rows.insert(insert_at, row)
        zs = row_z_positions(editor.rows)
        z_station = float(zs[insert_at]) if insert_at < len(zs) else 0.0
        row.desp_x, row.desp_y = float(centre[0]), float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        image_index = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image")
        print(f"  + {name} at {np.round(centre, 2).tolist()} (station z {z_station:.2f})")

    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)


def verify():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    chain_n = chain_reach = b_n = b_reach = 0
    ends = []
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[-1])):
            continue
        if sid == "source:faceB":
            b_n += 1
            e = p[-1]
            if abs(e[1] + 11) < 2 and e[0] < -250:
                b_reach += 1
            continue
        chain_n += 1
        if bool(getattr(rp, "reaches_image", False)):
            chain_reach += 1
            ends.append(p[-1])
    msg = f"chain {chain_n}/{chain_reach} reach; faceB {b_n}/{b_reach}"
    if ends:
        E = np.asarray(ends)
        msg += f"; chain strip z {E[:,2].min():.1f}..{E[:,2].max():.1f} y {E[:,1].mean():.1f}"
    print(msg)
    editor.destroy()


if __name__ == "__main__":
    main()
    verify()
