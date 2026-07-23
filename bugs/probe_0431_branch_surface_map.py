"""Probe (BS Phase 2, trace-driven): dump the branched-trace surface map on AZ85 + BS.

Confirms the data trace-driven placement will consume: after a branched NsTrace, each entry in
NS_BRANCH_RESULTS carries SURFACE (rows the branch hit), XYZ (world points), R_LMN (directions).
So per-element leg membership = "which branch's SURFACE array contains this row index", and each
leg's world frame comes from that branch's XYZ/R_LMN at the surface.

Run:
    .devenv/state/venv/bin/python bugs/probe_0431_branch_surface_map.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _dump_branches(system, label):
    try:
        system.NsTrace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    except Exception as exc:
        print(f"  {label}: NsTrace raised {type(exc).__name__}: {exc}")
        return
    results = list(getattr(system, "NS_BRANCH_RESULTS", []) or [])
    print(f"\n=== {label}: {len(results)} branch(es) ===")
    for r in results:
        surf = np.asarray(r.get("SURFACE", ()), dtype=int).ravel()
        xyz = r.get("XYZ", None)
        uniq = []
        for s in surf:
            if not uniq or uniq[-1] != int(s):
                uniq.append(int(s))
        # exit direction of the branch (last R_LMN)
        rlmn = r.get("R_LMN", None)
        d = None
        try:
            if rlmn is not None and len(rlmn):
                d = np.asarray(rlmn[-1], dtype=float).reshape(3).round(3)
        except Exception:
            d = None
        print(f"  branch_id={r.get('branch_id')} path={str(r.get('branch_path',''))[:26]:26} "
              f"power={float(r.get('branch_power',0)):.3f} term={str(r.get('branch_termination_reason',''))[:14]}")
        print(f"      surfaces hit (in order): {uniq}")
        print(f"      exit dir: {d}")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        print("row roster:")
        for i, r in enumerate(app.rows):
            print(f"  {i:2} surf={getattr(r,'surface','?'):9} name={getattr(r,'name','?')[:38]}")

        sys0 = app.build_system(require_solids=True, force_rebuild=True)
        _dump_branches(sys0, "AZ85 base (2 RA mirrors, no BS)")

        print("\n--- add_beam_splitter_to_led('plate') ---")
        res = app.add_beam_splitter_to_led("plate")
        print("   ", None if res is None else {k: res[k] for k in ("kind", "row_index", "coating_face") if k in res})
        for i, r in enumerate(app.rows):
            print(f"  {i:2} surf={getattr(r,'surface','?'):9} name={getattr(r,'name','?')[:38]}")
        sys1 = app.build_system(require_solids=True, force_rebuild=True)
        _dump_branches(sys1, "AZ85 + BS plate")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
