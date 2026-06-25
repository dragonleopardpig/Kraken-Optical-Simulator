# 0144 — A single-label STEP-overlay refresh drops another label's actors (lens "loses its face")

## Symptom

> *"sudden imaging lens STEP lost its face"* (flag `flag_20260625_120343_069`, 12:03)

With the camera + LED + beam-splitter + imaging-lens overlays loaded, the imaging
lens STEP overlay abruptly stopped rendering — its body and gold face-outline
vanished — even though the lens STEP was still loaded (present in
`step_overlay_poses` with a clean all-zero pose) and nothing had touched the lens.
It stayed gone for ~5 minutes (12:03:21 → 12:08:11) until a beam-splitter promote
forced a full scene refresh that rebuilt every overlay from scratch.

## Root cause

Actor keys are **VTK object addresses** (`actor.GetAddressAsString("")`,
`Kraken3DInspector._actor_key`). VTK **recycles a freed actor's address** for the
next actor it allocates.

The inspector keeps two flavours of actor bookkeeping:

- **reverse maps** — `_actor_step_follow_map[key] → label`, `_actor_step_map[key] →
  label`, … — dicts keyed by address that `_add_mesh_actor`
  **overwrites on every registration**, so they always name the *live* owner.
- **forward per-label lists** — `_step_follow_actor_map[label] → [key, …]`,
  `_step_actor_map[label] → [key, …]` — only pruned by
  `_remove_actor_registration`.

A teardown that frees an actor by **any other path** than
`_remove_actor_registration` (a direct `renderer.RemoveActor` + `_actor_by_key`
pop — e.g. the carry-grip / rotation-handle overlays) leaves that actor's address
**lingering in its forward list**. VTK then recycles the freed address for the
**next** overlay body it builds — which can be a *different* label. After the
recycle:

- the **reverse** map for that address is overwritten to the new owner (e.g.
  `_actor_step_follow_map[0xABC] = "lens"`), but
- the **stale forward entry** survives: `_step_follow_actor_map["optical"]` still
  lists `0xABC`, which now points at the **live lens body**.

A left-click selecting the beam-splitter fired the partial single-label
`refresh_imported_step_overlay("optical")` (`open3d_step_overlay_refresh.py`). Its
`_remove_step_overlay_actors("optical")` built its removal set partly from
`_step_follow_actor_map["optical"]`, so it swept up the recycled `0xABC` and tore
down the **live lens body** — `_remove_actor_from_renderers(lens_actor)` plus a pop
of `_step_actor_map["lens"]` (which is why the lens dropped out of the recorder's
`step_actor_labels`). The lens overlay was display-only and otherwise untouched, so
nothing redrew it until the next *full* refresh.

Timing-log fingerprint at the drop (idx ~2138, 12:03:21): `interaction_handler_start`
→ `left_click_vtk_pick` (`selected_step=optical`) → `load_step_mesh` **cache hit**
(BS `step_32704.step`, 1 ms — the mesh was fine, ruling out a load-None drop) →
`refresh_imported_step_overlay_start label=optical` → render with `step_actor_labels`
losing `lens` → `refresh_imported_step_overlay_rebuilt label=optical removed=15`.

## Fix

`KrakenOS/UI/services/open3d_step_overlay_refresh.py` — `_remove_step_overlay_actors`
now filters its removal set through the **live owner**:

- `_step_overlay_actor_owner_label(actor_key)` resolves the address through the
  always-fresh reverse maps (`_actor_step_follow_map`, then `_actor_step_map`, then
  `_actor_step_rotate_map`), returning the lowercased label or `None`.
- the collected `actor_keys` are kept only when
  `_step_overlay_actor_owner_label(key) in (None, label)`. A key whose live owner is
  a **different** label — the recycled-address collision — is skipped, so the foreign
  (lens) body is never torn down.

The genuine same-label actors still resolve to `label` and are removed as before, and
the wholesale `_step_follow_actor_map.pop(label)` / `_step_actor_map.pop(label)` at the
end discards the stale forward entry along with the rest of the refreshed label's list
— so the collision self-heals on the very refresh that used to trip on it.

(The deeper leak — actors freed without `_remove_actor_registration` seeding the stale
forward entry — is the underlying mechanism; the removal-side filter neutralises its
*cross-label* consequence robustly and is trivially testable. A rotate-map reverse
entry left stale on a recycled address is a separate latent mis-pick, out of scope
here.)

## Verification (`KrakenOS/UI/validate_open3d_step_overlay_refresh_keeps_other_labels.py`)

A display-free harness (`_FakeInspector` carrying the real maps + the leaf state the
removal path touches, driving the **real** `Open3DStepOverlayRefreshService`) registers
a lens body and an optical body at distinct addresses, then injects the recycled-address
collision (the lens's live address as a stale entry in optical's forward list):

- **Collision** — `refresh("optical")` leaves the lens body in `_actor_by_key` /
  `_step_actor_map["lens"]` / the renderer, and still removes the genuine optical body.
- **Symmetry** — the same collision the other way (recycled optical address stale in the
  lens list) is protected when refreshing `"lens"`.
- **No-collision baseline** — with no stale entry, `refresh("optical")` removes exactly
  optical and leaves lens (removal not over-narrowed).
- **Source wiring** — the owner-label resolver exists and the removal set is filtered
  through it.

All 5 checks pass. Removing the filter flips checks 1, 2 and 4 to FAIL (the lens body is
dropped + `step_map_lens=None` + `renderer_removed_lens=True`), confirming the guard
reproduces the bug rather than passing vacuously.

## Guard

- `KrakenOS/UI/validate_open3d_step_overlay_refresh_keeps_other_labels.py` (`run_checks`,
  display-free): the four pins above.
- Penta phase **133** (`phase_133_step_overlay_refresh_keeps_other_labels`);
  baseline → 133 = pass.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK click/pick that fires the partial refresh, so the
*felt* fix — the imaging-lens overlay staying drawn after clicking/selecting the
beam-splitter (or any other overlay) — is owed an in-app check alongside the 0142 / 0143
eyeballs.
