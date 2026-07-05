"""Display-free guard: the FOV "Solve for Thickness" works on a FOLDED (promoted-mirror) scene.

The user double-clicked the FOV plane, typed 55x55, clicked Solve for Thickness -- and NOTHING
happened. Root cause (both folded-scene bugs): image_thickness_row landed on the RA mirror (not the
image gap), and the plain _conjugate_pair used the whole-system principal planes -- inflated by the
flattened mirror plates (ppp ~ -196 mm) -- so its thin-lens conjugate yielded a NEGATIVE image
distance and returned None ("no real-image conjugate", shown only in the status bar).

Fix: `_folded_conjugate_gaps_for_magnification` solves the conjugate against the LENS-ONLY first
order (lens block, mirrors + object/image gaps excluded, last-surface gap zeroed) and maps the
solved distances onto the true folded object/image gap TOTALS; `_apply_conjugate_pair` takes this
folded branch and writes the gaps.

  (A) POSITIVE CONJUGATE: on the folded AZ85 the helper returns POSITIVE object + image distances
      for a target magnification (where the plain formula went negative -> None).
  (B) SOLVE APPLIES + IMAGES: fov_solve("object","thickness", ...) returns ok=True, changes the
      object/image gaps, and the scene still images (rays reach the detector).
  (C) NON-FOLDED UNTOUCHED: the helper returns None for an unfolded scene, so the plain
      _conjugate_pair path is used (no regression).
  (D) WIRED: _apply_conjugate_pair takes the folded branch via _folded_conjugate_gaps_for_magnification.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_folded_fov_solve
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.quick_estimation import QuickEstimationService
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _qe(editor):
    return QuickEstimationService(
        types.SimpleNamespace(
            editor=editor,
            quick_estimation_var=types.SimpleNamespace(get=lambda: True),
        )
    )


def _load_unfolded():
    path = _LAYOUTS / "machine_vision_85mm_azure_datasheet_05x_20x.py"
    info = _quiet(_load_python_data, path)
    rows = [KrakenLayoutEditor._row_from_layout_item(it) for it in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    ed = _quiet(_snapshot_editor, rows, info.get("settings", {}) or {})
    ed.tk = object()
    ed.current_layout_file = path
    for a in ("imported_lens_step_path", "imported_optical_step_path", "imported_led_step_path", "imported_camera_step_path"):
        if not hasattr(ed, a):
            setattr(ed, a, None)
    _quiet(ed._normalize_special_rows)
    return ed


def validate_folded_fov_solve() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)

    # ---- (A) positive conjugate for a target mag -------------------------------------------- #
    folded = _quiet(editor._folded_conjugate_gaps_for_magnification, 0.5)
    checks.append(Check(
        "POSITIVE CONJUGATE: the folded helper returns positive object + image distances (plain path went None)",
        folded is not None
        and folded["object_distance"] > 0
        and folded["image_distance"] > 0,
        f"folded={None if folded is None else {k: round(v, 2) if isinstance(v, float) else v for k, v in folded.items()}}",
    ))

    # ---- (B) fov_solve applies + still images ----------------------------------------------- #
    qe = _qe(editor)
    before = [float(r.thickness) for r in editor.rows]
    ok, msg = _quiet(qe.fov_solve, "object", "thickness", 40.0, 40.0, None)
    changed = before != [float(r.thickness) for r in editor.rows]
    _s, _r, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det = next(
        (np.asarray(t.center_world, dtype=float).reshape(3) for t in bundle.targets if getattr(t, "is_detector", False)),
        None,
    )
    ends = np.asarray([np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle.ray_paths]) if bundle.ray_paths else np.zeros((0, 3))
    reach = int((np.linalg.norm(ends - det, axis=1) < 5.0).sum()) if det is not None and len(ends) else 0
    checks.append(Check(
        "SOLVE APPLIES + IMAGES: fov_solve on the folded scene succeeds, changes the gaps, still images",
        bool(ok) and changed and reach >= 8,
        f"ok={ok} changed={changed} rays_on_detector={reach} msg={msg[:60]!r}",
    ))

    # ---- (C) non-folded scene falls through to the plain path ------------------------------- #
    try:
        unfolded = _load_unfolded()
        unfolded_folded = _quiet(unfolded._folded_conjugate_gaps_for_magnification, 0.5)
        ok_c = unfolded_folded is None
        detail_c = f"unfolded helper returns None: {unfolded_folded is None}"
    except Exception as exc:
        ok_c = False
        detail_c = f"unfolded load failed: {exc!r}"
    checks.append(Check(
        "NON-FOLDED UNTOUCHED: the folded helper returns None on an unfolded scene (plain path used)",
        ok_c,
        detail_c,
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    wired = (
        "_folded_conjugate_gaps_for_magnification" in src
        and "object_delta" in src
        and "image_delta" in src
    )
    checks.append(Check(
        "WIRED: _apply_conjugate_pair takes the folded branch and writes the folded gaps",
        wired,
        f"folded_branch={'_folded_conjugate_gaps_for_magnification' in src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_folded_fov_solve()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_folded_fov_solve()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("Folded-FOV-solve validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
