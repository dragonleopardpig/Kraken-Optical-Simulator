# 0861 -- three more analysis reports in the Qt shell (phase 3)

Detector Aperture, Path Throughput and Source Illumination, all the same shape as bugs/0860: their
data layers were already shared, so each port is a builder that calls exactly what the Tk dialog
calls, plus a menu entry.

| report | source of truth already in the tree |
|---|---|
| Detector Aperture | `detector_aperture_analysis.py` -- layout, table values, summary, report text, CSV columns |
| Path Throughput | `branch_throughput_analysis.py` -- the same, plus the path filter |
| Source Illumination | `source_illumination_analysis.py` -- the same, plus the target label |

The Qt shell's Analysis menu now holds five reports. On `om05a_folded.py`:

- Paraxial Matrix -- 25 surfaces, EFFL 85.13 mm
- Branch Gaussian Q -- 2 670 records
- Detector Aperture -- 1 detector, 226 rays, 106 hits (46.9%), 0 misses
- Path Throughput -- 2 paths, input 113.282, output sum 44.6728
- Source Illumination -- 2 sources, 106/226 rays onto S24, 39.43% power throughput

`ReportColumn` gained `align`, because these tables CENTRE their count columns (`rays`, `hits`,
`misses`, `other`, `worst_ray`) where the earlier two only ever had left or right; the Qt table
reads the analysis module's own anchors rather than inventing alignment.

Not ported with them, on purpose: the Tk **path filter** (Path Throughput) and **target selector**
(Source Illumination). The Qt views show the defaults -- every path, and the target the editor
resolves as "Auto" -- exactly what each Tk dialog opens on. Those controls are the next family:
a report with inputs, which the Gaussian Beam Report and the Paraxial Calculator also need.

## Guard

`validate_open3d_0861_analysis_reports_qt.py`, penta phase 640. A every one of the five builders
has an action of its own name, a method the window defines and a title. C the columns are the
analysis module's own layout, centred columns included. R per report: every cell equals the
module's `*_table_values`, the summary equals its `*_summary_text`, the CSV carries its
`*_CSV_COLUMNS` (22, 13 and 24 fieldnames respectively), and Copy carries its `*_report_text`.
