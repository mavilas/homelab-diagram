"""Icon lookup and embedding.

Icons are local files only (SVG or PNG): rendering never downloads anything.
Third-party icons come from fetch_icons.py, which pins them to a commit and
checks each file's sha256 (see icons.lock.json).
"""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Iterable, Sequence

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ICON_DIR = PACKAGE_ROOT / "icons"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
MIME = {".svg": "image/svg+xml", ".png": "image/png"}


class IconError(SystemExit):
    """A missing or invalid icon stops the render with a clear message (exit status 1)."""

    def __init__(self, message: str):
        super().__init__(message)


class IconStore:
    """Resolves icon names to files in an ordered list of directories."""

    def __init__(self, dirs: Sequence[Path | str] = (DEFAULT_ICON_DIR,)):
        self.dirs = [Path(d) for d in dirs]
        self._cache: dict[str, str] = {}

    def path(self, name: str) -> Path:
        if not NAME_RE.match(name):
            raise IconError(f"invalid icon name {name!r}: use lowercase letters, digits, '.', '-', '_'")
        for d in self.dirs:
            for ext in MIME:
                f = d / f"{name}{ext}"
                if f.is_file():
                    return f
        raise IconError(f"missing icon '{name}': run python3 fetch_icons.py")

    def has(self, name: str) -> bool:
        try:
            self.path(name)
            return True
        except IconError:
            return False

    def data_uri(self, name: str) -> str:
        if name not in self._cache:
            f = self.path(name)
            self._cache[name] = f"data:{MIME[f.suffix]};base64,{base64.b64encode(f.read_bytes()).decode()}"
        return self._cache[name]

    def missing(self, names: Iterable[str]) -> list[str]:
        return sorted({n for n in names if not self.has(n)})
