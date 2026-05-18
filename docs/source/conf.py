project = "KrakenOS"
author = "KrakenOS contributors"
copyright = "2026, KrakenOS contributors"

extensions = ["sphinx_rtd_theme", "sphinx.ext.mathjax"]
templates_path = ["_templates"]
exclude_patterns = []
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "sticky_navigation": True,
    "logo_only": False,
}
html_logo = "_static/logo.png"
html_static_path = ["_static"]
html_css_files = ["custom.css"]

rst_epilog = """
.. |ui| replace:: KrakenOS Layout Editor
"""
