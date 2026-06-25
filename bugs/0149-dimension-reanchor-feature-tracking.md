# 0149 — Re-anchored dimension endpoints are frozen-z and single-slot (don't track the model, only one end)

## Symptom

Two reports about the same override:

> *"I changed the FOV, the last re-anchored arrow stay where it was, wrong
> position now."*  (flag `flag_20260625_162312_629`)

> *"now I re-anchored arrow, only the right arrow can be reanchored, how about
> the left? Can make both arrow independent anchor?"*

A thickness/distance dimension arrow can be Ctrl-click re-anchored (bugs/0053):
the endpoint nearer the cursor follows the mouse onto a picked surface/edge and a
plain click commits a **measurement-only** override (the optical model is
untouched). The blue *model* thickness dims recompute every redraw and follow the
surfaces when the FOV/layout changes — but the re-anchored arrow did **not**, and
re-anchoring one end discarded the other.

## Root cause

bugs/0147 stored the override as a **single spec per row** holding only absolute
z's:

```python
spec = {"endpoint": endpoint, "ref_z": <moved end z>, "fixed_z": <other end z>}
```

`ref_z`/`fixed_z` are **absolute axial z snapshots** captured at pick time, and the
spec has **one** `endpoint` slot. Two consequences:

1. **No feature reference → can't track.** The override stores a *number*, not
   *which surface the end was pinned to*. When an FOV change shifts the surfaces,
   `_surface_reference_world_point(row)` (what the blue dims use) returns the new
   live z and the blue dims follow — but `reanchored_endpoints` just replayed the
   frozen `ref_z`/`fixed_z`, so the magenta arrow stayed at the old station. Stale.
   (`_dimension_anchor_feature_label` only ever produced a display string
   `"z=142.2"` — it was never a resolvable reference.)
2. **One slot → ends not independent.** Re-anchoring an end **replaced** the whole
   spec. bugs/0147 papered over the resulting "left reanchor moved the right arrow"
   by snapshotting the other end into `fixed_z` — but that froze it (problem 1) and
   still only carried *one* re-anchored feature.

## Fix — one independent, feature-tracking anchor **per endpoint**

The override now keeps **up to two anchors**, keyed by endpoint, alongside the
legacy mirror (kept for the value-edit path + old saved layouts):

```python
overrides[row] = {
    "start": {"kind": "surface", "row": 1, "face_id": "", "abs_z": 275.0, "label": ...} | None,
    "end":   {"kind": "absolute", "abs_z": 99.0, "label": ...} | None,
    # legacy mirror still written: endpoint / ref_z / ref_label / fixed_z
}
```

Each endpoint anchor is one of:

- `kind="surface"` — the pick resolved to an optical surface row. Its live axial z
  is **re-derived every redraw** from `editor._surface_reference_world_point(row,
  face_id)` (the same live source the blue model dims use), so it **follows the
  model** on an FOV/layout change. `abs_z` is the surface's station at pick time,
  kept only as a fallback.
- `kind="absolute"` — an empty-space / unresolved pick. Frozen at the picked z —
  the pre-0149 behaviour, retained as the fallback.

An endpoint with **no** anchor keeps its live `p0`/`p1` z (it already tracks the
model — it's the dimension's own surface).

Because each endpoint owns its slot, re-anchoring one end **never discards** the
other — the bugs/0147 sequence ("right then left") now composes with no `fixed_z`
snapshot needed and **both ends track their features**.

### The chain (5 edits)

- **Pick** — `_apply_dimension_anchor_pick_motion`
  (`open3d_inspector.py`) already resolved the hovered actor; it now records the
  optical-surface row it snapped onto into `state["snap_feature"]`
  (`{"row": r}` or `None` for empty space). `_commit_dimension_anchor_pick`
  forwards it as `feature_ref=`.
- **Store** — `apply_dimension_anchor_override(..., feature_ref=None)`
  (`scene_placement_commands.py`) builds the per-endpoint anchor via the new
  `_dimension_endpoint_anchor_from_feature` (surface vs absolute), **merges** it
  into the row's override (keeping the other end), still writes the legacy mirror,
  and migrates a pre-0149 `fixed_z` into an `absolute` anchor for the other end so a
  transition doesn't lose it.
- **Draw** — `reanchored_endpoints` (`open3d_thickness_dimensions.py`) takes a new
  branch when `start`/`end` anchors are present: each present anchor re-derives its
  live z via `_resolve_endpoint_anchor_z` (surface → live resolve, else `abs_z`,
  else live p0/p1); the absent end stays on p0/p1. The **legacy single-spec path is
  byte-identical** below it (old layouts + the value-edit mirror still freeze).
- **Persist** — `layout_settings.py` `_sanitise_dimension_anchor_override` (used on
  both save and load) carries `start`/`end` anchors + the legacy mirror through
  JSON.

## Verification

- `KrakenOS/UI/validate_open3d_dimension_reanchor_feature_track.py` (`run_checks`,
  display-free) — 12/12 PASS: a `surface` anchor follows a simulated FOV move
  (frozen would be the bug); both ends track independently; an `absolute` anchor
  stays frozen + an unanchored end stays live; failed-resolve / `editor=None` fall
  back to `abs_z` without crashing; `apply_dimension_anchor_override(feature_ref=…)`
  builds surface anchors, leaves the model thickness untouched, and re-anchoring the
  start keeps the end anchor (independent slots); a legacy `fixed_z` migrates to an
  absolute end anchor; the per-endpoint anchors round-trip through settings; the
  legacy single-spec form still draws frozen; and source markers across the
  draw/resolve/store/pick chain.
- The pre-existing guards stay green untouched (the legacy path is unchanged):
  `validate_open3d_dimension_reanchor.py` (10/10) and
  `validate_open3d_dimension_reanchor_fixed_end.py` (phase 136, all PASS).

## Guard

- `KrakenOS/UI/validate_open3d_dimension_reanchor_feature_track.py` as above.
- Penta phase **138** (`phase_138_dimension_reanchor_feature_track`); baseline →
  138 = pass (139 phases, 0–138).
- Source markers catch a revert to frozen-only / single-slot behaviour.

## In-app eyeball still owed

Headless cannot drive the embedded-VTK Ctrl-click pick. The *felt* result is owed
an in-app check: re-anchor an arrow end onto an optical surface, change the FOV (or
slide a surface), and confirm the magenta arrow **follows** the surface; then
re-anchor the *other* end and confirm the first end **stays on its feature**.

## Note — STEP-body / non-row anchors

A pick that resolves only to a STEP body (not an optical surface row) currently
stores an `absolute` anchor (frozen) — unchanged from pre-0149 and correct for a
static body. The `kind` field is extensible (the resolver defaults unknown kinds to
`abs_z`), so a future `kind="step"` that tracks a moving body is a small addition.
