def add_plotter_assets(app, pagename, templatename, context, doctree):
    if pagename != "knowledge_base/formula_plotter":
        return
    app.add_css_file("formula_plotter.css")
    for filename in (
        "vendor/latex-syntax-0.128.13.min.js",
        "vendor/complex-2.4.3.min.js",
        "formula_plotter_engine.js",
        "formula_plotter.js",
    ):
        app.add_js_file(filename)


def setup(app):
    app.connect("html-page-context", add_plotter_assets)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
