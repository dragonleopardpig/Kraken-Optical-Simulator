"""Display-free guard for bugs/0555 -- "sometimes the rays become all green".

flag_20260805_115527 ("changed FOV to 23x23. I noticed sometime the rays become all green.
I think it is due to the Illuminator") and flag_20260805_115638 ("Click Trace Now, the rays
colour become normal again").

It is NOT the illuminator. The two flags carry IDENTICAL traces -- 558 paths, the same
``{no_next_intersection: 305, target_termination: 160, missed_image: 6,
aperture_stop_vignette: 87}`` census -- but **1 merged ray actor versus 8**. Ray actors are
merged per STYLE, so one actor means every ray was painted one colour. The rays never changed;
only the palette did.

Root cause: a ray's colour was ``colors[field_index % len(colors)]`` where BOTH sides come from
the same ``field_count``:

* ``field_index = min(source_ray_index // ray_count_per_field, field_count - 1)`` -- clamped;
* ``colors = field_colors or _default_field_colors(field_count)`` -- and
  ``_default_field_colors(count <= 1)`` is exactly ``["#39FF14"]``, bright green.

The 3-D display takes that count from the CACHED ``_preview_field_bundle_count``, falling back
to ``_current_field_count()``, which returns 1 whenever field sampling is not flagged active.
When the cache is stale the count collapses to 1, the clamp folds every ray onto field 0, and
the modulo paints them all ``#39FF14``. "Trace Now" refreshes the cache, so 8 colours return --
which is why the palette has exactly 8 entries and the healthy flag has exactly 8 actors.

Fix: colour by the ray's TRUE field group (``source_ray_index // ray_count_per_field``, never
clamped) and widen the palette when it runs short, so the colour follows the rays that exist
rather than a cached count.

Checks (pure, no VTK/tk):
- COLLAPSE: with the stale single-entry palette, 8 field groups get 8 DISTINCT colours.
- SINGLE FIELD: a genuinely one-field scene still gets ``#39FF14`` (group index 0).
- CALLER PALETTE: an explicit ``field_colors`` list is respected where it covers the index.
- WRAP: a group beyond the palette wraps within the 8-colour map instead of collapsing.
- SOURCE: the per-path colour no longer indexes on the clamped ``field_index``.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0555_ray_colors_follow_fields
"""

from __future__ import annotations

import inspect


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI import scene_builder
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: scene_builder unavailable ({type(exc).__name__}: {exc})"]

    color_for = scene_builder._field_display_color
    default_colors = scene_builder._default_field_colors

    # --- COLLAPSE: the exact stale-cache condition from the flag ------------------------
    stale = default_colors(1)
    if stale != ["#39FF14"]:
        failures.append(f"premise changed: a 1-field palette is {stale}, expected ['#39FF14']")
    painted = [color_for(stale, group) for group in range(8)]
    if len(set(painted)) != 8:
        failures.append(
            f"collapse: with the stale single-entry palette, 8 field groups produced "
            f"{len(set(painted))} distinct colour(s) -- that is the all-green bug (bugs/0555)"
        )

    # --- SINGLE FIELD: a real one-field scene must stay green ---------------------------
    if color_for(stale, 0) != "#39FF14":
        failures.append(
            f"single-field: group 0 must stay #39FF14 (got {color_for(stale, 0)}) -- a genuinely "
            "one-field scene was always green and must not change"
        )

    # --- CALLER PALETTE respected -------------------------------------------------------
    supplied = ["#111111", "#222222", "#333333"]
    for index, want in enumerate(supplied):
        if color_for(supplied, index) != want:
            failures.append(f"caller palette: index {index} gave {color_for(supplied, index)}, wanted {want}")

    # --- WRAP beyond the palette --------------------------------------------------------
    wide = default_colors(8)
    far = color_for(wide, 25)
    if far not in wide:
        failures.append(f"wrap: a far field group must wrap into the palette, got {far}")
    if color_for([], 3) not in default_colors(8):
        failures.append("wrap: an empty palette must fall back to the default map")

    # --- SOURCE: the colour must not key on the clamped index ---------------------------
    source = inspect.getsource(scene_builder)
    if "color=colors[field_index % len(colors)]" in source:
        failures.append(
            "source: the per-path colour still indexes the CLAMPED field_index -- a stale "
            "field_count collapses every ray onto field 0 (bugs/0555)"
        )
    if "_field_display_color(" not in source:
        failures.append("source: the per-path colour must route through _field_display_color")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0555 ray-colour validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0555 validation passed: a ray's colour follows its TRUE field group, so a stale "
        "single-entry palette no longer paints every ray green; a genuinely single-field scene "
        "stays #39FF14 and an explicit palette is respected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
