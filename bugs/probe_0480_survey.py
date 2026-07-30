"""bugs/0480 survey -- on WHICH multi-arm scenes is no arm pinned to the designed Image?

That is the state in which `seat_camera_on_sensor`'s fallback ("take the first is_detector
target") actually decides where the camera body goes. Leaves are enumerated
``sorted(leaves)`` (branch-path alphabetical), so "first" means the alphabetically first
branch path -- ``reflect`` before ``transmit``.

Prints, per scene: detector count, how many arms are pinned (focus_source ==
"reached_image"), how many arms' OWN rays reach the designed Image, the arm the fallback
would choose, and the arm that actually images.

Run:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0480_survey.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

BUILT_INS = [
    "Beam Splitter Two Path Doublets",
    "Beam Splitter 50/50 Example",
    "Beam Splitter: MV 150 mm 1X (transmit) + MV 120 mm (reflect)",
    "Zemax LED Beam-Splitter Imaging",
    "Right-Angle Beam-Splitter Illumination",
    "Michelson Interferometer (Interferogram)",
]
ATTACHMENTS = [
    Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py"),
    Path("attachment/Michelson.py"),
]


def _image_point(app):
    stations = app._row_z_positions()
    index = app._image_plane_row_index()
    if index is None:
        return None
    row = app.rows[int(index)]
    point = np.asarray(
        [float(row.desp_x), float(row.desp_y), float(stations[int(index)]) + float(row.desp_z)],
        dtype=float,
    )
    fold = app._optical_axis_fold_world_transform_for_row(int(index))
    if fold is not None:
        point = (np.asarray(fold, dtype=float) @ np.append(point, 1.0))[:3]
    return point


def survey(app, tag: str) -> None:
    try:
        image_point = _image_point(app)
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
    except Exception as exc:
        print(f"{tag:46s} BUILD FAILED: {type(exc).__name__}: {exc}")
        return
    dets = [t for t in (getattr(bundle, "targets", None) or []) if bool(getattr(t, "is_detector", False))]
    metas = [getattr(t, "metadata", None) or {} for t in dets]
    pinned = [i for i, m in enumerate(metas) if str(m.get("focus_source", "")) == "reached_image"]
    reaching = [i for i, m in enumerate(metas) if bool(m.get("reaches_designed_image", False))]
    branch = [i for i, m in enumerate(metas) if str(m.get("target_source", "")) == "branch_detector"]
    flag = ""
    if len(dets) > 1 and not pinned:
        # the fallback decides; is its pick the arm that images?
        first_is_imaging = bool(reaching) and reaching[0] == 0
        flag = "  <== FALLBACK DECIDES" + ("" if first_is_imaging else "  *** WRONG ARM ***")
    print(
        f"{tag:46s} dets={len(dets)} branch={len(branch)} pinned={pinned} reaches={reaching}{flag}"
    )
    for i, t in enumerate(dets):
        centre = np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
        d = float(np.linalg.norm(centre - image_point)) if image_point is not None else float("nan")
        print(
            f"      [{i}] {str(metas[i].get('branch_path', '-'))[:44]:46s} "
            f"fs={str(metas[i].get('focus_source', '-')):16s} reaches={str(metas[i].get('reaches_designed_image', '-')):5s} "
            f"centre={np.round(centre, 2).tolist()} d(image)={d:.2f}"
        )


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    for name in BUILT_INS:
        app = None
        try:
            app = KrakenLayoutEditor()
            app.load_layout_by_name(name)
            survey(app, name)
        except Exception as exc:
            print(f"{name:46s} LOAD FAILED: {type(exc).__name__}: {exc}")
        finally:
            if app is not None:
                try:
                    app.destroy()
                except Exception:
                    pass

    for path in ATTACHMENTS:
        if not path.exists():
            print(f"{path.name:46s} SKIP (absent)")
            continue
        app = None
        try:
            app = KrakenLayoutEditor()
            app.layout_files["probe"] = path
            app.load_layout_by_name("probe")
            survey(app, path.name)
        except Exception as exc:
            print(f"{path.name:46s} LOAD FAILED: {type(exc).__name__}: {exc}")
        finally:
            if app is not None:
                try:
                    app.destroy()
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
