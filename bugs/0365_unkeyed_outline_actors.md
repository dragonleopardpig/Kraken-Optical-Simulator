# 0365 — Row hides left "residual aperture" rings: outline actors were unkeyed

**Flag:** 20260720_082505_845 (build e00e2c1b). **Status:** FIXED 2026-07-20 (phase-311 guard).

Hiding the Aperture Stop's row hid its FILL but left a dark outer ellipse + inner-hole dot: the
feature-edge outline actors were added with `track_row_index=None` for every NON-file-backed row
(`open3d_scene_refresh` outline add + the rays-on twins), so `_all_actor_keys_for_row` never found
them — hide-proof ghosts for every analytic row's rim (Object/Image discs included). Fix: outlines
are row-keyed unconditionally (`row_index >= 0`), rays-on twins too. Hardened in passing: the
virtual-plane markers (fill + border + arrow) were fully unkeyed — the next "residual plane"
waiting to happen — they now carry their owning row key.
