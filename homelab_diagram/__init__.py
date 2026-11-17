"""homelab-diagram: the r/homelab diagram style as a library and an offline spec renderer.

Stable public API (semantic versioning applies to these names only):

- Theme, DARK, LIGHT, THEMES                     colors and fonts
- Canvas, rounded                                SVG primitives (rect, text, icon, line, trunk, arrow, pill, label)
- card, device_card, folder, hw_bar, zone, addr, tab_width, TAB   composite pieces
- IconStore, IconError                           local icon lookup (no network)
- Spec, Group, Node, Item, Link, LegendEntry, SpecError, parse_spec, load_spec   declarative spec
- LayoutError, draw                              deterministic layout
- render, render_svg                             spec -> SVG/PNG
- preflight, PreflightError, MIN_LIBRSVG         renderer checks (librsvg >= 2.60, fonts)
"""
from .canvas import Canvas, rounded
from .components import TAB, addr, card, device_card, folder, hw_bar, tab_width, zone
from .icons import IconError, IconStore
from .layout import LayoutError, draw
from .render import render, render_svg
from .rsvg import MIN_LIBRSVG, PreflightError, preflight
from .spec import Group, Item, LegendEntry, Link, Node, Spec, SpecError, load_spec, parse_spec
from .theme import DARK, LIGHT, THEMES, Theme

__version__ = "0.2.0"

__all__ = [
    "Canvas", "rounded", "TAB", "addr", "card", "device_card", "folder", "hw_bar", "tab_width", "zone",
    "IconError", "IconStore", "LayoutError", "draw", "render", "render_svg", "MIN_LIBRSVG", "PreflightError",
    "preflight", "Group", "Item", "LegendEntry", "Link", "Node", "Spec", "SpecError", "load_spec", "parse_spec",
    "DARK", "LIGHT", "THEMES", "Theme", "__version__",
]
