"""Guard for bugs/0635 — the Open 3D left panel groups its solvers under category headers.

User: "categorize the calculators/solvers on the left panel under big titles like Given
xxx, Solve for yyy." The panel's build() now emits three category headers, each above its
sections, in order: Set up → Solve the current system → Size a new system.

Check (source contract): the three category titles are present, the section titles are
present, and the categories appear in the intended order above their sections.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0635_panel_categories
"""

from __future__ import annotations

import inspect


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel

    src = inspect.getsource(Open3DLiveControlsPanel.build)

    categories = ["Set up", "Solve the current system", "Size a new system"]
    sections = [
        "Field",
        "Trace / Display",
        "Object / Image / FOV (Quick Estimation)",
        "Variable thickness",
        "Camera + lens (System Selection)",
    ]
    missing_cat = [c for c in categories if f'"{c}"' not in src]
    missing_sec = [s for s in sections if f'"{s}"' not in src]
    if missing_cat:
        ok = False
        notes.append(f"FAIL: bugs/0635: missing category header(s): {missing_cat}")
    elif missing_sec:
        ok = False
        notes.append(f"FAIL: bugs/0635: missing section(s) under the categories: {missing_sec}")
    else:
        # Order: each category appears, and 'Solve the current system' precedes the FOV
        # section, 'Size a new system' precedes the System Selection section.
        positions = {name: src.index(f'"{name}"') for name in categories + sections}
        ordered = (
            positions["Set up"] < positions["Field"]
            < positions["Solve the current system"]
            < positions["Object / Image / FOV (Quick Estimation)"]
            < positions["Size a new system"]
            < positions["Camera + lens (System Selection)"]
        )
        if not ordered:
            ok = False
            notes.append("FAIL: bugs/0635: categories/sections are out of the intended order")
        else:
            notes.append("PASS: three category headers group the sections in order")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Panel-categories validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
