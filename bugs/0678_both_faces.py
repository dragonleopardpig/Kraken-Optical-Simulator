"""0678 (flag 094639): rays from BOTH faces of the 50x50x1 device in the arm-A
real scene -- the B-side prism train as inert pinned wedges (the 0224 beam-line
test keeps them out of arm A's sequential frame walk; the non-seq trace sees them
by geometry) + a face-B rectangle SOURCE emitting the second arm. FOV per face =
the sensor coverage (larger than the 50x1 face, as the user expects)."""
from dataclasses import asdict
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded_armA.py")
COMP = Path("attachment/om05a_components")

# (label, insert-after row name, wedge step, world centre, plane, d_in)
FOLDS_B = [
    ("Outer prism B", "RA mirror 2 (40 mm)", "wedge_105.step",
     (0.0, 0.0, -63.15), (0.0, 1.0, 1.0), (0.0, 0.0, -1.0)),
    ("Lower prism B", "RA mirror 2 (40 mm)", "wedge_150.step",
     (0.0, 11.65, -60.40), (0.0, 1.0, -1.0), (0.0, 1.0, 0.0)),
    ("Centre prism B", "RA mirror 2 (40 mm)", "wedge_120.step",
     (0.0, 13.73, -34.40), (0.0, 1.0, -1.0), (0.0, 0.0, 1.0)),
]


def main():
    import importlib.util

    spec_mod = importlib.util.spec_from_file_location("armA", "bugs/0676_build_armA.py")
    armA = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(armA)

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    for label, after_name, fname, centre, plane, d_in in FOLDS_B:
        if any(str(r.name) == label for r in editor.rows):
            continue
        idx = next(i for i, r in enumerate(editor.rows) if str(r.name) == after_name)
        mesh_path, cad_source, source_format = _optical_solid_mesh_path_from_source((COMP / fname).resolve())
        row = editor._optical_stl_solid_row(mesh_path.resolve(), source_path=(COMP / fname).resolve(),
                                            source_format=source_format)
        row.name = label
        row.thickness = 0.0  # zero-length pinned station at the chain END: the final
        # leg's beam line misses these planes by ~275 mm, so the 0224 hit-radius
        # test keeps them out of arm A's walk (inserted mid-chain they FOLDED the
        # frame -- the sign-agnostic line test sees planes BEHIND the launch too)
        row.diameter = 77.0
        row.glass = "BK7"
        faces = (row.advanced or {}).get("OpticalSolidFaces")
        face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
        hyp = None
        for rec in face_list or []:
            n = np.asarray(rec.get("normal") or [0, 0, 0], dtype=float)
            if abs(abs(n[1]) - 0.7071) < 0.06 and abs(abs(n[2]) - 0.7071) < 0.06:
                if hyp is None or int(rec.get("triangle_count") or 0) > int(hyp.get("triangle_count") or 0):
                    hyp = rec
        assert hyp is not None, label
        for rec in face_list or []:
            rec["port_role"] = "Auto"
        hyp["function"] = "Mirror"
        hyp["role"] = "Mirror"
        hyp["port_role"] = "Interaction Surface"
        hyp["assignment_source"] = "manual"
        picked = armA.pick_tilts(np.asarray(hyp.get("normal"), dtype=float), plane, d_in, False)
        assert picked is not None, f"{label}: no tilt matches"
        (tx, ty, tz), n_world = picked
        from KrakenOS.UI.nonseq_output_ports import row_z_positions

        zs = row_z_positions(editor.rows)
        z_station = float(zs[idx + 1]) if idx + 1 < len(zs) else 0.0
        row.tilt_x, row.tilt_y, row.tilt_z = float(tx), float(ty), float(tz)
        row.desp_x, row.desp_y = float(centre[0]), float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        row.advanced = dict(row.advanced or {})
        row.advanced["StepOverlayPromotion"] = {"center_world": list(map(float, centre))}
        editor.rows.insert(idx + 1, row)
        print(f"  {label}: pinned at {centre}, tilts ({tx},{ty},{tz}), hyp {np.round(n_world, 3)}")

    # face-B emitter: the second arm's rays (imaging NA, the face footprint)
    specs = list(getattr(editor, "layout_scene_source_specs", []) or [])
    if not any(s.get("source_id") == "source:faceB" for s in specs):
        specs.append({
            "source_id": "source:faceB",
            "name": "Device face B",
            "model": "Random rectangle source",
            "role": "illumination",
            "physical": True,
            "enabled": True,
            "source_x": 0.0, "source_y": 0.0, "source_z": -57.8,
            "source_l": 0.0, "source_m": 0.0, "source_n": -1.0,
            "radius_x": 25.0, "radius_y": 0.5, "radius": 25.0,
            "cone_deg": 2.2,
            "ray_count": 400,
            "power": 1.0,
            "wavelength": 0.55,
            "seed": 7,
        })
        editor.layout_scene_source_specs = specs
        print("  face-B source added")
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved")


def verify():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    chain_reach = 0
    src_paths = 0
    src_near_image = 0
    for rp in (getattr(bundle, "ray_paths", None) or []):
        sid = str(getattr(rp, "source_id", "") or "")
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[-1])):
            continue
        if sid == "source:faceB":
            src_paths += 1
            end = p[-1]
            if abs(end[0] + 272.7) < 15.0 and abs(end[1] + 11.0) < 15.0:
                src_near_image += 1
        elif bool(getattr(rp, "reaches_image", False)):
            chain_reach += 1
    print(f"chain (face A): {chain_reach} reach; face-B source: {src_paths} rays, "
          f"{src_near_image} end near the sensor")
    editor.destroy()


if __name__ == "__main__":
    main()
    verify()
