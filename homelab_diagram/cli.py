"""Command line: homelab-diagram {render,check,validate}.

Exit status: 0 success, 1 a check failed (spec, icons, layout, renderer),
2 usage error. Output files are written only after every check passed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .icon_lock import verify as verify_lock
from .icons import IconStore
from .layout import LayoutError
from .render import icon_dirs, render
from .rsvg import preflight
from .spec import SpecError, load_spec


def _render(args) -> int:
    if not args.out and not args.svg:
        print("render: give --out PNG and/or --svg SVG", file=sys.stderr)
        return 2
    spec = load_spec(args.spec)
    render(spec, args.out, args.svg, args.icons)
    for p in (args.out, args.svg):
        if p:
            print(p)
    return 0


def _validate(args) -> int:
    from .layout import Layout, needed_icons
    from .canvas import Canvas
    from .theme import THEMES
    spec = load_spec(args.spec)
    store = IconStore(icon_dirs(args.icons))
    if missing := store.missing(needed_icons(spec)):
        print(f"missing icon(s): {', '.join(missing)}", file=sys.stderr)
        return 1
    Layout(spec, Canvas(spec.width, THEMES[spec.theme], store)).compute()
    print(f"{args.spec}: ok ({len(spec.nodes)} nodes, {len(spec.groups)} groups, {len(spec.links)} links)")
    return 0


def _check(args) -> int:
    pre = preflight()
    print(f"rsvg-convert {'.'.join(map(str, pre.version))} at {pre.rsvg}: icons render, fonts installed")
    problems = verify_lock(Path(args.icon_dir)) if args.icon_dir else []
    for p in problems:
        print(p, file=sys.stderr)
    if args.icon_dir and not problems:
        print(f"{args.icon_dir}: every locked icon matches icons.lock.json")
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="homelab-diagram", description="Render homelab-style diagrams offline.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render", help="render a YAML/JSON spec to PNG (and SVG)")
    r.add_argument("spec", type=Path)
    r.add_argument("-o", "--out", type=Path, help="PNG output path")
    r.add_argument("--svg", type=Path, help="also write the SVG here (contains embedded third-party icons)")
    r.add_argument("--icons", type=Path, action="append", default=[], help="extra icon directory (repeatable)")
    r.set_defaults(func=_render)
    v = sub.add_parser("validate", help="check a spec, its icons and its layout without rendering")
    v.add_argument("spec", type=Path)
    v.add_argument("--icons", type=Path, action="append", default=[])
    v.set_defaults(func=_validate)
    c = sub.add_parser("check", help="preflight: librsvg >= 2.60 keeps icons, fonts installed, icon lock")
    c.add_argument("--icon-dir", help="also verify this directory against icons.lock.json")
    c.set_defaults(func=_check)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SpecError, LayoutError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except SystemExit as e:              # IconError, PreflightError, LockError carry their message
        if isinstance(e.code, str):
            print(f"error: {e.code}", file=sys.stderr)
            return 1
        raise
