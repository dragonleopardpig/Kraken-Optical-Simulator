from pathlib import Path
import numpy as np
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services import optical_axis_tree as tree_mod

def load():
    e = KrakenLayoutEditor()
    e.layout_files["p"] = Path("attachment/machine_vision_150mm_test.py")
    e.load_layout_by_name("p")
    return e

def report(e, tag):
    d = e._lens_surrogate_datum_rows()
    bz = float(np.asarray(e._step_body_world_center("lens"), float)[2])
    dz = float(np.asarray(tree_mod.row_world_pose(e.rows, int(d[0])), float)[2]) if d else float("nan")
    off = tuple(round(float(v), 3) for v in np.asarray(e._step_placement_offset_xyz("lens"), float))
    print(f"{tag}: body_z={bz:.2f} datum_z={dz:.2f} gap={bz-dz:.3f} offset={off}", flush=True)

# 1: glue then clean 40-frame carry
e = load(); e.glue_step_overlay_to_surrogate("lens"); report(e, "M1 post-glue")
e.translate_step_overlay("lens", (0.2, 0.0, 0.6), refresh=False, record_history=False)
for _ in range(39): e.translate_step_overlay("lens", (0.0, 0.0, 0.6), refresh=False, record_history=False)
report(e, "M1 after +24 carry")

# 2: glue then one BIG-jitter frame (4mm > the 3mm gate) + 39 axial
e2 = load(); e2.glue_step_overlay_to_surrogate("lens")
e2.translate_step_overlay("lens", (4.0, 0.0, 0.6), refresh=False, record_history=False)
for _ in range(39): e2.translate_step_overlay("lens", (0.0, 0.0, 0.6), refresh=False, record_history=False)
report(e2, "M2 after 4mm-jitter carry")

# 3: glue then single big axial commit
e3 = load(); e3.glue_step_overlay_to_surrogate("lens")
e3.translate_step_overlay("lens", (0.0, 0.0, 42.0), refresh=False, record_history=False)
report(e3, "M3 after single +42")
