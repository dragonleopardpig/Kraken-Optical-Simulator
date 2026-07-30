"""bugs/0485 stage 0 -- derive the optical-axis segment tree and falsify it against stored poses.

Feeds ``optical_axis_tree`` the fold geometry the editor ALREADY computes (the object/image
conjugate splits, the promoted-solid pose overrides) and reports, per scene:

  * the segments, their origins/directions, and where each starts on its parent;
  * every row's (segment, arc-length, transverse offset);
  * the structural violations -- TRANSVERSE / CONTINUITY / MONOTONIC.

A row that is meant to be on the beam but reports a transverse offset is the "not centered to
optical axis" report as a number. A fold segment whose origin is not its folder's pose is the
"fold axis slanted / does not follow" report as a number.

Run:
    xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0485_axis_tree.py
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.services import optical_axis_tree as tree_mod

SCENES = [
    ("AZ85 RA mirror + BS", Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py"), None),
    ("AZ85 RA mirror (no BS)", Path("attachment/machine_vision_AZ85_RA_Mirror.py"), None),
    ("Two Path Doublets", None, "Beam Splitter Two Path Doublets"),
    ("five penta cascade", Path("attachment/five_penta_prism_cascade.py"), None),
    ("plain doublet", Path("attachment/doublet.py"), None),
]


def fold_emissions(app) -> dict:
    """Every folder's (fold point, emitted direction), from the editor's own geometry."""
    out: dict[int, dict] = {}

    # Object-side fold: the BS coating. fold_point / entry_dir / leg_dir come straight from it.
    try:
        split = app._folded_object_conjugate_split()
        if isinstance(split, dict) and split.get("fold_point") is not None:
            out[int(split["mirror_row"])] = {
                "origin": np.asarray(split["fold_point"], dtype=float),
                "direction": np.asarray(split["leg_dir"], dtype=float),
                "kind": "reflect",
                "source": "object_split",
            }
    except Exception as exc:
        print(f"    (object split unavailable: {type(exc).__name__}: {exc})")

    # Image-side fold: the RA mirror. c_m is its centre, out_dir the emitted leg.
    try:
        split = app._folded_image_conjugate_split()
        if isinstance(split, dict):
            geo = app._frozen_image_fold_world_geometry(split)
            if isinstance(geo, dict) and geo.get("c_m") is not None:
                out[int(split["mirror_row"])] = {
                    "origin": np.asarray(geo["c_m"], dtype=float),
                    "direction": np.asarray(geo["out_dir"], dtype=float),
                    "kind": "reflect",
                    "source": "image_split",
                }
    except Exception as exc:
        print(f"    (image split unavailable: {type(exc).__name__}: {exc})")

    # Any remaining folding promoted solid, from the live override map.
    #
    # CORRECTION (stage 0 measurement): the override map's keys are the rows a fold REPOSITIONS,
    # not the rows that fold. Taking every key as a folder invented 8 segments on the single-fold
    # AZ85 scene (rows 2-9, all emitting +x). A row only EMITS a segment if it actually turns the
    # axis, so keep an override only when its direction is not parallel to the incoming one.
    try:
        from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

        incoming = np.asarray((0.0, 0.0, 1.0), dtype=float)
        for record in out.values():
            incoming = np.asarray(record["direction"], dtype=float)
        for row_index, pose in (optical_solid_output_port_pose_overrides(None, app.rows) or {}).items():
            if int(row_index) in out or not isinstance(pose, dict):
                continue
            rotation = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)
            emitted = rotation @ np.asarray((0.0, 0.0, 1.0), dtype=float)
            norm = float(np.linalg.norm(emitted))
            if norm <= 1e-12:
                continue
            emitted = emitted / norm
            if abs(abs(float(np.dot(emitted, incoming))) - 1.0) < 1e-6:
                continue  # repositioned BY a fold, not a folder itself
            out[int(row_index)] = {
                "origin": np.asarray(pose.get("center"), dtype=float).reshape(3),
                "direction": emitted,
                "kind": "reflect",
                "source": "pose_override",
            }
    except Exception as exc:
        print(f"    (pose overrides unavailable: {type(exc).__name__}: {exc})")
    return out


def report(app, tag: str) -> None:
    emissions = fold_emissions(app)
    print(f"\n--- {tag}: {len(emissions)} folder(s) {sorted(emissions)}")
    for row_index, spec in sorted(emissions.items()):
        print(
            f"      folder row {row_index} from {spec['source']:14s} "
            f"origin={np.round(spec['origin'], 3).tolist()} dir={np.round(spec['direction'], 4).tolist()}"
        )
    tree = tree_mod.build_axis_tree(app.rows, fold_emissions=emissions)
    snaps = tree_mod.snap_rows(app.rows, tree)
    print(tree_mod.describe(app.rows, tree, snaps))
    # every stored pose must equal the derived one (this is the tree's own consistency)
    worst = 0.0
    for snap in snaps:
        stored = tree_mod.row_world_pose(app.rows, snap.row_index)
        worst = max(worst, float(np.linalg.norm(tree_mod.world_pose_from_snap(tree, snap) - stored)))
    print(f"    derive-vs-stored worst |delta| = {worst:.3e} mm")
    problems = tree_mod.check_invariants(app.rows, tree, snaps)
    if problems:
        print(f"    !! {len(problems)} violation(s):")
        for p in problems:
            print(f"       {p}")
    else:
        print("    invariants: TRANSVERSE / CONTINUITY / MONOTONIC all hold")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    for label, path, builtin in SCENES:
        if path is not None and not path.exists():
            print(f"\n########## {label}: SKIP (absent)")
            continue
        app = None
        try:
            app = KrakenLayoutEditor()
            if builtin is not None:
                app.load_layout_by_name(builtin)
            else:
                app.layout_files["probe"] = path
                app.load_layout_by_name("probe")
            print(f"\n########## {label} ({len(app.rows)} rows)")
            report(app, "AS LOADED")
            # the flagged state: a 30x30 FOV solve
            if builtin is None and "AZ85" in label:
                qe = QuickEstimationService(SimpleNamespace(editor=app))
                ok, _msg = qe.fov_solve("object", "thickness", 30.0, 30.0, (23.04, 23.04))
                report(app, f"AFTER FOV 30x30 (applied={ok})")
        except Exception as exc:
            import traceback

            print(f"  FAILED: {type(exc).__name__}: {exc}")
            traceback.print_exc()
        finally:
            if app is not None:
                try:
                    app.destroy()
                except Exception:
                    pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
