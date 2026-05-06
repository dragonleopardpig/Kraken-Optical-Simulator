# Kraken Layout Editor Manual

## Launch

```bash
cd ~/Projects/Kraken-Optical-Simulator
devenv shell -- bash -lc 'python -m KrakenOS.UI.layout_editor'
```

Headless native snapshot:

```bash
cd ~/Projects/Kraken-Optical-Simulator
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot --mode native --output ~/Pictures/kraken_layout_headless.jpg
```

## Main UI layout

### Left side

- `Display`
  - object mode
  - wavelength
  - orientation
  - ray fan count
  - pupil factor
  - analysis stop surface
  - aperture type/value
- `Field`
  - field type
  - field value
  - field count
- `Source`
  - source model
  - pupil pattern
  - random source radius/cone/power/seed/origin
- editable prescription table
- plot area and analysis toolbar

### Right side

- `Information`
- `Optimization`
- `Progress`
- `Debug`

## Display panel

### Object mode

- `Infinity`
  - source is a collimated field definition
- `Finite`
  - source is a finite-distance object definition

`Field Half-Angle = 0` does not make `Finite` and `Infinity` equivalent. They remain different source models.

`Field Half-Angle` is a semi-angle, not a full field angle.

### Orientation

- `Vertical`
  - ordinary axial-style display
- `Horizontal`
  - folded/off-axis display orientation used for mirror-fold systems

### Analysis stop surface

- `Auto`
  - use the editor's default analysis stop
- or choose an explicit row by index and name

### Aperture

- `STOP`
- `EPD`

These settings affect analysis modes that depend on pupil construction.

## Field panel

### Field type

Available definitions:

- `Field Half-Angle`
- `Object Semi-Height`
- `Paraxial Image Semi-Height`
- `Real Image Semi-Height`

Only one field definition is active at a time.

`Object Diameter`, `Image Diameter`, and `EPD` stay as full diameters.

`Field samples > 1` means the traced field points span from `-max` to `+max`.

### Recommended usage

- for `Infinity`
  - use `Field Half-Angle`
- for `Finite`
  - use `Object Semi-Height`

The status bar shows:

- preferred field note
- any warning such as field semi-height exceeding the object half-size
- converted field summary

## Source panel

The default source model is `Pupil / field`, which keeps the traditional
KrakenOS field and pupil tracing workflow.

`Pupil pattern` controls the `PupilCalc.Ptype` pattern used when building
preview and geometric analysis bundles:

- `Meridional fan`: readable 2D fan in the active display plane.
- `Cross fan`: KrakenOS `fan` pattern.
- `Fan X`: KrakenOS `fanx` pattern.
- `Fan Y`: KrakenOS `fany` pattern.
- `Hexapolar`: filled circular pupil sampling.
- `Square`: rectangular grid clipped to the pupil.
- `Random disk`: randomized pupil sampling with the configured random seed.

Random source modes use KrakenOS `SourceRnd` or compatible deterministic
Monte Carlo bundles instead of field/pupil sampling:

- `Random circle source`: source positions fill a circular source radius.
- `Random square source`: source positions fill a square half-width.
- `Random line source`: source positions fill a line from `-radius` to
  `+radius` along local X.
- `Random point cone`: all source positions start at the source origin, with
  randomized directions inside the cone.
- `Source radius [mm]`: radius or half-width passed to `SourceRnd.dim`.
- `Cone half-angle [deg]`: angular cone passed to `SourceRnd.field`.
- `Source power [arb]`: total source power used for per-ray statistics and
  random-source illumination throughput reports.
- `Random seed`: deterministic seed for repeatable source and random-pupil traces.
- `Source X/Y/Z [mm]`: launch-plane offset added to random-source ray origins.

Random source mode is useful for first-pass illumination and extended-emitter
checks. It intentionally bypasses field samples; the random bundle is traced as
one source distribution. Current KrakenOS ray tracing remains geometrically
unweighted; the UI reports `power/ray`, transmission, and collected power for
illumination analysis, but spot/MTF/PSF still treat traced rays uniformly.

The bundled `Random Source Illumination Example` layout demonstrates a finite
extended circular emitter traced through a simple collector lens.

Additional source examples:

- `Line Source Illumination Example`: shows a line emitter with source power
  and random-source throughput.
- `Point Cone Source Example`: shows a point emitter with randomized angular
  cone rays.

## Prescription table

### Editing

- click a cell to select it
- double-click or type into editable numeric cells
- right-click `Surface` and `Glass` for popup choices

The `Surface` popup intentionally exposes seven UI templates:

- `Object`: source/object plane.
- `Standard`: refractive, reflective-by-material, aspheric, axicon, custom,
  Zernike, error-map, UDA, STL, coating, and other advanced KrakenOS surface
  attributes through the main row plus `Advanced...`.
- `Aperture`: clear/obscuration stop row.
- `Mirror`: mirror row with folded-preview handling.
- `Thin Lens`: ideal thin lens; the `Rc` column is used as focal length.
- `Grating`: diffraction grating row using order, pitch, and line angle.
- `Image`: detector/image plane.

Cells that are not used by the selected UI template are shown gray and cannot
be edited directly. This is a UI-template restriction, not a KrakenOS core
limitation; use `Advanced...`, `Coating...`, and `Error Map...` for native
surface attributes that do not belong in the compact prescription columns.

Element grouping is UI metadata, not a KrakenOS surface attribute. Element
groups are shown by shared row background colors rather than by an editable
column.

When an older Zemax-style prescription has no saved element metadata, the
editor infers groups from the sequential glass/air transitions on load. A glass
element starts at the first non-air medium and includes the exit surface whose
following medium is `AIR`; aperture stops, mirrors, thin lenses, and gratings
become standalone elements.

### Selection

- click: single selection
- click the `#` column: select the whole colored element block
- `Ctrl` + click: toggle row selection
- `Ctrl` + click the `#` column: toggle the whole element block
- `Shift` + click: contiguous row range
- arrow keys move the active cell
- right-click a contiguous selection: `Group selected rows as element`
- right-click an element selection: `Ungroup element`

### Menu Bar Actions

- `↶`: undo
- `↷`: redo
- `Reset`: clear to Object/Image only without tracing
- `Layouts`
- `Machine Vision`
- `Examples`

`Reset` immediately returns the prescription table to only `Object` and
`Image`, clears the 2D plot and cached ray data, and does not build or trace the
system. The editor starts in this reset state; click `Update` only when you want
to trace the minimal starter system.

### Main Layout

The editor uses a full-height left Controls sidebar, a central table/plot
workspace, and a full-height right Panels sidebar. Click the small arrow in the
left or right sidebar header to hide that sidebar; click the exposed edge arrow
to restore it.

`Actions -> Copy Phase 2 Report` copies a compact source/fabrication report to
the clipboard and debug log. It lists the active source model, measured
error-map surfaces with PV/RMS, coating surfaces, and loaded metal catalogs.
For examples, load `Measured Error Map Example` or `Coating Polarization
Example`, click `Update`, then use `Actions -> Copy Phase 2 Report`.

### Table Toolbar Actions

- `Add surface`
- `Delete`
- `Duplicate`
- `Advanced...`
- `Coating...`
- `Error Map...`
- `Flip`
- `▲`
- `▼`

`▲` and `▼` move the selected row. If the selected row belongs to an element,
the full contiguous element block swaps with the adjacent element block or
single surface. `Object` and `Image` remain anchored.

### Component insertion workflow

Use the `Insert` menu when you want to add an optic into the current prescription
without changing the current source, field, pupil, wavelength, analysis, or
display settings.

Insertion point:

- Select a row first to insert the component below that row.
- Select any row in a grouped element to insert below that whole selected block.
- If no row is selected, the component inserts before the final `Image` row.

Available insert commands:

- `Insert` -> `Common Component`: inserts component-style common layouts such as
  lenses, mirrors, and F-theta lens components.
- `Insert` -> `Stock Lens Catalog...`: opens the Edmund/Thorlabs `.ZMF` stock
  lens importer and expands the selected part into table rows.
- `Insert` -> `Optical STL Solid...`: inserts a file-backed KrakenOS optical
  solid row.
- `Insert` -> `Component to Current Path View...`: inserts a path-local detector,
  aperture, thin lens, refractive surface, or mirror using the active Path view.

`Layouts` still means "load a layout". Full example/system layouts replace the
current prescription because they carry their own object distance, source, pupil,
analysis, and plot defaults. Use `Insert` when the intent is to splice an optic
into the design already on screen.

### Surface and element copy/paste

The table supports component-level clipboard operations:

- `Ctrl-C` copies the selected surface rows.
- If a selected row belongs to a grouped element, the whole contiguous element
  block is copied.
- `Ctrl-V` pastes copied rows below the current selection, or before `Image`
  when nothing is selected.
- `Object` and `Image` are never copied or pasted as component rows.
- Pasted grouped elements get independent element labels so Move Up/Down,
  Flip, Ungroup, and path assignment do not accidentally merge them with the
  source element.

The same commands are available from `Edit` and from the table right-click menu.

### Surface Right-Click Menu

Right-click any table cell, including the `Surface` cell, to open the grouped
surface workflow menu:

- `Convert Type`: Standard, Aperture, Mirror, Beam Splitter, Thin Lens,
  Grating, Image, or convert the selected row to a file-backed Optical STL
  Solid.
- `Insert Component Below`: singlet, doublet, flat mirror, plate/window, wedge
  prism, right-angle prism primitive, cube beam splitter primitive, stock lens,
  STL solid, or path-local component.
- `Shape / Aperture`: Shape Builder plus circular, rectangular, polygon/UDA,
  annulus, spider mask, and rectangular clear-aperture presets.
- `Material`: glass catalog browser plus quick AIR/BK7/F2/MIRROR application to
  selected rows.
- `Coating / Polarization`: coating editor, AR/mirror presets, beam-splitter
  settings, metal Fresnel mirror mode, and Fresnel P/S deterministic split mode.
- `Geometry`: align to previous local orientation, set TiltX incidence, reverse
  element, and place/assign rows along the current Path view.
- `Element`: group, ungroup, settings, copy, paste, move, path assignment, and
  path role.
- `Diagnostics`: trace target, analysis surface, Ray Inspector, Trace Path
  Inspector, Scene Graph, missed/clipped-ray inspection, and row validation.
- `Advanced`: native KrakenOS attributes, Shape Builder, Error Map, Grating
  settings, Galvo overlay, and STL diagnostics/placement.

The quick prism and cube beam splitter entries are table primitives. They are
useful starter components, but an arbitrary physical prism or closed cube with
all side faces is still best represented as `Optical STL Solid` so KrakenOS can
trace against the actual solid boundary.

### Tilt / Decenter Tolerance Overlay

The pose columns `TiltX`, `TiltY`, `TiltZ`, `DespX`, `DespY`, and `DespZ`
accept comma-separated values or `start:stop:step` ranges. Examples:

- `TiltY`: `-0.1, 0, 0.1`
- `DespX`: `-0.05:0.05:0.05`
- `TiltZ`: `[-0.2, 0, 0.2]`

The middle value becomes the nominal scalar KrakenOS row value. The full list is
stored under row `Advanced -> Display2D -> pose_tolerance_overlay` and the 2-D
plot overlays additional dashed ray traces plus dashed affected surface
positions. If several pose cells contain lists with the same length, they are
swept together by index. If lengths differ, combinations are generated and
truncated to 25 variants.

For grouped elements, enter the pose list once on any row in the element. The
UI applies the same delta sweep to every row in the contiguous element block, so
a doublet behaves like one mechanically shifted component instead of three
independent tilted/decentered surfaces.

Mirror `TiltX` keeps its dedicated galvo/folded-scan behavior, because its
display value is the physical mirror slant rather than the raw KrakenOS local
tilt. Use the same comma/range syntax there for scan overlays.

### Common Optical Layout insertion

Component-style common layouts insert after the last selected row.

If nothing is selected, they insert before the final `Image` row.

Currently insertable components include:

- `Single Lens`
- `Doublet Lens`
- `Ideal 2F Lens`
- `Flat Mirror 45 Deg`
- any common layout declaring `layout_role = "component"`, such as the F-theta
  lens component presets.

Full example/system layouts replace the current prescription instead of
splicing into it. This avoids accidentally mixing complete systems and expanding
the table into a physically invalid layout.

For folded/off-axis layouts, `Image dia mode = Auto` also clamps extreme traced
spot sizes to a multiple of the optical clear apertures. Use `Manual` when a
larger sensor plane is intentional.

### Attachment Zemax Examples

The `Examples` menu includes `Zemax Prescriptions (attachment)` when text `.zmx`
files are present under `attachment/zemax`. The scan is recursive and groups
files by subfolder, for example `Class 13`, `Class 15`, `Class9`, and `Top Level`.

Selecting one of these entries uses the same converter as `File` -> `Import
Zemax File...`, so it loads a complete prescription and applies the Zemax-derived
field, aperture, wavelength, and object-mode defaults. Use `Insert` instead when
you want to splice an optic into the current design without replacing settings.

Only text `.zmx` prescriptions are listed. Zemax `.SES` session files, PDFs, and
other sidecar files are intentionally not shown because the current importer does
not use them as optical prescriptions.

Validation:

```bash
python -m KrakenOS.UI.validate_testing_zemax_examples
python -m KrakenOS.UI.validate_attachment_paths
```

### Stock Lens Import

Use `File` -> `Import Stock Lens...` to insert off-the-shelf optics from Zemax
`.ZMF` catalogs. The importer currently searches:

- `attachment/Edmund Optics 2019.ZMF`
- `attachment/THORLABS_MAY_2024.ZMF`
- bundled fallback catalogs in `KrakenOS/LensCat`

Pick a catalog, search by part number or description, then click `Import
Selected`. The selected part expands into ordinary prescription-table rows at
the selected insertion point. If no row is selected, it inserts before `Image`.

Import options:

- `Reverse element`: flips the catalog prescription orientation.
- `Gap after`: sets the distance from the last imported surface to the next
  existing table row, usually the image plane.

After import, the editor refreshes the 2D preview and the rows can be edited,
optimized, saved, or combined with other common-layout elements.

Imported stock-lens rows are automatically grouped by part number, so Move
Up/Down keeps the whole catalog optic together.

Some vendor catalogs reference private glass names that are not directly usable
by KrakenOS. During stock-lens import, the UI converts known catalog glasses to
`nvk,n,V,0` from KrakenOS Nd/Vd data, and uses an approximate `nvk,1.5,50,0`
fallback for private glasses with no available index data. The affected row gets
a `Note` in its advanced attributes.

## Advanced Surface Column

The main prescription table intentionally stays compact. KrakenOS-native fields
that are too specialized for the main table are stored in each saved layout row
as an `advanced` dictionary.

Conceptually, `advanced` is an extra sidecar column for surface attributes:

```python
{
    "name": "Asphere + Zernike plate",
    "rc": 0.0,
    "thickness": 30.0,
    "diameter": 25.0,
    "glass": "AIR",
    "advanced": {
        "AspherData": [0.0, 1.0e-5, -2.0e-9],
        "ZNK": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.12],
        "SubAperture": [0.9, 0.0, 0.0],
        "Note": "Advanced attrs are replayed onto Kos.surf().",
    },
}
```

### How To Edit It In The UI

1. Select a surface row.
2. Click `Advanced...`, or right-click any row cell and choose `Advanced surface...`.
3. Enter Python literal values.
4. Click `Apply`.
5. Click `Update` to rebuild and trace the system.

For coating-only edits, select a surface row and click `Coating...`. This opens
a smaller coating/material dialog with `Clear / no coating`, broadband AR, and
protected-mirror presets, metal CSV loading, and validation for the KrakenOS
coating table.

For measured-surface edits, select a physical surface row and click `Error
Map...`. This opens an import/clear/validate dialog for KrakenOS
`Error_map = [X, Y, Z, SPACE]` data.

The dialog is split into:

- `Shape`
- `Aperture/Mask`
- `Coating/Material`
- `Diagnostics/Native`
- `Custom Surface`

### Supported `advanced` Attributes

Shape:

- `AspherData`: asphere coefficient list. Short lists are padded to KrakenOS's native length.
- `ZNK`: Zernike coefficient list. Short lists are padded to KrakenOS's native length.
- `Cylinder_Rxy_Ratio`: cylindrical/asymmetric radius ratio.
- `ShiftX`, `ShiftY`: local surface shape shift.
- `Surface_type`: KrakenOS native surface type marker.
- `Res`: surface mesh/sample resolution used by some custom surfaces.

Aperture/mask:

- `SubAperture`: `[scale, y_offset, x_offset]` in KrakenOS native order.
- `Mask_Type`: native mask mode. Non-zero modes usually also need `Mask_Shape`.
- `Mask_Shape`: native mask geometry object or literal-compatible data.
- `Solid_3d_stl`: STL-backed solid reference.

Coating/material:

- `Coating`: KrakenOS coating table `[R, A, W, THETA]`.
- `CoatingMet`: metal catalog index passed to KrakenOS Fresnel handling.
- `Color`: display color metadata.
- `Nm_Pos`: name-label position metadata.

`Coating` table meaning:

- `R`: reflectance values. Shape must be `len(THETA) x len(W)`.
- `A`: absorption values. Shape must match `R`.
- `W`: wavelength grid in microns.
- `THETA`: incidence-angle grid in degrees.
- `T`: not stored; KrakenOS infers transmission as `1 - R - A`.
- `[[], [], [], []]`: no explicit coating table; KrakenOS falls back to Fresnel/metal handling.

Rows in `R` and `A` follow the `THETA` grid, columns follow the `W` grid. The
runtime lookup linearly interpolates over wavelength and incidence angle, then
clamps `R`, `A`, and `T` to `[0, 1]`. Explicit coating tables override the
Fresnel values returned through `CoatingMet`; use `CoatingMet` for mirror metal
catalog behavior when no explicit coating table is present.

Metal catalog indices:

- `0`: built-in `Alum.csv`, loaded by `Kos.Setup()`.
- `1..N`: CSV files listed in `SETTINGS["metal_catalogs"]` in order.
- The `Coating...` dialog can add a metal CSV and assigns the matching
  `CoatingMet` index for the selected mirror surface.

Layout-level metal catalog example:

```python
from pathlib import Path

METAL_DIR = Path(__file__).resolve().parent.parent / "Cat"

SETTINGS = {
    "metal_catalogs": [
        {"name": "Gold", "path": str(METAL_DIR / "Gold.csv"), "type": 1},
    ],
}

SURFACES = [
    {
        "surface": "Mirror",
        "glass": "MIRROR",
        "advanced": {"CoatingMet": 1},
    },
]
```

Use `type = 0` for KrakenOS semicolon complex-metal tables like `Alum.csv`.
Use `type = 1` for the two-section `wl,n` / `wl,k` CSV format used by
`Gold.csv`.

Example:

```python
AR_COATING = [
    [[0.010, 0.008, 0.011], [0.018, 0.014, 0.020]],
    [[0.000, 0.000, 0.000], [0.000, 0.000, 0.000]],
    [0.45, 0.55, 0.65],
    [0.0, 45.0],
]
```

At `W = 0.55 um` and `THETA = 0 deg`, this gives `R = 0.008`, `A = 0`, and
`T = 0.992`. At intermediate angles/wavelengths, KrakenOS interpolates between
the nearest grid samples.

### Measured Error Maps

`Error_map` stores measured surface sag/departure samples:

```python
"advanced": {
    "Error_map": [X, Y, Z, SPACE],
}
```

Meaning:

- `X`: flattened x-coordinate samples in millimetres.
- `Y`: flattened y-coordinate samples in millimetres.
- `Z`: flattened sag/departure samples in millimetres.
- `SPACE`: scalar sample pitch in millimetres.

`X`, `Y`, and `Z` must have the same sample count. `SPACE` is scalar because
KrakenOS core constructs `error_map__surf(X, Y, Z, SPACE)` with one grid pitch.
The UI accepts `[dx, dy]` only when both values are equal, then stores the scalar.
If a map is entirely zero, clear `Error_map` instead of storing it.

Supported imports from `Error Map...`:

- `.csv`, `.txt`, `.dat`, `.tsv` with `x,y,z` columns and optional `space`.
- Headerless text with exactly three columns, interpreted as `x y z`.
- Other rectangular text or NumPy 2D arrays, interpreted as a Z matrix with
  generated unit-pitch X/Y coordinates.
- `.npz` files with `X`, `Y`, `Z`, and optional `SPACE`.
- `.npy` files containing `x/y/z` columns, stacked `X/Y/Z` grids, or a 2D Z matrix.

Example `.py` layout:

```python
import numpy as np

def measured_map():
    pitch = 1.0
    axis = np.arange(-5.0, 6.0, pitch)
    x_grid, y_grid = np.meshgrid(axis, axis)
    z_grid = 2.0e-4 * np.sin(np.pi * x_grid / 5.0) * np.cos(np.pi * y_grid / 5.0)
    return [x_grid.ravel().tolist(), y_grid.ravel().tolist(), z_grid.ravel().tolist(), pitch]

SURFACES = [
    {"surface": "Object", "name": "Object", "thickness": 40.0, "diameter": 15.0, "glass": "AIR"},
    {
        "surface": "Standard",
        "name": "Measured surface",
        "rc": 80.0,
        "thickness": 4.0,
        "diameter": 15.0,
        "glass": "BK7",
        "advanced": {"Error_map": measured_map()},
    },
    {"surface": "Image", "name": "Image", "thickness": 0.0, "diameter": 8.0, "glass": "AIR"},
]
```

The bundled `Measured Error Map Example` common layout demonstrates the same
pattern with a synthetic low-order measured departure. After changing or
importing a map, click `Update` to rebuild and trace the perturbed surface.

Diagnostics/native:

- `Note`: free-form note.
- `Order`: native surface order.
- `Var`: native KrakenOS optimization-variable metadata.
- `Error_map`: measured surface map `[X, Y, Z, SPACE]`.
- `SPECIAL_SURF_FUNC`: native special surface hook.
- `Const`: native constant list.

### Custom Surface Fields

The `Custom Surface` tab edits:

- `ExtraData`: custom sag/profile data.
- `UDA`: useful diameter area polygon/data.

Literal/list-based values are saved and replayed. Imported callable/object values
are preserved while the editor is open, but are read-only in the dialog and may
be omitted on save if they cannot be represented as Python literals.

For safe authoring and replay, `ExtraData` also accepts preset dictionaries:

```python
"extra_data": {
    "kind": "extra_surface",
    "preset": "radial_sine",
    "params": [5.0, 0.5],
}
```

Supported `ExtraData` presets:

- `xy_cosines`: `[period, amplitude]`
- `radial_sine`: `[period, amplitude]`
- `micro_lens_array`: `[pitch, radius, conic]`

`UDA` accepts a regular-polygon preset:

```python
"uda": {
    "kind": "regular_polygon",
    "radius": 14.0,
    "sides": 6,
    "rotation_deg": 30.0,
}
```

The Advanced Surface dialog includes a `Validate` button. It checks coating
table shape/ranges, measured error-map shape, UDA polygon shape, and runs a
small preview evaluation for `ExtraData` presets/callables before applying.

### Example Layout Files

See:

- `KrakenOS/common_optical_layouts/advanced_surface_zernike_example.py`
- `KrakenOS/common_optical_layouts/coating_polarization_example.py`
- `KrakenOS/common_optical_layouts/custom_surface_preset_example.py`
- `KrakenOS/common_optical_layouts/metal_mirror_example.py`

## Plot modes

Toolbar buttons:

- `Open 3D`
- `2D`
- `Native`
- `Spot`
- `PSF`
- `PSFMap`
- `RMS`
- `FC/Dist`
- `Illum`
- `Pol`
- `LatClr`
- `FieldMap`
- `IllumMap`
- `WfeMap`
- `Atmos`
- `Pupil`
- `Seidel`
- `Wavefront`
- `Zernike`
- `MTF`

### `2D`

Use this for the stable scene preview. The left Display panel's `Scene trace`
selector controls which KrakenOS tracing backend is used.

`Auto` now treats non-sequential scene tracing as the primary path when the
layout contains a physical source, beam splitter, off-axis/tilted geometry,
STL optical solid, target surface, or probabilistic non-sequential coating
request. Forced `Sequential` is still available for conventional axial
ordered-surface lens design and regression comparison.

### Mirror folds

Mirror rows use KrakenOS `TiltX` and transform data for their physical trace.
In the 2D editor, the displayed mirror line is the mirror aperture tangent in
the current folded branch. A `+45` and `-45` fold send the reflected branch in
opposite Y directions.

The Image plane after a tilted mirror belongs on the reflected branch. In
`Auto`, scene-style mirror/off-axis layouts resolve to non-sequential scene
tracing when KrakenOS `NsTraceLoop` is available. `Folded Preview` remains as a
legacy compatibility display scaffold. In forced `Sequential` mode the Object,
Aperture, Image, and Mirror drawing uses KrakenOS `TRANS_2A` transforms, so the
plotted Image location matches the core ray trace.

### Optical STL solids and funny-shape prisms

Use `File -> Import Optical STL Solid...` to insert a closed STL mesh as an
optical solid row. The command creates a normal editable surface row with:

- `advanced["Solid_3d_stl"]` set to the selected STL path;
- default `Material = BK7`;
- default `Thickness = 40 mm`;
- default `AxisMove = 2`.

After import, edit `Material`, `Tilt`, `Decenter`, `Thickness`, `Diameter`, and
`AxisMove` exactly like any other row. In `Auto`, the `Scene trace` selector
resolves to `Non-Sequential Preview` because STL solids need KrakenOS
`NsTraceLoop`; sequential tracing is not a physical model for arbitrary closed
prisms. The 2D plot draws the projected STL footprint as a blue outline so the
solid body is visible separately from the ray bundle and row-plane marker.

To place a prism with the correct orientation:

1. Select the STL row in the editable table.
2. Open `Actions -> Place/Orient Selected STL Solid`.
3. Choose which STL local axis should point along the layout optical axis
   (`+Z`). For example, choose `+Z` when the STL was modeled with its optical
   length along local Z, or `+X` when it was modeled along local X.
4. Leave `Center rotated STL X/Y on layout axis` enabled for first placement.
5. Enable `Place rotated STL minimum Z on this row plane` when you want the
   mesh's front-most face to sit on the selected row station.
6. Apply, then click `Update`.

Important placement semantics:

- The previous row's `Thickness` sets the selected STL row's nominal Z station.
- `TiltX/Y/Z` rotate the STL mesh about the STL file origin.
- `DespX/Y/Z` translate the rotated STL mesh.
- `AxisMove` controls KrakenOS transform propagation to later rows; it is not
  the local STL orientation itself.

Practical rules:

- The STL file should be closed/manifold and have correct face normals.
- KrakenOS interprets the mesh dimensions in millimetres.
- The row `Material` controls refraction; the STL file carries geometry only.
- Use `Actions -> Inspect Optical STL Solids` to check triangle count, bounds,
  open boundary edges, non-manifold edges, degenerate triangles, signed volume,
  and likely face winding. A `CHECK` result means the prism may trace, but the
  mesh should be fixed before trusting physical steering/refraction.
- Use `Actions -> Non-Sequential Scene Graph` to verify the row lists `STL solid`
  plus mesh diagnostics, and `Actions -> Trace Path Inspector` to inspect hits
  through the solid.

Direct API example:

```bash
python KrakenOS/Examples/Examp_Phase6_Optical_STL_Prism.py
```

### `FieldMap`

Use this for the first Phase 3 wide-field image-quality map. The UI builds an
X/Y field grid from `Field value` and `Field samples`, traces each field point,
and plots geometric spot RMS as a heatmap. It uses `Pupil / field` sampling;
random source modes are for illumination throughput rather than field maps.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode field_map \
  --file KrakenOS/common_optical_layouts/wide_field_spot_map_example.py \
  --output /tmp/kraken_field_map.jpg
```

### `PSFMap`

Use this for the Phase 3 wide-field PSF image map. It uses the same X/Y field
grid as `FieldMap`, traces each field point, and renders a tiled normalized
geometric PSF thumbnail per field. It uses `Pupil / field` sampling.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode psf_map \
  --file KrakenOS/common_optical_layouts/wide_field_psf_map_example.py \
  --output /tmp/kraken_psf_map.jpg
```

### `IllumMap`

Use this for the Phase 3 wide-field relative illumination map. It uses the same
X/Y field grid as `FieldMap`, traces each field point, and normalizes
transmission to the nearest on-axis field sample. Use `Illum` instead when
working with random-source throughput.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode illum_map \
  --file KrakenOS/common_optical_layouts/wide_field_illumination_map_example.py \
  --output /tmp/kraken_illum_map.jpg
```

### `WfeMap`

Use this for the Phase 3 wide-field wavefront RMS map. It uses the same X/Y
field grid as `FieldMap`, computes wavefront phase at each field point, removes
piston, and plots RMS in waves. It uses `Pupil / field` sampling.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode wavefront_map \
  --file KrakenOS/common_optical_layouts/wide_field_wavefront_map_example.py \
  --output /tmp/kraken_wfe_map.jpg
```

### `Wavefront`

Use this for single-field wavefront inspection. The `Wavefront style` control
in the Display panel selects how the sampled KrakenOS phase is shown:

- `Wavefront Function`: default Zemax-style wireframe OPD surface over the
  normalized pupil, rendered without 3D axes and with a report strip. It removes
  the best-fit piston/tilt reference plane and reports P-V/RMS in waves.
- `Phase (unwrapped)`: raw phase in waves.
- `Wrapped phase`: phase folded into the `-0.5` to `+0.5` wave interval.
- `Interferogram`: relative fringe intensity from `cos(2*pi*phase)`.
- `Slope X`: pupil X derivative in waves per normalized pupil coordinate.
- `Slope Y`: pupil Y derivative in waves per normalized pupil coordinate.
- `Slope magnitude`: combined `sqrt((dW/dX)^2 + (dW/dY)^2)` slope.

The Information panel reports style, sample count, phase method, P-V, RMS, and
display range. Saved layouts store the selected style as `wavefront_style`.

Examples:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode wavefront \
  --file KrakenOS/common_optical_layouts/wavefront_function_example.py \
  --output /tmp/kraken_wavefront_function.jpg

./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode wavefront \
  --file KrakenOS/common_optical_layouts/wavefront_wrapped_phase_example.py \
  --output /tmp/kraken_wavefront_wrapped.jpg

./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode wavefront \
  --file KrakenOS/common_optical_layouts/wavefront_interferogram_example.py \
  --output /tmp/kraken_wavefront_interferogram.jpg

./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode wavefront \
  --file KrakenOS/common_optical_layouts/wavefront_slope_map_example.py \
  --output /tmp/kraken_wavefront_slope.jpg
```

### `Atmos`

Use this for Phase 3 atmosphere analysis. The Atmosphere panel controls
wavelength range, zenith angle, temperature, pressure, humidity, CO2, latitude,
and altitude. Observatory presets from KrakenOS fill the weather/site fields
while leaving wavelength range and zenith angle editable.

The `Atmos plot` control selects the workflow:

- `Refraction / dispersion`: absolute atmospheric refraction and chromatic
  dispersion relative to the current wavelength.
- `Image residual (current optics)`: traces atmospheric field bundles through
  the current table and plots residual image centroid shift. If the table
  contains ADC/prism surfaces, the plot shows the residual after those optics.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode atmosphere \
  --file KrakenOS/common_optical_layouts/atmospheric_dispersion_example.py \
  --output /tmp/kraken_atmosphere.jpg

./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode atmosphere \
  --file KrakenOS/common_optical_layouts/atmospheric_image_residual_example.py \
  --output /tmp/kraken_atmosphere_residual.jpg
```

### `Zernike`

Use this for the Phase 3 wavefront fitting workflow. It computes the current
wavefront phase, fits KrakenOS Zernike coefficients, plots the fitted
coefficients, and fills the `Information` panel with term count, P-V/RMS,
residual RMS/P-V, fitting error, and coefficient rows. Use
`Actions -> Copy Wavefront Fit Report` to copy the latest fit as text.

Example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode zernike \
  --file KrakenOS/common_optical_layouts/wavefront_zernike_fit_example.py \
  --output /tmp/kraken_zernike_fit.jpg
```

### `Native`

Use this for the folded-native debug/display path.

It shows:

- native-derived optical surfaces
- native-gated rays
- native surface diagnostics in `Information` and `Debug`

### Current folded limitation

For folded preview layouts, not every analysis mode is available yet.

That is expected. Folded-native analysis is still being built out.

### `Pol`

Use this for coating and polarization diagnostics.

The plot is built from KrakenOS `raykeeper` arrays:

- `TP`, `TS`: P/S transmission energy at each hit.
- `RP`, `RS`: P/S reflection energy at each hit.
- `TTBE`: per-hit throughput including bulk transmission.
- `TT`: cumulative ray throughput.

The `Information` panel also reports:

- coating attribute surface count
- mean total throughput
- image-reaching ray throughput
- mean `TP / TS`
- mean `RP / RS`
- mean P/S split

Headless snapshot example:

```bash
./.devenv/state/venv/bin/python -m KrakenOS.UI.render_layout_snapshot \
  --mode polarization \
  --layout "Coating Polarization Example" \
  --output /tmp/kraken_polarization.jpg
```

## Ray Inspector Columns

Click `Trace` to open the Ray Inspector.

Ray table:

- `Ray`: preview ray index.
- `Field`: field sample index.
- `Branch`: branch id. Currently `0` for the single-path preview bridge.
- `Status`: whether the ray reached the image surface or stopped early.
- `Termination`: reason such as `image`, `no_hit`, or `stopped_at_surface_N`.
- `Hits`: number of recorded surface hits.
- `Last`: last hit surface.
- `Target`: target image surface index.
- `Dist`: summed geometric distance.
- `OP`: summed optical path.
- `TT`: cumulative throughput.

Hit table:

- `L/M/N in`: incoming direction cosines.
- `L/M/N out`: outgoing/reflected/refracted direction cosines.
- `n0`, `n1`: refractive index before and after the hit.
- `Rp`, `Rs`: P/S reflection energy.
- `Tp`, `Ts`: P/S transmission energy.
- `TTBE`: per-hit throughput including bulk transmission.

## Optimization workflow

### Mark variables

Right-click a supported numeric cell.

Currently useful variable types include:

- `Radius`
- `Thickness`

Thickness optimization now supports:

- `Object`
- `Mirror`
- `Standard`
- `Thin Lens`
- `Grating`

`Image` remains excluded.

### Bounds

Right-click the same cell and choose:

- `Set bounds...`
- `Clear bounds`

### Operand setup

In the `Optimization` panel:

1. select one or more merit operands
2. configure per-operand fields such as:
   - `Weight`
   - `Target`
   - `Wvl`
   - `Field`
   - `Surf`
   - `Aper`
   - `AVal`
   - `Freq`
   - `Mode`
3. click `Start Optimization`

### Example: optimize a mirror distance

1. load `Double Mirror Fold`
2. right-click `Mirror 2` `Thickness`
3. select it for optimization
4. choose operand `Spot RMS`
5. click `Start Optimization`

### Example: optimize a singlet radius

1. load `Single Lens`
2. right-click front or back `Rc`
3. select it for optimization
4. set bounds
5. choose operand `Spot RMS` or `Wavefront RMS`
6. click `Start Optimization`

## Native folded workflow example

### Default folded system

The default startup layout is a folded mirror + singlet system.

Use it like this:

1. launch the editor
2. keep `Orientation = Horizontal`
3. use `Native`
4. inspect:
   - lens body
   - mirror overlays
   - rays
   - `Information`
   - `Debug`

### Insert a doublet after the singlet

1. click the row where insertion should happen
   - usually after the singlet back surface
2. choose `Doublet Lens` from `Layouts`
3. confirm the inserted rows appear immediately after the selected row
4. use `▲` / `▼` only for fine adjustment after insertion

## Files and persistence

### Save

- `File -> Save`
- `File -> Save As`

Saved Python layout files preserve optimization marks and bounds.

### Open

- `File -> Open`

## Diagnostics

### `Debug`

Use this for:

- native hit sequence information
- native overlay metrics
- fallback/error messages

### `Progress`

Use this for:

- optimization progress
- long analysis generation steps

### Headless snapshots

Use the headless renderer for reproducible image inspection when debugging visual issues.

## Known limitations

- folded-native display is ahead of folded-native analysis
- complex common layouts replace the current prescription rather than inserting
- native folded view still uses a readable scaffold for placement; it is not a raw Kraken projection view
