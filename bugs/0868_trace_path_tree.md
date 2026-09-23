# 0868 -- the Trace Path Inspector: the tree family

The fifth and last structural family of phase 3. bugs/0867 deliberately left this dialog alone
because its view is a HIERARCHY -- every traced ray is a node, and the paths it split into hang
underneath it, nested again when one path branched from another. A table cannot show that.

## What it took

`Report` gained `TreeRow` (a label, its cells, its children, and the `detail_key` the detail view
is asked for) plus `tree` and `tree_heading`. `ReportDialog` renders a `QTreeView` over a standard
item model when a report carries a tree, and a `QTableView` when it does not -- the detail half,
the summary, the controls and the export are unchanged, so the family cost one builder and one
branch in the dialog.

`reports/branch_tree_tables.py` holds the model side: the 13 columns and their widths from the Tk
branch tree, the ray node's cells (`field, -, -, -, ray, ..., path count, ...`), the path node's
cells, the `Path 3: primary+reflected` labels, and the nesting rule -- a path goes under its
PARENT path when it has one, else under its ray.

`reports/trace_paths.py` is the builder; the hits still come from the editor's own
`_ray_hit_table_values`, keyed by the record index each node carries.

On `om05a_folded.py`: 226 rays, 226 paths, 452 nodes, with 15 hits under ray 0's path and 9 under
ray 3's (which stops at S10).

## Guard

`validate_open3d_0868_trace_path_tree.py`, penta phase 646. C the columns are the Tk layout under
"Ray / Path". N the nesting is the model's -- one node per ray, every nested node a Path, exactly
one detail-carrying node per record. D the detail follows the selected NODE by its record key.
S the summary is the Tk trace-path line. T the REAL Tk branch tree is opened and walked depth
first: **one SHA-256 over all 452 nodes -- labels, cells and depth -- equal to the Qt tree's.**

## Phase 3's five families, all represented

| family | first port |
|---|---|
| report | Paraxial Matrix (0859) |
| report with controls | Path Throughput / Source Illumination (0863) |
| report with inputs | Gaussian Beam (0864) |
| form that writes back | Paraxial Calculator (0865) |
| master/detail | Ray Inspector (0867) |
| tree | Trace Path Inspector (0868) |

What remains of the 62 dialogs is mostly the editor-shaped ones -- Coating/Material, Advanced
Surface, and the 1 902-line CAD face-roles editor -- which are forms over a selected row.
