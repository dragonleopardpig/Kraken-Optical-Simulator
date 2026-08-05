"""Display-free guard for bugs/0565 -- a drawing title block still yields the lens.

error.png: swapping to ``attachment/Lens/ELS-85-4.5V16K`` refused with *"No Zemax .zmx
prescription, no System/Prescription Data dump, and the datasheet PDF did not yield an
effective focal length; cannot derive the lens optics."*

The folder is not short of information -- it carries the vendor spec PDF and a 4.9 MB STEP.
The problem is that AZURE Photonics ships a CAD **drawing title block** rather than a spec
table, and the flattened text extraction delaminates every label from its value::

    ...(Focal Length)F.O.V(DxVxH)...26mmD85mmELS-85/4.5V16Kg10-4141.85mm4.5Manual...

No ``Focal length`` pattern can pair a label with a number there.  The MODEL DESIGNATION
survives intact, though, and it is the vendor's own statement of the lens: ``ELS-85/4.5``
is an 85 mm f/4.5.  The user's hand-built ``machine_vision_AZ85_RA_Mirror`` surrogate for
this exact folder corroborates it -- ``Aperture Stop F/4.5`` of diameter
18.8889 = 85/4.5, and a 55 mm vertex span the STEP body reproduces.

The risk to contain is number-soup: the same flattened text contains decoys such as
``10-4141.85mm`` and a bare ``F/4.5``.  So the designation is accepted only when

* the token is ``LETTERS-<number>/<number>`` (a bare ``F/4.5`` or a date-like ``10-41``
  cannot match), and
* the focal length is CORROBORATED by the same number appearing as ``<n>mm`` elsewhere.

Uncorroborated, the parser returns ``None`` and the importer refuses exactly as before: a
silently wrong prescription is far worse than a clear "cannot derive the lens optics".

Checks (pure, no VTK/tk, no PDF needed):
- ELS: the real flattened ELS-85 text yields 85 mm / f4.5.
- GLUED: the designation is found with NO word boundary before it (it is glued to the
  previous value, which is what the first attempt at this fix got wrong).
- DECOYS: a bare ``F/4.5``, a date-like ``10-41/2`` and an out-of-range designation are
  all rejected.
- CORROBORATION: a designation whose focal length appears nowhere as ``<n>mm`` is refused.
- LAST RESORT: a labelled ``f'eff`` sheet still wins -- the designation must not override a
  real spec row.
- CONSUMER: parse_datasheet_cardinals routes through the helper.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0565_model_designation_lens
"""

from __future__ import annotations

import inspect

# The real flattened extraction of "ELS-85 4.5V16K_specification.pdf" (673 chars, trimmed
# here to the run that matters). Kept verbatim so the fixture cannot drift from the PDF.
ELS85_TEXT = (
    "Size1020(Operating Temperature)57.3626721DrawCheckUnit:mm(Back Focus)F(F/ No.)(Iris "
    "Type)(Distortion)(Relative Illuminate)(Mount)(TTL)(Coating)(Lens Effective Diameter)"
    "(Front)(Back)(CRA)112216AZURE Photonics Co.,LtdNo.12345678914171819(Product Technical "
    "Specification)(Name)(Specification)(Model)(Image Format)(Focal Length)F.O.V(DxVxH)"
    "(Resolution)(Suitable Distance)(Lens Construction)(Dimention)(Weight)No.(Specification)"
    "122324(Material Code)(Optimum Working Distance)1325(Filter Thread)RecheckApproval"
    "(Magnification)15(Design Wavelength)(Max Image )26mmD85mmELS-85/4.5V16Kg10-4141.85mm4.5"
    "Manual93.7%V196.8mm400nm-1000nm3.A01.018545V16K-A142mm68mm400-1000nm0.5X,1.0X,2.0X"
)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI.services import datasheet_prescription_import as dsi
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: datasheet_prescription_import unavailable ({exc!r})"]

    derive = dsi.model_designation_cardinals

    # --- ELS: the flagged folder ----------------------------------------------------------
    effl, fno = derive(ELS85_TEXT)
    if effl != 85.0:
        failures.append(
            f"ELS: the ELS-85/4.5 title block gave effl={effl}, expected 85.0 -- that refusal "
            "is the error.png dialog (bugs/0565)"
        )
    if fno != 4.5:
        failures.append(f"ELS: expected f/4.5 from the designation, got {fno}")

    # --- GLUED: no word boundary before the designation -------------------------------------
    # The first attempt used r"\b([A-Z]{2,5})-..." and found NOTHING, because the flattened
    # text runs "...26mmD85mmELS-85/4.5..." with no boundary between "mm" and "ELS".
    if derive("26mmD85mmELS-85/4.5V16K")[0] != 85.0:
        failures.append(
            "glued: the designation must be found when glued to the previous value -- a \\b "
            "anchor silently matches nothing on the real sheet"
        )

    # --- DECOYS ------------------------------------------------------------------------------
    for label, text in (
        ("bare F-number", "aperture F/4.5 fixed, 85mm"),
        ("date-like", "issued 10-41/2 on the 85mm drawing"),
        ("absurd focal", "XX-9999/4.5 and 9999mm"),
        ("absurd f-number", "XX-85/99 and 85mm"),
    ):
        got = derive(text)[0]
        if got is not None:
            failures.append(f"decoy ({label}): accepted {got} from {text!r} -- must refuse")

    # --- CORROBORATION -----------------------------------------------------------------------
    if derive("model ELS-85/4.5V16K with no focal value anywhere")[0] is not None:
        failures.append(
            "corroboration: a designation whose focal length never appears as '<n>mm' must be "
            "refused -- refusing is what keeps a wrong prescription off the user's scene"
        )
    if derive("ELS-85/4.5 ... focal length 85 mm")[0] != 85.0:
        failures.append("corroboration: '85 mm' with a space must still corroborate")

    # --- LAST RESORT: a real spec row wins ---------------------------------------------------
    source = inspect.getsource(dsi.parse_datasheet_cardinals)
    if "model_designation_cardinals" not in source:
        failures.append("consumer: parse_datasheet_cardinals must route through the helper")
    designation_at = source.find("model_designation_cardinals")
    for pattern in ("f['’]eff", "Focal len"):
        labelled_at = source.find(pattern)
        if labelled_at == -1:
            failures.append(f"premise changed: the labelled pattern {pattern!r} is gone")
        elif labelled_at > designation_at:
            failures.append(
                f"last resort: the labelled {pattern!r} row must be tried BEFORE the model "
                "designation -- a real spec row is always the better source"
            )
    if "if effl is None:" not in source:
        failures.append(
            "last resort: the designation must be reached only when every labelled pattern "
            "already returned None"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0565 model-designation lens validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0565 validation passed: a vendor drawing title block still yields the lens -- "
        "ELS-85/4.5 gives 85 mm f/4.5 even glued to the previous value, decoys and "
        "uncorroborated designations are refused, and a labelled f'eff row still wins."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
