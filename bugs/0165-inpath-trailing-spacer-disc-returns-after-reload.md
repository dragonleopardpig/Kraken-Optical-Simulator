# 0165 — Open 3D: the in-path trailing-spacer "big circle" returns after a save/reload (recurrence of 0093)

## Symptom (user's words)

`attachment/recorded_bug_repros/flag_20260626_163301_153` ("Big disc."), layout
`machine_vision_150mm_GN.py`:

> there is a big circle between the LED and the Imaging Lens.

A large Ø78 flat disc sits on the optical axis at `z = 270.67` — the back/transmit
face of the promoted beam-splitter solid. The recorder pins it on **row 2**:
`row_actor_bounds["2"] = [-39, 39, -39, 39, 270.6708, 270.6708]` (round Ø78, zero
z-thickness). The user later confirmed: *"I clicked on the disc, it is S2 in the
right browser panel, so it appear after BS promoted?"* — the disc is **pickable**
and selects as **S2**.

## This is a recurrence of bugs/0093

bugs/0093 already suppressed exactly this "big circle": the in-path promote
(bugs/0079) inserts a trailing AIR **gap-carrier** row right after the promoted
solid (`step_overlay_promotion.py` → `spacer.advanced = {"InPathTrailingSpacer": True}`).
It carries the solid's large diameter so the trace never clips the converging beam,
but it is a bookkeeping gap, **not** a physical surface. 0093 flags it and the
display skips its clear-aperture disc (`_iter_3d_optical_surface_meshes`) and its
surface ring/curve (`_build_sequential_surface_curves` / `_build_folded_surface_curves`),
all gated by `_is_inpath_trailing_spacer_row(row)` → `row.advanced.get("InPathTrailingSpacer")`.

## Root cause — the flag is stripped on save/reload

The 0093 fix only ever lived in **memory**: the live promote sets
`spacer.advanced["InPathTrailingSpacer"] = True` and the row keeps it for the rest
of that session. But when the layout is **saved to a `.py` and reloaded** (this
scene was), every surface's `advanced` dict is rebuilt through an **allowlist**:

  * `_advanced_surface_attrs_from_spec(spec)` (advanced_surface_attrs.py) keeps a
    key only if `_canonical_advanced_surface_attr(key)` resolves it against
    `ADVANCED_SURFACE_ATTR_NAMES` (the union of `ADVANCED_SURFACE_FIELD_GROUPS`);
  * `_row_from_surface` (layout_import_export.py) rebuilds `advanced` from the same
    `_advanced_surface_attr_names()` allowlist.

`InPathTrailingSpacer` was **never added to that allowlist**, so on import:

```
_advanced_surface_attrs_from_spec({'advanced': {'InPathTrailingSpacer': True}}) == {}
```

The flag is silently dropped → `_is_inpath_trailing_spacer_row(row)` is `False` →
S2 reverts to an ordinary surface that draws **both** its Ø78 clear-aperture disc
(the "big circle") **and** a surface curve → a pick region (so it is selectable as
"S2"). That pickability is the tell that the row is no longer being treated as a
spacer.

This is the same allowlist-round-trip trap noted before (cf. bugs/0082): any
row-`advanced` metadata that must survive a save/reload has to be registered in
`ADVANCED_SURFACE_FIELD_GROUPS`.

## Fix

Add `InPathTrailingSpacer` to `ADVANCED_SURFACE_FIELD_GROUPS` (the
"Diagnostics/Native" group, beside the other Open 3D promotion metadata). That
single registration:

  * auto-includes it in `ADVANCED_SURFACE_ATTR_NAMES` and `ADVANCED_SURFACE_ATTR_ALIASES`
    (the alias map is derived from the names), so `_advanced_surface_attrs_from_spec`
    preserves it from the `.py` dict spec;
  * is picked up by `_row_from_surface`'s `_advanced_surface_attr_names()` loop, so
    the Kos.surf round-trip preserves it too (`_surface_attr_differs_from_default`
    is `True`, the default surf has no such attr).

After the fix both import paths yield `row.advanced == {'InPathTrailingSpacer': True}`
and `_is_inpath_trailing_spacer_row(row)` is `True`, so the 0093 display skips fire
again and the big disc stays suppressed.

## Guard

`validate_open3d_inpath_spacer_flag_survives_reload` (display-free): a spacer spec
`{'advanced': {'InPathTrailingSpacer': True}}` round-trips through
`_advanced_surface_attrs_from_spec` and `_row_from_layout_item` with the flag
intact, `_is_inpath_trailing_spacer_row` stays `True`, and (fail-before/pass-after)
the flag is in `ADVANCED_SURFACE_ATTR_NAMES`. The Ø78 disc itself only builds under
the PyVista backend (absent headless), so the rendered disc still needs an in-app
eyeball — but the flag survival is now unit-pinned.
