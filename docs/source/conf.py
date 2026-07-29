project = "KrakenOS"
author = "KrakenOS contributors"
copyright = "2026, KrakenOS contributors"

extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.mathjax",
    "jupyterlite_sphinx",
]
templates_path = ["_templates"]
exclude_patterns = [
    "knowledge_base/worked_exercises/photonics_essentials/notebooks/*.ipynb",
]
html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
    "sticky_navigation": True,
    "logo_only": False,
}
html_logo = "_static/logo.svg"
html_static_path = ["_static"]
html_css_files = [
    "custom.css",
    "knowledge_base/worked_exercises/photonics_essentials/photodiode_lab.css",
]
html_js_files = [
    "knowledge_base/worked_exercises/photonics_essentials/photodiode_lab.js"
]

jupyterlite_contents = [
    "../../KrakenOS/Physics/photodiode.py",
    (
        "knowledge_base/worked_exercises/photonics_essentials/"
        "notebooks/*.ipynb"
    ),
]
jupyterlite_new_tab_button_text = "Open the live Python notebook"
notebooklite_new_tab_button_text = "Open the live Python notebook"

rst_epilog = """
.. |ui| replace:: KrakenOS Layout Editor
"""
