"""Inventory, redaction and the lab-specific helpers shared by top.py and server.py.

Usage (through ../build.py): python3 build.py [--unredacted] [--inventory FILE]
Line width encodes link speed (SPEED_W); trunks are drawn as a light cable with a dark core.
"""
import functools
import pathlib
import sys

import yaml

from homelab_diagram import DARK, Canvas, IconStore
from homelab_diagram import components as _c
from homelab_diagram.components import TAB  # noqa: F401  (used by the layout modules)
from homelab_diagram.text import measure, tw_title  # noqa: F401
from homelab_diagram.text import tw as _tw

ROOT = pathlib.Path(__file__).resolve().parent.parent
if "--inventory" in sys.argv:
    _i = sys.argv.index("--inventory") + 1
    if _i >= len(sys.argv) or sys.argv[_i].startswith("--"):
        raise SystemExit("--inventory needs a file")
    INV_FILE = pathlib.Path(sys.argv[_i])
else:
    INV_FILE = ROOT / "inventory.yaml"
INV = yaml.safe_load(INV_FILE.read_text())
ICONS = ROOT / "icons"
OUT = ROOT / "out"

UNREDACTED = "--unredacted" in sys.argv
RED = INV["redact"]
DOMAIN = INV["meta"]["domain"]
SHOWN_DOMAIN = DOMAIN if (UNREDACTED or not RED["domain"]) else RED["domain_placeholder"]

W = 2400
THEME = DARK

# ---------------------------------------------------------------- palette (from the theme)
BG, GRID, PANEL, PANEL2, CHIP = THEME.bg, THEME.grid, THEME.panel, THEME.panel2, THEME.chip
BORDER, TEXT, MUTED, FAINT = THEME.border, THEME.text, THEME.muted, THEME.faint
TRUNK, TRUNK_BORDER, LINK, HWC = THEME.trunk, THEME.trunk_border, THEME.link, THEME.hardware
SANS, MONO = THEME.sans, THEME.mono
SPEED_W = dict(THEME.speed_width)   # access-line widths
# colors only this lab's picture uses
REDDIT = "#ff5722"
DISK = "#1d2734"
DISK_EDGE = "#5a6b82"
PROTO = {"TCP": "#79c0ff", "UDP": "#39c5cf"}
UNKNOWN = "#6b7a90"   # a used port whose VLANs aren't known
VLAN = {v["key"]: v for v in INV["vlans"]}
C = {k: v["color"] for k, v in VLAN.items()}


def trunk_w(speed):
    return THEME.trunk_width(speed)


def sub(s):
    """Fill {domain} placeholders and apply redaction."""
    s = str(s).replace("{domain}", SHOWN_DOMAIN)
    if not UNREDACTED and RED["domain"]:
        s = s.replace(DOMAIN, SHOWN_DOMAIN)
    return s


def tw(s, size, mono=False):
    """Rough text width for layout decisions."""
    return _tw(sub(s), size, mono)


def fqdn(h):
    return f"{h}.{SHOWN_DOMAIN}"


S = Canvas(W, THEME, IconStore([ICONS]), text_filter=sub)
esc = S.esc


def hostname(g):
    """(text, color) for the second address line: public host, or <name>.internal."""
    if g.get("host"):
        return fqdn(g["host"]), LINK
    if g.get("internal"):
        return f"{g['internal']}.internal", None
    return None, None


def addr(x, y, ip, g, color, size=12):
    """Address line under a card's name: IP · hostname (a public Traefik hostname is blue)."""
    name, ncol = hostname(g)
    _c.addr(S, x, y, ip, color, name, ncol, size)


card = functools.partial(_c.card, S)
hw_bar = functools.partial(_c.hw_bar, S)
folder = functools.partial(_c.folder, S)


def tab_width(g):
    return _c.tab_width(S, g)


def device_card(x, y, w, h, icons, g, color, fill=PANEL, stroke=None, sw=1.6):
    _c.device_card(S, x, y, w, h, icons, g, color, fill, stroke, sw, hostname=hostname)


def jack(x, y, w, h, fill, stroke, sfp=False):
    S.rect(x, y, w, h, rx=5, fill=fill, stroke=stroke, sw=1.4)
    if sfp:
        S.rect(x + 8, y + 9, w - 16, h - 18, rx=2, fill="#0b0f15", stroke="none", sw=0)
    else:
        S.add(f'<path d="M{x+10},{y+h-8} v-14 h6 v-5 h{w-32} v5 h6 v14 z" fill="#0b0f15"/>')


def ticks(cx, y, untagged=None, tagged=(), up=False):
    """VLAN indicator bars for a port: tall = untagged, short = tagged. up=True grows upwards."""
    vk = ([untagged] if untagged else []) + list(tagged)
    x0 = cx - (len(vk) * 7) / 2
    for j, k in enumerate(vk):
        hh = 8 if k == untagged else 5
        yy = y - hh if up else y
        S.add(f'<rect x="{x0 + j*7:.1f}" y="{yy}" width="5" height="{hh}" rx="1" fill="{C[k]}"/>')


def vlan_tag(vkey):
    v = VLAN[vkey]
    return f"{v['tag']} · {v['name']}" if v["tag"].startswith("VLAN") else v["name"]
