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

## Prescription table

### Editing

- click a cell to select it
- double-click or type into editable numeric cells
- edit `Element` to assign rows to an optical component group
- right-click `Surface` and `Glass` for popup choices

`Element` is a UI grouping flag, not a KrakenOS surface attribute. Give the
same non-empty value to contiguous rows that belong to one physical component,
for example both surfaces of `Doublet-1` or all imported rows for Thorlabs part
`AC254-050-A`. The table highlights grouped rows with a shared background
color. Blank `Element` rows are treated as individual surfaces.

When an older Zemax-style prescription has no saved `Element` metadata, the
editor infers groups from the sequential glass/air transitions on load. A glass
element starts at the first non-air medium and includes the exit surface whose
following medium is `AIR`; aperture stops, mirrors, thin lenses, and gratings
become standalone elements.

### Selection

- click: single selection
- `Ctrl` + click: toggle row selection
- `Shift` + click: contiguous row range
- arrow keys move the active cell

### Toolbar actions

- `Add surface`
- `Delete`
- `Duplicate`
- `Advanced...`
- `Flip`
- `▲`
- `▼`
- `Common Optical Layout`
- `Examples`

`▲` and `▼` move the selected row. If the selected row has a non-empty
`Element` value, the full contiguous element block swaps with the adjacent
element block or single surface. `Object` and `Image` remain anchored.

### Common Optical Layout insertion

Component-style common layouts insert after the last selected row.

If nothing is selected, they insert before the final `Image` row.

Currently insertable components are:

- `Single Lens`
- `Doublet Lens`
- `Ideal 2F Lens`
- `Flat Mirror 45 Deg`

Full example/system layouts replace the current prescription instead of
splicing into it. This avoids accidentally mixing complete systems and expanding
the table into a physically invalid layout.

For folded/off-axis layouts, `Image dia mode = Auto` also clamps extreme traced
spot sizes to a multiple of the optical clear apertures. Use `Manual` when a
larger sensor plane is intentional.

### Stock Lens Import

Use `File` -> `Import Stock Lens...` to insert off-the-shelf optics from Zemax
`.ZMF` catalogs. The importer currently searches:

- `testing/Edmund Optics 2019.ZMF`
- `testing/THORLABS_MAY_2024.ZMF`
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

Imported stock-lens rows automatically get their part number in the `Element`
column, so Move Up/Down keeps the whole catalog optic together.

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
- `RMS`
- `FC/Dist`
- `Illum`
- `Pol`
- `LatClr`
- `Pupil`
- `Seidel`
- `Wavefront`
- `MTF`

### `2D`

Use this for the stable folded preview.

### Mirror folds

Mirror rows use KrakenOS `TiltX` and transform data for their physical trace.
In the 2D editor, the displayed mirror line is the mirror aperture tangent in
the current folded branch. A `+45` and `-45` fold send the reflected branch in
opposite Y directions.

The Image plane after a tilted mirror belongs on the reflected branch. In
`Auto` / `Folded Preview` this is built from the folded display scaffold. In
forced `Sequential` mode the Object, Aperture, Image, and Mirror drawing now
uses KrakenOS `TRANS_2A` transforms, so the plotted Image location matches the
core ray trace.

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
2. choose `Doublet Lens` from `Common Optical Layout`
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
