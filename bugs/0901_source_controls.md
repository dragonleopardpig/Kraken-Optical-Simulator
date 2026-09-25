# 0901 -- the source inputs in Qt

0900 gave the Qt shell the inputs that decide what the light goes **through**. This is the other
half: the **23** that decide what launches it -- source model and pupil pattern, radius and cone
angle, the seven Gaussian-beam fields, pupil r/θ, power, seed, position, direction and its
preset, and the random-source angular weight.

## No new mechanism

`SOURCE_CONTROLS` is a second group of the same `SystemControl`; `CONTROL_GROUPS` names both;
and one Qt `SystemPanel` renders either, so the **Source** dock is the System dock's class over
a different tuple. The six choice lists already lived in `source_trace_helpers.py` -- the
catalogue points at them rather than copying them -- and `commit_source_controls` joined its two
siblings on the model, leaving the Tk panel a two-line callback that delegates.

Measured on `om05a_folded`: the Source dock opens on the loaded source (*Pupil / field*,
*Meridional fan*), a model write repaints it, and a form write reaches the model and leaves
*"Display settings changed. Click Update."* on the status line.

## Found along the way: a variable the registry never knew about

`source_direction_preset_var` was **not** in `MODEL_VARIABLES`. A shell without Tk panels would
therefore never have had it at all -- the Tk panel is what creates it.

It escaped the 0852 audit because model code reads it as

```python
var = self.__dict__.get("source_direction_preset_var")
```

rather than as an attribute, and that guard's "every panel-made variable model code uses is
registered" scan looks for attribute access. Registering it took the registry from 64 to 65;
phase 655's count was updated to match, with the reason written next to it.

The `__dict__.get` blind spot is worth remembering: it hides a variable from the registry audit.
Nothing else was checked for it here -- that would be its own sweep.

## Guard

`KrakenOS/UI/validate_open3d_0901_source_controls.py` (penta phase 689):

- **C** -- 23 inputs, each against a registry-declared variable, and the Tk panel reads every
  one of their labels from the catalogue (no literal left)
- **V** -- the six choice lists *are* `source_trace_helpers`' own, not a copy
- **S** -- the commit is the model's; the Tk panel delegates
- **T** -- a REAL editor holds every source variable, and every choice it holds is in the
  catalogue's list
- **G** -- one Qt class renders both groups, into both docks
- **B / Q** -- the Qt form opens on the loaded source; a model write repaints it and a form
  write reaches the model and marks the plot stale
