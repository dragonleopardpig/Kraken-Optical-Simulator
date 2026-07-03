"""bugs/0212 (Fix A) -- a free-placed SECOND promoted RA mirror must stay pinned
where the user dropped it, instead of being dragged onto mirror 1's fold leg and
"misplaced by itself" (flag_20260703_082955_542 / the 090116+090206 before/after
pair, recording_20260703_090237.json).

Root cause (bugs/0211): mirror 2 is inserted as a plain downstream row, so the
fold-follower pose-override builder
(``build_optical_solid_output_port_pose_overrides`` in ``nonseq_output_ports``)
recomputes its world pose from mirror 1's fold frame + cumulative station and
sweeps it down the +X leg to X~=269 (on the image), overriding the placed
``center_world`` [210.7, 0, 71.9] at draw time.

Fix A (minimal, inert-2nd-mirror): a promoted optical solid that carries a solid
mesh but has NO assigned port faces is not a fold participant -- it is pinned
where placed. The follower loop now ``break``s on such a solid (terminating the
chain exactly as the pre-existing no-face optical-solid branch already did),
WITHOUT first writing the spurious override. A working fold mirror or a penta
prism carries assigned faces, so the guard is inert for them (penta stays green).

Display-free: exercises the pure override builder on the AZ85 folded scene, so it
needs no VTK/display. It does NOT assert the final rendered world pose (that is the
sequential-placement + desp reconstruction, which needs the in-app draw and is
owed an eyeball) -- it proves the mechanism: the spurious override is gone and the
upstream fold chain is untouched, keyed causally on the no-face condition.

Run:  python -m KrakenOS.UI.validate_open3d_second_mirror_pinned_to_placed_pose
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI import nonseq_output_ports as nop
from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACES_ADVANCED_ATTR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PORTS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "nonseq_output_ports.py"

# The placed world centre the user dropped the 2nd mirror at (bugs/0211 evidence).
_PLACED_X = 210.7


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _make_second_mirror(mirror1, *, strip_faces: bool):
    """A 2nd RA mirror built from mirror 1, re-posed to the placed +X leg. With
    ``strip_faces`` it mimics a fresh promote (no ports); otherwise it keeps
    mirror 1's assigned faces (a fold participant, for the causal contrast)."""
    m2 = copy.deepcopy(mirror1)
    advanced = dict(getattr(m2, "advanced", {}) or {})
    if strip_faces:
        advanced.pop(OPTICAL_SOLID_FACES_ADVANCED_ATTR, None)
    m2.advanced = advanced
    m2.desp_x = _PLACED_X
    m2.desp_y = 0.0
    return m2


def _center_x(entry) -> float:
    return float(np.asarray(entry.get("center"), dtype=float).reshape(3)[0])


def validate_second_mirror_pinned_to_placed_pose() -> list[Check]:
    checks: list[Check] = []
    editor = _build_editor(_AZ85)
    rows = list(editor.rows)
    img_idx = len(rows) - 1  # Image / Sensor is the last row
    mirror1 = rows[1]

    # 1) The fold SOURCE (mirror 1) is an optical solid WITH assigned faces, so
    #    the pin guard never touches it -- it drives the fold normally.
    src_solid = nop._row_has_optical_solid(nop._row_like(mirror1))
    src_faced = nop._optical_solid_has_assigned_faces(nop._row_like(mirror1))
    checks.append(
        Check(
            "AZ85 mirror 1 is an optical solid WITH assigned faces (fold source, never pinned)",
            src_solid is True and src_faced is True,
            f"has_optical_solid={src_solid}, has_assigned_faces={src_faced} (expect both True)",
        )
    )

    # 2) FIX INERT / single fold intact: with only mirror 1, the builder still
    #    folds the whole downstream chain onto the +X leg, incl. the Image at the
    #    folded focus (X~=275). The fix must not disturb the working single fold.
    base = nop.build_optical_solid_output_port_pose_overrides(rows)
    base_keys = sorted(base)
    img_folded = img_idx in base and _center_x(base[img_idx]) > 200.0
    checks.append(
        Check(
            "base AZ85 single fold intact: downstream chain incl. Image folded onto +X leg",
            base_keys == [2, 3, 4, 5, 6, 7, 8] and img_folded,
            f"override_keys={base_keys}, image_center_x="
            f"{_center_x(base[img_idx]) if img_idx in base else None}",
        )
    )

    # 3) DISCRIMINATOR: a fresh free-placed 2nd mirror (faces stripped) is an
    #    optical solid with NO assigned faces -- exactly what the guard keys on.
    m2 = _make_second_mirror(mirror1, strip_faces=True)
    m2_solid = nop._row_has_optical_solid(nop._row_like(m2))
    m2_faced = nop._optical_solid_has_assigned_faces(nop._row_like(m2))
    checks.append(
        Check(
            "a free-placed 2nd mirror (fresh promote) is an optical solid with NO assigned faces",
            m2_solid is True and m2_faced is False,
            f"has_optical_solid={m2_solid}, has_assigned_faces={m2_faced} (expect True, False)",
        )
    )

    # 4) THE FIX: insert that no-face mirror before the Image. Its row index gets
    #    NO override (pinned to its placed pose), and the upstream fold chain
    #    (rows 2..insert-1) is byte-identical to the base -- untouched.
    rows_no_face = list(rows[:img_idx]) + [m2] + list(rows[img_idx:])
    ov_no_face = nop.build_optical_solid_output_port_pose_overrides(rows_no_face)
    pinned = img_idx not in ov_no_face
    upstream_intact = all(
        idx in ov_no_face
        and np.allclose(
            np.asarray(ov_no_face[idx].get("center"), dtype=float),
            np.asarray(base[idx].get("center"), dtype=float),
        )
        for idx in range(2, img_idx)
    )
    checks.append(
        Check(
            "THE FIX: the no-face 2nd mirror gets NO override (pinned) and the upstream chain is unchanged",
            pinned and upstream_intact,
            f"mirror2_index={img_idx} in_overrides={not pinned} (expect False); "
            f"upstream_intact={upstream_intact}; keys={sorted(ov_no_face)}",
        )
    )

    # 5) CAUSAL / NON-VACUOUS: the SAME mirror with its faces KEPT is a fold
    #    participant -- its index DOES get an override. The only difference is the
    #    face assignment, so the no-face condition is exactly what pins it (pre-fix
    #    the pinned mirror would have been overridden the same way).
    m2_faced_row = _make_second_mirror(mirror1, strip_faces=False)
    rows_faced = list(rows[:img_idx]) + [m2_faced_row] + list(rows[img_idx:])
    ov_faced = nop.build_optical_solid_output_port_pose_overrides(rows_faced)
    faced_overridden = img_idx in ov_faced
    checks.append(
        Check(
            "CAUSAL: the identical mirror WITH faces is overridden (fold participant) -- proves the guard is the pin",
            faced_overridden is True,
            f"faced_mirror2_index={img_idx} in_overrides={faced_overridden} (expect True); keys={sorted(ov_faced)}",
        )
    )

    # 6) PLACED POSE PRESERVED: the pinned mirror keeps its authored placement
    #    (desp_x = the dropped +X centre) and receives no override, so the
    #    recorded center_world governs the draw -- the "pin where placed" contract.
    keeps_desp = abs(float(getattr(m2, "desp_x", 0.0)) - _PLACED_X) < 1e-6
    checks.append(
        Check(
            "the pinned mirror keeps its placed desp and takes no override (recorded pose governs the draw)",
            keeps_desp and pinned,
            f"desp_x={getattr(m2, 'desp_x', None)} (expect {_PLACED_X}), pinned={pinned}",
        )
    )

    # 7) The guard is actually wired into the follower loop (not vestigial).
    try:
        ports_src = _PORTS_SRC.read_text(encoding="utf-8")
    except Exception:
        ports_src = ""
    guard_wired = "not _optical_solid_has_assigned_faces(follower)" in ports_src
    checks.append(
        Check(
            "the follower loop actually gates on the no-assigned-faces condition (guard not vestigial)",
            guard_wired,
            f"guard present in nonseq_output_ports.py={guard_wired}",
        )
    )

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_second_mirror_pinned_to_placed_pose()
    failures = [f"{check.check} | {check.detail}" for check in checks if not check.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_second_mirror_pinned_to_placed_pose()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    print("Second mirror pinned-to-placed-pose validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
