# 0873 -- the Advanced Surface row form

Every KrakenOS surface attribute the main table does not show: 53 fields across 6 tabs -- the
shape parameters with the conic-k optimisation switch, one tab per attribute group, and the
custom sag/UDA pair.

## Three more framework properties

| property | for |
|---|---|
| `FormField.group` | the tab a field belongs to; a form with groups is laid out in tabs (`QTabWidget` in Qt, the existing scrolling `ttk.Notebook` in Tk) |
| `kind="bool"` | the "Optimize conic k" switch |
| `FormField.enabled` | a field the model will not take edits to |

`enabled` carries real meaning here. A value the literal reader cannot read back is **shown but
locked**, so a round trip can never mangle it; the shape parameters are locked on Object and
Image rows; and the conic-k switch and its bounds are locked where the variable registry does not
support k -- on S9 (a thin-lens group) it is off, on S1 it is available.

The conic switch writes native `Var`/`VarBounds` through the registry spec, exactly as the Tk
dialog did, and bounds that are not two increasing numbers are refused.

## Measured, not assumed

`_parse_literal_editor_text` **never raises**: text it cannot read as a Python literal is kept as
a **string**, because a KrakenOS attribute may legitimately be one. So an override that looks
broken is stored rather than refused -- what refuses is a shape value that is not a number
("Conic constant k expects a number."). My first assertion expected a refusal and was wrong; this
is the third row dialog where the model's real behaviour differed from the previous one's.

## Guard

`validate_open3d_0873_advanced_surface_row_form.py`, penta phase 651. G 53 fields across 6 tabs,
none loose. L the shape parameters are locked on the Image row. K1 the conic switch follows the
variable registry. K2 bad bounds are refused. E the string-keeping measured above. A apply writes
the shape value and sets the status. T the REAL Tk dialog opens with the same 6 tabs and 53 bound
values. Q1-Q4 the Qt form lays the same tabs in a `QTabWidget`, gives the switch a `QCheckBox`,
applies the same, and locks **exactly** the fields the model marks locked.
