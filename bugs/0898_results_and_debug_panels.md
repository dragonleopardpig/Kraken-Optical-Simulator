# 0898 -- the results, debug and progress panels are data, and Qt has them

Three more Tk widgets the **model** wrote into directly, of the kind 0893 removed:

```python
self.results_table.insert("", "end", values=(key, value))   # 98 property/value pairs
self.debug_text.insert("end", line + "\n")
self.progress_text.insert("end", message.rstrip() + "\n")
```

None of that is view code. What the analysis *found* and what it *logged* are results; only the
drawing is a toolkit's business. So the model now publishes

- `editor.results_items` -- the property/value pairs
- `editor.debug_lines`
- `editor.progress_lines`

and calls `show_results(items)` / `show_debug_line(line)` / `show_progress_line(line)`, which
each shell implements and a shell-less editor simply does not have -- the same seam shape 0893
used for `set_plot_cursor`.

## What it bought

**The Qt shell had none of these panels.** Before this it showed the 3D view, the 2D plot (0893)
and the surface table, and nothing of what the analysis produced. It now has **Results**, **Debug**
and **Progress** docks, the Results table reading the pairs straight off the editor.

Measured on `om05a_folded`: the analysis publishes **71** property/value pairs, and both shells
show the same 71 in the same order.

Copy Debug reads `debug_lines` now instead of selecting all the text in a widget, which also
means it works with no window open.

## Guard

`KrakenOS/UI/validate_open3d_0898_results_and_debug_panels.py` (penta phase 686):

- **S** -- no model function reaches for `results_table`, `debug_text` or `progress_text`, and
  Copy Debug copies the model's own lines
- **M** -- the REAL Tk results table holds exactly `results_items`, every entry a pair of strings
- **D** -- one debug line lands in `debug_lines`, in `kraken_debug_latest.log` **and** in the
  widget; a progress line lands in `progress_lines` and its own widget; Copy Debug carries the
  model's own text
- **H** -- an editor with no shell keeps publishing all three and raises nothing
- **Q / P** -- the Qt docks show the model's own rows, with the same property list as Tk

## A note on what was *not* ported

`missing_assets_dialog` was the previous turn's suggested next item. Having read it, it is not a
report: it is a resolution workflow with per-row status (`missing` / `located` / `skipped`), row
colour tags, an open-**file** chooser whose title is per-asset, a **directory** chooser for the
batch match, and no CSV at all. Putting it on `ReportWindow` would mean five new chooser and
styling capabilities on `Report` for one dialog that is not a data view. It stays as it is.
