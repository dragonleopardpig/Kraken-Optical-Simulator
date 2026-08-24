"""Guard for bugs/0641 — the BS reflect axis has a visible minimum length.

flag_20260824_141739 ("No 2nd optical axis created", after bugs/0640 made the coating
recognised): the reflect guide length was `reach = max((bounds corners - fold) . reflect_dir)`,
which clamps to the scene's extent in the reflect direction. On a coaxial BS nothing is
placed on the reflect arm, so it collapsed to a ~78 mm stub next to the ~1650 mm main axis --
invisible at zoom-to-fit. The guide now takes a MINIMUM length tied to the scene's largest
bounds dimension.

Check (source contract): `_bs_reflect_axis_guide_records` computes a minimum reach from the
bounds span and applies `reach = max(reach, min_reach)` before building the far endpoint.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0641_reflect_axis_visible_length
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    src = inspect.getsource(Kraken3DInspector._bs_reflect_axis_guide_records)
    has_min = "min_reach" in src and "reach = max(reach, min_reach)" in src
    ties_to_bounds = "bounds_span" in src or "bounds_arr[1::2]" in src
    if not has_min:
        ok = False
        notes.append(
            "FAIL: bugs/0641: the reflect guide has no minimum length -- it clamps to the scene "
            "extent and a coaxial BS reflect axis stays a tiny stub"
        )
    elif not ties_to_bounds:
        ok = False
        notes.append("FAIL: bugs/0641: the minimum length is not tied to the scene bounds span")
    else:
        notes.append("PASS: the reflect guide takes a scene-sized minimum length (visible second axis)")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Reflect-axis-visible-length validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
