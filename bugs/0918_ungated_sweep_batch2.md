# 0918 -- ungated sweep, batch 2: three product fixes and four stale checks

## Product fixes

1. **"Ray Fan count = N" drew 2N+1 rays in the 2-D preview.** bugs/0095 made N a literal
   per-field count, but only in the two 3-D display-bundle builders.
   `trace_preview._build_pupilcalc_preview_bundles` (the 2-D preview of a selected pattern) still
   set `Samp = ray_count`. KrakenOS's `Samp` is a per-axis density and a fan emits 2*Samp+1, so
   31 drew 63. Found by `validate_scene_sources` ("zero-field samples collapse to one launch",
   rays=63 for ray_count=31). The builder now inverts `Samp` with
   `kraken_pattern_samp_for_count`, as 0095 does elsewhere. 31 draws 31; `validate_open3d_ray_fan_count`
   still passes.
2. **Every headless snapshot editor failed in the legacy 3-D scene.** It was all 190 items of
   `validate_menu_smoke`, failing since 95615f05 (2026-05-29).
   - `render_layout_snapshot._snapshot_editor` (a production helper, also used by the two-arm
     fold) never declared the four `imported_*_step_path` attributes that
     `KrakenLayoutEditor.__init__` sets. The ghost-suppression lookup read them and raised.
     They are now declared (None).
3. **The legacy pyvista 3-D view read an INSPECTOR-only toggle through the editor.**
   `show_terminal_diagnostics_var` exists only on the 3D inspector. The legacy scene is
   populated by the editor, the fallback when no inspector is available, so it raised at the
   first ray endpoint. `inspection_cell` had worked around it by seeding the variable.
   `_legacy_show_terminal_diagnostics()` reads the editor's variable, else the inspector's,
   else the inspector's default (off). The three cases were checked.
   - `validate_menu_smoke`: 190/190 pass.

## Stale checks (claims hold; the code moved or the contract changed)

- **`validate_detector_aperture_analysis`.** The Ray Inspector became a report (0894-0897). The
  check reads `reports/ray_tables.RAY_COLUMNS` ("Detector aperture", "Miss [mm]") and the CSV
  header in `reports/ray_csv`.
- **`validate_galvo_f_theta_case_study`.** The case studies were renumbered (17 -> 19). The
  check accepts any number before the title.
- **`validate_open3d_ray_count_toolbar_sync`.** bugs/0093 REMOVED the toolbar's Ray count; one
  old check passed only by matching the removal comment. The checks follow the single source:
  one Live Controls combo on `ray_count_var`, with `sync_fields=True`.
- **`validate_scene_sources`.**
  - bug 0015 (gated phase 24) makes the terminal row a display detector on purpose. The claim
    "not auto-promoted" is its own switch, `_nonseq_plain_image_detector_enabled`, which is
    False.
  - The Meridional-fan default spreads along ONE axis since 0095.
  - The preview count equals the configured N.

`validate_native_nonseq_closure` and `validate_phase7_complete` pass on re-run: their failures
were the interferometer routing that 0917 fixed.
