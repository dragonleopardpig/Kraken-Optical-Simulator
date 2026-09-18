# KrakenOS Sphinx documentation

The Sphinx source lives in `docs/source`.
The HTML build uses the Read the Docs theme via `sphinx-rtd-theme`.
JupyterLite supplies a Pyodide-backed Python kernel for interactive
notebooks while keeping the GitHub Pages deployment fully static.

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

The Knowledge Base includes a browser-only LaTeX equation plotter at
`knowledge_base/formula_plotter.html`. Its reflection and Gaussian examples
use the same dependency-based evaluator as user-entered equations. The
vendored parser and complex-arithmetic libraries load only on that page.
Run its numerical/parser checks with `node --test tests/test_formula_plotter.cjs`
from the repository root.

## Schaum optics worked solutions

The collection at `knowledge_base/worked_exercises/schaum_optics/index.html`
contains 270 problem-specific worked solutions and 55 original SVG illustrations.
Edit the chapter records in `docs/schaum_optics_worked/`, not the generated RST.
Topic metadata lives in `docs/generate_schaum_optics_solutions.py`; figure captions
live in `docs/schaum_optics_worked/illustrations.py`.

Regenerate and validate from the repository root:

```bash
python docs/generate_schaum_optics_illustrations.py
python docs/generate_schaum_optics_solutions.py
python docs/validate_schaum_optics_solutions.py
python -m pytest tests/test_schaum_optics_docs.py
python -m sphinx -W -b html docs/source docs/build/html
```

The SVG generator uses the project's NumPy, SciPy, and Matplotlib dependencies;
the normal Sphinx build uses the checked-in assets and does not run the generator.
Use `--preview-dir /tmp/schaum-previews` to also render PNGs for visual review.
The validator checks the full inventory, distinct mathematical working, generated
page freshness, image references, alt text, and self-contained vector SVG assets.
The numerical tests cover representative sign conventions, diffraction integrals,
Fourier coefficients, and convolution constructions. They are regression checks,
not a symbolic verification of every solution. The private reference scans are not
required to regenerate or build the documentation.
