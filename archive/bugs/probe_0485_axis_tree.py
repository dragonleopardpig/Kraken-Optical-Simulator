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
    """bugs/0485 stage 1: ask the ONE authoritative classifier."""
    from KrakenOS.UI.nonseq_output_ports import axis_fold_emissions

    out = {}
    try:
        for row_index, spec in (axis_fold_emissions(app.rows) or {}).items():
            out[int(row_index)] = {
                "origin": np.asarray(spec["origin"], dtype=float),
                "direction": np.asarray(spec["direction"], dtype=float),
                "kind": "reflect",
                "source": f"{spec['kind']}/{spec['source']}",
            }
    except Exception as exc:
        import traceback

        print(f"    (axis_fold_emissions failed: {type(exc).__name__}: {exc})")
        traceback.print_exc()
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
