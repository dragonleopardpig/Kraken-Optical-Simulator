# 0382 — a flag bundle records WHICH scene it was on

**Origin:** user, while diagnosing the AZ85 lens-swap flags — *"I wonder why the key recording not
even recorded what file I load?"*

## Problem

The Open-3D flag bundle's `state.json` captured `build` / `cursor` / `recording` / `scene_state`, but
**not the loaded layout**. So a flagged bug could not say which scene it was on — the AZ85 flags all had
`current_layout_file: None` (several load / insert / promote paths clear it: an inserted machine-vision
surrogate, an unsaved import). I had to ask the user which file they'd loaded.

## Fix

`Kraken3DInspector._flag_layout_identity()` captures a `"layout"` block into every flag payload:
- `file` + `name` — `current_layout_file` when it is set (the best answer).
- `unsaved_import` — the bugs/0375 transient-import flag.
- `step_paths` — the STEP overlay source paths (`optical` / `lens` / `camera` / `led`), which pin the
  scene even when the layout file is None. A lens STEP of **ELS-85** identifies the AZ85 RA-mirror scene
  outright.

Best-effort (each part wrapped) so it can never take the flag write down.

## Verification

- Layout file set → `file` + `name` + `step_paths` captured.
- Layout file None → `step_paths` still pins the scene (the AZ85 case).
- Nothing loaded → empty, no crash. A bare/broken editor → no raise.

Guard `validate_open3d_flag_layout_identity`, penta **phase 323**.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_flag_layout_identity()` + `"layout"` in the flag payload.
- `KrakenOS/UI/validate_open3d_flag_layout_identity.py` — guard (phase 323).
