# 0859 -- one report, two toolkits (Qt migration, phase 3 begins)

Phase 3 is the dialogs: **62 functions build a `tk.Toplevel`, about 9 000 lines** (census
2026-09-23, validators and archive excluded). The largest are the CAD/STL face-roles editor
(1 902 lines), the Scene Source Manager (680) and the Paraxial Calculator (459).

Porting them one-for-one would double the dialog code and guarantee drift: two views, each
reading the model its own way, each formatting its own numbers.

## The recipe this establishes

For every dialog that is *a summary, a table and an export* -- a large share of the 62 -- the
DATA moves out of the dialog into a toolkit-free builder under `KrakenOS/UI/reports/`, returning
a `Report` (title, summary, columns, rows, status). Each toolkit then keeps only its layout, and
both render the same object, so a number cannot differ between them. As a side effect the
numbers become checkable **without a display**, which no Tk dialog's contents ever were.

| piece | what |
|---|---|
| `reports/base.py` | `ReportColumn` (heading, numeric -> format and alignment, width, stretch), `Report` (`cell()`, `write_csv()`), `ReportFailed` |
| `reports/paraxial_matrix.py` | `build_paraxial_matrix_report(owner)` -- the Paraxial Matrix Report's 17 columns and its summary line |
| `qt/dialogs/report_dialog.py` | `ReportDialog` -- the Qt layout for the whole family: summary, table, Export CSV, Close |
| `panels/main_paraxial_analysis_dialogs.py` | the Tk dialog, now layout only |

The first port is the **Paraxial Matrix Report** (Actions menu in Tk; Analysis menu, Ctrl+M, in
the Qt shell). On `om05a_folded.py`: 25 surfaces, 17 columns, EFFL 85.13 mm.

Both views ask for the export path through the UI host, so the Tk build gets `filedialog` and the
Qt build gets `QFileDialog` from the same call shape. The CSV carries the RAW values under the
column keys -- not the displayed `.8g` text.

Noted in passing, not fixed: the Tk failure branch calls `self.short_error_message(exc)`, which
nothing in the package defines; it would raise `AttributeError` on the path that is meant to
report an error. The builder now takes the message defensively
(`getattr(owner, "short_error_message", str)`), so the failure path works in both views.

## Guard

`validate_open3d_0859_paraxial_report_shared.py`, penta phase 638.

P1 the extracted builder equals an independent `system.ParaxMatrices` call, value by value, and
the summary carries the EFFL. P2 the REAL Tk dialog is opened and its Treeview read back: its
headings and every cell equal the report's. P3 the CSV holds raw values under the keys, proven
against the displayed text for the same field. P4 a model that cannot build raises `ReportFailed`
carrying the message. Q1 the Qt dialog's table, title and summary equal the same report -- so Tk
and Qt are shown to agree through a common reference rather than by eye. Q2 numeric columns are
right-aligned, text columns left. Q3 Export CSV asks through the UI host and writes a file
identical to the report's own. Q4 a failed build reports through the host and opens no dialog.
