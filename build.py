#!/usr/bin/env python3
"""Render the original author's homelab diagram (r/homelab style) from inventory.yaml.

Usage: python3 build.py [--unredacted] [--inventory FILE]
                                         → out/homelab.svg + out/homelab.png
                                            (--unredacted → out/homelab-unredacted.*)
Content comes from inventory.yaml; the layout of this one lab is hand-placed in
original/top.py and original/server.py on top of the homelab_diagram library.
For a new diagram, write a spec and use `python3 -m homelab_diagram render` instead.
Written with Claude (Anthropic) in Claude Code, see README.md.
"""
from homelab_diagram.rsvg import preflight

if __name__ == "__main__":
    preflight()   # fail loudly before drawing if librsvg would drop the icons or the fonts are missing
    from original import server
    server.write()
