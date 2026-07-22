# 0401 — coaxial-illuminator edge-profile selector (calibratable soft edge)

**Feature (chosen from the backlog):** a UI selector for the LED illumination profile — a flat-top
with a soft/rising edge whose width the user can dial — so the ~2 mm-per-side dark edge on MV-150 is
reproducible/calibratable instead of only the kernel's automatic default.

## What existed

The kernel already models a soft illumination edge: `source_object_coupling._aperture_soft_edge`
does a raised-cosine roll-off over a `penumbra_mm` band, and `coaxial_illuminator_footprint_map`
defaults the band to ~6 % of the aperture. The band is read off the source spec by
`coaxial_illuminator_descriptor` from `coaxial_penumbra_mm` (`> 0` uses it; else `None` → kernel
auto). But nothing in the UI wrote `coaxial_penumbra_mm` — the edge was always the auto default.

## Fix — map a named profile + edge width onto the existing `coaxial_penumbra_mm`

No new kernel path. Two pure helpers in `scene_source_analysis.py`:

- `coaxial_edge_penumbra_mm(profile, edge_width_text)` — the forward map the dialog's Apply uses:
  - **Flat-top, soft edge** + `Auto`/blank/garbage → `0.0` (descriptor reads `None` → kernel auto ~6 %);
  - **Flat-top, soft edge** + a positive number → that width in mm (e.g. `2.0` to calibrate MV-150);
  - **Uniform, sharp edge** → `0.01` (a sub-bin band ⇒ effectively a hard flat-top step), width ignored.
- `coaxial_edge_profile_and_width(spec)` — the inverse, to seed the dialog: an explicit stored
  `coaxial_edge_profile` wins; otherwise the profile/width are inferred from `coaxial_penumbra_mm`.

The **Edit Source…** dialog (`open3d_source_edit_dialog.py`) grows an *Illumination edge* row — a
readonly profile Combobox + an *Edge width (mm)* Entry — shown **only for a coaxial illuminator**
(`spec[coaxial_illuminator]`). Apply writes `coaxial_edge_profile` + `coaxial_penumbra_mm` through the
existing `update_scene_source_spec` path, so the footprint overlay + illumination trace follow on the
next rebuild.

### The one trap (bugs/0397-class whitelist)

`update_scene_source_spec` only lets keys in `SCENE_SOURCE_EDITABLE_KEYS` through — so the two new
keys would be **silently dropped** on Apply (the control would look wired yet never persist). Both
keys are added to that whitelist. `normalize_scene_source_specs` preserves arbitrary keys, so once
past the whitelist they survive save/reload.

## Verification (`validate_open3d_coaxial_edge_profile`, penta phase 329)

Display-free (no renderer / no Tk / no llvmpipe segfault): drives the **real**
`update_scene_source_spec` through its whitelist against a minimal stub.

| check | asserts |
|---|---|
| MAP | soft+Auto/blank/bad → 0 (auto); soft+num → num; sharp → 0.01 hard step (width ignored) |
| SEED | explicit profile wins + width round-trips; else inferred from `coaxial_penumbra_mm` |
| DESCRIPTOR | soft+auto → `None`, soft+2 → 2.0, sharp → 0.01 reach `coaxial_illuminator_descriptor` |
| WHITELIST | a real update **persists + refreshes** both keys; a non-editable junk key is dropped |
| WIRING | the dialog seeds/writes both keys gated on `is_coaxial`; both keys are whitelisted |

All pass. The penta baseline records phase 329 = pass.

## Files

- `KrakenOS/UI/scene_source_analysis.py` — profile constants + `coaxial_edge_penumbra_mm` /
  `coaxial_edge_profile_and_width`.
- `KrakenOS/UI/panels/open3d_source_edit_dialog.py` — the *Illumination edge* control (coaxial-only).
- `KrakenOS/UI/services/source_modeling.py` — whitelist the two keys in `SCENE_SOURCE_EDITABLE_KEYS`.
- `KrakenOS/UI/validate_open3d_coaxial_edge_profile.py` — guard (penta phase 329).

## In-app eyeball still owed

On MV-150: right-click the coaxial LED → **Edit Source…**, set *Flat-top, soft edge* + *Edge width*
≈ 2 mm, Apply — the object-plane footprint's edge should soften to a ~2 mm-per-side roll-off; switch
to *Uniform, sharp edge* for a hard flat top.
