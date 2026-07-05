"""Display-free guard for bugs/0230 -- a PERISCOPE (two adjacent promoted RA mirrors, e.g. the
Pyrite-85 scene) must not crash the folded trace with `non-sequential surface N: int has no
ray_trace or extract_surface method`.

Root cause: two adjacent 90-degree folds compose to a NET-IDENTITY rotation with a lateral
OFFSET (periscope). The general flat-plate straight-equivalent path
(`_folded_optical_solid_straight_equivalent_rows`, bugs/0208) was gated by `has_rotating_fold`,
which only recognised a non-identity ROTATION, so it read the periscope as unfolded and returned
None. The scene fell through to the single-fold sequential-Mirror surrogate, which cannot compose
the 2nd free-placed fold (it rotation-folds the running beam the wrong way) and left the 2nd
mirror as a promoted mesh solid -- fed into a build=0 (dummy, EEE = int 0s) trace system, whose
non-sequential intersection of that solid read an int -> crash.

Fix: the gate now treats a DISPLACING fold (identity rotation + non-zero translation) as a fold
too, so the periscope routes to the flat-plate equivalent (both mirrors flattened, build=0, no
mesh solid, no crash).

  (A) GATE RECOGNISES A PERISCOPE: with a promoted-solid row and a periscope fold transform
      (identity rotation + lateral offset) the straight-equivalent builder returns rows
      (non-None); the OLD rotation-only gate would have returned None.
  (B) GATE STILL REJECTS A NO-OP: an identity transform with ZERO translation (no real fold)
      still returns None -- unfolded scenes stay untouched.
  (C) AZ85 ROTATING FOLD UNCHANGED: the two-mirror AZ85 still yields flat-plate equivalent rows
      and its preview still folds to the known detector (no regression from the gate change).
  (E) FOLD-SIGN: a full-mirror row with an injected Input port still folds by its interaction
      reflection (`_row_uses_interaction_fold_pose` == True). Promotion auto-assigns an Input
      port to every promoted solid, which used to bail the interaction fold for a mirror
      FOLLOWER -- so the periscope's 2nd mirror sent the beam out its +Z transmit face and the
      detector/overlays landed on the OPPOSITE branch from the rays. The full-mirror override
      folds it by reflection instead; the injected-input check fails without that fix.
  (D) WIRED: the `displacing` translation gate AND the full-mirror interaction-fold override
      are present in source.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_periscope_fold_crash
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PARAXIAL_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "paraxial_tools.py"
_PORTS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "nonseq_output_ports.py"

# The two-mirror AZ85 (carryover._promote_mirror2) folds to this detector (the bugs/0224
# _KNOWN_FOLDED_DETECTOR); the gate change must leave it byte-identical.
_KNOWN_AZ85_DETECTOR = np.asarray((181.374, 0.0, -13.552), dtype=float)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _periscope_transform(row_index):
    """A periscope pose override: NET-IDENTITY rotation with a lateral +Y offset (the two
    adjacent 90-degree folds carry the downstream rows onto the parallel branch without
    rotating them). Applies from the second mirror onward."""
    if row_index is None or int(row_index) < 2:
        return None
    transform = np.eye(4, dtype=float)
    transform[:3, 3] = np.asarray((0.0, 188.0, 0.0), dtype=float)  # identity R, lateral offset
    return transform


def _identity_transform(row_index):
    """A no-op override: identity rotation AND zero translation -- not a real fold."""
    if row_index is None or int(row_index) < 2:
        return None
    return np.eye(4, dtype=float)


def _detector(bundle):
    for target in getattr(bundle, "targets", []) or []:
        if getattr(target, "is_detector", False):
            return np.asarray(target.center_world, dtype=float).reshape(3)
    return None


def validate_periscope_fold_crash() -> list[Check]:
    checks: list[Check] = []

    # Build a two-mirror AZ85 -- a real folded editor with promoted optical-solid rows -- then
    # drive the gate through its OWN `_optical_axis_fold_world_transform_for_row` by swapping in
    # a periscope / no-op transform. This isolates the gate change (bugs/0230) without needing
    # the gitignored Pyrite STL fixtures.
    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)
    original_fold = editor._optical_axis_fold_world_transform_for_row

    # ---- (A) periscope (identity R + lateral offset) is recognised as a fold --------------- #
    try:
        editor._optical_axis_fold_world_transform_for_row = _periscope_transform
        periscope_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    finally:
        editor._optical_axis_fold_world_transform_for_row = original_fold
    checks.append(Check(
        "GATE recognises a periscope (identity rotation + lateral offset) as a fold",
        periscope_rows is not None and len(periscope_rows) == len(editor.rows),
        f"straight-equivalent rows={None if periscope_rows is None else len(periscope_rows)} "
        f"(expect {len(editor.rows)}; the old rotation-only gate returned None here -> crash)",
    ))

    # ---- (B) a true no-op (identity, zero translation) is still NOT a fold ------------------ #
    try:
        editor._optical_axis_fold_world_transform_for_row = _identity_transform
        noop_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    finally:
        editor._optical_axis_fold_world_transform_for_row = original_fold
    checks.append(Check(
        "GATE still rejects a no-op transform (identity rotation, zero translation)",
        noop_rows is None,
        f"straight-equivalent rows={None if noop_rows is None else len(noop_rows)} "
        f"(expect None; a zero-displacement identity is not a real fold)",
    ))

    # ---- (C) the real AZ85 rotating fold is unchanged (no regression) ----------------------- #
    az_rows = _quiet(editor._folded_optical_solid_straight_equivalent_rows)
    checks.append(Check(
        "AZ85 rotating fold still yields flat-plate equivalent rows (unchanged)",
        az_rows is not None and len(az_rows) == len(editor.rows),
        f"equivalent rows={None if az_rows is None else len(az_rows)}",
    ))
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = _detector(bundle)
    checks.append(Check(
        "AZ85 two-mirror preview still folds to its known detector (gate change is inert here)",
        det is not None and bool(np.allclose(det, _KNOWN_AZ85_DETECTOR, atol=0.5))
        and len(getattr(bundle, "ray_paths", []) or []) > 0,
        f"detector={None if det is None else np.round(det, 2)} "
        f"(expect ~{np.round(_KNOWN_AZ85_DETECTOR, 1)}) rays={len(getattr(bundle, 'ray_paths', []) or [])}",
    ))

    # ---- (E) FOLD-SIGN: a full-mirror FOLLOWER folds by reflection, not its transmit port --- #
    # bugs/0230 alignment fix: promotion auto-assigns an Input port to every promoted solid, so
    # `_interaction_fold_pose_from_frame` used to bail on the input-port check and disable the
    # interaction fold for a mirror processed as a FOLLOWER -- the periscope's 2nd mirror then
    # sent the downstream chain out its +Z transmit face (detector on the opposite branch from
    # the folded rays). A full mirror must ALWAYS fold by reflection: `_row_uses_interaction_
    # fold_pose` must now return True for a full-mirror row even though it carries an Input port.
    from KrakenOS.UI.nonseq_output_ports import (
        _row_uses_interaction_fold_pose,
        _solid_has_full_mirror_interaction_face,
        _row_advanced,
    )
    from KrakenOS.UI.optical_solid_metadata import (
        OPTICAL_SOLID_FACES_ADVANCED_ATTR,
        OPTICAL_SOLID_FACE_PORT_INPUT,
        normalize_optical_solid_face_metadata,
        optical_solid_face_by_port_role,
        optical_solid_face_world_records,
    )

    import copy

    mirror_row = None
    for row in editor.rows:
        advanced = getattr(row, "advanced", {}) or {}
        if not (isinstance(advanced, dict) and advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR)):
            continue
        try:
            world_faces = optical_solid_face_world_records(row, 0.0, assigned_only=True)
        except Exception:
            continue
        if _solid_has_full_mirror_interaction_face(world_faces):
            mirror_row = row
            break

    # Inject an explicit Input port onto a non-Mirror face of a COPY of the mirror row -- the
    # exact promotion state that broke the Pyrite periscope's 2nd mirror. With the bugs/0230
    # override the full mirror must STILL fold by its interaction reflection (True); the old
    # input-port bail forced this False, sending the beam out a transmit port (opposite branch).
    injected_input = False
    uses_with_input = False
    if mirror_row is not None:
        row_with_input = copy.deepcopy(mirror_row)
        osf = row_with_input.advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        for face in (osf.get("faces", []) if isinstance(osf, dict) else []):
            if isinstance(face, dict) and str(face.get("function", "")).strip() != "Mirror":
                face["port_role"] = OPTICAL_SOLID_FACE_PORT_INPUT
                face["role"] = "Input"
                break
        meta_in = normalize_optical_solid_face_metadata(
            _row_advanced(row_with_input).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        injected_input = (
            optical_solid_face_by_port_role(meta_in, OPTICAL_SOLID_FACE_PORT_INPUT) is not None
        )
        uses_with_input = bool(
            _row_uses_interaction_fold_pose(row_with_input, np.zeros(3), np.eye(3))
        )
    checks.append(Check(
        "FOLD-SIGN: a full-mirror row folds by its interaction reflection EVEN WITH an Input port",
        mirror_row is not None and injected_input and uses_with_input,
        f"full_mirror_row_found={mirror_row is not None} injected_input_port={injected_input} "
        f"uses_interaction_fold={uses_with_input} "
        f"(all must be True; the input-port bail used to force this False -> +Z transmit exit)",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    try:
        src = _PARAXIAL_SRC.read_text(encoding="utf-8")
        ports_src = _PORTS_SRC.read_text(encoding="utf-8")
    except Exception:
        src = ports_src = ""
    wired = (
        "bugs/0230" in src
        and "displacing" in src
        and "np.linalg.norm(translation)" in src
        and "bugs/0230" in ports_src
        and "_solid_has_full_mirror_interaction_face(faces)" in ports_src
    )
    checks.append(Check(
        "the translating-fold gate AND the full-mirror interaction-fold override are wired",
        wired,
        f"gate(bugs/0230,displacing)={'bugs/0230' in src and 'displacing' in src} "
        f"fold_sign(ports bugs/0230)={'bugs/0230' in ports_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_periscope_fold_crash()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_periscope_fold_crash()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Periscope-fold-crash validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
