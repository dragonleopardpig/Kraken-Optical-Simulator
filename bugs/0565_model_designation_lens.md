# 0565 — a vendor drawing title block still yields the lens

`error.png`: swapping to `attachment/Lens/ELS-85-4.5V16K` refused with

> No Zemax .zmx prescription, no System/Prescription Data dump, and the datasheet PDF did not
> yield an effective focal length; cannot derive the lens optics.

## Why it refused

The folder is not short of information — it carries the vendor spec PDF **and** a 4.9 MB STEP.
The problem is the *shape* of the PDF: AZURE Photonics ships a CAD **drawing title block**, not a
spec table, so the flattened text extraction delaminates every label from its value:

```
...(Focal Length)F.O.V(DxVxH)...26mmD85mmELS-85/4.5V16Kg10-4141.85mm4.5Manual93.7%V196.8mm...
```

All 673 characters are like that — labels in one run, numbers in another. No `f'eff [mm]`,
`Focal length [mm]` or bugs/0371 `focal length f' (mm)` pattern can pair a label with a number,
so `parse_datasheet_cardinals` returned `None` and Path C refused. The refusal was correct given
what it could see; it just wasn't looking at the one token that survived.

## The token that survives

`ELS-85/4.5` is the vendor's own designation: an 85 mm f/4.5. The user's hand-built
`machine_vision_AZ85_RA_Mirror` surrogate for *this exact folder* corroborates it — an
`Aperture Stop F/4.5` of diameter **18.8889 = 85/4.5**, and a 55 mm front-to-rear vertex span
that the bundled STEP body reproduces independently.

So the fix adds `model_designation_cardinals(text)` as the **last** source, after every labelled
pattern has already returned `None`.

## Containing the risk

The same flattened text is full of decoys — `10-4141.85mm`, a bare `F/4.5`, `V16K-A142mm`. Two
constraints keep this from becoming number-soup:

* the token must be `LETTERS-<number>/<number>`, so a bare `F/4.5` or a date-like `10-41` cannot
  match, and the numbers must be in range (1–2000 mm, f/0.5–f/64);
* the focal length must be **corroborated** by the same number appearing as `<n>mm` elsewhere in
  the sheet (here `D85mm`, the orphaned Focal Length value).

Uncorroborated, it returns `None` and the importer refuses exactly as before. A silently wrong
prescription is far worse than a clear "cannot derive the lens optics".

One detail cost a run: the designation is **glued** to the previous value (`...26mmD85mmELS-85...`),
so there is no word boundary before `ELS`. The first attempt anchored on `\b` and matched nothing.
The guard pins this case specifically.

## Result

`import_lens_folder("attachment/Lens/ELS-85-4.5V16K")` now builds
`machine_vision_els_85_4_5v16k.py`: EFL 85 mm, F/4.5, 55 mm span taken from the STEP body extent —
the same span as the hand-built AZ85. The two-group split differs (f = 137.802, d = 52.2 versus the
hand-built f = 159.489, d = 19.723); both are valid symmetric EFL-equivalents and the generated
file says so: *"the principal-plane split is nominal"*.

## Guard

`KrakenOS/UI/validate_open3d_0565_model_designation_lens.py` (penta phase 440), pure — no PDF
needed, the real 673-character extraction is inlined as the fixture: the ELS token yields 85/4.5
even when glued; a bare `F/4.5`, a date-like `10-41/2` and out-of-range designations are refused;
an uncorroborated designation is refused; and a labelled `f'eff` row is still tried first.

## Not fixed here

Swapping *to* this lens then exposed a separate, real bug — the fold mirror moves 51 mm off the
leg. That is bugs/0566, tracked separately.
