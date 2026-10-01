"""The Qt shell's command icons (bugs/0935: the ribbon and the menus).

Line icons drawn for this project on a 24x24 grid, kept here as SVG text rather than files, so they
ship with the code and scale to any size. ``{fg}`` is the pen colour and ``{accent}`` the light /
optics colour; both are filled from the widget palette when an icon is made, so the icons follow a
light or dark theme.
"""
from __future__ import annotations

_OPEN = 'stroke="{fg}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"'
_LIGHT = 'stroke="{accent}" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"'
_GLASS = 'fill="{accent}" fill-opacity="0.22" stroke="{fg}" stroke-width="1.6" stroke-linejoin="round"'

#: icon name -> the SVG body (inside a 24x24 viewBox)
ICONS: dict[str, str] = {
    # ---- file / view -------------------------------------------------------------------------
    "open": f'<path {_OPEN} d="M3 7h6l2 2h10v10H3z"/><path {_OPEN} d="M3 7V5h6l2 2"/>',
    "reload": f'<path {_OPEN} d="M19 8a8 8 0 1 0 1 6"/><path {_OPEN} d="M20 3v5h-5"/>',
    "quit": f'<path {_OPEN} d="M12 3v8"/><path {_OPEN} d="M7 6a8 8 0 1 0 10 0"/>',
    "reset_camera": (f'<path {_OPEN} d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/>'
                     f'<rect {_GLASS} x="8" y="8" width="8" height="8" rx="1"/>'),
    "redraw": (f'<path {_OPEN} d="M4 12a8 8 0 0 1 14-5l2 2"/><path {_OPEN} d="M20 4v5h-5"/>'
               f'<path {_OPEN} d="M20 12a8 8 0 0 1-14 5l-2-2"/><path {_OPEN} d="M4 20v-5h5"/>'),
    "show_rays": (f'<path {_LIGHT} d="M2 6l9 6 11-4M2 12h9l11 0M2 18l9-6 11 4"/>'
                  f'<ellipse {_GLASS} cx="11" cy="12" rx="2" ry="8"/>'),
    "inspector": (f'<path {_GLASS} d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/>'
                  f'<path {_OPEN} d="M4 7.5l8 4.5 8-4.5M12 12v9"/>'),
    "about": f'<circle {_OPEN} cx="12" cy="12" r="9"/><path {_OPEN} d="M12 11v6M12 7.5v.5"/>',
    # ---- surfaces ------------------------------------------------------------------------------
    "advanced_surface": (f'<path {_GLASS} d="M9 3c-3 5-3 13 0 18h6c3-5 3-13 0-18z"/>'
                         f'<path {_OPEN} d="M2 12h20" stroke-dasharray="2 2"/>'),
    "surface_shape": (f'<path {_OPEN} d="M4 20V4M4 20h16"/>'
                      f'<path {_LIGHT} d="M4 18c5 0 7-2 9-6s4-7 7-8"/>'),
    "coating_material": (f'<rect {_GLASS} x="4" y="13" width="16" height="7"/>'
                         f'<path {_LIGHT} d="M4 10h16M4 7h16"/><path {_OPEN} d="M4 4h16"/>'),
    "error_map": (f'<path {_OPEN} d="M3 8c3-3 6 3 9 0s6 3 9 0M3 13c3-3 6 3 9 0s6 3 9 0M3 18c3-3 6 3 9 0s6 3 9 0"/>'),
    "beam_splitter": (f'<rect {_GLASS} x="6" y="6" width="12" height="12"/>'
                      f'<path {_OPEN} d="M6 18L18 6"/><path {_LIGHT} d="M1 12h11v10M12 12h11"/>'),
    "diffuse_scatter": (f'<path {_OPEN} d="M3 19h18"/><path {_LIGHT} d="M12 19V9M12 19l-6-7M12 19l6-7M12 19l-8-3M12 19l8-3"/>'
                        f'<path {_LIGHT} d="M5 3l7 16"/>'),
    "grating_settings": (f'<path {_OPEN} d="M3 16h18M5 16l2-3 2 3 2-3 2 3 2-3 2 3 2-3"/>'
                         f'<path {_LIGHT} d="M12 3v10M12 13l-6-9M12 13l6-9"/>'),
    "detector_settings": (f'<rect {_GLASS} x="5" y="5" width="14" height="14" rx="1"/>'
                          f'<path {_OPEN} d="M9.7 5v14M14.3 5v14M5 9.7h14M5 14.3h14"/>'),
    "galvo_scan": (f'<path {_OPEN} d="M8 18l8-12"/><circle {_OPEN} cx="12" cy="12" r="1.2"/>'
                   f'<path {_LIGHT} d="M2 12h10l8 6M12 12l8-8"/><path {_OPEN} d="M18 9a7 7 0 0 1 0 6" stroke-dasharray="1.5 1.5"/>'),
    "glass_catalog": (f'<path {_OPEN} d="M4 4h6a2 2 0 0 1 2 2v14a2 2 0 0 0-2-2H4zM20 4h-6a2 2 0 0 0-2 2v14a2 2 0 0 1 2-2h6z"/>'
                      f'<path {_LIGHT} d="M6 8h3M15 8h3M6 11h3M15 11h3"/>'),
    "stock_lens": (f'<path {_GLASS} d="M10 3c-2 6-2 12 0 18h4c2-6 2-12 0-18z"/>'
                   f'<path {_OPEN} d="M3 7h3M3 12h3M3 17h3M18 7h3M18 12h3M18 17h3"/>'),
    "optical_solid_diagnostics": (f'<path {_GLASS} d="M3 17L8 5l7 3 1 9z"/><path {_OPEN} d="M8 5l-1 12M15 8l-8 9M3 17h13"/>'
                        f'<circle {_OPEN} cx="17" cy="15" r="4"/><path {_LIGHT} d="M15.3 15l1.2 1.2 2.2-2.4"/>'
                        f'<path {_OPEN} d="M20 18l2.5 2.5"/>'),
    "mtf_from_image": (f'<rect {_OPEN} x="3" y="3" width="18" height="18" rx="1.5"/>'
                       f'<path fill="{{fg}}" fill-opacity="0.35" d="M3 3h7l4 18H3z"/>'
                       f'<path {_LIGHT} d="M5 7c4 0 7 2 9 6s4 6 6 6"/>'),
    # ---- scene ------------------------------------------------------------------------------------
    "scene_target": (f'<circle {_OPEN} cx="12" cy="12" r="8"/><circle {_OPEN} cx="12" cy="12" r="4"/>'
                     f'<circle cx="12" cy="12" r="1.3" fill="{{accent}}"/>'),
    "path_local_pose": (f'<path {_OPEN} d="M5 19V5M5 19h14"/><path {_LIGHT} d="M5 19l9-9"/>'
                        f'<path {_OPEN} d="M3 7l2-2 2 2M17 17l2 2-2 2"/>'),
    "element_settings": (f'<path {_OPEN} d="M4 6h16M4 12h16M4 18h16"/>'
                         f'<circle {_GLASS} cx="9" cy="6" r="2"/><circle {_GLASS} cx="15" cy="12" r="2"/>'
                         f'<circle {_GLASS} cx="7" cy="18" r="2"/>'),
    "scene_sources": (f'<circle {_GLASS} cx="12" cy="10" r="4"/>'
                      f'<path {_LIGHT} d="M12 2v2M12 16v2M4 10h2M18 10h2M6.3 4.3l1.4 1.4M16.3 14.3l1.4 1.4M6.3 15.7l1.4-1.4M16.3 5.7l1.4-1.4"/>'
                      f'<path {_OPEN} d="M4 21h16"/>'),
    "source_edit": (f'<circle {_GLASS} cx="9" cy="9" r="4"/>'
                    f'<path {_LIGHT} d="M9 2v1.5M2 9h1.5M4 4l1 1M14 4l-1 1M4 14l1-1"/>'
                    f'<path {_OPEN} d="M13 21l1-4 6-6 3 3-6 6z"/>'),
    "face_roles": (f'<path {_GLASS} d="M4 19L12 4l8 15z"/><path {_OPEN} d="M12 4v15"/>'
                   f'<path stroke="{{accent}}" stroke-width="3" stroke-linecap="round" d="M12 5.5L19 18.5"/>'),
    "inspection_cell": (f'<rect {_OPEN} x="8" y="2" width="8" height="6" rx="1"/><path {_OPEN} d="M10 8h4v2h-4z"/>'
                        f'<path {_LIGHT} d="M12 10l-5 8M12 10l5 8"/><rect {_GLASS} x="4" y="18" width="16" height="3"/>'),
    "inspection_part": (f'<path {_GLASS} d="M4 8l8-4 8 4v8l-8 4-8-4z"/><path {_OPEN} d="M4 8l8 4 8-4M12 12v8"/>'
                        f'<circle {_LIGHT} cx="16" cy="12.5" r="1.5"/>'),
    # ---- analysis -----------------------------------------------------------------------------------
    "paraxial_matrix": (f'<path {_OPEN} d="M7 4H4v16h3M17 4h3v16h-3"/>'
                        f'<path {_LIGHT} d="M8 9h2M14 9h2M8 15h2M14 15h2"/>'),
    "paraxial_calculator": (f'<rect {_OPEN} x="5" y="2" width="14" height="20" rx="2"/>'
                            f'<rect {_GLASS} x="8" y="5" width="8" height="4"/>'
                            f'<path {_OPEN} d="M8.5 13h1M12 13h1M15 13h.5M8.5 16.5h1M12 16.5h1M15 16.5h.5M8.5 19.5h1M12 19.5h1"/>'),
    "gaussian_beam": (f'<path {_LIGHT} d="M2 4c6 5 14 5 20 0M2 20c6-5 14-5 20 0"/>'
                      f'<path {_OPEN} d="M2 12h20" stroke-dasharray="2 2"/><path {_OPEN} d="M12 9v6"/>'),
    "branch_gaussian_q": (f'<path {_LIGHT} d="M2 8c4 3 6 3 9 4M2 16c4-3 6-3 9-4"/>'
                          f'<path {_LIGHT} d="M11 12l10-7M11 12l10 7"/><rect {_GLASS} x="9" y="10" width="4" height="4" transform="rotate(45 11 12)"/>'),
    "ray_inspector": (f'<path {_LIGHT} d="M2 18l7-6 5 3"/><circle {_OPEN} cx="16" cy="9" r="5"/>'
                      f'<path {_OPEN} d="M19.5 12.5L22 15"/>'),
    "trace_paths": (f'<circle {_GLASS} cx="4" cy="12" r="2"/><path {_LIGHT} d="M6 12h5l4-6h5M11 12l4 6h5"/>'
                    f'<circle {_OPEN} cx="20" cy="6" r="1.5"/><circle {_OPEN} cx="20" cy="18" r="1.5"/>'),
    "nonseq_scene_graph": (f'<circle {_GLASS} cx="12" cy="5" r="2.5"/><circle {_GLASS} cx="5" cy="18" r="2.5"/>'
                           f'<circle {_GLASS} cx="19" cy="18" r="2.5"/><path {_OPEN} d="M10.7 7.2L6.3 15.8M13.3 7.2l4.4 8.6M7.5 18h9"/>'),
    "detector_aperture": (f'<circle {_GLASS} cx="16" cy="12" r="6"/><circle {_OPEN} cx="16" cy="12" r="3"/>'
                          f'<path {_LIGHT} d="M1 7l15 5M1 17l15-5M1 12h15"/>'),
    "branch_throughput": (f'<path {_OPEN} d="M3 21h18"/><rect {_GLASS} x="5" y="11" width="3" height="10"/>'
                          f'<rect {_GLASS} x="10.5" y="6" width="3" height="15"/><rect {_GLASS} x="16" y="14" width="3" height="7"/>'),
    "source_illumination": (f'<circle {_LIGHT} cx="7" cy="6" r="3"/><path {_LIGHT} d="M9 9l4 7M7 9v7M5 9l-2 7"/>'
                            f'<path {_GLASS} d="M2 17h20l-2 4H4z"/>'),
    "system_selection": (f'<rect {_GLASS} x="2" y="7" width="11" height="10" rx="1.5"/>'
                         f'<path {_OPEN} d="M13 9.5h3l5-2.5v10l-5-2.5h-3"/><circle {_OPEN} cx="7.5" cy="12" r="2.5"/>'),
    "catalog_matcher": (f'<path {_OPEN} d="M9 6h12M9 12h12M9 18h12"/>'
                        f'<path {_LIGHT} d="M2 6l1.5 1.5L6 4.5M2 12l1.5 1.5L6 10.5M2 18l1.5 1.5L6 16.5"/>'),
    "tolerance_preset": (f'<path {_OPEN} d="M5 3h11l3 3v15H5z"/><path {_OPEN} d="M8 3v5h7V3"/>'
                         f'<path {_LIGHT} d="M9 14h6M12 11v6M9 19h6"/>'),
    "apply_tolerance_preset": (f'<path {_LIGHT} d="M4 8h6M7 5v6M4 14h6"/>'
                               f'<path {_GLASS} d="M13 6l8 6-8 6z"/>'),
    # ---- the ribbon's own -------------------------------------------------------------------------
    "search": f'<circle {_OPEN} cx="10" cy="10" r="6"/><path {_OPEN} d="M14.5 14.5L20 20"/>',
}


def svg_markup(name: str, fg: str, accent: str) -> str:
    """The full SVG document of icon ``name`` in the given colours (KeyError if unknown)."""
    body = ICONS[name].replace("{fg}", fg).replace("{accent}", accent)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">{body}</svg>'


_CACHE: dict = {}


def icon(name: str, palette=None):
    """A QIcon for ``name`` in ``palette``'s text colour (the application palette by default),
    rendered crisp at every size Qt asks for; an unknown name gives an empty QIcon."""
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPalette, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    if name not in ICONS:
        return QIcon()
    palette = palette or QGuiApplication.palette()
    fg = palette.color(QPalette.ColorRole.WindowText).name()
    accent = "#e8871e" if palette.color(QPalette.ColorRole.Window).lightness() > 128 else "#ffb454"
    key = (name, fg, accent)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    renderer = QSvgRenderer(QByteArray(svg_markup(name, fg, accent).encode()))
    result = QIcon()
    ratio = 2.0  # HiDPI: every size is drawn at twice its logical pixels
    for size in (16, 20, 24, 32, 40, 48):
        pixmap = QPixmap(int(size * ratio), int(size * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        result.addPixmap(pixmap)
    _CACHE[key] = result
    return result
