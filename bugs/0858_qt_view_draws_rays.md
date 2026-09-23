# 0858 -- the Qt 3D view draws the traced light

Follows 0857. With the optical elements drawn, the Qt view still showed no rays: glass without
light is a CAD view, not an optical one.

## What changed

`SceneViewport._draw_rays(editor, rays, bundle)` walks the model's own ray-display pipeline --
the same one `services/legacy_3d_scene.py` walks for the Tk 3D view:

| step | why it is the model's and not ours |
|---|---|
| `_iter_3d_scene_ray_records(rays, bundle)` | the record per ray: index, colour, points, terminal status |
| `_bounded_3d_ray_points_for_display(...)` | a ray that MISSES the detector must visibly miss -- bounded against the scene radius, aimed at the missed-detector target, never stopped short and never teleported |
| `_ray_vertex_display_inset(radius)` | keeps segment ends off the glass |
| `_ray_terminal_3d_style(colour, status)` | colour/opacity/width carry the terminal status: colour here is physics, not decoration |

Drawn unlit (`SetLighting(False)`): a ray is light, not a lit surface.

`show_editor_scene` now builds the preview system **once** and hands it to both the element and
ray passes -- drawn light has to belong to the drawn glass, and a second build would double the
cost of every redraw. It returns `{"elements", "rays", "bodies", "error"}`, and the status line
reads e.g. "3D view: 20 optical elements, 106 rays, 3 imported bodies."

`View -> Show Rays` (Ctrl+L, on by default) hides and shows them, as the Tk view's switch does;
a redraw honours whatever the menu currently says.

On `om05a_folded.py`: 106 rays, all `hit_detector`, from the part on the om05a stage through the
fold mirror and the lens to the sensor.

## Guard

`validate_open3d_0858_qt_view_draws_rays.py`, penta phase 637. R1 one actor per ray record,
recomputed independently through the same helpers; R2 each drawn polyline equals the model's
BOUNDED display polyline point-for-point (drawing raw ray points would pass a count check and
silently break the missed-ray invariant -- this is the check that catches it); R3 colour, opacity
and width come from the terminal style and every ray is unlit; R4 one system build per redraw;
R5 the toggle hides only the rays and a redraw honours the menu.
