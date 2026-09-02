"""0695 stage 2: swap om05a's six fold rows to the VENDOR-EXACT solids and the
USER-CLARIFIED architecture (flag series 2026-09-02; fixes 0694's two focal
planes):

  window station ("BS cube X" rows):    -> FIRST RA MIRROR (one prism; the 0684
      model had the CUBE BS here -- backwards. The spurious far-half blocks at
      the towers are re-purposed as the REAL BS far halves below).
  lower station ("Outer RA mirror X"):  -> CUBE BS near half (coated hypotenuse
      folds the imaging beam toward the centre; LED transmits from below).
  centre station ("Centre RA mirror X"): same role, VENDOR-TRUE half-V prism
      (11.89 mm tall -- the old one was ~2x too tall, the 0694 root cause).
  far halves: moved to the lower station to complete the BS cubes.
  NEW: two LED panel rows (inert, glass AIR) lying FLAT under the BS cubes at
      the vendor PCB pose (user: "lying flat under the BS cube").

Meshes from bugs/0695_build_vendor_prisms.py (manifest_0695v.json).
"""
import json
import os
from pathlib import Path

import numpy as np

SCENE = Path(os.environ.get("KRAKEN_0695_SCENE", "attachment/om05a_folded.py"))
COMP = Path("attachment/om05a_components")
MANIFEST = json.loads((COMP / "manifest_0695v.json").read_text())

# old row name -> (new name, mesh, beam fold point in world)
SWAPS = {
    "BS cube A": ("First RA mirror A", "ra_mirror_A_0695v", (0.0, 0.25, 8.88)),
    "Outer RA mirror A": ("BS cube A", "bs_near_A_0695v", (0.0, 10.89, 8.88)),
    "Centre RA mirror A": ("Centre RA mirror A", "centre_half_A_0695v", (0.0, 10.89, -15.92)),
    "BS cube B": ("First RA mirror B", "ra_mirror_B_0695v", (0.0, 0.25, -58.88)),
    "Outer RA mirror B": ("BS cube B", "bs_near_B_0695v", (0.0, 10.89, -58.88)),
    "Centre RA mirror B": ("Centre RA mirror B", "centre_half_B_0695v", (0.0, 10.89, -34.08)),
    "BS cube A (far half)": ("BS cube A (far half)", "bs_far_A_0695v", None),
    "BS cube B (far half)": ("BS cube B (far half)", "bs_far_B_0695v", None),
}
LED_PANELS = [
    ("LED panel A", "led_panel_A_0695v"),
    ("LED panel B", "led_panel_B_0695v"),
]


def flag_faces(row, fold_point, center_world):
    faces = (row.advanced or {}).get("OpticalSolidFaces")
    face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
    assert face_list, row.name
    for rec in face_list:
        rec["port_role"] = "Auto"
    if fold_point is None:
        return
    target = np.asarray(fold_point, dtype=float)
    centre = np.asarray(center_world, dtype=float)
    hyp = hyp_dist = None
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
    print(f"    {row.name}: fold face {hyp_dist:.2f} mm from beam point, "
          f"n={[round(v, 2) for v in hyp.get('normal')]}")
    hyp["function"] = "Mirror"
    hyp["role"] = "Mirror"
    hyp["port_role"] = "Interaction Surface"
    hyp["assignment_source"] = "manual"


def new_solid_row(editor, mesh_name):
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    mesh_path, _src, source_format = _optical_solid_mesh_path_from_source(
        (COMP / f"{mesh_name}.step").resolve()
    )
    return editor._optical_stl_solid_row(
        mesh_path.resolve(), source_path=(COMP / f"{mesh_name}.step").resolve(),
        source_format=source_format,
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
    for name, mesh_name in LED_PANELS:
        if any(str(r.name) == name for r in editor.rows):
            continue
        centre = np.asarray(MANIFEST[mesh_name], dtype=float)
        row = new_solid_row(editor, mesh_name)
        row.name = name
        row.thickness = 0.0
        row.glass = "AIR"  # inert PCB: drawn + pickable, never refracts
        row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        flag_faces(row, None, centre)
        adv = dict(row.advanced or {})
        adv["StepOverlayPromotion"] = {"center_world": centre.tolist()}
        row.advanced = adv
        editor.rows.insert(image_index, row)
        zs = row_z_positions(editor.rows)
        z_station = float(zs[image_index]) if image_index < len(zs) else 0.0
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
            if abs(e[1] + 9.9) < 3 and e[0] < -250:
                b_reach += 1
            continue
        chain_n += 1
        if bool(getattr(rp, "reaches_image", False)):
            chain_reach += 1
            ends.append(p[-1])
    msg = f"chain {chain_reach}/{chain_n} reach; faceB {b_reach}/{b_n}"
    if ends:
        E = np.asarray(ends)
        msg += f"; chain strip z {E[:, 2].min():.1f}..{E[:, 2].max():.1f} y {E[:, 1].mean():.1f}"
    print(msg)
    editor.destroy()


if __name__ == "__main__":
    main()
    verify()
