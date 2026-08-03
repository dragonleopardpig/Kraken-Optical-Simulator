# 0522 — compulsory FOV-corner probe rays

## Request

User (2026-08-03): "the launch ray matrix, can make compulsory to launch ray from the very
edge or corner so that user can immediately know anything in between potentially clip the
rays?"

## Gap

With `field_count = 1` (the common setting on the machine-vision scenes) the finite-object
world launch sampled ONLY the FOV centre: an obstruction clipping the field EDGE was
invisible until the user manually raised the field count. (The pupil rim itself was already
sampled — the cone/fan samplers reach the full launch radius.)

## Implementation

`_build_world_bundles_from_pupil_points`: when a rectangular imaging bound is active
(`_coupled_imaging_launch_half_extents`), append a skeletal probe fan — chief + 4
pupil-rim rays — from each FOV corner the field grid missed (~20 extra rays). Any clip
between the object corners and the sensor now shows immediately as missing corner rays.
The main fans keep the literal "Ray Count = N per field" contract (0095) untouched; scenes
without the rectangular bound (penta, plain sequential) are byte-identical. A field grid
with `count > 1` already reaches the corners (linspace endpoints), so probes only fill the
missing ones.

## Guard

`validate_open3d_0522_fov_corner_probes.py` (penta phase 420): on the AZ85 scene the
preview bundle carries launch origins at all four FOV corners; a corner-blocking obstacle
loses those rays (the visibility property the user asked for) — checked display-free via
ray-path launch origins.
