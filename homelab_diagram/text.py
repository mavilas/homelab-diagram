"""Text width measurement for layout decisions.

Widths come from the real font through Pillow when Fira Sans is installed;
otherwise a rough per-character estimate keeps rendering possible. The
preflight in rsvg.py refuses to render when the fonts are missing, because
rsvg would then fall back to another face and every width would be off.
"""
from __future__ import annotations

from .commands import CommandError, run
from functools import lru_cache

FC_TIMEOUT_S = 5
_WEIGHT_STYLE = {700: "bold", 600: "semibold", 400: "regular"}


def tw(s: str, size: float, mono: bool = False) -> float:
    """Rough text width (the original estimate used for pills and labels)."""
    return len(s) * size * (0.6 if mono else 0.53)


def tw_title(s: str, size: float) -> float:
    """Width estimate for bold title text (capitals are wider than lowercase)."""
    return sum(0.68 if c.isupper() else 0.58 if c.isdigit() else 0.5 for c in s) * size


def fc_match(pattern: str, fmt: str) -> str | None:
    """One fontconfig lookup; None when fontconfig is unavailable."""
    try:
        out = run(["fc-match", "-f", fmt, pattern], timeout=FC_TIMEOUT_S)
    except CommandError:
        return None
    return out.stdout.strip() or None


def font_file(family: str, weight: int) -> str | None:
    """Path of the installed face, or None if fontconfig would substitute another family."""
    pattern = f"{family}:{_WEIGHT_STYLE[weight]}"
    if family not in (fc_match(pattern, "%{family}") or ""):
        return None
    return fc_match(pattern, "%{file}")


@lru_cache(maxsize=None)
def _font(family: str, weight: int, size: float):
    from PIL import ImageFont   # optional dependency, imported only when measuring
    path = font_file(family, weight)
    if path is None:
        raise LookupError(f"{family} {weight} not installed")
    return ImageFont.truetype(path, size=size * 8)


@lru_cache(maxsize=None)
def _have_real_fonts(family: str) -> bool:
    try:
        for w in _WEIGHT_STYLE:
            _font(family, w, 10)
        return True
    except Exception:   # no Pillow or no font file: fall back to the estimate
        return False


def measure(s: str, size: float, weight: int = 700, family: str = "Fira Sans") -> float:
    """Rendered width of s in px, from the real font when available."""
    if _have_real_fonts(family):
        return _font(family, weight, size).getlength(s) / 8
    return tw_title(s, size)
