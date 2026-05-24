"""Formula help HTML generation service."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any


class FormulaHelpService:
    """Build the generated optics formula sheet from editor state."""

    def __init__(self, editor: Any, *, docs_html_dir: Path, docs_source_dir: Path) -> None:
        self.editor = editor
        self.docs_html_dir = docs_html_dir
        self.docs_source_dir = docs_source_dir

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def build_formula_help_html(self) -> str:
        object_mode = html.escape(self._current_object_mode())
        wavelength = self._current_wavelength()
        object_gap = float(self.rows[0].thickness) if self.rows else float("nan")
        image_gap = self._current_image_distance()
        object_size = float(self.rows[0].diameter) if self.rows else float("nan")
        sensor_size = float(self.rows[-1].diameter) if self.rows else float("nan")
        field_type = html.escape(self._field_type_display_label(self._current_field_type()))
        field_value = self._current_field_value()

        def _doc_link(page: str, label: str, section: str = "manual") -> str:
            html_path = self.docs_html_dir / section / f"{page}.html"
            rst_path = self.docs_source_dir / section / f"{page}.rst"
            target = html_path if html_path.exists() else rst_path
            if target.exists():
                href = html.escape(target.as_uri())
                return f'<a href="{href}">{html.escape(label)}</a>'
            return html.escape(label)

        def _doc_list(items: list[tuple[str, str, str]]) -> str:
            return "\n        ".join(
                f"<li>{_doc_link(page, label, section=section)}</li>"
                for label, page, section in items
            )

        kb_links_html = _doc_list([
            ("Rules of Thumb — Optics · Imaging · Laser",          "rules_of_thumb",       "knowledge_base"),
            ("Cardinal Points (EP, XP, PP) walkthrough",           "cardinal_points",      "knowledge_base"),
            ("Lens Design Families — Photographic & Machine Vision", "lens_design_intro",  "knowledge_base"),
            ("IR Sub-pixel Hot-Spot Detection",                    "ir_subpixel_detection", "knowledge_base"),
        ])
        tools_links_html = _doc_list([
            ("Analysis Tools reference (Spot, PSF, MTF, Seidel, encircled energy, atmospheric)", "analysis_tools", "manual"),
            ("Paraxial Matrix Tool",                  "parax_tool",            "manual"),
            ("PupilCalc Tool",                        "pupilcalc_tool",        "manual"),
            ("Pupil Patterns",                        "pupil_patterns",        "manual"),
            ("Pupil / Paraxial Analysis",             "pupil_paraxial_analysis", "manual"),
            ("Gaussian Beams & cavity eigenmodes",    "gaussian_beams",        "manual"),
        ])
        workflow_links_html = _doc_list([
            ("Core Model",                       "core_model",                "manual"),
            ("Classes and Attributes",           "classes_and_attributes",    "manual"),
            ("Working with the Library",         "working_with_library",      "manual"),
            ("Editable Table",                   "editable_table",            "manual"),
            ("Tracing and Ray Data",             "tracing_and_ray_data",      "manual"),
            ("Non-Sequential First Design",      "nonsequential_first_design", "manual"),
            ("Zemax Rayfile Sources",            "zemax_rayfile_sources",     "manual"),
            ("Beam Splitters",                   "beam_splitters",            "manual"),
            ("Diffuse Scattering",               "diffuse_scattering",        "manual"),
            ("Lens Fabrication Drawings",        "lens_fabrication_drawings", "manual"),
            ("2D Viewers",                       "viewers",                   "manual"),
            ("3D Viewer",                        "viewer_3d",                 "manual"),
        ])
        extras_links_html = _doc_list([
            ("Examples",                "examples",       "manual"),
            ("References",              "references",     "manual"),
            ("Installation Notes",      "installation",   "manual"),
            ("Manual Index",            "index",          "manual"),
            ("Knowledge Base Index",    "index",          "knowledge_base"),
        ])
        effl_text = "Unavailable"
        ppa_text = "Unavailable"
        ppp_text = "Unavailable"
        image_size_text = "Unavailable"
        fill_text = "Unavailable"
        try:
            effl, ppa, ppp = self._exact_paraxial_cardinals(wavelength)
            effl_text = f"{effl:.6g} mm"
            ppa_text = f"{ppa:.6g} mm"
            ppp_text = f"{ppp:.6g} mm"
            if self._current_object_mode() == "Finite" and object_gap > 0:
                s = object_gap + ppa
                if abs(s) > 1e-12:
                    denom = (1.0 / effl) - (1.0 / s)
                    if abs(denom) > 1e-12:
                        sp = 1.0 / denom
                        magnification = sp / s
                        image_size = abs(magnification) * max(object_size, 0.0)
                        image_size_text = f"{image_size:.6g} mm"
                        if sensor_size > 1e-12:
                            fill_text = f"{100.0 * image_size / sensor_size:.4g}%"
        except Exception:
            pass

        return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>KrakenOS Optics Formula Sheet</title>
      <style>
        :root {{
          --bg: #f6f8fc;
          --panel: #ffffff;
          --ink: #1f2937;
          --muted: #4b5563;
          --accent: #0f766e;
          --line: #d1d5db;
        }}
        body {{
          margin: 0;
          background: linear-gradient(180deg, #eef2ff 0%, var(--bg) 40%);
          color: var(--ink);
          font-family: \"Iosevka Aile\", \"Source Sans 3\", \"Noto Sans\", sans-serif;
          line-height: 1.55;
        }}
        .wrap {{
          max-width: 980px;
          margin: 0 auto;
          padding: 28px 20px 40px;
        }}
        .hero {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 14px;
          padding: 18px 20px;
          box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
          margin-bottom: 16px;
        }}
        h1 {{
          margin: 0 0 8px 0;
          font-size: 1.42rem;
        }}
        .grid {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 8px 16px;
          font-size: 0.96rem;
        }}
        .card {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-left: 4px solid var(--accent);
          border-radius: 12px;
          padding: 14px 16px;
          margin: 12px 0;
          box-shadow: 0 6px 16px rgba(15, 23, 42, 0.05);
        }}
        h2 {{
          margin: 0 0 8px 0;
          font-size: 1.08rem;
        }}
        .note {{
          color: var(--muted);
          font-size: 0.94rem;
        }}
        ul {{
          margin-top: 8px;
          padding-left: 18px;
        }}
        code {{
          background: #eef2ff;
          border: 1px solid #c7d2fe;
          border-radius: 5px;
          padding: 0 5px;
        }}
      </style>
      <script>
        window.MathJax = {{
          tex: {{ inlineMath: [['\\\\(','\\\\)'], ['$', '$']], displayMath: [['\\\\[','\\\\]']] }},
          svg: {{ fontCache: 'global' }}
        }};
      </script>
      <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
    </head>
    <body>
      <div class="wrap">
        <section class="hero">
          <h1>KrakenOS Formula Sheet</h1>
          <p class="note">This page is generated from your current UI state. It uses the same centered paraxial model as the <code>Paraxial Solve</code> tool.</p>
          <div class="grid">
        <div><strong>Object mode:</strong> {object_mode}</div>
        <div><strong>Wavelength:</strong> {wavelength:.6g} um</div>
        <div><strong>Object gap:</strong> {object_gap:.6g} mm</div>
        <div><strong>Image gap:</strong> {image_gap:.6g} mm</div>
        <div><strong>Object size:</strong> {object_size:.6g} mm</div>
        <div><strong>Sensor size:</strong> {sensor_size:.6g} mm</div>
        <div><strong>Field:</strong> {field_type} = {field_value:.6g}</div>
        <div><strong>EFFL / PPA / PPP:</strong> {html.escape(effl_text)} / {html.escape(ppa_text)} / {html.escape(ppp_text)}</div>
        <div><strong>Paraxial image size:</strong> {html.escape(image_size_text)}</div>
        <div><strong>Sensor fill:</strong> {html.escape(fill_text)}</div>
          </div>
        </section>

        <section class="card">
          <h2>Paraxial imaging</h2>
          <p>\\[\\frac{{1}}{{f}} = \\frac{{1}}{{s}} + \\frac{{1}}{{s'}}\\]</p>
          <p>\\[m = \\frac{{s'}}{{s}} = \\frac{{y'}}{{y}}\\]</p>
          <p class="note">Solve in principal-plane space, then map to table thickness values.</p>
        </section>

        <section class="card">
          <h2>UI thickness conversion</h2>
          <p>\\[s = z_{{\\mathrm{{obj}}}} + \\mathrm{{PPA}}\\]</p>
          <p>\\[z_{{\\mathrm{{img}}}} = s' + \\mathrm{{PPP}}\\]</p>
          <p class="note"><code>Object Thickness</code> is \\(z_\\mathrm{{obj}}\\). Image solve writes to the last optical row thickness before <code>Image</code>.</p>
        </section>

        <section class="card">
          <h2>2F rule for thick lenses</h2>
          <p>\\[s = 2f \\Rightarrow s' = 2f\\]</p>
          <p>\\[z_{{\\mathrm{{obj}},2F}} = 2f - \\mathrm{{PPA}},\\qquad z_{{\\mathrm{{img}},2F}} = 2f + \\mathrm{{PPP}}\\]</p>
          <p class="note">The symmetry is around principal planes H1/H2, not lens vertices.</p>
        </section>

        <section class="card">
          <h2>Image diameter and sensor fill</h2>
          <p>\\[y' = \\left|\\frac{{s'}}{{s}}\\right|\\,y\\]</p>
          <p>\\[\\mathrm{{fill}} = \\frac{{y'}}{{y_{{\\mathrm{{sensor}}}}}}\\]</p>
          <p class="note">Changing <code>Image Diameter</code> does not change focus distance. It changes framing/fill.</p>
        </section>

        <section class="card">
          <h2>Aperture quick rule</h2>
          <p>\\[N = \\frac{{f}}{{D_{{\\mathrm{{EP}}}}}},\\qquad D_{{\\mathrm{{EP}}}} \\approx \\frac{{f}}{{N}}\\]</p>
          <p class="note">Keep <code>STOP</code> and <code>EPD</code> choices consistent between analysis and optimization.</p>
        </section>

        <section class="card">
          <h2>Practical UI reminders</h2>
          <ul>
        <li><code>Object Diameter</code>, <code>Image Diameter</code>, and <code>EPD</code> use full diameters.</li>
        <li><code>Field Half-Angle</code> and all <code>* Semi-Height</code> field types use semi-field values.</li>
        <li><code>Field samples</code> spans from <code>-max</code> to <code>+max</code> when the count is greater than 1.</li>
        <li>Paraxial solve is intended for centered refractive layouts. Mirror/tilt/decenter cases still need full trace validation.</li>
          </ul>
        </section>

        <section class="card">
          <h2>Deeper reading — Sphinx docs</h2>
          <p class="note">These pages go further than this popup: SVG ray-construction figures, worked numerical examples,
        Strehl/Maréchal, diffraction-limited MTF, Gaussian-beam q-parameters, cavity stability, and the matching
        KrakenOS code for every formula.</p>

          <p><strong>Knowledge Base — theory &amp; rules of thumb</strong></p>
          <ul>
        {kb_links_html}
          </ul>

          <p><strong>Tools &amp; Analysis</strong></p>
          <ul>
        {tools_links_html}
          </ul>

          <p><strong>Model &amp; Workflow</strong></p>
          <ul>
        {workflow_links_html}
          </ul>

          <p><strong>Examples &amp; References</strong></p>
          <ul>
        {extras_links_html}
          </ul>

          <p class="note">Not built yet?  Run
        <code>cd docs &amp;&amp; sphinx-build -E -b html source build/html</code>
        once, then re-open this page.</p>
        </section>
      </div>
    </body>
    </html>
    """
