# 0867 -- the Ray Inspector: the master/detail family

The fourth phase-3 family: a master table (every traced ray) with a detail table beneath it (the
hits of whichever ray is selected).

## What moved

The detail side was already shared -- `_ray_hit_table_specs` and `_ray_hit_table_values` on the
editor. The master rows were formatted inline inside the Tk refresh, and are now
`KrakenOS/UI/reports/ray_tables.py`: the 22-column layout, the `source:index` label, the
`S12  name` last-surface text, and the summary line.

`Report` gained a `DetailView`: columns, and `rows(master_index)` returning already-formatted
cells. `ReportDialog` shows it as a second table in a vertical splitter and refills it whenever the
master selection changes -- so the family costs one builder and no new dialog class.

On `om05a_folded.py`: 226 rays x 22 columns, with 15 hits for ray 0 and 9 for ray 3 (which stops
at S10 and bypasses the sensor).

**The Trace Path Inspector is deliberately not ported.** Its records are branch-tree records, not
ray records, and its Tk view is a HIERARCHY -- rays with their paths nested underneath -- which a
table cannot show. It needs a QTreeView and a tree model: the fifth family. Reusing the ray
columns for it produced `KeyError: 'source_ray_index'`, which is the right answer to the wrong
question, so the port was removed rather than bent into shape.

## A circular import worth remembering

`ray_tables.py` first lived at `KrakenOS/UI/`, beside the other toolkit-free analysis modules --
but it declares `ReportColumn`s, so it imports `reports.base`. Importing it FIRST ran the reports
package's `__init__`, which imports the builder, which imports `ray_tables` while it is still
initialising: `ImportError: cannot import name 'EMPTY' ... partially initialized module`. It only
bit when the module was imported before the package, which is exactly what a guard does. It lives
inside the package now.

## Guard

`validate_open3d_0867_ray_inspector_master_detail.py`, penta phase 645. C the detail columns are
the editor's own 59 hit-table specs. M all 226 x 22 master cells equal `ray_table_values`. D the
detail follows the selection -- ray 0's 15 hits and ray 3's 9, each by `_ray_hit_table_values`.
S the summary is the Tk ray inspector's own line. T the REAL Tk ray inspector is opened and its
master Treeview read back: **one SHA-256 over all 226 rows, equal to the Qt table's.**
