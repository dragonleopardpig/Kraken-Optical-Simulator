# 0850 -- the Optimize button and Action -> Paraxial Matrix Report work again

Found while cutting the Qt seam (docs/design_qt_migration.md): the seam converter declined to
rewrite a `self.after(...)` inside `start_optimization`, because that method was **static**.

The mixin extraction of 2026-05-26 (`fcb42075`) left a stray decorator a blank line above two
methods:

    @staticmethod

    def start_optimization(self) -> None:          # the Optimize button
    ...
    @staticmethod

    def open_paraxial_matrix_report(self) -> None: # Action -> Paraxial Matrix Report

A static method receives no instance, so `command=self.start_optimization` called it with no
arguments -> `TypeError: missing 1 required positional argument: 'self'`, on every click, for four
months. Not silent -- `report_callback_exception` put up the error dialog -- but neither feature
has run since the extraction.

**Fix:** the two decorators removed. A whole-package AST scan found no other static method whose
first parameter is `self` / `cls`.

## Guard

`validate_open3d_0850_no_static_method_takes_self.py`, display-free, penta phase 629.

- **S1** across `KrakenOS/` no static method takes `self`/`cls`; **S2** CONTROL: the scan finds the
  exact slip (decorator, blank line, `def m(self)`)
- **B1** both methods, called as their button / menu entry calls them (bound, no arguments), reach
  their bodies; **B2** CONTROL: the static version raises the very `TypeError`

`validate_optimization_controls` passes; `validate_3d_interaction_contract` fails with the same 18
stale items before and after (identical lists) -- pre-existing, not this change.
