# 0622 — Ctrl+drag box-selects; plain drag rotates (user revision of 0620)

User: *"can you change Ctrl-drag to select and drag to rotate? Drag to rotate because
it is most frequently used than select."* Right call — orbit is the dominant gesture
and guessing intent from the press location (0620's empty-space heuristic) was less
predictable than a modifier.

## Behaviour

- **Plain left-drag orbits the camera, everywhere** — the pre-0620 default restored,
  including over empty background.
- **Ctrl+left-drag draws the one-shot box select, from anywhere** (empty or over
  bodies — a selection box does not care where it starts). Release selects; the
  Selection right-click menu follows.
- The 0053 Ctrl-click dimension-anchor re-anchor keeps priority (resolved before the
  select arming); armed click-to-target modes (measure, snap-to-axis, …) keep their
  Ctrl-orbit fallback via the eligibility gate; Ctrl+click (no drag) stays a no-op;
  Shift+drag / middle-drag still pan; the armed menu rubber-band modes still own
  their plain drags.
- The 0620 `_press_on_empty_space` heuristic is retired.

Guard: phase 466's F checks re-derived (Ctrl-press arms behind the eligibility gate,
Ctrl-motion activates the transient, the empty-space heuristic must NOT return).
Toolbar hint + docs/open3d_dynamic_interaction.md updated.
