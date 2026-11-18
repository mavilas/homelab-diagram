"""SVG canvas: the low-level drawing primitives of the homelab-diagram style.

Coordinates are SVG user units on a canvas `width` wide; the height is set by
finish() once the content is known. All output is plain strings built in call
order, so the same calls always produce the same bytes.
"""
from __future__ import annotations

import html
from typing import Callable, Sequence

from .icons import IconStore
from .text import tw
from .theme import DARK, Theme

Point = tuple[float, float]


def rounded(pts: Sequence[Point], r: float) -> str:
    """SVG path data for an orthogonal polyline with rounded corners."""
    if len(pts) == 2:
        return f"M{pts[0][0]},{pts[0][1]} L{pts[1][0]},{pts[1][1]}"
    d = f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1 = max(abs(x1 - x0), abs(y1 - y0))
        l2 = max(abs(x2 - x1), abs(y2 - y1))
        rr = min(r, l1 / 2, l2 / 2)
        ax = x1 - (x1 - x0) / l1 * rr if l1 else x1
        ay = y1 - (y1 - y0) / l1 * rr if l1 else y1
        bx = x1 + (x2 - x1) / l2 * rr if l2 else x1
        by = y1 + (y2 - y1) / l2 * rr if l2 else y1
        d += f" L{ax:.1f},{ay:.1f} Q{x1},{y1} {bx:.1f},{by:.1f}"
    d += f" L{pts[-1][0]},{pts[-1][1]}"
    return d


class Canvas:
    """An SVG document under construction.

    text_filter is applied to every visible string before escaping (the
    original uses it for domain redaction); it defaults to the identity.
    """

    def __init__(self, width: float = 2400, theme: Theme = DARK, icons: IconStore | None = None,
                 text_filter: Callable[[str], str] = lambda s: s):
        self.width = width
        self.theme = theme
        self.icons = icons or IconStore()
        self.text_filter = text_filter
        self.p: list[str] = []
        self._bg_idx: int | None = None

    # ------------------------------------------------------------ helpers
    def sub(self, s) -> str:
        return self.text_filter(str(s))

    def esc(self, s) -> str:
        return html.escape(self.sub(s), quote=True)

    def tw(self, s, size: float, mono: bool = False) -> float:
        return tw(self.sub(s), size, mono)

    def add(self, s: str) -> None:
        self.p.append(s)

    # ------------------------------------------------------------ primitives
    def rect(self, x, y, w, h, rx=10, fill=None, stroke=None, sw=1.2, op=1, dash=None):
        fill = self.theme.panel if fill is None else fill
        stroke = self.theme.border if stroke is None else stroke
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')

    def text(self, x, y, s, size=14, fill=None, weight=400, anchor="start", mono=False, ls=0, op=1):
        fill = self.theme.text if fill is None else fill
        fam = self.theme.mono if mono else self.theme.sans
        lsa = f' letter-spacing="{ls}"' if ls else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" fill="{fill}" '
                 f'font-weight="{weight}" text-anchor="{anchor}" opacity="{op}"{lsa}>{self.esc(s)}</text>')

    def icon(self, name: str, x, y, size):
        self.add(f'<image x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" '
                 f'href="{self.icons.data_uri(name)}"/>')

    def line(self, pts, color, sw=3, dash=None, r=10, op=1, cap="round"):
        self.add(f'<path d="{rounded(pts, r)}" fill="none" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linecap="{cap}" stroke-linejoin="round" opacity="{op}"'
                 + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")

    def trunk(self, pts, r=12, sw=7):
        """Tagged trunk: light cable with a dark core."""
        self.line(pts, self.theme.trunk, sw=sw, r=r)
        self.line(pts, self.theme.bg, sw=sw - 4.4, r=r)

    def arrow(self, pts, color=None, sw=1.8, dash=None, r=8):
        """Line with an arrowhead at the last point."""
        color = self.theme.muted if color is None else color
        self.line(pts, color, sw, dash=dash, r=r)
        (x0, y0), (x1, y1) = pts[-2], pts[-1]
        dx, dy = x1 - x0, y1 - y0
        ln = max(abs(dx), abs(dy)) or 1
        ux, uy = dx / ln, dy / ln
        a, b = 8, 4.5
        p1 = (x1 - ux * a - uy * b, y1 - uy * a + ux * b)
        p2 = (x1 - ux * a + uy * b, y1 - uy * a - ux * b)
        self.add(f'<path d="M{x1},{y1} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} Z" fill="{color}"/>')

    def pill(self, x, y, s, color, size=12, fill=None, mono=False, anchor="start", h=None, pad=8, tcolor=None,
             weight=600):
        w = self.tw(s, size, mono) + pad * 2
        h = h or size + 10
        if anchor == "middle":
            x -= w / 2
        elif anchor == "end":
            x -= w
        self.rect(x, y, w, h, rx=h / 2, fill=fill or color + "22", stroke=color + "88", sw=1)
        self.text(x + w / 2, y + h / 2 + size * 0.36, s, size, tcolor or color, weight, "middle", mono)
        return w

    def label(self, x, y, s, color=None, size=12, anchor="middle", mono=False, bg=None):
        """Text on a line, with a background knock-out."""
        color = self.theme.muted if color is None else color
        bg = self.theme.bg if bg is None else bg
        w = self.tw(s, size, mono) + 12
        bx = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
        self.rect(bx, y - size - 2, w, size + 9, rx=5, fill=bg, stroke=bg, sw=0)
        self.text(bx + w / 2, y + 1, s, size, color, 500, "middle", mono)

    # ------------------------------------------------------------ document
    def begin(self) -> None:
        """Reserve the background slots; call once before drawing anything."""
        self.add(f'<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
                 f'<circle cx="1.5" cy="1.5" r="1.3" fill="{self.theme.grid}"/></pattern></defs>')
        self._bg_idx = len(self.p)
        self.add("")
        self.add("")

    def finish(self, height: float) -> str:
        """Fill in the background (solid + dot grid) at the final height and return the SVG text."""
        if self._bg_idx is None:
            raise RuntimeError("Canvas.begin() was not called")
        bg = self.theme.bg
        self.rect(0, 0, self.width, height, rx=0, fill=bg, stroke=bg, sw=0)
        self.rect(0, 0, self.width, height, rx=0, fill="url(#dots)", stroke="none", sw=0)
        dots = self.p.pop()
        self.p[self._bg_idx], self.p[self._bg_idx + 1] = self.p.pop(), dots
        return self.render(height)

    def render(self, height: float) -> str:
        w = self.width
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{height}" viewBox="0 0 {w} {height}">'
                + "".join(self.p) + "</svg>")
