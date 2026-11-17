"""Pinned third-party icons: download at one commit, verify sha256, never follow a branch.

icons.lock.json records the source repository, the commit, the URL template
and, per local icon name, the remote name, an optional recolor and the
sha256 of the file as written to the icons directory. fetch() refuses any
file whose hash differs; verify() checks an icons directory offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .icons import DEFAULT_ICON_DIR, NAME_RE, PACKAGE_ROOT

LOCK_FILE = PACKAGE_ROOT / "icons.lock.json"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
FETCH_TIMEOUT_S = 20
FETCH_TRIES = 3
USER_AGENT = "homelab-diagram/1.0"


class LockError(SystemExit):
    """Lock file, download or verification problem (exit status 1)."""


@dataclass(frozen=True)
class LockedIcon:
    name: str
    remote: str
    sha256: str | None
    recolor: tuple[str, str] | None = None


@dataclass(frozen=True)
class Lock:
    source: str
    commit: str
    url: str
    icons: tuple[LockedIcon, ...]

    def url_for(self, icon: LockedIcon) -> str:
        return self.url.format(commit=self.commit, name=icon.remote)


def load_lock(path: Path = LOCK_FILE) -> Lock:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not COMMIT_RE.match(raw.get("commit", "")):
        raise LockError(f"{path}: commit must be a full 40-character sha, not a branch or tag")
    if not raw.get("url", "").startswith("https://") or "{commit}" not in raw["url"]:
        raise LockError(f"{path}: url must be https and contain {{commit}}")
    icons = []
    for name, entry in sorted(raw["icons"].items()):
        if not NAME_RE.match(name) or not NAME_RE.match(entry["remote"]):
            raise LockError(f"{path}: invalid icon name {name!r}")
        rc = entry.get("recolor")
        icons.append(LockedIcon(name, entry["remote"], entry.get("sha256"), tuple(rc) if rc else None))
    return Lock(raw["source"], raw["commit"], raw["url"], tuple(icons))


def write_lock(lock: Lock, path: Path = LOCK_FILE) -> None:
    data = {"source": lock.source, "commit": lock.commit, "url": lock.url, "icons": {
        i.name: {"remote": i.remote, **({"recolor": list(i.recolor)} if i.recolor else {}), "sha256": i.sha256}
        for i in lock.icons}}
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str) -> bytes:
    last: Exception | None = None
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(FETCH_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as r:
                return r.read()
        except Exception as e:   # bounded retry with backoff; a 404 will not get better
            last = e
            if getattr(e, "code", None) in (403, 404):
                break
            time.sleep(2 * (attempt + 1))
    raise LockError(f"download failed: {url}: {last}")


def materialize(icon: LockedIcon, raw: bytes) -> bytes:
    if icon.recolor:
        old, new = icon.recolor
        text = raw.decode("utf-8")
        if old not in text:
            raise LockError(f"{icon.name}: recolor pattern {old!r} not found")
        return text.replace(old, new).encode("utf-8")
    return raw


ICON_MODE = 0o644   # renders run as another user (container), so icons must be world-readable


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")   # mkstemp creates 0600
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(tmp, ICON_MODE)
    os.replace(tmp, path)


def fetch(dest: Path = DEFAULT_ICON_DIR, lock: Lock | None = None, update: bool = False) -> Lock:
    """Download every locked icon into dest. update=True records new hashes (maintainers, after review)."""
    lock = lock or load_lock()
    dest.mkdir(parents=True, exist_ok=True)
    out, failed = [], []
    for icon in lock.icons:
        data = materialize(icon, _download(lock.url_for(icon)))
        digest = sha256(data)
        if not update and digest != icon.sha256:
            failed.append(f"{icon.name}: sha256 {digest} != locked {icon.sha256}")
            continue
        _atomic_write(dest / f"{icon.name}.svg", data)
        out.append(LockedIcon(icon.name, icon.remote, digest, icon.recolor))
    if failed:
        raise LockError("icon hash mismatch, nothing trusted from these files:\n  " + "\n  ".join(failed))
    return Lock(lock.source, lock.commit, lock.url, tuple(out))


def verify(icon_dir: Path = DEFAULT_ICON_DIR, lock: Lock | None = None) -> list[str]:
    """Offline check; returns problems (missing file or wrong hash), empty when all locked icons match."""
    lock = lock or load_lock()
    problems = []
    for icon in lock.icons:
        f = icon_dir / f"{icon.name}.svg"
        if not f.is_file():
            problems.append(f"{icon.name}: missing (run: python3 fetch_icons.py)")
        elif sha256(f.read_bytes()) != icon.sha256:
            problems.append(f"{icon.name}: sha256 does not match icons.lock.json")
    return problems
