#!/usr/bin/env python3
"""Download the third-party service icons into icons/, pinned and hash-checked.

They are not part of this repo (they belong to their projects). Source and
commit are recorded in icons.lock.json; every file must match its sha256 or
nothing from the run is accepted for that icon. The own glyph-*.svg icons
are already in icons/.

Usage: python3 fetch_icons.py [--dest DIR] [--verify]
       python3 fetch_icons.py --update-lock   (maintainers: after changing the commit or adding icons)
"""
import argparse
import pathlib
import sys

from homelab_diagram.icon_lock import DEFAULT_ICON_DIR, fetch, verify, write_lock


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", type=pathlib.Path, default=DEFAULT_ICON_DIR)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="offline: check dest against the lock")
    mode.add_argument("--update-lock", action="store_true", help="record the hashes of the pinned commit")
    args = ap.parse_args(argv)
    if args.verify:
        problems = verify(args.dest)
        print("\n".join(problems) if problems else f"icons in {args.dest} match icons.lock.json")
        return 1 if problems else 0
    lock = fetch(args.dest, update=args.update_lock)
    if args.update_lock:
        write_lock(lock)
    print(f"icons in {args.dest}: {len(lock.icons)} pinned at {lock.commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
