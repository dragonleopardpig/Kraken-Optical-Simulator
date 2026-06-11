# 0059 — Open 3D: surface Ray count in the top toolbar, synced with 2D

## Reported (direct request)

> 3D is missing Ray count, and it should sync with 2D one.

The 2D trace/display controls show a prominent **Ray fan count** (default 31). In
the embedded Open 3D inspector the only ray-count entry lived in the **Source**
section of the left-docked, collapsible Live Controls panel — not where a user
comparing the two views would look. The always-visible top View toolbar exposed
a **Show rays** toggle but no way to set *how many* rays, so the count read as
"missing" in 3D.

## Root cause

Not a defect — a placement/discoverability gap. The 3D ray-count control already
shared the 2D variable: the 2D panel creates `editor.ray_count_var`
(`MainTraceDisplayControlsPanel.build`, whose `__setattr__` forwards to the
owning editor), and the Live panel pulls it back through
`Open3DLiveControlsPanel.editor_var("ray_count_var")`. Both reference the same
`KrakenLayoutEditor`, and the 2D controls build eagerly at main-window
construction, so the variable always exists before the inspector opens. The
sync mechanism was sound; the count simply wasn't surfaced in the toolbar where
"Show rays" lives.

## Fix

Added a **Ray count** entry to the top View toolbar
(`Open3DTopControlsPanel.build_view_toolbar`), right after the Show rays / Pick
rays toggles:

- a compact `CommitEntry` (width 4) bound to
  `self.inspector._editor_var("ray_count_var")` — the *same* shared accessor the
  Live panel uses, so the toolbar, the Live panel, and the 2D "Ray fan count" are
  all the one `tk.StringVar`. Editing any of them moves the others with no extra
  wiring.
- `on_commit` routes through `_commit_live_control_update(sync_fields=True)` and
  `on_focus_in` through `editor._begin_history_capture`, i.e. byte-for-byte the
  same commit/undo path as the Live-panel Ray count, so retrace + 2D refresh
  behave identically.

The View row keeps 6 direct controls (cap 10), so it stays narrow-window
friendly. No change to the Live-panel Source entry — both surface the same var.

## Tests

- `validate_open3d_toolbar_layout.py` gains a check: the View row exposes a
  `"Ray count"` entry wired to `_editor_var("ray_count_var")` and the
  `_commit_live_control_update(sync_fields=True)` commit. (The pre-existing
  "hide side panels" failure in this validator is unrelated branch debt — the
  toolbar now uses ◀/▶ collapse arrows instead of the old Live panel/Components
  checkboxes the stale check still expects.)
- `validate_open3d_ray_count_toolbar_sync.py` (new, display-free; needs a Tk root
  under Xvfb, no VTK): instantiates `Open3DLiveControlsPanel` against a stub
  editor and asserts `editor_var("ray_count_var") is editor.ray_count_var`
  (identity), that mutating either side moves the other, that unknown names fall
  back to a fresh StringVar, and — via `inspect.getsource` — that the toolbar
  builds the Ray count entry on the shared accessor + sync commit.

Visually confirmed by rendering `build_view_toolbar` to PNG under Xvfb: the
toolbar reads `… ☑ Show rays  ☐ Pick rays  Ray count [31]  Overlays …`.

No penta phase added (a toolbar-placement change is guarded by the toolbar
validator, mirroring 0058); penta baseline unchanged.
