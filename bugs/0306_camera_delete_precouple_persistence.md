# 0306 — Deleting a camera leaves the detector behind *after a save/reload* (0296 resurface)

Flag `flag_20260714_164822_481`:

> *why the bug resurface? Deleting a camera still leave the detector behind.*

The state.json for that flag shows the terminal Image row (row 8) still carrying a **±16.29 mm**
aperture after the camera was deleted — the PYTHON 25K sensor half-diagonal (23.04×23.04 → semi-diagonal
16.2915). The vendor sensor *rectangle* overlay was gone (the model reset to None), but the coupled
image-surface *circle* stayed. That is exactly the symptom 0296 fixed in-session, come back.

## Why it came back
0296 gave the camera sensor coupling a **stash-on-couple / restore-on-decouple** lifecycle: the first couple
stashes the pre-camera field / image-surface aperture (`_stash_camera_precouple_field_state` →
`_camera_coverage_precouple_stash`), and deleting the camera (or setting the dropdown back to None) restores it
(`_decouple_camera_model`). But that stash lived **only in the running session** — it was never serialized.

0296's own doc flagged this as a known limitation: *"a layout saved with a camera already coupled and then
deleted in a fresh session has no pre-camera state to restore."* It stayed latent until **0305 ("save
everything")** made save → reopen the common workflow. Now the path is:

1. couple a camera (interactive/STEP import) → stash captured, image circle forced to the sensor coverage;
2. **Save** → the layout `.py` persists `camera_model` and the coupled rows, but **not** the stash;
3. **reopen** → the load-time coverage auto-fill (`open_layout`, layout_table_workbench.py:538) re-couples the
   sensor but deliberately never stashes (load has no meaningful "before");
4. **delete the camera** → `_decouple_camera_model` finds **no stash**, so it resets the model to None but
   leaves the sensor image circle on the terminal Image row. Detector left behind.

## The fix
**Part 1 — persist the stash (root cause).** `_collect_layout_settings` now writes `camera_precouple_stash`
and `_apply_layout_settings` restores it into `_camera_coverage_precouple_stash` (gated on a valid restored
camera, so a stray stash never blocks the next first-couple capture). The stash is first captured on the
initial *interactive/STEP* couple — i.e. with the genuine pre-camera field — so persisting it carries the
natural state across every save/reload: a delete after reload now finds the stash and reverts to the
un-coupled image circle / field / image-diameter mode, exactly like an in-session delete.

**Part 2 — legacy grace.** A layout saved *before* 0306 (or any file that reaches a delete with no stash)
can no longer reconstruct its exact pre-camera field — the couple overwrote both the Real Image Height field
and the object diameter, and the datasheet image circle is not independently persisted. So `_decouple_camera_model`
now at least **unlocks** the aperture: with no stash it flips a `Manual` image-diameter mode back to the
self-computing `Auto` mode instead of leaving it pinned to the deleted sensor. The residual image circle only
*fully* clears once the camera layout is rebuilt / re-imported (which re-captures **and** now persists the
stash) — an honest limitation of legacy files, called out so a rebuild is the known cure.

## Files
- `KrakenOS/UI/services/layout_settings.py` — persist (`_collect_layout_settings`) + restore
  (`_apply_layout_settings`) `camera_precouple_stash`; the camera-model restore now computes `camera_is_valid`
  once and gates the stash restore on it.
- `KrakenOS/UI/services/layout_table_workbench.py` — `_decouple_camera_model` no-stash branch flips
  `Manual` → `Auto` (legacy unlock) before returning `False`.

## Verified (display-free — headless VTK segfaults under Xvfb llvmpipe)
- `KrakenOS/UI/validate_open3d_camera_coupling_persistence.py` (`run_checks()`) — **PASSED**:
  * structural: `_collect_layout_settings` / `_apply_layout_settings` carry the stash key;
  * semantic: a real captured stash JSON round-trips through the settings key and drives a correct
    reopen → delete revert on a stub (image circle, field, and mode all return to the pre-camera values,
    from a start state that really was at the sensor coverage);
  * legacy: a no-stash decouple clears the model and flips `Manual` → `Auto`.
- 0296's own guards still green: `validate_open3d_camera_coupling_lifecycle` (**PASS**, penta phase 260) and
  `validate_camera_folder_import` (**PASS**, penta phase 265).
- New penta **phase 269** (`phase_269_camera_coupling_persistence`) delegates to the guard; baseline
  `"269": "pass"`.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): import a vendor camera, **Save**, reopen the layout + Open 3D,
  **delete the camera**, and confirm the terminal Image row shrinks back to the lens's natural image circle
  (no ±16.29 sensor disc left behind). Then repeat with a *freshly rebuilt* legacy camera layout.
