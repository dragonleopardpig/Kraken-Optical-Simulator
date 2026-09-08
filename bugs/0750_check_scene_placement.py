"""bugs/0750: check a scene's promoted rows against their AUTHORED placement.

Run this after ANY hand edit to a scene .py -- especially one that touches row thicknesses. It is
the guard for the bugs/0748 class of mistake: changing the SUM of the two lens sliding gaps slid the
whole arm-B block 8.54 mm while arm A stayed put, and nothing said so until the user flagged a
"haywire prism assembly" twice.

A 3D-window banner cannot catch this, because the actor editing a .py file is not looking at the
3D window. This is a script for exactly that actor.

  # what moved, absolutely (a stale authored snapshot reads red -- see --compare)
  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u \
      bugs/0750_check_scene_placement.py --check attachment/om05a_folded_80mm.py

  # THE ONE TO USE WHEN EDITING: did my edit move anything off its authored placement?
  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u \
      bugs/0750_check_scene_placement.py --compare attachment/om05a_folded_80mm.py.pre-edit.bak \
                                                   attachment/om05a_folded_80mm.py

--compare exits 1 when a row moved, so it can gate a commit.
"""
import sys
import contextlib
import io
from pathlib import Path


def _load(scene):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor._preview_trace_deferred_until_requested = True
    editor.layout_files["scene"] = Path(scene).resolve()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor.load_layout_by_name("scene")
    return editor


def _drifts(scene):
    from KrakenOS.UI.services.scene_placement_audit import pinned_placement_drifts

    editor = _load(scene)
    try:
        return pinned_placement_drifts(editor.rows)
    finally:
        editor.destroy()


def check(scene):
    from KrakenOS.UI.services.scene_placement_audit import format_drift_report

    records = _drifts(scene)
    print(f"{scene}: {len(records)} promoted row(s) carry an authored placement\n")
    print(format_drift_report(records))
    return 0


def compare(before_scene, after_scene):
    from KrakenOS.UI.services.scene_placement_audit import compare_drifts, format_moved_report

    before = _drifts(before_scene)
    after = _drifts(after_scene)
    moved = compare_drifts(before, after)
    print(f"before: {before_scene}\nafter : {after_scene}\n")
    print(format_moved_report(moved))
    if moved:
        print(
            "\nThe gap SUM is probably no longer invariant. Rows AFTER an edited gap inherit the\n"
            "change through their station -- see bugs/0749. The bugs/0719 FOV solve avoids this by\n"
            "moving a thickness PAIR (rows[front-1] += d, rows[rear] -= d) so the sum is unchanged."
        )
        return 1
    return 0


def main(argv):
    if len(argv) >= 3 and argv[1] == "--check":
        return check(argv[2])
    if len(argv) >= 4 and argv[1] == "--compare":
        return compare(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
