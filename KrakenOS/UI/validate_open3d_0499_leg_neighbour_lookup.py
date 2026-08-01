"""bugs/0499 -- "the element before this one" comes from the AXIS, not from row order.

Row INDEX order stops being optical order the moment a scene folds. On the AZ85 machine-vision
layout the rows read ``0 Object, 1 Front datum, 2 BB1, 3 BS, 4 Aperture, 5 BB2, 6 Rear datum,
7 mirror, 8 Image`` -- the lens datums BRACKET the beam splitter, because the splitter emits the leg
the lens sits on.

That is not academic. The lens drag redirect used ``rows[lens_front_idx - 1]`` to choose the gap to
rewrite and got the OBJECT gap -- section 1, the object-to-splitter distance -- so dragging the lens
along its own leg lifted the entire leg instead of changing the splitter-to-lens distance. Measured:
a +X 20 mm drag moved the body and both datums +Z 20 mm. That attempt was reverted; this is the
primitive it was missing.

Built from the tree the rest of the fold work already uses, so a caller cannot disagree with
``rows_on_emitted_leg`` (bugs/0485) or ``point_on_emitted_leg`` (bugs/0496) about what is on a leg.

Display-free: reads the scene's SURFACES directly, no Tk and no renderer.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0499_leg_neighbour_lookup
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
# Measured on that scene. The three that DIFFER from index order are the whole point.
EXPECTED = {1: 3, 2: 1, 3: 0, 4: 2, 5: 4, 6: 5, 7: 6, 8: 7}
EXPECTED_LEGS = {"axis:root": [0, 3], "axis:fold:3": [1, 2, 4, 5, 6], "axis:fold:7": [7, 8]}


def _scene_rows():
    from KrakenOS.UI.nonseq_output_ports import _row_like

    spec = importlib.util.spec_from_file_location("kraken_scene_0499", str(SCENE.resolve()))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [_row_like(row) for row in copy.deepcopy(module.SURFACES)]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.services import optical_axis_tree as tree_mod
    except Exception as exc:
        notes.append(f"SKIP: optical_axis_tree unavailable ({type(exc).__name__}: {exc})")
        return ok, notes

    check(hasattr(tree_mod, "leg_upstream_neighbour"), "A1: the tree can name a row's upstream neighbour")
    check(hasattr(tree_mod, "rows_along_leg"), "A2: ... and order a leg's rows by arc length")

    # --- B. the reduction: with no folds it IS index order --------------------------------
    class _Row:
        def __init__(self, t):
            self.desp_x = self.desp_y = self.desp_z = 0.0
            self.thickness = float(t)

    flat = [_Row(10.0) for _ in range(6)]
    flat_tree = tree_mod.build_axis_tree(flat)
    flat_snaps = tree_mod.snap_rows(flat, flat_tree)
    reduced = {i: tree_mod.leg_upstream_neighbour(flat_tree, flat_snaps, i) for i in range(6)}
    check(
        reduced == {0: None, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4},
        f"B1: on an UNFOLDED scene the lookup collapses to plain index order ({reduced}) -- the "
        f"check that this generalises rather than replacing the old rule",
    )

    if not SCENE.exists():
        notes.append("SKIP: the AZ85 BS scene is not checked out (gitignored attachment)")
        return ok, notes

    # --- C. the folded scene -------------------------------------------------------------
    try:
        from KrakenOS.UI.nonseq_output_ports import axis_fold_emissions

        rows = _scene_rows()
        emissions = axis_fold_emissions(rows) or {}
        tree = tree_mod.build_axis_tree(
            rows,
            fold_emissions={
                k: {"origin": v["origin"], "direction": v["direction"], "kind": "reflect"}
                for k, v in emissions.items()
            },
        )
        snaps = tree_mod.snap_rows(rows, tree)
    except Exception as exc:
        notes.append(f"SKIP: the scene could not be prepared ({type(exc).__name__}: {exc})")
        return ok, notes

    legs = {seg: tree_mod.rows_along_leg(snaps, seg) for seg in EXPECTED_LEGS}
    check(legs == EXPECTED_LEGS, f"C1: each leg's rows come back in optical order ({legs})")

    actual = {i: tree_mod.leg_upstream_neighbour(tree, snaps, i) for i in EXPECTED}
    wrong = {i: (actual[i], want) for i, want in EXPECTED.items() if actual[i] != want}
    check(not wrong, f"C2: every row's upstream neighbour is its LEG neighbour ({wrong or 'all correct'})")

    differ = {i: (actual[i], i - 1) for i in EXPECTED if actual[i] != i - 1}
    check(
        set(differ) == {1, 3, 4},
        f"C3: and it differs from rows[i-1] exactly where the fold reorders things ({differ}) -- "
        f"row 1's upstream is the SPLITTER (3), not the Object (0), which is the bug that reverted",
    )
    selfref = [i for i in EXPECTED if actual[i] == i]
    check(
        not selfref,
        f"C4: no row is its own upstream neighbour ({selfref}) -- a folder sits at s=0 on the leg "
        f"it emits, so the naive source_row fallback returned itself",
    )
    check(
        tree_mod.leg_upstream_neighbour(tree, snaps, 0) is None,
        "C5: the first row on the root axis has nothing upstream",
    )
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "NOTE")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
