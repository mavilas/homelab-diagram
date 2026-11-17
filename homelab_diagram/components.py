"""Composite pieces of the style: cards, physical-device folders, hardware bars and zones.

Every function draws onto the Canvas passed as its first argument and returns
nothing unless documented. Dimensions are SVG user units.
"""
from __future__ import annotations

from typing import Callable, Mapping, Sequence

from .canvas import Canvas
from .text import measure

TAB = 34   # height of the folder tab on physical-device cards

Hostname = Callable[[Mapping], "tuple[str | None, str | None]"]


def card(c: Canvas, x, y, w, h, color=None, title=None, icons=None, sub_=None, isz=34, tsize=19) -> float:
    """Panel with a colored left accent, icons, title and subtitle. Returns the text x position."""
    t = c.theme
    c.rect(x, y, w, h, rx=14, fill=t.panel, stroke=(color + "aa") if color else t.border, sw=1.6)
    if color:
        c.add(f'<rect x="{x+1}" y="{y+14}" width="4" height="{h-28}" rx="2" fill="{color}"/>')
    ix = x + 18
    for ic in icons or []:
        c.icon(ic, ix, y + 16, isz)
        ix += isz + 6
    tx_ = ix + 4 if icons else x + 18
    if title:
        c.text(tx_, y + 16 + isz * 0.5 - (2 if sub_ else -6), title, tsize, t.text, 600)
    if sub_:
        c.text(tx_, y + 16 + isz * 0.5 + 17, sub_, 13, t.muted, 400)
    return tx_


def hw_bar(c: Canvas, x, y, h) -> None:
    """Left accent bar = this card is a physical box / hardware part."""
    c.add(f'<rect x="{x+1}" y="{y+12}" width="4" height="{h-24}" rx="2" fill="{c.theme.hardware}"/>')


def tab_width(c: Canvas, g: Mapping) -> float:
    """Tab fits 'name · type' (name 20px bold, type 14px semibold), measured from the font."""
    f = c.theme.sans
    return (16 + measure(g["name"], 20, 700, f) + 7 + measure("·", 20, 700, f) + 7
            + measure(g["type"], 14, 600, f) + 18)


def folder(c: Canvas, x, y, w, h, tab_w, fill, stroke, sw) -> None:
    """Card body at (x, y, w, h) with a folder tab on its top-left edge, tab_w wide and TAB high."""
    t = y - TAB
    r, rt, sl = 12, 9, 16
    d = (f"M{x},{y+h-r} L{x},{t+rt} Q{x},{t} {x+rt},{t} L{x+tab_w-sl:.1f},{t} "
         f"C{x+tab_w-sl/3:.1f},{t} {x+tab_w-sl/3:.1f},{y} {x+tab_w+sl/2:.1f},{y} "
         f"L{x+w-r},{y} Q{x+w},{y} {x+w},{y+r} L{x+w},{y+h-r} Q{x+w},{y+h} {x+w-r},{y+h} "
         f"L{x+r},{y+h} Q{x},{y+h} {x},{y+h-r} Z")
    c.add(f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def addr(c: Canvas, x, y, ip, color, host=None, host_color=None, size=12) -> None:
    """Address line: 'ip · host' in mono; host_color marks a public hostname (else muted VLAN color)."""
    c.text(x, y, ip, size, color, 500, mono=True)
    if host:
        cw_ = size * 0.6                      # Fira Code advance width
        dx = x + len(ip) * cw_ + cw_ * 0.6
        c.text(dx, y, "·", size, c.theme.muted, 400, mono=True)
        c.text(dx + cw_ * 1.6, y, host, size, host_color or color, 400, mono=True, op=1 if host_color else 0.85)


def device_card(c: Canvas, x, y, w, h, icons: Sequence[str], g: Mapping, color, fill=None, stroke=None, sw=1.6,
                hostname: Hostname | None = None) -> None:
    """Physical device: folder tab 'name · type'; body = icon, model, address line, OS, optional config line.

    g needs name, type and ip; model, os and config are optional. hostname(g)
    may return (text, color) for a second address part.
    """
    t = c.theme
    folder(c, x, y, w, h, tab_width(c, g), t.panel if fill is None else fill, stroke or color + "aa", sw)
    c.add(f'<text x="{x+16}" y="{y-10}" font-family="{t.sans}" fill="{t.text}">'
          f'<tspan font-size="20" font-weight="700">{c.esc(g["name"])}</tspan>'
          f'<tspan dx="7" font-size="20" font-weight="700" fill-opacity="0.6">·</tspan>'
          f'<tspan dx="7" font-size="14" font-weight="600">{c.esc(g["type"])}</tspan></text>')
    ix = x + 14
    for ic in icons:                      # icon spans the three body lines (full name … OS)
        c.icon(ic, ix, y + 15, 54)
        ix += 58
    tx_ = ix + 8
    dy = 0 if g.get("os") else 8          # no OS line → center the two lines on the icon
    c.text(tx_, y + 28 + dy, g.get("model") or "custom build", 14, t.text if g.get("model") else t.muted, 500)
    if g.get("ip"):
        host, hcol = hostname(g) if hostname else (None, None)
        addr(c, tx_, y + 48 + dy, g["ip"], color, host, hcol)
    if g.get("os"):
        c.text(tx_, y + 66, g["os"], 12, t.muted, 400)
    if g.get("config"):                   # optional 4th line: how the device is set up
        c.text(tx_, y + 84, g["config"], 12, t.faint, 400)


def zone(c: Canvas, x, y, w, h, color, title=None, tag=None, note=None) -> None:
    """Tinted group area (like the DMZ zone): optional title, a pill tag top-right and a note line."""
    c.rect(x, y, w, h, rx=14, fill=color + "0d", stroke=color + "88", sw=1.5)
    if tag:
        c.pill(x + w - 14, y + 16, tag, color, 10.5, mono=True, h=19, pad=6, anchor="end")
    if title:
        c.text(x + 18, y + 34, title, 20, c.theme.text, 700)
    if note:
        c.text(x + 18, y + (56 if title else 31), note, 12.5, c.theme.muted, 400)
