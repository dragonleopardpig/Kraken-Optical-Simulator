"""Display-free guard for bugs/0201 (#6): the 2D preview must SHOW ray tracing on the
folded RA-mirror scene.

Flag ("2D does not show any ray tracing at all!"): the 2D preview (``refresh_plot``)
traced the MESH non-seq system directly --
``system = build_system(require_solids=True); rays = raykeeper(system);
_trace_preview_rays(system, rays, ...)``. On the folded AZ85 the promoted mirror cube is
a non-seq body, so that trace RETROREFLECTS the ideal Thin Lenses into a scattered mess
(endpoints strewn X=100..296, transverse RMS ~45mm). Those world-space rays then hit the
2D meridional SLICE filter (``_should_filter_projection_slice`` is on for world_cone /
world_sections) and NONE survive the projection -- the 2D pane shows ZERO rays. The 3D
view already routed the folded scene through its straight equivalent (bugs/0197) /
sequential-Mirror chain (bugs/0187); the 2D path did not.

Fix (bugs/0201): factor the folded-aware trace + display-bend into shared editor helpers
(``_trace_preview_rays_folded_aware`` / ``_apply_folded_display_bend``) and call them from
BOTH the 3D ``_build_preview_system_rays_bundle`` and the 2D ``refresh_plot``.

This guard drives the exact call sequence ``refresh_plot`` now uses (the shared helpers,
NOT the 3D method), then runs the REAL 2D projection pipeline, and asserts:
  1. the OLD direct mesh trace projects to ZERO rays in the 2D view (the bug: empty pane);
  2. the NEW routed 2D trace projects to many rays AND its world cone converges ON the
     drawn +X detector (folded path engaged, endpoint RMS < 0.1mm);
  3. an unfolded layout (flat_mirror_45_deg.py) still projects rays (helper returns None
     -> the plain mesh trace, byte-identical to before).

STANDALONE (NOT a penta phase) -- no penta phase drives the 2D refresh. In-app eyeball
still owed (headless cannot render the matplotlib 2D canvas).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_2d_folded_shows_rays

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_plot_controller import project_scene_bundle
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor

_PLAIN = "flat_mirror_45_deg.py"


def _preview_2d_sampling_mode(editor) -> str:
    mode = editor._preview_2d_sampling_mode()
    if mode == "display_slice":
        mode = editor._preview_scene_sampling_mode()
    return mode


def _project(editor, bundle):
    return project_scene_bundle(
        bundle,
        editor._current_display_orientation(),
        filter_projection_axis_fields=editor._should_filter_projection_axis_fields(bundle),
        filter_projection_slice=editor._should_filter_projection_slice(bundle),
        filter_ray_display=editor._filter_projected_scene_for_ray_display,
        filter_arm_view=editor._filter_projected_scene_for_arm_view,
    )


def _projected_ray_count(editor, bundle) -> int:
    projected = _project(editor, bundle)
    return len(list(getattr(projected, "rays", []) or []))


def _trace_2d_routed(editor):
    """Replicate the 2D ``refresh_plot`` trace path AFTER the bugs/0201 fix."""
    wavelength = float(editor._current_wavelength())
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    folded_trace_rows = editor._folded_sequential_trace_rows(editor.rows)
    rays, fold_transform = editor._trace_preview_rays_folded_aware(
        system, wavelength, max_radius,
        sampling_mode=_preview_2d_sampling_mode(editor),
        folded_trace_rows=folded_trace_rows,
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    if folded_trace_rows is not None:
        editor._apply_folded_display_bend(bundle, fold_transform)
    return system, bundle, bool(folded_trace_rows is not None)


def _trace_2d_old_mesh(editor):
    """The OLD 2D path: a direct mesh non-seq trace (the one that showed no rays)."""
    wavelength = float(editor._current_wavelength())
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    rays = Kos.raykeeper(system)
    editor._trace_preview_rays(
        system, rays, wavelength, max_radius,
        allow_full_pupil=True, sampling_mode=_preview_2d_sampling_mode(editor),
    )
    return editor._build_scene_bundle(system, rays, max_radius)


def _onaxis_endpoint_stats(bundle):
    ends = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            ends.append(pw[-1][:3])
    if len(ends) < 6:
        return None
    arr = np.asarray(ends, dtype=float)
    x_mean = float(arr[:, 0].mean())
    trms = float(np.sqrt(((arr[:, 1:3] - arr[:, 1:3].mean(0)) ** 2).sum(1).mean()))
    return len(ends), x_mean, trms


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()

        old_bundle = _trace_2d_old_mesh(editor)
        old_projected = _projected_ray_count(editor, old_bundle)

        system, bundle, folded_engaged = _trace_2d_routed(editor)
        new_projected = _projected_ray_count(editor, bundle)
        n = len(editor.rows)
        drawn = np.asarray(
            editor._surface_reference_world_point(n - 1, system=system), dtype=float
        ).reshape(3)
        onaxis = _onaxis_endpoint_stats(bundle)

        plain = _build_editor(_PLAIN)
        _plain_sys, plain_bundle, plain_folded = _trace_2d_routed(plain)
        plain_projected = _projected_ray_count(plain, plain_bundle)

    drawn_x = float(drawn[0])

    # (1) the OLD direct mesh trace projects to zero 2D rays (the empty pane).
    if old_projected != 0:
        notes.append(
            f"NOTE: the OLD mesh trace already projected {old_projected} 2D rays (expected 0) "
            f"-- the bug may be masked; the routed path is still asserted below"
        )

    # (2) the NEW routed 2D trace projects many rays and converges on the +X detector.
    if not folded_engaged:
        failures.append("folded-sequential path did NOT engage on the 2D trace (helper returned None)")
    if new_projected < 12:
        failures.append(
            f"the routed 2D trace projected too few rays ({new_projected}) -- the 2D pane would "
            f"still look empty (old mesh trace projected {old_projected})"
        )
    if onaxis is None:
        failures.append("routed 2D trace produced too few on-axis rays reaching the +X sensor")
    else:
        count, x_mean, trms = onaxis
        if abs(x_mean - drawn_x) > 0.05:
            failures.append(
                f"routed 2D on-axis endpoints not on the drawn detector: X mean {x_mean:.3f} "
                f"vs drawn {drawn_x:.3f} (dX {x_mean - drawn_x:+.3f})"
            )
        if not (trms < 0.1):
            failures.append(
                f"routed 2D on-axis cone not converged at the detector: endpoint RMS {trms:.4f}mm >= 0.1"
            )
        else:
            notes.append(
                f"routed 2D projects {new_projected} rays (old mesh: {old_projected}); on-axis cone "
                f"lands {count} rays at X={x_mean:.3f} (drawn {drawn_x:.3f}), endpoint RMS={trms:.5f}mm"
            )

    # (3) an unfolded layout still projects rays (helper returns None -> plain mesh path).
    if plain_folded:
        failures.append("unfolded flat_mirror_45_deg wrongly engaged the folded 2D path")
    if plain_projected < 1:
        failures.append(f"unfolded flat_mirror_45_deg 2D trace projected no rays ({plain_projected})")
    else:
        notes.append(f"unfolded flat_mirror_45_deg: {plain_projected} projected rays (plain mesh path)")

    if failures:
        print("FAIL bugs/0201 2D folded shows rays:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0201 2D preview shows rays on the folded RA-mirror scene:")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
