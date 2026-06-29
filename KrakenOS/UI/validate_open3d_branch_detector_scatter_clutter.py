"""Display-free regression guard for bugs/0182.

The folded MV-150 coaxial area-LED scene is a diffuse double-pass: the object
scatter forks one leaf branch per scattered ray (``S3/scatter01..N``). Each leaf
used to earn its own synthesized branch detector, so the 2-D 'full 3-D'
projection drew dozens of crisscrossing orange footprint/plane rectangles (one
``detector_active_footprint`` quad + ``detector_active_center`` crosshairs +
``image`` plane outline per detector).

``derive_branch_detectors`` now drops any leaf that has passed through a diffuse
scatter (a non-deterministic branch with no single focus). A scatter-free split
(a genuine beam splitter) keeps every arm, so clean beam-splitter scenes are
untouched.

Two checks:

* Unit -- ``derive_branch_detectors`` directly: a 3-way scatter fork yields NO
  scatter detector (at most the clean straight-through leak); a clean 2-arm beam
  splitter still yields both arm detectors.
* Real scene -- the folded coaxial-LED bundle: 0 branch detectors carry a scatter
  branch path, and the total branch-detector count collapses from dozens to <=2.

Run headless: ``python -m KrakenOS.UI.validate_open3d_branch_detector_scatter_clutter``
"""
from __future__ import annotations

import os

import numpy as np

from KrakenOS.UI.scene_geometry import RayPath3D
from KrakenOS.UI.services.branch_detectors import (
    _branch_path_has_scatter,
    derive_branch_detectors,
)

os.environ.setdefault("KRAKENOS_HEADLESS", "1")


def _ray(branch_path: str, origin, direction, *, ray_index: int) -> RayPath3D:
    o = np.asarray(origin, dtype=float)
    d = np.asarray(direction, dtype=float)
    pts = np.vstack((o, o + 0.0 * d, o + 40.0 * d))  # >=2 distinct points -> a real exit segment
    return RayPath3D(
        ray_index=int(ray_index),
        points_world=np.asarray((o, o + 40.0 * d), dtype=float),
        branch_path=branch_path,
        branch_label=branch_path,
    )


# --- Part 1: unit -- derive_branch_detectors ----------------------------------

def _scatter_fork_paths() -> list[RayPath3D]:
    """A diffuse fork: the reflect arm hits the object then scatters three ways,
    plus a clean straight-through transmit leak. Each scatter leaf points off in
    its own random direction -- none earns a detector."""
    paths: list[RayPath3D] = []
    # intermediate reflect arm (a proper prefix of the scatter leaves -> not a leaf)
    paths.append(_ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, -1.0, 0.0], ray_index=0))
    # three scatter leaves, each a distinct random direction
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter01", [0.0, -30.0, 0.0], [0.3, 1.0, 0.2], ray_index=1))
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter02", [0.0, -30.0, 0.0], [-0.4, 1.0, -0.1], ray_index=2))
    paths.append(_ray("S1:S1/reflect -> S3:S3/scatter03", [0.0, -30.0, 0.0], [0.1, 1.0, 0.5], ray_index=3))
    # clean straight-through leak (deterministic, no scatter -> keeps a detector)
    paths.append(_ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=4))
    paths.append(_ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=5))
    return paths


def _clean_beam_splitter_paths() -> list[RayPath3D]:
    """A genuine beam splitter: reflect (+Y) and transmit (+Z) arms, no scatter."""
    paths: list[RayPath3D] = []
    paths.append(_ray("S1:S1/reflect", [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], ray_index=0))
    paths.append(_ray("S1:S1/reflect", [0.0, 2.0, 0.0], [0.0, 1.0, 0.0], ray_index=1))
    paths.append(_ray("S1:S1/transmit", [0.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=2))
    paths.append(_ray("S1:S1/transmit", [2.0, 0.0, 0.0], [0.0, 0.0, 1.0], ray_index=3))
    return paths


def _check_unit(notes: list[str]) -> bool:
    ok = True

    fork = derive_branch_detectors(_scatter_fork_paths(), existing_targets=[], scene_radius=50.0)
    scatter_dets = [d for d in fork if _branch_path_has_scatter(d.branch_path)]
    if scatter_dets:
        bps = [d.branch_path for d in scatter_dets]
        notes.append(f"scatter branches still earned {len(scatter_dets)} detectors: {bps}")
        ok = False
    else:
        notes.append("scatter fork: 0 scatter detectors (random branches suppressed)")
    if len(fork) > 1:
        notes.append(f"scatter fork left {len(fork)} detectors (expected <=1: the clean leak)")
        ok = False
    else:
        notes.append(f"scatter fork: {len(fork)} surviving detector(s) (clean leak only)")

    clean = derive_branch_detectors(_clean_beam_splitter_paths(), existing_targets=[], scene_radius=50.0)
    if len(clean) != 2:
        notes.append(f"clean beam splitter expected 2 arm detectors, got {len(clean)}")
        ok = False
    else:
        notes.append("clean beam splitter keeps both arm detectors (filter is a no-op without scatter)")
    return ok


# --- Part 2: real folded coaxial-LED scene ------------------------------------

def _check_real_scene(notes: list[str]) -> bool:
    try:
        from KrakenOS.UI.validate_open3d_optical_axis_scatter_clutter import _build_folded_bundle
    except Exception as exc:  # pragma: no cover
        notes.append(f"could not import folded-scene harness: {exc!r}")
        return False
    try:
        bundle = _build_folded_bundle(15)
    except Exception as exc:  # pragma: no cover
        notes.append(f"real folded-scene build raised: {exc!r}")
        return False

    branch_targets = []
    for target in list(getattr(bundle, "targets", []) or []):
        meta = getattr(target, "metadata", {}) or {}
        if str(meta.get("target_source", "") or "") == "branch_detector":
            branch_targets.append(target)
    scatter_targets = [
        t for t in branch_targets
        if _branch_path_has_scatter(str((getattr(t, "metadata", {}) or {}).get("branch_path", "")))
    ]
    notes.append(
        f"real folded scene: {len(branch_targets)} branch detectors, "
        f"{len(scatter_targets)} on scatter branches"
    )
    ok = True
    if scatter_targets:
        notes.append("scatter-branch detectors survived -> 2-D clutter not suppressed")
        ok = False
    if len(branch_targets) > 2:
        notes.append(f"too many branch detectors ({len(branch_targets)}) -> clutter remains")
        ok = False
    return ok


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    ok = _check_unit(notes) and ok
    ok = _check_real_scene(notes) and ok
    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(("  ok  " if ok else "  --  ") + note)
    label = "diffuse double-pass draws no per-scatter branch-detector clutter (2-D full-3D)"
    print(("[PASS] " if ok else "[FAIL] ") + label + " (bugs/0182)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
