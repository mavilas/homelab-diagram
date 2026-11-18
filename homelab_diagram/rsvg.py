"""PNG conversion through rsvg-convert, with a preflight that fails loudly.

librsvg older than 2.60 (for example Debian bookworm's 2.54) renders the
diagram but silently drops every <image> icon. preflight() checks the version
and then proves icons survive by rendering a probe SVG that embeds a solid
green SVG icon and reading the pixel back.
"""
from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .text import fc_match

MIN_LIBRSVG = (2, 60, 0)
RSVG_ENV = "HOMELAB_DIAGRAM_RSVG"          # optional path to rsvg-convert
RSVG_TIMEOUT_S = int(os.environ.get("HOMELAB_DIAGRAM_RSVG_TIMEOUT_S", "120"))
PNG_ZOOM = 1.6                               # PNG pixels = SVG units x 1.6 (original output size)
REQUIRED_FONTS = ("Fira Sans", "Fira Code")
_PROBE_COLOR = (0, 200, 0)


class PreflightError(SystemExit):
    """Raised (exit status 1) when the renderer would produce a wrong picture."""


@dataclass(frozen=True)
class Preflight:
    rsvg: str
    version: tuple[int, int, int]


def rsvg_binary() -> str:
    exe = os.environ.get(RSVG_ENV) or shutil.which("rsvg-convert")
    if not exe:
        raise PreflightError("rsvg-convert not found: install librsvg >= 2.60 (see README, Requirements)")
    return exe


def parse_version(text: str) -> tuple[int, int, int]:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not m:
        raise PreflightError(f"cannot read the librsvg version from: {text.strip()!r}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def librsvg_version(exe: str) -> tuple[int, int, int]:
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=RSVG_TIMEOUT_S, check=False)
    return parse_version(out.stdout + out.stderr)


def svg_to_png(exe: str, svg: Path, png: Path, zoom: float = PNG_ZOOM) -> None:
    subprocess.run([exe, "-z", str(zoom), "-o", str(png), str(svg)], check=True, timeout=RSVG_TIMEOUT_S)


def _probe_svg() -> str:
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
            '<rect width="10" height="10" fill="#00c800"/></svg>')
    uri = "data:image/svg+xml;base64," + base64.b64encode(icon.encode()).decode()
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<rect width="20" height="20" fill="#000000"/>'
            f'<image x="0" y="0" width="20" height="20" href="{uri}"/></svg>')


def icons_survive(exe: str) -> bool:
    """Render the probe and check the center pixel is the icon's green, not the black background."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        svg, png = Path(tmp, "probe.svg"), Path(tmp, "probe.png")
        svg.write_text(_probe_svg())
        svg_to_png(exe, svg, png, zoom=1)
        with Image.open(png) as im:
            return im.convert("RGB").getpixel((10, 10)) == _PROBE_COLOR


def missing_fonts() -> list[str]:
    return [f for f in REQUIRED_FONTS if f not in (fc_match(f, "%{family}") or "")]


def preflight(check_fonts: bool = True) -> Preflight:
    """Fail loudly unless rsvg-convert >= 2.60 renders embedded icons and the Fira fonts are installed."""
    exe = rsvg_binary()
    version = librsvg_version(exe)
    if version < MIN_LIBRSVG:
        need = ".".join(map(str, MIN_LIBRSVG))
        have = ".".join(map(str, version))
        raise PreflightError(f"librsvg {have} is too old: {need} or newer is required, older versions "
                             "silently drop every icon (Debian bookworm ships 2.54)")
    if not icons_survive(exe):
        raise PreflightError(f"rsvg-convert {'.'.join(map(str, version))} dropped the embedded probe icon: "
                             "icons would be missing from the PNG")
    if check_fonts and (gone := missing_fonts()):
        raise PreflightError(f"fonts not installed: {', '.join(gone)} (fontconfig would substitute them)")
    return Preflight(exe, version)
