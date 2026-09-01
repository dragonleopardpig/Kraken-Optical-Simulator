"""0680: the symmetric B side, with CORRECT accounting (chain = 'source:0').

Stage 1: face-B source alone on a COPY -- does the chain (source:0) survive?
Stage 2: + the three pinned B-side wedges (chain end) -- chain still alive, and
         where do the faceB rays go?
Stage 3: apply to the real scene when green.
"""
import importlib.util
import shutil
from pathlib import Path

import numpy as np

WORK = Path("attachment/om05a_symB_work.py")
COMP = Path("attachment/om05a_components")

FOLDS_B = [
    ("Outer prism B", (0.0, 0.0, -63.15), (0.0, 1.0, 1.0), (0.0, 0.0, -1.0), "wedge_105.step"),
    ("Lower prism B", (0.0, 11.65, -60.40), (0.0, 1.0, -1.0), (0.0, 1.0, 0.0), "wedge_150.step"),
    ("Centre prism B", (0.0, 13.73, -34.40), (0.0, 1.0, -1.0), (0.0, 0.0, 1.0), "wedge_120.step"),
]

FACEB_SOURCE = {
    "source_id": "source:faceB", "name": "Device face B",
    "model": "Random rectangle source", "role": "illumination",
    "physical": True, "enabled": True, "additive": True,
    "source_x": 0.0, "source_y": 0.0, "source_z": -57.8,
    "source_l": 0.0, "source_m": 0.0, "source_n": -1.0,
    "radius_x": 25.0, "radius_y": 0.5, "radius": 25.0,
    # the scene is mirror-symmetric about the shared lens leg plane z=-28.9: arm B's
    # exact imaging bundle is the chain's calibrated launch reflected through it
    "mirror_launch_plane_z": -28.9,
    "cone_deg": 5.5, "ray_count": 400, "power": 1.0, "wavelength": 0.55, "seed": 7,
}


def load(scene):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path(scene).resolve()
    editor.load_layout_by_name("p")
    return editor


def stats(editor, tag):
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    chain_reach = 0
    chain_n = 0
    b_n = 0
    b_ends = []
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[-1])):
            continue
        if sid == "source:faceB":
            b_n += 1
            b_ends.append(p[-1])
        else:
            chain_n += 1
            if bool(getattr(rp, "reaches_image", False)):
                chain_reach += 1
    msg = f"{tag}: chain {chain_n}/{chain_reach} reach; faceB {b_n} rays"
    if b_ends:
        ends = np.asarray(b_ends)
        near = int(np.sum((np.abs(ends[:, 0] + 272.7) < 25) & (np.abs(ends[:, 1] + 11) < 25)))
        centroid = np.round(ends.mean(axis=0), 1).tolist()
        msg += f", {near} end near the sensor, mean end {centroid}"
    print(msg)


def main():
    shutil.copyfile("attachment/om05a_folded.py", WORK)
    editor = load(WORK)
    stats(editor, "stage 0 (baseline copy)")
    editor.destroy()

    # stage 1: source only
    editor = load(WORK)
    specs = list(getattr(editor, "layout_scene_source_specs", []) or [])
    specs.append(dict(FACEB_SOURCE))
    editor.layout_scene_source_specs = specs
    editor._sync_table()
    editor._write_layout_file(WORK.resolve())
    editor.destroy()
    editor = load(WORK)
    stats(editor, "stage 1 (source only)")
    editor.destroy()

    # stage 2: + pinned B wedges at the chain end
    spec_mod = importlib.util.spec_from_file_location("armA", "bugs/0676_build_armA.py")
    armA = importlib.util.module_from_spec(spec_mod)
    spec_mod.loader.exec_module(armA)
    from KrakenOS.UI.nonseq_output_ports import row_z_positions
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    editor = load(WORK)
    for label, centre, plane, d_in, fname in FOLDS_B:
        # insert immediately BEFORE the Image row -- truly at the chain END, after the
        # REAL mirror row. (A substring match on "RA mirror 2" hit the VIRTUAL 'to
        # camera (unfolded RA mirror 2)' station first and parked the wedges mid-chain,
        # where the 0224 backward-line test folds the frame: reach 68 -> 2.)
        idx = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image") - 1
        mesh_path, cad_source, source_format = _optical_solid_mesh_path_from_source((COMP / fname).resolve())
        row = editor._optical_stl_solid_row(mesh_path.resolve(), source_path=None, source_format=source_format)
        row.name = label
        row.thickness = 0.0
        row.glass = "BK7"
        faces = (row.advanced or {}).get("OpticalSolidFaces")
        face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
        hyp = max((rec for rec in face_list or []
                   if abs(abs(np.asarray(rec.get("normal"), dtype=float)[1]) - 0.7071) < 0.06),
                  key=lambda r: int(r.get("triangle_count") or 0))
        for rec in face_list or []:
            rec["port_role"] = "Auto"
        hyp.update(function="Mirror", role="Mirror", port_role="Interaction Surface",
                   assignment_source="manual")
        picked = armA.pick_tilts(np.asarray(hyp.get("normal"), dtype=float), plane, d_in, False)
        assert picked is not None, label
        (tx, ty, tz), _n = picked
        zs = row_z_positions(editor.rows)
        z_station = float(zs[idx + 1]) if idx + 1 < len(zs) else 0.0
        row.tilt_x, row.tilt_y, row.tilt_z = tx, ty, tz
        row.desp_x, row.desp_y, row.desp_z = centre[0], centre[1], centre[2] - z_station
        row.advanced = dict(row.advanced or {})
        row.advanced["StepOverlayPromotion"] = {"center_world": list(map(float, centre))}
        editor.rows.insert(idx + 1, row)
        print(f"  {label} pinned, tilts ({tx},{ty},{tz})")
    editor._sync_table()
    editor._write_layout_file(WORK.resolve())
    editor.destroy()
    editor = load(WORK)
    stats(editor, "stage 2 (source + B wedges)")
    editor.destroy()


if __name__ == "__main__":
    main()
