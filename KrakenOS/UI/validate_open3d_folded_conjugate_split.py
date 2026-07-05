"""Display-free guard for the folded object-distance split core (feature: split the object /
image distance at the fold mirror; user pins one mechanical leg and the mirror slides).

In a folded relay the object working distance c is bent by an RA mirror: c = a + b (object plane
-> mirror centre -> first optical surface, along the optical axis). The optics fix c (the
conjugate); the split is the mechanical freedom. `_folded_object_conjugate_split` reports the
legs; `_apply_folded_object_split` pins one leg and SLIDES the mirror (object gap +delta against
the trailing air spacer -delta) so c -- and therefore the first-order image -- is untouched.

  (A) SPLIT: on the folded AZ85 the object split reports near (object -> mirror centre) + far
      (mirror centre -> first surface) == total, and ``near`` equals the mirror centre's along-axis
      position (the +Z world position of the RA-mirror fold vertex).
  (B) SLIDE keeps the conjugate: pinning ``near`` to a new value slides the mirror there and the
      total object distance is unchanged (a pure mechanical repackaging).
  (C) RANGE: a constraint that would need a negative gap is rejected, not applied.
  (D) TRACE: after a valid slide the scene still images -- rays reach the detector.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_conjugate_split
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def validate_folded_conjugate_split() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)

    split = _quiet(editor._folded_object_conjugate_split)
    total0, _ = _quiet(editor._paraxial_total_object_gap)
    mirror_center = (
        _quiet(editor._ra_mirror_fold_vertex_world, split["mirror_row"]) if split else None
    )

    # ---- (A) split adds up + near == mirror centre along-axis -------------------------------- #
    near_matches_vertex = (
        split is not None
        and mirror_center is not None
        and abs(float(split["near"]) - float(np.asarray(mirror_center, dtype=float).reshape(3)[2])) < 0.5
    )
    checks.append(Check(
        "SPLIT: near + far == total, and near = the RA-mirror centre's along-axis position",
        split is not None
        and abs((split["near"] + split["far"]) - split["total"]) < 1e-6
        and near_matches_vertex,
        f"split={None if split is None else {k: round(v, 2) if isinstance(v, float) else v for k, v in split.items()}} "
        f"mirror_center_z={None if mirror_center is None else round(float(mirror_center[2]), 2)}",
    ))

    # ---- (B) slide keeps the conjugate ------------------------------------------------------ #
    target_near = float(split["near"]) - 15.0 if split else 0.0
    ok, _msg = _quiet(editor._apply_folded_object_split, "near", target_near)
    total1, _ = _quiet(editor._paraxial_total_object_gap)
    split1 = _quiet(editor._folded_object_conjugate_split)
    checks.append(Check(
        "SLIDE: pinning the near leg slides the mirror there while the total conjugate is unchanged",
        bool(ok)
        and split1 is not None
        and abs(split1["near"] - target_near) < 1e-4
        and abs(total1 - total0) < 1e-4,
        f"applied={ok} new_near={None if split1 is None else round(split1['near'], 2)} "
        f"(target {round(target_near, 2)}) total {round(total0, 2)}->{round(total1, 2)}",
    ))

    # ---- (C) out-of-range rejected ---------------------------------------------------------- #
    ok_bad, msg_bad = _quiet(editor._apply_folded_object_split, "near", 1.0e6)
    checks.append(Check(
        "RANGE: a constraint that needs a negative gap is rejected, not applied",
        not ok_bad,
        f"rejected={not ok_bad} msg={msg_bad[:70]!r}",
    ))

    # ---- (D) still images after a valid slide ----------------------------------------------- #
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = next(
        (np.asarray(t.center_world, dtype=float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)),
        None,
    )
    ends = np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths]) if bundle.ray_paths else np.zeros((0, 3))
    reach = int((np.linalg.norm(ends - det, axis=1) < 5.0).sum()) if det is not None and len(ends) else 0
    checks.append(Check(
        "TRACE: after the slide the scene still images (rays reach the detector)",
        det is not None and reach >= 8,
        f"rays={len(bundle.ray_paths)} detector={None if det is None else np.round(det, 1)} within5mm={reach}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_conjugate_split()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_conjugate_split()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-conjugate-split validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
