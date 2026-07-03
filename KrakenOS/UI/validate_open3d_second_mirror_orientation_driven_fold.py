"""Display-free guard for bugs/0213 (Fix B) -- a free-placed, user-ORIENTED second
promoted RA mirror folds BOTH the detector and the drawn rays by physics off its OWN
world orientation (``r = d - 2(d.n)n``), with NO hard-coded fold axis.

Background: bugs/0212 (Fix A) stopped a fresh no-face 2nd mirror being swept onto
mirror 1's fold leg -- it pinned it where dropped, but inertly (no fold). The user's
architectural ask was the general case: let the user place AND orient the mirror, and
have the beam follow the mirror's orientation. Fix B makes the PINNED mirror a real
fold in the two display systems that must agree:

  * the pose-override builder (``build_optical_solid_output_port_pose_overrides`` in
    ``nonseq_output_ports``) pins the free-placed mirror at its authored world pose and
    folds the downstream detector off that mirror's WORLD-oriented interaction face;
  * the display rays (``_reflect_straight_equivalent_display_rays`` in
    ``three_d_scene_tools``) get a POST-PASS that reflects the already-folded polyline
    about the mirror's REAL world plane (``free_placed_mirror_world_planes`` in
    ``services.folded_sequential_fold``) -- point = its world centre, normal = the
    Mirror face's local normal rotated by the row tilt.

The free-placed mirror's ``desp`` encodes the FOLDED-world drop point (``desp_x`` = folded
X, ``desp_z`` = ``center_world_z - station``), which ``_solve_mirror_tilt`` cannot seat, so
it yields NO sequential-fold record -- hence the world-plane post-pass rather than a
sequential record. Layout-authored cascade prisms (penta) carry NO ``center_world``
marker, so ``free_placed_mirror_world_planes`` returns [] for them: penta is untouched.

This guard is display-free (it builds the ray bundle geometry headlessly, no VTK draw)
and asserts BOTH halves agree AND that the fold DIRECTION follows the mirror orientation
(a causal tilt-0 vs tilt_y=-90 contrast flips the fold leg), AND that the mechanism is
penta-safe (marker-keyed) and actually wired into both source modules.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_second_mirror_orientation_driven_fold
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import copy
import io
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor
from KrakenOS.UI import nonseq_output_ports as nop
from KrakenOS.UI.services.folded_sequential_fold import (
    fold_promoted_mirror_specs_to_sequential,
    free_placed_mirror_world_planes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PORTS_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "nonseq_output_ports.py"
_SCENE_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "three_d_scene_tools.py"

# The placed world centre the user dropped + oriented the 2nd mirror at (bugs/0211/0212).
_PLACED = np.asarray([210.7, 0.0, 71.9], dtype=float)


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _free_placed_mirror2(mirror1, z_station: float, tilt_y: float):
    """A 2nd RA mirror built like a fresh promote of mirror 1, free-placed at
    ``_PLACED`` and oriented by ``tilt_y``. Carries the ``StepOverlayPromotion``
    ``center_world`` marker + the folded-world ``desp`` a real promote writes."""
    m2 = copy.deepcopy(mirror1)
    advanced = dict(getattr(m2, "advanced", {}) or {})
    advanced["StepOverlayPromotion"] = {
        "step_label": "optical",
        "center_world": [float(x) for x in _PLACED],
    }
    m2.advanced = advanced
    m2.desp_x, m2.desp_y, m2.desp_z = float(_PLACED[0]), float(_PLACED[1]), float(_PLACED[2] - z_station)
    m2.tilt_x, m2.tilt_y, m2.tilt_z = 0.0, float(tilt_y), 0.0
    m2.name = "Promoted OPTICAL STEP optical solid (free-placed 2nd fold)"
    return m2


def _onaxis(bundle):
    out = []
    for p in getattr(bundle, "ray_paths", None) or []:
        pw = np.asarray(getattr(p, "points_world", None), dtype=float)
        if pw.ndim == 2 and pw.shape[0] >= 2 and pw.shape[1] >= 3 and float(np.linalg.norm(pw[0][:3])) <= 1.0:
            out.append(pw)
    return out


def _kinks(path: np.ndarray, cos_max: float = 0.2) -> int:
    seg = np.diff(path[:, :3], axis=0)
    ln = np.linalg.norm(seg, axis=1)
    ok = ln > 1e-6
    if int(ok.sum()) < 2:
        return 0
    u = np.zeros_like(seg)
    u[ok] = seg[ok] / ln[ok, None]
    cos_turn = np.sum(u[:-1] * u[1:], axis=1)
    return int(np.sum(cos_turn < cos_max))


def _tag(bundle) -> str:
    for p in getattr(bundle, "ray_paths", None) or []:
        src = str(getattr(p, "display_geometry_source", "") or "")
        if src:
            return src
    return ""


def _center(entry) -> np.ndarray:
    return np.asarray(entry.get("center"), dtype=float).reshape(3)


def _run(tilt_y: float) -> dict:
    """Build the free-placed 2-mirror scene at ``tilt_y`` and return the override poses,
    the free-placed world planes, and the on-axis display-ray fold, headlessly."""
    editor = _build_editor(_AZ85)
    rows = list(editor.rows)
    img_idx = len(rows) - 1
    mirror1 = rows[1]
    z_pos = nop.row_z_positions([nop._row_like(r) for r in rows])
    z_station = float(z_pos[img_idx]) if img_idx < len(z_pos) else 0.0
    m2 = _free_placed_mirror2(mirror1, z_station, tilt_y)
    editor.rows = rows[:img_idx] + [m2] + rows[img_idx:]
    editor._normalize_special_rows()
    mirror2_idx, image_idx = img_idx, img_idx + 1

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        overrides = nop.build_optical_solid_output_port_pose_overrides(list(editor.rows))
        specs = editor._serializable_specs_for_rows(list(editor.rows))
        _folded, records = fold_promoted_mirror_specs_to_sequential(specs)
        record_rows = {int(r.get("row_index", -1)) for r in records}
        planes = free_placed_mirror_world_planes(specs, exclude_row_indices=record_rows)
        _sys, _r, bundle = editor._build_preview_system_rays_bundle(update_state=True)

    oa = _onaxis(bundle)
    path = oa[0] if oa else None
    return {
        "mirror2_center": _center(overrides[mirror2_idx]) if mirror2_idx in overrides else None,
        "image_center": _center(overrides[image_idx]) if image_idx in overrides else None,
        "planes": planes,
        "kinks": _kinks(path) if path is not None else -1,
        "endpoint": np.asarray(path[-1][:3], dtype=float) if path is not None else None,
        "tag": _tag(bundle),
    }


def _marker_free_plane_counts() -> tuple[int, int]:
    """free_placed plane counts for two LAYOUT-authored (no center_world marker) scenes:
    the stock single-fold AZ85 and the 0208 thickness-authored 2-mirror chain."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        ed = _build_editor(_AZ85)
        specs = ed._serializable_specs_for_rows(list(ed.rows))
        _f, recs = fold_promoted_mirror_specs_to_sequential(specs)
        rr = {int(r.get("row_index", -1)) for r in recs}
        stock = len(free_placed_mirror_world_planes(specs, exclude_row_indices=rr))

        rows = list(ed.rows)
        m2 = SurfaceRow(**asdict(rows[1]))
        m2.name = "2nd fold (thickness-authored)"
        rows[7].thickness = 90.0
        m2.thickness = 60.0
        ed.rows = rows[:8] + [m2] + [rows[8]]
        ed._normalize_special_rows()
        specs2 = ed._serializable_specs_for_rows(list(ed.rows))
        _f2, recs2 = fold_promoted_mirror_specs_to_sequential(specs2)
        rr2 = {int(r.get("row_index", -1)) for r in recs2}
        chain = len(free_placed_mirror_world_planes(specs2, exclude_row_indices=rr2))
    return stock, chain


def validate_second_mirror_orientation_driven_fold() -> list[Check]:
    checks: list[Check] = []
    down = _run(-90.0)   # user orients the 2nd mirror to fold onto the -Z leg
    flat = _run(0.0)     # same placement, orientation as mirror 1 -> folds onto +Z leg

    # 1) OVERRIDE PINS the free-placed mirror at its dropped world pose (not swept
    #    down mirror 1's +X leg as pre-0212).
    m2c = down["mirror2_center"]
    pinned = m2c is not None and bool(np.linalg.norm(m2c - _PLACED) < 1.0)
    checks.append(
        Check(
            "override pins the free-placed 2nd mirror at its dropped world pose [210.7,0,71.9]",
            pinned,
            f"mirror2 override center={None if m2c is None else tuple(round(float(v),3) for v in m2c)} "
            f"(expect ~{tuple(round(float(v),3) for v in _PLACED)})",
        )
    )

    # 2) OVERRIDE FOLDS the detector off the mirror's WORLD face onto the -Z leg:
    #    X stays at the mirror station (~210.7), Z folds negative (leaves the +X leg
    #    at Z~=71.9). This is physics off the mirror's own oriented face.
    imc = down["image_center"]
    det_folded = (
        imc is not None
        and abs(float(imc[0]) - _PLACED[0]) < 1.0
        and float(imc[2]) < -10.0
    )
    checks.append(
        Check(
            "override folds the detector off the mirror's world face onto the -Z leg (tilt_y=-90)",
            det_folded,
            f"Image override center={None if imc is None else tuple(round(float(v),3) for v in imc)} "
            f"(expect X~210.7, Z<<0)",
        )
    )

    # 3) THE DISPLAY RAYS AGREE: the on-axis ray folds TWICE (once per mirror) on the
    #    cone-preserving reflection path, and its endpoint COINCIDES with the folded
    #    detector -- the two systems land the beam at the same physics-fold point.
    ep = down["endpoint"]
    rays_agree = (
        down["kinks"] == 2
        and down["tag"] == "folded_straight_equivalent_reflected"
        and ep is not None
        and imc is not None
        and bool(np.linalg.norm(ep - imc) < 1.0)
    )
    checks.append(
        Check(
            "the display rays fold twice and land ON the folded detector (rays == detector)",
            rays_agree,
            f"kinks={down['kinks']} (expect 2), tag={down['tag']!r}, endpoint="
            f"{None if ep is None else tuple(round(float(v),3) for v in ep)} vs detector="
            f"{None if imc is None else tuple(round(float(v),3) for v in imc)} (expect coincident)",
        )
    )

    # 4) CAUSAL / ORIENTATION-DRIVEN: the SAME placement with tilt 0 folds onto the
    #    +Z leg instead. Both the drawn ray endpoint AND the detector override flip
    #    their Z sign with the mirror orientation -- so the fold direction is physics
    #    off the mirror's own normal (r = d - 2(d.n)n), NOT a hard-coded axis.
    ep0 = flat["endpoint"]
    im0 = flat["image_center"]
    ray_flip = (
        ep is not None and ep0 is not None
        and flat["kinks"] == 2
        and float(ep[2]) < -1.0 and float(ep0[2]) > 1.0
    )
    det_flip = (
        imc is not None and im0 is not None
        and float(imc[2]) < -1.0 and float(im0[2]) > 1.0
    )
    checks.append(
        Check(
            "CAUSAL: tilt 0 folds onto the +Z leg -- both ray + detector Z flip with orientation (no fixed axis)",
            ray_flip and det_flip,
            f"tilt_y=-90 ray.z={None if ep is None else round(float(ep[2]),3)} "
            f"det.z={None if imc is None else round(float(imc[2]),3)}; "
            f"tilt 0 ray.z={None if ep0 is None else round(float(ep0[2]),3)} "
            f"det.z={None if im0 is None else round(float(im0[2]),3)} (expect signs to flip)",
        )
    )

    # 5) PENTA-SAFE (marker-keyed): the free-placed scene yields exactly ONE world
    #    plane; the stock single-fold AZ85 and the 0208 thickness-authored 2-mirror
    #    chain (both LAYOUT-authored, no center_world marker) yield ZERO -- so the
    #    post-pass never touches a layout-authored cascade (penta stays green).
    stock_n, chain_n = _marker_free_plane_counts()
    n_free = len(down["planes"])
    penta_safe = n_free == 1 and stock_n == 0 and chain_n == 0
    checks.append(
        Check(
            "penta-safe: 1 free-placed plane for the marked scene, 0 for marker-less layouts (stock AZ85, 0208 chain)",
            penta_safe,
            f"free_placed_planes: marked_scene={n_free} (expect 1), stock_AZ85={stock_n} (expect 0), "
            f"chain_2mirror={chain_n} (expect 0)",
        )
    )

    # 6) NON-VACUOUS orientation: the single free-placed plane's WORLD normal rotates
    #    with the tilt -- tilt_y=-90's normal differs from tilt 0's (n_local carried
    #    into the world by R(tilt)), so the fold really tracks the orientation.
    n_down = down["planes"][0][2] if down["planes"] else None
    n_flat = flat["planes"][0][2] if flat["planes"] else None
    normal_tracks_tilt = (
        n_down is not None and n_flat is not None
        and float(np.linalg.norm(np.asarray(n_down) - np.asarray(n_flat))) > 0.1
    )
    checks.append(
        Check(
            "the free-placed plane normal tracks the row tilt (tilt_y=-90 normal != tilt 0 normal)",
            normal_tracks_tilt,
            f"tilt_y=-90 world_normal={None if n_down is None else tuple(round(float(v),3) for v in n_down)} "
            f"vs tilt 0={None if n_flat is None else tuple(round(float(v),3) for v in n_flat)} (expect different)",
        )
    )

    # 7) WIRED into both source modules (guard not vestigial): the pinned-pose helper
    #    in nonseq_output_ports, the world-plane post-pass call in three_d_scene_tools.
    try:
        ports_src = _PORTS_SRC.read_text(encoding="utf-8")
    except Exception:
        ports_src = ""
    try:
        scene_src = _SCENE_SRC.read_text(encoding="utf-8")
    except Exception:
        scene_src = ""
    wired = (
        "_free_placed_solid_pinned_pose" in ports_src
        and "free_placed_mirror_world_planes" in scene_src
    )
    checks.append(
        Check(
            "the pin + post-pass are wired into both source modules (nonseq_output_ports + three_d_scene_tools)",
            wired,
            f"pinned_pose_helper_in_ports={'_free_placed_solid_pinned_pose' in ports_src}, "
            f"post_pass_call_in_scene_tools={'free_placed_mirror_world_planes' in scene_src}",
        )
    )

    return checks


def run_checks() -> tuple[bool, list[str]]:
    """Penta-phase entry point: ``(passed, notes)`` where notes are the failures."""
    checks = validate_second_mirror_orientation_driven_fold()
    failures = [f"{check.check} | {check.detail}" for check in checks if not check.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_second_mirror_orientation_driven_fold()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} | {check.detail}")
    if failed:
        raise SystemExit(1)
    print("Second mirror orientation-driven fold validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
