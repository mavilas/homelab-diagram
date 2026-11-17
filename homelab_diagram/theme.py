"""Color palette, fonts and line widths of the homelab-diagram style.

A Theme is immutable so one render cannot change the look of another. The
default DARK theme reproduces the original r/homelab diagram exactly.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping


def _frozen(d: dict) -> Mapping:
    return MappingProxyType(dict(d))


@dataclass(frozen=True)
class Theme:
    """Every color and font the drawing primitives use. Colors are '#rrggbb' strings."""

    name: str = "dark"
    bg: str = "#0b0f15"
    grid: str = "#151c26"
    panel: str = "#111821"
    panel2: str = "#161f2b"
    chip: str = "#19222e"
    border: str = "#253042"
    text: str = "#e6edf3"
    muted: str = "#8d9aab"
    faint: str = "#5d6a7c"
    trunk: str = "#d5dde6"
    trunk_border: str = "#3a475a"   # border for devices on a tagged trunk (not in a single VLAN)
    link: str = "#79c0ff"
    hardware: str = "#c08a5c"       # "physical hardware" accent bar
    sans: str = "Fira Sans"
    mono: str = "Fira Code"
    # access-line widths by negotiated link speed; a trunk adds TRUNK_EXTRA
    speed_width: Mapping[str, float] = field(
        default_factory=lambda: _frozen({"10G": 9.5, "2.5G": 3.8, "1G": 2.4, "100M": 1.4}))
    trunk_extra: float = 3.4
    # named accent colors a spec can use instead of hex values
    accents: Mapping[str, str] = field(default_factory=lambda: _frozen({
        "blue": "#58a6ff", "purple": "#bc8cff", "cyan": "#39c5cf", "green": "#3fb950",
        "orange": "#f0883e", "red": "#f85149", "yellow": "#d29922", "pink": "#db61a2",
        "grey": "#6b7a90", "tan": "#c08a5c"}))

    def color(self, value: str | None) -> str | None:
        """Resolve an accent name or a hex color; None stays None."""
        if value is None:
            return None
        return self.accents.get(value, value)

    def trunk_width(self, speed: str) -> float:
        return self.speed_width[speed] + self.trunk_extra


DARK = Theme()

LIGHT = dataclasses.replace(
    DARK, name="light", bg="#ffffff", grid="#eef1f5", panel="#f6f8fa", panel2="#eef1f5",
    chip="#eaeef2", border="#d0d7de", text="#1f2328", muted="#59636e", faint="#818b98",
    trunk="#57606a", trunk_border="#8c959f", link="#0969da")

THEMES: Mapping[str, Theme] = _frozen({"dark": DARK, "light": LIGHT})
