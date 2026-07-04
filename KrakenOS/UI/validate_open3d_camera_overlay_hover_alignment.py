#!/usr/bin/env python3
"""Display-free guard for the camera/LED STEP face-metadata caching cost
(bugs/0111, which reverts bugs/0109).

A camera STEP body is positioned by the layout's image plane
(``_transformed_imported_camera_step_mesh`` aligns its front face to
``image_plane_z - front_to_sensor``). bugs/0109 folded that alignment target into
the face-metadata cache key so the gold hover outline would track the body after
an image-plane move. That was a mistake: baking the display-only camera/led
metadata is NOT subsecond -- it is the full planar-clustering + affine-fit +
snap-STL pipeline, ~18-35 s for the 228k-cell camera body -- so re-keying made the
bake re-run whenever the image plane moved (a solve / image-at-focus shift /
thickness edit) OR on a deselect/refresh, freezing the UI for ~18 s.

The fix keeps the display-only labels POSE-BLIND, so the metadata is baked at most
once per session (the proven pre-0109, freeze-free behaviour). The cosmetic
hover-outline offset 0109 chased must be fixed without re-baking (apply the axial
alignment delta to the cached geometry on read) -- that is tracked separately.

What it checks:
  A. ``_step_overlay_alignment_target_z`` still resolves the camera/led axial
     targets (kept for the future delta-shift fix; ``None`` elsewhere).
  B. Functional cache: an image-plane MOVE does NOT recompute the camera metadata
     (it stays a cache hit) -- the freeze-free contract.
  C. Source: the cache key for the display-only labels does NOT fold the alignment
     target (it would re-trigger the 18-35 s bake), and the bugs/0111 rationale is
     present.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_overlay_hover_alignment

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


class _FakeEditor:
    """Borrows the real unbound metadata methods, stubbing the cheap
    collaborators so the cache-key logic runs without a Tk/VTK editor."""

    def __init__(self):
        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        self._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC = (
            ScenePlacementMixin._DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC
        )
        self.image_plane_z = 700.0
        self.front_to_sensor = 11.5
        self.led_z = 40.0
        self._compute_calls = 0
        self._step_overlay_alignment_target_z = types.MethodType(
            ScenePlacementMixin._step_overlay_alignment_target_z, self
        )
        self._step_overlay_face_metadata = types.MethodType(
            ScenePlacementMixin._step_overlay_face_metadata, self
        )

    def _step_path_for_label(self, label):
        return f"/tmp/{label}.step"

    def _step_overlay_stat_key(self, path):
        return ("stat", str(path))

    def _step_overlay_pose_cache_signature(self, label):
        return ()

    def _current_image_plane_z(self):
        return float(self.image_plane_z)

    def _camera_track_image_plane_z(self):
        # bugs/0220: the camera placement tracks the paraxial focus only on a folded overshoot;
        # this unfolded fake has no fold, so it tracks the prescription Image-row plane.
        return float(self.image_plane_z)

    def _current_camera_front_to_sensor_mm(self):
        return float(self.front_to_sensor)

    def _led_step_z_translation(self):
        return float(self.led_z)

    def _step_overlay_face_metadata_compute(self, label):
        # Stand in for the real ~18-35 s bake; count calls so a recompute is visible.
        self._compute_calls += 1
        return {
            "label": label,
            "baked_align": self._step_overlay_alignment_target_z(label),
            "call_index": self._compute_calls,
        }


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    failures: list[str] = []

    # A) alignment-target accessor still resolves (kept for the delta-shift fix).
    ed = _FakeEditor()
    cam_target = ed._step_overlay_alignment_target_z("camera")
    expected_cam = round(ed.image_plane_z - ed.front_to_sensor, 6)
    if cam_target != expected_cam:
        failures.append(
            f"FAIL: camera alignment target should be image_plane_z - front_to_sensor "
            f"({expected_cam}), got {cam_target}")
    if ed._step_overlay_alignment_target_z("led") != round(ed.led_z, 6):
        failures.append(
            f"FAIL: led alignment target should be the led z ({round(ed.led_z, 6)}), "
            f"got {ed._step_overlay_alignment_target_z('led')}")
    for label in ("lens", "optical", "bogus"):
        if ed._step_overlay_alignment_target_z(label) is not None:
            failures.append(f"FAIL: {label} should have no image-plane alignment target (None)")

    # B) freeze-free contract: an image-plane MOVE must NOT recompute the camera
    #    metadata -- the expensive bake stays a cache hit (pose-blind).
    ed = _FakeEditor()
    first = ed._step_overlay_face_metadata("camera")
    calls_after_first = ed._compute_calls
    ed._step_overlay_face_metadata("camera")  # unchanged -> hit
    if ed._compute_calls != calls_after_first:
        failures.append("FAIL: an unchanged-pose camera metadata read must be a cache hit")
    ed.image_plane_z = 730.0  # an image-at-focus shift / solve moves the image plane
    moved = ed._step_overlay_face_metadata("camera")
    if ed._compute_calls != calls_after_first:
        failures.append(
            "FAIL: moving the image plane must NOT recompute the camera face metadata "
            "(bugs/0111: re-baking the 18-35 s display-only metadata froze the UI on "
            "image-plane moves / deselect)")
    if moved is not first:
        failures.append("FAIL: the camera metadata must stay the one cached (pose-blind) object")

    # An analytic label still re-keys on its pose signature (only display-only is blind).
    # (no further assertion needed; covered by the pose-signature path.)

    # C) source: the cache key must NOT fold the alignment target for display-only
    #    labels, and the bugs/0111 rationale must be present.
    meta_src = inspect.getsource(ScenePlacementMixin._step_overlay_face_metadata)
    display_only_block = meta_src.split("_DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC", 1)[-1]
    if 'cache_key + (("align_z"' in meta_src or "+ ((\"align_z\"" in meta_src:
        failures.append(
            "FAIL: _step_overlay_face_metadata must NOT fold the alignment target into the "
            "display-only cache key (it re-triggers the 18-35 s bake -> freeze)")
    if "bugs/0111" not in meta_src:
        failures.append("FAIL: the bugs/0111 pose-blind rationale is missing from the source")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] camera/LED STEP face metadata stays pose-blind cached (freeze-free)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] camera/LED STEP face metadata is pose-blind cached -> no 18-35 s re-bake "
          "on an image-plane move or deselect")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
