"""Render a spec to SVG and PNG, offline and deterministically.

The pipeline is: validate spec -> check every icon exists -> preflight
rsvg-convert (version, icon probe, fonts) -> layout -> SVG -> PNG. Nothing
here opens a network connection; icons are read from local directories.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Sequence

from .canvas import Canvas
from .icons import DEFAULT_ICON_DIR, IconError, IconStore
from .layout import draw, needed_icons
from .rsvg import preflight, svg_to_png
from .spec import Spec
from .theme import THEMES

ICON_DIRS_ENV = "HOMELAB_DIAGRAM_ICON_DIRS"   # extra icon directories, os.pathsep-separated


def icon_dirs(extra: Sequence[Path | str] = ()) -> list[Path]:
    """Search order: explicit --icons dirs, then $HOMELAB_DIAGRAM_ICON_DIRS, then the repo's icons/."""
    env = [p for p in os.environ.get(ICON_DIRS_ENV, "").split(os.pathsep) if p]
    return [Path(p) for p in (*extra, *env)] + [DEFAULT_ICON_DIR]


def render_svg(spec: Spec, icons: IconStore) -> str:
    missing = icons.missing(needed_icons(spec))
    if missing:
        raise IconError(f"missing icon(s): {', '.join(missing)} (searched {', '.join(map(str, icons.dirs))})")
    return draw(spec, Canvas(spec.width, THEMES[spec.theme], icons))


def render(spec: Spec, png: Path | None, svg: Path | None = None, extra_icon_dirs: Sequence[Path | str] = ()) -> str:
    """Write the PNG (and the SVG if asked); returns the SVG text. Fails before writing on any check."""
    icons = IconStore(icon_dirs(extra_icon_dirs))
    text = render_svg(spec, icons)
    pre = preflight() if png else None
    if png and pre:
        png = Path(png)
        png.parent.mkdir(parents=True, exist_ok=True)
        # Conversion may create a partial file before failing. Stage it on the
        # destination filesystem so a failed tool never damages an old output.
        with tempfile.TemporaryDirectory(dir=png.parent) as tmp:
            src, ready = Path(tmp, "diagram.svg"), Path(tmp, "diagram.png")
            src.write_text(text, encoding="utf-8")
            svg_to_png(pre.rsvg, src, ready)
            if svg:
                _write_svg(Path(svg), text)
            os.replace(ready, png)
    elif svg:
        _write_svg(Path(svg), text)
    return text


def _write_svg(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
