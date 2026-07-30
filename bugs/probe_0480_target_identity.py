"""bugs/0480 -- identify the NON-branch detector targets on the scenes where no arm is pinned.

The ladder's second rung wants "the scene's prescription Image detector". The codebase already
has that answer: ``branch_detectors._reached_image_target`` -- is_detector, surface == "Image",
not a branch detector, furthest z. This dumps enough of each target to confirm that rung picks
the sensor, and prints what that shared helper returns.

Run:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0480_target_identity.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENES = [
    ("Beam Splitter Two Path Doublets", None),
    ("Beam Splitter: MV 150 mm 1X (transmit) + MV 120 mm (reflect)", None),
    ("Michelson Interferometer (Interferogram)", None),
    ("Beam Splitter 50/50 Example", None),
    ("AZ85_RA_Mirror_BS", Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")),
]


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.branch_detectors import _reached_image_target

    for tag, path in SCENES:
        if path is not None and not path.exists():
            print(f"\n##### {tag}: SKIP (absent)")
            continue
        app = None
        try:
            app = KrakenLayoutEditor()
            if path is None:
                app.load_layout_by_name(tag)
            else:
                app.layout_files["probe"] = path
                app.load_layout_by_name("probe")
            print(f"\n##### {tag}")
            print("  rows:")
            for i, r in enumerate(app.rows):
                print(
                    f"    S{i} surface={str(getattr(r, 'surface', '')):10s} name={str(getattr(r, 'name', ''))[:38]:40s} "
                    f"thick={float(getattr(r, 'thickness', 0.0)):9.3f} desp=({float(r.desp_x):.2f},{float(r.desp_y):.2f},{float(r.desp_z):.2f})"
                )
            print(f"  _image_plane_row_index() = {app._image_plane_row_index()}")
            _s, _r, bundle = app._build_preview_system_rays_bundle(
                sampling_mode=None, update_state=False, trace_rays=True
            )
            dets = [t for t in (getattr(bundle, "targets", None) or []) if bool(getattr(t, "is_detector", False))]
            print(f"  detector targets ({len(dets)}):")
            for i, t in enumerate(dets):
                meta = getattr(t, "metadata", None) or {}
                centre = np.asarray(getattr(t, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
                print(
                    f"    [{i}] row={getattr(t, 'row_index', None)} surface={str(getattr(t, 'surface', None)):8s} "
                    f"role={str(getattr(t, 'role', None)):10s} src={str(meta.get('target_source')):16s} "
                    f"centre={np.round(centre, 2).tolist()} name={str(getattr(t, 'name', ''))[:34]!r}"
                )
            picked = _reached_image_target(dets)
            if picked is None:
                print("  _reached_image_target -> None")
            else:
                centre = np.asarray(getattr(picked, "center_world", (np.nan,) * 3), dtype=float).reshape(-1)[:3]
                print(
                    f"  _reached_image_target -> row={getattr(picked, 'row_index', None)} "
                    f"centre={np.round(centre, 3).tolist()} name={str(getattr(picked, 'name', ''))[:40]!r}"
                )
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}")
        finally:
            if app is not None:
                try:
                    app.destroy()
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
