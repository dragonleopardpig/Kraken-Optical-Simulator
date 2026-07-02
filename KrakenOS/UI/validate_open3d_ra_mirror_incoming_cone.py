"""Display-free guard for bugs/0205: on the folded RA-mirror scene the INCOMING (pre-mirror)
leg of the drawn rays must be a real CONE (a 2D disk cross-section), not a flat fan.

The user flagged (flag_20260702_130129_167) "the launched rays seem to be a Fan, but after
reflection become a Cone?" on the folded AZ85 RA-mirror. Root cause: the display fold
ROTATED every straight-equivalent vertex at/after the mirror station about the fold anchor
(``_fold_straight_equivalent_display_rays`` -> ``_fold_ray_downstream_of_station``). Because
the station sits at the FIRST surface (~59.4mm), essentially the whole ray was rotated,
mapping the incoming cone's meridional (X) spread into pure axial (Z) displacement -> the
incoming leg collapsed to a flat Y-only fan while the meridional spread migrated into the
outgoing arm's Z-spread.

Fix (bugs/0205): fold by REFLECTING the straight-equivalent rays about the mirror plane
(``_reflect_straight_equivalent_display_rays``). A reflection is an ISOMETRY: the incoming
leg (same side of the plane as the launch point) is left UNTOUCHED -> its cone is preserved;
the outgoing leg is congruent -> still a cone whose focus stays on the drawn detector.

This guard binds the REAL wired pipeline to the live AZ85 editor and asserts, on the
on-axis field's incoming leg (a Z-slice BELOW the mirror station, clear of the fold):
  1. the FINAL (folded) incoming (X,Y) cross-section is a 2D DISK (2nd singular value
     > 0.5), not collinear -- i.e. a cone, not a fan;
  2. it is ROUND (X-spread ~ Y-spread) -- a revolved cone, not an elongated slit;
  3. its spread is UNCHANGED from the RAW straight-equivalent incoming cross-section (the
     reflection leaves the incoming leg where it was -- the isometry property; a rotation
     fold would have shrunk the X-spread to ~0);
  4. the OUTGOING arm (Y,Z) cross-section stays a 2D DISK (the fold did not flatten it).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_incoming_cone

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

# A Z-slice comfortably BELOW the mirror station (~59.4mm) so it samples the incoming
# leg only; the +X outgoing arm never reaches back here.
_Z_INCOMING = 35.0


def _s2(points, cols) -> float:
    """2nd singular value of a 2-column point cloud: >0 means it spans 2D (a disk),
    ~0 means it is collinear (a flat fan)."""
    a = np.asarray(points, dtype=float)
    if a.ndim != 2 or a.shape[0] < 3:
        return 0.0
    centred = a[:, cols] - a[:, cols].mean(0)
    s = np.linalg.svd(centred, compute_uv=False)
    return float(s[1]) if s.size >= 2 else 0.0


def _onaxis(paths, need_x=False):
    out = []
    for p in paths:
        if p.ndim == 2 and p.shape[0] >= 3 and p.shape[1] >= 3 and float(np.linalg.norm(p[0, :3])) <= 1.0:
            if need_x and float(p[:, 0].max()) <= 250.0:
                continue
            out.append(p)
    return out


def _xsec_z(paths, z, cols):
    out = []
    for p in paths:
        za = p[:, 2]
        for i in range(len(p) - 1):
            if (za[i] - z) * (za[i + 1] - z) <= 0 and abs(za[i + 1] - za[i]) > 1e-9:
                t = (z - za[i]) / (za[i + 1] - za[i])
                out.append((p[i] + t * (p[i + 1] - p[i]))[cols])
                break
    return np.asarray(out, dtype=float)


def _xsec_x(paths, x, cols):
    out = []
    for p in paths:
        xa = p[:, 0]
        for i in range(len(p) - 1):
            if (xa[i] - x) * (xa[i + 1] - x) <= 0 and abs(xa[i + 1] - xa[i]) > 1e-9:
                t = (x - xa[i]) / (xa[i + 1] - xa[i])
                out.append((p[i] + t * (p[i + 1] - p[i]))[cols])
                break
    return np.asarray(out, dtype=float)


def _run() -> tuple[list[str], list[str]]:
    failures: list[str] = []
    notes: list[str] = []
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(_AZ85)
            editor.snap_detector_to_image_plane()
            # RAW straight-equivalent: shadow the reflection fold -> unfolded +Z bundle.
            editor._preview_scene_trace_dirty = True
            editor._reflect_straight_equivalent_display_rays = lambda bundle: None
            _s0, _r0, raw_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            raw = [np.asarray(p.points_world, dtype=float) for p in (raw_bundle.ray_paths or [])]
            # FINAL production reflection fold.
            del editor._reflect_straight_equivalent_display_rays
            editor._preview_scene_trace_dirty = True
            _s1, _r1, fin_bundle = editor._build_preview_system_rays_bundle(update_state=True)
            fin = [np.asarray(p.points_world, dtype=float) for p in (fin_bundle.ray_paths or [])]

        raw_oa = _onaxis(raw)               # straight-equivalent: +Z rays, no +X fold
        fin_oa = _onaxis(fin, need_x=True)  # folded: reach out the +X arm
        if len(fin_oa) < 10:
            failures.append(f"only {len(fin_oa)} folded on-axis rays (need >=10 for a cross-section)")
        if len(raw_oa) < 10:
            failures.append(f"only {len(raw_oa)} straight-equivalent on-axis rays")

        fin_inc = _xsec_z(fin_oa, _Z_INCOMING, [0, 1])   # (X,Y)
        raw_inc = _xsec_z(raw_oa, _Z_INCOMING, [0, 1])
        s2_inc = _s2(fin_inc, [0, 1])

        # (1) DISK not fan
        if s2_inc <= 0.5:
            failures.append(
                f"incoming (X,Y)@Z={_Z_INCOMING} is FLAT (s2={s2_inc:.3f}<=0.5) -> fan not cone (bugs/0205 regression)"
            )
        # (2) round
        if len(fin_inc) >= 3:
            xs, ys = float(np.ptp(fin_inc[:, 0])), float(np.ptp(fin_inc[:, 1]))
            ratio = xs / ys if ys > 1e-9 else 0.0
            if not (0.7 <= ratio <= 1.4):
                failures.append(
                    f"incoming cone not round: X-spread {xs:.3f} / Y-spread {ys:.3f} = {ratio:.3f} (want ~1)"
                )
        # (3) isometry: incoming spread unchanged from the raw straight-equivalent
        if len(raw_inc) >= 3 and len(fin_inc) >= 3:
            rx, ry = float(np.ptp(raw_inc[:, 0])), float(np.ptp(raw_inc[:, 1]))
            fx, fy = float(np.ptp(fin_inc[:, 0])), float(np.ptp(fin_inc[:, 1]))
            if rx > 1e-6 and abs(fx - rx) / rx > 0.05:
                failures.append(
                    f"incoming X-spread changed by the fold: raw {rx:.3f} -> final {fx:.3f} (>5%, not an isometry)"
                )
            if ry > 1e-6 and abs(fy - ry) / ry > 0.05:
                failures.append(
                    f"incoming Y-spread changed by the fold: raw {ry:.3f} -> final {fy:.3f} (>5%)"
                )
        else:
            failures.append(f"too few incoming cross-section points raw {len(raw_inc)} / final {len(fin_inc)}")

        # (4) outgoing arm stays a disk
        dx = max((float(p[:, 0].max()) for p in fin_oa), default=0.0)
        fin_out = _xsec_x(fin_oa, 0.6 * dx, [1, 2])   # (Y,Z)
        s2_out = _s2(fin_out, [0, 1])
        if s2_out <= 0.5:
            failures.append(
                f"outgoing (Y,Z)@X={0.6 * dx:.0f} is FLAT (s2={s2_out:.3f}<=0.5) -> fan not cone"
            )

        notes.append(
            f"on-axis rays raw {len(raw_oa)} / folded {len(fin_oa)} | incoming s2={s2_inc:.3f} "
            f"(X {float(np.ptp(fin_inc[:, 0])) if len(fin_inc) else 0:.3f} ~ Y "
            f"{float(np.ptp(fin_inc[:, 1])) if len(fin_inc) else 0:.3f}) | outgoing s2={s2_out:.3f} | drawn arm X={dx:.1f}"
        )
    except Exception as exc:  # noqa: BLE001
        failures.append(f"AZ85 incoming-cone integration raised {exc!r}")
    return failures, notes


def run_checks() -> tuple[bool, list[str]]:
    """(passed, notes) for the penta-validator phase. Notes carry the failure lines when
    it fails, else the single info line."""
    failures, notes = _run()
    return len(failures) == 0, (failures + notes if failures else notes)


def main() -> int:
    failures, notes = _run()
    if failures:
        print("FAIL bugs/0205 folded RA-mirror incoming cone (launched cone collapsed to a fan):")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0205 folded RA-mirror incoming cone (incoming leg is a preserved cone):")
    print("  - incoming (X,Y) cross-section is a 2D disk (s2>0.5), round, not a flat fan")
    print("  - incoming spread is unchanged from the raw straight-equivalent (reflection is an isometry)")
    print("  - outgoing arm (Y,Z) cross-section stays a 2D disk")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
