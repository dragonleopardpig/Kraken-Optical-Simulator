from pathlib import Path
from collections import Counter
import numpy as np
from KrakenOS.UI.layout_editor import KrakenLayoutEditor

def report(app, tag):
    z = app._row_z_positions()
    img = next(i for i in range(len(app.rows)-1,-1,-1) if str(getattr(app.rows[i],'surface',''))=='Image')
    presc = np.array([float(app.rows[img].desp_x), float(app.rows[img].desp_y), float(z[img])+float(app.rows[img].desp_z)])
    try:
        m = app._transformed_imported_step_mesh_for_label("camera"); b=np.asarray(m.bounds).reshape(6)
        cam = np.array([(b[0]+b[1])/2,(b[2]+b[3])/2,(b[4]+b[5])/2])
    except Exception: cam = None
    _s,_r,bundle = app._build_preview_system_rays_bundle(sampling_mode=None, update_state=True, trace_rays=True)
    dets=[]
    for t in list(getattr(bundle,'targets',[]) or []):
        md=getattr(t,'metadata',None) or {}
        if getattr(t,'is_detector',False):
            c=np.asarray(getattr(t,'center_world',[0,0,0])).reshape(-1)[:3]
            dets.append((str(md.get('focus_source','')), np.round(c,2).tolist(), bool(md.get('draw_suppressed'))))
    st=Counter()
    for _i,_c,_p,s in app._iter_3d_scene_ray_records(_r,bundle): st[str(s or '').lower()]+=1
    print(f"--- {tag}")
    print(f"    Image row {img}: prescription={np.round(presc,2).tolist()}  camera_body={None if cam is None else np.round(cam,2).tolist()}")
    for d in dets: print(f"    detector focus={d[0]:16s} center={d[1]} supp={d[2]}")
    print(f"    rays={dict(st)}")
    return presc

app = KrakenLayoutEditor()
try:
    app.layout_files["az85"]=Path("attachment/machine_vision_AZ85_RA_Mirror.py")
    app.load_layout_by_name("az85")
    report(app,"1. original")
    m1=next(i for i,r in enumerate(app.rows) if "Promoted" in str(getattr(r,'name','')))
    app.delete_optical_step_rows([m1])
    report(app,"2. 1st RA mirror deleted")
    try: app._select_table_indices([1],focus_index=1)
    except Exception: app._select_table_row(1)
    app.add_beam_splitter_to_led(kind="plate")
    report(app,"3. BS added")
    # the user's rubber band: every row except Object and the BS
    bs=[i for i,r in enumerate(app.rows) if "Promoted" in str(getattr(r,'name','')) and float(r.desp_x)<40]
    chain=[i for i in range(1,len(app.rows)) if i not in bs]
    z=app._row_z_positions(); leg_z=float(z[chain[0]])+float(app.rows[chain[0]].desp_z)
    app.snap_rows_to_axis(chain, {"axis_id":"axis:global:split",
        "points":np.array([(0.0,0.0,leg_z),(400.0,0.0,leg_z)]),
        "picked_world":np.array([90.0,0.0,leg_z])})
    report(app,f"4. snapped rows {chain}")
finally:
    try: app.destroy()
    except Exception: pass
