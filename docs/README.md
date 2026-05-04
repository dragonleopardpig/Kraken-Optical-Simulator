# KrakenOS Sphinx documentation

The Sphinx source lives in `docs/source`.
The HTML build uses the Read the Docs theme via `sphinx-rtd-theme`.

Build locally:

```bash
kraken-install
make -C docs html
```

The standard Sphinx entrypoints are `docs/Makefile` and `docs/make.bat`.
HTML output is written to `docs/build/html`.

`devenv.nix` also includes Sphinx and `sphinx-rtd-theme` in the Nix Python
package set, so a fresh devenv shell has the Read the Docs theme available.

The converted provisional manual starts at `docs/source/manual/index.rst`.
The source PDF is retained at `KrakenOS/Docs/USER_MANUAL_KrakenOS_Provisional.pdf`.
