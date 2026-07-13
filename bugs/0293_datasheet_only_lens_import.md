# 0293 — Datasheet-only lens import (+ folder importer in Open 3D)

The user dropped a real vendor lens folder and hit an error on import:

> *It gives error about Zemax file. Not every vendor happily provide Zemax file or Blackbox. Most of the
> time is unavailable, please make sure the surrogate can be made from datasheet only if zemax file is
> absent, and please make the Import available in 3D as well.*

Two parts: **(A)** build the first-order surrogate from the **datasheet PDF alone** when no `.zmx` and no
Black-Box dump exist (the common case), and **(B)** expose *Import Lens from Folder* in the Open 3D view,
not just the 2D layout editor.

## The folder importer before this change
`build_surrogate_from_assets` had two optical sources, tried in order:

* **Path A** — a readable Zemax `.zmx` sequential prescription → `Parax` → exact `(EFL, ppa, ppp, span)` →
  `solve_two_thin_groups` reproduces all four cardinals.
* **Path B** — a Black-Box *System/Prescription Data* text dump (encrypted surfaces) → EFL + span only →
  `solve_symmetric_two_groups` (nominal principal-plane split).

A folder with only a datasheet PDF had `has_optical_source == False`, so import raised *"No Zemax .zmx
prescription and no System/Prescription Data dump was found…"* — exactly the error the user saw.

## Part A — Path C: cardinals from the datasheet spec table
The Schneider/PYRITE datasheet spec table lists the first-order cardinals directly. Crucially it lists **both
focal distances**, so **both principal planes** are recoverable and the *exact* two-group solve (as Path A,
not the Path B symmetric fallback) applies:

| datasheet field | meaning | used as |
|---|---|---|
| `f'eff [mm]` | effective focal length | `EFL` |
| `SF [mm]` (negative) | first vertex → front focal point | `ppa = SF + f'eff` |
| `S'F' [mm]` (positive) | last vertex → back focal point | `ppp = S'F' − f'eff` |
| `HH' [mm]` | inter-principal-plane distance | cross-check only |
| `d [mm] Σ` (Σd) | first → last vertex span | the two-group `span` |
| `F/… …` | F-number | stop `= EFL / FNO` |
| `Max. sensor size [mm]` | image-circle diameter | image aperture |
| title `1.0x` / `0.5x` | nominal magnification | negated → finite conjugate |

The self-consistency guard is `HH' = span − ppa + ppp`; it must equal the datasheet `HH'`. On the user's
dropped folder it lands **−1.31 mm vs datasheet −1.31 mm** — the solve is exact, not fitted.

### Pure-stdlib PDF text extraction (no new dependency)
Per the tooling-simplicity rule (must work for any GitHub user, download nothing), the extractor is
`zlib` + regex only — no PDF library. The Schneider PDFs are mPDF output using **subset CID fonts**
(`MPDFAA+` prefix, 2-byte glyph codes), so:

* content streams are `FlateDecode` (zlib-inflate); **ToUnicode CMaps are uncompressed plaintext** — so a
  failed `zlib.decompress` returns the raw bytes rather than erroring;
* a single merged CMap collides across fonts, so the decoder tracks the active `/Fn Tf` and switches
  **per-font ToUnicode CMaps** (`/F1`…`/F7` are global/stable);
* a `TJ` advance more negative than −90 is emitted as a space so the table tokens separate.

`Σd` anchors on the Σ glyph (U+03A3, appears once) because the `d` glues onto the previous number
(`"22.26d [mm]Σ43.19"`) and defeats a `\bd` word boundary.

### The optics build (`_core_from_datasheet` → `_core_from_datasheet_cardinals`)
Split so the cardinals→optics step is unit-testable without a real PDF:

* span = datasheet `Σd` (keeps the cardinals self-consistent) else the STEP body extent else `EFL/3`;
* `has_principal_planes` (both SF & S'F' present) → `solve_two_thin_groups(EFL, ppa, ppp, span)` (exact),
  else `solve_symmetric_two_groups(EFL, span)` (honest Path-B-style fallback);
* conjugate from the datasheet nominal magnification (`_finite_conjugate_gaps`), else object at infinity;
* stop `= EFL / FNO`; image dia `= Max. sensor size`; object dia `= image dia / |m|` (finite);
* graceful degrade: an unreadable / EFL-less PDF raises a clear build error (surrogate not fabricated).

`has_optical_source` now also counts a datasheet PDF, and `scan_lens_folder` adds a *"Datasheet-only lens…"*
note when the PDF is the sole source.

## Part B — Import Lens from Folder in Open 3D
The editor method `LayoutTableWorkbenchMixin.import_machine_vision_lens_from_folder` grew a `dialog_parent`
kwarg (re-parents the folder chooser / error dialog to the 3D window) and now **returns** the built
`SurrogateModel` (or `None` on cancel / failure). `Kraken3DInspector.import_machine_vision_lens_from_folder`
delegates with `dialog_parent=self`, and — on a non-`None` model — clears transient STEP carry / rotation /
selection state before `refresh_from_editor(force_retrace=True)` rebuilds the scene from the loaded layout.
A new *"Import Lens from Folder…"* command sits at the top of the Open 3D **CAD** menu
(`open3d_top_controls.py`).

## Files
- `KrakenOS/UI/services/datasheet_prescription_import.py` — **NEW**, pure-stdlib PDF → `DatasheetCardinals`.
- `KrakenOS/UI/services/machine_vision_folder_import.py` — Path C wiring (`_core_from_datasheet`,
  `_core_from_datasheet_cardinals`, `has_optical_source`/dispatch/notes/errors).
- `KrakenOS/UI/services/layout_table_workbench.py` — `dialog_parent` kwarg + returns the model.
- `KrakenOS/UI/open3d_inspector.py` — `import_machine_vision_lens_from_folder` (delegate + refresh).
- `KrakenOS/UI/panels/open3d_top_controls.py` — CAD-menu command.

## Verified end-to-end (real dropped folder, no display)
`attachment/Lens/PYRITE_56_80_10x_V38_1097785` (datasheet PDF only — no `.zmx`, no dump):

| quantity | datasheet | built surrogate | via |
|---|---|---|---|
| EFL | 82.39 | **82.39** | Parax |
| ppa / ppp | 22.25 / −22.25 | **22.25 / −22.25** | exact two-group solve |
| span (Σd) | 43.19 | **43.19** | datasheet vertex span |
| HH' cross-check | −1.31 | **−1.31** | span − ppa + ppp |
| object mode | 1.0x | **Finite** (m = −1.0, 2f–2f) | |

5 of the 6 bundled PYRITE datasheets parse cleanly (the sole miss, `PYRITE_F5.6_120_0.5x`, is a PDF-1.7 from
a different producer and a **redundant duplicate** of lens ID 1097787 whose mPDF twin parses perfectly — the
extractor degrades to `None` → clear build error, no fabricated optics; a universal PDF parser would violate
the tooling-simplicity rule).

## Guard + gate
`KrakenOS/UI/validate_datasheet_lens_import.py` (`run_checks()`) — display-free, deterministic (synthetic
cardinals modelled on the real 80 mm lens, no vendor assets required): `DatasheetCardinals`
ppa/ppp/HH-cross-check/object_mode; `_core_from_datasheet_cardinals` exact solve reproduces
EFL/ppa/ppp/span/stop/apertures + symmetric 2f–2f conjugate; emit→discover→reload→`Parax`→trace round-trip;
symmetric fallback when SF/S'F' absent; `has_optical_source` includes a PDF while an unreadable stub still
raises; **3D wiring contract** (`inspect.getsource`: inspector delegates with `dialog_parent=self` +
`if model is None` + `refresh_from_editor`; editor `dialog_parent=None` returns the model; top-controls
command present); **real vendor PDF when present** (EFL ≈ 82.39, both principal planes, HH cross-check
< 0.1). Penta **phase 257**, baseline updated.

`validate_machine_vision_folder_import.py` was updated (the has-optical-source change made a stub PDF a Path C
candidate): a truly source-less folder still raises, and a stub-PDF folder is a candidate but degrades to a
`ValueError` on the unreadable PDF.

## Note / remaining
Path C targets the Schneider/PYRITE mPDF spec-table layout. Other vendors' datasheets will need their own
field regexes / font handling; the extractor already degrades gracefully (returns `None` → the same clear
build error), so an unrecognised datasheet never fabricates a wrong surrogate.
