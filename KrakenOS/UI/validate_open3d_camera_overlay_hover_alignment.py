#!/usr/bin/env python3
"""Display-free guard for the camera/LED STEP hover-outline alignment
(bugs/0109: "ghost highlight" / "offset highlight").

A camera STEP body is NOT moved by a translate/rotate gesture but by the
layout's image plane: ``_transformed_imported_camera_step_mesh`` aligns the
camera front face to ``image_plane_z - front_to_sensor`` (the LED to its own z).
The rendered mesh re-keys on that target, but the face-metadata cache key for
the display-only labels (camera/led/lens) was pose-blind -- so once the image
plane moved (a solve, an image-at-focus shift, a thickness edit, or a
camera/sensor reassignment) the baked face geometry stayed at the body's former
pose and the gold hover outline floated ~17 mm off the drawn body.

The fix folds ``_step_overlay_alignment_target_z(label)`` into the metadata
cache key for the image-plane-aligned overlays, so the next hover recomputes the
face geometry against the freshly-aligned mesh.

What it checks:
  A. ``_step_overlay_alignment_target_z`` returns ``image_plane_z -
     front_to_sensor`` for the camera, the led z for the led, and ``None`` for
     overlays whose pose is captured by the translate/rotate signature.
  B. Functional cache: with the image plane fixed, a second metadata read is a
     cache hit (no recompute); after the image plane MOVES, the read recomputes
     and returns geometry baked at the NEW alignment target (never the stale
     entry).
  C. Source: the metadata cache key folds ``_step_overlay_alignment_target_z``
     for the display-only labels.

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
        # image-plane / sensor inputs the camera alignment derives from
        self.image_plane_z = 700.0
        self.front_to_sensor = 11.5
        self.led_z = 40.0
        self._compute_calls = 0
        # bind the real methods under test
        self._step_overlay_alignment_target_z = types.MethodType(
            ScenePlacementMixin._step_overlay_alignment_target_z, self
        )
        self._step_overlay_face_metadata = types.MethodType(
            ScenePlacementMixin._step_overlay_face_metadata, self
        )

    # --- collaborators the metadata method touches (all stubbed cheap) ---
    def _step_path_for_label(self, label):
        return f"/tmp/{label}.step"

    def _step_overlay_stat_key(self, path):
        return ("stat", str(path))

    def _step_overlay_pose_cache_signature(self, label):
        return ()

    def _current_image_plane_z(self):
        return float(self.image_plane_z)

    def _current_camera_front_to_sensor_mm(self):
        return float(self.front_to_sensor)

    def _led_step_z_translation(self):
        return float(self.led_z)

    def _step_overlay_face_metadata_compute(self, label):
        # Bake the current alignment target so a stale cache hit is detectable.
        self._compute_calls += 1
        return {
            "label": label,
            "baked_align": self._step_overlay_alignment_target_z(label),
            "call_index": self._compute_calls,
        }


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    failures: list[str] = []

    # A) alignment-target accessor.
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
            failures.append(
                f"FAIL: {label} has no image-plane alignment target -> should be None, "
                f"got {ed._step_overlay_alignment_target_z(label)}")

    # B) functional cache behaviour.
    ed = _FakeEditor()
    first = ed._step_overlay_face_metadata("camera")
    calls_after_first = ed._compute_calls
    second = ed._step_overlay_face_metadata("camera")  # image plane unchanged
    if ed._compute_calls != calls_after_first:
        failures.append(
            "FAIL: a second camera metadata read with the image plane unchanged must "
            "be a cache hit (no recompute)")
    if second is not first:
        failures.append("FAIL: the unchanged-pose read should return the cached object")

    # Move the image plane -> the cached entry is now stale; the read must
    # recompute against the new alignment target and never return the old bake.
    ed.image_plane_z = 730.0  # +30 mm, like an image-at-focus shift / solve
    moved = ed._step_overlay_face_metadata("camera")
    if ed._compute_calls <= calls_after_first:
        failures.append(
            "FAIL: moving the image plane must invalidate the camera metadata "
            "(recompute), but no recompute happened -> stale hover outline (bugs/0109)")
    expected_moved = round(730.0 - ed.front_to_sensor, 6)
    if moved.get("baked_align") != expected_moved:
        failures.append(
            f"FAIL: after the image plane moved, the metadata must be baked at the new "
            f"alignment target ({expected_moved}), got {moved.get('baked_align')}")
    if moved.get("baked_align") == first.get("baked_align"):
        failures.append(
            "FAIL: the post-move metadata must differ from the pre-move bake "
            "(the stale entry must not be reused)")

    # Moving back returns to the original target (and may reuse the warm entry).
    ed.image_plane_z = 700.0
    back = ed._step_overlay_face_metadata("camera")
    if back.get("baked_align") != expected_cam:
        failures.append(
            f"FAIL: restoring the image plane must bake at the original target "
            f"({expected_cam}), got {back.get('baked_align')}")

    # C) source check: the cache key folds the alignment target for display-only.
    meta_src = inspect.getsource(ScenePlacementMixin._step_overlay_face_metadata)
    if "_step_overlay_alignment_target_z" not in meta_src:
        failures.append(
            "FAIL: _step_overlay_face_metadata must fold _step_overlay_alignment_target_z "
            "into the cache key for the image-plane-aligned display-only overlays")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] camera/LED STEP hover-outline alignment tracks the image plane")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] camera/LED STEP face metadata re-keys on its image-plane alignment "
          "target -> the gold hover outline tracks the rendered body")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
