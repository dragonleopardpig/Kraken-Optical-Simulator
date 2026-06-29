"""Folded variant of the AZURE ELS-85/4.5V16K machine-vision surrogate.

This is the straight ``machine_vision_85mm_azure_datasheet_05x_20x`` layout with a
single 45-degree sequential fold mirror inserted between the object and the lens, so
the imaging lens (and the sensor behind it) sit on the REFLECTED branch of the fold.

Why a sequential ``Mirror`` row, not a promoted prism solid:
  A non-sequential promoted prism/mirror solid folds the traced RAYS in 3D but leaves
  the sequential table rows on the original straight axis -- so the lens rows stay
  unfolded and stop receiving the beam.  A sequential ``Mirror`` surface
  (``glass="MIRROR"``) folds the optical AXIS itself: KrakenOS re-orients every row
  after the mirror onto the reflected path automatically (the canonical pattern is
  ``double_mirror_fold`` / ``flat_mirror_45_deg``, where the lens follows immediately
  after the mirror).  ``tilt_x = -45`` folds the +Z object axis into +Y, so the whole
  ELS-85 surrogate -- front/rear optical vertex datums, the two ideal blackbox groups,
  the F/4.5 stop, and the image plane -- lands on the +Y reflected branch (matching the
  +Y fold of the user's imported Edmund 87391 right-angle mirror).  A headless trace
  confirms the on-axis ray reaches the sensor at the reflected image point.

Conjugate is preserved:
  At 1X the object-to-front-vertex working distance is 141.85 mm.  The fold splits that
  distance across the bend (object -> mirror  +  mirror -> front vertex == 141.85), so
  the 1X imaging conjugate is unchanged; only the path is bent 90 degrees.

STEP overlays are intentionally omitted here:
  The CAD overlay aligner seats a STEP mesh along the straight cumulative-thickness +Z
  axis (``layout_polyline_display._cad_mesh_aligned_to_optical_axis`` ends with
  ``aligned[:, 2] += target_front_z``).  It does not follow a folded polyline, so on a
  folded branch the barrel/camera STEP bodies would render DETACHED on the straight
  axis instead of on the lens.  The sequential rows -- the two optical vertex datums,
  the two blackbox groups, the stop, and the fold mirror -- already show the folded
  imaging path.  To inspect the vendor barrel STEP, open the straight
  ``Machine Vision 85 mm Azure (Datasheet 0.5X-2.0X)`` layout.  ``camera_model`` is kept
  so the image format stays camera/FOV-driven at runtime.
"""

from __future__ import annotations

import copy

from KrakenOS.common_optical_layouts import (
    machine_vision_85mm_azure_datasheet_05x_20x as base,
)

TITLE = "Machine Vision 85 mm Azure Folded (Datasheet 0.5X-2.0X)"

# Split the 1X object working distance (object -> front optical vertex == 141.85 mm)
# across the 45-degree fold.  Any split summing to OBJECT_TO_FRONT_VERTEX_1X keeps the
# 1X conjugate; this one puts most of the working distance on the object arm and folds
# the last stretch up to the lens.
FOLD_OBJECT_TO_MIRROR = 100.0
FOLD_MIRROR_TO_FRONT_VERTEX = round(
    float(base.OBJECT_TO_FRONT_VERTEX_1X) - FOLD_OBJECT_TO_MIRROR, 6
)
# A 29 mm clear aperture folded at 45 degrees needs ~29*sqrt(2) ~= 41 mm of mirror in
# the fold plane; 50 mm leaves margin.
FOLD_MIRROR_DIAMETER = 50.0
# tilt_x = -45 folds the +Z object axis up into +Y (matches the user's imported
# right-angle mirror, which reflects to +Y). The editor forces AxisMove = 2.0 on any
# Mirror row, so every row after this one re-orients onto the reflected branch.
FOLD_MIRROR_TILT_X_DEG = -45.0

# Inherit every operational default from the straight AZ85 surrogate, then drop the two
# CAD overlays that the straight-axis aligner cannot fold (see module docstring).  The
# camera MODEL is kept so the runtime image format stays camera/FOV-driven.
SETTINGS = copy.deepcopy(base.SETTINGS)
SETTINGS["lens_step_path"] = ""
SETTINGS["camera_step_path"] = ""

# Reuse the straight surrogate's optical chain verbatim (front optical vertex datum ->
# blackbox group 1 -> F/4.5 stop -> blackbox group 2 -> rear optical vertex datum ->
# image); deep-copied so a load never mutates the shared base module.
_LENS_CHAIN = copy.deepcopy(base.SURFACES[1:])

SURFACES = [
    {
        "surface": "Object",
        "name": "Object at 1X",
        "rc": 0.0,
        "thickness": FOLD_OBJECT_TO_MIRROR,
        "diameter": float(base.MAX_SENSOR_DIAMETER),
        "tilt_x": 0.0,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "AIR",
    },
    {
        "surface": "Mirror",
        "name": "Right Angle Fold Mirror",
        "rc": 0.0,
        "thickness": FOLD_MIRROR_TO_FRONT_VERTEX,
        "diameter": FOLD_MIRROR_DIAMETER,
        "tilt_x": FOLD_MIRROR_TILT_X_DEG,
        "tilt_y": 0.0,
        "tilt_z": 0.0,
        "desp_x": 0.0,
        "desp_y": 0.0,
        "desp_z": 0.0,
        "axis_move": 0.0,
        "glass": "MIRROR",
    },
    *_LENS_CHAIN,
]
