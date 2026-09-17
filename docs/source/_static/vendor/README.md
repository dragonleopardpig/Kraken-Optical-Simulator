# Equation plotter dependencies

These unmodified browser bundles are loaded only on the LaTeX equation
plotter page. They allow calculation without a CDN or a build-time npm step.

- `latex-syntax-0.128.13.min.js`: `@cortex-js/compute-engine` 0.128.13,
  `https://unpkg.com/@cortex-js/compute-engine@0.128.13/dist/umd-min/latex-syntax.cjs`.
  Upstream license: `compute-engine-LICENSE` (MIT).
- `complex-2.4.3.min.js`: `complex.js` 2.4.3,
  `https://unpkg.com/complex.js@2.4.3/dist/complex.min.js`.
  Upstream license: `complex-LICENSE` (MIT).

The CortexJS bundle supplies parsing and serialization only. The plotter
validates and evaluates a supported subset of MathJSON operations; it does
not execute arbitrary user code or claim to support every CortexJS operation.

After updating either library, run `node --test tests/test_formula_plotter.cjs`
from the repository root and check the built Sphinx page in a browser.
