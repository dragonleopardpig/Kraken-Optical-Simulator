#!/usr/bin/env python3
"""Display-free regression for bugs/0097 (thickness part): no cross-arm thickness dim.

The surface table is one linear list, but a beam splitter forks into two arms (rows
tagged with ``advanced.Element.branch_selector`` = "transmit" / "reflect", e.g.
beam_splitter_two_arm_doublets). The thickness-dimension overlay measures the gap
between consecutive rows -- so the last transmit row -> first reflect row, and the
last reflect row -> global image, drew dimensions SPANNING from the transmitting path
to the reflecting path (the user's "one thickness overlay span from transmitting to
reflecting"). ``_is_cross_arm_gap`` detects those crossings so the loop skips them;
the per-branch exit->detector overlays measure each arm cleanly.

Asserts the transmit->reflect and reflect->image gaps are flagged cross-arm, while
within-arm and common->arm-start gaps are kept.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_cross_arm_skip

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.surface_table_model import SurfaceRow
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService as Svc

    failures: list[str] = []

    def row(name: str, branch: str) -> SurfaceRow:
        return SurfaceRow(surface="Standard", name=name, thickness=10.0, advanced={"Element": {"branch_selector": branch}})

    # beam_splitter_two_arm_doublets shape: 0-2 common, 3-6 transmit, 7-10 reflect, 11 image.
    rows = [
        row("Obj", ""), row("BS front", ""), row("BS rear", ""),
        row("Tx1", "transmit"), row("Tx2", "transmit"), row("Tx3", "transmit"), row("Tx det", "transmit"),
        row("Rx1", "reflect"), row("Rx2", "reflect"), row("Rx3", "reflect"), row("Rx det", "reflect"),
        row("Image", ""),
    ]

    cross = {i for i in range(len(rows) - 1) if Svc._is_cross_arm_gap(rows, i)}
    # The only cross-arm gaps are transmit->reflect (6->7) and reflect->image (10->11).
    if cross != {6, 10}:
        failures.append(f"FAIL: cross-arm gaps should be {{6, 10}}, got {sorted(cross)}")
    # Within-arm + common->arm-start gaps must be kept (a real axial spacing).
    for i in (0, 1, 2, 3, 4, 5, 7, 8, 9):
        if Svc._is_cross_arm_gap(rows, i):
            failures.append(f"FAIL: gap {i}->{i+1} is within an arm (or common->arm) and must NOT be skipped")
    # A plain single-arm layout (no branch_selector) skips nothing.
    plain = [row("O", ""), row("L", ""), row("I", "")]
    if any(Svc._is_cross_arm_gap(plain, i) for i in range(len(plain) - 1)):
        failures.append("FAIL: a layout with no branch arms must not skip any gap")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0097 cross-arm thickness dimension")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] thickness dims skip cross-arm gaps; within-arm + single-arm gaps kept (bugs/0097)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
