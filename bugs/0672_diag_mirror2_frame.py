"""0672: why is mirror2's fold invariant to its face-plane sign? Print the swept
pose, the interaction face's world normal, and the reflected leg -- no ray trace."""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import (
        _downstream_pose_from_frame,
        _frame_rotation_from_normal,
        _optical_solid_faces_at_pose,
        _reflected_frame_from_interaction_face,
        _row_has_optical_solid,
        row_z_positions,
        select_optical_solid_interaction_face,
    )

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    rows = editor.rows
    zs = row_z_positions(rows)
    solids = [i for i, r in enumerate(rows) if _row_has_optical_solid(r)]
    print("solid rows:", [(i, rows[i].name) for i in solids])
    m1, m2 = solids[0], solids[1]

    # mirror 1: straight incoming frame at its station
    o1 = np.array([0.0, 0.0, float(zs[m1])])
    r1 = _frame_rotation_from_normal((0.0, 0.0, 1.0))
    faces1 = _optical_solid_faces_at_pose(
        rows[m1], np.array([0.0, 0.0, float(zs[m1])]), r1, assigned_only=True)
    f1 = select_optical_solid_interaction_face(faces1)
    print("m1 interaction n_world:", np.round(np.asarray(f1.get("normal_world"), dtype=float), 3),
          "centroid:", np.round(np.asarray(f1.get("centroid_world"), dtype=float), 1))
    frame1 = _reflected_frame_from_interaction_face(faces1, o1, r1, float(rows[m1].thickness))
    c1, rot1 = frame1
    print("after m1: leg dir", np.round(rot1[:, 2], 3), " frame origin", np.round(c1, 1))

    # mirror 2 as the follower: swept pose from the folded frame
    center2, rotm2 = _downstream_pose_from_frame(rows[m2], c1, rot1)
    print("m2 swept centre", np.round(np.asarray(center2, dtype=float), 1))
    print("m2 swept rotation:\n", np.round(np.asarray(rotm2, dtype=float), 3))
    faces2 = _optical_solid_faces_at_pose(rows[m2], np.asarray(center2, dtype=float),
                                          np.asarray(rotm2, dtype=float), assigned_only=True)
    f2 = select_optical_solid_interaction_face(faces2)
    print("m2 interaction n_local(record):", "(from file)",
          " n_world:", np.round(np.asarray(f2.get("normal_world"), dtype=float), 3),
          " centroid:", np.round(np.asarray(f2.get("centroid_world"), dtype=float), 1))
    frame2 = _reflected_frame_from_interaction_face(faces2, c1, rot1, float(rows[m2].thickness))
    if frame2 is None:
        print("m2 reflected frame: None")
    else:
        c2, rot2 = frame2
        print("after m2: leg dir", np.round(rot2[:, 2], 3), " frame origin", np.round(c2, 1))
    editor.destroy()


if __name__ == "__main__":
    main()
