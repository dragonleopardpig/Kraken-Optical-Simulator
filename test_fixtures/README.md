# test_fixtures/ -- the validators' input scenes, kept in git

The validators read their scenes from `attachment/`, which git ignores and Filen syncs. A scene lost
there (a Filen trash, a snapshot restore, a fresh machine) used to make its validators SKIP or fail
quietly. The files listed in `MANIFEST.txt` are kept here, at the same paths relative to
`attachment/`:

```
python tools/validator_fixtures.py --check      # which fixtures are missing / differ in attachment/
python tools/validator_fixtures.py --restore    # copy every MISSING one back (never overwrites)
python tools/validator_fixtures.py --update om05a_folded.py   # adopt an intended scene change
```

Both penta gates run `--restore` before they start.

## What is deliberately NOT here

- **Vendor CAD and datasheets.** This repository is public. That covers the camera, lens, LED and
  prism STEP files and their PDFs. Validators needing them skip cleanly when they are absent.
- **What validators WRITE.** Reference renders, reports, synthetic recordings and the
  `perf_ns_trace` meshes are outputs; they are also excluded from Filen in `attachment/.filenignore`.
- **Caches** such as `cad_cache/`, which regenerate from their sources.
