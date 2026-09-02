"""Guard for bugs/0680 -- ADDITIVE scene sources keep the imaging launch.

User architecture (om05a): "it is symmetry 2-sided ... one FOV is looking at two
object plane". The imaging chain covers ONE device face; the opposite face's light
enters through its own prism train. Before 0680, ANY physical scene source
short-circuited the preview to source-driven tracing -- adding the face-B emitter
killed the imaging chain outright (this masqueraded for half a day as "the B prisms
fold the chain", until corrected accounting showed chain rays carry
source_id='source:0').

The contract:
  1  a spec with ``additive: True`` never short-circuits `_collect_scene_sources`
     -- the imaging reference stays sources[0];
  2  `_build_scene_source_bundles` (the replace-the-launch path) excludes it;
  3  the preview keeper holds BOTH families: the imaging chain byte-identical to
     the source-free scene, plus the additive rays appended after it;
  4  ``aim_x/y/z`` re-centres every sampled cone on one world aim point (the
     apparent entrance pupil) -- launch lines converge there;
  5  ``mirror_launch_plane_z`` replaces model sampling with the stashed imaging
     launch reflected through the plane (z -> 2*zp - z, n -> -n), bounded to the
     physical face (radius_x/radius_y).

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0680_additive_imaging_source
"""

from __future__ import annotations

import numpy as np

ADDITIVE_SPEC = {
    "source_id": "source:second_arm",
    "name": "Second arm",
    "model": "Random rectangle source",
    "role": "illumination",
    "physical": True,
    "enabled": True,
    "additive": True,
    "source_x": 0.0, "source_y": 0.0, "source_z": -40.0,
    "source_l": 0.0, "source_m": 0.0, "source_n": -1.0,
    "radius_x": 5.0, "radius_y": 0.5, "radius": 5.0,
    "cone_deg": 3.0, "ray_count": 60, "power": 1.0, "wavelength": 0.55, "seed": 3,
}


def _fresh_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    return editor


def _chain_signature(bundle) -> list:
    sig = []
    for rp in (getattr(bundle, "ray_paths", None) or []):
        if str(getattr(rp, "source_id", "") or "").startswith("source:second_arm"):
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim == 2 and np.all(np.isfinite(p[-1])):
            sig.append(np.round(p[-1], 6).tolist())
    return sig


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_additive_to_imaging

    editor = _fresh_editor()
    try:
        # baseline: the stock layout, no scene sources
        try:
            editor._preview_trace_deferred_until_requested = False
        except Exception:
            pass
        _s, _r, baseline_bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        baseline_sig = _chain_signature(baseline_bundle)
        ok(len(baseline_sig) > 0, f"S0: the stock scene traces a chain ({len(baseline_sig)} paths)")

        editor.layout_scene_source_specs = [dict(ADDITIVE_SPEC)]
        specs = editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
        ok(
            scene_source_spec_is_additive_to_imaging(specs[0]),
            "C1: `additive: True` survives spec normalization and the predicate sees it",
        )
        sources = editor._collect_scene_sources(wavelength=0.55)
        ok(
            len(sources) >= 2 and str(sources[0].source_id) == "source:0"
            and any(str(s.source_id) == "source:second_arm" for s in sources[1:]),
            f"C2: no short-circuit -- imaging reference stays sources[0] "
            f"({[str(s.source_id) for s in sources]})",
        )
        replace_bundles, _rs = editor._build_scene_source_bundles(0.55)
        ok(
            len(replace_bundles) == 0,
            f"C3: the replace-the-launch path excludes the additive source ({len(replace_bundles)} bundles)",
        )
        add_bundles, add_sources = editor._build_additive_imaging_source_bundles(0.55)
        ok(
            len(add_bundles) == 1 and len(np.asarray(add_bundles[0][0])) == 60,
            f"C4: the additive builder samples the source's own model "
            f"({len(add_bundles)} bundles, {len(np.asarray(add_bundles[0][0])) if add_bundles else 0} rays)",
        )

        _s, _r, mixed_bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
        mixed_sig = _chain_signature(mixed_bundle)
        additive_paths = sum(
            1 for rp in (mixed_bundle.ray_paths or [])
            if str(getattr(rp, "source_id", "") or "") == "source:second_arm"
        )
        ok(
            mixed_sig == baseline_sig,
            f"C5: the imaging chain is BYTE-IDENTICAL with the additive source present "
            f"({len(mixed_sig)} vs {len(baseline_sig)} paths)",
        )
        ok(
            additive_paths > 0,
            f"C6: the additive rays ride the SAME live bundle ({additive_paths} paths)",
        )

        # aim point: launch lines converge at the requested world point
        aimed = {**ADDITIVE_SPEC, "aim_x": 3.0, "aim_y": -2.0, "aim_z": 60.0, "cone_deg": 0.0}
        editor.layout_scene_source_specs = [aimed]
        aim_bundles, _as = editor._build_additive_imaging_source_bundles(0.55)
        converge = False
        if aim_bundles:
            x, y, z, l, m, n = (np.asarray(part, dtype=float) for part in aim_bundles[0])
            starts = np.column_stack((x, y, z))
            dirs = np.column_stack((l, m, n))
            target = np.array([3.0, -2.0, 60.0])
            t = ((target[None, :] - starts) * dirs).sum(axis=1)
            miss = np.linalg.norm(starts + t[:, None] * dirs - target[None, :], axis=1)
            converge = bool(np.max(miss) < 1e-6)
        ok(
            converge,
            "C7: aim_x/y/z re-centres every launch on the world aim point (zero-cone rays hit it exactly)",
        )

        # mirrored launch: reflection of the stashed imaging bundles, face-bounded
        # bugs/0687 split the keys: mirror_bound_x/y are the LAUNCH bounds
        # (radius_x/y only size the glyph); bugs/0696 keeps that contract.
        mirrored = {**ADDITIVE_SPEC, "mirror_launch_plane_z": -10.0,
                    "mirror_bound_x": 4.0, "mirror_bound_y": 0.5}
        editor.layout_scene_source_specs = [mirrored]
        stash = [(
            np.array([0.0, 0.2, 8.0]),   # x: inside bound
            np.array([0.0, 0.2, 0.9]),   # y: 0.9 exceeds radius_y for the last ray
            np.array([1.0, 1.0, 1.0]),
            np.array([0.0, 0.1, 0.0]),
            np.array([0.0, 0.0, 0.1]),
            np.array([1.0, 1.0, 1.0]),
        )]
        # bugs/0696: the mirror is INLINE now -- `_trace_preview_bundles` mirrors
        # each imaging call's OWN bundles via `_inline_mirrored_additive_bundles`
        # (the post-hoc stash mirror reflected a stale pass: 19.2 mm faceB defocus).
        mir_bundles, _ms = editor._inline_mirrored_additive_bundles(stash, 0.55)
        mirrored_ok = False
        if mir_bundles:
            x, y, z, l, m, n = (np.asarray(part, dtype=float) for part in mir_bundles[0])
            mirrored_ok = (
                len(x) == 2  # ray 3 launches at x=8, y=0.9 -- off the 4 x 0.5 face
                and np.allclose(z, 2.0 * -10.0 - 1.0)
                and np.allclose(n, -1.0)
                and np.all(np.abs(x) <= 4.0 + 1e-9)
                and np.all(np.abs(y) <= 0.5 + 1e-9)
            )
        ok(
            mirrored_ok,
            f"C8: the INLINE mirror reflects the imaging call's own bundles (z -> 2*zp - z, "
            f"n -> -n) and drops launch points off the physical face "
            f"({len(np.asarray(mir_bundles[0][0])) if mir_bundles else 0} of 3 kept)",
        )
        legacy_bundles, _ls = editor._build_additive_imaging_source_bundles(0.55)
        ok(
            not legacy_bundles,
            f"C8b: the additive-append builder SKIPS mirror specs (inline handles them; "
            f"no double-trace) ({len(legacy_bundles)} bundles)",
        )
    finally:
        try:
            editor.destroy()
        except Exception:
            pass

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("additive imaging source validation PASSED")
        return 0
    print("additive imaging source validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
