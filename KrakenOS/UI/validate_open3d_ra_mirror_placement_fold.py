"""Display-free guard for bugs/0193: on the folded RA-mirror scene a row-backed scene
PLACEMENT (an aperture-stop / reference-grid marker) must fold onto the mirror's
reflected +X branch, not float on the unfolded +Z axis.

The user re-flagged the folded AZ85 after bugs/0192 fixed the reflection: "there still
exist S2 overlay" / "one arrow wrong location" -- a reference grid stranded at
(0,0,~169) on the straight axis, above the folded optics.

Root cause: ``scene_builder.build_scene_placements`` copies each placement's world pose
from the targets BEFORE ``_fold_promoted_mirror_table_row_targets`` runs, so the aperture
stop (row 5) keeps the unfolded +Z center while every consumer (grid overlay, drag
gizmo) draws it there. ``_fold_promoted_mirror_table_row_targets`` folds the targets but
not the parallel placements.

Fix: ``_fold_promoted_mirror_scene_placements`` applies the identical per-row rigid fold
(``_optical_axis_fold_world_transform_for_row``) to every placement whose row carries a
fold override, right after the target fold. Unfolded rows (the mirror pivot, plain
layouts) return ``None`` and stay byte-identical.

This guard asserts, on the live AZ85 editor:
  1. BEFORE (method shadowed): the row-5 scene_target placement floats unfolded at X~0,
     Z>90 -- the precondition, so the guard is not vacuous;
  2. AFTER (real method): that placement folds onto +X (X>40), lands at Z~=the mirror
     plane, and its center matches the row-5 TARGET's folded center (consistency);
  3. the mirror pivot placement (row 1, no fold override) is byte-identical BEFORE/AFTER;
  4. scope: the sequential flat_mirror scene has zero fold overrides -> the method folds
     0 placements (inert on non-promoted / plain-mirror layouts).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_placement_fold

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _build_editor, _AZ85, _PLAIN


def _placements_by_row(bundle):
    out = {}
    for pl in list(getattr(bundle, "placements", []) or []):
        ri = getattr(pl, "row_index", None)
        if ri is not None:
            out[int(ri)] = pl
    return out


def _targets_by_row(bundle):
    out = {}
    for t in list(getattr(bundle, "targets", []) or []):
        ri = getattr(t, "row_index", None)
        if ri is not None:
            out[int(ri)] = t
    return out


def _center(obj):
    return np.asarray(getattr(obj, "center_world"), dtype=float).reshape(-1)[:3]


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)
            # BEFORE: shadow the wired placement fold with a no-op -> raw unfolded grid.
            editor._fold_promoted_mirror_scene_placements = lambda bundle: 0
            _s0, _r0, raw_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            raw_pl = _placements_by_row(raw_bundle)
            # AFTER: the REAL wired method inside a fresh preview build.
            del editor._fold_promoted_mirror_scene_placements
            _s1, _r1, fixed_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            fixed_pl = _placements_by_row(fixed_bundle)
            fixed_tg = _targets_by_row(fixed_bundle)

        # locate the folded scene_target placement (the aperture-stop grid, row 5).
        target_rows = [
            ri for ri, pl in raw_pl.items()
            if str(getattr(pl, "source_kind", "")) == "scene_target"
        ]
        if not target_rows:
            failures.append("AZ85: no scene_target placement found (precondition gone)")
        else:
            ap_row = max(target_rows)  # the aperture stop sits downstream of the mirror

            # (1) BEFORE: unfolded on the straight +Z axis.
            b = _center(raw_pl[ap_row])
            if not (abs(b[0]) < 20.0 and b[2] > 90.0):
                failures.append(
                    f"AZ85 precondition: row {ap_row} placement BEFORE is not the stranded +Z grid; "
                    f"got {np.round(b,2).tolist()} (guard vacuous)"
                )

            # (2) AFTER: folded onto +X, at the mirror plane, matching its target.
            a = _center(fixed_pl[ap_row])
            if not (a[0] > 40.0):
                failures.append(
                    f"AZ85: row {ap_row} placement AFTER did not fold onto +X; got {np.round(a,2).tolist()}"
                )
            if a[2] > 90.0:
                failures.append(
                    f"AZ85: row {ap_row} placement AFTER still floats high on +Z (z={a[2]:.2f}); expected the folded plane"
                )
            tgt = fixed_tg.get(ap_row)
            if tgt is not None:
                tc = _center(tgt)
                if not np.allclose(a, tc, atol=1e-6):
                    failures.append(
                        f"AZ85: row {ap_row} placement center {np.round(a,3).tolist()} != its folded target "
                        f"center {np.round(tc,3).tolist()} (inconsistent fold)"
                    )
            notes.append(
                f"AZ85 row {ap_row} aperture grid: BEFORE {np.round(b,2).tolist()} -> AFTER {np.round(a,2).tolist()}"
            )

        # (3) the mirror pivot placement (no fold override) is unchanged.
        solid_rows = [
            ri for ri, pl in raw_pl.items()
            if str(getattr(pl, "source_kind", "")) == "optical_solid"
        ]
        for ri in solid_rows:
            b = _center(raw_pl[ri])
            a = _center(fixed_pl[ri])
            if not np.allclose(a, b, atol=1e-9):
                failures.append(
                    f"AZ85: mirror-pivot placement row {ri} moved {np.round(b,3).tolist()} -> "
                    f"{np.round(a,3).tolist()} (the pivot must stay byte-identical)"
                )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 integration raised {exc!r}")

    # (4) scope: the sequential flat_mirror scene folds ZERO placements.
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            plain = _build_editor(_PLAIN)
            _sp, _rp, plain_bundle = plain._build_preview_system_rays_bundle(update_state=True)
            plain_folded = plain._fold_promoted_mirror_scene_placements(plain_bundle)
        if plain_folded != 0:
            failures.append(
                f"regression: {_PLAIN} folded {plain_folded} placement(s) -> the fold is not inert on a plain mirror"
            )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"flat_mirror scope check raised {exc!r}")

    if failures:
        print("FAIL bugs/0193 folded RA-mirror scene placement fold (aperture grid stranded on +Z):")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0193 folded RA-mirror scene placement fold (aperture grid on the reflected +X branch):")
    print("  - BEFORE the row-5 aperture grid floats unfolded on +Z; AFTER it folds onto +X at the mirror plane")
    print("  - the folded placement center matches its folded detector target; the mirror pivot is unchanged")
    print(f"  - scope: {_PLAIN} folds 0 placements (inert on plain / sequential mirrors)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
