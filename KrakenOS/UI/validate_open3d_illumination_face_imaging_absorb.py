"""Display-free guard for bugs/0273: an illumination-marked CAD/STL face ABSORBS imaging rays.

flag_20260709_075456_691 (part 2): a beam-splitter face promoted to an Illumination Source still showed
its phantom Image Plane + detector on the IMAGING reflecting arm. Root cause: the "Illumination Source"
label binds a scene-level ``SceneSource3D`` marker to the face (bugs/0264/0268), DISJOINT from the
``OpticalSolidFaces`` face-function metadata -- so the marked face KEPT its beam-splitter optical behaviour
in the imaging trace, and its reflection branch spawned a branch detector/image plane (bugs/0088 row-base
100000). The user's directive: the reflection-arm sensor/image plane is dropped only when the face is
Absorption; an Illumination face is the opaque LED emitter plate, so it should drop the same way.

The fix models the physics (display follows the engine): the marked face IS backed by the opaque LED
plate, so imaging rays hitting it are BLOCKED. The build resolves illumination-marked faces onto
``surface.OpticalSolidFaceIlluminationBlock``; ``KrakenSys.__OpticalSolidFaceInteraction`` forces
absorption there; the absorbed reflection leaf then feeds the existing bugs/0108 chain
(``_leaf_fully_absorbed`` -> ``derive_branch_detectors`` drops the phantom detector). The ISOLATED
illumination-emission pass (bugs/0272) must NOT self-absorb at launch, so a system-level flag
``_suppress_illumination_face_absorption`` disables the hook while emitting.

Two display-free parts:

* WIRING (source inspection, always runs) -- the cache signature keys on the new spec (without it, marking a
  face never invalidates the ``build_system`` cache and the fix silently no-ops, like bugs/0267); the
  KrakenSys interaction hook keys on the illumination block AND respects the emission-suppress flag; the
  emission overlay compute sets the suppress flag around its trace.
* BINDING (real promoted-prism STEP fixture; SKIPs when the STEP is not checked out) -- a real marked face
  (1) lands ``illumination_block_face_ids`` on the row spec, (2) stashes
  ``surface.OpticalSolidFaceIlluminationBlock``, (3) forces absorption in the imaging trace while (3b) an
  unmarked reflecting face does NOT, (4) is NOT absorbed once the emission-suppress flag is set, (5) yields a
  real ``absorb`` terminal event so (6) ``derive_branch_detectors`` drops the reflection-arm detector, and
  (7) the isolated emission still floods OUT of the solid (bugs/0272 not regressed).
"""

from __future__ import annotations

import inspect
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _check_wiring(failures: list[str]) -> None:
    # (W1) the root-cause cache guard: _row_specs_signature MUST key on illumination_block_face_ids, else
    # marking a face leaves the signature unchanged and build_system returns a STALE system without the
    # absorb block (the same cache-fingerprint footgun as bugs/0267).
    try:
        from KrakenOS.UI.services import row_spec_contracts

        sig_src = inspect.getsource(row_spec_contracts._row_specs_signature)
        if "illumination_block_face_ids" not in sig_src:
            failures.append(
                "WIRING: _row_specs_signature does not key on 'illumination_block_face_ids' -- marking a "
                "face will not invalidate the build_system cache (stale-cache no-op, bugs/0267 class)"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"WIRING: could not read _row_specs_signature ({exc!r})")

    # (W2) the imaging absorb hook: __OpticalSolidFaceInteraction keys on the illumination block AND is
    # gated by the emission-suppress flag.
    try:
        from KrakenOS.KrakenSys import system as kraken_system

        hook_src = inspect.getsource(getattr(kraken_system, "_system__OpticalSolidFaceInteraction"))
        if "OpticalSolidFaceIlluminationBlock" not in hook_src:
            failures.append(
                "WIRING: __OpticalSolidFaceInteraction no longer reads OpticalSolidFaceIlluminationBlock "
                "(the imaging absorb hook is gone)"
            )
        if "_suppress_illumination_face_absorption" not in hook_src:
            failures.append(
                "WIRING: __OpticalSolidFaceInteraction no longer honours _suppress_illumination_face_absorption "
                "(the emission pass would self-absorb at launch, bugs/0272 regression)"
            )
        if "force_absorption" not in hook_src:
            failures.append("WIRING: __OpticalSolidFaceInteraction no longer sets force_absorption")
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"WIRING: could not read __OpticalSolidFaceInteraction ({exc!r})")

    # (W3) the emission overlay compute sets the suppress flag around its isolated trace.
    try:
        from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

        overlay_src = inspect.getsource(
            ThreeDSceneToolsMixin._compute_illumination_marker_rays_overlay_spec
        )
        if "_suppress_illumination_face_absorption" not in overlay_src:
            failures.append(
                "WIRING: the emission overlay compute no longer sets _suppress_illumination_face_absorption "
                "(the emission flood would self-absorb, bugs/0272 regression)"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"WIRING: could not read _compute_illumination_marker_rays_overlay_spec ({exc!r})")


def _check_binding(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import (
        KrakenLayoutEditor,
        OPTICAL_SOLID_FACES_ADVANCED_ATTR,
        SurfaceRow,
        optical_solid_face_world_records,
    )
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        notes.append("SKIP binding: PRISM_42779_STEP fixture not checked out")
        return

    le.CAD_CACHE_DIR = Path("/tmp/kraken-open3d-illum-face-absorb-cache/cad")
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical", insert_at=1, open_face_editor=False, clear_overlay=True
        )
        if promoted is None:
            failures.append("BINDING: could not promote the prism STEP to an optical solid row")
            return
        row_index = int(promoted["row_index"])

        _row, _path, metadata = app._optical_solid_face_metadata_for_row(row_index)
        temp_row = SurfaceRow(**asdict(app.rows[row_index]))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        faces = optical_solid_face_world_records(
            temp_row, app._stl_row_z_station(row_index), assigned_only=False
        )
        if not faces:
            failures.append("BINDING: promoted optical solid exposed no faces")
            return
        # A few reflecting faces make the isolated emission genuinely non-sequential; a DIFFERENT face is the
        # illumination source, aimed INTO the solid (the LED plate on the +X face of the BS cube).
        for f in faces[:3]:
            app.assign_optical_solid_face_function(
                row_index, str(f.get("face_id", "") or ""), "Full Reflecting", direct_context=True
            )
        illum_face_id = str(faces[-1].get("face_id", "") or "").strip()
        other_face_id = str(faces[0].get("face_id", "") or "").strip()
        app.assign_optical_solid_face_function(row_index, illum_face_id, "Uncoated", direct_context=True)
        if not app.create_illumination_source_at_face(row_index, face_id=illum_face_id, aim="inward"):
            failures.append("BINDING: create_illumination_source_at_face returned no source id")
            return

        # (1) the build-side resolver stashes the marked face on the row spec (drives the cache signature).
        specs = app._serializable_row_specs()
        block = specs[row_index].get("illumination_block_face_ids")
        if not block or illum_face_id not in block:
            failures.append(
                f"BINDING (1): row spec missing illumination_block_face_ids: {block!r} (want {illum_face_id})"
            )

        system = app.build_system()

        # (2) build stashes the surface attribute (a fresh build, because the signature now keys on the spec).
        illum_block = getattr(system.SDT[row_index], "OpticalSolidFaceIlluminationBlock", None)
        if not illum_block or illum_face_id not in illum_block:
            failures.append(
                f"BINDING (2): surface.OpticalSolidFaceIlluminationBlock missing the marked face: {illum_block!r}"
            )

        interact = system._system__OpticalSolidFaceInteraction
        marked = next(f for f in faces if str(f.get("face_id", "")).strip() == illum_face_id)
        pt = np.asarray(marked["centroid_world"], dtype=float)
        nrm = np.asarray(marked.get("normal_world", (0.0, 0.0, 1.0)), dtype=float)

        # (3) the marked face forces absorption in the IMAGING trace.
        ov = interact(row_index, pt, nrm, {"face_id": illum_face_id})
        if not (isinstance(ov, dict) and ov.get("force_absorption") is True):
            failures.append(f"BINDING (3): the marked face did not force_absorption: {ov!r}")

        # (3b) an unmarked (reflecting) face is NOT absorbed by THIS hook.
        other = next(f for f in faces if str(f.get("face_id", "")).strip() == other_face_id)
        ov_other = interact(
            row_index,
            np.asarray(other["centroid_world"], dtype=float),
            np.asarray(other.get("normal_world", (0, 0, 1)), dtype=float),
            {"face_id": other_face_id},
        )
        if (
            isinstance(ov_other, dict)
            and ov_other.get("force_absorption") is True
            and illum_block
            and other_face_id not in illum_block
        ):
            failures.append(f"BINDING (3b): an unmarked face was wrongly force-absorbed: {ov_other!r}")

        # (4) the emission-suppress flag disables the hook (the emission pass must flood, not self-absorb).
        system._suppress_illumination_face_absorption = True
        ov_sup = interact(row_index, pt, nrm, {"face_id": illum_face_id})
        system._suppress_illumination_face_absorption = False
        if isinstance(ov_sup, dict) and ov_sup.get("force_absorption") is True:
            failures.append(
                f"BINDING (4): the emission-suppress flag failed -- marked face still absorbed while emitting: {ov_sup!r}"
            )

        # (5) force_absorption yields a REAL absorb terminal event (the same one Absorber/Mechanical emits).
        term = system._system__NsTraceTerminalEvent(
            row_index, {"face_id": illum_face_id, "force_absorption": True}
        )
        term_reason = ""
        if isinstance(term, dict):
            term_reason = str(
                term.get("interaction_type") or term.get("transition") or term.get("kind") or ""
            )
        if "absorb" not in term_reason.lower():
            failures.append(
                f"BINDING (5): force_absorption did not produce an absorb terminal event: {term!r}"
            )
            term_reason = "absorbed"

        # (6) END-TO-END: a reflection leaf that dies 'absorbed' at this face yields NO branch detector, so
        #     the phantom Image Plane/detector the user reported is dropped (bugs/0108 chain). The transmit
        #     leaf reaches the sequential Image, so the whole scene collapses to it -- 0 branch detectors.
        from KrakenOS.UI.services.branch_detectors import derive_branch_detectors
        from KrakenOS.UI.scene_geometry import RayPath3D, RayEvent3D

        reflect_focus = pt + nrm * 40.0
        reflect_leaf: list = []
        for kk in range(3):
            origin = reflect_focus + np.asarray((float(kk - 1) * 3.0, -55.0, 0.0), dtype=float)
            direction = reflect_focus - origin
            direction = direction / np.linalg.norm(direction)
            pts = np.vstack((origin - direction * 5.0, origin, origin + direction * 300.0))
            reflect_leaf.append(
                RayPath3D(
                    branch_path="S1:BS/reflect",
                    reaches_image=False,
                    points_world=pts,
                    events=[RayEvent3D(event_kind="terminal", termination_reason=term_reason)],
                )
            )
        transmit_leaf = [
            RayPath3D(
                branch_path="S1:BS/transmit",
                reaches_image=True,
                points_world=np.asarray([[0.0, y, 0.0], [0.0, y * 0.2, 120.0], [0.0, 0.0, 200.0]], dtype=float),
            )
            for y in (-2.0, 0.0, 2.0)
        ]
        dets = derive_branch_detectors(
            transmit_leaf + reflect_leaf, existing_targets=[], scene_radius=80.0
        )
        if any("reflect" in d.branch_path for d in dets):
            failures.append(
                "BINDING (6): the absorbed illumination face still spawned a reflection branch "
                f"detector/image plane: {[d.branch_path for d in dets]}"
            )

        # sanity: WITHOUT the absorb (reflection leaf reaches its own focus), the reflection arm DOES earn a
        # detector -- proving check (6) is the absorb dropping it, not the harness always returning 0.
        reflect_live: list = []
        for kk in range(3):
            origin = reflect_focus + np.asarray((float(kk - 1) * 3.0, -55.0, 0.0), dtype=float)
            direction = reflect_focus - origin
            direction = direction / np.linalg.norm(direction)
            pts = np.vstack((origin - direction * 5.0, origin, origin + direction * 300.0))
            reflect_live.append(
                RayPath3D(branch_path="S1:BS/reflect", reaches_image=False, points_world=pts)
            )
        live_dets = derive_branch_detectors(
            transmit_leaf + reflect_live, existing_targets=[], scene_radius=80.0
        )
        if not any("reflect" in d.branch_path for d in live_dets):
            failures.append(
                "BINDING (6-control): a LIVE (unabsorbed) reflection arm produced no branch detector -- "
                "the drop test in (6) is vacuous"
            )

        # (7) the isolated EMISSION overlay STILL floods OUT of the solid (bugs/0272 intact, suppression works).
        spec = app.illumination_marker_rays_overlay_spec(system, None)
        if not spec or int(spec.get("drawn", 0)) < 1:
            failures.append(
                "BINDING (7): emission overlay produced no drawable rays -- self-absorbed at launch? (bugs/0272 regression)"
            )
        else:
            face_pts = np.asarray([f["centroid_world"] for f in faces], dtype=float)
            solid_diag = float(np.linalg.norm(face_pts.max(axis=0) - face_pts.min(axis=0)))
            drawn_pts = np.asarray(spec.get("points"), dtype=float)
            drawn_diag = (
                float(np.linalg.norm(drawn_pts.max(axis=0) - drawn_pts.min(axis=0)))
                if drawn_pts.size
                else 0.0
            )
            if drawn_diag <= solid_diag + 20.0:
                failures.append(
                    f"BINDING (7): emission did not exit the solid: drawn {drawn_diag:.1f} vs solid {solid_diag:.1f} (bugs/0272 regression)"
                )
            elif not failures:
                notes.append(
                    f"binding OK: marked face {illum_face_id} forces absorption in imaging (reflection arm "
                    f"detector dropped), is suppressed for emission, and the emission still exits the solid "
                    f"(drawn span {drawn_diag:.0f} mm >> solid {solid_diag:.0f} mm, {spec['drawn']} rays)"
                )
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_wiring(failures)
    _check_binding(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] bugs/0273 illumination-face imaging absorb")
        return 1
    print("[PASS] illumination-marked face absorbs imaging rays (reflection-arm detector dropped); emission intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
