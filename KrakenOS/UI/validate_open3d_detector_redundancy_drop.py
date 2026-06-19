#!/usr/bin/env python3
"""Display-free regression for bugs/0098 (detector redundancy): on a beam-splitter
split, each arm shows ONE clean branch detector -- the redundant sequential per-arm
detectors and the global Image are dropped.

`derive_branch_detectors` appends a branch detector per terminal leaf (at each arm's
focus), but the scene's own per-arm detector rows and the global Image still drew on
top -> the user's "2 square detectors on each arm" on beam_splitter_two_arm_doublets,
plus the mis-oriented sequential reflect detector. 0093 dropped only the sequential
**Image**; `drop_superseded_image_display` now drops EVERY sequential detector the
branch detectors supersede (all is_detector targets on real rows < 100000), keeping
the branch detectors (synthetic rows >= 100000). No-op without a branch detector.

Asserts:
  - with branch detectors: sequential per-arm detectors + Image dropped, non-detector
    rows + branch detectors kept (targets, curves, labels);
  - without branch detectors: nothing dropped (plain sequential/folded scenes).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_detector_redundancy_drop

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace


def _scene():
    target = lambda row_index, det: SimpleNamespace(row_index=row_index, is_detector=det)
    keyed = lambda row_index: SimpleNamespace(row_index=row_index)
    # 3 = a lens surface (not a detector); 6/10 = sequential per-arm detectors;
    # 11 = global Image; 100000/100001 = branch detectors.
    targets = [target(3, False), target(6, True), target(10, True), target(11, True),
               target(100000, True), target(100001, True)]
    curves = [keyed(i) for i in (3, 6, 10, 11, 100000, 100001)]
    labels = [keyed(i) for i in (6, 10, 11, 3)]
    return targets, curves, labels


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.scene_builder import drop_superseded_image_display

    failures: list[str] = []
    targets, curves, labels = _scene()

    kept_t, kept_c, kept_l = drop_superseded_image_display(
        targets, curves, labels, [], has_branch_detector=True
    )
    kept_target_rows = sorted(int(getattr(t, "row_index", -1)) for t in kept_t)
    if kept_target_rows != [3, 100000, 100001]:
        failures.append(
            f"FAIL: with branch detectors, kept target rows {kept_target_rows}, expected "
            f"[3, 100000, 100001] (drop sequential 6/10 + Image 11, keep lens + branch dets)"
        )
    kept_curve_rows = sorted(int(getattr(c, "row_index", -1)) for c in kept_c)
    if kept_curve_rows != [3, 100000, 100001]:
        failures.append(f"FAIL: with branch detectors, kept curve rows {kept_curve_rows}")
    if any(int(getattr(l, "row_index", -1)) in {6, 10, 11} for l in kept_l):
        failures.append("FAIL: a superseded detector's label survived")

    kept_t2, _c2, _l2 = drop_superseded_image_display(
        targets, curves, labels, [], has_branch_detector=False
    )
    if len(kept_t2) != len(targets):
        failures.append("FAIL: without a branch detector, nothing should be dropped")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0098 detector redundancy")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] one clean branch detector per arm; redundant sequential detectors + Image dropped (bugs/0098)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
